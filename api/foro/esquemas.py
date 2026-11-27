"""Foro: esquemas de Marshmallow.

  Salida:   PublicacionSchema (listado), respuesta_a_dict, denuncia_a_dict
  Entrada:  PublicacionEntradaSchema (POST), ModeracionSchema (PUT del moderador),
            RespuestaEntradaSchema, DenunciaEntradaSchema
  Filtros:  FiltrosSchema (GET /api/foro/publicaciones)
"""

from __future__ import annotations

from marshmallow import EXCLUDE, ValidationError, fields, pre_load, validate, validates_schema

from ..extensiones import ma
from ..utilidades import ZONA_COLOMBIA
from .modelos import CATEGORIAS, MOTIVOS_DENUNCIA, VERIFICACION, Publicacion


def fecha_iso(valor):
    return valor.replace(tzinfo=ZONA_COLOMBIA).isoformat(timespec="minutes") if valor else None


def limpiar(datos, opcionales=()):
    """Quita espacios sobrantes y convierte "" en null en los campos opcionales (útil con formularios)."""
    if not isinstance(datos, dict):
        return datos
    limpios = {}
    for campo, valor in datos.items():
        if isinstance(valor, str):
            valor = valor.strip()
            if valor == "" and campo in opcionales:
                valor = None
        limpios[campo] = valor
    return limpios


# ---------------------------------------------------------------------------
# Salida
# ---------------------------------------------------------------------------
class PublicacionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Publicacion
        load_instance = True
        fields = (
            "id_publicacion", "titulo", "contenido", "categoria", "categoria_nombre", "ubicacion", "autor",
            "verificacion", "verificacion_nombre", "oculta", "validaciones", "total_respuestas",
            "denuncias_pendientes", "creado_en", "ultima_actividad",
        )

    categoria_nombre = fields.Method("obtener_categoria")
    verificacion_nombre = fields.Method("obtener_verificacion")
    total_respuestas = fields.Method("obtener_total_respuestas")
    denuncias_pendientes = fields.Integer()
    creado_en = fields.Method("obtener_creado_en")
    ultima_actividad = fields.Method("obtener_ultima_actividad")

    def obtener_categoria(self, p):
        return CATEGORIAS.get(p.categoria, p.categoria)

    def obtener_verificacion(self, p):
        return VERIFICACION.get(p.verificacion, p.verificacion)

    def obtener_total_respuestas(self, p):
        return len(p.respuestas)

    def obtener_creado_en(self, p):
        return fecha_iso(p.creado_en)

    def obtener_ultima_actividad(self, p):
        return fecha_iso(p.ultima_actividad)


publicacion_schema = PublicacionSchema()
publicaciones_schema = PublicacionSchema(many=True)


def respuesta_a_dict(r) -> dict:
    return {"id_respuesta": r.id_respuesta, "id_publicacion": r.id_publicacion, "autor": r.autor,
            "contenido": r.contenido, "creado_en": fecha_iso(r.creado_en)}


def denuncia_a_dict(d) -> dict:
    return {"id_denuncia": d.id_denuncia, "motivo": d.motivo, "motivo_nombre": MOTIVOS_DENUNCIA.get(d.motivo, d.motivo),
            "detalle": d.detalle, "revisada": d.revisada, "creado_en": fecha_iso(d.creado_en)}


def publicacion_completa(p, moderacion: bool = False) -> dict:
    """La publicación con sus respuestas; el moderador además ve las denuncias."""
    datos = publicacion_schema.dump(p)
    datos["respuestas"] = [respuesta_a_dict(r) for r in p.respuestas]
    if moderacion:
        datos["denuncias"] = [denuncia_a_dict(d) for d in p.denuncias]
    return datos


# ---------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------
class PublicacionEntradaSchema(ma.Schema):
    """POST /api/foro/publicaciones (lo que escribe cualquier persona en foro.html)."""

    titulo = fields.String(required=True, validate=validate.Length(min=5, max=150))
    contenido = fields.String(required=True, validate=validate.Length(min=10, max=3000))
    categoria = fields.String(load_default="general", validate=validate.OneOf(list(CATEGORIAS)))
    ubicacion = fields.String(allow_none=True, validate=validate.Length(max=150))
    autor = fields.String(required=True, validate=validate.Length(min=2, max=80))

    @pre_load
    def limpiar_textos(self, datos, **kwargs):
        return limpiar(datos, ("ubicacion",))


publicacion_entrada_schema = PublicacionEntradaSchema()


class ModeracionSchema(ma.Schema):
    """PUT /api/foro/publicaciones/<id> (lo que puede cambiar el moderador)."""

    titulo = fields.String(validate=validate.Length(min=5, max=150))
    contenido = fields.String(validate=validate.Length(min=10, max=3000))
    categoria = fields.String(validate=validate.OneOf(list(CATEGORIAS)))
    ubicacion = fields.String(allow_none=True, validate=validate.Length(max=150))
    verificacion = fields.String(validate=validate.OneOf(list(VERIFICACION)))
    oculta = fields.Boolean()

    @pre_load
    def limpiar_textos(self, datos, **kwargs):
        return limpiar(datos, ("ubicacion",))

    @validates_schema
    def algo_que_cambiar(self, datos, **kwargs):
        if not datos:
            raise ValidationError("Envía al menos un campo para cambiar.")


moderacion_schema = ModeracionSchema()


class RespuestaEntradaSchema(ma.Schema):
    autor = fields.String(required=True, validate=validate.Length(min=2, max=80))
    contenido = fields.String(required=True, validate=validate.Length(min=2, max=2000))

    @pre_load
    def limpiar_textos(self, datos, **kwargs):
        return limpiar(datos)


respuesta_entrada_schema = RespuestaEntradaSchema()


class DenunciaEntradaSchema(ma.Schema):
    motivo = fields.String(required=True, validate=validate.OneOf(list(MOTIVOS_DENUNCIA)))
    detalle = fields.String(allow_none=True, validate=validate.Length(max=300))

    @pre_load
    def limpiar_textos(self, datos, **kwargs):
        return limpiar(datos, ("detalle",))


denuncia_entrada_schema = DenunciaEntradaSchema()


# ---------------------------------------------------------------------------
# Filtros de GET /api/foro/publicaciones
# ---------------------------------------------------------------------------
class FiltrosSchema(ma.Schema):
    class Meta:
        unknown = EXCLUDE

    q = fields.String(load_default=None, validate=validate.Length(max=100))
    categoria = fields.List(fields.String(validate=validate.OneOf(list(CATEGORIAS))), load_default=list)
    verificacion = fields.String(load_default=None, validate=validate.OneOf(list(VERIFICACION)))
    # Panel del moderador: incluye las ocultas; revision=pendiente deja solo lo que hay que revisar
    moderacion = fields.Boolean(load_default=False)
    revision = fields.String(load_default=None, validate=validate.OneOf(["pendiente", "ocultas"]))
    limite = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))
    offset = fields.Integer(load_default=0, validate=validate.Range(min=0))


def leer_filtros(args) -> dict:
    datos = {}
    for clave in args:
        if clave == "categoria":
            datos[clave] = [v for valor in args.getlist(clave) for v in valor.split(",") if v]
        else:
            datos[clave] = args.get(clave)
    return FiltrosSchema().load(datos)
