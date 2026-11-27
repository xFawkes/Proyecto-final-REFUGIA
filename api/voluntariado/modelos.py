"""Voluntariado: modelo (la tabla "voluntariados" en MySQL), como la clase Categoria del tutorial."""

from datetime import datetime

from ..extensiones import db
from ..utilidades import ZONA_COLOMBIA

# Catálogos (los mismos de los formularios y filtros de las páginas)
MODALIDADES = {
    "presencial": "Presencial",
    "virtual": "Virtual",
    "mixta": "Presencial y virtual",
}
ESTADOS = {
    "activo": "Activo",    # se muestra en voluntariado.html
    "cerrado": "Cerrado",  # ya no recibe voluntarios: solo se ve en el panel
}


def ahora_colombia() -> datetime:
    """Fecha y hora de Colombia sin zona (MySQL DATETIME no guarda la zona)."""
    return datetime.now(ZONA_COLOMBIA).replace(tzinfo=None, microsecond=0)


class Voluntariado(db.Model):  # se crea la clase que genera la tabla
    __tablename__ = "voluntariados"

    id_voluntariado = db.Column(db.Integer, primary_key=True)  # llave primaria
    actividad = db.Column(db.String(150), nullable=False)      # título: "Voluntariado en logística"
    organizacion = db.Column(db.String(150), nullable=False)   # organización responsable
    descripcion = db.Column(db.Text, nullable=False)           # texto de la tarjeta
    requisitos = db.Column(db.Text)                            # uno por línea
    modalidad = db.Column(db.String(20), nullable=False, default="presencial")
    ubicacion = db.Column(db.String(150))                      # ciudad o lugar (opcional si es virtual)
    enlace = db.Column(db.String(500))                         # enlace de inscripción oficial
    imagen = db.Column(db.String(300))                         # ruta (img/…) o enlace https://
    imagen_alt = db.Column(db.String(200))                     # descripción de la imagen (accesibilidad)
    estado = db.Column(db.String(20), nullable=False, default="activo", index=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_colombia)
    actualizado_en = db.Column(db.DateTime, nullable=False, default=ahora_colombia, onupdate=ahora_colombia)
