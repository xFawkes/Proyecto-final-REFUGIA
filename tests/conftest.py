"""Configuración común de las pruebas.

Por defecto usan SQLite en memoria (no necesitan MySQL encendido). Para probar
contra MySQL real, define REFUGIA_TEST_DB con una base de datos DE PRUEBAS
(se borra y se vuelve a crear):

    $env:REFUGIA_TEST_DB = "mysql+pymysql://root:tu_clave@localhost:3306/refugia_pruebas"
    python -m pytest
"""

import os

import pytest
from sqlalchemy.engine import make_url

URI_PRUEBAS = os.environ.get("REFUGIA_TEST_DB", "sqlite:///:memory:")
os.environ["DATABASE_URL"] = URI_PRUEBAS  # nunca la base de datos real del proyecto


def borrar_base_mysql(uri: str) -> None:
    url = make_url(uri)
    if not url.drivername.startswith("mysql"):
        return
    if url.database in ("refugia", os.environ.get("NOMBRE_BD")):
        raise RuntimeError("REFUGIA_TEST_DB no puede ser la base de datos del proyecto: usa una de pruebas.")
    import pymysql

    with pymysql.connect(host=url.host, port=url.port or 3306, user=url.username, password=url.password or "") as c:
        with c.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{url.database}`")


@pytest.fixture(scope="session")
def app():
    borrar_base_mysql(URI_PRUEBAS)
    from api import crear_app

    app = crear_app({"TESTING": True})
    yield app


@pytest.fixture(scope="session")
def cliente(app):
    return app.test_client()
