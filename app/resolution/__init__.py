"""Resolución de identidades: agrupa las variantes de un mismo dato."""
from app.resolution.cluster import build_clusters, mentions_to_detections

__all__ = ["build_clusters", "mentions_to_detections"]
