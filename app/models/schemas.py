"""Esquemas de datos (Pydantic).

Basado en el módulo de esquemas del Anonimizador Judicial de IALAB — Facultad
de Derecho, UBA (Apache 2.0). Modificado: el catálogo de categorías argentinas
fue reemplazado por las nueve categorías chilenas de este proyecto, y se
agregaron los esquemas de reversibilidad y de sensibilidad de detección.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# --- Catálogo de entidades ------------------------------------------------
# Estas nueve categorías son las únicas que la aplicación detecta. No se
# agregan otras: cada categoría adicional amplía la superficie de falsos
# positivos y diluye la revisión humana.
Categoria = Literal[
    "PERSONA",       # Personas naturales
    "RUT",           # RUT / Cédula de identidad
    "ORGANIZACION",  # Organizaciones: empresas, instituciones y organismos
    "EMAIL",         # Correos electrónicos
    "TELEFONO",      # Teléfonos fijos y móviles
    "DOMICILIO",     # Domicilios y direcciones
    "PATENTE",       # Patentes o placas patente únicas de vehículos
    "OTRO",          # Otros datos sensibles
    "CAUSA",         # Número de causa: RIT, RUC y ROL
]

CATEGORIAS: tuple[str, ...] = (
    "PERSONA",
    "RUT",
    "ORGANIZACION",
    "EMAIL",
    "TELEFONO",
    "DOMICILIO",
    "PATENTE",
    "OTRO",
    "CAUSA",
)

# Nombre visible de cada categoría, en español latinoamericano neutro.
ETIQUETAS_CATEGORIA: dict[str, str] = {
    "PERSONA": "Personas",
    "RUT": "RUT/Cédula de identidad",
    "ORGANIZACION": "Organizaciones",
    "EMAIL": "Emails",
    "TELEFONO": "Teléfonos",
    "DOMICILIO": "Domicilios",
    "PATENTE": "Patentes",
    "OTRO": "Otros sensibles",
    "CAUSA": "Número de causa",
}

ModoEtiqueta = Literal["cat", "gen", "ini"]
EstadoGrupo = Literal["sugerido", "confirmado", "rechazado"]
Confianza = Literal["alta", "media", "baja"]
Sensibilidad = Literal["exhaustiva", "equilibrada", "precisa"]


class Position(BaseModel):
    """Una ocurrencia concreta de un dato dentro del documento."""

    start: int
    end: int
    raw: str = ""


class Mention(BaseModel):
    """Mención individual detectada por alguna capa del motor."""

    id: str
    cat: Categoria
    surface: str
    start: int
    end: int
    norm: str = ""
    source_layer: str = "regex"


class Detection(BaseModel):
    """Dato detectado, agrupando todas sus ocurrencias en el documento."""

    id: int
    cat: Categoria
    original: str
    placeholder: str
    enabled: bool = True
    positions: list[Position] = Field(default_factory=list)
    mention_ids: list[str] = Field(default_factory=list)
    cluster_id: str | None = None
    manual_placeholder: bool = False
    user_added: bool = False
    fuente: str = "regex"


class Cluster(BaseModel):
    """Conjunto de menciones que se consideran la misma identidad."""

    cluster_id: str
    cat: Categoria
    canonical_label: str | None = None
    placeholder: str | None = None
    mention_ids: list[str] = Field(default_factory=list)
    surfaces: list[str] = Field(default_factory=list)
    confidence: Confianza = "media"
    status: EstadoGrupo = "sugerido"
    reasons: list[str] = Field(default_factory=list)


class SessionState(BaseModel):
    """Estado completo de una sesión de trabajo (solo en memoria)."""

    session_id: str
    doc_name: str = "documento"
    doc_text: str = ""
    doc_paragraphs: list[str] = Field(default_factory=list)
    mentions: list[Mention] = Field(default_factory=list)
    detections: list[Detection] = Field(default_factory=list)
    clusters: list[Cluster] = Field(default_factory=list)
    label_mode: ModoEtiqueta = "cat"
    sensibilidad: Sensibilidad = "exhaustiva"
    enabled_categories: list[Categoria] = Field(default_factory=list)
    aviso_extraccion: str = ""


# --- Solicitudes y respuestas --------------------------------------------


class UploadResponse(BaseModel):
    session_id: str
    doc_name: str
    char_count: int
    paragraph_count: int
    aviso: str = ""
    message: str = "Documento cargado correctamente."


class AnalyzeRequest(BaseModel):
    session_id: str
    label_mode: ModoEtiqueta = "cat"
    sensibilidad: Sensibilidad = "exhaustiva"
    enabled_categories: list[Categoria] | None = None


class AnalyzeResponse(BaseModel):
    session_id: str
    detections: list[Detection]
    clusters: list[Cluster]
    stats: dict[str, int]


class CancelRequest(BaseModel):
    session_id: str


class DetectionPatchRequest(BaseModel):
    session_id: str
    cat: Categoria | None = None
    placeholder: str | None = None
    enabled: bool | None = None


class ManualDetectionRequest(BaseModel):
    session_id: str
    cat: Categoria
    start: int = Field(ge=0)
    end: int = Field(ge=1)
    original: str | None = None


class SearchAndAnonymizeRequest(BaseModel):
    """Anonimización desde el buscador de la vista previa.

    La interfaz ya calculó las posiciones sobre el texto del documento; aquí
    solo se validan, se eliminan duplicados y se crea o extiende la detección.
    """

    session_id: str
    cat: Categoria
    original: str
    positions: list[Position]
    placeholder: str | None = None


class AssignClusterRequest(BaseModel):
    session_id: str
    detection_id: int
    cluster_id: str  # identificador existente o "__nuevo__"


class ClusterAddDetectionsRequest(BaseModel):
    detection_ids: list[int]


class ClusterCreateRequest(BaseModel):
    detection_ids: list[int]
    cat: Categoria | None = None


class ClusterUpdateRequest(BaseModel):
    placeholder: str | None = None
    canonical_label: str | None = None


class ClusterSplitRequest(BaseModel):
    mention_ids: list[str]


class ClusterRemoveSurfaceRequest(BaseModel):
    surface: str


class ClusterMergeRequest(BaseModel):
    cluster_ids: list[str]


class ClusterAbsorbRequest(BaseModel):
    source_cluster_id: str


class ConfirmResponse(BaseModel):
    cluster: Cluster
    detections: list[Detection]


class ExportFormatOptions(BaseModel):
    font_name: str = "Times New Roman"
    font_size_pt: int = Field(default=12, ge=8, le=24)
    line_spacing: float = Field(default=1.5, ge=1.0, le=3.0)
    margin_cm: float = Field(default=3.0, ge=1.0, le=5.0)
    margin_top_bottom_cm: float = Field(default=2.5, ge=1.0, le=5.0)
    alignment: Literal["left", "justify", "center", "right"] = "justify"


class ExportRequest(BaseModel):
    session_id: str


class ExportDocumentRequest(BaseModel):
    """Exportación con texto editado y formato opcional."""

    session_id: str
    text: str | None = None
    format: ExportFormatOptions | None = None


class AnonymizedPreviewResponse(BaseModel):
    session_id: str
    doc_name: str
    text: str


# --- Reversibilidad -------------------------------------------------------


class MapaRequest(BaseModel):
    """Solicitud de generación del mapa de reversión cifrado."""

    session_id: str
    passphrase: str = Field(min_length=12)
    nota: str = ""


class RevertirRequest(BaseModel):
    """Solicitud de reversión: texto anonimizado más mapa y frase de paso."""

    texto: str
    mapa: str
    passphrase: str


class RevertirResponse(BaseModel):
    texto: str
    doc_name: str
    reemplazos: int
    sin_coincidencia: list[str] = Field(default_factory=list)
