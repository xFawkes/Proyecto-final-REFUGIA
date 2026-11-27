"""Sección Foro: publicaciones de la comunidad, respuestas, validaciones y denuncias.

Hecha a partir de api/_plantilla. Como toda sección, expone dos cosas que usa api/__init__.py:
  • bp                    → el Blueprint con sus rutas (rutas.py)
  • cargar_datos_ejemplo  → llena las tablas la primera vez (si están vacías)

La consumen:
  • foro.html          con js/foro.js          (leer, publicar, responder, validar y denunciar)
  • admin/foro.html    con js/admin/foro.js    (moderación: aprobar, ocultar y eliminar)
  • admin/inicio.html  con js/admin/panel.js   (publicaciones por revisar y tareas pendientes)
"""

from datetime import timedelta

from ..extensiones import db
from .datos_ejemplo import PUBLICACIONES
from .modelos import Denuncia, Publicacion, Respuesta, ahora_colombia
from .rutas import bp


def cargar_datos_ejemplo() -> None:
    if db.session.scalar(db.select(db.func.count()).select_from(Publicacion)):
        return  # ya hay datos
    ahora = ahora_colombia()
    for posicion, datos in enumerate(PUBLICACIONES):
        datos = dict(datos)
        respuestas = datos.pop("respuestas", [])
        denuncias = datos.pop("denuncias", [])
        creado = ahora - timedelta(hours=posicion * 5 + 1)  # fechas escalonadas, la primera es la más reciente
        publicacion = Publicacion(**datos, creado_en=creado, ultima_actividad=creado, actualizado_en=creado)
        for i, (autor, contenido) in enumerate(respuestas, start=1):
            publicacion.respuestas.append(Respuesta(autor=autor, contenido=contenido,
                                                    creado_en=creado + timedelta(minutes=20 * i)))
        if publicacion.respuestas:
            publicacion.ultima_actividad = publicacion.respuestas[-1].creado_en
        for motivo, detalle in denuncias:
            publicacion.denuncias.append(Denuncia(motivo=motivo, detalle=detalle, creado_en=creado))
        db.session.add(publicacion)
    db.session.commit()


__all__ = ["bp", "cargar_datos_ejemplo"]
