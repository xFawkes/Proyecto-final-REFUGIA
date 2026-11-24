"""Pruebas de la API de noticias: consultas, CRUD, validaciones y subida de imágenes."""

import io

import pytest

PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c63f8cfc0f01f0005000201a5f2d4b30000000049454e44ae426082"
)

NUEVA = {
    "titulo": "Alerta por lluvias en Bogotá",
    "contenido": "El IDIGER recomienda evitar zonas de ladera.\n\nSegundo párrafo.",
    "fuente": "IDIGER",
    "enlace": "https://www.idiger.gov.co",
    "verificacion": "oficial",
}


def test_listado_inicial(cliente):
    r = cliente.get("/api/noticias")
    assert r.status_code == 200
    assert r.json["total"] >= 5
    primera = r.json["resultados"][0]
    assert primera["destacada"] is True  # la destacada va primero
    assert {"id_noticia", "titulo", "contenido", "fuente", "verificacion_nombre", "fecha_publicacion"} <= set(primera)


def test_busqueda_y_filtros(cliente):
    assert cliente.get("/api/noticias?q=Caldas").json["total"] == 1
    assert cliente.get("/api/noticias?q=sismo agosto").json["total"] >= 1
    assert cliente.get("/api/noticias?q=palabraquenoexiste").json["total"] == 0
    r = cliente.get("/api/noticias?verificacion=en_verificacion")
    assert all(n["verificacion"] == "en_verificacion" for n in r.json["resultados"])
    r = cliente.get("/api/noticias?limite=2&offset=1")
    assert len(r.json["resultados"]) == 2 and r.json["offset"] == 1


def test_filtros_invalidos(cliente):
    r = cliente.get("/api/noticias?verificacion=inventada&limite=0")
    assert r.status_code == 400
    assert {"verificacion", "limite"} <= set(r.json["detalles"])


def test_catalogo_verificacion(cliente):
    claves = [v["clave"] for v in cliente.get("/api/noticias/verificacion").json]
    assert claves == ["oficial", "en_verificacion", "sin_verificar"]


def test_crud_completo(cliente):
    # POST
    r = cliente.post("/api/noticias", json=NUEVA)
    assert r.status_code == 201, r.json
    id_ = r.json["id_noticia"]
    assert r.json["publicada"] is True and r.json["destacada"] is False
    # GET por id
    assert cliente.get(f"/api/noticias/{id_}").json["fuente"] == "IDIGER"
    # PUT parcial
    r = cliente.put(f"/api/noticias/{id_}", json={"verificacion": "en_verificacion"})
    assert r.status_code == 200 and r.json["verificacion"] == "en_verificacion"
    assert r.json["titulo"] == NUEVA["titulo"]  # lo demás no cambia
    # DELETE
    r = cliente.delete(f"/api/noticias/{id_}")
    assert r.status_code == 200 and r.json["id_noticia"] == id_
    assert cliente.get(f"/api/noticias/{id_}").status_code == 404


def test_borradores_no_se_ven_en_la_pagina_publica(cliente):
    id_ = cliente.post("/api/noticias", json={**NUEVA, "publicada": False}).json["id_noticia"]
    publicas = [n["id_noticia"] for n in cliente.get("/api/noticias?limite=100").json["resultados"]]
    borradores = [n["id_noticia"] for n in cliente.get("/api/noticias?publicada=false").json["resultados"]]
    todas = [n["id_noticia"] for n in cliente.get("/api/noticias?incluir_ocultas=true&limite=100").json["resultados"]]
    assert id_ not in publicas and id_ in borradores and id_ in todas
    # Aprobar
    cliente.put(f"/api/noticias/{id_}", json={"publicada": True})
    assert id_ in [n["id_noticia"] for n in cliente.get("/api/noticias?limite=100").json["resultados"]]
    cliente.delete(f"/api/noticias/{id_}")


def test_solo_una_destacada(cliente):
    anterior = cliente.get("/api/noticias?destacada=true").json["resultados"][0]["id_noticia"]
    nueva = cliente.post("/api/noticias", json={**NUEVA, "destacada": True}).json["id_noticia"]
    destacadas = cliente.get("/api/noticias?destacada=true").json["resultados"]
    assert [n["id_noticia"] for n in destacadas] == [nueva]
    # Se devuelve la destacada original para no afectar otras pruebas
    cliente.put(f"/api/noticias/{anterior}", json={"destacada": True})
    cliente.delete(f"/api/noticias/{nueva}")


