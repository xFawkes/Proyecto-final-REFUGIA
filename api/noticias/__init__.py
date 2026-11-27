"""Sección Noticias: noticias sobre emergencias y ayuda humanitaria.

Hecha a partir de api/_plantilla. Como toda sección, expone dos cosas que usa api/__init__.py:
  • bp                    → el Blueprint con sus rutas (rutas.py)
  • cargar_datos_ejemplo  → llena la tabla la primera vez (si está vacía)

La consumen:
  • noticias.html        con js/noticias.js        (solo consulta: GET)
  • admin/noticias.html  con js/admin/noticias.js  (CRUD completo: GET, POST, PUT y DELETE)
"""

from ..extensiones import db
from .datos_ejemplo import NOTICIAS
from .modelos import Noticia
from .rutas import bp


def cargar_datos_ejemplo() -> None:
    if db.session.scalar(db.select(db.func.count()).select_from(Noticia)):
        return  # ya hay datos
    for datos in NOTICIAS:
        db.session.add(Noticia(**datos))
    db.session.commit()


__all__ = ["bp", "cargar_datos_ejemplo"]
