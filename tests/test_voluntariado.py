"""Pruebas de la API de voluntariado: consultas, CRUD, validaciones y subida de imágenes."""

import io

import pytest

PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c63f8cfc0f01f0005000201a5f2d4b30000000049454e44ae426082"
)

NUEVO = {
    "actividad": "Apoyo en ollas comunitarias",
    "organizacion": "Junta de Acción Comunal",
    "descripcion": "Prepara y sirve alimentos para familias damnificadas.",
    "requisitos": "Mayor de edad\nCarné de manipulación de alimentos",
    "modalidad": "presencial",
    "ubicacion": "Bogotá, Kennedy",
    "enlace": "https://example.org/inscripcion",
}


def test_listado_inicial(cliente):
    r = cliente.get("/api/voluntariados")
    assert r.status_code == 200
    assert r.json["total"] >= 6
    v = r.json["resultados"][0]
    assert v["estado"] == "activo"
    assert {"id_voluntariado", "actividad", "organizacion", "descripcion", "modalidad_nombre", "estado_nombre"} <= set(v)


def test_busqueda_y_filtros(cliente):
    assert cliente.get("/api/voluntariados?q=acopio").json["total"] == 1
    assert cliente.get("/api/voluntariados?q=voluntariado digital").json["total"] == 1
    assert cliente.get("/api/voluntariados?q=palabraquenoexiste").json["total"] == 0
    r = cliente.get("/api/voluntariados?modalidad=virtual")
    assert r.json["total"] >= 1 and all(v["modalidad"] == "virtual" for v in r.json["resultados"])
    r = cliente.get("/api/voluntariados?modalidad=presencial,mixta")
    assert all(v["modalidad"] in ("presencial", "mixta") for v in r.json["resultados"])
    r = cliente.get("/api/voluntariados?limite=2&offset=2")
    assert len(r.json["resultados"]) == 2 and r.json["offset"] == 2


def test_filtros_invalidos(cliente):
    r = cliente.get("/api/voluntariados?modalidad=teletransporte&estado=borrado&limite=500")
    assert r.status_code == 400
    assert {"modalidad", "estado", "limite"} <= set(r.json["detalles"])


def test_catalogos(cliente):
    r = cliente.get("/api/voluntariados/catalogos").json
    assert [m["clave"] for m in r["modalidades"]] == ["presencial", "virtual", "mixta"]
    assert [e["clave"] for e in r["estados"]] == ["activo", "cerrado"]


def test_crud_completo(cliente):
    # POST
    r = cliente.post("/api/voluntariados", json=NUEVO)
    assert r.status_code == 201, r.json
    id_ = r.json["id_voluntariado"]
    assert r.json["estado"] == "activo" and r.json["modalidad_nombre"] == "Presencial"
    # GET por id
    assert cliente.get(f"/api/voluntariados/{id_}").json["organizacion"] == "Junta de Acción Comunal"
    # PUT parcial
    r = cliente.put(f"/api/voluntariados/{id_}", json={"modalidad": "mixta"})
    assert r.status_code == 200 and r.json["modalidad"] == "mixta"
    assert r.json["actividad"] == NUEVO["actividad"]  # lo demás no cambia
    # DELETE
    r = cliente.delete(f"/api/voluntariados/{id_}")
    assert r.status_code == 200 and r.json["id_voluntariado"] == id_
    assert cliente.get(f"/api/voluntariados/{id_}").status_code == 404


def test_cerrados_no_se_ven_en_la_pagina_publica(cliente):
    id_ = cliente.post("/api/voluntariados", json=NUEVO).json["id_voluntariado"]
    cliente.put(f"/api/voluntariados/{id_}", json={"estado": "cerrado"})
    publicos = [v["id_voluntariado"] for v in cliente.get("/api/voluntariados?limite=100").json["resultados"]]
    cerrados = [v["id_voluntariado"] for v in cliente.get("/api/voluntariados?estado=cerrado").json["resultados"]]
    todos = [v["id_voluntariado"] for v in cliente.get("/api/voluntariados?estado=todos&limite=100").json["resultados"]]
    assert id_ not in publicos and id_ in cerrados and id_ in todos
    # Reabrir
    cliente.put(f"/api/voluntariados/{id_}", json={"estado": "activo"})
    assert id_ in [v["id_voluntariado"] for v in cliente.get("/api/voluntariados?limite=100").json["resultados"]]
    cliente.delete(f"/api/voluntariados/{id_}")


