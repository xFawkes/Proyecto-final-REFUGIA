"""Respuestas de error en JSON y traducción al español de los mensajes de Marshmallow."""

import re

from flask import Flask, jsonify, request
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException

# Mensajes de Marshmallow traducidos al español
TRADUCCIONES = {
    "Missing data for required field.": "Este campo es obligatorio.",
    "Field may not be null.": "Este campo no puede estar vacío.",
    "Unknown field.": "Campo desconocido. Revisa cómo está escrito.",
    "Not a valid number.": "Debe ser un número.",
    "Not a valid integer.": "Debe ser un número entero.",
    "Not a valid boolean.": "Debe ser true o false.",
    "Not a valid string.": "Debe ser texto.",
    "Not a valid list.": "Debe ser una lista [ ].",
    "Not a valid email address.": "Correo electrónico no válido.",
    "Not a valid URL.": "Dirección web no válida (debe empezar por http:// o https://).",
    "Invalid input type.": "Tipo de dato no válido.",
}
PATRONES = [
    (re.compile(r"^Must be one of: (.*)\.$"), r"Debe ser uno de: \1."),
    (re.compile(r"^Must be greater than or equal to (\S+) and less than or equal to (\S+)\.$"), r"Debe estar entre \1 y \2."),
    (re.compile(r"^Must be greater than or equal to (\S+)\.$"), r"Debe ser mayor o igual a \1."),
    (re.compile(r"^Must be greater than (\S+) and less than or equal to (\S+)\.$"), r"Debe ser mayor que \1 y menor o igual a \2."),
    (re.compile(r"^Length must be between (\d+) and (\d+)\.$"), r"Debe tener entre \1 y \2 caracteres."),
    (re.compile(r"^Shorter than minimum length (\d+)\.$"), r"Debe tener al menos \1 caracteres."),
    (re.compile(r"^Longer than maximum length (\d+)\.$"), r"Debe tener máximo \1 caracteres."),
]


# Mensajes por defecto de Flask cuando la ruta no da uno propio (ej. una URL que no existe)
MENSAJES_HTTP = {
    400: "La petición no es válida.",
    404: "La ruta solicitada no existe.",
    405: "Este método HTTP no está permitido en esta ruta.",
    413: "El archivo enviado es demasiado grande.",
    415: "Tipo de contenido no soportado.",
    500: "Error interno del servidor.",
}


def traducir(mensajes):
    if isinstance(mensajes, dict):
        return {k: traducir(v) for k, v in mensajes.items()}
    if isinstance(mensajes, list):
        return [traducir(m) for m in mensajes]
    if isinstance(mensajes, str):
        if mensajes in TRADUCCIONES:
            return TRADUCCIONES[mensajes]
        for patron, reemplazo in PATRONES:
            if patron.match(mensajes):
                return patron.sub(reemplazo, mensajes)
    return mensajes


def registrar_errores(app: Flask) -> None:
    """En /api/... los errores se responden en JSON (lo que espera Postman o el JavaScript)."""

    @app.errorhandler(ValidationError)
    def datos_invalidos(error: ValidationError):
        return jsonify({"error": "Los datos enviados no son válidos.", "detalles": traducir(error.messages)}), 400

    @app.errorhandler(HTTPException)
    def error_http(error: HTTPException):
        if request.path.startswith("/api/"):
            mensaje = error.description
            if mensaje == type(error).description:  # no se dio un mensaje propio: se usa el de español
                mensaje = MENSAJES_HTTP.get(error.code, mensaje)
            return jsonify({"error": mensaje}), error.code
        return error
