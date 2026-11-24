"""Mapa: endpoints de la API (/api/puntos, /api/tipos, /api/servicios, /api/verificacion)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from .. import database
from .busqueda import Filtros, buscar_puntos, contar_por_tipo, obtener_punto
from .catalogos import SERVICIOS, TIPOS, VERIFICACION
from .modelos import ListaPuntos, NivelVerificacion, Orden, Punto, Servicio, Tipo, TipoPunto, Verificacion

router = APIRouter(prefix="/api", tags=["Mapa"])


@router.get("/puntos", response_model=ListaPuntos, summary="Buscar y filtrar puntos")
def listar_puntos(
    q: Annotated[str | None, Query(max_length=100, description="Texto libre: nombre, tipo, barrio, dirección, servicio…")] = None,
    tipo: Annotated[list[TipoPunto], Query(description="Uno o varios tipos (repetir el parámetro)")] = [],
    servicio: Annotated[list[str], Query(description="Servicios que el punto debe ofrecer TODOS")] = [],
    verificacion: Annotated[list[NivelVerificacion], Query(description="Niveles de verificación aceptados")] = [],
    abierto_ahora: Annotated[bool, Query(description="Solo lugares abiertos en este momento (hora de Colombia)")] = False,
    gratuito: Annotated[bool, Query(description="Solo lugares sin costo")] = False,
    con_cupos: Annotated[bool, Query(description="Solo albergues con cupos disponibles")] = False,
    confianza_min: Annotated[float | None, Query(ge=0, le=5, description="Índice de confianza mínimo (0 a 5)")] = None,
    ids: Annotated[str | None, Query(description="Lista de IDs separados por coma (ej. puntos guardados)", pattern=r"^\s*\d*(\s*,\s*\d+)*\s*$")] = None,
    lat: Annotated[float | None, Query(ge=-90, le=90, description="Latitud del usuario")] = None,
    lng: Annotated[float | None, Query(ge=-180, le=180, description="Longitud del usuario")] = None,
    radio_km: Annotated[float | None, Query(gt=0, le=100, description="Radio máximo desde (lat, lng)")] = None,
    orden: Annotated[Orden | None, Query(description="Por defecto: relevancia si hay texto, distancia si hay ubicación, si no confianza")] = None,
    limite: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    if (lat is None) != (lng is None):
        raise HTTPException(422, "Envía lat y lng juntos.")
    if lat is None and (radio_km is not None or orden == "distancia"):
        raise HTTPException(422, "radio_km y orden=distancia necesitan lat y lng.")

    servicios_invalidos = [s for s in servicio if s not in SERVICIOS]
    if servicios_invalidos:
        raise HTTPException(422, f"Servicio desconocido: {', '.join(servicios_invalidos)}. Consulta /api/servicios.")

    lista_ids = None
    if ids is not None:
        lista_ids = [int(i) for i in ids.split(",") if i.strip()]

    filtros = Filtros(
        q=q, tipos=list(tipo), servicios=servicio, verificacion=list(verificacion),
        abierto_ahora=abierto_ahora, gratuito=gratuito, con_cupos=con_cupos,
        confianza_min=confianza_min, ids=lista_ids, lat=lat, lng=lng, radio_km=radio_km,
        orden=orden, limite=limite, offset=offset,
    )
    with database.conectar() as conexion:
        total, resultados = buscar_puntos(conexion, filtros)
    return {"total": total, "limite": limite, "offset": offset, "resultados": resultados}


@router.get("/puntos/{punto_id}", response_model=Punto, summary="Detalle de un punto")
def detalle_punto(
    punto_id: int,
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lng: Annotated[float | None, Query(ge=-180, le=180)] = None,
):
    with database.conectar() as conexion:
        punto = obtener_punto(conexion, punto_id, lat, lng)
    if punto is None:
        raise HTTPException(404, "No existe un punto con ese ID.")
    return punto


@router.get("/tipos", response_model=list[Tipo], summary="Tipos de lugar y cuántos hay")
def listar_tipos():
    with database.conectar() as conexion:
        conteo = contar_por_tipo(conexion)
    return [
        {"clave": clave, "nombre": t["nombre"], "plural": t["plural"], "total": conteo[clave]}
        for clave, t in TIPOS.items()
    ]


@router.get("/servicios", response_model=list[Servicio], summary="Servicios filtrables")
def listar_servicios():
    return [{"clave": clave, "nombre": nombre} for clave, nombre in SERVICIOS.items()]


@router.get("/verificacion", response_model=list[Verificacion], summary="Niveles de verificación")
def listar_verificacion():
    return [{"clave": clave, "nombre": nombre} for clave, nombre in VERIFICACION.items()]
