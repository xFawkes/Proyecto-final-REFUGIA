"""Rutas de la sección: GET, GET por id, POST, PUT y DELETE (como en el tutorial).

Diferencias con el tutorial, por la versión actual de las librerías:
  • Se usa un Blueprint (bp) en lugar de app, para que cada sección tenga su archivo.
  • db.get_or_404(Elemento, id) en lugar de Elemento.query.get(id): hace lo mismo
    y, si el id no existe, responde 404 en vez de fallar.

Para que solo los administradores puedan crear, editar o borrar (como en las demás secciones),
importa el decorador y ponlo debajo de @bp.route en POST, PUT y DELETE:

    from ..autenticacion import requiere_admin

    @bp.route("", methods=["POST"])
    @requiere_admin
    def insert_elemento(): ...
"""

from flask import Blueprint, abort, jsonify, request

from ..errores import traducir
from ..extensiones import db
from .esquemas import elemento_schema, elementos_schema
from .modelos import Elemento

bp = Blueprint("elementos", __name__, url_prefix="/api/elementos")


def leer_json() -> dict:
    datos = request.get_json(force=True, silent=True)  # lee el JSON enviado desde Postman o JavaScript
    if not isinstance(datos, dict):
        abort(400, description="El cuerpo de la petición debe ser un objeto JSON.")
    return datos


# GET: todos los elementos
@bp.route("", methods=["GET"])
def get_elementos():
    all_elementos = db.session.scalars(db.select(Elemento)).all()  # trae todos los registros
    result = elementos_schema.dump(all_elementos)                  # los convierte a lista de diccionarios
    return jsonify(result)                                         # responde en JSON


# GET por id: un solo elemento
@bp.route("/<int:id>", methods=["GET"])
def get_elemento(id):
    un_elemento = db.get_or_404(Elemento, id, description="No existe un elemento con ese ID.")
    return jsonify(elemento_schema.dump(un_elemento))


# POST: crear
@bp.route("", methods=["POST"])
def insert_elemento():
    datos = leer_json()
    errores = elemento_schema.validate(datos)  # devuelve los errores de validación (vacío si todo está bien)
    if errores:
        return jsonify({"error": "Los datos enviados no son válidos.", "detalles": traducir(errores)}), 400
    nuevo_elemento = Elemento(datos["titulo"], datos.get("descripcion"))
    db.session.add(nuevo_elemento)  # INSERT
    db.session.commit()             # ejecuta la sentencia
    return jsonify(elemento_schema.dump(nuevo_elemento)), 201


# PUT: actualizar
@bp.route("/<int:id>", methods=["PUT"])
def update_elemento(id):
    actualizar_elemento = db.get_or_404(Elemento, id, description="No existe un elemento con ese ID.")
    datos = leer_json()
    errores = elemento_schema.validate(datos)
    if errores:
        return jsonify({"error": "Los datos enviados no son válidos.", "detalles": traducir(errores)}), 400
    actualizar_elemento.titulo = datos["titulo"]
    actualizar_elemento.descripcion = datos.get("descripcion")
    db.session.commit()  # UPDATE
    return jsonify(elemento_schema.dump(actualizar_elemento))


# DELETE: eliminar
@bp.route("/<int:id>", methods=["DELETE"])
def delete_elemento(id):
    eliminar_elemento = db.get_or_404(Elemento, id, description="No existe un elemento con ese ID.")
    respuesta = elemento_schema.dump(eliminar_elemento)
    db.session.delete(eliminar_elemento)  # DELETE
    db.session.commit()
    return jsonify(respuesta)
