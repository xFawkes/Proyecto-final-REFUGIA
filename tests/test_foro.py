"""Pruebas de la API del foro: publicaciones, respuestas, validaciones, denuncias y moderación."""

import pytest

NUEVA = {
    "titulo": "Se necesitan voluntarios en Ciudad Bolívar",
    "contenido": "El comedor comunitario necesita manos para servir almuerzos el domingo.",
    "categoria": "necesidades",
    "ubicacion": "Bogotá, Ciudad Bolívar",
}
# El autor no se envía: es la persona que inició sesión (el cliente de las pruebas es el admin)
AUTOR_ADMIN = "Administración REFUGIA"


def crear(cliente, **extra):
    r = cliente.post("/api/foro/publicaciones", json={**NUEVA, **extra})
    assert r.status_code == 201, r.json
    return r.json["id_publicacion"]


def test_catalogos(cliente):
    r = cliente.get("/api/foro/catalogos").json
    assert "desaparecidos" in [c["clave"] for c in r["categorias"]]
    assert r["denuncias_para_ocultar"] == 3


def test_listado_inicial(cliente):
    r = cliente.get("/api/foro/publicaciones")
    assert r.status_code == 200 and r.json["total"] >= 5
    p = r.json["resultados"][0]
    assert {"titulo", "categoria_nombre", "total_respuestas", "ultima_actividad", "verificacion_nombre"} <= set(p)


def test_busqueda_y_filtros(cliente):
    assert cliente.get("/api/foro/publicaciones?q=cobijas").json["total"] == 1
    r = cliente.get("/api/foro/publicaciones?categoria=desaparecidos").json
    assert r["total"] >= 1 and all(p["categoria"] == "desaparecidos" for p in r["resultados"])
    r = cliente.get("/api/foro/publicaciones?verificacion=confirmada").json
    assert all(p["verificacion"] == "confirmada" for p in r["resultados"])
    assert cliente.get("/api/foro/publicaciones?categoria=chismes").status_code == 400


def test_crear_responder_y_detalle(cliente):
    id_ = crear(cliente)
    p = cliente.get(f"/api/foro/publicaciones/{id_}").json
    assert p["verificacion"] == "sin_confirmar" and p["respuestas"] == []
    assert "denuncias" not in p  # el público no ve las denuncias

    assert p["autor"] == AUTOR_ADMIN
    r = cliente.post(f"/api/foro/publicaciones/{id_}/respuestas", json={"contenido": "Yo puedo ir."})
    assert r.status_code == 201
    p = cliente.get(f"/api/foro/publicaciones/{id_}").json
    assert [x["autor"] for x in p["respuestas"]] == [AUTOR_ADMIN] and p["total_respuestas"] == 1
    # Al responder, la publicación sube al primer lugar del listado
    assert cliente.get("/api/foro/publicaciones?limite=1").json["resultados"][0]["id_publicacion"] == id_
    cliente.delete(f"/api/foro/publicaciones/{id_}")


def test_validar(cliente):
    id_ = crear(cliente)
    assert cliente.post(f"/api/foro/publicaciones/{id_}/validar").json["validaciones"] == 1
    assert cliente.post(f"/api/foro/publicaciones/{id_}/validar").json["validaciones"] == 2
    cliente.delete(f"/api/foro/publicaciones/{id_}")


def test_denuncias_ocultan_y_el_moderador_aprueba(cliente):
    id_ = crear(cliente)
    for i in range(3):
        r = cliente.post(f"/api/foro/publicaciones/{id_}/denuncias", json={"motivo": "falsa", "detalle": f"Denuncia {i}"})
        assert r.status_code == 201
    assert r.json["publicacion_oculta"] is True

    # Oculta: el público ya no la ve ni puede responder
    assert cliente.get(f"/api/foro/publicaciones/{id_}").status_code == 404
    assert id_ not in [p["id_publicacion"] for p in cliente.get("/api/foro/publicaciones?limite=100").json["resultados"]]
    assert cliente.post(f"/api/foro/publicaciones/{id_}/respuestas", json={"autor": "X", "contenido": "hola"}).status_code == 404

    # El moderador sí la ve, en "por revisar" y en "ocultas"
    pendientes = cliente.get("/api/foro/publicaciones?moderacion=true&revision=pendiente&limite=100").json["resultados"]
    assert pendientes[0]["id_publicacion"] == id_  # las denunciadas van primero
    assert id_ in [p["id_publicacion"] for p in cliente.get("/api/foro/publicaciones?moderacion=true&revision=ocultas").json["resultados"]]
    detalle = cliente.get(f"/api/foro/publicaciones/{id_}?moderacion=true").json
    assert len(detalle["denuncias"]) == 3 and detalle["denuncias_pendientes"] == 3

    # Aprobar: confirmada, visible y denuncias revisadas
    r = cliente.put(f"/api/foro/publicaciones/{id_}", json={"verificacion": "confirmada", "oculta": False})
    assert r.status_code == 200
    assert r.json["oculta"] is False and r.json["denuncias_pendientes"] == 0
    assert all(d["revisada"] for d in r.json["denuncias"])
    assert cliente.get(f"/api/foro/publicaciones/{id_}").status_code == 200
    assert id_ not in [p["id_publicacion"] for p in cliente.get("/api/foro/publicaciones?moderacion=true&revision=pendiente&limite=100").json["resultados"]]
    cliente.delete(f"/api/foro/publicaciones/{id_}")


