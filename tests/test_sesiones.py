"""Pruebas de usuarios y sesiones: iniciar/cerrar sesión, registro, perfil, panel de usuarios
y la protección de las rutas de las demás secciones."""

import pytest

from conftest import iniciar_sesion


def nueva_cuenta(app, nombre_usuario, **extra):
    """Registra una cuenta nueva y devuelve el cliente con su sesión iniciada."""
    cliente = app.test_client()
    datos = {"nombre_usuario": nombre_usuario, "correo": f"{nombre_usuario}@prueba.test",
             "contrasena": "Segura123", **extra}
    r = cliente.post("/api/usuarios", json=datos)
    assert r.status_code == 201, r.json
    return cliente, r.json["usuario"]


# ---------------------------------------------------------------------------
# Iniciar y cerrar sesión
# ---------------------------------------------------------------------------
def test_sin_sesion(anonimo):
    assert anonimo.get("/api/sesion").json == {"autenticado": False, "usuario": None}


def test_admin_va_al_panel(anonimo):
    r = anonimo.post("/api/sesion", json={"usuario": "admin", "contrasena": "Admin2026*"})
    assert r.status_code == 200
    assert r.json["redireccion"] == "admin/inicio.html" and r.json["usuario"]["rol"] == "administrador"
    assert "contrasena" not in r.json["usuario"]  # nunca se envía la contraseña (ni su hash)
    assert "HttpOnly" in r.headers["Set-Cookie"] and "SameSite=Lax" in r.headers["Set-Cookie"]
    sesion = anonimo.get("/api/sesion").json
    assert sesion["autenticado"] and sesion["usuario"]["nombre_usuario"] == "admin"
    assert sesion["usuario"]["ultimo_acceso"] is not None


def test_usuario_va_al_inicio_y_puede_entrar_con_correo(anonimo):
    r = anonimo.post("/api/sesion", json={"usuario": "  Ana.Gomez@Refugia.test ", "contrasena": "Usuario2026*"})
    assert r.status_code == 200 and r.json["redireccion"] == "inicio.html"


@pytest.mark.parametrize("usuario, contrasena", [
    ("admin", "otra-clave1"),        # contraseña incorrecta
    ("no.existe", "Admin2026*"),      # usuario que no existe
])
def test_datos_incorrectos_mismo_mensaje(anonimo, usuario, contrasena):
    r = anonimo.post("/api/sesion", json={"usuario": usuario, "contrasena": contrasena})
    # El mismo mensaje en los dos casos: no se revela qué usuarios existen
    assert r.status_code == 401 and r.json["error"] == "Usuario o contraseña incorrectos."
    assert anonimo.get("/api/sesion").json["autenticado"] is False


def test_cuenta_desactivada(anonimo):
    r = anonimo.post("/api/sesion", json={"usuario": "cuenta.inactiva", "contrasena": "Usuario2026*"})
    assert r.status_code == 403 and "desactivada" in r.json["error"]


def test_inicio_sesion_valida_campos(anonimo):
    r = anonimo.post("/api/sesion", json={"usuario": "", "contrasena": ""})
    assert r.status_code == 400 and {"usuario", "contrasena"} <= set(r.json["detalles"])
    assert anonimo.post("/api/sesion", data="no es json").status_code == 400


def test_cerrar_sesion(usuario_comun):
    assert usuario_comun.delete("/api/sesion").status_code == 200
    assert usuario_comun.get("/api/sesion").json["autenticado"] is False
    assert usuario_comun.put("/api/usuarios/yo", json={"nombre": "Otra"}).status_code == 401


# ---------------------------------------------------------------------------
# Registro
# ---------------------------------------------------------------------------
def test_registro_crea_usuario_comun_e_inicia_sesion(app):
    cliente = app.test_client()
    r = cliente.post("/api/usuarios", json={
        "nombre_usuario": " Maria.Perez ", "correo": "MARIA@Prueba.test", "contrasena": "Segura123",
        "rol": "administrador",  # no se acepta: el registro siempre crea usuarios comunes
    })
    assert r.status_code == 400 and "rol" in r.json["detalles"]  # campo desconocido

    r = cliente.post("/api/usuarios", json={
        "nombre_usuario": " Maria.Perez ", "correo": "MARIA@Prueba.test", "contrasena": "Segura123"})
    assert r.status_code == 201
    u = r.json["usuario"]
    assert (u["nombre_usuario"], u["correo"], u["rol"]) == ("maria.perez", "maria@prueba.test", "usuario")
    assert r.json["redireccion"] == "inicio.html"
    assert cliente.get("/api/sesion").json["usuario"]["id_usuario"] == u["id_usuario"]
    # Puede volver a entrar con su contraseña
    iniciar_sesion(app.test_client(), "maria.perez", "Segura123")


