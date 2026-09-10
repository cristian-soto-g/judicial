"""Capa opcional de reconocimiento de entidades con spaCy.

Basada en la capa homóloga del Anonimizador Judicial de IALAB — Facultad de
Derecho, UBA (Apache 2.0). Modificado: las etiquetas se asignan a las nueve
categorías chilenas, los patrones del reconocedor por reglas corresponden a
tratamientos y roles del proceso chileno, y la capa pasó a ser estrictamente
opcional: si spaCy o su modelo no están instalados, la aplicación funciona
igual con la detección determinística.

Advertencia de licencia: el modelo es_core_news_md se distribuye bajo GPL-3.0.
No forma parte de este repositorio y debe instalarse por separado.
"""
from __future__ import annotations

import logging

from app.detection.regex_cl import (
    RawItem,
    recortar_nombre_de_persona,
    tiene_nombre_y_apellido,
)

logger = logging.getLogger(__name__)

_nlp = None
_error_inicial: str | None = None
MODELO_ES = "es_core_news_md"

# El reconocedor por reglas aporta lo que el modelo estadístico suele omitir en
# escritos chilenos: nombres precedidos por tratamiento profesional.
PATRONES_REGLA = [
    {
        "label": "PERSONA",
        "pattern": [
            {
                "ORTH": {
                    "IN": [
                        "Sr.", "Sra.", "Srta.", "Dr.", "Dra.", "Don", "Doña",
                        "Ab.", "Prof.",
                    ]
                }
            },
            {"IS_ALPHA": True, "IS_TITLE": True, "OP": "{1,4}"},
        ],
    },
    {
        "label": "ORGANIZACION",
        "pattern": [
            {"LOWER": {"IN": ["juzgado", "tribunal", "fiscalía", "fiscalia"]}},
            {"IS_ALPHA": True, "OP": "{1,6}"},
        ],
    },
]

MAPA_ETIQUETAS = {
    "PER": "PERSONA",
    "PERSON": "PERSONA",
    "PERSONA": "PERSONA",
    "ORG": "ORGANIZACION",
    "ORGANIZACION": "ORGANIZACION",
    "LOC": "DOMICILIO",
    "GPE": "DOMICILIO",
}


def _obtener_nlp():
    global _nlp, _error_inicial
    if _nlp is not None:
        return _nlp
    if _error_inicial is not None:
        raise RuntimeError(_error_inicial)

    try:
        import spacy

        from app.runtime_paths import spacy_model_dir

        empaquetado = spacy_model_dir()
        nlp = spacy.load(empaquetado if empaquetado else MODELO_ES)
        if "entity_ruler" not in nlp.pipe_names:
            reglas = nlp.add_pipe("entity_ruler", before="ner")
            reglas.add_patterns(PATRONES_REGLA)
        _nlp = nlp
        logger.info("Capa de lenguaje natural cargada: %s", MODELO_ES)
        return _nlp
    except ImportError as error:
        _error_inicial = (
            "spaCy no está instalado. Es opcional: la detección determinística "
            "funciona sin él. Para instalarlo: pip install -r requirements-nlp.txt"
        )
        raise RuntimeError(_error_inicial) from error
    except OSError as error:
        _error_inicial = (
            f"El modelo {MODELO_ES} no está instalado. Para instalarlo: "
            f"python -m spacy download {MODELO_ES}"
        )
        raise RuntimeError(_error_inicial) from error
    except Exception as error:  # pragma: no cover - depende del entorno
        _error_inicial = str(error)
        raise


def spacy_status() -> dict:
    """Devuelve el estado de la capa sin interrumpir la aplicación."""
    if _nlp is not None:
        return {"disponible": True, "modelo": MODELO_ES}
    if _error_inicial:
        return {"disponible": False, "motivo": _error_inicial}
    try:
        _obtener_nlp()
        return {"disponible": True, "modelo": MODELO_ES}
    except Exception as error:
        return {"disponible": False, "motivo": str(error)}


def detect_spacy(texto: str, sensibilidad: str = "exhaustiva") -> list[RawItem]:
    """Devuelve las entidades reconocidas por el modelo de lenguaje."""
    nlp = _obtener_nlp()

    if len(texto) > getattr(nlp, "max_length", 1_000_000):
        nlp.max_length = len(texto) + 100

    documento = nlp(texto[: min(len(texto), 500_000)])
    items: list[RawItem] = []

    from app.detection.filters import is_valid_detection

    # En el nivel de sensibilidad preciso, lo que aporta el modelo se somete a
    # los mismos requisitos que las reglas. De otro modo el ajuste no diría la
    # verdad: la interfaz ofrece menos falsos positivos y el modelo seguiría
    # proponiendo los suyos.
    procedencia = "regla" if sensibilidad == "precisa" else "modelo"

    for entidad in documento.ents:
        categoria = MAPA_ETIQUETAS.get(entidad.label_)
        if not categoria:
            continue

        superficie = entidad.text
        inicio = entidad.start_char

        if categoria == "PERSONA":
            # El modelo suele incluir en la entidad el tratamiento que precede
            # al nombre y el sufijo societario que lo sigue. Ninguno de los dos
            # es un dato personal.
            superficie, desplazamiento = recortar_nombre_de_persona(superficie)
            inicio += desplazamiento
            if len(superficie) < 3:
                continue
            # El nivel preciso exige el mismo respaldo que a las reglas: un
            # nombre de pila y un apellido presentes en el catálogo.
            if procedencia == "regla" and not tiene_nombre_y_apellido(superficie):
                continue

        if not is_valid_detection(
            categoria, superficie, texto, inicio, procedencia=procedencia
        ):
            continue

        items.append(
            RawItem(
                cat=categoria,
                original=superficie,
                start=inicio,
                end=inicio + len(superficie),
                source_layer="spacy",
                score=0.75,
                # La clasificación del modelo cuenta como evidencia propia: sin
                # esto, la resolución de solapamientos relegaría siempre sus
                # menciones frente a las de las reglas.
                etiquetado=True,
            )
        )

    return items
