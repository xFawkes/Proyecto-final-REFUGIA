"""REFUGIA — aplicación Flask: API + páginas del sitio.

crear_app() arma la aplicación: conexión a MySQL, extensiones, secciones de la
API y páginas. La ejecuta main.py (en la raíz del proyecto) con:  python main.py
"""

from __future__ import annotations

import sys

import pymysql
from flask import Flask
from flask_cors import CORS
from sqlalchemy.engine import make_url

from . import donaciones, mapa, noticias, paginas, voluntariado
from .config import configuracion
from .errores import registrar_errores
from .extensiones import db, ma

# ---------------------------------------------------------------------------
# Secciones de la API. Para agregar una (ver api/_plantilla):
#     from . import donaciones, foro, mapa, noticias, paginas, voluntariado
#     SECCIONES = [mapa, noticias, voluntariado, donaciones, foro]
# ---------------------------------------------------------------------------
SECCIONES = [mapa, noticias, voluntariado, donaciones]


def crear_app(config_extra: dict | None = None) -> Flask:
    app = Flask(__name__, static_folder=None)  # las páginas las sirve api/paginas.py
    app.config.from_mapping(configuracion())
    if config_extra:
        app.config.update(config_extra)
    app.json.ensure_ascii = False  # tildes y ñ tal cual en el JSON
    app.json.sort_keys = False

    db.init_app(app)
    ma.init_app(app)

    # Permite llamar la API desde Live Server de VS Code (puerto 5500)
    origenes = ["http://localhost:5500", "http://127.0.0.1:5500", *app.config["ORIGENES_CORS"]]
    CORS(app, resources={r"/api/*": {"origins": origenes}})

    for seccion in SECCIONES:
        app.register_blueprint(seccion.bp)
    app.register_blueprint(paginas.bp)
    registrar_errores(app)

    with app.app_context():
        crear_base_si_no_existe(app.config["SQLALCHEMY_DATABASE_URI"])
        db.create_all()  # igual que en el tutorial: crea las tablas que falten
        for seccion in SECCIONES:
            seccion.cargar_datos_ejemplo()

    return app


def crear_base_si_no_existe(uri: str) -> None:
    """Si la base de datos (schema) de MySQL no existe, la crea.

    Equivale a crearla a mano en MySQL Workbench, como en el tutorial.
    """
    url = make_url(uri)
    if not url.drivername.startswith("mysql"):
        return
    try:
        conexion = pymysql.connect(
            host=url.host or "localhost", port=url.port or 3306,
            user=url.username, password=url.password or "", charset="utf8mb4",
        )
    except pymysql.err.OperationalError as error:
        codigo = error.args[0]
        if codigo == 1045:
            motivo = "usuario o contraseña incorrectos. Revisa USUARIO_BD y PASSWORD_BD en el archivo .env"
        elif codigo in (2003, 2005):
            motivo = f"no hay un servidor MySQL en {url.host}:{url.port}. ¿Está encendido MySQL?"
        else:
            motivo = str(error)
        sys.exit(f"\n[REFUGIA] No se pudo conectar a MySQL: {motivo}\n")
    with conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{url.database}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