@pytest.mark.parametrize("cambio, campo", [
    ({"nombre_usuario": "ab"}, "nombre_usuario"),             # muy corto
    ({"nombre_usuario": "con espacio"}, "nombre_usuario"),
    ({"nombre_usuario": "josé"}, "nombre_usuario"),            # tildes no
    ({"correo": "sin-arroba"}, "correo"),
    ({"contrasena": "corta1"}, "contrasena"),                  # menos de 8
    ({"contrasena": "solamenteletras"}, "contrasena"),         # sin números
    ({"contrasena": "12345678"}, "contrasena"),                # sin letras
    ({"nombre_usuario": "admin"}, "nombre_usuario"),           # ya existe
    ({"nombre_usuario": "ADMIN"}, "nombre_usuario"),           # ya existe (mayúsculas no cuentan)
    ({"correo": "Admin@refugia.test"}, "correo"),              # ya existe
])
def test_registro_validaciones(anonimo, cambio, campo):
    datos = {"nombre_usuario": "valido.1", "correo": "valido1@prueba.test", "contrasena": "Segura123", **cambio}
    r = anonimo.post("/api/usuarios", json=datos)
    assert r.status_code == 400 and campo in r.json["detalles"], r.json


# ---------------------------------------------------------------------------
# Mi perfil
# ---------------------------------------------------------------------------
def test_editar_mi_perfil(app):
    cliente, u = nueva_cuenta(app, "perfil.prueba")
    r = cliente.put("/api/usuarios/yo", json={"nombre": "Pepa Prueba", "telefono": "300 123 4567",
                                              "ubicacion": " Pasto ", "correo": "Pepa@Prueba.test"})
    assert r.status_code == 200
    assert (r.json["nombre"], r.json["ubicacion"], r.json["correo"]) == ("Pepa Prueba", "Pasto", "pepa@prueba.test")
    assert r.json["nombre_visible"] == "Pepa Prueba"
    # "" borra los opcionales; el rol no se puede cambiar desde el perfil
    r = cliente.put("/api/usuarios/yo", json={"telefono": ""})
    assert r.status_code == 200 and r.json["telefono"] is None
    assert cliente.put("/api/usuarios/yo", json={"rol": "administrador"}).status_code == 400
    r = cliente.put("/api/usuarios/yo", json={"telefono": "llámame"})
    assert r.status_code == 400 and "telefono" in r.json["detalles"]
    r = cliente.put("/api/usuarios/yo", json={"correo": "admin@refugia.test"})  # correo de otra cuenta
    assert r.status_code == 400 and "correo" in r.json["detalles"]


def test_cambiar_mi_contrasena_cierra_otras_sesiones(app):
    cliente, _ = nueva_cuenta(app, "clave.prueba")
    otro_dispositivo = iniciar_sesion(app.test_client(), "clave.prueba", "Segura123")

    r = cliente.put("/api/usuarios/yo/contrasena", json={"actual": "incorrecta1", "nueva": "Nueva12345"})
    assert r.status_code == 400 and "actual" in r.json["detalles"]
    r = cliente.put("/api/usuarios/yo/contrasena", json={"actual": "Segura123", "nueva": "Segura123"})
    assert r.status_code == 400 and "nueva" in r.json["detalles"]
    assert cliente.put("/api/usuarios/yo/contrasena", json={"actual": "Segura123", "nueva": "corta"}).status_code == 400

    assert cliente.put("/api/usuarios/yo/contrasena", json={"actual": "Segura123", "nueva": "Nueva12345"}).status_code == 200
    assert cliente.get("/api/sesion").json["autenticado"] is True             # esta sesión sigue
    assert otro_dispositivo.get("/api/sesion").json["autenticado"] is False   # la otra se cerró
    iniciar_sesion(app.test_client(), "clave.prueba", "Nueva12345")


