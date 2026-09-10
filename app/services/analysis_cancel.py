"""Cancelación cooperativa de análisis prolongados.

Basado en el módulo homónimo del Anonimizador Judicial de IALAB — Facultad de
Derecho, UBA (Apache 2.0), con adecuación del lenguaje.
"""
from __future__ import annotations

import threading

_lock = threading.Lock()
_cancelados: set[str] = set()


class AnalysisCancelledError(Exception):
    """El usuario interrumpió el análisis en curso."""


def request_cancel(session_id: str) -> None:
    with _lock:
        _cancelados.add(session_id)


def clear_cancel(session_id: str) -> None:
    with _lock:
        _cancelados.discard(session_id)


def check_cancel(session_id: str | None) -> None:
    """Interrumpe el análisis si se solicitó su cancelación."""
    if not session_id:
        return
    with _lock:
        if session_id in _cancelados:
            _cancelados.discard(session_id)
            raise AnalysisCancelledError()