@pytest.mark.parametrize("datos, campo", [
    ({**NUEVA, "titulo": "   "}, "titulo"),
    ({**NUEVA, "enlace": "ftp://algo"}, "enlace"),
    ({**NUEVA, "verificacion": "rumor"}, "verificacion"),
    ({**NUEVA, "imagen": "img/x.png"}, "imagen_alt"),             # imagen sin descripción
    ({**NUEVA, "imagen": "../.env", "imagen_alt": "x"}, "imagen"),  # ruta peligrosa
    ({**NUEVA, "fecha_publicacion": "20-10-2026"}, "fecha_publicacion"),
    ({**NUEVA, "campo_raro": 1}, "campo_raro"),
    ({k: v for k, v in NUEVA.items() if k != "fuente"}, "fuente"),
])
def test_validaciones(cliente, datos, campo):
    r = cliente.post("/api/noticias", json=datos)
    assert r.status_code == 400
    assert campo in r.json["detalles"]


def test_put_valida_imagen_con_lo_guardado(cliente):
    id_ = cliente.post("/api/noticias", json=NUEVA).json["id_noticia"]
    r = cliente.put(f"/api/noticias/{id_}", json={"imagen": "img/noticias/portada.png"})
    assert r.status_code == 400 and "imagen_alt" in r.json["detalles"]
    assert cliente.get(f"/api/noticias/{id_}").json["imagen"] is None  # no se guardó nada
    cliente.delete(f"/api/noticias/{id_}")


def test_campos_vacios_del_formulario_se_guardan_como_null(cliente):
    r = cliente.post("/api/noticias", json={**NUEVA, "enlace": "", "imagen": "", "imagen_alt": " "})
    assert r.status_code == 201
    assert r.json["enlace"] is None and r.json["imagen"] is None
    cliente.delete(f"/api/noticias/{r.json['id_noticia']}")


def test_errores_en_json_y_en_espanol(cliente):
    assert cliente.get("/api/noticias/99999").json == {"error": "No existe una noticia con ese ID."}
    assert cliente.put("/api/noticias/99999", json={}).status_code == 404
    r = cliente.post("/api/noticias", data="no es json", content_type="application/json")
    assert r.status_code == 400 and "JSON" in r.json["error"]
    r = cliente.patch("/api/noticias/1")
    assert r.status_code == 405 and r.json["error"] == "Este método HTTP no está permitido en esta ruta."


def test_subir_imagen_y_borrarla_con_la_noticia(app, cliente, tmp_path):
    app.config["CARPETA_SUBIDAS_NOTICIAS"] = tmp_path
    try:
        r = cliente.post("/api/noticias/imagen", data={"imagen": (io.BytesIO(PNG_1X1), "foto.png")})
        assert r.status_code == 201
        ruta = r.json["imagen"]
        assert ruta.startswith("img/subidas/noticias/") and ruta.endswith(".png")
        assert len(list(tmp_path.iterdir())) == 1

        id_ = cliente.post("/api/noticias", json={**NUEVA, "imagen": ruta, "imagen_alt": "Foto de prueba"}).json["id_noticia"]
        cliente.delete(f"/api/noticias/{id_}")
        assert list(tmp_path.iterdir()) == []  # el archivo se borra con la noticia
    finally:
        app.config.pop("CARPETA_SUBIDAS_NOTICIAS")


@pytest.mark.parametrize("contenido, nombre", [
    (b"<?php echo 'hola'; ?>", "foto.png"),   # no es una imagen aunque diga .png
    (b"MZ\x90\x00", "programa.jpg"),
])
def test_subir_imagen_rechaza_archivos_que_no_son_imagen(app, cliente, tmp_path, contenido, nombre):
    app.config["CARPETA_SUBIDAS_NOTICIAS"] = tmp_path
    try:
        r = cliente.post("/api/noticias/imagen", data={"imagen": (io.BytesIO(contenido), nombre)})
        assert r.status_code == 400
        assert list(tmp_path.iterdir()) == []
    finally:
        app.config.pop("CARPETA_SUBIDAS_NOTICIAS")


def test_subir_imagen_sin_archivo(cliente):
    assert cliente.post("/api/noticias/imagen").status_code == 400


def test_paginas_cargan_los_scripts(cliente):
    publica = cliente.get("/noticias.html").get_data(as_text=True)
    assert 'src="js/api.js"' in publica and 'src="js/noticias.js"' in publica
    admin = cliente.get("/admin/noticias.html").get_data(as_text=True)
    assert 'src="../js/api.js"' in admin and 'src="../js/admin/noticias.js"' in admin
    for ruta in ("/js/api.js", "/js/noticias.js", "/js/admin/noticias.js", "/js/admin/panel.js"):
        assert cliente.get(ruta).status_code == 200
