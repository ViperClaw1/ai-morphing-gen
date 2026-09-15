"""Turns an ordered sequence of face photos into a morphed video frame sequence.

Pipeline (docs/implementation_plan.md §1.4):
  1. normalize   — resize/crop every source photo to the same working canvas
  2. landmarks   — MediaPipe face mesh, per photo
  3. warp+blend  — per in-between frame: triangulated geometric warp + cross-dissolve
  4. easing      — non-linear progression so motion doesn't look mechanical
  5. repair      — every frame gets one gpu_worker /repair call (see gpu_client.py)
  6. deflicker   — cheap temporal smoothing across the repaired sequence

ffmpeg_service.py picks up from here: cinematic effects + final encode.
"""

import argparse
import urllib.request
from collections.abc import Callable
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from loguru import logger
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions, RunningMode
from PIL import Image

from app.core.config import get_settings
from app.services.gpu_client import repair_frame

# Google's official model — see https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker
_LANDMARKER_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)

# Repair prompt per style — only one preset exists (full SettingsPanel is Phase 2 §2.2
# scope). Kept as a plain dict, not a schema/enum, until a second preset actually exists.
STYLE_PRESETS: dict[str, tuple[str, str]] = {
    "default": (
        "high quality portrait, natural skin, preserve identity and pose, same composition",
        "blurry, distorted face, deformed, extra limbs, low quality, artifacts, wrong identity",
    ),
}