# ---------------------------------------------------------------------------
# Panel de usuarios (administrador)
# ---------------------------------------------------------------------------
def test_listar_y_buscar_usuarios(cliente):
    r = cliente.get("/api/usuarios").json
    assert r["total"] >= 5 and r["resultados"][0]["rol"] == "administrador"  # primero los admin
    assert all("contrasena" not in u for u in r["resultados"])
    assert cliente.get("/api/usuarios?q=ana.gomez").json["total"] == 1
    assert all(u["rol"] == "administrador" for u in cliente.get("/api/usuarios?rol=administrador").json["resultados"])
    assert [u["nombre_usuario"] for u in cliente.get("/api/usuarios?activo=false").json["resultados"]] == ["cuenta.inactiva"]
    assert cliente.get("/api/usuarios?rol=jefe").status_code == 400
    assert cliente.get("/api/usuarios?q=&rol=&activo=").json["total"] >= 5  # vacíos = sin filtro (Postman)
    assert cliente.get("/api/usuarios/99999").status_code == 404
    assert [r["clave"] for r in cliente.get("/api/usuarios/catalogos").json["roles"]] == ["usuario", "administrador"]


def test_admin_cambia_rol_y_desactiva(app, cliente):
    otro, u = nueva_cuenta(app, "promovida")
    assert otro.get("/api/usuarios").status_code == 403

    r = cliente.put(f"/api/usuarios/{u['id_usuario']}", json={"rol": "administrador"})
    assert r.status_code == 200 and r.json["rol_nombre"] == "Administrador"
    assert otro.get("/api/usuarios").status_code == 200  # el cambio de rol aplica de inmediato

    assert cliente.put(f"/api/usuarios/{u['id_usuario']}", json={"activo": False}).status_code == 200
    assert otro.get("/api/sesion").json["autenticado"] is False  # se le cerró la sesión
    r = app.test_client().post("/api/sesion", json={"usuario": "promovida", "contrasena": "Segura123"})
    assert r.status_code == 403

    assert cliente.put(f"/api/usuarios/{u['id_usuario']}", json={"rol": "jefe"}).status_code == 400
    assert cliente.put(f"/api/usuarios/{u['id_usuario']}", json={"correo": "admin@refugia.test"}).status_code == 400


def test_admin_no_puede_bloquearse(cliente):
    yo = cliente.get("/api/sesion").json["usuario"]["id_usuario"]
    assert cliente.put(f"/api/usuarios/{yo}", json={"rol": "usuario"}).status_code == 409
    assert cliente.put(f"/api/usuarios/{yo}", json={"activo": False}).status_code == 409
    assert cliente.delete(f"/api/usuarios/{yo}").status_code == 409
    assert cliente.put(f"/api/usuarios/{yo}", json={"ubicacion": "Bogotá"}).status_code == 200


def test_contrasena_temporal_y_eliminar(app, cliente):
    otro, u = nueva_cuenta(app, "olvidadiza")
    r = cliente.post(f"/api/usuarios/{u['id_usuario']}/contrasena-temporal")
    assert r.status_code == 200
    temporal = r.json["contrasena_temporal"]
    assert len(temporal) == 10 and any(c.isdigit() for c in temporal)
    assert otro.get("/api/sesion").json["autenticado"] is False       # la sesión anterior se cerró
    iniciar_sesion(app.test_client(), "olvidadiza", temporal)         # entra con la temporal

    assert cliente.delete(f"/api/usuarios/{u['id_usuario']}").json["nombre_usuario"] == "olvidadiza"
    assert cliente.get(f"/api/usuarios/{u['id_usuario']}").status_code == 404
    assert app.test_client().post("/api/sesion", json={"usuario": "olvidadiza", "contrasena": temporal}).status_code == 401


# ---------------------------------------------------------------------------
# Protección de las demás secciones
# ---------------------------------------------------------------------------
SOLO_ADMIN = [
    ("POST", "/api/noticias"), ("PUT", "/api/noticias/1"), ("DELETE", "/api/noticias/1"),
    ("POST", "/api/noticias/imagen"), ("GET", "/api/noticias?publicada=false"),
    ("GET", "/api/noticias?incluir_ocultas=true"),
    ("POST", "/api/voluntariados"), ("PUT", "/api/voluntariados/1"), ("DELETE", "/api/voluntariados/1"),
    ("POST", "/api/voluntariados/imagen"), ("GET", "/api/voluntariados?estado=todos"),
    ("POST", "/api/organizaciones"), ("PUT", "/api/organizaciones/1"), ("DELETE", "/api/organizaciones/1"),
    ("POST", "/api/organizaciones/imagen"), ("GET", "/api/organizaciones?incluir_inactivas=true"),
    ("GET", "/api/donaciones"), ("GET", "/api/donaciones/resumen"),
    ("PUT", "/api/donaciones/RFG-AAAAAAAA"), ("DELETE", "/api/donaciones/RFG-AAAAAAAA"),
    ("GET", "/api/foro/publicaciones?moderacion=true"), ("GET", "/api/foro/publicaciones/1?moderacion=true"),
    ("PUT", "/api/foro/publicaciones/1"), ("DELETE", "/api/foro/publicaciones/1"),
    ("DELETE", "/api/foro/respuestas/1"),
    ("POST", "/api/puntos"), ("PUT", "/api/puntos/1"), ("DELETE", "/api/puntos/1"),
    ("GET", "/api/usuarios"), ("GET", "/api/usuarios/1"), ("PUT", "/api/usuarios/1"),
    ("DELETE", "/api/usuarios/1"), ("POST", "/api/usuarios/1/contrasena-temporal"),
]


