"""Pruebas de las rutas HTTP y del flujo completo de la aplicación."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.store import store

DOCUMENTO = (
    "4° Tribunal de Juicio Oral en lo Penal de Santiago\n"
    "RIT N° 145-2024 — RUC 2300456789-1\n\n"
    "Compareció don Juan Ignacio Pérez Muñoz, cédula de identidad "
    "N° 12.345.678-5, domiciliado en Pasaje Los Aromos 45, comuna de Maipú, "
    "teléfono +56 9 8765 4321, correo juan.perez@correo.cl. Conducía el "
    "vehículo patente BBBB12.\n"
).encode("utf-8")

FRASE = "una frase de paso larga para la prueba"


@pytest.fixture
def cliente():
    # La dirección base debe ser la real: la aplicación rechaza de manera
    # deliberada las peticiones dirigidas a cualquier otro anfitrión.
    with TestClient(app, base_url="http://127.0.0.1:8799") as c:
        yield c
    store.clear()


@pytest.fixture
def sesion(cliente):
    respuesta = cliente.post(
        "/api/cargar", files={"file": ("causa.txt", DOCUMENTO, "text/plain")}
    )
    assert respuesta.status_code == 200
    session_id = respuesta.json()["session_id"]
    cliente.post(
        "/api/analizar",
        json={"session_id": session_id, "label_mode": "cat", "sensibilidad": "exhaustiva"},
    )
    return session_id


class TestEstado:
    def test_informa_las_nueve_categorias(self, cliente):
        datos = cliente.get("/estado").json()
        assert len(datos["categorias"]) == 9
        assert datos["procesamiento"] == "local"

    def test_reconoce_la_obra_en_que_se_basa(self, cliente):
        datos = cliente.get("/estado").json()
        assert "IALAB" in datos["basado_en"]["autor"]
        assert datos["basado_en"]["licencia"] == "Apache 2.0"


class TestSeguridad:
    def test_rechaza_peticiones_de_otro_anfitrion(self, cliente):
        # La aplicación es de uso personal y local: una petición dirigida a
        # otro anfitrión indica que quedó expuesta fuera del equipo.
        respuesta = cliente.get("/estado", headers={"Host": "ejemplo.cl"})
        assert respuesta.status_code == 403

    def test_no_permite_almacenar_en_cache(self, cliente):
        respuesta = cliente.get("/estado")
        assert "no-store" in respuesta.headers.get("Cache-Control", "")


class TestCarga:
    def test_carga_texto_plano(self, cliente):
        datos = cliente.post(
            "/api/cargar", files={"file": ("causa.txt", DOCUMENTO, "text/plain")}
        ).json()
        assert datos["char_count"] > 0
        assert datos["doc_name"] == "causa"

    def test_rechaza_formato_no_admitido(self, cliente):
        respuesta = cliente.post(
            "/api/cargar", files={"file": ("imagen.png", b"binario", "image/png")}
        )
        assert respuesta.status_code == 422

    def test_rechaza_archivo_vacio(self, cliente):
        respuesta = cliente.post(
            "/api/cargar", files={"file": ("vacio.txt", b"", "text/plain")}
        )
        assert respuesta.status_code == 400


class TestAnalisis:
    def test_devuelve_detecciones_y_estadisticas(self, cliente, sesion):
        datos = cliente.post(
            "/api/analizar", json={"session_id": sesion, "label_mode": "cat"}
        ).json()
        assert datos["stats"]["TOTAL"] > 0
        categorias = {d["cat"] for d in datos["detections"]}
        assert {"PERSONA", "RUT", "CAUSA"} <= categorias

    def test_respeta_las_categorias_desactivadas(self, cliente, sesion):
        datos = cliente.post(
            "/api/analizar",
            json={"session_id": sesion, "enabled_categories": ["RUT", "EMAIL"]},
        ).json()
        assert {d["cat"] for d in datos["detections"]} <= {"RUT", "EMAIL"}

    def test_sesion_inexistente(self, cliente):
        respuesta = cliente.post("/api/analizar", json={"session_id": "inventada"})
        assert respuesta.status_code == 404


class TestRevision:
    def test_desactivar_una_deteccion_la_excluye(self, cliente, sesion):
        detecciones = cliente.get(f"/api/grupos?session_id={sesion}").json()["detecciones"]
        objetivo = next(d for d in detecciones if d["cat"] == "RUT")

        cliente.patch(
            f"/api/detecciones/{objetivo['id']}",
            json={"session_id": sesion, "enabled": False},
        )
        texto = cliente.post(
            "/api/exportar/vista-previa", json={"session_id": sesion}
        ).json()["text"]
        assert objetivo["original"] in texto

    def test_agregar_una_deteccion_a_mano(self, cliente, sesion):
        vista = cliente.get(f"/api/vista-previa?session_id={sesion}").json()
        inicio = vista["texto"].index("Maipú")
        respuesta = cliente.post(
            "/api/detecciones/manual",
            json={
                "session_id": sesion,
                "cat": "DOMICILIO",
                "start": inicio,
                "end": inicio + len("Maipú"),
                "original": "Maipú",
            },
        )
        assert respuesta.status_code == 200
        assert any(d["original"] == "Maipú" for d in respuesta.json()["detecciones"])


class TestExportacion:
    @pytest.mark.parametrize(
        "formato, firma",
        [("docx", b"PK"), ("pdf", b"%PDF"), ("txt", b"[ORGANIZACION_1]")],
    )
    def test_genera_los_formatos(self, cliente, sesion, formato, firma):
        respuesta = cliente.post(
            f"/api/exportar/{formato}", json={"session_id": sesion}
        )
        assert respuesta.status_code == 200
        assert respuesta.content.startswith(firma)

    def test_el_documento_exportado_no_conserva_los_datos(self, cliente, sesion):
        texto = cliente.post(
            "/api/exportar/txt", json={"session_id": sesion}
        ).content.decode("utf-8")
        assert "12.345.678-5" not in texto
        assert "juan.perez@correo.cl" not in texto

    def test_tabla_de_equivalencias(self, cliente, sesion):
        respuesta = cliente.post("/api/exportar/csv", json={"session_id": sesion})
        contenido = respuesta.content.decode("utf-8")
        assert "Dato original" in contenido
        assert "12.345.678-5" in contenido


class TestReversibilidad:
    def test_flujo_completo(self, cliente, sesion):
        anonimizado = cliente.post(
            "/api/exportar/vista-previa", json={"session_id": sesion}
        ).json()["text"]

        mapa = cliente.post(
            "/api/reversion/mapa",
            json={"session_id": sesion, "passphrase": FRASE, "nota": "prueba"},
        )
        assert mapa.status_code == 200
        assert b"12.345.678-5" not in mapa.content

        respuesta = cliente.post(
            "/api/reversion/revertir",
            data={"passphrase": FRASE, "texto": anonimizado},
            files={"mapa": ("causa.anonmap", mapa.content, "application/octet-stream")},
        )
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert "12.345.678-5" in datos["texto"]
        assert datos["sin_coincidencia"] == []

    def test_frase_incorrecta(self, cliente, sesion):
        mapa = cliente.post(
            "/api/reversion/mapa", json={"session_id": sesion, "passphrase": FRASE}
        ).content
        respuesta = cliente.post(
            "/api/reversion/revertir",
            data={"passphrase": "una frase de paso equivocada", "texto": "[RUT_1]"},
            files={"mapa": ("causa.anonmap", mapa, "application/octet-stream")},
        )
        assert respuesta.status_code == 400
        assert "frase de paso" in respuesta.json()["detail"]

    def test_frase_demasiado_corta(self, cliente, sesion):
        respuesta = cliente.post(
            "/api/reversion/mapa", json={"session_id": sesion, "passphrase": "corta"}
        )
        assert respuesta.status_code == 422


class TestSesion:
    def test_cerrar_la_sesion_descarta_el_documento(self, cliente, sesion):
        assert cliente.get(f"/api/sesion/{sesion}").status_code == 200
        cliente.delete(f"/api/sesion/{sesion}")
        assert cliente.get(f"/api/sesion/{sesion}").status_code == 404
