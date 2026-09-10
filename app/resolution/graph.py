"""Grafo de menciones y sus componentes conexas.

Basado en el módulo homónimo del Anonimizador Judicial de IALAB — Facultad de
Derecho, UBA (Apache 2.0), con adecuación del lenguaje.
"""
from __future__ import annotations

import networkx as nx

from app.models.schemas import Mention


def build_graph(
    mentions: list[Mention],
    edges: list[tuple[str, str, float, str]],
) -> nx.Graph:
    grafo = nx.Graph()
    for mencion in mentions:
        grafo.add_node(mencion.id, mention=mencion)
    for origen, destino, peso, razon in edges:
        grafo.add_edge(origen, destino, weight=peso, reason=razon)
    return grafo


def connected_components(grafo: nx.Graph) -> list[list[str]]:
    return [list(componente) for componente in nx.connected_components(grafo)]
