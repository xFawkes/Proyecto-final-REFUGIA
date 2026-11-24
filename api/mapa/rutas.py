"""Mapa: rutas de la API (siguiendo los pasos del tutorial: GET, POST, PUT y DELETE).

  GET    /api/puntos           → buscar y filtrar puntos
  GET    /api/puntos/<id>      → un punto
  POST   /api/puntos           → crear un punto
  PUT    /api/puntos/<id>      → actualizar un punto (se pueden enviar solo algunos campos)
  DELETE /api/puntos/<id>      → eliminar un punto
  GET    /api/tipos, /api/servicios, /api/verificacion → catálogos para los filtros
"""

from flask import Blueprint, abort, jsonify, request
from marshmallow import ValidationError

from ..extensiones import db
from .busqueda import a_diccionario, buscar_puntos, contar_por_tipo
from .catalogos import SERVICIOS, TIPOS, VERIFICACION
from .esquemas import leer_filtros, punto_entrada_schema
from .modelos import Punto

bp = Blueprint("mapa", __name__, url_prefix="/api")


def leer_json() -> dict:
    """Como en el tutorial: request.get_json(force=True) lee el JSON enviado (ej. desde Postman)."""
    datos = request.get_json(force=True, silent=True)
    if not isinstance(datos, dict):
        abort(400, description="El cuerpo de la petición debe ser un objeto JSON.")
    return datos


def ubicacion_usuario():
    try:
        lat, lng = request.args.get("lat", type=float), request.args.get("lng", type=float)
    except ValueError:
        return None, None
    return (lat, lng) if lat is not None and lng is not None else (None, None)


# ---------------------------------------------------------------------------
# GET: consultar
# ---------------------------------------------------------------------------
@bp.route("/puntos", methods=["GET"])
def get_puntos():
    filtros = leer_filtros(request.args)  # valida los parámetros (?q=…&tipo=…)
    total, resultados = buscar_puntos(filtros)
    return jsonify({"total": total, "limite": filtros["limite"], "offset": filtros["offset"], "resultados": resultados})


@bp.route("/puntos/<int:id>", methods=["GET"])
def get_punto(id):
    punto = db.get_or_404(Punto, id, description="No existe un punto con ese ID.")
    return jsonify(a_diccionario(punto, *ubicacion_usuario()))


# ---------------------------------------------------------------------------
# POST: crear
# ---------------------------------------------------------------------------
@bp.route("/puntos", methods=["POST"])
def insert_punto():
    datos = punto_entrada_schema.load(leer_json())  # valida; si algo está mal responde 400 con el detalle

    servicios = datos.pop("servicios", [])
    nuevo_punto = Punto(**datos)  # crea el objeto con los datos recibidos
    nuevo_punto.asignar_servicios(servicios)
    nuevo_punto.actualizar_texto_busqueda()

    db.session.add(nuevo_punto)  # INSERT
    db.session.commit()          # ejecuta la sentencia
    return jsonify(a_diccionario(nuevo_punto)), 201  # 201 = creado


# ---------------------------------------------------------------------------
# PUT: actualizar
# ---------------------------------------------------------------------------
@bp.route("/puntos/<int:id>", methods=["PUT"])
def update_punto(id):
    actualizar_punto = db.get_or_404(Punto, id, description="No existe un punto con ese ID.")
    # partial=True: se pueden enviar solo los campos que cambian (ej. {"cupos_disponibles": 10})
    datos = punto_entrada_schema.load(leer_json(), partial=True)

    if "servicios" in datos:
        actualizar_punto.asignar_servicios(datos.pop("servicios"))
    for campo, valor in datos.items():
        setattr(actualizar_punto, campo, valor)

    # Revisar cupos contra la capacidad ya guardada (por si solo llegó uno de los dos)
    cap, cupos = actualizar_punto.capacidad, actualizar_punto.cupos_disponibles
    if cap is not None and cupos is not None and cupos > cap:
        db.session.rollback()
        raise ValidationError({"cupos_disponibles": ["No puede haber más cupos disponibles que la capacidad."]})

    actualizar_punto.actualizar_texto_busqueda()
    db.session.commit()  # UPDATE
    return jsonify(a_diccionario(actualizar_punto))


# ---------------------------------------------------------------------------
# DELETE: eliminar
# ---------------------------------------------------------------------------
@bp.route("/puntos/<int:id>", methods=["DELETE"])
def delete_punto(id):
    eliminar_punto = db.get_or_404(Punto, id, description="No existe un punto con ese ID.")
    respuesta = a_diccionario(eliminar_punto)  # se guarda antes de borrar, para devolverlo
    db.session.delete(eliminar_punto)  # DELETE (sus servicios se borran también)
    db.session.commit()
    return jsonify(respuesta)


# ---------------------------------------------------------------------------
# Catálogos (para los filtros de la página)
# ---------------------------------------------------------------------------
@bp.route("/tipos", methods=["GET"])
def get_tipos():
    conteo = contar_por_tipo()
    return jsonify([
        {"clave": clave, "nombre": t["nombre"], "plural": t["plural"], "total": conteo[clave]}
        for clave, t in TIPOS.items()
    ])


@bp.route("/servicios", methods=["GET"])
def get_servicios():
    return jsonify([{"clave": clave, "nombre": nombre} for clave, nombre in SERVICIOS.items()])


@bp.route("/verificacion", methods=["GET"])
def get_verificacion():
    return jsonify([{"clave": clave, "nombre": nombre} for clave, nombre in VERIFICACION.items()])
