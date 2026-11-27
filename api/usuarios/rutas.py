"""Usuarios y sesiones: rutas de la API.

Sesión (iniciar y cerrar sesión):
  GET    /api/sesion                          → ¿quién soy? {"autenticado": true/false, "usuario": {...}}
  POST   /api/sesion                          → iniciar sesión {"usuario": "admin", "contrasena": "…"}
  DELETE /api/sesion                          → cerrar sesión

Cuenta propia (cualquier persona):
  POST   /api/usuarios                        → crear cuenta (registro) e iniciar sesión
  PUT    /api/usuarios/yo                     → editar mis datos (Mi perfil)          [con sesión]
  PUT    /api/usuarios/yo/contrasena          → cambiar mi contraseña                  [con sesión]

Panel de administración (solo administradores):
  GET    /api/usuarios                        → listar y buscar (?q=ana&rol=administrador&activo=true)
  GET    /api/usuarios/<id>                   → un usuario
  PUT    /api/usuarios/<id>                   → cambiar rol, activar/desactivar o editar datos
  DELETE /api/usuarios/<id>                   → eliminar
  POST   /api/usuarios/<id>/contrasena-temporal → genera una contraseña temporal (si la olvidó)
  GET    /api/usuarios/catalogos              → roles (para formularios y filtros)
"""

from __future__ import annotations

import secrets

from flask import Blueprint, abort, jsonify, request
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from ..autenticacion import (cerrar_sesion, exigir_admin, iniciar_sesion, requiere_admin, requiere_sesion,
                             usuario_actual)
from ..extensiones import db
from .esquemas import (cambio_contrasena_schema, inicio_sesion_schema, leer_filtros, perfil_schema,
                       registro_schema, usuario_admin_schema, usuario_schema, usuarios_schema)
from .modelos import ROLES, Usuario, ahora_colombia

bp = Blueprint("usuarios", __name__, url_prefix="/api")

# Hash de relleno: si el usuario no existe se revisa la contraseña contra este, para que la
# respuesta tarde lo mismo y no se pueda adivinar qué usuarios existen midiendo el tiempo.
HASH_RELLENO = generate_password_hash("relleno-refugia")
MENSAJE_DATOS_INCORRECTOS = "Usuario o contraseña incorrectos."


def leer_json() -> dict:
    """Como en el tutorial: request.get_json(force=True) lee el JSON enviado (ej. desde Postman)."""
    datos = request.get_json(force=True, silent=True)
    if not isinstance(datos, dict):
        abort(400, description="El cuerpo de la petición debe ser un objeto JSON.")
    return datos


def error_datos(detalles: dict):
    """Mismo formato que los errores de validación de Marshmallow."""
    return jsonify({"error": "Los datos enviados no son válidos.", "detalles": detalles}), 400


def buscar_usuario(id) -> Usuario:
    return db.get_or_404(Usuario, id, description="No existe un usuario con ese ID.")


def datos_repetidos(datos: dict, sin_contar: int | None = None) -> dict:
    """Revisa que el nombre de usuario y el correo no los tenga otra cuenta."""
    errores = {}
    for campo, mensaje in (("nombre_usuario", "Ese nombre de usuario ya está en uso. Prueba con otro."),
                           ("correo", "Ya existe una cuenta con ese correo.")):
        if not datos.get(campo):
            continue
        consulta = db.select(Usuario.id_usuario).where(getattr(Usuario, campo) == datos[campo])
        if sin_contar is not None:
            consulta = consulta.where(Usuario.id_usuario != sin_contar)
        if db.session.scalar(consulta) is not None:
            errores[campo] = [mensaje]
    return errores


def guardar_cambios() -> None:
    """commit(); si dos personas registran el mismo usuario a la vez, responde 400 en vez de 500."""
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(400, description="El nombre de usuario o el correo ya están en uso.")


def pagina_inicial(usuario: Usuario) -> str:
    """A dónde llevar a la persona después de iniciar sesión."""
    return "admin/inicio.html" if usuario.es_admin else "inicio.html"


def respuesta_sesion(usuario: Usuario, mensaje: str):
    return {"mensaje": mensaje, "usuario": usuario_schema.dump(usuario), "redireccion": pagina_inicial(usuario)}


