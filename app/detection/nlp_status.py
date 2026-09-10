"""Diagnóstico de la capa opcional de procesamiento de lenguaje natural."""
from __future__ import annotations

from app.config import ENABLE_SPACY


def get_nlp_layers_status() -> dict:
    """Informa si la capa de lenguaje natural está disponible."""
    estado: dict = {
        "spacy": {
            "habilitada": ENABLE_SPACY,
            "disponible": False,
            "descripcion": (
                "Capa opcional. La detección determinística funciona sin ella; "
                "su presencia mejora el reconocimiento de nombres y "
                "organizaciones no previstos por las reglas."
            ),
        }
    }

    if ENABLE_SPACY:
        try:
            from app.detection.spacy_layer import spacy_status

            estado["spacy"].update(spacy_status())
        except Exception as error:  # pragma: no cover - depende del entorno
            estado["spacy"]["error"] = str(error)

    return estado
