"""Generación de sustituciones y aplicación al texto."""
from app.anonymize.apply import anonymize_text, build_highlights
from app.anonymize.placeholders import make_placeholder

__all__ = ["anonymize_text", "build_highlights", "make_placeholder"]
