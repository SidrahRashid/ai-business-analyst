"""
CACHE PROVIDER ARCHITECTURE
===========================
Pluggable, enterprise caching layer supporting:
1. InMemoryCacheProvider: High-speed local process memory.
2. FileSharedCacheProvider: Shared multi-worker disk cache with TTL and atomic file locking.
3. RedisCacheProvider: Distributed enterprise cache for multi-server / cloud container deployments.
"""

import os
import json
import time
import hashlib
from typing import Any, Optional, Dict
from pathlib import Path

# Optional Redis import
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class BaseCacheProvider:
    """Abstract Cache Provider Interface."""

    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        raise NotImplementedError

    def delete(self, key: str) -> bool:
        raise NotImplementedError

    def clear(self) -> bool:
        raise NotImplementedError

    def get_stats(self) -> Dict[str, Any]:
        return {"type": self.__class__.__name__}


class InMemoryCacheProvider(BaseCacheProvider):
    """High-speed in-process Python memory cache with timestamp TTL."""

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        item = self._store.get(key)
        if not item:
            return None
        if item["expires_at"] and item["expires_at"] < time.time():
            del self._store[key]
            return None
        return item["value"]

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        expires_at = time.time() + ttl_seconds if ttl_seconds > 0 else None
        self._store[key] = {
            "value": value,
            "expires_at": expires_at,
            "created_at": time.time(),
        }
        return True

    def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    def clear(self) -> bool:
        self._store.clear()
        return True

    def get_stats(self) -> Dict[str, Any]:
        valid_keys = [k for k, v in self._store.items() if not v["expires_at"] or v["expires_at"] >= time.time()]
        return {
            "type": "InMemoryCacheProvider",
            "active_keys": len(valid_keys),
            "total_allocated": len(self._store),
        }


class FileSharedCacheProvider(BaseCacheProvider):
    """
    Disk-backed inter-process cache enabling multiple Uvicorn worker processes
    or container instances sharing a persistent volume to share cached items.
    """

    def __init__(self, cache_dir: Optional[str] = None):
        base_dir = Path(__file__).resolve().parent
        self.cache_dir = Path(cache_dir) if cache_dir else base_dir / "data" / "cache" / "shared"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key_path(self, key: str) -> Path:
        hashed = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{hashed}.cache"

    def get(self, key: str) -> Optional[Any]:
        path = self._key_path(key)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("expires_at") and data["expires_at"] < time.time():
                path.unlink(missing_ok=True)
                return None
            return data.get("value")
        except Exception:
            return None

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        path = self._key_path(key)
        try:
            expires_at = time.time() + ttl_seconds if ttl_seconds > 0 else None
            payload = {
                "key": key,
                "value": value,
                "expires_at": expires_at,
                "created_at": time.time(),
            }
            tmp_path = path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f)
            tmp_path.replace(path)
            return True
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        path = self._key_path(key)
        if path.exists():
            try:
                path.unlink()
                return True
            except Exception:
                return False
        return False

    def clear(self) -> bool:
        try:
            for item in self.cache_dir.glob("*.cache"):
                item.unlink(missing_ok=True)
            return True
        except Exception:
            return False

    def get_stats(self) -> Dict[str, Any]:
        count = len(list(self.cache_dir.glob("*.cache")))
        return {
            "type": "FileSharedCacheProvider",
            "cache_dir": str(self.cache_dir),
            "total_files": count,
        }


class RedisCacheProvider(BaseCacheProvider):
    """
    Distributed Redis Cache Provider for horizontal scaling across Kubernetes
    or cloud containers.
    """

    def __init__(self, redis_url: str):
        if not REDIS_AVAILABLE:
            raise RuntimeError("Redis python client is not installed. Install with: pip install redis")
        self.client = redis.from_url(redis_url, decode_responses=True)
        self.prefix = "ai_analyst:"

    def get(self, key: str) -> Optional[Any]:
        try:
            val = self.client.get(f"{self.prefix}{key}")
            if val is not None:
                return json.loads(val)
            return None
        except Exception:
            return None

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        try:
            serialized = json.dumps(value)
            if ttl_seconds > 0:
                return bool(self.client.setex(f"{self.prefix}{key}", ttl_seconds, serialized))
            else:
                return bool(self.client.set(f"{self.prefix}{key}", serialized))
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        try:
            return bool(self.client.delete(f"{self.prefix}{key}"))
        except Exception:
            return False

    def clear(self) -> bool:
        try:
            keys = self.client.keys(f"{self.prefix}*")
            if keys:
                return bool(self.client.delete(*keys))
            return True
        except Exception:
            return False

    def get_stats(self) -> Dict[str, Any]:
        try:
            info = self.client.info("memory")
            return {
                "type": "RedisCacheProvider",
                "connected": True,
                "used_memory_human": info.get("used_memory_human", "unknown"),
            }
        except Exception as e:
            return {"type": "RedisCacheProvider", "connected": False, "error": str(e)}


def get_cache_provider() -> BaseCacheProvider:
    """
    Factory resolving the appropriate cache provider according to environment configuration:
    - REDIS_URL in env -> RedisCacheProvider
    - CACHE_BACKEND='file' or default multi-worker -> FileSharedCacheProvider
    - CACHE_BACKEND='memory' -> InMemoryCacheProvider
    """
    redis_url = os.getenv("REDIS_URL", "").strip()
    cache_backend = os.getenv("CACHE_BACKEND", "file").strip().lower()

    if redis_url and REDIS_AVAILABLE:
        try:
            provider = RedisCacheProvider(redis_url)
            # Ping test
            provider.client.ping()
            return provider
        except Exception:
            pass  # Fall back to file/memory

    if cache_backend == "memory":
        return InMemoryCacheProvider()

    # Default to FileSharedCacheProvider for multi-process worker safety
    return FileSharedCacheProvider()
