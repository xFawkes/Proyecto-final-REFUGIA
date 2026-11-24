"""Modelos: definen la forma del JSON que devuelve la API (y su documentación en /docs)."""

from pydantic import BaseModel


class Elemento(BaseModel):
    id: int
    titulo: str
    descripcion: str | None
    creado_en: str


class ListaElementos(BaseModel):
    total: int
    resultados: list[Elemento]
