"""Sección Donaciones: organizaciones que reciben donaciones y pasarela de pagos SIMULADA.

Hecha a partir de api/_plantilla. Como toda sección, expone dos cosas que usa api/__init__.py:
  • bp                    → el Blueprint con sus rutas (rutas.py)
  • cargar_datos_ejemplo  → llena la tabla de organizaciones la primera vez (si está vacía)

La consumen:
  • donaciones.html         con js/donaciones.js         (organizaciones, donar y pagar)
  • admin/donaciones.html   con js/admin/donaciones.js   (CRUD de organizaciones y gestión de donaciones)

La pasarela NO cobra dinero: ver pasarela.py.
"""

from ..extensiones import db
from .datos_ejemplo import ORGANIZACIONES
from .modelos import Organizacion
from .rutas import bp


def cargar_datos_ejemplo() -> None:
    if db.session.scalar(db.select(db.func.count()).select_from(Organizacion)):
        return  # ya hay datos
    for datos in ORGANIZACIONES:
        db.session.add(Organizacion(**datos))
    db.session.commit()


__all__ = ["bp", "cargar_datos_ejemplo"]
