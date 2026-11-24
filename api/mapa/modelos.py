"""Mapa: modelos de respuesta (definen el JSON que devuelve la API y su documentación en /docs)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

TipoPunto = Literal["albergue", "centro_salud", "hospital", "centro_acopio", "otro"]
NivelVerificacion = Literal["oficial", "comunitaria", "sin_confirmar"]
Orden = Literal["relevancia", "distancia", "confianza", "nombre"]


class Franja(BaseModel):
    dias: list[int] = Field(description="0 = lunes … 6 = domingo")
    abre: str = Field(examples=["08:00"])
    cierra: str = Field(examples=["19:00"])


class Servicio(BaseModel):
    clave: str
    nombre: str


class Punto(BaseModel):
    id: int
    nombre: str
    tipo: TipoPunto
    tipo_nombre: str
    descripcion: str | None
    direccion: str
    barrio: str | None
    localidad: str | None
    ciudad: str
    lat: float
    lng: float
    telefono: str | None
    whatsapp: str | None
    correo: str | None
    sitio_web: str | None
    imagen: str | None
    gratuito: bool
    costo_detalle: str | None
    confianza: float = Field(ge=0, le=5, description="Índice de confianza de 0 a 5")
    verificacion: NivelVerificacion
    verificacion_nombre: str
    fuente: str | None
    capacidad: int | None
    cupos_disponibles: int | None
    horario: list[Franja]
    horario_texto: str
    abierto_ahora: bool
    servicios: list[Servicio]
    actualizado_en: str
    distancia_km: float | None = Field(
        default=None, description="Solo si se envían lat y lng del usuario"
    )


class ListaPuntos(BaseModel):
    total: int = Field(description="Total de resultados antes de paginar")
    limite: int
    offset: int
    resultados: list[Punto]


class Tipo(BaseModel):
    clave: TipoPunto
    nombre: str
    plural: str
    total: int


class Verificacion(BaseModel):
    clave: NivelVerificacion
    nombre: str

