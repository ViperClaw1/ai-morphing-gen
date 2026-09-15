"""ffmpeg itself isn't installed on every dev/CI machine (confirmed absent on the
Windows box this was built on) — subprocess.run is monkeypatched so these tests are
portable. assemble_video() was separately verified by hand against a real ffmpeg binary
during development; these tests lock in that contract going forward.
"""

import subprocess
import sys

import pytest
from PIL import Image

from app.services import ffmpeg_service


def _frames(n: int = 3) -> list[Image.Image]:
    return [Image.new("RGB", (8, 8), color=(i * 10, 0, 0)) for i in range(n)]


def test_missing_binary_raises(tmp_path):
    with pytest.raises(ffmpeg_service.FFmpegNotFoundError):
        ffmpeg_service.assemble_video(
            _frames(),
            tmp_path / "out.mp4",
            width=16,
            height=16,
            fps=4,
            ffmpeg_binary="definitely-not-a-real-binary",
        )


def test_nonzero_exit_raises_ffmpeg_error(tmp_path, monkeypatch):
    def fake_run(cmd, capture_output, text):
        return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="encoder exploded")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(ffmpeg_service.FFmpegError, match="encoder exploded"):
        ffmpeg_service.assemble_video(
            _frames(),
            tmp_path / "out.mp4",
            width=16,
            height=16,
            fps=4,
            ffmpeg_binary=sys.executable,
        )


def test_success_writes_output_path_and_frames(tmp_path, monkeypatch):
    captured_cmd = {}

    def fake_run(cmd, capture_output, text):
        captured_cmd["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    out_path = tmp_path / "nested" / "out.mp4"
    result = ffmpeg_service.assemble_video(
        _frames(5), out_path, width=32, height=32, fps=8, ffmpeg_binary=sys.executable
    )

    assert result == out_path
    assert out_path.parent.exists()  # parent dir created even though ffmpeg itself was mocked
    cmd = captured_cmd["cmd"]
    assert cmd[0] == sys.executable
    assert "-framerate" in cmd and "8" in cmd
    assert str(out_path) == cmd[-1]
    assert "-frames:v" in cmd
    assert cmd[cmd.index("-frames:v") + 1] == "5"


def test_no_zoom_uses_plain_scale_filter(monkeypatch, tmp_path):
    captured_cmd = {}

    def fake_run(cmd, capture_output, text):
        captured_cmd["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    ffmpeg_service.assemble_video(
        _frames(),
        tmp_path / "out.mp4",
        width=16,
        height=16,
        fps=4,
        zoom=False,
        ffmpeg_binary=sys.executable,
    )

    vf = captured_cmd["cmd"][captured_cmd["cmd"].index("-vf") + 1]
    assert vf == "scale=16:16:flags=lanczos"


def test_empty_frames_raises(tmp_path):
    with pytest.raises(ValueError):
        ffmpeg_service.assemble_video([], tmp_path / "out.mp4", width=16, height=16, fps=4)
