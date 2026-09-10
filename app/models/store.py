"""Almacenamiento de sesiones.

Decisión de diseño relevante para la protección de datos: las sesiones viven
únicamente en memoria. El texto del documento no se escribe en disco en ningún
momento, de modo que al cerrar la aplicación no queda rastro del contenido
procesado. Es una diferencia deliberada respecto de la obra original, que
contemplaba persistencia opcional en SQLite.
"""
from __future__ import annotations

import threading
import uuid

from app.models.schemas import SessionState


class SessionStore:
    """Registro de sesiones en memoria, seguro frente a accesos concurrentes."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._memory: dict[str, SessionState] = {}

    def create(self) -> str:
        sid = str(uuid.uuid4())
        with self._lock:
            self._memory[sid] = SessionState(session_id=sid)
        return sid

    def get(self, session_id: str) -> SessionState | None:
        with self._lock:
            return self._memory.get(session_id)

    def save(self, state: SessionState) -> None:
        with self._lock:
            self._memory[state.session_id] = state

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._memory.pop(session_id, None)

    def clear(self) -> int:
        """Elimina todas las sesiones. Devuelve cuántas se descartaron."""
        with self._lock:
            count = len(self._memory)
            self._memory.clear()
        return count

    def count(self) -> int:
        with self._lock:
            return len(self._memory)


store = SessionStore()
