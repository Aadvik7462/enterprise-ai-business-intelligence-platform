from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

CACHE_DIRECTORY = Path("cache")
DEFAULT_TTL_SECONDS = 300


def init_cache_directory() -> None:
    CACHE_DIRECTORY.mkdir(parents=True, exist_ok=True)


def _cache_filename(namespace: str, payload: Any) -> str:
    serialized = json.dumps(payload, sort_keys=True, default=str)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return f"{namespace}_{digest}.json"


def get_cached_result(namespace: str, payload: Any, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> Any | None:
    init_cache_directory()
    path = CACHE_DIRECTORY / _cache_filename(namespace, payload)
    if not path.exists():
        return None
    if time.time() - path.stat().st_mtime > ttl_seconds:
        try:
            path.unlink()
        except OSError:
            pass
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def set_cached_result(namespace: str, payload: Any, result: Any) -> None:
    init_cache_directory()
    path = CACHE_DIRECTORY / _cache_filename(namespace, payload)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(result, default=str), encoding="utf-8")
    os.replace(temp, path)


def clear_cache(namespace: str | None = None) -> int:
    init_cache_directory()
    pattern = f"{namespace}_*.json" if namespace else "*.json"
    deleted = 0
    for path in CACHE_DIRECTORY.glob(pattern):
        try:
            path.unlink()
            deleted += 1
        except OSError:
            continue
    return deleted