@pytest.mark.parametrize("metodo, ruta", SOLO_ADMIN)
def test_rutas_solo_admin(anonimo, usuario_comun, metodo, ruta):
    assert anonimo.open(ruta, method=metodo, json={}).status_code == 401
    r = usuario_comun.open(ruta, method=metodo, json={})
    assert r.status_code == 403 and r.json["error"] == "Solo un administrador puede hacer esto."


PUBLICAS = [
    "/api/noticias", "/api/noticias/1", "/api/voluntariados", "/api/organizaciones",
    "/api/donaciones/pasarela", "/api/foro/publicaciones", "/api/foro/publicaciones/1",
    "/api/puntos", "/api/usuarios/catalogos",
]


@pytest.mark.parametrize("ruta", PUBLICAS)
def test_consultas_publicas_sin_sesion(anonimo, ruta):
    assert anonimo.get(ruta).status_code == 200


def test_borrador_no_es_publico(cliente, anonimo):
    r = cliente.post("/api/noticias", json={
        "titulo": "Borrador de prueba de sesiones", "contenido": "Contenido de prueba suficiente.",
        "fuente": "REFUGIA", "verificacion": "en_verificacion", "publicada": False})
    assert r.status_code == 201, r.json
    id_ = r.json["id_noticia"]
    assert anonimo.get(f"/api/noticias/{id_}").status_code == 404
    assert cliente.get(f"/api/noticias/{id_}").status_code == 200
    cliente.delete(f"/api/noticias/{id_}")


def test_foro_publicar_requiere_sesion_y_usa_su_nombre(anonimo, usuario_comun):
    nueva = {"titulo": "Prueba de autor con sesión", "contenido": "Mensaje para probar el autor.",
             "categoria": "general", "autor": "Me hago pasar por otra persona"}
    r = anonimo.post("/api/foro/publicaciones", json=nueva)
    assert r.status_code == 401
    r = usuario_comun.post("/api/foro/publicaciones", json=nueva)
    assert r.status_code == 201 and r.json["autor"] == "Ana Gómez"
    id_ = r.json["id_publicacion"]
    assert anonimo.post(f"/api/foro/publicaciones/{id_}/respuestas", json={"contenido": "Hola"}).status_code == 401
    # Validar y denunciar siguen abiertos (no necesitan cuenta)
    assert anonimo.post(f"/api/foro/publicaciones/{id_}/validar").status_code == 200
    assert usuario_comun.delete(f"/api/foro/publicaciones/{id_}").status_code == 403


# ---------------------------------------------------------------------------
# Páginas protegidas (cuando Flask sirve el sitio)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("pagina", ["/admin/inicio.html", "/admin/usuarios.html", "/Admin/Inicio.HTML", "/perfil.html"])
def test_paginas_protegidas_sin_sesion(anonimo, pagina):
    r = anonimo.get(pagina)
    if pagina.startswith("/Admin"):
        assert r.status_code in (302, 404)  # nunca se entrega sin sesión
        return
    assert r.status_code == 302 and r.headers["Location"] == f"/iniciar-sesion.html?siguiente={pagina}"


def test_paginas_segun_rol(usuario_comun, cliente):
    assert usuario_comun.get("/perfil.html").status_code == 200
    assert usuario_comun.get("/admin/inicio.html").status_code == 302  # no es admin
    assert cliente.get("/admin/inicio.html").status_code == 200
    for pagina in ("/iniciar-sesion.html", "/registro.html"):
        assert usuario_comun.get(pagina).status_code == 200


def test_clave_secreta_no_se_publica(anonimo):
    assert anonimo.get("/.clave_secreta").status_code == 404
