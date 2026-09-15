import torch
from PIL import Image

from app.core.config import Settings, get_settings


class FaceNotDetectedError(RuntimeError):
    pass


class FaceEmbedder:
    """Singleton insightface FaceAnalysis wrapper producing IP-Adapter FaceID embeddings.

    insightface/onnxruntime are imported lazily inside _ensure_loaded, not at module
    import time — mirrors ModelLoader (app/core/model_loader.py) so importing this
    module on the CPU-only test env (requirements-dev.txt has neither package) never
    touches them; only an actual .get_embedding() call would.
    """

    _instance: "FaceEmbedder | None" = None

    def __new__(cls) -> "FaceEmbedder":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._app = None
        return cls._instance

    def _ensure_loaded(self, settings: Settings) -> None:
        if self._app is not None:
            return
        from insightface.app import FaceAnalysis

        providers = (
            ["CUDAExecutionProvider", "CPUExecutionProvider"]
            if settings.device == "cuda"
            else ["CPUExecutionProvider"]
        )
        analysis = FaceAnalysis(
            name=settings.insightface_model_name,
            root=str(settings.insightface_root),
            providers=providers,
        )
        analysis.prepare(ctx_id=0 if settings.device == "cuda" else -1, det_size=(640, 640))
        self._app = analysis

    def get_embedding(self, image: Image.Image) -> torch.Tensor:
        settings = get_settings()
        self._ensure_loaded(settings)

        import numpy as np

        bgr = np.array(image.convert("RGB"))[:, :, ::-1]
        faces = self._app.get(bgr)
        if not faces:
            raise FaceNotDetectedError("No face detected in uploaded image.")

        largest = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        return torch.from_numpy(largest.normed_embedding).unsqueeze(0)


def get_face_embedder() -> FaceEmbedder:
    return FaceEmbedder()
