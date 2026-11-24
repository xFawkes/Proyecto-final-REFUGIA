"""PLANTILLA para crear una sección nueva de la API (noticias, donaciones, voluntariado, foro…).

Sigue los mismos pasos del tutorial del profesor: modelo (tabla), esquema
(Marshmallow) y rutas GET, GET por id, POST, PUT y DELETE.

Pasos (ejemplo con "noticias"):
  1. Copia esta carpeta api/_plantilla y llámala api/noticias
  2. En los archivos cambia "Elemento"/"elementos" por tu recurso
     ("Noticia"/"noticias") y ajusta las columnas del modelo.
  3. En api/__init__.py:   from . import mapa, noticias, paginas
                           SECCIONES = [mapa, noticias]
  4. Reinicia el servidor (python main.py): la tabla se crea sola en MySQL.
     Prueba las rutas en Postman: http://127.0.0.1:5000/api/noticias

Esta carpeta NO está registrada en api/__init__.py: solo es el punto de partida.
"""

from ..extensiones import db
from .modelos import Elemento
from .rutas import bp

DATOS_EJEMPLO = [
    ("Primer elemento de ejemplo", "Reemplázame por datos reales de tu sección."),
    ("Segundo elemento de ejemplo", "Otro registro de prueba."),
]


def cargar_datos_ejemplo() -> None:
    """Si la tabla está vacía, inserta los datos de ejemplo (como los INSERT del tutorial)."""
    if db.session.scalar(db.select(db.func.count()).select_from(Elemento)):
        return
    for titulo, descripcion in DATOS_EJEMPLO:
        db.session.add(Elemento(titulo, descripcion))
    db.session.commit()


__all__ = ["bp", "cargar_datos_ejemplo"]
