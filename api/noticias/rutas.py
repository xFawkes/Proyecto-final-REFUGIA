"""Noticias: rutas de la API (los mismos pasos del tutorial: GET, POST, PUT y DELETE).

  GET    /api/noticias                → listar, buscar y filtrar (?q=sismo&verificacion=oficial&publicada=false)
  GET    /api/noticias/<id>           → una noticia
  POST   /api/noticias                → crear una noticia
  PUT    /api/noticias/<id>           → actualizar (se pueden enviar solo los campos que cambian)
  DELETE /api/noticias/<id>           → eliminar
  GET    /api/noticias/verificacion   → niveles de verificación (para el formulario)
  POST   /api/noticias/imagen         → subir una imagen (formulario multipart, campo "imagen")
"""

from __future__ import annotations

from flask import Blueprint, abort, jsonify, request
from marshmallow import ValidationError

from ..autenticacion import es_admin, exigir_admin, requiere_admin
from ..extensiones import db
from ..imagenes import borrar_imagen_subida, guardar_imagen_subida
from .esquemas import leer_filtros, noticia_entrada_schema, noticia_schema, noticias_schema
from .modelos import VERIFICACION, Noticia

bp = Blueprint("noticias", __name__, url_prefix="/api/noticias")


def leer_json() -> dict:
    """Como en el tutorial: request.get_json(force=True) lee el JSON enviado (ej. desde Postman)."""
    datos = request.get_json(force=True, silent=True)
    if not isinstance(datos, dict):
        abort(400, description="El cuerpo de la petición debe ser un objeto JSON.")
    return datos


def buscar_noticia(id) -> Noticia:
    return db.get_or_404(Noticia, id, description="No existe una noticia con ese ID.")


def quitar_otras_destacadas(noticia: Noticia) -> None:
    """Solo puede haber una noticia destacada: si esta lo es, las demás dejan de serlo."""
    if noticia.destacada:
        db.session.execute(
            db.update(Noticia).where(Noticia.id_noticia != noticia.id_noticia).values(destacada=False)
        )


def revisar_descripcion_imagen(noticia: Noticia) -> None:
    if noticia.imagen and not noticia.imagen_alt:
        db.session.rollback()
        raise ValidationError({"imagen_alt": ["Describe la imagen: es obligatorio cuando hay imagen."]})


# ---------------------------------------------------------------------------
# GET: consultar
# ---------------------------------------------------------------------------
@bp.route("", methods=["GET"])
def get_noticias():
    filtros = leer_filtros(request.args)  # valida ?q=…&verificacion=…&limite=…
    if filtros["publicada"] is not None or filtros["incluir_ocultas"]:
        exigir_admin()  # los borradores solo los ve el panel de administración
    consulta = db.select(Noticia)

    if filtros["publicada"] is not None:      # ?publicada=false → solo borradores
        consulta = consulta.where(Noticia.publicada.is_(filtros["publicada"]))
    elif not filtros["incluir_ocultas"]:      # por defecto la página pública solo ve las publicadas
        consulta = consulta.where(Noticia.publicada.is_(True))
    if filtros["verificacion"]:
        consulta = consulta.where(Noticia.verificacion.in_(filtros["verificacion"]))
    if filtros["destacada"] is not None:
        consulta = consulta.where(Noticia.destacada.is_(filtros["destacada"]))
    # Búsqueda: cada palabra debe aparecer en el título, el contenido o la fuente
    for palabra in (filtros["q"] or "").split():
        consulta = consulta.where(db.or_(
            Noticia.titulo.contains(palabra, autoescape=True),
            Noticia.contenido.contains(palabra, autoescape=True),
            Noticia.fuente.contains(palabra, autoescape=True),
        ))

    total = db.session.scalar(db.select(db.func.count()).select_from(consulta.subquery()))
    consulta = (
        consulta.order_by(Noticia.destacada.desc(), Noticia.fecha_publicacion.desc(), Noticia.id_noticia.desc())
        .limit(filtros["limite"]).offset(filtros["offset"])
    )
    resultados = db.session.scalars(consulta).all()
    return jsonify({
        "total": total,
        "limite": filtros["limite"],
        "offset": filtros["offset"],
        "resultados": noticias_schema.dump(resultados),
    })


@bp.route("/<int:id>", methods=["GET"])
def get_noticia(id):
    noticia = buscar_noticia(id)
    if not noticia.publicada and not es_admin():  # un borrador no existe para el público
        abort(404, description="No existe una noticia con ese ID.")
    return jsonify(noticia_schema.dump(noticia))


@bp.route("/verificacion", methods=["GET"])
def get_verificacion():
    return jsonify([{"clave": clave, "nombre": nombre} for clave, nombre in VERIFICACION.items()])


# ---------------------------------------------------------------------------
# POST: crear
# ---------------------------------------------------------------------------
@bp.route("", methods=["POST"])
@requiere_admin
def insert_noticia():
    datos = noticia_entrada_schema.load(leer_json())  # valida; si algo está mal responde 400 con el detalle
    nueva_noticia = Noticia(**datos)

    db.session.add(nueva_noticia)  # INSERT
    db.session.flush()             # asigna el id antes de revisar la destacada
    quitar_otras_destacadas(nueva_noticia)
    db.session.commit()            # ejecuta las sentencias
    return jsonify(noticia_schema.dump(nueva_noticia)), 201  # 201 = creado


# ---------------------------------------------------------------------------
# PUT: actualizar
# ---------------------------------------------------------------------------
@bp.route("/<int:id>", methods=["PUT"])
@requiere_admin
def update_noticia(id):
    actualizar_noticia = buscar_noticia(id)
    # partial=True: se pueden enviar solo los campos que cambian (ej. {"publicada": true} para aprobar un borrador)
    datos = noticia_entrada_schema.load(leer_json(), partial=True)
    for campo, valor in datos.items():
        setattr(actualizar_noticia, campo, valor)

    revisar_descripcion_imagen(actualizar_noticia)
    quitar_otras_destacadas(actualizar_noticia)
    db.session.commit()  # UPDATE
    return jsonify(noticia_schema.dump(actualizar_noticia))


# ---------------------------------------------------------------------------
# DELETE: eliminar
# ---------------------------------------------------------------------------
@bp.route("/<int:id>", methods=["DELETE"])
@requiere_admin
def delete_noticia(id):
    eliminar_noticia = buscar_noticia(id)
    respuesta = noticia_schema.dump(eliminar_noticia)  # se guarda antes de borrar, para devolverlo
    imagen = eliminar_noticia.imagen
    db.session.delete(eliminar_noticia)  # DELETE
    db.session.commit()
    # Si la imagen se subió desde el panel y ninguna otra noticia la usa, se borra el archivo
    en_uso = db.session.scalar(db.select(db.func.count()).select_from(Noticia).where(Noticia.imagen == imagen))
    borrar_imagen_subida("noticias", imagen, sigue_en_uso=bool(en_uso))
    return jsonify(respuesta)


# ---------------------------------------------------------------------------
# Subir imagen (desde el panel de administración)
# ---------------------------------------------------------------------------
@bp.route("/imagen", methods=["POST"])
@requiere_admin
def subir_imagen():
    """Guarda la imagen en img/subidas/noticias/ y responde su ruta, para enviarla luego en POST o PUT."""
    return jsonify({"imagen": guardar_imagen_subida("noticias")}), 201
