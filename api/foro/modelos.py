"""Foro: modelos (tablas "publicaciones", "respuestas" y "denuncias" en MySQL)."""

from datetime import datetime

from ..extensiones import db
from ..utilidades import ZONA_COLOMBIA

CATEGORIAS = {
    "desaparecidos": "Desaparecidos",
    "necesidades": "Necesidades",
    "ofrecimientos": "Ofrezco ayuda",
    "alertas": "Alertas",
    "general": "General",
}
VERIFICACION = {
    "sin_confirmar": "Sin confirmar",
    "confirmada": "Confirmada",  # un moderador la revisó y la aprobó
}
MOTIVOS_DENUNCIA = {
    "falsa": "Información falsa",
    "ofensiva": "Contenido ofensivo",
    "datos_personales": "Expone datos personales",
    "spam": "Publicidad o spam",
    "otro": "Otro motivo",
}
# Con este número de denuncias sin revisar, la publicación se oculta hasta que un moderador la revise
DENUNCIAS_PARA_OCULTAR = 3


def ahora_colombia() -> datetime:
    """Fecha y hora de Colombia sin zona (MySQL DATETIME no guarda la zona)."""
    return datetime.now(ZONA_COLOMBIA).replace(tzinfo=None, microsecond=0)


class Publicacion(db.Model):
    """Un tema del foro (cada fila de foro.html)."""

    __tablename__ = "publicaciones"

    id_publicacion = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    categoria = db.Column(db.String(20), nullable=False, default="general", index=True)
    ubicacion = db.Column(db.String(150))                    # barrio o municipio (opcional)
    autor = db.Column(db.String(80), nullable=False)
    verificacion = db.Column(db.String(20), nullable=False, default="sin_confirmar", index=True)
    oculta = db.Column(db.Boolean, nullable=False, default=False)  # True = no se ve en foro.html
    validaciones = db.Column(db.Integer, nullable=False, default=0)  # personas que confirman la información
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_colombia)
    ultima_actividad = db.Column(db.DateTime, nullable=False, default=ahora_colombia, index=True)  # crear o responder
    actualizado_en = db.Column(db.DateTime, nullable=False, default=ahora_colombia, onupdate=ahora_colombia)

    respuestas = db.relationship(
        "Respuesta", back_populates="publicacion", cascade="all, delete-orphan", passive_deletes=True,
        order_by="Respuesta.creado_en", lazy="selectin",
    )
    denuncias = db.relationship(
        "Denuncia", back_populates="publicacion", cascade="all, delete-orphan", passive_deletes=True,
        order_by="Denuncia.creado_en", lazy="selectin",
    )

    @property
    def denuncias_pendientes(self) -> int:
        return sum(1 for d in self.denuncias if not d.revisada)


class Respuesta(db.Model):
    """Un mensaje dentro de un tema (la columna "Mensajes" de foro.html los cuenta)."""

    __tablename__ = "respuestas"

    id_respuesta = db.Column(db.Integer, primary_key=True)
    id_publicacion = db.Column(
        db.Integer, db.ForeignKey("publicaciones.id_publicacion", ondelete="CASCADE"), nullable=False, index=True
    )
    autor = db.Column(db.String(80), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_colombia)

    publicacion = db.relationship("Publicacion", back_populates="respuestas")


class Denuncia(db.Model):
    """Reporte de un usuario sobre una publicación (lo revisa el moderador en admin/foro.html)."""

    __tablename__ = "denuncias"

    id_denuncia = db.Column(db.Integer, primary_key=True)
    id_publicacion = db.Column(
        db.Integer, db.ForeignKey("publicaciones.id_publicacion", ondelete="CASCADE"), nullable=False, index=True
    )
    motivo = db.Column(db.String(20), nullable=False)
    detalle = db.Column(db.String(300))
    revisada = db.Column(db.Boolean, nullable=False, default=False)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_colombia)

    publicacion = db.relationship("Publicacion", back_populates="denuncias")
