"""Pruebas de la aplicación de sustituciones sobre el texto."""
from __future__ import annotations

import re

from app.anonymize.apply import anonymize_text, build_highlights
from app.anonymize.placeholders import make_placeholder

DOCUMENTO = """4° Tribunal de Juicio Oral en lo Penal de Santiago
RIT N° 145-2024 — RUC 2300456789-1

Compareció don Juan Ignacio Pérez Muñoz, cédula de identidad N° 12.345.678-5,
domiciliado en Pasaje Los Aromos 45, comuna de Maipú, teléfono +56 9 8765 4321,
correo juan.perez@correo.cl. Conducía el vehículo patente BBBB12.

Más adelante, don Juan Pérez Muñoz ratificó su declaración, y la señora
Painemal reiteró la suya.
"""


class TestSustitucion:
    def test_no_queda_ningun_dato_identificatorio(self, analizar):
        _, resultado = analizar(DOCUMENTO)
        anonimizado = anonymize_text(DOCUMENTO, resultado.detections)

        for dato in [
            "12.345.678-5",
            "juan.perez@correo.cl",
            "+56 9 8765 4321",
            "BBBB12",
            "145-2024",
            "2300456789-1",
        ]:
            assert dato not in anonimizado, f"quedó sin anonimizar: {dato}"

    def test_todas_las_menciones_de_una_persona_quedan_cubiertas(self, analizar):
        # Es el punto en que un anonimizador falla de manera más silenciosa: la
        # primera mención lleva el nombre completo y las siguientes solo el
        # apellido. Si estas últimas no se reemplazan, el documento parece
        # anonimizado sin estarlo.
        _, resultado = analizar(DOCUMENTO)
        anonimizado = anonymize_text(DOCUMENTO, resultado.detections)
        assert "Pérez" not in anonimizado
        assert "Painemal" not in anonimizado

    def test_una_persona_recibe_siempre_la_misma_etiqueta(self, analizar):
        _, resultado = analizar(DOCUMENTO)
        anonimizado = anonymize_text(DOCUMENTO, resultado.detections)
        # Las dos formas del mismo nombre deben confluir en una sola detección,
        # de manera que el texto no use dos seudónimos para una misma persona.
        personas = [d for d in resultado.detections if d.cat == "PERSONA"]
        de_perez = [d for d in personas if "Pérez" in d.original]
        assert len(de_perez) == 1
        assert len(de_perez[0].positions) >= 2
        assert anonimizado.count(de_perez[0].placeholder) >= 2

    def test_conserva_los_rotulos_del_documento(self, analizar):
        _, resultado = analizar(DOCUMENTO)
        anonimizado = anonymize_text(DOCUMENTO, resultado.detections)
        # El documento debe seguir diciendo que allí había un RIT y un RUT: se
        # anonimiza el dato, no la mención de su existencia.
        assert "RIT" in anonimizado
        assert "cédula de identidad" in anonimizado

    def test_respeta_las_detecciones_desactivadas(self, analizar):
        _, resultado = analizar(DOCUMENTO)
        for deteccion in resultado.detections:
            if deteccion.cat == "ORGANIZACION":
                deteccion.enabled = False
        anonimizado = anonymize_text(DOCUMENTO, resultado.detections)
        assert "Tribunal de Juicio Oral" in anonimizado

    def test_no_corrompe_el_texto_con_reemplazos_solapados(self):
        from app.models.schemas import Detection, Position

        texto = "Juan Pérez Muñoz declaró."
        detecciones = [
            Detection(
                id=0, cat="PERSONA", original="Juan Pérez Muñoz",
                placeholder="[PERSONA_1]",
                positions=[Position(start=0, end=16)],
            ),
            Detection(
                id=1, cat="PERSONA", original="Pérez",
                placeholder="[PERSONA_2]",
                positions=[Position(start=5, end=10)],
            ),
        ]
        resultado = anonymize_text(texto, detecciones)
        assert resultado == "[PERSONA_1] declaró."


class TestEtiquetas:
    def test_modo_categorizado_numera_por_tipo(self):
        assert make_placeholder("PERSONA", "Juan Pérez", 3, "cat") == "[PERSONA_3]"
        assert make_placeholder("RUT", "12.345.678-5", 1, "cat") == "[RUT_1]"

    def test_modo_generico_no_numera(self):
        assert make_placeholder("PERSONA", "Juan Pérez", 3, "gen") == "[NOMBRE]"
        assert make_placeholder("CAUSA", "145-2024", 2, "gen") == "[CAUSA]"

    def test_modo_iniciales(self):
        assert make_placeholder("PERSONA", "Juan Ignacio Pérez Muñoz", 1, "ini") == "J.I.P.M."
        # Las partículas y los sufijos societarios no aportan iniciales.
        assert make_placeholder("ORGANIZACION", "Comercial Los Andes SpA", 1, "ini") == "C.A."

    def test_las_etiquetas_categorizadas_son_unicas(self, analizar):
        _, resultado = analizar(DOCUMENTO)
        etiquetas = [d.placeholder for d in resultado.detections]
        assert len(etiquetas) == len(set(etiquetas)), (
            "Con el modo categorizado cada dato debe tener una etiqueta propia; "
            "de lo contrario la reversión sería ambigua."
        )


class TestResaltados:
    def test_no_se_solapan(self, analizar):
        _, resultado = analizar(DOCUMENTO)
        resaltados = build_highlights(resultado.detections)
        ultimo_fin = -1
        for rango in resaltados:
            assert rango["start"] >= ultimo_fin
            ultimo_fin = rango["end"]

    def test_coinciden_con_el_texto_del_documento(self, analizar):
        _, resultado = analizar(DOCUMENTO)
        for rango in build_highlights(resultado.detections):
            fragmento = DOCUMENTO[rango["start"] : rango["end"]]
            assert fragmento.strip(), "un resaltado no puede apuntar a texto vacío"
