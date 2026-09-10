"""Pruebas de la detección sobre texto de documentos chilenos."""
from __future__ import annotations

import pytest


class TestRut:
    def test_detecta_con_y_sin_rotulo(self, detectar):
        texto = (
            "El imputado, RUT 12.345.678-5, y su cónyuge, cédula de identidad "
            "N° 15.678.234-K, comparecieron. También consta el 76.086.428-5."
        )
        assert len(detectar(texto).get("RUT", [])) == 3

    def test_no_confunde_cifras_de_dinero(self, detectar):
        texto = "Se condenó al pago de $12.345.678 a título de indemnización."
        assert "RUT" not in detectar(texto)

    def test_rotulo_no_forma_parte_de_la_sustitucion(self, detectar):
        # El rótulo debe permanecer en el documento: se anonimiza el dato, no
        # la mención de que existe un RUT.
        detectados = detectar("Compareció con RUT 12.345.678-5.")
        assert detectados["RUT"] == ["12.345.678-5"]


class TestNumeroDeCausa:
    @pytest.mark.parametrize(
        "texto, esperado",
        [
            ("Causa RIT N° 145-2024 del tribunal.", "145-2024"),
            ("En autos RIT O-1234-2023 sobre despido.", "O-1234-2023"),
            ("RUC 2300456789-1 del Ministerio Público.", "2300456789-1"),
            ("Rol N° 12.345-2023 de la Corte.", "12.345-2023"),
            ("Rol Ingreso Corte N° 5678-2024.", "5678-2024"),
        ],
    )
    def test_detecta_las_tres_nomenclaturas(self, detectar, texto, esperado):
        assert esperado in detectar(texto).get("CAUSA", [])

    def test_conserva_el_rotulo(self, detectar):
        assert detectar("RIT N° 145-2024")["CAUSA"] == ["145-2024"]


class TestPatente:
    def test_detecta_formato_vigente_sin_rotulo(self, detectar):
        assert "BBBB12" in detectar("El vehículo BBBB12 fue incautado.")["PATENTE"]

    def test_detecta_con_rotulo(self, detectar):
        detectados = detectar("Camioneta placa patente XY-9988 del acusado.")
        assert detectados.get("PATENTE")

    def test_no_confunde_cita_normativa(self, detectar):
        texto = "Conforme al artículo 196 de la Ley 18.290 sobre tránsito."
        assert "PATENTE" not in detectar(texto)


class TestTelefono:
    @pytest.mark.parametrize(
        "texto",
        [
            "Su teléfono es +56 9 8765 4321.",
            "Contacto: 9 8765 4321.",
            "Fono fijo 22 234 5678.",
        ],
    )
    def test_detecta_numeracion_chilena(self, detectar, texto):
        assert detectar(texto).get("TELEFONO")


class TestDomicilio:
    @pytest.mark.parametrize(
        "texto, esperado",
        [
            (
                "Domiciliado en Pasaje Los Aromos 45, comuna de Maipú.",
                "Pasaje Los Aromos 45, comuna de Maipú",
            ),
            (
                "Con domicilio en Avenida Providencia 1234, departamento 56.",
                "Avenida Providencia 1234, departamento 56",
            ),
            ("Reside en Calle Las Rosas 123, Villa El Bosque.", "Calle Las Rosas 123"),
        ],
    )
    def test_detecta_direcciones_con_nombre_de_articulo(self, detectar, texto, esperado):
        # Las vías chilenas que comienzan por artículo —Los Aromos, Las Rosas,
        # El Bosque— son numerosísimas: descartarlas dejaría sin anonimizar una
        # fracción importante de los domicilios reales.
        detectados = detectar(texto).get("DOMICILIO", [])
        assert any(esperado in d for d in detectados), detectados

    def test_no_captura_la_narracion_posterior(self, detectar):
        texto = (
            "Domiciliada en Pasaje Los Aromos 45, comuna de Maipú, declaró que "
            "el imputado la amenazó reiteradamente."
        )
        detectados = detectar(texto).get("DOMICILIO", [])
        assert detectados
        assert all("amenazó" not in d for d in detectados)

    def test_ignora_frases_sin_direccion(self, detectar):
        texto = "El tribunal se encuentra en la calle que fue reparada el año pasado."
        assert not detectar(texto).get("DOMICILIO")


