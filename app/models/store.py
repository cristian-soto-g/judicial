"""Almacenamiento de sesiones.

Decisión de diseño relevante para la protección de datos: las sesiones viven
únicamente en memoria. El texto del documento no se escribe en disco en ningún
momento, de modo que al cerrar la aplicación no queda rastro del contenido
procesado. Es una diferencia deliberada respecto de la obra original, que
contemplaba persistencia opcional en SQLite.
"""
from __future__ import annotations

import logging
import threading
import uuid
from collections import OrderedDict

from app.config import MAX_SESIONES_EN_MEMORIA
from app.models.schemas import SessionState

logger = logging.getLogger(__name__)


class SessionStore:
    """Registro de sesiones en memoria, seguro frente a accesos concurrentes.

    Conserva un número acotado de sesiones y descarta la usada hace más
    tiempo. Es una medida de protección de datos antes que de rendimiento: el
    texto de un documento no debe seguir en memoria mucho después de que se
    dejó de trabajar en él.
    """

    def __init__(self, maximo: int = MAX_SESIONES_EN_MEMORIA) -> None:
        self._lock = threading.Lock()
        self._memory: OrderedDict[str, SessionState] = OrderedDict()
        self._maximo = max(1, maximo)

    def _descartar_antiguas(self) -> None:
        """Elimina las sesiones más antiguas que excedan el límite.

        Debe invocarse con el cerrojo tomado.
        """
        while len(self._memory) > self._maximo:
            session_id, _ = self._memory.popitem(last=False)
            logger.info(
                "Se descartó de la memoria la sesión %s por no ser la de trabajo "
                "actual. Su documento ya no está en memoria.",
                session_id[:8],
            )

    def create(self) -> str:
        sid = str(uuid.uuid4())
        with self._lock:
            self._memory[sid] = SessionState(session_id=sid)
            self._descartar_antiguas()
        return sid

    def get(self, session_id: str) -> SessionState | None:
        with self._lock:
            estado = self._memory.get(session_id)
            if estado is not None:
                # La sesión que se consulta es la que está en uso: pasa al
                # final para que no sea nunca la candidata a descartarse.
                self._memory.move_to_end(session_id)
            return estado

    def save(self, state: SessionState) -> None:
        with self._lock:
            self._memory[state.session_id] = state
            self._memory.move_to_end(state.session_id)
            self._descartar_antiguas()

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
