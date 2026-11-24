"""Configuración común de las pruebas: base de datos temporal y cliente HTTP."""

import os
import tempfile

import pytest

# Base de datos temporal para no tocar api/refugia.db (antes de importar la app)
os.environ["REFUGIA_DB"] = os.path.join(tempfile.mkdtemp(), "prueba.db")

from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402


@pytest.fixture(scope="session")
def cliente():
    with TestClient(app) as c:
        yield c
