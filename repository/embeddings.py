from __future__ import annotations
import os
import math
import hashlib
from typing import List
import httpx

from settings import GROQ_API_KEY, LLM_TIMEOUT_SEC

def _hash_embed(text: str, dim: int) -> List[float]:
    text = (text or "")[:8000]
    vec = []
    seed = hashlib.sha256(text.encode("utf-8")).digest()
    
    counter = 0
    while len(vec) < dim:
        h = hashlib.sha256(seed + counter.to_bytes(4, "little")).digest()
        for i in range(0, len(h), 4):
            if len(vec) >= dim:
                break
            n = int.from_bytes(h[i:i+4], "little", signed=False)
            x = (n / 2**32) * 2.0 - 1.0
            vec.append(float(x))
        counter += 1
    # L2-normalize
    norm = math.sqrt(sum(x*x for x in vec)) or 1.0
    return [x / norm for x in vec]

def embed_one(text: str) -> List[float]:
    text = (text or "")[:8000]

    provider = (os.getenv("EMBED_PROVIDER") or "mock").strip().lower()
    dim = int(os.getenv("EMBED_DIM", "768"))

    if provider == "mock" or provider == "local" or provider == "zero":
        return _hash_embed(text, dim)

    if provider == "groq":
        base = (os.getenv("EMBED_BASE_URL") or "https://api.groq.com/openai/v1").rstrip("/")
        model = os.getenv("EMBED_MODEL", "text-embedding-3-small")
        key = GROQ_API_KEY
        if not key:
            # fail-open ke mock jika kunci tidak ada
            return _hash_embed(text, dim)
        try:
            with httpx.Client(timeout=float(LLM_TIMEOUT_SEC or 30)) as client:
                r = client.post(
                    f"{base}/embeddings",
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                    },
                    json={"model": model, "input": text},
                )
                r.raise_for_status()
                emb = r.json()["data"][0]["embedding"]
                if len(emb) != dim:
                    if len(emb) > dim:
                        emb = emb[:dim]
                    else:
                        emb = list(emb) + _hash_embed(text + "|pad", dim - len(emb))
                # L2-normalize
                norm = math.sqrt(sum(x*x for x in emb)) or 1.0
                return [float(x) / norm for x in emb]
        except Exception:
            return _hash_embed(text, dim)

    # provider lain tidak dikenali → fallback
    return _hash_embed(text, dim)