# ===========================================================================
# SESIÓN
# ===========================================================================
@bp.route("/sesion", methods=["GET"])
def get_sesion():
    usuario = usuario_actual()
    return jsonify({"autenticado": usuario is not None,
                    "usuario": usuario_schema.dump(usuario) if usuario else None})


@bp.route("/sesion", methods=["POST"])
def iniciar():
    datos = inicio_sesion_schema.load(leer_json())
    usuario = db.session.scalar(db.select(Usuario).where(
        db.or_(Usuario.nombre_usuario == datos["usuario"], Usuario.correo == datos["usuario"])
    ))
    if usuario is None:
        check_password_hash(HASH_RELLENO, datos["contrasena"])  # mismo tiempo de respuesta
        abort(401, description=MENSAJE_DATOS_INCORRECTOS)
    if not usuario.revisar_contrasena(datos["contrasena"]):
        abort(401, description=MENSAJE_DATOS_INCORRECTOS)
    if not usuario.activo:
        abort(403, description="Esta cuenta está desactivada. Comunícate con un administrador de REFUGIA.")

    usuario.ultimo_acceso = ahora_colombia()
    db.session.commit()
    iniciar_sesion(usuario)
    return jsonify(respuesta_sesion(usuario, f"Hola, {usuario.nombre_visible}."))


@bp.route("/sesion", methods=["DELETE"])
def cerrar():
    cerrar_sesion()
    return jsonify({"mensaje": "Cerraste sesión."})


# ===========================================================================
# CUENTA PROPIA
# ===========================================================================
@bp.route("/usuarios", methods=["POST"])
def registrar():
    datos = registro_schema.load(leer_json())  # valida; si algo está mal responde 400 con el detalle
    errores = datos_repetidos(datos)
    if errores:
        return error_datos(errores)

    contrasena = datos.pop("contrasena")
    nuevo_usuario = Usuario(**datos, rol="usuario")  # el registro siempre crea usuarios comunes
    nuevo_usuario.cambiar_contrasena(contrasena)
    nuevo_usuario.ultimo_acceso = ahora_colombia()
    db.session.add(nuevo_usuario)  # INSERT
    guardar_cambios()
    iniciar_sesion(nuevo_usuario)  # queda con la sesión iniciada
    return jsonify(respuesta_sesion(nuevo_usuario, f"¡Bienvenida o bienvenido a REFUGIA, {nuevo_usuario.nombre_visible}!")), 201


@bp.route("/usuarios/yo", methods=["PUT"])
@requiere_sesion
def update_mi_perfil():
    usuario = usuario_actual()
    datos = perfil_schema.load(leer_json(), partial=True)
    errores = datos_repetidos(datos, sin_contar=usuario.id_usuario)
    if errores:
        return error_datos(errores)
    for campo, valor in datos.items():
        setattr(usuario, campo, valor)
    guardar_cambios()
    return jsonify(usuario_schema.dump(usuario))


@bp.route("/usuarios/yo/contrasena", methods=["PUT"])
@requiere_sesion
def update_mi_contrasena():
    usuario = usuario_actual()
    datos = cambio_contrasena_schema.load(leer_json())
    if not usuario.revisar_contrasena(datos["actual"]):
        return error_datos({"actual": ["La contraseña actual no es correcta."]})
    if datos["actual"] == datos["nueva"]:
        return error_datos({"nueva": ["La nueva contraseña debe ser diferente a la actual."]})
    usuario.cambiar_contrasena(datos["nueva"])  # cierra las sesiones abiertas en otros dispositivos…
    db.session.commit()
    iniciar_sesion(usuario)                      # …pero no esta
    return jsonify({"mensaje": "Tu contraseña se cambió."})


# ===========================================================================
# PANEL DE ADMINISTRACIÓN
# ===========================================================================
@bp.route("/usuarios/catalogos", methods=["GET"])
def get_catalogos():
    return jsonify({"roles": [{"clave": clave, "nombre": nombre} for clave, nombre in ROLES.items()]})


