from typing import Any
import os
import pickle
import hashlib
import threading


class CacheManager:
    """
    Manages disk caching of Python objects using pickle serialization.
    Each object is associated with a unique key, which is hashed to create
    a filename in the specified cache directory.
    """

    def __init__(self, cache_dir: str) -> None:
        self.cache_dir = os.path.abspath(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        self._lock = threading.Lock()

    def _key_to_path(self, key: Any) -> str:
        key_bytes = pickle.dumps(key)
        digest = hashlib.sha256(key_bytes).hexdigest()
        return os.path.join(self.cache_dir, digest)

    def save(self, key: Any, obj: Any) -> None:
        path = self._key_to_path(key)
        tmp_path = path + ".__tmp__"
        with self._lock, open(tmp_path, "wb") as f:
            pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp_path, path)

    def load(self, key: Any) -> Any | None:
        path = self._key_to_path(key)
        try:
            with self._lock, open(path, "rb") as f:
                return pickle.load(f)
        except Exception:
            return None

    def exists(self, key: Any) -> bool:
        path = self._key_to_path(key)
        return os.path.exists(path)

    def invalidate(self, key: Any) -> None:
        path = self._key_to_path(key)
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
