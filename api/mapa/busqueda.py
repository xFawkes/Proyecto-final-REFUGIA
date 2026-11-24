"""Mapa: búsqueda y filtrado de puntos de ayuda."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field

from ..utilidades import distancia_km, esta_abierto, horario_legible, normalizar
from .catalogos import SERVICIOS, TIPOS, VERIFICACION

PALABRAS_VACIAS = {"de", "del", "la", "las", "el", "los", "y", "en", "para", "un", "una", "con", "a", "al"}


@dataclass
class Filtros:
    q: str | None = None
    tipos: list[str] = field(default_factory=list)
    servicios: list[str] = field(default_factory=list)
    verificacion: list[str] = field(default_factory=list)
    abierto_ahora: bool = False
    gratuito: bool = False
    con_cupos: bool = False
    confianza_min: float | None = None
    ids: list[int] | None = None
    lat: float | None = None
    lng: float | None = None
    radio_km: float | None = None
    orden: str | None = None
    limite: int = 100
    offset: int = 0


def terminos_busqueda(q: str | None) -> list[str]:
    """'Centros de salud' -> ['centro', 'salud'] (sin tildes, sin palabras vacías, en singular)."""
    terminos = []
    for palabra in normalizar(q).split():
        if palabra in PALABRAS_VACIAS:
            continue
        # Singular aproximado: hospitales -> hospital, albergues -> albergu, centros -> centro.
        # Como la búsqueda es por subcadena, 'albergu' sigue encontrando 'albergue'.
        if len(palabra) > 4 and palabra.endswith("es"):
            palabra = palabra[:-2]
        elif len(palabra) > 3 and palabra.endswith("s"):
            palabra = palabra[:-1]
        terminos.append(palabra)
    return terminos


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def fila_a_punto(fila: sqlite3.Row, servicios: list[str], lat=None, lng=None) -> dict:
    franjas = json.loads(fila["horario"])
    punto = {k: fila[k] for k in fila.keys() if k not in ("texto_busqueda", "horario")}
    punto.update(
        gratuito=bool(fila["gratuito"]),
        tipo_nombre=TIPOS[fila["tipo"]]["nombre"],
        verificacion_nombre=VERIFICACION[fila["verificacion"]],
        horario=franjas,
        horario_texto=horario_legible(franjas),
        abierto_ahora=esta_abierto(franjas),
        servicios=[{"clave": s, "nombre": SERVICIOS[s]} for s in servicios if s in SERVICIOS],
        distancia_km=None,
    )
    if lat is not None and lng is not None:
        punto["distancia_km"] = round(distancia_km(lat, lng, fila["lat"], fila["lng"]), 2)
    return punto


def _servicios_por_punto(conexion: sqlite3.Connection, ids: list[int]) -> dict[int, list[str]]:
    resultado: dict[int, list[str]] = {i: [] for i in ids}
    if not ids:
        return resultado
    marcadores = ",".join("?" for _ in ids)
    filas = conexion.execute(
        f"SELECT punto_id, servicio FROM punto_servicio WHERE punto_id IN ({marcadores})", ids
    )
    for fila in filas:
        resultado[fila["punto_id"]].append(fila["servicio"])
    orden = list(SERVICIOS)  # mismo orden del catálogo
    return {k: sorted(v, key=orden.index) for k, v in resultado.items()}


def _puntaje(punto: dict, nombre_norm: str, terminos: list[str]) -> float:
    """Relevancia: coincidir en el nombre pesa más que en la descripción o la dirección."""
    puntaje = 0.0
    palabras_nombre = nombre_norm.split()
    for t in terminos:
        if any(p.startswith(t) for p in palabras_nombre):
            puntaje += 3
        elif t in nombre_norm:
            puntaje += 2
        else:
            puntaje += 1
    return puntaje + punto["confianza"] / 10  # desempate por confianza


def buscar_puntos(conexion: sqlite3.Connection, f: Filtros) -> tuple[int, list[dict]]:
    condiciones: list[str] = []
    parametros: list = []

    # --- Filtros que resuelve SQL ---
    terminos = terminos_busqueda(f.q)
    for t in terminos:
        condiciones.append("texto_busqueda LIKE ? ESCAPE '\\'")
        parametros.append(f"%{_escapar_like(t)}%")

    if f.tipos:
        condiciones.append(f"tipo IN ({','.join('?' for _ in f.tipos)})")
        parametros += f.tipos

    if f.verificacion:
        condiciones.append(f"verificacion IN ({','.join('?' for _ in f.verificacion)})")
        parametros += f.verificacion

    if f.gratuito:
        condiciones.append("gratuito = 1")

    if f.con_cupos:
        condiciones.append("cupos_disponibles > 0")

    if f.confianza_min is not None:
        condiciones.append("confianza >= ?")
        parametros.append(f.confianza_min)

    if f.ids is not None:
        if not f.ids:
            return 0, []
        condiciones.append(f"id IN ({','.join('?' for _ in f.ids)})")
        parametros += f.ids

    if f.servicios:
        # El punto debe ofrecer TODOS los servicios pedidos
        condiciones.append(
            f"""id IN (SELECT punto_id FROM punto_servicio
                       WHERE servicio IN ({','.join('?' for _ in f.servicios)})
                       GROUP BY punto_id HAVING COUNT(DISTINCT servicio) = ?)"""
        )
        parametros += f.servicios + [len(set(f.servicios))]

    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
    filas = conexion.execute(f"SELECT * FROM puntos {where}", parametros).fetchall()
    servicios = _servicios_por_punto(conexion, [fila["id"] for fila in filas])

    # --- Filtros que dependen de la hora actual o de la ubicación del usuario ---
    puntos = []
    for fila in filas:
        punto = fila_a_punto(fila, servicios[fila["id"]], f.lat, f.lng)
        if f.abierto_ahora and not punto["abierto_ahora"]:
            continue
        if f.radio_km is not None and punto["distancia_km"] > f.radio_km:
            continue
        punto["_puntaje"] = _puntaje(punto, normalizar(punto["nombre"]), terminos)
        puntos.append(punto)

    # --- Orden ---
    orden = f.orden or ("relevancia" if terminos else "distancia" if f.lat is not None else "confianza")
    if orden == "relevancia":
        puntos.sort(key=lambda p: (-p["_puntaje"], p["distancia_km"] or 0, p["nombre"]))
    elif orden == "distancia":
        puntos.sort(key=lambda p: (p["distancia_km"], p["nombre"]))
    elif orden == "confianza":
        puntos.sort(key=lambda p: (-p["confianza"], p["nombre"]))
    else:
        puntos.sort(key=lambda p: normalizar(p["nombre"]))

    for p in puntos:
        del p["_puntaje"]

    total = len(puntos)
    return total, puntos[f.offset : f.offset + f.limite]


def obtener_punto(conexion: sqlite3.Connection, punto_id: int, lat=None, lng=None) -> dict | None:
    fila = conexion.execute("SELECT * FROM puntos WHERE id = ?", (punto_id,)).fetchone()
    if fila is None:
        return None
    return fila_a_punto(fila, _servicios_por_punto(conexion, [punto_id])[punto_id], lat, lng)


def contar_por_tipo(conexion: sqlite3.Connection) -> dict[str, int]:
    conteo = {clave: 0 for clave in TIPOS}
    for fila in conexion.execute("SELECT tipo, COUNT(*) AS n FROM puntos GROUP BY tipo"):
        conteo[fila["tipo"]] = fila["n"]
    return conteo
