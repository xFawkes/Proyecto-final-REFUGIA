"""Donaciones: modelos (tablas "organizaciones" y "donaciones" en MySQL)."""

import secrets
from datetime import datetime

from ..extensiones import db
from ..utilidades import ZONA_COLOMBIA


def ahora_colombia() -> datetime:
    """Fecha y hora de Colombia sin zona (MySQL DATETIME no guarda la zona)."""
    return datetime.now(ZONA_COLOMBIA).replace(tzinfo=None, microsecond=0)


class Organizacion(db.Model):
    """ONG que recibe donaciones (las tarjetas de la izquierda en donaciones.html)."""

    __tablename__ = "organizaciones"

    id_organizacion = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False, unique=True)
    descripcion = db.Column(db.Text, nullable=False)
    impacto = db.Column(db.String(300))        # "Tu donación ayuda a: …"
    enlace = db.Column(db.String(500))         # página oficial de la ONG
    imagen = db.Column(db.String(300))
    imagen_alt = db.Column(db.String(200))
    activa = db.Column(db.Boolean, nullable=False, default=True)  # False = no recibe donaciones ni sale en la página
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_colombia)

    donaciones = db.relationship("Donacion", back_populates="organizacion", passive_deletes=True)


class Donacion(db.Model):
    """Una donación y el resultado de su pago en la pasarela SIMULADA.

    Por seguridad NUNCA se guarda el número completo de la tarjeta ni el CVV:
    solo la franquicia y los últimos 4 dígitos (detalle_pago), como hacen las pasarelas reales.
    """

    __tablename__ = "donaciones"

    id_donacion = db.Column(db.Integer, primary_key=True)
    referencia = db.Column(db.String(20), nullable=False, unique=True)  # RFG-1A2B3C4D (para el comprobante)
    id_organizacion = db.Column(
        db.Integer, db.ForeignKey("organizaciones.id_organizacion", ondelete="SET NULL"), index=True
    )
    destino = db.Column(db.String(150), nullable=False)  # nombre de la ONG al donar (se conserva si la borran)
    monto = db.Column(db.Integer, nullable=False)        # pesos colombianos, sin decimales
    frecuencia = db.Column(db.String(10), nullable=False, default="unica")
    nombre_donante = db.Column(db.String(120), nullable=False)
    correo = db.Column(db.String(150), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="pendiente", index=True)
    metodo_pago = db.Column(db.String(20))               # tarjeta, transferencia o billetera
    detalle_pago = db.Column(db.String(80))              # "Visa terminada en 4242"
    codigo_autorizacion = db.Column(db.String(12))
    mensaje_pasarela = db.Column(db.String(200))
    nota = db.Column(db.String(300))                     # nota del administrador
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_colombia, index=True)
    pagado_en = db.Column(db.DateTime)
    actualizado_en = db.Column(db.DateTime, nullable=False, default=ahora_colombia, onupdate=ahora_colombia)

    organizacion = db.relationship("Organizacion", back_populates="donaciones")

    @staticmethod
    def nueva_referencia() -> str:
        """Referencia corta y difícil de adivinar (con ella se consulta el comprobante)."""
        while True:
            referencia = f"RFG-{secrets.token_hex(4).upper()}"
            if not db.session.scalar(db.select(Donacion.id_donacion).where(Donacion.referencia == referencia)):
                return referencia
