from __future__ import annotations

import hashlib
import os

import numpy as np


class Embedder:
    dim = 256

    def encode(self, texts: list[str]) -> np.ndarray:
        raise NotImplementedError


class HashingEmbedder(Embedder):
    """Deterministic n-gram hashing. Used in tests and as CPU fallback."""

    dim = 256

    def encode(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, text in enumerate(texts):
            lowered = text.lower()
            for n in (2, 3):
                for j in range(max(0, len(lowered) - n + 1)):
                    gram = lowered[j : j + n]
                    h = int(hashlib.md5(gram.encode("utf-8")).hexdigest(), 16)
                    sign = 1.0 if h & 1 else -1.0
                    out[i, h % self.dim] += sign
            norm = np.linalg.norm(out[i])
            if norm > 0:
                out[i] /= norm
        return out


class BGEM3Embedder(Embedder):
    dim = 1024

    def __init__(self) -> None:
        from FlagEmbedding import BGEM3FlagModel

        self.model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = []
        for i in range(0, len(texts), 8):
            batch = texts[i : i + 8]
            out = self.model.encode(batch, return_dense=True, return_sparse=False)
            dense = out["dense_vecs"]
            vectors.append(np.asarray(dense, dtype=np.float32))
        stacked = np.vstack(vectors) if vectors else np.zeros((0, self.dim), dtype=np.float32)
        return stacked


def get_embedder() -> Embedder:
    name = os.environ.get("MEMMASTER_EMBEDDER", "hash").lower()
    if name in {"bge-m3", "bge", "bge_m3"}:
        try:
            return BGEM3Embedder()
        except Exception:
            return HashingEmbedder()
    return HashingEmbedder()
