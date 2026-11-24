"""Pruebas de la API de donaciones: organizaciones (CRUD), donaciones y pasarela de pagos simulada."""

import io

import pytest

from api.donaciones.esquemas import cumple_luhn

PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c63f8cfc0f01f0005000201a5f2d4b30000000049454e44ae426082"
)

ORGANIZACION = {
    "nombre": "Fundación de prueba",
    "descripcion": "Organización creada en las pruebas automáticas.",
    "impacto": "probar que el CRUD funciona.",
    "enlace": "https://example.org",
}
DONACION = {"monto": 50000, "nombre_donante": "Ana Pérez", "correo": "Ana.Perez@correo.com"}
TARJETA_OK = {"titular": "Ana Pérez", "numero": "4242 4242 4242 4242", "vencimiento": "12/39", "cvv": "123"}
TARJETA_RECHAZADA = {**TARJETA_OK, "numero": "4000 0000 0000 0002"}


def crear_donacion(cliente, **extra):
    r = cliente.post("/api/donaciones", json={**DONACION, **extra})
    assert r.status_code == 201, r.json
    return r.json["referencia"]


def pagar(cliente, referencia, **pago):
    return cliente.post(f"/api/donaciones/{referencia}/pago", json=pago)


# ---------------------------------------------------------------------------
# Organizaciones
# ---------------------------------------------------------------------------
def test_organizaciones_iniciales(cliente):
    nombres = [o["nombre"] for o in cliente.get("/api/organizaciones").json]
    assert {"Cruz Roja Colombia", "UNICEF Colombia", "TECHO Colombia"} <= set(nombres)


def test_crud_organizaciones(cliente):
    r = cliente.post("/api/organizaciones", json=ORGANIZACION)
    assert r.status_code == 201, r.json
    id_ = r.json["id_organizacion"]
    assert r.json["activa"] is True
    assert cliente.get(f"/api/organizaciones/{id_}").json["nombre"] == ORGANIZACION["nombre"]

    r = cliente.put(f"/api/organizaciones/{id_}", json={"activa": False})
    assert r.status_code == 200 and r.json["activa"] is False
    assert id_ not in [o["id_organizacion"] for o in cliente.get("/api/organizaciones").json]
    assert id_ in [o["id_organizacion"] for o in cliente.get("/api/organizaciones?incluir_inactivas=true").json]

    assert cliente.delete(f"/api/organizaciones/{id_}").status_code == 200
    assert cliente.get(f"/api/organizaciones/{id_}").status_code == 404


def test_organizacion_nombre_repetido(cliente):
    r = cliente.post("/api/organizaciones", json={**ORGANIZACION, "nombre": "Cruz Roja Colombia"})
    assert r.status_code == 400 and "nombre" in r.json["detalles"]
    otra = cliente.post("/api/organizaciones", json={**ORGANIZACION, "nombre": "Otra fundación"}).json["id_organizacion"]
    r = cliente.put(f"/api/organizaciones/{otra}", json={"nombre": "UNICEF Colombia"})
    assert r.status_code == 400 and "nombre" in r.json["detalles"]
    cliente.delete(f"/api/organizaciones/{otra}")


@pytest.mark.parametrize("datos, campo", [
    ({**ORGANIZACION, "descripcion": "corta"}, "descripcion"),
    ({**ORGANIZACION, "enlace": "no-es-enlace"}, "enlace"),
    ({**ORGANIZACION, "imagen": "img/x.png"}, "imagen_alt"),
    ({k: v for k, v in ORGANIZACION.items() if k != "nombre"}, "nombre"),
])
def test_validaciones_organizacion(cliente, datos, campo):
    r = cliente.post("/api/organizaciones", json=datos)
    assert r.status_code == 400 and campo in r.json["detalles"]


def test_eliminar_organizacion_conserva_sus_donaciones(cliente):
    id_ = cliente.post("/api/organizaciones", json={**ORGANIZACION, "nombre": "Se eliminará"}).json["id_organizacion"]
    referencia = crear_donacion(cliente, id_organizacion=id_)
    pagar(cliente, referencia, metodo="tarjeta", tarjeta=TARJETA_OK)
    cliente.delete(f"/api/organizaciones/{id_}")
    donacion = cliente.get(f"/api/donaciones/{referencia}").json
    assert donacion["destino"] == "Se eliminará" and donacion["id_organizacion"] is None
    assert donacion["estado"] == "aprobada"


