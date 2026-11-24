"""Subida de imágenes desde el panel de administración (la usan noticias, voluntariado…).

Las imágenes se guardan en img/subidas/<seccion>/ con un nombre aleatorio. Esa carpeta no
se sube a GitHub (.gitignore): cada integrante tiene las suyas, igual que su base de datos.

Uso en las rutas de una sección:
    from ..imagenes import borrar_imagen_subida, guardar_imagen_subida

    @bp.route("/imagen", methods=["POST"])
    def subir_imagen():
        return jsonify({"imagen": guardar_imagen_subida("voluntariado")}), 201
"""

from __future__ import annotations

import uuid
from pathlib import Path

from flask import abort, current_app, request

RAIZ_PROYECTO = Path(__file__).resolve().parents[1]
CARPETA_SUBIDAS = "img/subidas"
TAMANO_MAXIMO = 5 * 1024 * 1024  # 5 MB
FIRMAS_IMAGEN = {                # primeros bytes de cada formato
    b"\x89PNG\r\n\x1a\n": ".png",
    b"\xff\xd8\xff": ".jpg",
    b"GIF87a": ".gif",
    b"GIF89a": ".gif",
}

# Rutas de imagen permitidas al guardar un registro: una imagen del proyecto (img/…) o un enlace web
RUTA_IMAGEN = r"^(img/[\w\-/]+\.(png|jpe?g|webp|gif|avif)|https?://\S+)$"


def carpeta_seccion(seccion: str) -> Path:
    """Carpeta en disco. En las pruebas se cambia con app.config["CARPETA_SUBIDAS"]."""
    base = Path(current_app.config.get("CARPETA_SUBIDAS", RAIZ_PROYECTO / CARPETA_SUBIDAS))
    return base / seccion


def extension_por_contenido(contenido: bytes) -> str | None:
    """Revisa los primeros bytes: así no basta con cambiarle la extensión a un archivo para subirlo."""
    if contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return ".webp"
    for firma, extension in FIRMAS_IMAGEN.items():
        if contenido.startswith(firma):
            return extension
    return None


def guardar_imagen_subida(seccion: str, campo: str = "imagen") -> str:
    """Guarda la imagen enviada en un formulario multipart y devuelve su ruta (img/subidas/<seccion>/…)."""
    archivo = request.files.get(campo)
    if archivo is None or not archivo.filename:
        abort(400, description=f'Envía la imagen en un formulario multipart con el campo "{campo}".')

    contenido = archivo.stream.read(TAMANO_MAXIMO + 1)
    if len(contenido) > TAMANO_MAXIMO:
        abort(400, description="La imagen pesa más de 5 MB.")
    extension = extension_por_contenido(contenido)
    if extension is None:
        abort(400, description="Formato no permitido. Usa PNG, JPG, WEBP o GIF.")

    carpeta = carpeta_seccion(seccion)
    carpeta.mkdir(parents=True, exist_ok=True)
    nombre = f"{uuid.uuid4().hex}{extension}"  # nombre nuevo: evita choques y nombres peligrosos
    (carpeta / nombre).write_bytes(contenido)
    return f"{CARPETA_SUBIDAS}/{seccion}/{nombre}"


def borrar_imagen_subida(seccion: str, ruta: str | None, sigue_en_uso: bool = False) -> None:
    """Borra el archivo si se subió desde el panel (img/subidas/<seccion>/…) y ya nadie lo usa."""
    prefijo = f"{CARPETA_SUBIDAS}/{seccion}/"
    if not ruta or sigue_en_uso or not ruta.startswith(prefijo):
        return
    (carpeta_seccion(seccion) / Path(ruta).name).unlink(missing_ok=True)
