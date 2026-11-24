"""Mapa: tablas en la base de datos y carga de los datos de ejemplo."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from ..utilidades import ZONA_COLOMBIA, normalizar
from .catalogos import SERVICIOS, TIPOS
from .datos_ejemplo import PUNTOS

ESQUEMA = """
CREATE TABLE IF NOT EXISTS puntos (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre            TEXT    NOT NULL,
    tipo              TEXT    NOT NULL,
    descripcion       TEXT,
    direccion         TEXT    NOT NULL,
    barrio            TEXT,
    localidad         TEXT,
    ciudad            TEXT    NOT NULL DEFAULT 'Bogotá',
    lat               REAL    NOT NULL,
    lng               REAL    NOT NULL,
    telefono          TEXT,
    whatsapp          TEXT,
    correo            TEXT,
    sitio_web         TEXT,
    imagen            TEXT,
    gratuito          INTEGER NOT NULL DEFAULT 1,
    costo_detalle     TEXT,
    confianza         REAL    NOT NULL DEFAULT 0 CHECK (confianza BETWEEN 0 AND 5),
    verificacion      TEXT    NOT NULL DEFAULT 'sin_confirmar',
    fuente            TEXT,
    capacidad         INTEGER,
    cupos_disponibles INTEGER,
    horario           TEXT    NOT NULL DEFAULT '[]',   -- JSON con franjas
    actualizado_en    TEXT    NOT NULL,
    texto_busqueda    TEXT    NOT NULL DEFAULT ''      -- texto normalizado para buscar
);

CREATE TABLE IF NOT EXISTS punto_servicio (
    punto_id INTEGER NOT NULL REFERENCES puntos(id) ON DELETE CASCADE,
    servicio TEXT    NOT NULL,
    PRIMARY KEY (punto_id, servicio)
);

CREATE INDEX IF NOT EXISTS idx_puntos_tipo ON puntos(tipo);
CREATE INDEX IF NOT EXISTS idx_servicio ON punto_servicio(servicio);
"""


def construir_texto_busqueda(punto: dict, servicios: list[str]) -> str:
    """Junta en un solo texto normalizado todo lo que se puede buscar."""
    partes = [
        punto["nombre"],
        TIPOS[punto["tipo"]]["nombre"],
        TIPOS[punto["tipo"]]["palabras_clave"],
        punto.get("descripcion"),
        punto["direccion"],
        punto.get("barrio"),
        punto.get("localidad"),
        punto.get("ciudad", "Bogotá"),
        *(SERVICIOS[s] for s in servicios),
    ]
    return normalizar(" ".join(p for p in partes if p))


def insertar_punto(conexion: sqlite3.Connection, punto: dict) -> int:
    servicios = punto.get("servicios", [])
    columnas = [
        "nombre", "tipo", "descripcion", "direccion", "barrio", "localidad", "lat", "lng",
        "telefono", "whatsapp", "correo", "sitio_web", "imagen", "gratuito", "costo_detalle",
        "confianza", "verificacion", "fuente", "capacidad", "cupos_disponibles",
    ]
    valores = [punto.get(c) for c in columnas]
    columnas += ["horario", "actualizado_en", "texto_busqueda"]
    valores += [
        json.dumps(punto.get("horario", [])),
        punto.get("actualizado_en") or datetime.now(ZONA_COLOMBIA).isoformat(timespec="minutes"),
        construir_texto_busqueda(punto, servicios),
    ]
    marcadores = ", ".join("?" for _ in columnas)
    cursor = conexion.execute(
        f"INSERT INTO puntos ({', '.join(columnas)}) VALUES ({marcadores})", valores
    )
    punto_id = cursor.lastrowid
    conexion.executemany(
        "INSERT INTO punto_servicio (punto_id, servicio) VALUES (?, ?)",
        [(punto_id, s) for s in servicios],
    )
    return punto_id


def inicializar(conexion: sqlite3.Connection) -> None:
    """Crea las tablas del mapa y, si están vacías, carga los datos de ejemplo."""
    conexion.executescript(ESQUEMA)
    vacia = conexion.execute("SELECT COUNT(*) FROM puntos").fetchone()[0] == 0
    if vacia:
        for punto in PUNTOS:
            insertar_punto(conexion, punto)