def test_subir_imagen_organizacion(app, cliente, tmp_path):
    app.config["CARPETA_SUBIDAS"] = tmp_path
    try:
        r = cliente.post("/api/organizaciones/imagen", data={"imagen": (io.BytesIO(PNG_1X1), "logo.png")})
        assert r.status_code == 201 and r.json["imagen"].startswith("img/subidas/donaciones/")
        id_ = cliente.post("/api/organizaciones", json={**ORGANIZACION, "nombre": "Con imagen", "imagen": r.json["imagen"],
                                                         "imagen_alt": "Logo"}).json["id_organizacion"]
        cliente.delete(f"/api/organizaciones/{id_}")
        assert list((tmp_path / "donaciones").iterdir()) == []
    finally:
        app.config.pop("CARPETA_SUBIDAS")


# ---------------------------------------------------------------------------
# Donaciones y pasarela simulada
# ---------------------------------------------------------------------------
def test_info_de_la_pasarela(cliente):
    r = cliente.get("/api/donaciones/pasarela").json
    assert r["simulada"] is True
    assert [m["clave"] for m in r["metodos"]] == ["tarjeta", "transferencia", "billetera"]
    assert any(t["resultado"] == "rechazada" for t in r["tarjetas_prueba"])


def test_flujo_completo_con_tarjeta(cliente):
    referencia = crear_donacion(cliente, id_organizacion=1, frecuencia="mensual")
    pendiente = cliente.get(f"/api/donaciones/{referencia}").json
    assert pendiente["estado"] == "pendiente" and pendiente["destino"] == "Cruz Roja Colombia"
    assert pendiente["correo"] == "a***@correo.com"  # el comprobante no muestra el correo completo

    r = pagar(cliente, referencia, metodo="tarjeta", tarjeta=TARJETA_OK)
    assert r.status_code == 200
    assert r.json["estado"] == "aprobada"
    assert r.json["detalle_pago"] == "Visa terminada en 4242"
    assert len(r.json["codigo_autorizacion"]) == 6 and r.json["pagado_en"]
    assert "4242424242424242" not in str(r.json)  # nunca se devuelve ni se guarda el número completo

    # No se puede pagar dos veces
    assert pagar(cliente, referencia, metodo="tarjeta", tarjeta=TARJETA_OK).status_code == 409


def test_pago_rechazado_y_reintento(cliente):
    referencia = crear_donacion(cliente)
    r = pagar(cliente, referencia, metodo="tarjeta", tarjeta=TARJETA_RECHAZADA)
    assert r.json["estado"] == "rechazada" and "fondos insuficientes" in r.json["mensaje_pasarela"]
    assert r.json["codigo_autorizacion"] is None
    r = pagar(cliente, referencia, metodo="transferencia", banco="banco_aprueba")
    assert r.json["estado"] == "aprobada" and r.json["metodo_pago"] == "transferencia"


@pytest.mark.parametrize("pago, aprobada", [
    ({"metodo": "transferencia", "banco": "banco_rechaza"}, False),
    ({"metodo": "billetera", "celular": "3001234567"}, True),
    ({"metodo": "billetera", "celular": "3009999999"}, False),
    ({"metodo": "tarjeta", "tarjeta": {**TARJETA_OK, "numero": "5555-5555-5555-4444"}}, True),
])
def test_medios_de_pago(cliente, pago, aprobada):
    referencia = crear_donacion(cliente)
    r = pagar(cliente, referencia, **pago)
    assert r.status_code == 200
    assert r.json["estado"] == ("aprobada" if aprobada else "rechazada")


@pytest.mark.parametrize("pago, campo", [
    ({"metodo": "tarjeta", "tarjeta": {**TARJETA_OK, "numero": "4111 1111 1111 1111"}}, "tarjeta"),  # real, no es de prueba
    ({"metodo": "tarjeta", "tarjeta": {**TARJETA_OK, "numero": "4242 4242 4242 4241"}}, "tarjeta"),  # no cumple Luhn
    ({"metodo": "tarjeta", "tarjeta": {**TARJETA_OK, "vencimiento": "01/20"}}, "tarjeta"),
    ({"metodo": "tarjeta", "tarjeta": {**TARJETA_OK, "cvv": "12"}}, "tarjeta"),
    ({"metodo": "tarjeta"}, "tarjeta"),
    ({"metodo": "transferencia", "banco": "bancolombia"}, "banco"),
    ({"metodo": "billetera", "celular": "3111111111"}, "celular"),
    ({"metodo": "billetera", "celular": "123"}, "celular"),
    ({"metodo": "efectivo"}, "metodo"),
])
def test_pagos_invalidos_no_cambian_la_donacion(cliente, pago, campo):
    referencia = crear_donacion(cliente)
    r = pagar(cliente, referencia, **pago)
    assert r.status_code == 400 and campo in r.json["detalles"]
    assert cliente.get(f"/api/donaciones/{referencia}").json["estado"] == "pendiente"


