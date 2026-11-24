"""PLANTILLA para crear una sección nueva de la API (noticias, donaciones, voluntariado, foro…).

Pasos (ejemplo con "noticias"):
  1. Copia esta carpeta api/_plantilla y llámala api/noticias
  2. En los 4 archivos, cambia "elemento"/"elementos" por tu recurso
     ("noticia"/"noticias") y ajusta las columnas de la tabla y del modelo.
  3. En api/main.py:   from . import database, mapa, noticias
                       SECCIONES = [mapa, noticias]
  4. Reinicia uvicorn. Tus endpoints aparecen en http://127.0.0.1:8000/docs

Esta carpeta NO está registrada en main.py: solo sirve como punto de partida.
"""

from .rutas import router
from .tablas import inicializar

__all__ = ["router", "inicializar"]