class TestOrganizacion:
    @pytest.mark.parametrize(
        "texto, esperado",
        [
            (
                "Ante el 4° Tribunal de Juicio Oral en lo Penal de Santiago.",
                "4° Tribunal de Juicio Oral en lo Penal de Santiago",
            ),
            ("La empresa Comercial Los Andes SpA aportó.", "Comercial Los Andes SpA"),
            # El punto final de la abreviatura se recorta al normalizar la mención.
            ("Constructora del Sur Ltda. ejecutó la obra.", "Constructora del Sur Ltda"),
        ],
    )
    def test_detecta_organizaciones(self, detectar, texto, esperado):
        detectados = detectar(texto).get("ORGANIZACION", [])
        assert any(esperado in d for d in detectados), detectados

    def test_no_invade_la_oracion_siguiente(self, detectar):
        texto = "Fue detenido por Carabineros de Chile. SEXTO: Que el acusado declaró."
        detectados = detectar(texto).get("ORGANIZACION", [])
        assert detectados
        assert all("SEXTO" not in d for d in detectados)


class TestPersona:
    def test_detecta_nombre_precedido_por_tratamiento(self, detectar):
        detectados = detectar("Compareció don Juan Ignacio Pérez Muñoz.")
        assert "Juan Ignacio Pérez Muñoz" in detectados["PERSONA"]

    def test_detecta_nombre_contiguo_al_rut(self, detectar):
        # Regla clave para el control de sesgo: opera por contexto y no por
        # diccionario, de modo que reconoce apellidos poco frecuentes.
        detectados = detectar("Declaró Kavinski Wolodarsky Trewhela, RUT 12.345.678-5.")
        assert any("Wolodarsky" in p for p in detectados["PERSONA"])

    def test_detecta_apellido_aislado_tras_tratamiento(self, detectar):
        detectados = detectar("La señora Painemal ratificó su declaración.")
        assert "Painemal" in detectados["PERSONA"]

    def test_no_toma_formulas_forenses_por_nombres(self, detectar):
        texto = (
            "VISTOS Y OÍDOS: Que el Tribunal Oral en lo Penal, conforme al "
            "artículo 297 del Código Procesal Penal, tuvo por acreditado."
        )
        assert not detectar(texto).get("PERSONA")

    def test_no_une_dos_personas_por_el_conector(self, detectar):
        detectados = detectar("Declararon Ana Soto Rojas y Luis Pérez Muñoz.")
        assert all(" y " not in p for p in detectados.get("PERSONA", []))


class TestOtrosSensibles:
    @pytest.mark.parametrize(
        "texto",
        [
            "El NUE 1234567 corresponde a la evidencia.",
            "Pasaporte N° AB1234567 del extranjero.",
            "Nacido el 14 de julio de 1988.",
            "Cuenta corriente N° 12345678 del Banco Estado.",
        ],
    )
    def test_detecta_otros_datos(self, detectar, texto):
        assert detectar(texto).get("OTRO")


class TestCatalogoDeCategorias:
    def test_solo_existen_las_nueve_categorias_pedidas(self, detectar):
        from app.models.schemas import CATEGORIAS

        assert set(CATEGORIAS) == {
            "PERSONA",
            "RUT",
            "ORGANIZACION",
            "EMAIL",
            "TELEFONO",
            "DOMICILIO",
            "PATENTE",
            "OTRO",
            "CAUSA",
        }

    def test_el_analisis_no_produce_categorias_ajenas(self, detectar):
        from app.models.schemas import CATEGORIAS

        texto = (
            "Don Juan Pérez Muñoz, RUT 12.345.678-5, domiciliado en Calle Los "
            "Aromos 45, comuna de Maipú, teléfono +56 9 8765 4321, correo "
            "juan@correo.cl, patente BBBB12, causa RIT 145-2024, ante el "
            "Juzgado de Garantía de Santiago. NUE 1234567."
        )
        assert set(detectar(texto)) <= set(CATEGORIAS)


