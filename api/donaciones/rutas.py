"""Donaciones: rutas de la API (los mismos pasos del tutorial: GET, POST, PUT y DELETE).

Organizaciones (ONG que reciben donaciones):
  GET    /api/organizaciones               → listar (?incluir_inactivas=true para el panel)
  GET    /api/organizaciones/<id>          → una organización
  POST   /api/organizaciones               → crear
  PUT    /api/organizaciones/<id>          → actualizar (se pueden enviar solo los campos que cambian)
  DELETE /api/organizaciones/<id>          → eliminar (sus donaciones se conservan)
  POST   /api/organizaciones/imagen        → subir una imagen (multipart, campo "imagen")

Donaciones y pasarela de pagos SIMULADA (ver pasarela.py):
  POST   /api/donaciones                   → 1. crear la donación (queda "pendiente")
  POST   /api/donaciones/<referencia>/pago → 2. pagar (responde "aprobada" o "rechazada")
  GET    /api/donaciones/<referencia>      → 3. comprobante
  GET    /api/donaciones                   → listar y filtrar (panel de administración)
  GET    /api/donaciones/resumen           → totales para el panel
  GET    /api/donaciones/pasarela          → medios de pago y datos de prueba
  PUT    /api/donaciones/<referencia>      → anular una donación aprobada o agregar una nota
  DELETE /api/donaciones/<referencia>      → eliminar (solo si no está aprobada)
"""

from __future__ import annotations

from flask import Blueprint, abort, jsonify, request

from ..autenticacion import exigir_admin, requiere_admin
from ..extensiones import db
from ..imagenes import borrar_imagen_subida, guardar_imagen_subida
from .catalogos import (BANCOS_PRUEBA, BILLETERAS_PRUEBA, DESTINO_GENERAL, ESTADOS, FRECUENCIAS, METODOS,
                        MONTO_MAXIMO, MONTO_MINIMO, TARJETAS_PRUEBA)
from .esquemas import (comprobante, donacion_cambio_schema, donacion_entrada_schema, donacion_schema,
                       donaciones_schema, leer_filtros, organizacion_entrada_schema, organizacion_schema,
                       organizaciones_schema, pago_schema)
from .modelos import Donacion, Organizacion, ahora_colombia
from .pasarela import procesar_pago

bp = Blueprint("donaciones", __name__, url_prefix="/api")


def leer_json() -> dict:
    """Como en el tutorial: request.get_json(force=True) lee el JSON enviado (ej. desde Postman)."""
    datos = request.get_json(force=True, silent=True)
    if not isinstance(datos, dict):
        abort(400, description="El cuerpo de la petición debe ser un objeto JSON.")
    return datos


def error_datos(campo: str, mensaje: str):
    """Mismo formato que los errores de validación de Marshmallow."""
    return jsonify({"error": "Los datos enviados no son válidos.", "detalles": {campo: [mensaje]}}), 400


def buscar_organizacion(id) -> Organizacion:
    return db.get_or_404(Organizacion, id, description="No existe una organización con ese ID.")


def buscar_donacion(referencia: str) -> Donacion:
    donacion = db.session.scalar(db.select(Donacion).where(Donacion.referencia == referencia.upper()))
    if donacion is None:
        abort(404, description="No existe una donación con esa referencia.")
    return donacion


def nombre_repetido(nombre: str, sin_contar: int | None = None) -> bool:
    consulta = db.select(Organizacion.id_organizacion).where(Organizacion.nombre == nombre)
    if sin_contar is not None:
        consulta = consulta.where(Organizacion.id_organizacion != sin_contar)
    return db.session.scalar(consulta) is not None


# ===========================================================================
# ORGANIZACIONES
# ===========================================================================
@bp.route("/organizaciones", methods=["GET"])
def get_organizaciones():
    incluir_inactivas = request.args.get("incluir_inactivas", "").lower() in ("true", "1", "si", "sí")
    consulta = db.select(Organizacion).order_by(Organizacion.id_organizacion)
    if incluir_inactivas:
        exigir_admin()  # las inactivas solo las ve el panel de administración
    else:
        consulta = consulta.where(Organizacion.activa.is_(True))
    return jsonify(organizaciones_schema.dump(db.session.scalars(consulta).all()))


@bp.route("/organizaciones/<int:id>", methods=["GET"])
def get_organizacion(id):
    return jsonify(organizacion_schema.dump(buscar_organizacion(id)))


