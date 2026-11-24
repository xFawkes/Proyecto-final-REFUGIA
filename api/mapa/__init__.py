"""Sección Mapa: albergues, centros de salud, hospitales, centros de acopio y otros puntos.

Toda sección expone dos cosas que usa api/__init__.py:
  • bp                    → el Blueprint con sus rutas (rutas.py)
  • cargar_datos_ejemplo  → llena sus tablas la primera vez (si están vacías)
"""

from ..extensiones import db
from .datos_ejemplo import PUNTOS
from .modelos import Punto
from .rutas import bp


def cargar_datos_ejemplo() -> None:
    if db.session.scalar(db.select(db.func.count()).select_from(Punto)):
        return  # ya hay datos
    for datos in PUNTOS:
        datos = dict(datos)
        servicios = datos.pop("servicios", [])
        punto = Punto(**datos)
        punto.asignar_servicios(servicios)
        punto.actualizar_texto_busqueda()
        db.session.add(punto)
    db.session.commit()


__all__ = ["bp", "cargar_datos_ejemplo"]