class TestCategoriasDesactivadas:
    """El descarte de categorías no debe arrastrar consigo otras detecciones."""

    TEXTO = "Compareció la empresa Juan Pérez Muñoz Ltda. en representación."

    def test_desactivar_organizaciones_no_oculta_a_la_persona(self, detectar):
        # Regresión de un defecto de privacidad. La organización abarca al
        # nombre y tiene prioridad sobre él; si el descarte de categorías se
        # aplicara después de resolver los solapamientos, la persona
        # desaparecería junto con la organización que la contenía.
        detectados = detectar(self.TEXTO, enabled_categories=["PERSONA"])
        assert detectados.get("PERSONA"), (
            "Con solo «Personas» activa, el nombre debe detectarse aunque una "
            "organización descartada lo abarcara."
        )
        assert "Juan Pérez Muñoz" in detectados["PERSONA"]

    def test_respeta_la_seleccion_de_categorias(self, detectar):
        detectados = detectar(self.TEXTO, enabled_categories=["ORGANIZACION"])
        assert set(detectados) == {"ORGANIZACION"}

    def test_no_atribuye_el_sufijo_societario_a_la_persona(self, detectar):
        detectados = detectar(self.TEXTO, enabled_categories=["PERSONA"])
        assert all("Ltda" not in p for p in detectados["PERSONA"])


class TestSensibilidad:
    """Los tres niveles deben producir resultados efectivamente distintos."""

    TEXTO = (
        "En autos O-1234-2023 se resolvió. Su número es 987654321 según consta. "
        "El testigo Zbigniew declaró. El vehículo XY·1234 fue incautado. "
        "La conexión provino de 192.168.1.45."
    )

    def _cantidad(self, detectar, nivel: str) -> int:
        return sum(len(v) for v in detectar(self.TEXTO, sensibilidad=nivel).values())

    def test_la_exhaustiva_detecta_mas_que_la_equilibrada(self, detectar):
        assert self._cantidad(detectar, "exhaustiva") > self._cantidad(
            detectar, "equilibrada"
        )

    def test_la_precisa_no_detecta_mas_que_la_equilibrada(self, detectar):
        assert self._cantidad(detectar, "precisa") <= self._cantidad(
            detectar, "equilibrada"
        )

    def test_la_exhaustiva_suma_las_reglas_ambiguas(self, detectar):
        detectados = detectar(self.TEXTO, sensibilidad="exhaustiva")
        # Identificador de causa sin rótulo, teléfono de nueve dígitos sin
        # separadores y apellido ausente del catálogo tras un rol procesal.
        assert "O-1234-2023" in detectados.get("CAUSA", [])
        assert "987654321" in detectados.get("TELEFONO", [])
        assert "Zbigniew" in detectados.get("PERSONA", [])

    def test_la_equilibrada_prescinde_de_ellas(self, detectar):
        detectados = detectar(self.TEXTO, sensibilidad="equilibrada")
        assert "O-1234-2023" not in detectados.get("CAUSA", [])
        assert "987654321" not in detectados.get("TELEFONO", [])
        assert "Zbigniew" not in detectados.get("PERSONA", [])

    def test_la_precisa_descarta_lo_que_no_lleva_rotulo(self, detectar):
        precisa = detectar(self.TEXTO, sensibilidad="precisa")
        equilibrada = detectar(self.TEXTO, sensibilidad="equilibrada")
        # Dirección IP y patente de formato antiguo: se reconocen solo por su
        # forma y son las más expuestas a coincidir por azar.
        assert "192.168.1.45" in equilibrada.get("OTRO", [])
        assert "192.168.1.45" not in precisa.get("OTRO", [])
        assert "XY·1234" not in precisa.get("PATENTE", [])

    def test_la_precisa_exige_nombre_y_apellido_conocidos(self, detectar):
        texto = "En la audiencia de juicio oral, Ana Painemal Quilaqueo expuso."
        assert detectar(texto, sensibilidad="precisa").get("PERSONA")

        # Un apellido conocido sin nombre de pila que lo ancle ya no basta.
        texto_debil = "En la audiencia de juicio oral, Painemal Quilaqueo expuso."
        assert not detectar(texto_debil, sensibilidad="precisa").get("PERSONA")
        assert detectar(texto_debil, sensibilidad="exhaustiva").get("PERSONA")