@bp.route("/organizaciones", methods=["POST"])
@requiere_admin
def insert_organizacion():
    datos = organizacion_entrada_schema.load(leer_json())
    if nombre_repetido(datos["nombre"]):
        return error_datos("nombre", "Ya existe una organización con ese nombre.")
    nueva_organizacion = Organizacion(**datos)
    db.session.add(nueva_organizacion)  # INSERT
    db.session.commit()
    return jsonify(organizacion_schema.dump(nueva_organizacion)), 201


@bp.route("/organizaciones/<int:id>", methods=["PUT"])
@requiere_admin
def update_organizacion(id):
    actualizar_organizacion = buscar_organizacion(id)
    datos = organizacion_entrada_schema.load(leer_json(), partial=True)
    if "nombre" in datos and nombre_repetido(datos["nombre"], sin_contar=id):
        return error_datos("nombre", "Ya existe una organización con ese nombre.")
    for campo, valor in datos.items():
        setattr(actualizar_organizacion, campo, valor)
    if actualizar_organizacion.imagen and not actualizar_organizacion.imagen_alt:
        db.session.rollback()
        return error_datos("imagen_alt", "Describe la imagen: es obligatorio cuando hay imagen.")
    db.session.commit()  # UPDATE
    return jsonify(organizacion_schema.dump(actualizar_organizacion))


@bp.route("/organizaciones/<int:id>", methods=["DELETE"])
@requiere_admin
def delete_organizacion(id):
    eliminar_organizacion = buscar_organizacion(id)
    respuesta = organizacion_schema.dump(eliminar_organizacion)
    imagen = eliminar_organizacion.imagen
    # Las donaciones se conservan: guardan el nombre en "destino" y su id_organizacion queda en null
    db.session.execute(
        db.update(Donacion).where(Donacion.id_organizacion == id).values(id_organizacion=None)
    )
    db.session.delete(eliminar_organizacion)  # DELETE
    db.session.commit()
    en_uso = db.session.scalar(
        db.select(db.func.count()).select_from(Organizacion).where(Organizacion.imagen == imagen)
    )
    borrar_imagen_subida("donaciones", imagen, sigue_en_uso=bool(en_uso))
    return jsonify(respuesta)


@bp.route("/organizaciones/imagen", methods=["POST"])
@requiere_admin
def subir_imagen_organizacion():
    return jsonify({"imagen": guardar_imagen_subida("donaciones")}), 201


# ===========================================================================
# DONACIONES
# ===========================================================================
@bp.route("/donaciones/pasarela", methods=["GET"])
def get_pasarela():
    """Todo lo que necesita el formulario de pago: medios, montos y datos de prueba."""
    return jsonify({
        "simulada": True,
        "aviso": "Pasarela de pagos simulada: no se hacen cobros reales.",
        "monto_minimo": MONTO_MINIMO,
        "monto_maximo": MONTO_MAXIMO,
        "frecuencias": [{"clave": c, "nombre": n} for c, n in FRECUENCIAS.items()],
        "metodos": [{"clave": c, "nombre": n} for c, n in METODOS.items()],
        "tarjetas_prueba": [
            {"numero": " ".join(numero[i:i + 4] for i in range(0, 16, 4)), "franquicia": t["franquicia"],
             "resultado": "aprobada" if t["aprobada"] else "rechazada"}
            for numero, t in TARJETAS_PRUEBA.items()
        ],
        "bancos_prueba": [{"clave": c, "nombre": b["nombre"]} for c, b in BANCOS_PRUEBA.items()],
        "billeteras_prueba": [
            {"celular": c, "resultado": "aprobada" if b["aprobada"] else "rechazada"}
            for c, b in BILLETERAS_PRUEBA.items()
        ],
    })


@bp.route("/donaciones", methods=["POST"])
def insert_donacion():
    """Paso 1: registra la intención de donar. El pago se hace después, con la referencia."""
    datos = donacion_entrada_schema.load(leer_json())

    destino = DESTINO_GENERAL
    if datos["id_organizacion"] is not None:
        organizacion = db.session.get(Organizacion, datos["id_organizacion"])
        if organizacion is None or not organizacion.activa:
            return error_datos("id_organizacion", "La organización no existe o no está recibiendo donaciones.")
        destino = organizacion.nombre

    nueva_donacion = Donacion(referencia=Donacion.nueva_referencia(), destino=destino, **datos)
    db.session.add(nueva_donacion)  # INSERT
    db.session.commit()
    return jsonify(comprobante(nueva_donacion)), 201


