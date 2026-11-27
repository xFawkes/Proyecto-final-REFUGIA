"""Sirve las páginas del sitio (HTML, CSS, JS e imágenes) desde el mismo servidor de la API.

Solo se publican las carpetas y extensiones del frontend: nunca .env, el código
de la API, las pruebas ni el entorno virtual.

Las páginas del panel (admin/) solo se entregan a administradores, y perfil.html solo a
quien inició sesión: a los demás se les lleva a iniciar-sesion.html. (Con Live Server esta
revisión la hace js/sesion.js; los datos los protege la API en cualquier caso.)
"""

from pathlib import Path
from urllib.parse import quote

from flask import Blueprint, abort, redirect, send_from_directory

from .autenticacion import usuario_actual
from .config import RAIZ_PROYECTO

bp = Blueprint("paginas", __name__)

CARPETAS_PUBLICAS = {"css", "js", "img", "admin"}
EXTENSIONES_RAIZ = {".html", ".webmanifest", ".ico", ".png", ".svg"}
ARCHIVOS_RAIZ = {"sw.js", "service-worker.js", "manifest.json"}


@bp.route("/")
def inicio():
    return redirect("/inicio.html")


def pide_iniciar_sesion(ruta: str):
    """Si la página necesita sesión (o ser admin) y no la hay, responde la redirección al login."""
    minusculas = ruta.lower()  # en Windows "Admin/Inicio.HTML" también abre el archivo
    es_admin_html = minusculas.startswith("admin/") and minusculas.endswith(".html")
    if not es_admin_html and minusculas != "perfil.html":
        return None
    usuario = usuario_actual()
    if usuario is not None and (usuario.es_admin or not es_admin_html):
        return None
    return redirect(f"/iniciar-sesion.html?siguiente={quote('/' + ruta)}")


@bp.route("/<path:ruta>", methods=["GET", "HEAD"])
def archivo(ruta: str):
    partes = Path(ruta).parts
    if ".." in partes or "\\" in ruta:
        abort(404)  # nunca salir de las carpetas públicas (ej. /css/../.env)
    redireccion = pide_iniciar_sesion(ruta)
    if redireccion is not None:
        return redireccion
    if len(partes) > 1 and partes[0] in CARPETAS_PUBLICAS:
        # Se sirve desde la carpeta pública misma: send_from_directory no deja salir de ella
        return send_from_directory(RAIZ_PROYECTO / partes[0], "/".join(partes[1:]))
    if len(partes) == 1 and (Path(ruta).suffix.lower() in EXTENSIONES_RAIZ or ruta in ARCHIVOS_RAIZ):
        if (RAIZ_PROYECTO / ruta).is_file():
            return send_from_directory(RAIZ_PROYECTO, ruta)
        if ruta.endswith(".html"):
            return send_from_directory(RAIZ_PROYECTO, "error.html"), 404  # página 404 del proyecto
    abort(404)
