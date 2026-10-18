"""Pruebas de los defectos encontrados en revisión, para que no reaparezcan.

Cada clase documenta un defecto real que llegó a estar en el código. Se agrupan
aquí, y no en el archivo de la funcionalidad correspondiente, porque lo que
cuida cada una no es una característica sino una promesa: que lo que la
aplicación muestra sea lo que hace.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.anonymize.apply import anonymize_text
from app.main import app
from app.models.schemas import ExportDocumentRequest, SessionState
from app.models.store import SessionStore, store
from app.resolution.normalize import aplanar
from app.services.analyze import run_full_analysis
from app.services.detections import _buscar_ocurrencias, update_detection
from app.export.export_utils import resolver_texto_exportacion

DOCUMENTO = (
    "Compareció don Juan Ignacio Pérez Muñoz, cédula de identidad "
    "N° 12.345.678-5, ante el tribunal."
)


def _analizado(texto: str = DOCUMENTO) -> SessionState:
    estado = SessionState(session_id="prueba", doc_text=texto, doc_name="prueba")
    run_full_analysis(estado)
    return estado


class TestLaExportacionRespetaLaRevision:
    """La exportación debe aplicar exactamente lo que la tabla muestra.

    El defecto: al exportar se volvían a aplicar los filtros de calidad, que
    existen para depurar lo que propuso el motor. Una detección que el usuario
    había reclasificado a mano podía dejar de superarlos y desaparecía del
    documento final sin aviso, mientras la tabla seguía mostrándola marcada. El
    usuario daba por anonimizado un dato que quedaba en claro.
    """

    def test_conserva_una_deteccion_reclasificada_a_mano(self):
        estado = _analizado()
        persona = next(d for d in estado.detections if d.cat == "PERSONA")

        # Una reclasificación que el filtro automático rechazaría: el texto no
        # tiene forma de patente.
        update_detection(estado, persona.id, cat="PATENTE")

        exportado = resolver_texto_exportacion(
            estado, ExportDocumentRequest(session_id=estado.session_id)
        )
        assert "Juan Ignacio Pérez Muñoz" not in exportado, (
            "La tabla de revisión mostraba el dato marcado: la exportación no "
            "puede dejarlo en claro."
        )

    def test_la_vista_previa_coincide_con_lo_exportado(self):
        estado = _analizado()
        persona = next(d for d in estado.detections if d.cat == "PERSONA")
        update_detection(estado, persona.id, cat="PATENTE")

        vista = anonymize_text(estado.doc_text, estado.detections)
        exportado = resolver_texto_exportacion(
            estado, ExportDocumentRequest(session_id=estado.session_id)
        )
        assert vista == exportado

    def test_desactivar_sigue_excluyendo(self):
        # La corrección no debe convertir el filtro en una omisión del control
        # del usuario en el otro sentido: lo desmarcado no se reemplaza.
        estado = _analizado()
        persona = next(d for d in estado.detections if d.cat == "PERSONA")
        update_detection(estado, persona.id, enabled=False)

        exportado = resolver_texto_exportacion(
            estado, ExportDocumentRequest(session_id=estado.session_id)
        )
        assert "Juan Ignacio Pérez Muñoz" in exportado


class TestIdentificadoresEstables:
    """Los identificadores de las detecciones no deben cambiar solos.

    El defecto: la vista previa de exportación renumeraba las detecciones de la
    sesión. La tabla de la interfaz conservaba los identificadores anteriores,
    de modo que editar o borrar una fila después de mirar la vista previa podía
    afectar a otra.
    """

    def test_la_vista_previa_no_renumera(self):
        estado = _analizado()
        antes = [(d.id, d.original) for d in estado.detections]

        resolver_texto_exportacion(
            estado, ExportDocumentRequest(session_id=estado.session_id)
        )
        anonymize_text(estado.doc_text, estado.detections)

        despues = [(d.id, d.original) for d in estado.detections]
        assert antes == despues

    def test_los_identificadores_son_unicos(self):
        estado = _analizado()
        identificadores = [d.id for d in estado.detections]
        assert len(identificadores) == len(set(identificadores))


class TestNormalizacionQueConservaLaLongitud:
    """Las posiciones de búsqueda se aplican sobre el documento original.

    El defecto: la normalización descomponía los caracteres y descartaba las
    marcas. Para el español conserva la longitud, pero no para todo: una sílaba
    coreana se descompone en tres letras que no son marcas. El texto
    normalizado quedaba más largo y todas las posiciones siguientes se
    desplazaban, de modo que el reemplazo caía en el lugar equivocado: parte
    del nombre permanecía en el documento y se borraba texto que debía
    conservarse.
    """

    @pytest.mark.parametrize(
        "texto",
        ["Muñoz Peñalolén Ñuñoa", "한글 문서", "İstanbul", "ế", "Å", "ﬁ", "José"],
    )
    def test_conserva_la_longitud(self, texto):
        assert len(aplanar(texto)) == len(texto)

    def test_ignora_acentos_y_mayusculas(self):
        assert aplanar("Muñoz") == aplanar("MUNOZ")

    def test_las_posiciones_apuntan_al_texto_correcto(self):
        texto = (
            "Informe de 한 páginas. Compareció Juan Pérez Muñoz, domiciliado "
            "en Maipú, y también Juan Pérez Muñoz firmó."
        )
        posiciones = _buscar_ocurrencias(texto, "Juan Pérez Muñoz")
        assert len(posiciones) == 2
        for posicion in posiciones:
            assert texto[posicion.start : posicion.end] == "Juan Pérez Muñoz"

    def test_la_anonimizacion_no_corrompe_el_texto(self):
        texto = "El informe 한 menciona a Juan Pérez Muñoz como testigo."
        estado = SessionState(session_id="p", doc_text=texto, doc_name="p")
        run_full_analysis(estado)
        resultado = anonymize_text(texto, estado.detections)
        assert "Juan Pérez Muñoz" not in resultado
        assert resultado.startswith("El informe 한 menciona a ")
        assert resultado.endswith(" como testigo.")


class TestSesionesAcotadas:
    """El texto de un documento no debe quedar en memoria indefinidamente.

    El defecto: las sesiones no se liberaban nunca, de modo que el contenido de
    cada documento abierto durante la jornada permanecía en la memoria del
    proceso hasta cerrar la aplicación. La promesa de que el documento se
    descarta dejaba de ser cierta en la práctica.
    """

    def test_descarta_las_sesiones_mas_antiguas(self):
        almacen = SessionStore(maximo=2)
        primera = almacen.create()
        almacen.create()
        almacen.create()

        assert almacen.count() == 2
        assert almacen.get(primera) is None

    def test_nunca_descarta_la_sesion_en_uso(self):
        almacen = SessionStore(maximo=2)
        en_uso = almacen.create()
        almacen.create()

        # Se sigue trabajando en la primera mientras se abren otras.
        almacen.get(en_uso)
        almacen.create()

        assert almacen.get(en_uso) is not None, (
            "Descartar la sesión que el usuario está usando le haría perder el "
            "trabajo de revisión."
        )

    def test_el_limite_minimo_es_una_sesion(self):
        almacen = SessionStore(maximo=0)
        sesion = almacen.create()
        assert almacen.get(sesion) is not None


class TestFlujoCompletoPorLaApi:
    """Comprobación de extremo a extremo de la corrección principal."""

    @pytest.fixture
    def cliente(self):
        with TestClient(app, base_url="http://127.0.0.1:8799") as c:
            yield c
        store.clear()

    def test_lo_marcado_en_la_tabla_es_lo_que_se_exporta(self, cliente):
        carga = cliente.post(
            "/api/cargar",
            files={"file": ("causa.txt", DOCUMENTO.encode("utf-8"), "text/plain")},
        ).json()
        sesion = carga["session_id"]

        analisis = cliente.post(
            "/api/analizar", json={"session_id": sesion, "label_mode": "cat"}
        ).json()
        persona = next(d for d in analisis["detections"] if d["cat"] == "PERSONA")

        cliente.patch(
            f"/api/detecciones/{persona['id']}",
            json={"session_id": sesion, "cat": "PATENTE"},
        )

        texto = cliente.post(
            "/api/exportar/txt", json={"session_id": sesion}
        ).content.decode("utf-8")
        assert persona["original"] not in texto


class TestDocumentoSinDatosPersonales:
    """Un documento que el motor considera limpio debe poder exportarse.

    El defecto: la exportación exigía que hubiera detecciones, de modo que un
    documento sin datos personales quedaba bloqueado. El mensaje, además, le
    pedía al usuario que analizara un documento que ya había analizado.
    """

    LIMPIO = b"En Santiago, se resuelve dar lugar a lo solicitado. Notifiquese."

    @pytest.fixture
    def cliente(self):
        with TestClient(app, base_url="http://127.0.0.1:8799") as c:
            yield c
        store.clear()

    def _sesion_analizada(self, cliente) -> str:
        sesion = cliente.post(
            "/api/cargar", files={"file": ("acta.txt", self.LIMPIO, "text/plain")}
        ).json()["session_id"]
        resultado = cliente.post("/api/analizar", json={"session_id": sesion}).json()
        assert resultado["stats"]["TOTAL"] == 0
        return sesion

    def test_exige_el_analisis_antes_de_exportar(self, cliente):
        sesion = cliente.post(
            "/api/cargar", files={"file": ("acta.txt", self.LIMPIO, "text/plain")}
        ).json()["session_id"]
        respuesta = cliente.post("/api/exportar/txt", json={"session_id": sesion})
        assert respuesta.status_code == 400
        assert "Analice el documento" in respuesta.json()["detail"]

    @pytest.mark.parametrize("formato", ["txt", "docx", "pdf", "csv"])
    def test_permite_exportar_sin_detecciones(self, cliente, formato):
        sesion = self._sesion_analizada(cliente)
        respuesta = cliente.post(
            f"/api/exportar/{formato}", json={"session_id": sesion}
        )
        assert respuesta.status_code == 200, respuesta.json()

    def test_el_texto_exportado_queda_intacto(self, cliente):
        sesion = self._sesion_analizada(cliente)
        texto = cliente.post(
            "/api/exportar/txt", json={"session_id": sesion}
        ).content.decode("utf-8")
        assert "se resuelve dar lugar a lo solicitado" in texto