def test_moderador_oculta_corrige_y_elimina(cliente):
    id_ = crear(cliente)
    r = cliente.put(f"/api/foro/publicaciones/{id_}", json={"oculta": True, "categoria": "general"})
    assert r.json["oculta"] is True and r.json["categoria"] == "general"
    assert cliente.put(f"/api/foro/publicaciones/{id_}", json={}).status_code == 400
    assert cliente.put(f"/api/foro/publicaciones/{id_}", json={"autor": "Otro"}).status_code == 400  # no se cambia el autor
    cliente.post(f"/api/foro/publicaciones/{id_}/denuncias", json={"motivo": "spam"})  # oculta: 404
    cliente.put(f"/api/foro/publicaciones/{id_}", json={"oculta": False})
    id_resp = cliente.post(f"/api/foro/publicaciones/{id_}/respuestas", json={"autor": "Ana", "contenido": "Spam"}).json["id_respuesta"]
    assert cliente.delete(f"/api/foro/respuestas/{id_resp}").status_code == 200
    assert cliente.delete(f"/api/foro/respuestas/{id_resp}").status_code == 404
    r = cliente.delete(f"/api/foro/publicaciones/{id_}")
    assert r.status_code == 200 and r.json["id_publicacion"] == id_
    assert cliente.get(f"/api/foro/publicaciones/{id_}?moderacion=true").status_code == 404


def test_eliminar_publicacion_borra_respuestas_y_denuncias(cliente, app):
    from api.extensiones import db
    from api.foro.modelos import Denuncia, Respuesta

    id_ = crear(cliente)
    cliente.post(f"/api/foro/publicaciones/{id_}/respuestas", json={"autor": "Ana", "contenido": "Hola"})
    cliente.post(f"/api/foro/publicaciones/{id_}/denuncias", json={"motivo": "otro"})
    cliente.delete(f"/api/foro/publicaciones/{id_}")
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count()).select_from(Respuesta).where(Respuesta.id_publicacion == id_)) == 0
        assert db.session.scalar(db.select(db.func.count()).select_from(Denuncia).where(Denuncia.id_publicacion == id_)) == 0


@pytest.mark.parametrize("datos, campo", [
    ({**NUEVA, "titulo": "Hola"}, "titulo"),
    ({**NUEVA, "contenido": "corto"}, "contenido"),
    ({**NUEVA, "categoria": "chismes"}, "categoria"),
    ({**NUEVA, "verificacion": "confirmada"}, "verificacion"),  # el público no puede confirmarse a sí mismo
    ({k: v for k, v in NUEVA.items() if k != "titulo"}, "titulo"),
])
def test_validaciones_publicacion(cliente, datos, campo):
    r = cliente.post("/api/foro/publicaciones", json=datos)
    assert r.status_code == 400 and campo in r.json["detalles"]


def test_validaciones_respuesta_y_denuncia(cliente):
    r = cliente.post("/api/foro/publicaciones/1/respuestas", json={"contenido": ""})
    assert r.status_code == 400 and "contenido" in r.json["detalles"]
    r = cliente.post("/api/foro/publicaciones/1/denuncias", json={"motivo": "aburrida"})
    assert r.status_code == 400 and "motivo" in r.json["detalles"]
    assert cliente.post("/api/foro/publicaciones/99999/validar").status_code == 404


def test_paginas(cliente):
    publica = cliente.get("/foro.html").get_data(as_text=True)
    assert 'src="js/foro.js"' in publica and 'id="foro-lista"' in publica
    admin = cliente.get("/admin/foro.html").get_data(as_text=True)
    assert 'src="../js/admin/foro.js"' in admin
    panel = cliente.get("/admin/inicio.html").get_data(as_text=True)
    assert 'id="tareas-pendientes"' in panel and "/api/foro/publicaciones?moderacion=true" in panel
