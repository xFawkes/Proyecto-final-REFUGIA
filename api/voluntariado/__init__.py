"""Sección Voluntariado: oportunidades para ayudar en emergencias.

Hecha a partir de api/_plantilla. Como toda sección, expone dos cosas que usa api/__init__.py:
  • bp                    → el Blueprint con sus rutas (rutas.py)
  • cargar_datos_ejemplo  → llena la tabla la primera vez (si está vacía)

La consumen:
  • voluntariado.html          con js/voluntariado.js          (solo consulta: GET)
  • admin/voluntariados.html   con js/admin/voluntariados.js   (CRUD completo: GET, POST, PUT y DELETE)
"""

from datetime import timedelta

from ..extensiones import db
from .datos_ejemplo import ORGANIZACION, VOLUNTARIADOS
from .modelos import Voluntariado, ahora_colombia
from .rutas import bp


def cargar_datos_ejemplo() -> None:
    if db.session.scalar(db.select(db.func.count()).select_from(Voluntariado)):
        return  # ya hay datos
    ahora = ahora_colombia()
    for posicion, datos in enumerate(VOLUNTARIADOS):
        # Fechas escalonadas para que se muestren en el mismo orden que tenía la página
        creado = ahora - timedelta(minutes=posicion)
        db.session.add(Voluntariado(organizacion=ORGANIZACION, creado_en=creado, actualizado_en=creado, **datos))
    db.session.commit()


__all__ = ["bp", "cargar_datos_ejemplo"]
