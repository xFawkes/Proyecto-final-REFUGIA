"""Conexión a la base de datos SQLite compartida por todas las secciones.

Cada sección (mapa, noticias, donaciones…) crea sus propias tablas en su
archivo tablas.py; esta función solo abre la conexión y las inicializa.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

# Se puede cambiar con la variable de entorno REFUGIA_DB (las pruebas la usan)
RUTA_BD = Path(os.environ.get("REFUGIA_DB", Path(__file__).parent / "refugia.db"))


def conectar() -> sqlite3.Connection:
    conexion = sqlite3.connect(RUTA_BD)
    conexion.row_factory = sqlite3.Row  # filas accesibles como diccionario: fila["nombre"]
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def inicializar_bd(secciones) -> None:
    """Llama a inicializar(conexion) de cada sección: crea sus tablas y carga datos de ejemplo."""
    RUTA_BD.parent.mkdir(parents=True, exist_ok=True)
    with conectar() as conexion:
        for seccion in secciones:
            seccion.inicializar(conexion)