@pytest.mark.parametrize("datos, campo", [
    ({**DONACION, "monto": 9999}, "monto"),
    ({**DONACION, "monto": 20_000_001}, "monto"),
    ({**DONACION, "monto": "mucho"}, "monto"),
    ({**DONACION, "correo": "sin-arroba"}, "correo"),
    ({**DONACION, "frecuencia": "anual"}, "frecuencia"),
    ({**DONACION, "id_organizacion": 9999}, "id_organizacion"),
    ({k: v for k, v in DONACION.items() if k != "nombre_donante"}, "nombre_donante"),
])
def test_validaciones_donacion(cliente, datos, campo):
    r = cliente.post("/api/donaciones", json=datos)
    assert r.status_code == 400 and campo in r.json["detalles"]


def test_no_se_dona_a_organizacion_inactiva(cliente):
    id_ = cliente.post("/api/organizaciones", json={**ORGANIZACION, "nombre": "Inactiva", "activa": False}).json["id_organizacion"]
    r = cliente.post("/api/donaciones", json={**DONACION, "id_organizacion": id_})
    assert r.status_code == 400 and "id_organizacion" in r.json["detalles"]
    cliente.delete(f"/api/organizaciones/{id_}")


def test_listado_resumen_anular_y_eliminar(cliente):
    antes = cliente.get("/api/donaciones/resumen").json["total_recaudado"]
    aprobada = crear_donacion(cliente, monto=70000)
    pagar(cliente, aprobada, metodo="billetera", celular="3001234567")
    pendiente = crear_donacion(cliente, nombre_donante="Pendiente Única")

    assert cliente.get("/api/donaciones/resumen").json["total_recaudado"] == antes + 70000
    listado = cliente.get("/api/donaciones?estado=pendiente&q=Pendiente Única").json
    assert [d["referencia"] for d in listado["resultados"]] == [pendiente]
    assert listado["resultados"][0]["correo"] == "ana.perez@correo.com"  # el panel sí ve el correo

    # Una aprobada no se elimina: se anula
    assert cliente.delete(f"/api/donaciones/{aprobada}").status_code == 409
    r = cliente.put(f"/api/donaciones/{aprobada}", json={"estado": "anulada", "nota": "Prueba"})
    assert r.status_code == 200 and r.json["estado"] == "anulada"
    assert cliente.get("/api/donaciones/resumen").json["total_recaudado"] == antes
    assert cliente.delete(f"/api/donaciones/{aprobada}").status_code == 200

    # Una pendiente no se puede anular, pero sí eliminar
    assert cliente.put(f"/api/donaciones/{pendiente}", json={"estado": "anulada"}).status_code == 409
    assert cliente.put(f"/api/donaciones/{pendiente}", json={"estado": "aprobada"}).status_code == 400
    assert cliente.delete(f"/api/donaciones/{pendiente}").status_code == 200
    assert cliente.get(f"/api/donaciones/{pendiente}").status_code == 404


def test_errores(cliente):
    assert cliente.get("/api/donaciones/RFG-NOEXISTE").json == {"error": "No existe una donación con esa referencia."}
    assert cliente.post("/api/donaciones/RFG-NOEXISTE/pago", json={"metodo": "billetera"}).status_code == 404
    assert cliente.get("/api/donaciones?estado=regalada").status_code == 400


def test_luhn():
    assert cumple_luhn("4242424242424242") and cumple_luhn("5555555555554444")
    assert not cumple_luhn("4242424242424241")


def test_paginas(cliente):
    publica = cliente.get("/donaciones.html").get_data(as_text=True)
    assert 'src="js/donaciones.js"' in publica and 'id="plantilla-pasarela"' in publica
    admin = cliente.get("/admin/donaciones.html")
    assert admin.status_code == 200 and 'src="../js/admin/donaciones.js"' in admin.get_data(as_text=True)
    for pagina in ("inicio", "noticias", "foro", "voluntariados"):
        assert 'href="donaciones.html"' in cliente.get(f"/admin/{pagina}.html").get_data(as_text=True)
