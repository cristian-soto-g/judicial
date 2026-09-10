"""Pruebas de control de sesgo en la detección de nombres de personas.

Un anonimizador que reconozca peor unos apellidos que otros protege de manera
desigual, y lo hace precisamente en perjuicio de quienes ya están menos
representados. Estas pruebas no miden calidad general: miden si la protección
es pareja entre orígenes.

El diseño del motor apunta a esa paridad por dos vías. La primera es un
catálogo de apellidos que incluye deliberadamente los de origen mapuche y los
habituales entre las comunidades migrantes residentes en Chile. La segunda, más
importante, es que las reglas de contexto —tratamiento de cortesía, rol
procesal, RUT contiguo— no consultan el catálogo en absoluto, de modo que un
apellido ausente de él se detecta igual.
"""
from __future__ import annotations

import pytest

GRUPOS_DE_APELLIDOS = {
    "castellano": [
        "Juan Pérez Muñoz",
        "María González Rojas",
        "Carlos Silva Contreras",
        "Ana Fuentes Espinoza",
    ],
    "mapuche": [
        "Ana Painemal Quilaqueo",
        "Luis Huenchullán Marileo",
        "Rosa Catrileo Nahuelpán",
        "Pedro Millaqueo Antileo",
    ],
    "haitiano": [
        "Wisly Jean Baptiste",
        "Guerline Pierre Joseph",
        "Frantz Dorvil Casimir",
        "Islande Louis Charles",
    ],
    "andino": [
        "Wilson Quispe Mamani",
        "Hilda Condori Huamán",
        "Percy Apaza Choque",
        "Justina Ticona Vilca",
    ],
    "asiatico": [
        "Wei Chan Lam",
        "Min Kim Park",
        "Jun Wang Liu",
        "Mei Zhang Chen",
    ],
}

# Nombres deliberadamente ausentes de todo catálogo. Sirven para comprobar que
# la detección por contexto funciona sin apoyo del diccionario, que es la
# garantía de fondo frente al sesgo.
NOMBRES_FUERA_DE_CATALOGO = [
    "Kavinski Wolodarsky Trewhela",
    "Ingeborg Steinsapir Bacigalupo",
    "Anselmo Pichiñual Traipe",
    "Oumar Diallo Sankara",
]

PLANTILLAS_CON_CONTEXTO = [
    "Compareció don {nombre} a la audiencia.",
    "{nombre}, RUT 12.345.678-5, prestó declaración.",
    "El imputado {nombre} guardó silencio.",
    "Declaró la testigo {nombre} ante el tribunal.",
]

PLANTILLA_SIN_CONTEXTO = "En la audiencia de juicio oral, {nombre} expuso los hechos."


def _detecta_el_nombre(detectar, texto: str, nombre: str) -> bool:
    """Comprueba que el apellido del nombre quede cubierto por alguna detección."""
    personas = detectar(texto).get("PERSONA", [])
    apellido = nombre.split()[-1]
    return any(apellido in persona for persona in personas)


class TestParidadPorContexto:
    """Las reglas de contexto no deben depender del origen del apellido."""

    @pytest.mark.parametrize("grupo", sorted(GRUPOS_DE_APELLIDOS))
    @pytest.mark.parametrize("plantilla", PLANTILLAS_CON_CONTEXTO)
    def test_todos_los_origenes_se_detectan_igual(self, detectar, grupo, plantilla):
        fallidos = [
            nombre
            for nombre in GRUPOS_DE_APELLIDOS[grupo]
            if not _detecta_el_nombre(detectar, plantilla.format(nombre=nombre), nombre)
        ]
        assert not fallidos, (
            f"El grupo «{grupo}» no fue detectado en la plantilla "
            f"«{plantilla}»: {fallidos}"
        )

    @pytest.mark.parametrize("nombre", NOMBRES_FUERA_DE_CATALOGO)
    @pytest.mark.parametrize("plantilla", PLANTILLAS_CON_CONTEXTO)
    def test_detecta_apellidos_ausentes_del_catalogo(self, detectar, plantilla, nombre):
        texto = plantilla.format(nombre=nombre)
        assert _detecta_el_nombre(detectar, texto, nombre), (
            "Un apellido fuera del catálogo debe detectarse igualmente cuando "
            "el contexto lo identifica como persona."
        )


class TestParidadPorCatalogo:
    """Sin contexto, la detección se apoya en el catálogo: debe ser pareja."""

    def test_ningun_origen_queda_por_debajo_de_los_demas(self, detectar):
        tasas: dict[str, float] = {}
        for grupo, nombres in GRUPOS_DE_APELLIDOS.items():
            detectados = sum(
                1
                for nombre in nombres
                if _detecta_el_nombre(
                    detectar, PLANTILLA_SIN_CONTEXTO.format(nombre=nombre), nombre
                )
            )
            tasas[grupo] = detectados / len(nombres)

        peor, mejor = min(tasas.values()), max(tasas.values())
        assert peor == mejor == 1.0, (
            "La detección sin contexto resultó desigual entre orígenes. "
            f"Tasas por grupo: {tasas}. Corresponde ampliar el catálogo de "
            "apellidos del grupo más débil antes de dar por buena esta versión."
        )


class TestCatalogo:
    def test_el_catalogo_cubre_los_distintos_origenes(self):
        from app.detection.dictionaries import get_apellidos

        apellidos = get_apellidos()
        muestras = {
            "mapuche": ["painemal", "huenchullan", "catrileo", "millaqueo"],
            "haitiano": ["pierre", "baptiste", "dorvil", "casimir"],
            "andino": ["quispe", "mamani", "condori", "huaman"],
            "asiatico": ["chan", "kim", "wang", "zhang"],
            "castellano": ["perez", "gonzalez", "munoz", "silva"],
        }
        ausentes = {
            origen: [a for a in lista if a not in apellidos]
            for origen, lista in muestras.items()
        }
        assert not any(ausentes.values()), f"Faltan apellidos en el catálogo: {ausentes}"
