"""Mapa: tablas de la base de datos como clases de Python (SQLAlchemy).

Igual que la clase Categoria del tutorial: cada clase es una tabla y cada
db.Column una columna. db.create_all() las crea en MySQL al iniciar.
"""

from __future__ import annotations

from datetime import datetime

from ..extensiones import db
from ..utilidades import ZONA_COLOMBIA, normalizar
from .catalogos import SERVICIOS, TIPOS


def ahora_colombia() -> datetime:
    return datetime.now(ZONA_COLOMBIA).replace(tzinfo=None, second=0, microsecond=0)


class Punto(db.Model):
    __tablename__ = "puntos"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    tipo = db.Column(db.String(20), nullable=False, index=True)
    descripcion = db.Column(db.Text)
    direccion = db.Column(db.String(200), nullable=False)
    barrio = db.Column(db.String(100))
    localidad = db.Column(db.String(100))
    ciudad = db.Column(db.String(100), nullable=False, default="Bogotá")
    lat = db.Column(db.Double, nullable=False)
    lng = db.Column(db.Double, nullable=False)
    telefono = db.Column(db.String(30))
    whatsapp = db.Column(db.String(30))
    correo = db.Column(db.String(120))
    sitio_web = db.Column(db.String(255))
    imagen = db.Column(db.String(255))
    gratuito = db.Column(db.Boolean, nullable=False, default=True)
    costo_detalle = db.Column(db.String(200))
    confianza = db.Column(db.Double, nullable=False, default=0)  # 0 a 5
    verificacion = db.Column(db.String(20), nullable=False, default="sin_confirmar")
    fuente = db.Column(db.String(150))
    capacidad = db.Column(db.Integer)
    cupos_disponibles = db.Column(db.Integer)
    horario = db.Column(db.JSON, nullable=False, default=list)  # [{"dias": [0..6], "abre": "08:00", "cierra": "19:00"}]
    actualizado_en = db.Column(db.DateTime, nullable=False, default=ahora_colombia, onupdate=ahora_colombia)
    texto_busqueda = db.Column(db.Text, nullable=False, default="")  # nombre, tipo, barrio… sin tildes

    # Servicios del punto (tabla punto_servicio). Al borrar el punto se borran sus servicios.
    servicios = db.relationship(
        "PuntoServicio", cascade="all, delete-orphan", lazy="selectin", order_by="PuntoServicio.servicio"
    )

    @property
    def claves_servicios(self) -> list[str]:
        orden = list(SERVICIOS)
        return sorted((s.servicio for s in self.servicios), key=lambda s: orden.index(s) if s in orden else 99)

    def asignar_servicios(self, claves: list[str]) -> None:
        self.servicios = [PuntoServicio(servicio=c) for c in dict.fromkeys(claves)]

    def actualizar_texto_busqueda(self) -> None:
        """Junta en un solo texto normalizado todo lo que se puede buscar."""
        tipo = TIPOS.get(self.tipo, {})
        partes = [
            self.nombre, tipo.get("nombre"), tipo.get("palabras_clave"), self.descripcion,
            self.direccion, self.barrio, self.localidad, self.ciudad,
            *(SERVICIOS.get(c, "") for c in self.claves_servicios),
        ]
        self.texto_busqueda = normalizar(" ".join(p for p in partes if p))


class PuntoServicio(db.Model):
    __tablename__ = "punto_servicio"

    punto_id = db.Column(db.Integer, db.ForeignKey("puntos.id", ondelete="CASCADE"), primary_key=True)
    servicio = db.Column(db.String(30), primary_key=True, index=True)