@bp.route("/donaciones/<referencia>/pago", methods=["POST"])
def pagar_donacion(referencia):
    """Paso 2: la pasarela simulada procesa el pago. Si fue rechazado, se puede intentar otra vez."""
    donacion = buscar_donacion(referencia)
    if donacion.estado not in ("pendiente", "rechazada"):
        abort(409, description=f"Esta donación ya está {ESTADOS[donacion.estado].lower()}: no se puede pagar otra vez.")

    pago = pago_schema.load(leer_json())
    resultado = procesar_pago(pago)  # puede responder 400 si no son datos de prueba

    donacion.estado = "aprobada" if resultado.aprobada else "rechazada"
    donacion.metodo_pago = pago["metodo"]
    donacion.detalle_pago = resultado.detalle
    donacion.mensaje_pasarela = resultado.mensaje
    donacion.codigo_autorizacion = resultado.codigo
    donacion.pagado_en = ahora_colombia() if resultado.aprobada else None
    db.session.commit()  # UPDATE
    return jsonify(comprobante(donacion))


@bp.route("/donaciones/<referencia>", methods=["GET"])
def get_donacion(referencia):
    """Paso 3: comprobante (con el correo oculto)."""
    return jsonify(comprobante(buscar_donacion(referencia)))


@bp.route("/donaciones", methods=["GET"])
@requiere_admin
def get_donaciones():
    """Listado para el panel de administración."""
    filtros = leer_filtros(request.args)
    consulta = db.select(Donacion)
    if filtros["estado"]:
        consulta = consulta.where(Donacion.estado.in_(filtros["estado"]))
    if filtros["id_organizacion"] is not None:
        consulta = consulta.where(Donacion.id_organizacion == filtros["id_organizacion"])
    for palabra in (filtros["q"] or "").split():
        consulta = consulta.where(db.or_(
            Donacion.referencia.contains(palabra, autoescape=True),
            Donacion.nombre_donante.contains(palabra, autoescape=True),
            Donacion.correo.contains(palabra, autoescape=True),
        ))

    total = db.session.scalar(db.select(db.func.count()).select_from(consulta.subquery()))
    consulta = (consulta.order_by(Donacion.creado_en.desc(), Donacion.id_donacion.desc())
                .limit(filtros["limite"]).offset(filtros["offset"]))
    return jsonify({
        "total": total,
        "limite": filtros["limite"],
        "offset": filtros["offset"],
        "resultados": donaciones_schema.dump(db.session.scalars(consulta).all()),
    })


@bp.route("/donaciones/resumen", methods=["GET"])
@requiere_admin
def get_resumen():
    """Totales para el panel: lo recaudado (solo aprobadas) y cuántas hay en cada estado."""
    por_estado = dict(db.session.execute(
        db.select(Donacion.estado, db.func.count()).group_by(Donacion.estado)
    ).all())
    filas = db.session.execute(
        db.select(Donacion.destino, db.func.count(), db.func.coalesce(db.func.sum(Donacion.monto), 0))
        .where(Donacion.estado == "aprobada")
        .group_by(Donacion.destino)
        .order_by(db.func.sum(Donacion.monto).desc())
    ).all()
    return jsonify({
        "simulada": True,
        "total_recaudado": int(sum(monto for _, _, monto in filas)),
        "cantidad_por_estado": {estado: por_estado.get(estado, 0) for estado in ESTADOS},
        "por_destino": [{"destino": d, "cantidad": c, "total": int(m)} for d, c, m in filas],
    })


@bp.route("/donaciones/<referencia>", methods=["PUT"])
@requiere_admin
def update_donacion(referencia):
    """El administrador puede anular una donación aprobada (simula un reembolso) o escribir una nota."""
    donacion = buscar_donacion(referencia)
    datos = donacion_cambio_schema.load(leer_json())
    if datos.get("estado") == "anulada" and donacion.estado != "aprobada":
        abort(409, description="Solo se pueden anular las donaciones aprobadas.")
    for campo, valor in datos.items():
        setattr(donacion, campo, valor)
    db.session.commit()  # UPDATE
    return jsonify(donacion_schema.dump(donacion))


@bp.route("/donaciones/<referencia>", methods=["DELETE"])
@requiere_admin
def delete_donacion(referencia):
    donacion = buscar_donacion(referencia)
    if donacion.estado == "aprobada":
        abort(409, description="Una donación aprobada no se puede eliminar: anúlala primero.")
    respuesta = donacion_schema.dump(donacion)
    db.session.delete(donacion)  # DELETE
    db.session.commit()
    return jsonify(respuesta)
