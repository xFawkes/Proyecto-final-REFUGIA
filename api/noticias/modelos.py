"""Noticias: modelo (la tabla "noticias" en MySQL), como la clase Categoria del tutorial."""

from datetime import datetime

from ..extensiones import db
from ..utilidades import ZONA_COLOMBIA

# Niveles de verificación (los mismos del formulario de admin/noticias.html)
VERIFICACION = {
    "oficial": "Fuente oficial",
    "en_verificacion": "En verificación",
    "sin_verificar": "Sin verificar",
}


def ahora_colombia() -> datetime:
    """Fecha y hora de Colombia sin zona (MySQL DATETIME no guarda la zona)."""
    return datetime.now(ZONA_COLOMBIA).replace(tzinfo=None, microsecond=0)


class Noticia(db.Model):  # se crea la clase que genera la tabla
    __tablename__ = "noticias"

    id_noticia = db.Column(db.Integer, primary_key=True)  # llave primaria
    titulo = db.Column(db.String(200), nullable=False)
    contenido = db.Column(db.Text, nullable=False)        # resumen; los párrafos se separan con una línea en blanco
    fuente = db.Column(db.String(150), nullable=False)    # entidad que publica (UNGRD, IDIGER…)
    enlace = db.Column(db.String(500))                    # enlace a la noticia en el canal oficial
    imagen = db.Column(db.String(300))                    # ruta (img/noticias/…) o enlace https://
    imagen_alt = db.Column(db.String(200))                # descripción de la imagen (accesibilidad)
    verificacion = db.Column(db.String(20), nullable=False, default="oficial")
    destacada = db.Column(db.Boolean, nullable=False, default=False)  # la grande de arriba (solo una)
    publicada = db.Column(db.Boolean, nullable=False, default=True)   # False = borrador (no se ve en la página pública)
    fecha_publicacion = db.Column(db.Date, nullable=False, default=lambda: ahora_colombia().date(), index=True)
    actualizado_en = db.Column(db.DateTime, nullable=False, default=ahora_colombia, onupdate=ahora_colombia)
