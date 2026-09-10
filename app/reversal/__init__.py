"""Reversibilidad: mapa de correspondencias cifrado y restitución del texto."""
from app.reversal.mapping import (
    ErrorMapa,
    construir_mapa,
    generar_mapa_cifrado,
    revertir_texto,
)

__all__ = [
    "ErrorMapa",
    "construir_mapa",
    "generar_mapa_cifrado",
    "revertir_texto",
]
