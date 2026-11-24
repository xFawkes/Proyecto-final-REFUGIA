"""Configuración del servidor y de la conexión a MySQL.

Los datos de conexión se leen del archivo .env (en la raíz del proyecto),
para no escribir la contraseña en el código ni subirla a GitHub.
Son las mismas variables del tutorial: usuario_bd, password_bd, servidor_bd,
puerto_bd y nombre_bd.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote_plus

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent


def cargar_env(ruta: Path = RAIZ_PROYECTO / ".env") -> None:
    """Lee un archivo .env sencillo (CLAVE=valor) sin dependencias extra."""
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


def datos_conexion() -> dict:
    return {
        "usuario": os.environ.get("USUARIO_BD", "root"),
        "password": os.environ.get("PASSWORD_BD", ""),
        "servidor": os.environ.get("SERVIDOR_BD", "localhost"),
        "puerto": int(os.environ.get("PUERTO_BD", "3306")),
        "nombre": os.environ.get("NOMBRE_BD", "refugia"),
    }


def uri_mysql(d: dict) -> str:
    # quote_plus permite contraseñas con caracteres especiales como @ o #
    return (
        f"mysql+pymysql://{quote_plus(d['usuario'])}:{quote_plus(d['password'])}"
        f"@{d['servidor']}:{d['puerto']}/{d['nombre']}?charset=utf8mb4"
    )


def configuracion() -> dict:
    cargar_env()
    return {
        # Igual que en el tutorial: cadena de conexión y desactivar avisos innecesarios.
        # DATABASE_URL permite usar otra base (las pruebas usan SQLite en memoria).
        "SQLALCHEMY_DATABASE_URI": os.environ.get("DATABASE_URL") or uri_mysql(datos_conexion()),
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        # MySQL cierra las conexiones inactivas: se revisan antes de usarlas
        "SQLALCHEMY_ENGINE_OPTIONS": {"pool_pre_ping": True, "pool_recycle": 280},
        # Orígenes extra que pueden llamar la API (ej. el dominio donde se publique)
        "ORIGENES_CORS": [o.strip() for o in os.environ.get("REFUGIA_CORS", "").split(",") if o.strip()],
    }
