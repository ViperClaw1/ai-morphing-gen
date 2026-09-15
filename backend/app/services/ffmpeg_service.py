"""Cinematic pass + final MP4 encode (docs/implementation_plan.md §1.4/1.6, stages 8-9).

Takes the frame sequence morph_engine.py produces (already warped/blended/repaired/
deflickered) and:
  1. writes them to a temp PNG sequence
  2. applies a slow continuous zoom (Ken Burns-lite) via ffmpeg's zoompan filter
  3. scales to the real target resolution — frames are generated at a repair-safe
     resolution (<=1024px, gpu_worker's cap); Full HD 1080x1920 upscale happens here,
     not in morph_engine, via ffmpeg's own scaler (see zoompan's `s=` below)
  4. encodes to H.264 MP4

ponytail: zoompan does one continuous zoom-in across the whole clip, not the per-segment
pan/hold/motion-blur choreography implementation_plan.md's Stage 5 describes — a
placeholder "cinematic" pass, not the full vision. Upgrade to per-transition camera
moves if a flat zoom isn't enough once you see it.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

from loguru import logger
from PIL import Image


class FFmpegError(RuntimeError):
    pass


class FFmpegNotFoundError(FFmpegError):
    pass


def assemble_video(
    frames: list[Image.Image],
    output_path: Path,
    *,
    width: int,
    height: int,
    fps: int,
    zoom: bool = True,
    ffmpeg_binary: str = "ffmpeg",
) -> Path:
    if not frames:
        raise ValueError("No frames to assemble.")
    if shutil.which(ffmpeg_binary) is None:
        raise FFmpegNotFoundError(
            f"{ffmpeg_binary!r} not found on PATH. Install ffmpeg (apt-get install ffmpeg "
            "on the deploy target, or point ffmpeg_binary at a real binary for local testing) "
            "— this is not something morph_engine can work around."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="morph_frames_") as tmp:
        tmp_dir = Path(tmp)
        for i, frame in enumerate(frames):
            frame.save(tmp_dir / f"frame_{i:05d}.png")

        if zoom:
            # Slow, continuous zoom-in across the whole clip — see module docstring.
            vf = (
                f"zoompan=z='min(zoom+0.0008,1.08)':d=1:"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"s={width}x{height}:fps={fps}"
            )
        else:
            vf = f"scale={width}:{height}:flags=lanczos"

        cmd = [
            ffmpeg_binary,
            "-y",
            "-framerate", str(fps),
            "-i", str(tmp_dir / "frame_%05d.png"),
            "-vf", vf,
            "-frames:v", str(len(frames)),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(output_path),
        ]  # fmt: skip

        logger.info("Running ffmpeg: {}", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error("ffmpeg failed:\n{}", result.stderr[-4000:])
            raise FFmpegError(f"ffmpeg exited {result.returncode}: {result.stderr[-500:]}")

    return output_path
