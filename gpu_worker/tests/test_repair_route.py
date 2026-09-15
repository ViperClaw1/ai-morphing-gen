"""Mocked contract tests for the /repair route.

Per .claude/rules/testing.md, GPU worker calls must be mocked in unit tests
— never load the real SD1.5 pipeline here. These tests stub out CUDA checks
and model loading so the app can boot and be exercised on a machine with no
GPU at all, then mock run_repair()/run_with_timeout() per test to drive every
response branch in app/api/routes/inference.py. Real-model behavior (actual
image quality, real VRAM/OOM limits, true cold-start latency) still needs a
CUDA host — see README.md's "Local launch" section for that.
"""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import app.main as main_module
from app.core import model_loader as model_loader_module
from app.core.model_loader import ModelLoadError
from app.services.face_embedding import FaceNotDetectedError
from app.services.repair_pipeline import CudaOutOfMemoryError, RepairResult
from app.services.timeout_handler import InferenceTimeoutError


def _png_bytes(width: int = 64, height: int = 64) -> bytes:
    img = Image.new("RGB", (width, height), color=(200, 150, 100))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _fake_load(self, settings=None) -> None:
    self._pipeline = "mock-pipeline"
    self._load_duration_ms = 0


@pytest.fixture(autouse=True)
def _isolated_model_loader_singleton():
    model_loader_module.ModelLoader._instance = None
    yield
    model_loader_module.ModelLoader._instance = None


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main_module, "assert_cuda_available", lambda: None)
    monkeypatch.setattr(main_module, "get_device_name", lambda: "mock-gpu")
    monkeypatch.setattr(model_loader_module.ModelLoader, "load", _fake_load)

    with TestClient(main_module.create_app()) as test_client:
        yield test_client


def test_health_live(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"success": True}


def test_repair_success_returns_mocked_image(client, monkeypatch):
    import app.api.routes.inference as inference_module

    canned = RepairResult(
        image=Image.new("RGB", (64, 64)),
        seed=42,
        duration_ms=123,
        output_width=64,
        output_height=64,
    )

    async def _fake_run_repair(image, params, request_id):
        return canned

    async def _passthrough(coro_factory, timeout_seconds=None):
        return await coro_factory()

    monkeypatch.setattr(inference_module, "run_repair", _fake_run_repair)
    monkeypatch.setattr(inference_module, "run_with_timeout", _passthrough)

    response = client.post(
        "/repair",
        files={"image": ("frame.png", _png_bytes(), "image/png")},
        data={"prompt": "high quality portrait", "seed": "42"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["seed"] == 42
    assert body["data"]["duration_ms"] == 123
    assert body["data"]["mime_type"] == "image/png"
    assert len(body["data"]["image_base64"]) > 0


def test_repair_rejects_unsupported_mime_type(client):
    response = client.post(
        "/repair",
        files={"image": ("frame.txt", b"not an image", "text/plain")},
        data={"prompt": "repair this", "seed": "1"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_IMAGE"


def test_repair_rejects_oversized_resolution(client):
    response = client.post(
        "/repair",
        files={"image": ("frame.png", _png_bytes(1200, 1200), "image/png")},
        data={"prompt": "repair this", "seed": "1"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNSUPPORTED_RESOLUTION"


def test_repair_rejects_invalid_params(client):
    response = client.post(
        "/repair",
        files={"image": ("frame.png", _png_bytes(), "image/png")},
        data={"prompt": "repair this", "seed": "-1"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_repair_timeout_returns_504(client, monkeypatch):
    import app.api.routes.inference as inference_module

    async def _raise_timeout(coro_factory, timeout_seconds=None):
        raise InferenceTimeoutError("Inference exceeded timeout of 120 seconds.")

    monkeypatch.setattr(inference_module, "run_with_timeout", _raise_timeout)

    response = client.post(
        "/repair",
        files={"image": ("frame.png", _png_bytes(), "image/png")},
        data={"prompt": "repair this", "seed": "1"},
    )

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "INFERENCE_TIMEOUT"


def test_repair_no_face_returns_422(client, monkeypatch):
    import app.api.routes.inference as inference_module

    async def _raise_no_face(coro_factory, timeout_seconds=None):
        raise FaceNotDetectedError("No face detected in uploaded image.")

    monkeypatch.setattr(inference_module, "run_with_timeout", _raise_no_face)

    response = client.post(
        "/repair",
        files={"image": ("frame.png", _png_bytes(), "image/png")},
        data={"prompt": "repair this", "seed": "1"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "NO_FACE_DETECTED"


def test_repair_cuda_oom_returns_503(client, monkeypatch):
    import app.api.routes.inference as inference_module

    async def _raise_oom(coro_factory, timeout_seconds=None):
        raise CudaOutOfMemoryError("CUDA out of memory during inference.")

    monkeypatch.setattr(inference_module, "run_with_timeout", _raise_oom)

    response = client.post(
        "/repair",
        files={"image": ("frame.png", _png_bytes(), "image/png")},
        data={"prompt": "repair this", "seed": "1"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "CUDA_OOM"


def test_repair_model_not_loaded_returns_503(client, monkeypatch):
    import app.api.routes.inference as inference_module

    async def _raise_not_loaded(coro_factory, timeout_seconds=None):
        raise ModelLoadError("Pipeline not loaded.")

    monkeypatch.setattr(inference_module, "run_with_timeout", _raise_not_loaded)

    response = client.post(
        "/repair",
        files={"image": ("frame.png", _png_bytes(), "image/png")},
        data={"prompt": "repair this", "seed": "1"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "MODEL_LOAD_FAILURE"


def test_repair_unexpected_error_returns_500(client, monkeypatch):
    import app.api.routes.inference as inference_module

    async def _raise_unexpected(coro_factory, timeout_seconds=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(inference_module, "run_with_timeout", _raise_unexpected)

    response = client.post(
        "/repair",
        files={"image": ("frame.png", _png_bytes(), "image/png")},
        data={"prompt": "repair this", "seed": "1"},
    )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INFERENCE_FAILED"
