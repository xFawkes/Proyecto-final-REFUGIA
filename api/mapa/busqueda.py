"""Mapa: búsqueda y filtrado de puntos de ayuda con SQLAlchemy."""

from __future__ import annotations

from ..extensiones import db
from ..utilidades import distancia_km, normalizar
from .catalogos import TIPOS
from .esquemas import punto_schema
from .modelos import Punto, PuntoServicio

PALABRAS_VACIAS = {"de", "del", "la", "las", "el", "los", "y", "en", "para", "un", "una", "con", "a", "al"}


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


def _puntaje(nombre_norm: str, terminos: list[str], confianza: float) -> float:
    """Relevancia: coincidir en el nombre pesa más que en la descripción o la dirección."""
    puntaje = 0.0
    palabras = nombre_norm.split()
    for t in terminos:
        if any(p.startswith(t) for p in palabras):
            puntaje += 3
        elif t in nombre_norm:
            puntaje += 2
        else:
            puntaje += 1
    return puntaje + confianza / 10  # desempate por confianza


def a_diccionario(punto: Punto, lat=None, lng=None) -> dict:
    datos = punto_schema.dump(punto)
    datos["distancia_km"] = (
        round(distancia_km(lat, lng, punto.lat, punto.lng), 2) if lat is not None and lng is not None else None
    )
    return datos


def buscar_puntos(f: dict) -> tuple[int, list[dict]]:
    """f es el diccionario validado por FiltrosSchema."""
    consulta = db.select(Punto)

    # --- Filtros que resuelve la base de datos ---
    terminos = terminos_busqueda(f.get("q"))
    for t in terminos:
        consulta = consulta.where(Punto.texto_busqueda.contains(t, autoescape=True))
    if f["tipo"]:
        consulta = consulta.where(Punto.tipo.in_(f["tipo"]))
    if f["verificacion"]:
        consulta = consulta.where(Punto.verificacion.in_(f["verificacion"]))
    if f["gratuito"]:
        consulta = consulta.where(Punto.gratuito.is_(True))
    if f["con_cupos"]:
        consulta = consulta.where(Punto.cupos_disponibles > 0)
    if f.get("confianza_min") is not None:
        consulta = consulta.where(Punto.confianza >= f["confianza_min"])
    if f.get("ids") is not None:
        ids = [int(i) for i in f["ids"].split(",") if i.strip()]
        if not ids:
            return 0, []
        consulta = consulta.where(Punto.id.in_(ids))
    if f["servicio"]:
        # El punto debe ofrecer TODOS los servicios pedidos
        pedidos = set(f["servicio"])
        con_todos = (
            db.select(PuntoServicio.punto_id)
            .where(PuntoServicio.servicio.in_(pedidos))
            .group_by(PuntoServicio.punto_id)
            .having(db.func.count(db.distinct(PuntoServicio.servicio)) == len(pedidos))
        )
        consulta = consulta.where(Punto.id.in_(con_todos))

    puntos = db.session.scalars(consulta).all()

    # --- Filtros que dependen de la hora actual o de la ubicación del usuario ---
    lat, lng = f.get("lat"), f.get("lng")
    resultados = []
    for punto in puntos:
        datos = a_diccionario(punto, lat, lng)
        if f["abierto_ahora"] and not datos["abierto_ahora"]:
            continue
        if f.get("radio_km") is not None and datos["distancia_km"] > f["radio_km"]:
            continue
        datos["_puntaje"] = _puntaje(normalizar(punto.nombre), terminos, punto.confianza)
        resultados.append(datos)

    # --- Orden ---
    orden = f.get("orden") or ("relevancia" if terminos else "distancia" if lat is not None else "confianza")
    if orden == "relevancia":
        resultados.sort(key=lambda p: (-p["_puntaje"], p["distancia_km"] or 0, p["nombre"]))
    elif orden == "distancia":
        resultados.sort(key=lambda p: (p["distancia_km"], p["nombre"]))
    elif orden == "confianza":
        resultados.sort(key=lambda p: (-p["confianza"], p["nombre"]))
    else:
        resultados.sort(key=lambda p: normalizar(p["nombre"]))
    for p in resultados:
        del p["_puntaje"]

    total = len(resultados)
    return total, resultados[f["offset"] : f["offset"] + f["limite"]]


def contar_por_tipo() -> dict[str, int]:
    conteo = {clave: 0 for clave in TIPOS}
    filas = db.session.execute(db.select(Punto.tipo, db.func.count()).group_by(Punto.tipo))
    for tipo, n in filas:
        conteo[tipo] = n
    return conteo