def test_virtual_no_necesita_ubicacion(cliente):
    datos = {**NUEVO, "modalidad": "virtual"}
    del datos["ubicacion"]
    r = cliente.post("/api/voluntariados", json=datos)
    assert r.status_code == 201 and r.json["ubicacion"] is None
    # Si pasa a presencial sin ubicación, la API lo rechaza y no guarda el cambio
    id_ = r.json["id_voluntariado"]
    r = cliente.put(f"/api/voluntariados/{id_}", json={"modalidad": "presencial"})
    assert r.status_code == 400 and "ubicacion" in r.json["detalles"]
    assert cliente.get(f"/api/voluntariados/{id_}").json["modalidad"] == "virtual"
    cliente.delete(f"/api/voluntariados/{id_}")


@pytest.mark.parametrize("datos, campo", [
    ({**NUEVO, "actividad": "   "}, "actividad"),
    ({**NUEVO, "descripcion": "corta"}, "descripcion"),
    ({**NUEVO, "enlace": "javascript:alert(1)"}, "enlace"),
    ({**NUEVO, "modalidad": "teletransporte"}, "modalidad"),
    ({**NUEVO, "estado": "borrador"}, "estado"),
    ({**NUEVO, "ubicacion": ""}, "ubicacion"),                       # presencial sin ubicación
    ({**NUEVO, "imagen": "img/x.png"}, "imagen_alt"),                # imagen sin descripción
    ({**NUEVO, "imagen": "img/../../.env", "imagen_alt": "x"}, "imagen"),
    ({**NUEVO, "campo_raro": 1}, "campo_raro"),
    ({k: v for k, v in NUEVO.items() if k != "organizacion"}, "organizacion"),
])
def test_validaciones(cliente, datos, campo):
    r = cliente.post("/api/voluntariados", json=datos)
    assert r.status_code == 400
    assert campo in r.json["detalles"]


def test_campos_vacios_del_formulario_se_guardan_como_null(cliente):
    r = cliente.post("/api/voluntariados", json={**NUEVO, "requisitos": "", "enlace": "  ", "imagen": "", "imagen_alt": ""})
    assert r.status_code == 201
    assert r.json["requisitos"] is None and r.json["enlace"] is None and r.json["imagen"] is None
    cliente.delete(f"/api/voluntariados/{r.json['id_voluntariado']}")


def test_errores_en_json_y_en_espanol(cliente):
    assert cliente.get("/api/voluntariados/99999").json == {"error": "No existe un voluntariado con ese ID."}
    assert cliente.delete("/api/voluntariados/99999").status_code == 404
    r = cliente.put("/api/voluntariados/1", data="[1, 2]", content_type="application/json")
    assert r.status_code == 400 and "JSON" in r.json["error"]


def test_subir_imagen_y_borrarla_con_el_voluntariado(app, cliente, tmp_path):
    app.config["CARPETA_SUBIDAS"] = tmp_path
    try:
        r = cliente.post("/api/voluntariados/imagen", data={"imagen": (io.BytesIO(PNG_1X1), "foto.png")})
        assert r.status_code == 201
        ruta = r.json["imagen"]
        assert ruta.startswith("img/subidas/voluntariado/") and ruta.endswith(".png")
        carpeta = tmp_path / "voluntariado"
        assert len(list(carpeta.iterdir())) == 1

        id_ = cliente.post("/api/voluntariados", json={**NUEVO, "imagen": ruta, "imagen_alt": "Foto de prueba"}).json["id_voluntariado"]
        cliente.delete(f"/api/voluntariados/{id_}")
        assert list(carpeta.iterdir()) == []  # el archivo se borra con el voluntariado
    finally:
        app.config.pop("CARPETA_SUBIDAS")


def test_subir_imagen_rechaza_archivos_que_no_son_imagen(app, cliente, tmp_path):
    app.config["CARPETA_SUBIDAS"] = tmp_path
    try:
        r = cliente.post("/api/voluntariados/imagen", data={"imagen": (io.BytesIO(b"<script>"), "foto.jpg")})
        assert r.status_code == 400
        assert not (tmp_path / "voluntariado").exists()
    finally:
        app.config.pop("CARPETA_SUBIDAS")


def test_paginas_cargan_los_scripts(cliente):
    publica = cliente.get("/voluntariado.html").get_data(as_text=True)
    assert 'src="js/api.js"' in publica and 'src="js/voluntariado.js"' in publica
    admin = cliente.get("/admin/voluntariados.html").get_data(as_text=True)
    assert 'src="../js/api.js"' in admin and 'src="../js/admin/voluntariados.js"' in admin
    for ruta in ("/js/voluntariado.js", "/js/admin/voluntariados.js"):
        assert cliente.get(ruta).status_code == 200
