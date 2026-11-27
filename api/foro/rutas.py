"""Foro: rutas de la API (los mismos pasos del tutorial: GET, POST, PUT y DELETE).

Lo que usa cualquier persona (foro.html):
  GET    /api/foro/publicaciones                      → listar, buscar y filtrar (?q=…&categoria=…)
  GET    /api/foro/publicaciones/<id>                 → una publicación con sus respuestas
  POST   /api/foro/publicaciones                      → crear (queda "sin confirmar")
  POST   /api/foro/publicaciones/<id>/respuestas      → responder
  POST   /api/foro/publicaciones/<id>/validar         → "Yo confirmo esta información" (+1)
  POST   /api/foro/publicaciones/<id>/denuncias       → denunciar (con 3 sin revisar se oculta)
  GET    /api/foro/catalogos                          → categorías y motivos de denuncia

Lo que usa el moderador (admin/foro.html):
  GET    /api/foro/publicaciones?moderacion=true&revision=pendiente → lo que hay que revisar
  PUT    /api/foro/publicaciones/<id>                 → aprobar, ocultar o corregir
  DELETE /api/foro/publicaciones/<id>                 → eliminar (con sus respuestas y denuncias)
  DELETE /api/foro/respuestas/<id>                    → eliminar una respuesta
"""

from __future__ import annotations

from flask import Blueprint, abort, jsonify, request

from ..autenticacion import exigir_admin, requiere_admin, requiere_sesion, usuario_actual
from ..extensiones import db
from .esquemas import (denuncia_a_dict, denuncia_entrada_schema, leer_filtros, moderacion_schema,
                       publicacion_completa, publicacion_entrada_schema, publicaciones_schema,
                       respuesta_a_dict, respuesta_entrada_schema)
from .modelos import (CATEGORIAS, DENUNCIAS_PARA_OCULTAR, MOTIVOS_DENUNCIA, VERIFICACION, Denuncia, Publicacion,
                      Respuesta, ahora_colombia)

bp = Blueprint("foro", __name__, url_prefix="/api/foro")


def leer_json() -> dict:
    """Como en el tutorial: request.get_json(force=True) lee el JSON enviado (ej. desde Postman)."""
    datos = request.get_json(force=True, silent=True)
    if not isinstance(datos, dict):
        abort(400, description="El cuerpo de la petición debe ser un objeto JSON.")
    return datos


def es_moderacion() -> bool:
    moderacion = request.args.get("moderacion", "").lower() in ("true", "1", "si", "sí")
    if moderacion:
        exigir_admin()  # la vista de moderación es solo del panel de administración
    return moderacion


def leer_json_con_autor() -> dict:
    """El autor es la persona que inició sesión (no se puede publicar a nombre de otra)."""
    return {**leer_json(), "autor": usuario_actual().nombre_visible}


def buscar_publicacion(id, permitir_oculta: bool = False) -> Publicacion:
    publicacion = db.session.get(Publicacion, id)
    if publicacion is None or (publicacion.oculta and not permitir_oculta):
        abort(404, description="No existe una publicación con ese ID.")
    return publicacion


# ---------------------------------------------------------------------------
# GET: consultar
# ---------------------------------------------------------------------------
@bp.route("/catalogos", methods=["GET"])
def get_catalogos():
    return jsonify({
        "categorias": [{"clave": c, "nombre": n} for c, n in CATEGORIAS.items()],
        "verificacion": [{"clave": c, "nombre": n} for c, n in VERIFICACION.items()],
        "motivos_denuncia": [{"clave": c, "nombre": n} for c, n in MOTIVOS_DENUNCIA.items()],
        "denuncias_para_ocultar": DENUNCIAS_PARA_OCULTAR,
    })


@bp.route("/publicaciones", methods=["GET"])
def get_publicaciones():
    filtros = leer_filtros(request.args)
    if filtros["moderacion"]:
        exigir_admin()  # la vista de moderación es solo del panel de administración
    consulta = db.select(Publicacion)

    if not filtros["moderacion"]:
        consulta = consulta.where(Publicacion.oculta.is_(False))  # foro.html no ve las ocultas
    if filtros["categoria"]:
        consulta = consulta.where(Publicacion.categoria.in_(filtros["categoria"]))
    if filtros["verificacion"]:
        consulta = consulta.where(Publicacion.verificacion == filtros["verificacion"])

    tiene_denuncias = (
        db.select(Denuncia.id_denuncia)
        .where(Denuncia.id_publicacion == Publicacion.id_publicacion, Denuncia.revisada.is_(False))
        .exists()
    )
    if filtros["revision"] == "pendiente":  # sin confirmar, con denuncias por revisar u oculta
        consulta = consulta.where(db.or_(
            Publicacion.verificacion == "sin_confirmar", tiene_denuncias, Publicacion.oculta.is_(True)
        ))
    elif filtros["revision"] == "ocultas":
        consulta = consulta.where(Publicacion.oculta.is_(True))

    # Búsqueda: cada palabra debe aparecer en el título, el contenido, la ubicación o el autor
    for palabra in (filtros["q"] or "").split():
        consulta = consulta.where(db.or_(
            Publicacion.titulo.contains(palabra, autoescape=True),
            Publicacion.contenido.contains(palabra, autoescape=True),
            Publicacion.ubicacion.contains(palabra, autoescape=True),
            Publicacion.autor.contains(palabra, autoescape=True),
        ))

    total = db.session.scalar(db.select(db.func.count()).select_from(consulta.subquery()))
    if filtros["revision"]:
        orden = (tiene_denuncias.desc(), Publicacion.creado_en.desc())  # primero las denunciadas
    else:
        orden = (Publicacion.ultima_actividad.desc(),)                   # las de actividad más reciente
    consulta = (consulta.order_by(*orden, Publicacion.id_publicacion.desc())
                .limit(filtros["limite"]).offset(filtros["offset"]))
    return jsonify({
        "total": total,
        "limite": filtros["limite"],
        "offset": filtros["offset"],
        "resultados": publicaciones_schema.dump(db.session.scalars(consulta).all()),
    })