@bp.route("/usuarios", methods=["GET"])
@requiere_admin
def get_usuarios():
    filtros = leer_filtros(request.args)  # valida ?q=…&rol=…&activo=…
    consulta = db.select(Usuario)
    if filtros["rol"]:
        consulta = consulta.where(Usuario.rol == filtros["rol"])
    if filtros["activo"] is not None:
        consulta = consulta.where(Usuario.activo.is_(filtros["activo"]))
    for palabra in (filtros["q"] or "").split():
        consulta = consulta.where(db.or_(
            Usuario.nombre_usuario.contains(palabra.lower(), autoescape=True),
            Usuario.correo.contains(palabra.lower(), autoescape=True),
            Usuario.nombre.contains(palabra, autoescape=True),
        ))

    total = db.session.scalar(db.select(db.func.count()).select_from(consulta.subquery()))
    consulta = (
        # Primero los administradores, luego por nombre de usuario
        consulta.order_by((Usuario.rol == "administrador").desc(), Usuario.nombre_usuario)
        .limit(filtros["limite"]).offset(filtros["offset"])
    )
    return jsonify({
        "total": total,
        "limite": filtros["limite"],
        "offset": filtros["offset"],
        "resultados": usuarios_schema.dump(db.session.scalars(consulta).all()),
    })


@bp.route("/usuarios/<int:id>", methods=["GET"])
@requiere_admin
def get_usuario(id):
    return jsonify(usuario_schema.dump(buscar_usuario(id)))


@bp.route("/usuarios/<int:id>", methods=["PUT"])
@requiere_admin
def update_usuario(id):
    actualizar_usuario = buscar_usuario(id)
    datos = usuario_admin_schema.load(leer_json(), partial=True)

    # Un administrador no puede quitarse el rol ni desactivarse: el panel podría quedar sin nadie
    if actualizar_usuario.id_usuario == exigir_admin().id_usuario and (
        datos.get("rol", "administrador") != "administrador" or datos.get("activo", True) is False
    ):
        abort(409, description="No puedes quitarte el rol de administrador ni desactivar tu propia cuenta.")

    errores = datos_repetidos(datos, sin_contar=actualizar_usuario.id_usuario)
    if errores:
        return error_datos(errores)

    if datos.get("activo") is False and actualizar_usuario.activo:
        actualizar_usuario.version_sesion += 1  # se le cierra la sesión que tenga abierta
    for campo, valor in datos.items():
        setattr(actualizar_usuario, campo, valor)
    guardar_cambios()  # UPDATE
    return jsonify(usuario_schema.dump(actualizar_usuario))


@bp.route("/usuarios/<int:id>", methods=["DELETE"])
@requiere_admin
def delete_usuario(id):
    eliminar_usuario = buscar_usuario(id)
    if eliminar_usuario.id_usuario == usuario_actual().id_usuario:
        abort(409, description="No puedes eliminar tu propia cuenta desde el panel.")
    respuesta = usuario_schema.dump(eliminar_usuario)  # se guarda antes de borrar, para devolverlo
    db.session.delete(eliminar_usuario)  # DELETE
    db.session.commit()
    return jsonify(respuesta)


# Sin letras ni números que se confundan al dictarla (0/O, 1/l/I)
CARACTERES_TEMPORAL = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generar_contrasena_temporal(largo: int = 10) -> str:
    while True:
        contrasena = "".join(secrets.choice(CARACTERES_TEMPORAL) for _ in range(largo))
        if any(c.isdigit() for c in contrasena) and any(c.isalpha() for c in contrasena):
            return contrasena


@bp.route("/usuarios/<int:id>/contrasena-temporal", methods=["POST"])
@requiere_admin
def crear_contrasena_temporal(id):
    """Para quien olvidó su contraseña: el administrador se la entrega y la persona la cambia en Mi perfil."""
    usuario = buscar_usuario(id)
    temporal = generar_contrasena_temporal()
    usuario.cambiar_contrasena(temporal)  # también cierra las sesiones que tenga abiertas
    db.session.commit()
    if usuario.id_usuario == usuario_actual().id_usuario:
        iniciar_sesion(usuario)  # si es la propia cuenta, no se cierra esta sesión
    return jsonify({
        "mensaje": f"Entrégale esta contraseña a {usuario.nombre_visible}. No se volverá a mostrar.",
        "contrasena_temporal": temporal,
    })
