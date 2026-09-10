"""Pruebas de la capa opcional de lenguaje natural.

La capa es opcional por diseño: la aplicación funciona sin ella. Estas pruebas
se omiten cuando spaCy o su modelo no están instalados, de modo que la suite
siga siendo verde en una instalación mínima.

Su valor está en detectar lo que las reglas y el catálogo no alcanzan, que son
justamente los apellidos poco frecuentes. Por eso las pruebas verifican que la
aplicación no vuelva a exigirle a la capa el respaldo del diccionario: hacerlo
la dejaría sin utilidad y reintroduciría el sesgo que se busca evitar.
"""
from __future__ import annotations

import pytest

from app.models.schemas import SessionState
from app.services.analyze import run_full_analysis


def _capa_disponible() -> bool:
    from app.detection.nlp_status import get_nlp_layers_status

    return bool(get_nlp_layers_status()["spacy"].get("disponible"))


pytestmark = pytest.mark.skipif(
    not _capa_disponible(),
    reason="La capa de lenguaje natural no está instalada; es opcional.",
)


def _detectar(texto: str, **opciones) -> dict[str, list[str]]:
    estado = SessionState(session_id="p", doc_text=texto, doc_name="p", **opciones)
    resultado = run_full_analysis(estado)
    por_categoria: dict[str, list[str]] = {}
    for deteccion in resultado.detections:
        por_categoria.setdefault(deteccion.cat, []).append(deteccion.original)
    return por_categoria


class TestAporteDeLaCapa:
    def test_detecta_nombres_ausentes_del_catalogo_y_sin_contexto(self):
        # Ninguna regla puede alcanzar este caso: no hay tratamiento, ni rol
        # procesal, ni RUT contiguo, y los apellidos no figuran en el catálogo.
        texto = "En la audiencia, Kavinski Wolodarsky expuso los antecedentes."
        assert any("Wolodarsky" in p for p in _detectar(texto).get("PERSONA", []))

    def test_no_incluye_el_tratamiento_en_el_nombre(self):
        # El modelo tiende a englobar el tratamiento dentro de la entidad. No
        # es un dato personal y quitarlo conserva la concordancia del texto.
        detectados = _detectar("La señora Painemal ratificó su declaración.")
        assert all("señora" not in p.lower() for p in detectados.get("PERSONA", []))

    def test_no_incluye_el_sufijo_societario_en_el_nombre(self):
        detectados = _detectar("Compareció la empresa Juan Pérez Muñoz Ltda.")
        assert all("Ltda" not in p for p in detectados.get("PERSONA", []))


class TestCoherenciaConLaSensibilidad:
    TEXTO = "En la audiencia, Painemal Quilaqueo expuso los antecedentes."

    def test_el_nivel_preciso_le_exige_el_mismo_respaldo(self):
        # Si el modelo siguiera proponiendo sus hallazgos en el nivel preciso,
        # el ajuste no diría la verdad al usuario.
        assert not _detectar(self.TEXTO, sensibilidad="precisa").get("PERSONA")

    def test_en_los_demas_niveles_la_capa_aporta(self):
        assert _detectar(self.TEXTO, sensibilidad="exhaustiva").get("PERSONA")


class TestPosicionesCorrectas:
    def test_las_menciones_calzan_con_el_texto(self):
        # Un desplazamiento en las posiciones corrompería la sustitución.
        texto = (
            "Declaró Kavinski Wolodarsky ante el tribunal. La señora Ingeborg "
            "Steinsapir ratificó lo obrado."
        )
        estado = SessionState(session_id="p", doc_text=texto, doc_name="p")
        resultado = run_full_analysis(estado)
        for deteccion in resultado.detections:
            for posicion in deteccion.positions:
                assert texto[posicion.start : posicion.end] == deteccion.original