@bp.route("/publicaciones/<int:id>", methods=["GET"])
def get_publicacion(id):
    moderacion = es_moderacion()
    return jsonify(publicacion_completa(buscar_publicacion(id, permitir_oculta=moderacion), moderacion))


# ---------------------------------------------------------------------------
# POST: crear publicación, responder, validar y denunciar
# ---------------------------------------------------------------------------
@bp.route("/publicaciones", methods=["POST"])
@requiere_sesion
def insert_publicacion():
    datos = publicacion_entrada_schema.load(leer_json_con_autor())
    nueva_publicacion = Publicacion(**datos)  # queda "sin confirmar" hasta que la apruebe un moderador
    db.session.add(nueva_publicacion)         # INSERT
    db.session.commit()
    return jsonify(publicacion_completa(nueva_publicacion)), 201


@bp.route("/publicaciones/<int:id>/respuestas", methods=["POST"])
@requiere_sesion
def insert_respuesta(id):
    publicacion = buscar_publicacion(id)
    datos = respuesta_entrada_schema.load(leer_json_con_autor())
    nueva_respuesta = Respuesta(id_publicacion=id, **datos)
    db.session.add(nueva_respuesta)
    publicacion.ultima_actividad = ahora_colombia()  # el tema sube en el listado
    db.session.commit()
    return jsonify(respuesta_a_dict(nueva_respuesta)), 201


@bp.route("/publicaciones/<int:id>/validar", methods=["POST"])
def validar_publicacion(id):
    """Suma una validación ("yo también confirmo esta información").

    Sin inicio de sesión no se puede saber quién validó: la página evita que el mismo
    navegador valide dos veces. Con sesiones, se guardaría quién validó cada publicación.
    """
    publicacion = buscar_publicacion(id)
    publicacion.validaciones = Publicacion.validaciones + 1  # suma en la base de datos (sin carreras)
    db.session.commit()
    return jsonify({"id_publicacion": id, "validaciones": publicacion.validaciones})


@bp.route("/publicaciones/<int:id>/denuncias", methods=["POST"])
def insert_denuncia(id):
    publicacion = buscar_publicacion(id)
    datos = denuncia_entrada_schema.load(leer_json())
    nueva_denuncia = Denuncia(id_publicacion=id, **datos)
    db.session.add(nueva_denuncia)
    db.session.flush()
    db.session.refresh(publicacion)
    ocultada = False
    if publicacion.denuncias_pendientes >= DENUNCIAS_PARA_OCULTAR and not publicacion.oculta:
        publicacion.oculta = True  # se oculta hasta que un moderador la revise
        ocultada = True
    db.session.commit()
    return jsonify({**denuncia_a_dict(nueva_denuncia), "publicacion_oculta": ocultada}), 201


# ---------------------------------------------------------------------------
# PUT: moderar
# ---------------------------------------------------------------------------
@bp.route("/publicaciones/<int:id>", methods=["PUT"])
@requiere_admin
def update_publicacion(id):
    """El moderador puede aprobar ({"verificacion": "confirmada", "oculta": false}), ocultar o corregir.

    Al aprobar, las denuncias pendientes quedan marcadas como revisadas.
    """
    actualizar_publicacion = buscar_publicacion(id, permitir_oculta=True)
    datos = moderacion_schema.load(leer_json())
    for campo, valor in datos.items():
        setattr(actualizar_publicacion, campo, valor)
    if datos.get("verificacion") == "confirmada":
        for denuncia in actualizar_publicacion.denuncias:
            denuncia.revisada = True
    db.session.commit()  # UPDATE
    return jsonify(publicacion_completa(actualizar_publicacion, moderacion=True))


# ---------------------------------------------------------------------------
# DELETE: eliminar
# ---------------------------------------------------------------------------
@bp.route("/publicaciones/<int:id>", methods=["DELETE"])
@requiere_admin
def delete_publicacion(id):
    eliminar_publicacion = buscar_publicacion(id, permitir_oculta=True)
    respuesta = publicacion_completa(eliminar_publicacion, moderacion=True)
    db.session.delete(eliminar_publicacion)  # DELETE (sus respuestas y denuncias también)
    db.session.commit()
    return jsonify(respuesta)


@bp.route("/respuestas/<int:id>", methods=["DELETE"])
@requiere_admin
def delete_respuesta(id):
    eliminar_respuesta = db.get_or_404(Respuesta, id, description="No existe una respuesta con ese ID.")
    respuesta = respuesta_a_dict(eliminar_respuesta)
    db.session.delete(eliminar_respuesta)
    db.session.commit()
    return jsonify(respuesta)
