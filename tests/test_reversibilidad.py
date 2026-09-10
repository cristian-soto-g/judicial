"""Pruebas de la reversibilidad y del cifrado del mapa de correspondencias."""
from __future__ import annotations

import json

import pytest

from app.anonymize.apply import anonymize_text
from app.reversal.crypto import ErrorCifrado, cifrar, descifrar
from app.reversal.mapping import (
    ErrorMapa,
    construir_mapa,
    generar_mapa_cifrado,
    leer_mapa_cifrado,
    revertir_texto,
)

FRASE = "una frase de paso suficientemente larga"

TEXTO = (
    "Compareció don Juan Ignacio Pérez Muñoz, cédula de identidad "
    "N° 12.345.678-5, domiciliado en Pasaje Los Aromos 45, comuna de Maipú, "
    "teléfono +56 9 8765 4321, en la causa RIT 145-2024."
)


class TestCifrado:
    def test_ciclo_completo(self):
        sobre = cifrar(b"contenido secreto", FRASE)
        assert descifrar(sobre, FRASE) == b"contenido secreto"

    def test_el_contenido_no_viaja_en_claro(self):
        sobre = cifrar(b"Juan Perez Munoz", FRASE)
        assert "Juan" not in json.dumps(sobre)

    def test_rechaza_frase_incorrecta(self):
        sobre = cifrar(b"contenido", FRASE)
        with pytest.raises(ErrorCifrado):
            descifrar(sobre, "otra frase de paso distinta")

    def test_rechaza_frase_demasiado_corta(self):
        with pytest.raises(ErrorCifrado):
            cifrar(b"contenido", "corta")

    def test_detecta_la_alteracion_del_archivo(self):
        # AES-GCM autentica el contenido: un archivo manipulado no se descifra,
        # falla de manera explícita en lugar de devolver datos corruptos.
        sobre = cifrar(b"contenido", FRASE)
        alterado = dict(sobre)
        contenido = bytearray(
            __import__("base64").b64decode(alterado["contenido"])
        )
        contenido[0] ^= 0xFF
        alterado["contenido"] = __import__("base64").b64encode(bytes(contenido)).decode()
        with pytest.raises(ErrorCifrado):
            descifrar(alterado, FRASE)

    def test_detecta_la_alteracion_de_los_parametros(self):
        sobre = cifrar(b"contenido", FRASE)
        alterado = {**sobre, "derivacion": "pbkdf2"}
        with pytest.raises(ErrorCifrado):
            descifrar(alterado, FRASE)

    def test_dos_cifrados_del_mismo_contenido_difieren(self):
        # Sal y nonce aleatorios por operación: dos mapas del mismo documento
        # no deben ser comparables entre sí.
        primero = cifrar(b"contenido", FRASE)
        segundo = cifrar(b"contenido", FRASE)
        assert primero["contenido"] != segundo["contenido"]
        assert primero["sal"] != segundo["sal"]


class TestMapa:
    def test_restituye_el_documento_original(self, analizar):
        estado, resultado = analizar(TEXTO)
        anonimizado = anonymize_text(TEXTO, resultado.detections)
        assert "12.345.678-5" not in anonimizado

        archivo = generar_mapa_cifrado(estado, FRASE)
        mapa = leer_mapa_cifrado(archivo, FRASE)
        restituido, reemplazos, faltantes = revertir_texto(anonimizado, mapa)

        assert restituido == TEXTO
        assert reemplazos > 0
        assert faltantes == []

    def test_el_archivo_del_mapa_no_expone_los_datos(self, analizar):
        estado, _ = analizar(TEXTO)
        archivo = generar_mapa_cifrado(estado, FRASE).decode("utf-8")
        assert "12.345.678-5" not in archivo
        assert "Pérez" not in archivo
        # La advertencia sí debe leerse sin descifrar: es lo que alerta a quien
        # encuentre el archivo sobre su carácter sensible.
        assert "volver a identificar" in archivo

    def test_advierte_cuando_el_mapa_no_corresponde_al_documento(self, analizar):
        estado, resultado = analizar(TEXTO)
        archivo = generar_mapa_cifrado(estado, FRASE)
        mapa = leer_mapa_cifrado(archivo, FRASE)
        _, _, faltantes = revertir_texto("Un texto que no guarda relación.", mapa)
        assert faltantes, "debe informarse que las etiquetas no aparecen"

    def test_rechaza_el_etiquetado_no_reversible(self, analizar):
        # Con etiquetas genéricas varias personas comparten "[NOMBRE]", de modo
        # que la reversión sería ambigua. Antes que devolver un mapa engañoso,
        # la aplicación lo rechaza y explica cómo obtener uno válido.
        estado, _ = analizar(
            "Declararon don Juan Pérez Muñoz y doña Ana Painemal Soto.",
            label_mode="gen",
        )
        with pytest.raises(ErrorMapa) as error:
            construir_mapa(estado)
        assert "Categorizado" in str(error.value)

    def test_rechaza_sesion_sin_detecciones(self, analizar):
        estado, _ = analizar("Texto sin datos personales de ninguna especie.")
        with pytest.raises(ErrorMapa):
            construir_mapa(estado)

    def test_no_confunde_etiquetas_de_numeracion_contigua(self):
        # "[PERSONA_1]" es un prefijo de "[PERSONA_10]": el reemplazo debe
        # ordenarse de mayor a menor longitud o quedaría un "0" suelto.
        mapa = {
            "entradas": [
                {"etiqueta": "[PERSONA_1]", "original": "Ana Soto"},
                {"etiqueta": "[PERSONA_10]", "original": "Luis Pérez"},
            ]
        }
        restituido, _, _ = revertir_texto("[PERSONA_10] y [PERSONA_1].", mapa)
        assert restituido == "Luis Pérez y Ana Soto."

    def test_frase_incorrecta_da_un_mensaje_comprensible(self, analizar):
        estado, _ = analizar(TEXTO)
        archivo = generar_mapa_cifrado(estado, FRASE)
        with pytest.raises(ErrorMapa) as error:
            leer_mapa_cifrado(archivo, "una frase de paso equivocada")
        assert "frase de paso" in str(error.value)

    def test_rechaza_un_archivo_que_no_es_un_mapa(self):
        with pytest.raises(ErrorMapa):
            leer_mapa_cifrado(b"esto no es un mapa", FRASE)