# 8 fixed points (4 corners + 4 edge midpoints) added to every landmark set so the whole
# canvas warps, not just the face interior — otherwise hair/shoulders/background stay
# static while only the face region moves, which looks broken, not "morphed."
def _boundary_points(width: int, height: int) -> np.ndarray:
    return np.array(
        [
            [0, 0],
            [width // 2, 0],
            [width - 1, 0],
            [0, height // 2],
            [width - 1, height // 2],
            [0, height - 1],
            [width // 2, height - 1],
            [width - 1, height - 1],
        ],
        dtype=np.float32,
    )


class NoFaceDetectedError(RuntimeError):
    pass


_landmarker: FaceLandmarker | None = None


def _get_landmarker() -> FaceLandmarker:
    global _landmarker
    if _landmarker is not None:
        return _landmarker

    settings = get_settings()
    model_path = settings.mediapipe_model_path
    if not model_path.exists():
        logger.info("Downloading face landmark model to {}", model_path)
        model_path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(_LANDMARKER_MODEL_URL, model_path)

    options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path)),
        running_mode=RunningMode.IMAGE,
        num_faces=1,
    )
    _landmarker = FaceLandmarker.create_from_options(options)
    return _landmarker


def detect_landmarks(image_bgr: np.ndarray) -> np.ndarray:
    """Returns Nx2 pixel-coordinate landmarks (478 points) for the one largest face.
    Raises NoFaceDetectedError if none found — callers must not silently skip this;
    it's the same check the real upload flow's face-detection gate will use (§1.3).
    """
    height, width = image_bgr.shape[:2]
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
    result = _get_landmarker().detect(mp_image)
    if not result.face_landmarks:
        raise NoFaceDetectedError("No face detected in one of the source photos.")

    points = np.array(
        [[lm.x * width, lm.y * height] for lm in result.face_landmarks[0]],
        dtype=np.float32,
    )
    return np.vstack([points, _boundary_points(width, height)])


def _normalize(image_bgr: np.ndarray, width: int, height: int) -> np.ndarray:
    """Resize+center-crop to the working canvas (like CSS object-fit: cover) — keeps
    aspect ratio instead of squishing faces, which would break landmark correspondence.
    """
    h, w = image_bgr.shape[:2]
    scale = max(width / w, height / h)
    resized = cv2.resize(image_bgr, (round(w * scale), round(h * scale)))
    rh, rw = resized.shape[:2]
    x0, y0 = (rw - width) // 2, (rh - height) // 2
    return resized[y0 : y0 + height, x0 : x0 + width]


def _ease(t: float) -> float:
    """Smoothstep — starts and ends slow, matches implementation_plan.md §1.4's 'easing'
    stage. Plain formula, no easing library needed for one curve."""
    return t * t * (3 - 2 * t)


def _triangulate(points: np.ndarray, width: int, height: int) -> list[tuple[int, int, int]]:
    subdiv = cv2.Subdiv2D((0, 0, width, height))
    for x, y in points:
        subdiv.insert((float(np.clip(x, 0, width - 1)), float(np.clip(y, 0, height - 1))))

    raw = subdiv.getTriangleList()
    if len(raw) == 0:
        return []

    # Subdiv2D quantizes points internally, so triangle vertices it returns aren't
    # bit-exact to what was inserted — exact/rounded-dict matching silently drops nearly
    # every triangle (this produced solid-black frames before). Nearest-neighbor is the
    # correct match; batching all triangle vertices into one distance matrix instead of
    # one numpy call per vertex is what makes it fast (~2850 individual calls collapsed
    # into a single (num_verts, num_points) matrix op).
    verts = raw.reshape(-1, 2)  # (num_triangles * 3, 2)
    dists = ((verts[:, None, :] - points[None, :, :]) ** 2).sum(axis=2)
    nearest = dists.argmin(axis=1).reshape(-1, 3)
    return [tuple(int(i) for i in tri) for tri in nearest]


def _warp_triangle(
    src: np.ndarray, src_tri: np.ndarray, dst_tri: np.ndarray
) -> tuple[np.ndarray, np.ndarray, tuple[int, int, int, int]]:
    """Affine-warps one triangle from src, cropped to its destination bounding box —
    NOT the full canvas. Warping the whole image per triangle (~950 triangles/frame from
    478 landmarks + boundary points) was the earlier version's bug: it turned a sub-second
    operation into ~17s/frame at just 384x384, and would be minutes/frame at Full HD.
    This is the standard approach (see LearnOpenCV's face-morph tutorial) — bound the work
    to what each triangle actually touches.
    """
    src_rect = cv2.boundingRect(src_tri.astype(np.float32))
    dst_rect = cv2.boundingRect(dst_tri.astype(np.float32))
    sx, sy, sw, sh = src_rect
    dx, dy, dw, dh = dst_rect

    src_crop = src[sy : sy + sh, sx : sx + sw]
    src_tri_local = src_tri - [sx, sy]
    dst_tri_local = (dst_tri - [dx, dy]).astype(np.float32)

    matrix = cv2.getAffineTransform(src_tri_local.astype(np.float32), dst_tri_local)
    warped = cv2.warpAffine(
        src_crop, matrix, (dw, dh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101
    )
    mask = np.zeros((dh, dw), dtype=np.uint8)
    cv2.fillConvexPoly(mask, dst_tri_local.astype(np.int32), 255)
    return warped, mask, dst_rect


def _warp_and_blend(
    img_a: np.ndarray, pts_a: np.ndarray, img_b: np.ndarray, pts_b: np.ndarray, t: float
) -> np.ndarray:
    """One morphed frame at progress t: both images warped toward the t-interpolated
    landmark positions, then cross-dissolved. Standard triangulation morph (LearnOpenCV's
    face-morph tutorial documents the same approach) — ponytail: this is real algorithmic
    complexity the task needs, not an unrequested abstraction.
    """
    height, width = img_a.shape[:2]
    mid_points = (1 - t) * pts_a + t * pts_b
    triangles = _triangulate(mid_points, width, height)

    warped_a = np.zeros_like(img_a, dtype=np.float32)
    warped_b = np.zeros_like(img_b, dtype=np.float32)

    for i0, i1, i2 in triangles:
        mid_tri = mid_points[[i0, i1, i2]]
        a_tri = pts_a[[i0, i1, i2]]
        b_tri = pts_b[[i0, i1, i2]]

        warped, mask, (x, y, w, h) = _warp_triangle(img_a, a_tri, mid_tri)
        mask_f = (mask.astype(np.float32) / 255.0)[..., None]
        region = warped_a[y : y + h, x : x + w]
        region[:] = region * (1 - mask_f) + warped.astype(np.float32) * mask_f

        warped, mask, (x, y, w, h) = _warp_triangle(img_b, b_tri, mid_tri)
        mask_f = (mask.astype(np.float32) / 255.0)[..., None]
        region = warped_b[y : y + h, x : x + w]
        region[:] = region * (1 - mask_f) + warped.astype(np.float32) * mask_f

    blended = (1 - t) * warped_a + t * warped_b
    return np.clip(blended, 0, 255).astype(np.uint8)


def _deflicker(frames: list[np.ndarray]) -> list[np.ndarray]:
    """3-tap temporal smoothing across the AI-repaired sequence.
    ponytail: naive fixed-weight blend, not optical-flow-based temporal consistency —
    upgrade if flicker is still visible after this; cheap enough to always run first.
    """
    if len(frames) < 3:
        return frames
    stacked = np.stack(frames).astype(np.float32)
    smoothed = stacked.copy()
    smoothed[1:-1] = 0.15 * stacked[:-2] + 0.7 * stacked[1:-1] + 0.15 * stacked[2:]
    return [np.clip(f, 0, 255).astype(np.uint8) for f in smoothed]


def _frame_plan(
    num_photos: int, fps: int, duration_seconds: float, hold_seconds: float
) -> tuple[int, list[int]]:
    """How many hold frames per photo, and how many transition frames per gap between
    consecutive photos. Even split across transitions, remainder to the last one —
    an explicit default, not specified by implementation_plan.md's prose.
    """
    hold_frames = max(round(fps * hold_seconds), 1)
    total_frames = max(round(fps * duration_seconds), num_photos)
    num_transitions = max(num_photos - 1, 1)

    transition_total = max(total_frames - num_photos * hold_frames, num_transitions)
    base = transition_total // num_transitions
    remainder = transition_total - base * num_transitions
    per_transition = [base] * num_transitions
    per_transition[-1] += remainder
    return hold_frames, per_transition


def generate_frames(
    photo_paths: list[Path],
    *,
    width: int,
    height: int,
    fps: int = 12,
    duration_seconds: float = 2.0,
    hold_seconds: float = 0.4,
    style_preset: str = "default",
    seed: int = 42,
    repair_fn: Callable[..., Image.Image] = repair_frame,
) -> list[Image.Image]:
    """Full stages 1-6. Returns the final repaired+deflickered frame sequence, in order.
    Resolution here is the *processing* resolution — must stay within gpu_worker's
    1024x1024 cap; ffmpeg_service.py handles the final upscale to the real output size.
    """
    if len(photo_paths) < 2:
        raise ValueError("Need at least 2 photos to morph between.")
    if style_preset not in STYLE_PRESETS:
        raise ValueError(f"Unknown style_preset {style_preset!r}. Known: {list(STYLE_PRESETS)}")
    prompt, negative_prompt = STYLE_PRESETS[style_preset]

    images = [_normalize(cv2.imread(str(p)), width, height) for p in photo_paths]
    landmarks = [detect_landmarks(img) for img in images]

    hold_frames, per_transition = _frame_plan(len(photo_paths), fps, duration_seconds, hold_seconds)

    raw_frames: list[np.ndarray] = []
    for photo_idx in range(len(images)):
        raw_frames.extend([images[photo_idx]] * hold_frames)
        if photo_idx == len(images) - 1:
            break
        n = per_transition[photo_idx]
        for i in range(1, n + 1):
            t = _ease(i / (n + 1))
            raw_frames.append(
                _warp_and_blend(
                    images[photo_idx],
                    landmarks[photo_idx],
                    images[photo_idx + 1],
                    landmarks[photo_idx + 1],
                    t,
                )
            )

    logger.info("Repairing {} frames via gpu_worker", len(raw_frames))
    repaired: list[np.ndarray] = []
    for i, frame in enumerate(raw_frames):
        pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        repaired_pil = repair_fn(
            pil_frame,
            prompt=prompt,
            negative_prompt=negative_prompt,
            seed=seed,
            request_id=f"morph-frame-{i:04d}",
        )
        repaired.append(cv2.cvtColor(np.array(repaired_pil.convert("RGB")), cv2.COLOR_RGB2BGR))

    final = _deflicker(repaired)
    return [Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB)) for f in final]


