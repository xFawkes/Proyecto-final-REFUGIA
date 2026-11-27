"""Sesiones: quién hizo la petición y qué puede hacer (compartido por todas las secciones).

Cuando alguien inicia sesión (POST /api/sesion), Flask guarda su id en una cookie firmada
("session"). En cada petición se lee esa cookie para saber quién es.

Para proteger una ruta basta con ponerle un decorador encima:

    @bp.route("", methods=["POST"])
    @requiere_admin                 # solo administradores (si no: 401 o 403)
    def insert_noticia(): ...

    @bp.route("/publicaciones", methods=["POST"])
    @requiere_sesion                # cualquier persona que haya iniciado sesión
    def insert_publicacion(): ...

Y dentro de una ruta:  usuario_actual()  → el Usuario o None;  exigir_admin()  → aborta si no es admin.
"""

from __future__ import annotations

from functools import wraps

from flask import abort, g, session

from .extensiones import db

MENSAJE_SIN_SESION = "Inicia sesión para continuar."
MENSAJE_SOLO_ADMIN = "Solo un administrador puede hacer esto."


def iniciar_sesion(usuario) -> None:
    """Guarda en la cookie de sesión quién es (solo el id y la versión, nunca la contraseña)."""
    session.clear()
    session["id_usuario"] = usuario.id_usuario
    session["version"] = usuario.version_sesion
    session.permanent = True  # dura PERMANENT_SESSION_LIFETIME (ver api/config.py)
    g.usuario_actual = usuario


def cerrar_sesion() -> None:
    session.clear()
    g.usuario_actual = None


def usuario_actual():
    """El Usuario que hizo la petición, o None si no ha iniciado sesión.

    Se consulta en la base de datos en cada petición: si al usuario lo desactivaron o le
    cambiaron la contraseña, la sesión que tenía abierta deja de servir.
    """
    if "usuario_actual" in g:
        return g.usuario_actual
    from .usuarios.modelos import Usuario  # aquí para evitar importaciones circulares

    usuario = None
    id_usuario = session.get("id_usuario")
    if id_usuario is not None:
        usuario = db.session.get(Usuario, id_usuario)
        if usuario is None or not usuario.activo or usuario.version_sesion != session.get("version"):
            session.clear()
            usuario = None
    g.usuario_actual = usuario
    return usuario


def es_admin() -> bool:
    usuario = usuario_actual()
    return usuario is not None and usuario.es_admin


def exigir_sesion():
    usuario = usuario_actual()
    if usuario is None:
        abort(401, description=MENSAJE_SIN_SESION)
    return usuario


def exigir_admin():
    usuario = exigir_sesion()
    if not usuario.es_admin:
        abort(403, description=MENSAJE_SOLO_ADMIN)
    return usuario


def requiere_sesion(funcion):
    """Decorador: la ruta solo responde si hay una sesión iniciada (si no, 401)."""
    @wraps(funcion)
    def envoltura(*args, **kwargs):
        exigir_sesion()
        return funcion(*args, **kwargs)
    return envoltura


def requiere_admin(funcion):
    """Decorador: la ruta solo responde a administradores (401 sin sesión, 403 si no es admin)."""
    @wraps(funcion)
    def envoltura(*args, **kwargs):
        exigir_admin()
        return funcion(*args, **kwargs)
    return envoltura
