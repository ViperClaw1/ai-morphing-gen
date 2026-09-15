"""Per .claude/rules/testing.md: GPU worker calls MUST be mocked in unit tests —
never hit a real gpu_worker/RunPod endpoint here. httpx.post is monkeypatched per test.
"""

import base64
import io

import httpx
import pytest
from PIL import Image

from app.core.config import Settings
from app.services import gpu_client


def _settings(**overrides) -> Settings:
    defaults = {"runpod_endpoint_url": "http://gpu-worker.test", "runpod_api_key": "secret"}
    return Settings(**{**defaults, **overrides})


def _fake_response(status_code: int, json_body: dict) -> httpx.Response:
    return httpx.Response(
        status_code, json=json_body, request=httpx.Request("POST", "http://gpu-worker.test/repair")
    )


def _sample_image_b64() -> str:
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), color=(1, 2, 3)).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def test_repair_frame_success(monkeypatch):
    monkeypatch.setattr(gpu_client, "get_settings", lambda: _settings())
    captured = {}

    def fake_post(url, *, files, data, headers, timeout):
        captured["url"] = url
        captured["data"] = data
        captured["headers"] = headers
        return _fake_response(
            200,
            {
                "success": True,
                "data": {"image_base64": _sample_image_b64(), "seed": 42, "duration_ms": 10},
            },
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    result = gpu_client.repair_frame(
        Image.new("RGB", (4, 4)), prompt="p", seed=42, request_id="req-1"
    )

    assert isinstance(result, Image.Image)
    assert captured["url"] == "http://gpu-worker.test/repair"
    assert captured["data"]["seed"] == "42"
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["headers"]["X-Request-Id"] == "req-1"


def test_repair_frame_no_endpoint_configured(monkeypatch):
    monkeypatch.setattr(gpu_client, "get_settings", lambda: _settings(runpod_endpoint_url=""))

    with pytest.raises(gpu_client.GpuRepairError) as exc:
        gpu_client.repair_frame(Image.new("RGB", (4, 4)), prompt="p", seed=1)

    assert exc.value.code == "NO_ENDPOINT_CONFIGURED"


def test_repair_frame_worker_error_response(monkeypatch):
    monkeypatch.setattr(gpu_client, "get_settings", lambda: _settings())
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *a, **k: _fake_response(
            422, {"success": False, "error": {"code": "NO_FACE_DETECTED", "message": "no face"}}
        ),
    )

    with pytest.raises(gpu_client.GpuRepairError) as exc:
        gpu_client.repair_frame(Image.new("RGB", (4, 4)), prompt="p", seed=1)

    assert exc.value.code == "NO_FACE_DETECTED"


def test_repair_frame_unreachable(monkeypatch):
    monkeypatch.setattr(gpu_client, "get_settings", lambda: _settings())

    def raise_request_error(*a, **k):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "post", raise_request_error)

    with pytest.raises(gpu_client.GpuRepairError) as exc:
        gpu_client.repair_frame(Image.new("RGB", (4, 4)), prompt="p", seed=1)

    assert exc.value.code == "GPU_UNREACHABLE"
