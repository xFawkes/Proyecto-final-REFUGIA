"""Voluntariado: rutas de la API (los mismos pasos del tutorial: GET, POST, PUT y DELETE).

  GET    /api/voluntariados              → listar, buscar y filtrar (?q=acopio&modalidad=virtual&estado=todos)
  GET    /api/voluntariados/<id>         → un voluntariado
  POST   /api/voluntariados              → crear un voluntariado
  PUT    /api/voluntariados/<id>         → actualizar (se pueden enviar solo los campos que cambian)
  DELETE /api/voluntariados/<id>         → eliminar
  GET    /api/voluntariados/catalogos    → modalidades y estados (para formularios y filtros)
  POST   /api/voluntariados/imagen       → subir una imagen (formulario multipart, campo "imagen")
"""

from __future__ import annotations

from flask import Blueprint, abort, jsonify, request
from marshmallow import ValidationError

from ..autenticacion import exigir_admin, requiere_admin
from ..extensiones import db
from ..imagenes import borrar_imagen_subida, guardar_imagen_subida
from .esquemas import (leer_filtros, revisar_coherencia, voluntariado_entrada_schema, voluntariado_schema,
                       voluntariados_schema)
from .modelos import ESTADOS, MODALIDADES, Voluntariado

bp = Blueprint("voluntariado", __name__, url_prefix="/api/voluntariados")

CAMPOS_COHERENCIA = ("imagen", "imagen_alt", "modalidad", "ubicacion")


def leer_json() -> dict:
    """Como en el tutorial: request.get_json(force=True) lee el JSON enviado (ej. desde Postman)."""
    datos = request.get_json(force=True, silent=True)
    if not isinstance(datos, dict):
        abort(400, description="El cuerpo de la petición debe ser un objeto JSON.")
    return datos


def buscar_voluntariado(id) -> Voluntariado:
    return db.get_or_404(Voluntariado, id, description="No existe un voluntariado con ese ID.")


# ---------------------------------------------------------------------------
# GET: consultar
# ---------------------------------------------------------------------------
@bp.route("", methods=["GET"])
def get_voluntariados():
    filtros = leer_filtros(request.args)  # valida ?q=…&modalidad=…&estado=…
    if filtros["estado"] != "activo":
        exigir_admin()  # los cerrados solo los ve el panel de administración
    consulta = db.select(Voluntariado)

    if filtros["estado"] != "todos":
        consulta = consulta.where(Voluntariado.estado == filtros["estado"])
    if filtros["modalidad"]:
        consulta = consulta.where(Voluntariado.modalidad.in_(filtros["modalidad"]))
    # Búsqueda: cada palabra debe aparecer en la actividad, la organización, la descripción o la ubicación
    for palabra in (filtros["q"] or "").split():
        consulta = consulta.where(db.or_(
            Voluntariado.actividad.contains(palabra, autoescape=True),
            Voluntariado.organizacion.contains(palabra, autoescape=True),
            Voluntariado.descripcion.contains(palabra, autoescape=True),
            Voluntariado.ubicacion.contains(palabra, autoescape=True),
        ))

    total = db.session.scalar(db.select(db.func.count()).select_from(consulta.subquery()))
    consulta = (
        # Primero los activos, luego los más recientes
        consulta.order_by((Voluntariado.estado == "activo").desc(), Voluntariado.creado_en.desc(),
                          Voluntariado.id_voluntariado.desc())
        .limit(filtros["limite"]).offset(filtros["offset"])
    )
    resultados = db.session.scalars(consulta).all()
    return jsonify({
        "total": total,
        "limite": filtros["limite"],
        "offset": filtros["offset"],
        "resultados": voluntariados_schema.dump(resultados),
    })


@bp.route("/<int:id>", methods=["GET"])
def get_voluntariado(id):
    return jsonify(voluntariado_schema.dump(buscar_voluntariado(id)))


@bp.route("/catalogos", methods=["GET"])
def get_catalogos():
    return jsonify({
        "modalidades": [{"clave": clave, "nombre": nombre} for clave, nombre in MODALIDADES.items()],
        "estados": [{"clave": clave, "nombre": nombre} for clave, nombre in ESTADOS.items()],
    })


# ---------------------------------------------------------------------------
# POST: crear
# ---------------------------------------------------------------------------
@bp.route("", methods=["POST"])
@requiere_admin
def insert_voluntariado():
    datos = voluntariado_entrada_schema.load(leer_json())  # valida; si algo está mal responde 400 con el detalle
    nuevo_voluntariado = Voluntariado(**datos)
    db.session.add(nuevo_voluntariado)  # INSERT
    db.session.commit()                 # ejecuta la sentencia
    return jsonify(voluntariado_schema.dump(nuevo_voluntariado)), 201  # 201 = creado


# ---------------------------------------------------------------------------
# PUT: actualizar
# ---------------------------------------------------------------------------
@bp.route("/<int:id>", methods=["PUT"])
@requiere_admin
def update_voluntariado(id):
    actualizar_voluntariado = buscar_voluntariado(id)
    # partial=True: se pueden enviar solo los campos que cambian (ej. {"estado": "cerrado"})
    datos = voluntariado_entrada_schema.load(leer_json(), partial=True)
    for campo, valor in datos.items():
        setattr(actualizar_voluntariado, campo, valor)

    # Revisar las reglas entre campos con lo que quedó (lo enviado + lo que ya estaba guardado)
    errores = revisar_coherencia({c: getattr(actualizar_voluntariado, c) for c in CAMPOS_COHERENCIA})
    if errores:
        db.session.rollback()
        raise ValidationError(errores)

    db.session.commit()  # UPDATE
    return jsonify(voluntariado_schema.dump(actualizar_voluntariado))


# ---------------------------------------------------------------------------
# DELETE: eliminar
# ---------------------------------------------------------------------------
@bp.route("/<int:id>", methods=["DELETE"])
@requiere_admin
def delete_voluntariado(id):
    eliminar_voluntariado = buscar_voluntariado(id)
    respuesta = voluntariado_schema.dump(eliminar_voluntariado)  # se guarda antes de borrar, para devolverlo
    imagen = eliminar_voluntariado.imagen
    db.session.delete(eliminar_voluntariado)  # DELETE
    db.session.commit()
    # Si la imagen se subió desde el panel y ningún otro voluntariado la usa, se borra el archivo
    en_uso = db.session.scalar(
        db.select(db.func.count()).select_from(Voluntariado).where(Voluntariado.imagen == imagen)
    )
    borrar_imagen_subida("voluntariado", imagen, sigue_en_uso=bool(en_uso))
    return jsonify(respuesta)


# ---------------------------------------------------------------------------
# Subir imagen (desde el panel de administración)
# ---------------------------------------------------------------------------
@bp.route("/imagen", methods=["POST"])
@requiere_admin
def subir_imagen():
    """Guarda la imagen en img/subidas/voluntariado/ y responde su ruta, para enviarla luego en POST o PUT."""
    return jsonify({"imagen": guardar_imagen_subida("voluntariado")}), 201
