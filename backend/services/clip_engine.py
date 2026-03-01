import logging
from typing import Optional, Union

import numpy as np
import open_clip
import torch
from PIL import Image

logger = logging.getLogger(__name__)


def _get_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


class CLIPEngine:
    """
    CLIP ViT-L/14 engine for visual embedding, coherence scoring, and mirror comparison.
    Auto-selects MPS on Apple Silicon, CUDA on Linux GPU, CPU otherwise.

    Embedding dimension: 768
    """

    MODEL_NAME = "ViT-L-14"
    PRETRAINED = "openai"
    EMBEDDING_DIM = 768

    def __init__(self):
        self.device = _get_device()
        logger.info(f"CLIPEngine initializing on device: {self.device}")
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            self.MODEL_NAME, pretrained=self.PRETRAINED
        )
        self.model.eval()
        self.model.to(self.device)
        logger.info("CLIPEngine ready.")

    def embed_images(self, images: list[Union[Image.Image, str]]) -> np.ndarray:
        """
        Embed a list of PIL Images or local file paths.
        Returns L2-normalized float32 array of shape (N, 768).
        """
        tensors = []
        for img in images:
            if isinstance(img, str):
                img = Image.open(img).convert("RGB")
            elif not isinstance(img, Image.Image):
                raise ValueError(f"Expected PIL.Image or file path, got {type(img)}")
            tensors.append(self.preprocess(img))

        batch = torch.stack(tensors).to(self.device)
        with torch.no_grad():
            features = self.model.encode_image(batch)
            features = features / features.norm(dim=-1, keepdim=True)

        return features.cpu().numpy().astype(np.float32)

    def collection_coherence(
        self, embeddings: np.ndarray, outlier_threshold: float = 0.65
    ) -> dict:
        """
        Measure visual coherence of an image collection (0-100).
        Identifies outliers as images whose cosine similarity to the centroid
        falls below outlier_threshold.

        Returns:
            score            — 0-100 coherence score
            centroid         — normalized 768-dim mean vector
            outlier_indices  — list of outlier image indices
            per_image_scores — per-image cosine similarity to centroid
        """
        if len(embeddings) == 0:
            return {"score": 0.0, "centroid": [], "outlier_indices": [], "per_image_scores": []}

        centroid = embeddings.mean(axis=0)
        centroid = centroid / np.linalg.norm(centroid)
        similarities = (embeddings @ centroid).tolist()
        outlier_indices = [i for i, s in enumerate(similarities) if s < outlier_threshold]
        mean_sim = float(np.mean(similarities))
        score = round(max(0.0, min(100.0, (mean_sim - 0.5) * 200)), 2)

        return {
            "score": score,
            "centroid": centroid.tolist(),
            "outlier_indices": outlier_indices,
            "per_image_scores": [round(s, 4) for s in similarities],
        }

    def mirror_score(
        self,
        map_centroid: np.ndarray,
        series_embeddings: np.ndarray,
    ) -> dict:
        """
        Módulo 3 — Modo Espejo.
        Compares a visual map centroid against a final image series.
        Returns mirror score 0-100 and per-image similarity scores.
        """
        if len(series_embeddings) == 0:
            return {"mirror_score": 0.0, "per_image_scores": []}

        centroid = map_centroid / np.linalg.norm(map_centroid)
        per_image = (series_embeddings @ centroid).tolist()
        mean_sim = float(np.mean(per_image))
        score = round(max(0.0, min(100.0, (mean_sim - 0.5) * 200)), 2)

        return {
            "mirror_score": score,
            "per_image_scores": [round(s, 4) for s in per_image],
        }

    def embed_from_urls(self, urls: list[str]) -> np.ndarray:
        """Download images from URLs (e.g. Cloudflare R2) and embed them."""
        import httpx
        from io import BytesIO

        images = []
        for url in urls:
            r = httpx.get(url, timeout=30)
            r.raise_for_status()
            images.append(Image.open(BytesIO(r.content)).convert("RGB"))
        return self.embed_images(images)


# Singleton — loaded once per worker process
_clip_engine: Optional[CLIPEngine] = None


def get_clip_engine() -> CLIPEngine:
    global _clip_engine
    if _clip_engine is None:
        _clip_engine = CLIPEngine()
    return _clip_engine
