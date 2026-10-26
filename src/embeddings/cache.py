"""Content-addressed embedding cache to avoid redundant model calls."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Callable
from src.utils.constants import PROCESSED_DATA_ROOT
DEFAULT_CACHE_DIR = PROCESSED_DATA_ROOT / "embedding_cache"
def _cache_key(text: str, model_name: str) -> str:
    digest = hashlib.sha256(("%s|%s" % (model_name, text)).encode("utf-8")).hexdigest()
    return digest
def _cache_path(cache_dir: Path, key: str) -> Path:
    return cache_dir / ("%s.json" % key)
def get_or_embed(text: str, model_name: str, embed_fn: Callable[[str], list[float]], *, cache_dir: Path | s
tr = DEFAULT_CACHE_DIR) -> list[float]:
    """Return a cached embedding for ‘text‘ or compute and persist one."""
    directory = Path(cache_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = _cache_path(directory, _cache_key(text, model_name))
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    vector = embed_fn(text)
    path.write_text(json.dumps(vector), encoding="utf-8")
    return vector
def embed_many_with_cache(texts: list[str], model_name: str, embed_fn: Callable[[list[str]], list[list[floa
t]]], *, cache_dir: Path | str = DEFAULT_CACHE_DIR) -> list[list[float]]:
    """Batch embed only the texts missing from the cache, preserving input order."""
    directory = Path(cache_dir)
    directory.mkdir(parents=True, exist_ok=True)
    keys = [_cache_key(text, model_name) for text in texts]
    paths = [_cache_path(directory, key) for key in keys]
    results: list[list[float] | None] = [None] * len(texts)
    missing_indices = [index for index, path in enumerate(paths) if not path.is_file()]
    for index, path in enumerate(paths):
        if path.is_file():
            results[index] = json.loads(path.read_text(encoding="utf-8"))
    if missing_indices:
        computed = embed_fn([texts[index] for index in missing_indices])
        if len(computed) != len(missing_indices):
            raise ValueError("embed_fn must return one vector per requested text")
        for index, vector in zip(missing_indices, computed):
            results[index] = vector
            paths[index].write_text(json.dumps(vector), encoding="utf-8")
    return [vector for vector in results if vector is not None]
