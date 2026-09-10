"""Carga de diccionarios de apoyo a la detección.

Basado en el módulo de diccionarios del Anonimizador Judicial de IALAB —
Facultad de Derecho, UBA (Apache 2.0). Modificado: los catálogos argentinos
fueron reemplazados por catálogos chilenos y los sufijos societarios pasaron a
ser los del derecho comercial chileno (S.A., SpA, Ltda., E.I.R.L.).

Nota sobre control de sesgo. Los diccionarios de nombres y apellidos son la
principal fuente de sesgo de este motor: un apellido ausente del catálogo se
detecta peor que uno frecuente, de modo que la anonimización protege menos a
quienes llevan apellidos poco representados. Por eso el catálogo incluye
deliberadamente apellidos mapuche y apellidos habituales entre las comunidades
migrantes residentes en Chile, junto con los apellidos de origen castellano.
Además, la detección nunca depende únicamente del diccionario: los patrones
por contexto (tratamiento, rol procesal, encabezado) operan sin él, de manera
que un apellido no catalogado sigue siendo detectable.
"""
from __future__ import annotations

import json

from app.config import DATA_DIR, RESOURCE_DATA_DIR

_nombres: set[str] | None = None
_apellidos: set[str] | None = None
_formulas: set[str] | None = None


def _cargar_json(nombre: str) -> set[str]:
    """Carga un catálogo desde los recursos del paquete o desde el disco."""
    for base in (RESOURCE_DATA_DIR, DATA_DIR):
        ruta = base / "dictionaries" / nombre
        if ruta.exists():
            with open(ruta, encoding="utf-8") as archivo:
                return set(json.load(archivo))
    return set()


def get_nombres() -> set[str]:
    global _nombres
    if _nombres is None:
        _nombres = _cargar_json("nombres.json")
    return _nombres


def get_apellidos() -> set[str]:
    global _apellidos
    if _apellidos is None:
        _apellidos = _cargar_json("apellidos.json")
    return _apellidos


def get_formulas() -> set[str]:
    """Palabras propias del lenguaje forense chileno que no son nombres."""
    global _formulas
    if _formulas is None:
        _formulas = _cargar_json("formulas_judiciales.json")
    return _formulas


# Palabras vacías y términos institucionales que no deben integrar el nombre de
# una persona.
STOPWORDS_FRASE = {
    "el", "la", "los", "las", "un", "una", "y", "o", "de", "del", "que", "con",
    "por", "para", "en", "su", "sus", "se", "no", "si", "pero", "este", "esta",
    "estos", "estas", "ese", "esa", "al", "lo", "le", "les", "como", "cuando",
    "donde", "cual", "cuales", "quien", "quienes", "cuyo", "cuya", "mediante",
    "conforme", "segun", "sobre", "ante", "bajo", "entre", "hacia", "hasta",
    "desde", "durante", "mientras", "porque", "aunque", "sino", "tambien",
    "tribunal", "juzgado", "corte", "suprema", "apelaciones", "garantia",
    "oral", "penal", "civil", "familia", "laboral", "cobranza", "letras",
    "fiscalia", "fiscal", "defensoria", "defensor", "ministerio", "publico",
    "sala", "articulo", "codigo", "ley", "decreto", "resolucion", "sentencia",
    "auto", "audiencia", "region", "regional", "metropolitana", "comuna",
    "provincia", "nacional", "chile", "chileno", "chilena", "republica",
    "estado", "gobierno", "sr", "sra", "srta", "don", "dona", "dr", "dra",
    "srs", "sres", "usted", "ustedes",
}

# Sufijos societarios chilenos. Se aceptan con y sin puntos porque en los
# escritos aparecen de ambas formas.
SUFIJOS_ORGANIZACION = (
    r"(?:"
    r"S\.?\s?A\.?(?:\s?C\.?)?"                       # S.A., S.A.C.
    r"|S\.?\s?p\.?\s?A\.?"                            # SpA
    r"|S\.?\s?G\.?\s?R\.?"                            # SGR
    r"|Ltda\.?|Limitada"                              # Limitada
    r"|E\.?\s?I\.?\s?R\.?\s?L\.?"                     # E.I.R.L.
    r"|S\.?\s?C\.?\s?M\.?"                            # Sociedad contractual minera
    r"|y\s+C[ií]a\.?(?:\s+Ltda\.?)?"                  # y Cía. Ltda.
    r"|Cooperativa|Corporaci[oó]n|Fundaci[oó]n"
    r"|Asociaci[oó]n\s+Gremial|A\.?\s?G\.?"
    r")"
)

# Palabras que encabezan el nombre de una institución pública u organización.
PREFIJOS_ORGANIZACION = (
    r"(?:"
    r"Juzgado|Tribunal|Corte|Fiscal[ií]a|Defensor[ií]a|Ministerio|"
    r"Municipalidad|Ilustre\s+Municipalidad|Gobernaci[oó]n|Delegaci[oó]n\s+Presidencial|"
    r"Intendencia|Seremi|Servicio|Instituto|Direcci[oó]n\s+(?:General|Regional|Nacional)|"
    r"Superintendencia|Subsecretar[ií]a|Contralor[ií]a|Consejo|Comisi[oó]n|"
    r"Carabineros|Polic[ií]a\s+de\s+Investigaciones|Gendarmer[ií]a|Ej[eé]rcito|Armada|"
    r"Registro\s+Civil|Servicio\s+M[eé]dico\s+Legal|Tesorer[ií]a|Aduana|"
    r"Hospital|Cl[ií]nica|Consultorio|CESFAM|SAPU|Centro\s+de\s+Salud|"
    r"Universidad|Instituto\s+Profesional|Liceo|Colegio|Escuela|Jard[ií]n\s+Infantil|"
    r"Banco|Caja\s+de\s+Compensaci[oó]n|Isapre|Mutual|"
    r"Sociedad|Empresa|Comercial|Constructora|Inmobiliaria|Consultora|"
    r"Distribuidora|Importadora|Exportadora|Transportes|Servicios|Agr[ií]cola|"
    r"Compa[nñ][ií]a|Corporaci[oó]n|Fundaci[oó]n|Cooperativa|Sindicato|"
    r"Junta\s+de\s+Vecinos|Club\s+Deportivo"
    r")"
)

# Siglas de instituciones chilenas que por sí solas identifican a un organismo.
SIGLAS_ORGANIZACION = (
    "SII", "PDI", "SML", "SENDA", "SENAME", "SERNAC", "SERNAMEG", "INE",
    "IPS", "FONASA", "AFP", "CAJ", "DPP", "MP", "OS7", "OS9", "SIP", "BICRIM",
    "LABOCAR", "SEBV", "SENAPRED", "CONADI", "JUNAEB", "JUNJI", "INDAP",
    "SERVIU", "MINVU", "MINEDUC", "MINSAL", "DICREP", "CDE", "TDLC",
)
