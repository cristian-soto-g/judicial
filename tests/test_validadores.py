"""Pruebas de los validadores de identificadores chilenos."""
from __future__ import annotations

import pytest

from app.detection.validadores import (
    calcular_dv,
    compactar_patente,
    digitos_telefono,
    es_movil,
    formatear_rut,
    validar_formato_ruc,
    validar_patente,
    validar_rut,
    validar_telefono,
)


class TestRut:
    @pytest.mark.parametrize(
        "cuerpo, dv",
        [
            ("12345678", "5"),
            ("11111111", "1"),
            ("22222222", "2"),
            ("76086428", "5"),
            ("5126663", "3"),
        ],
    )
    def test_digito_verificador(self, cuerpo, dv):
        assert calcular_dv(cuerpo) == dv

    def test_acepta_verificador_k(self):
        # El verificador K aparece cuando el resto del módulo 11 es 10.
        cuerpos_con_k = [c for c in range(10_000_000, 10_000_200) if calcular_dv(c) == "K"]
        assert cuerpos_con_k, "debería existir al menos un RUT con verificador K"
        for cuerpo in cuerpos_con_k:
            assert validar_rut(f"{cuerpo}-K")
            assert validar_rut(f"{cuerpo}-k"), "el verificador debe aceptarse en minúscula"

    @pytest.mark.parametrize(
        "rut",
        ["12.345.678-5", "12345678-5", "12 345 678 - 5", "12.345.678–5"],
    )
    def test_acepta_formatos_habituales(self, rut):
        assert validar_rut(rut)

    @pytest.mark.parametrize("rut", ["12.345.678-9", "12345678-0", "11111111-9"])
    def test_rechaza_verificador_incorrecto(self, rut):
        assert not validar_rut(rut)

    @pytest.mark.parametrize("rut", ["123-4", "1.234-5", "", "abc-1", "123456789012-3"])
    def test_rechaza_estructuras_invalidas(self, rut):
        assert not validar_rut(rut)

    def test_formateo(self):
        assert formatear_rut("123456785") == "12.345.678-5"
        assert formatear_rut("5126663-3") == "5.126.663-3"


class TestRuc:
    @pytest.mark.parametrize(
        "ruc", ["2300456789-1", "2300456789-K", "23 00456789 - 7", "0012345678-9"]
    )
    def test_acepta_formatos_validos(self, ruc):
        assert validar_formato_ruc(ruc)

    @pytest.mark.parametrize("ruc", ["230045678-1", "23004567890-1", "abc", "1234-2020"])
    def test_rechaza_formatos_invalidos(self, ruc):
        assert not validar_formato_ruc(ruc)


class TestPatente:
    @pytest.mark.parametrize("patente", ["BBBB12", "LZRT·45", "SKDF-90", "CJRT 88"])
    def test_acepta_formato_vigente(self, patente):
        assert validar_patente(patente)

    @pytest.mark.parametrize("patente", ["AB1234", "XY·5678"])
    def test_acepta_formato_anterior(self, patente):
        assert validar_patente(patente)

    @pytest.mark.parametrize("patente", ["AAAA12", "EEEE99", "MMMM11", "QQQQ22"])
    def test_rechaza_letras_no_usadas_en_placas(self, patente):
        # Las placas chilenas emitidas desde 2007 excluyen las vocales y las
        # letras M, N y Q para evitar confusiones de lectura.
        assert not validar_patente(patente)

    def test_con_etiqueta_admite_mas_formatos(self):
        assert not validar_patente("XY99")
        assert validar_patente("XY99", con_etiqueta=True)

    def test_compactado(self):
        assert compactar_patente("lz rt · 45") == "LZRT·45".replace("·", "")


class TestTelefono:
    @pytest.mark.parametrize(
        "telefono",
        ["+56 9 8765 4321", "+56987654321", "9 8765 4321", "22 234 5678", "987654321"],
    )
    def test_acepta_numeracion_chilena(self, telefono):
        assert validar_telefono(telefono)

    @pytest.mark.parametrize("telefono", ["123", "12345678", "1234567890123", "111111111"])
    def test_rechaza_numeracion_invalida(self, telefono):
        assert not validar_telefono(telefono)

    def test_descarta_prefijo_pais(self):
        assert digitos_telefono("+56 9 8765 4321") == "987654321"
        assert digitos_telefono("9 8765 4321") == "987654321"

    def test_distingue_movil(self):
        assert es_movil("+56 9 8765 4321")
        assert not es_movil("22 234 5678")
