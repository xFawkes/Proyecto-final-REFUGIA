"""Verifica que la plantilla api/_plantilla funciona, para que copiarla sea seguro."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import _plantilla, database


def test_plantilla_crea_tabla_y_responde():
    database.inicializar_bd([_plantilla])
    app = FastAPI()
    app.include_router(_plantilla.router)
    with TestClient(app) as c:
        datos = c.get("/api/elementos").json()
        assert datos["total"] == 2
        primero = datos["resultados"][0]["id"]
        assert c.get(f"/api/elementos/{primero}").status_code == 200
        assert c.get("/api/elementos", params={"q": "Segundo"}).json()["total"] == 1
        assert c.get("/api/elementos/9999").status_code == 404
