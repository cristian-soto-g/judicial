"""Agrupación de menciones en identidades.

Basado en el módulo de agrupación del Anonimizador Judicial de IALAB —
Facultad de Derecho, UBA (Apache 2.0). Modificado: la construcción de aristas
usa el RUT como identificador de enlace y los nombres de estado de los grupos
están en español ("sugerido", "confirmado").
"""
from __future__ import annotations

from collections import defaultdict

from app.anonymize.placeholders import build_detections_from_mentions
from app.models.schemas import Cluster, Confianza, Detection, Mention
from app.resolution.graph import build_graph, connected_components
from app.resolution.normalize import get_surnames, normalize_mention, tokenize_name
from app.resolution.similarity import compute_edge, link_personas_near_identifier


def _mejor_confianza(razones: list[str], puntajes: list[float]) -> Confianza:
    if "identificador_compartido" in razones or "identica" in razones:
        return "alta"
    if "iniciales" in razones or "similitud_alta" in razones:
        return "alta"
    if max(puntajes, default=0) >= 0.92:
        return "alta"
    if any(
        razon in razones
        for razon in ("nombre_abreviado", "apellido_solo", "apellido_comun", "proximidad")
    ):
        return "media"
    if max(puntajes, default=0) >= 0.85:
        return "media"
    return "baja"


def _grupos_identicos(mentions: list[Mention]) -> dict[tuple[str, str], list[Mention]]:
    grupos: dict[tuple[str, str], list[Mention]] = defaultdict(list)
    for mencion in mentions:
        grupos[(mencion.cat, normalize_mention(mencion.surface))].append(mencion)
    return grupos


def build_edges(
    mentions: list[Mention], texto: str
) -> list[tuple[str, str, float, str]]:
    """Construye las aristas del grafo sin comparar todos los pares posibles."""
    aristas: list[tuple[str, str, float, str]] = []

    grupos = _grupos_identicos(mentions)
    for miembros in grupos.values():
        if len(miembros) < 2:
            continue
        ancla = miembros[0]
        for miembro in miembros[1:]:
            aristas.append((ancla.id, miembro.id, 1.0, "identica"))

    representantes = [miembros[0] for miembros in grupos.values()]
    por_categoria: dict[str, list[Mention]] = defaultdict(list)
    for representante in representantes:
        por_categoria[representante.cat].append(representante)

    vistos: set[tuple[str, str]] = set()

    def intentar(m1: Mention, m2: Mention) -> None:
        par = (m1.id, m2.id) if m1.id < m2.id else (m2.id, m1.id)
        if par in vistos:
            return
        vistos.add(par)
        resultado = compute_edge(m1, m2, texto)
        if resultado:
            peso, _confianza, razon = resultado
            aristas.append((m1.id, m2.id, peso, razon))

    for categoria, representantes_categoria in por_categoria.items():
        if categoria == "PERSONA":
            # Se agrupa por apellido para no comparar todos contra todos.
            cubetas: dict[str, list[Mention]] = defaultdict(list)
            for representante in representantes_categoria:
                tokens = tokenize_name(normalize_mention(representante.surface))
                apellidos = get_surnames(tokens)
                if not apellidos:
                    cubetas[tokens[0] if tokens else "_sin_clave"].append(representante)
                    continue
                for apellido in apellidos:
                    cubetas[apellido].append(representante)
            for cubeta in cubetas.values():
                for indice, m1 in enumerate(cubeta):
                    for m2 in cubeta[indice + 1 :]:
                        intentar(m1, m2)
        else:
            for indice, m1 in enumerate(representantes_categoria):
                for m2 in representantes_categoria[indice + 1 :]:
                    intentar(m1, m2)

    aristas.extend(link_personas_near_identifier(mentions))
    return aristas


def build_clusters(mentions: list[Mention], texto: str) -> list[Cluster]:
    """Devuelve los grupos de menciones que parecen ser el mismo dato."""
    if not mentions:
        return []

    aristas = build_edges(mentions, texto)
    grafo = build_graph(mentions, aristas)
    componentes = connected_components(grafo)

    mapa_menciones = {m.id: m for m in mentions}
    grupos: list[Cluster] = []

    for indice, componente in enumerate(componentes):
        if len(componente) < 2:
            continue

        menciones_componente = [
            mapa_menciones[mid] for mid in componente if mid in mapa_menciones
        ]
        if not menciones_componente:
            continue

        superficies = list({m.surface.strip() for m in menciones_componente})
        if len(superficies) < 2:
            # Todas las menciones son el mismo texto: no hay nada que unificar.
            continue

        razones: list[str] = []
        puntajes: list[float] = []
        for origen, destino, peso, razon in aristas:
            if origen in componente and destino in componente:
                razones.append(razon)
                puntajes.append(peso)

        grupos.append(
            Cluster(
                cluster_id=f"sug_{indice}",
                cat=menciones_componente[0].cat,
                mention_ids=[m.id for m in menciones_componente],
                surfaces=superficies,
                confidence=_mejor_confianza(razones, puntajes),
                status="sugerido",
                reasons=sorted(set(razones)),
            )
        )

    return grupos


def mentions_to_detections(
    mentions: list[Mention], label_mode: str, clusters: list[Cluster]
) -> list[Detection]:
    """Convierte las menciones en detecciones, una por dato distinto."""
    return build_detections_from_mentions(mentions, label_mode)
