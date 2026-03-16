import os
import json
import math
from typing import List, Optional

SIMILARITY_THRESHOLD = float(os.getenv("DEDUP_THRESHOLD", "0.85"))

# Try to load a local embedding model; fall back to a simple TF-IDF hash
try:
    from sentence_transformers import SentenceTransformer
    _model = SentenceTransformer("all-MiniLM-L6-v2")
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    _model = None
    EMBEDDINGS_AVAILABLE = False


def embed_text(text: str) -> List[float]:
    """Return a vector representation of the text."""
    if EMBEDDINGS_AVAILABLE and _model is not None:
        vec = _model.encode(text, normalize_embeddings=True)
        return vec.tolist()
    # Fallback: character n-gram frequency vector (dim=128, fast, no GPU)
    return _ngram_hash(text)


def _ngram_hash(text: str, dim: int = 128) -> List[float]:
    """Simple character 3-gram hashing trick as a no-dependency fallback."""
    vec = [0.0] * dim
    text_lower = text.lower()
    for i in range(len(text_lower) - 2):
        gram = text_lower[i:i+3]
        idx = hash(gram) % dim
        vec[idx] += 1.0
    # L2 normalise
    norm = math.sqrt(sum(x*x for x in vec)) or 1.0
    return [x / norm for x in vec]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot   = sum(x*y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x*x for x in a))
    norm_b = math.sqrt(sum(x*x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def is_duplicate(
    new_text: str,
    existing_embeddings: List[List[float]],
    threshold: float = SIMILARITY_THRESHOLD,
) -> bool:
    """Return True if new_text is too similar to any existing question."""
    if not existing_embeddings:
        return False
    new_vec = embed_text(new_text)
    for existing_vec in existing_embeddings:
        if cosine_similarity(new_vec, existing_vec) >= threshold:
            return True
    return False
