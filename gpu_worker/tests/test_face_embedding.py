"""Unit tests for FaceEmbedder's face-selection logic.

Bypasses _ensure_loaded (no insightface/onnxruntime installed in the CPU-only
test env, see requirements-dev.txt) by monkeypatching FaceEmbedder._app
directly to a fake analysis object.
"""

from dataclasses import dataclass

import numpy as np
import pytest
from PIL import Image

from app.services.face_embedding import FaceEmbedder, FaceNotDetectedError


@dataclass
class _FakeFace:
    bbox: tuple[float, float, float, float]
    normed_embedding: np.ndarray


class _FakeAnalysis:
    def __init__(self, faces: list[_FakeFace]) -> None:
        self._faces = faces

    def get(self, _bgr_array):
        return self._faces


@pytest.fixture(autouse=True)
def _isolated_singleton():
    FaceEmbedder._instance = None
    yield
    FaceEmbedder._instance = None


def _embedder_with_faces(faces: list[_FakeFace]) -> FaceEmbedder:
    embedder = FaceEmbedder()
    embedder._app = _FakeAnalysis(faces)
    return embedder


def test_no_face_raises():
    embedder = _embedder_with_faces([])
    with pytest.raises(FaceNotDetectedError):
        embedder.get_embedding(Image.new("RGB", (64, 64)))


def test_picks_largest_face():
    small = _FakeFace(bbox=(0, 0, 10, 10), normed_embedding=np.zeros(512, dtype=np.float32))
    large = _FakeFace(bbox=(0, 0, 100, 100), normed_embedding=np.ones(512, dtype=np.float32))
    embedder = _embedder_with_faces([small, large])

    result = embedder.get_embedding(Image.new("RGB", (64, 64)))

    assert result.shape == (1, 512)
    assert bool((result == 1.0).all())
