"""Per .claude/rules/testing.md: GPU worker calls (repair_fn) are mocked here — never a
real gpu_worker call in unit tests. Landmark detection is also mocked for the
generate_frames() orchestration tests (it needs a downloaded model + real face), but the
warp/blend math itself is exercised directly with synthetic points/images, no mocking
needed since it's pure numpy/opencv.
"""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.services import morph_engine


def test_ease_endpoints_and_midpoint():
    assert morph_engine._ease(0.0) == 0.0
    assert morph_engine._ease(1.0) == 1.0
    assert morph_engine._ease(0.5) == pytest.approx(0.5)


def test_ease_is_slower_at_the_ends_than_linear():
    # smoothstep's defining property: below linear early, above linear late.
    assert morph_engine._ease(0.25) < 0.25
    assert morph_engine._ease(0.75) > 0.75


@pytest.mark.parametrize(
    "num_photos,fps,duration,hold,expected_hold_frames",
    [
        (2, 10, 2.0, 0.5, 5),
        (3, 12, 3.0, 0.4, 5),
    ],
)
def test_frame_plan_hold_frames(num_photos, fps, duration, hold, expected_hold_frames):
    hold_frames, per_transition = morph_engine._frame_plan(num_photos, fps, duration, hold)
    assert hold_frames == expected_hold_frames
    assert len(per_transition) == num_photos - 1
    assert all(n >= 1 for n in per_transition)


def test_frame_plan_never_goes_negative_when_hold_exceeds_budget():
    # Pathological input: holds alone would exceed the total frame budget.
    hold_frames, per_transition = morph_engine._frame_plan(
        num_photos=5, fps=10, duration_seconds=1.0, hold_seconds=1.0
    )
    assert all(n >= 1 for n in per_transition)


def test_warp_and_blend_at_t0_matches_image_a():
    img_a = np.full((20, 20, 3), 50, dtype=np.uint8)
    img_b = np.full((20, 20, 3), 200, dtype=np.uint8)
    pts = morph_engine._boundary_points(
        20, 20
    )  # identical points both sides: pure cross-dissolve, no geometry change

    result = morph_engine._warp_and_blend(img_a, pts, img_b, pts, t=0.0)

    assert result.mean() == pytest.approx(50, abs=2)


def test_warp_and_blend_at_t1_matches_image_b():
    img_a = np.full((20, 20, 3), 50, dtype=np.uint8)
    img_b = np.full((20, 20, 3), 200, dtype=np.uint8)
    pts = morph_engine._boundary_points(20, 20)

    result = morph_engine._warp_and_blend(img_a, pts, img_b, pts, t=1.0)

    assert result.mean() == pytest.approx(200, abs=2)


def test_warp_and_blend_at_midpoint_is_between():
    img_a = np.full((20, 20, 3), 50, dtype=np.uint8)
    img_b = np.full((20, 20, 3), 200, dtype=np.uint8)
    pts = morph_engine._boundary_points(20, 20)

    result = morph_engine._warp_and_blend(img_a, pts, img_b, pts, t=0.5)

    assert 50 < result.mean() < 200


def test_deflicker_smooths_a_single_outlier_frame():
    frames = [np.full((4, 4, 3), 100, dtype=np.uint8) for _ in range(5)]
    frames[2] = np.full((4, 4, 3), 255, dtype=np.uint8)  # one flickery outlier

    result = morph_engine._deflicker(frames)

    assert result[2].mean() < 255  # smoothed toward its neighbors
    assert result[0].mean() == 100  # untouched ends


def test_deflicker_noop_below_three_frames():
    frames = [np.zeros((2, 2, 3), dtype=np.uint8), np.ones((2, 2, 3), dtype=np.uint8)]
    assert morph_engine._deflicker(frames) is frames


def _write_test_photo(path: Path, color: tuple[int, int, int]) -> None:
    Image.new("RGB", (32, 32), color=color).save(path)


def test_generate_frames_calls_repair_once_per_frame(tmp_path, monkeypatch):
    monkeypatch.setattr(
        morph_engine, "detect_landmarks", lambda img: morph_engine._boundary_points(32, 32)
    )

    photo_a = tmp_path / "a.png"
    photo_b = tmp_path / "b.png"
    _write_test_photo(photo_a, (255, 0, 0))
    _write_test_photo(photo_b, (0, 255, 0))

    repair_calls = []

    def fake_repair(image, **kwargs):
        repair_calls.append(kwargs)
        return image

    hold_frames, per_transition = morph_engine._frame_plan(
        2, fps=4, duration_seconds=1.0, hold_seconds=0.25
    )
    expected_total = 2 * hold_frames + sum(per_transition)

    frames = morph_engine.generate_frames(
        [photo_a, photo_b],
        width=32,
        height=32,
        fps=4,
        duration_seconds=1.0,
        hold_seconds=0.25,
        repair_fn=fake_repair,
    )

    assert len(frames) == expected_total
    assert len(repair_calls) == expected_total
    assert all(isinstance(f, Image.Image) for f in frames)


def test_generate_frames_rejects_single_photo():
    with pytest.raises(ValueError):
        morph_engine.generate_frames([Path("only_one.jpg")], width=32, height=32)


def test_generate_frames_rejects_unknown_style():
    with pytest.raises(ValueError, match="style_preset"):
        morph_engine.generate_frames(
            [Path("a.jpg"), Path("b.jpg")], width=32, height=32, style_preset="nonexistent"
        )


def test_detect_landmarks_raises_when_no_face(monkeypatch):
    class _FakeResult:
        face_landmarks: list = []

    class _FakeLandmarker:
        def detect(self, mp_image):
            return _FakeResult()

    monkeypatch.setattr(morph_engine, "_get_landmarker", lambda: _FakeLandmarker())

    blank = np.zeros((32, 32, 3), dtype=np.uint8)
    with pytest.raises(morph_engine.NoFaceDetectedError):
        morph_engine.detect_landmarks(blank)
