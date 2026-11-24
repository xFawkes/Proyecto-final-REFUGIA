"""Sección Mapa: albergues, centros de salud, hospitales, centros de acopio y otros puntos.

Toda sección expone dos cosas que usa api/main.py:
  • router       → los endpoints (rutas.py)
  • inicializar  → crea sus tablas y carga datos de ejemplo (tablas.py)
"""

from .rutas import router
from .tablas import inicializar

__all__ = ["router", "inicializar"]