def _main() -> None:
    parser = argparse.ArgumentParser(description="Generate a morph video end-to-end.")
    parser.add_argument("--photos", nargs="+", required=True, type=Path)
    parser.add_argument(
        "--out-dir",
        required=True,
        type=Path,
        help="Where to save frame PNGs (kept for inspection).",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=512,
        help="Processing resolution — must stay <=1024 (gpu_worker's cap).",
    )
    parser.add_argument("--height", type=int, default=512)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--duration", type=float, default=2.0)
    parser.add_argument("--hold", type=float, default=0.4)
    parser.add_argument("--style", default="default")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out-video",
        type=Path,
        help="If set, assembles frames into an MP4 here via ffmpeg_service.",
    )
    parser.add_argument(
        "--video-width",
        type=int,
        help="Final video width — can exceed 1024 (ffmpeg upscales). Defaults to --width.",
    )
    parser.add_argument(
        "--video-height", type=int, help="Final video height. Defaults to --height."
    )
    parser.add_argument(
        "--no-zoom", action="store_true", help="Disable the cinematic zoom pass — plain scale only."
    )
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    frames = generate_frames(
        args.photos,
        width=args.width,
        height=args.height,
        fps=args.fps,
        duration_seconds=args.duration,
        hold_seconds=args.hold,
        style_preset=args.style,
        seed=args.seed,
    )
    for i, frame in enumerate(frames):
        frame.save(args.out_dir / f"frame_{i:05d}.png")
    print(f"Wrote {len(frames)} frames to {args.out_dir}")

    if args.out_video:
        from app.services.ffmpeg_service import assemble_video

        assemble_video(
            frames,
            args.out_video,
            width=args.video_width or args.width,
            height=args.video_height or args.height,
            fps=args.fps,
            zoom=not args.no_zoom,
        )
        print(f"Wrote video to {args.out_video}")


if __name__ == "__main__":
    _main()
