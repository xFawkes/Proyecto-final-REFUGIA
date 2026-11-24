"""Pruebas de POST, PUT y DELETE de /api/puntos (como en Postman en el tutorial)."""

import pytest

NUEVO = {
    "nombre": "Albergue de Prueba Kennedy",
    "tipo": "albergue",
    "direccion": "Calle 38 Sur # 78-10",
    "barrio": "Kennedy Central",
    "localidad": "Kennedy",
    "lat": 4.6301,
    "lng": -74.1531,
    "telefono": "601 000 0199",
    "correo": "prueba@example.org",
    "confianza": 4.2,
    "verificacion": "comunitaria",
    "capacidad": 50,
    "cupos_disponibles": 20,
    "horario": [{"dias": [0, 1, 2, 3, 4, 5, 6], "abre": "00:00", "cierra": "24:00"}],
    "servicios": ["refugio", "agua", "mascotas"],
}


@pytest.fixture
def punto_creado(cliente):
    r = cliente.post("/api/puntos", json=NUEVO)
    assert r.status_code == 201, r.json
    yield r.json
    cliente.delete(f"/api/puntos/{r.json['id']}")  # limpieza (si la prueba no lo borró)


def total(cliente):
    return cliente.get("/api/puntos").json["total"]


def test_post_crea_y_queda_disponible(cliente, punto_creado):
    p = punto_creado
    assert p["nombre"] == NUEVO["nombre"] and p["tipo_nombre"] == "Albergue"
    assert [s["clave"] for s in p["servicios"]] == ["refugio", "agua", "mascotas"]
    assert p["abierto_ahora"] is True and p["horario_texto"] == "Todos los días, 24 horas."
    assert p["ciudad"] == "Bogotá" and p["gratuito"] is True  # valores por defecto
    # Aparece en GET, en la búsqueda por texto y en los filtros
    assert cliente.get(f"/api/puntos/{p['id']}").status_code == 200
    busqueda = cliente.get("/api/puntos", query_string={"q": "prueba kennedy"}).json
    assert p["id"] in [x["id"] for x in busqueda["resultados"]]
    con_mascotas = cliente.get("/api/puntos", query_string=[("servicio", "mascotas"), ("con_cupos", "true")]).json
    assert p["id"] in [x["id"] for x in con_mascotas["resultados"]]


def test_put_parcial_actualiza_solo_lo_enviado(cliente, punto_creado):
    id_ = punto_creado["id"]
    r = cliente.put(f"/api/puntos/{id_}", json={"cupos_disponibles": 0, "servicios": ["refugio"]})
    assert r.status_code == 200
    assert r.json["cupos_disponibles"] == 0 and r.json["nombre"] == NUEVO["nombre"]
    assert [s["clave"] for s in r.json["servicios"]] == ["refugio"]
    sin_cupos = cliente.get("/api/puntos", query_string={"con_cupos": "true"}).json
    assert id_ not in [x["id"] for x in sin_cupos["resultados"]]


def test_put_cambia_nombre_y_actualiza_busqueda(cliente, punto_creado):
    id_ = punto_creado["id"]
    cliente.put(f"/api/puntos/{id_}", json={"nombre": "Refugio Temporal Zeta"})
    encontrados = cliente.get("/api/puntos", query_string={"q": "zeta"}).json["resultados"]
    assert [x["id"] for x in encontrados] == [id_]


def test_delete_elimina(cliente, punto_creado):
    antes = total(cliente)
    r = cliente.delete(f"/api/puntos/{punto_creado['id']}")
    assert r.status_code == 200 and r.json["id"] == punto_creado["id"]  # devuelve lo eliminado
    assert total(cliente) == antes - 1
    assert cliente.get(f"/api/puntos/{punto_creado['id']}").status_code == 404
    assert cliente.delete(f"/api/puntos/{punto_creado['id']}").status_code == 404


@pytest.mark.parametrize(
    "cambios, campo",
    [
        ({"nombre": None}, "nombre"),
        ({"tipo": "cine"}, "tipo"),
        ({"lat": 40.4}, "lat"),                       # fuera de Colombia (¿lat y lng invertidas?)
        ({"correo": "no-es-correo"}, "correo"),
        ({"cupos_disponibles": 99}, "cupos_disponibles"),  # más cupos que capacidad
        ({"horario": [{"dias": [9], "abre": "8am", "cierra": "19:00"}]}, "horario"),
        ({"servicios": ["piscina"]}, "servicios"),
        ({"nombr": "typo"}, "nombr"),                  # campo desconocido
    ],
)
def test_post_rechaza_datos_invalidos(cliente, cambios, campo):
    antes = total(cliente)
    datos = {**NUEVO, **cambios}
    r = cliente.post("/api/puntos", json=datos)
    assert r.status_code == 400
    assert campo in r.json["detalles"]
    assert total(cliente) == antes


def test_post_sin_campos_obligatorios(cliente):
    r = cliente.post("/api/puntos", json={"nombre": "Solo nombre"})
    assert r.status_code == 400
    assert {"tipo", "direccion", "lat", "lng"} <= set(r.json["detalles"])


def test_put_valida_cupos_contra_capacidad_guardada(cliente, punto_creado):
    r = cliente.put(f"/api/puntos/{punto_creado['id']}", json={"cupos_disponibles": 51})
    assert r.status_code == 400
    assert cliente.get(f"/api/puntos/{punto_creado['id']}").json["cupos_disponibles"] == 20  # no cambió


def test_cuerpo_que_no_es_json(cliente):
    r = cliente.post("/api/puntos", data="esto no es json", content_type="text/plain")
    assert r.status_code == 400 and "JSON" in r.json["error"]


def test_put_y_delete_de_punto_inexistente(cliente):
    assert cliente.put("/api/puntos/99999", json={"nombre": "X"}).status_code == 404
    assert cliente.delete("/api/puntos/99999").status_code == 404
    assert cliente.get("/api/puntos/99999").json["error"] == "No existe un punto con ese ID."


def test_metodo_no_permitido_responde_json(cliente):
    r = cliente.patch("/api/puntos/1", json={})
    assert r.status_code == 405 and "error" in r.json
