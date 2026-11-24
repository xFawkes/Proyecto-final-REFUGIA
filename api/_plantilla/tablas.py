"""Tablas de la sección y datos de ejemplo.

Si cambias las columnas después de crear la base, borra api/refugia.db y
reinicia el servidor para que se vuelva a crear.
"""

import sqlite3

# Usa un nombre de tabla propio de la sección para no chocar con otras
ESQUEMA = """
CREATE TABLE IF NOT EXISTS elementos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo      TEXT NOT NULL,
    descripcion TEXT,
    creado_en   TEXT NOT NULL DEFAULT (datetime('now', '-5 hours'))  -- hora de Colombia
);
"""

DATOS_EJEMPLO = [
    {"titulo": "Primer elemento de ejemplo", "descripcion": "Reemplázame por datos reales de tu sección."},
    {"titulo": "Segundo elemento de ejemplo", "descripcion": None},
]


def inicializar(conexion: sqlite3.Connection) -> None:
    """Crea las tablas y, si están vacías, carga los datos de ejemplo."""
    conexion.executescript(ESQUEMA)
    if conexion.execute("SELECT COUNT(*) FROM elementos").fetchone()[0] == 0:
        conexion.executemany(
            "INSERT INTO elementos (titulo, descripcion) VALUES (:titulo, :descripcion)",
            DATOS_EJEMPLO,
        )
