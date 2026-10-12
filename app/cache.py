"""Caché TTL en memoria, thread-safe.

Evita re-raspar hispamula.org entre búsquedas repetidas (p. ej. el RSS
sync de los *arr, que consulta sin `q` y antes obligaba a scrapear las
fichas de toda la portada). Los enlaces ed2k y las fichas cambian poco,
por lo que un TTL amplio es suficiente.
"""

from __future__ import annotations

import threading
import time
from typing import Any


class TTLCache:
    """Caché clave→valor con expiración por tiempo (segundos)."""

    def __init__(self, ttl: float) -> None:
        self._ttl = ttl
        self._lock = threading.Lock()
        self._data: dict[Any, tuple[float, Any]] = {}

    def get(self, key: Any) -> Any | None:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires, value = item
            if time.monotonic() >= expires:
                del self._data[key]
                return None
            return value

    def set(self, key: Any, value: Any) -> None:
        with self._lock:
            self._data[key] = (time.monotonic() + self._ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
