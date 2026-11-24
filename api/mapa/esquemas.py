"""Mapa: esquemas de Marshmallow.

  • PuntoSchema         → convierte un Punto a JSON (como CategoriaSchema del tutorial).
  • PuntoEntradaSchema  → valida los datos que llegan en POST y PUT.
  • FiltrosSchema       → valida los parámetros de búsqueda de GET /api/puntos.
"""

from __future__ import annotations

from marshmallow import EXCLUDE, ValidationError, fields, validate, validates_schema

from ..extensiones import ma
from ..utilidades import ZONA_COLOMBIA, esta_abierto, horario_legible
from .catalogos import SERVICIOS, TIPOS, VERIFICACION
from .modelos import Punto

HORA = r"^([01]\d|2[0-3]):[0-5]\d$"
HORA_CIERRE = r"^(([01]\d|2[0-3]):[0-5]\d|24:00)$"
TELEFONO = r"^\+?[\d\s-]{7,20}$"


# ---------------------------------------------------------------------------
# Respuesta (salida)
# ---------------------------------------------------------------------------
class PuntoSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Punto
        load_instance = True
        exclude = ("texto_busqueda",)

    tipo_nombre = fields.Method("obtener_tipo_nombre")
    verificacion_nombre = fields.Method("obtener_verificacion_nombre")
    horario_texto = fields.Method("obtener_horario_texto")
    abierto_ahora = fields.Method("obtener_abierto_ahora")
    servicios = fields.Method("obtener_servicios")
    actualizado_en = fields.Method("obtener_actualizado_en")

    def obtener_tipo_nombre(self, punto):
        return TIPOS[punto.tipo]["nombre"]

    def obtener_verificacion_nombre(self, punto):
        return VERIFICACION[punto.verificacion]

    def obtener_horario_texto(self, punto):
        return horario_legible(punto.horario or [])

    def obtener_abierto_ahora(self, punto):
        return esta_abierto(punto.horario or [])

    def obtener_servicios(self, punto):
        return [{"clave": c, "nombre": SERVICIOS[c]} for c in punto.claves_servicios if c in SERVICIOS]

    def obtener_actualizado_en(self, punto):
        return punto.actualizado_en.replace(tzinfo=ZONA_COLOMBIA).isoformat(timespec="minutes")


punto_schema = PuntoSchema()            # un solo punto
puntos_schema = PuntoSchema(many=True)  # varios puntos


# ---------------------------------------------------------------------------
# Datos que llegan en POST y PUT (entrada)
# ---------------------------------------------------------------------------
class FranjaSchema(ma.Schema):
    dias = fields.List(fields.Integer(validate=validate.Range(0, 6)), required=True,
                       validate=validate.Length(min=1, error="Indica al menos un día (0 = lunes … 6 = domingo)."))
    abre = fields.String(required=True, validate=validate.Regexp(HORA, error="Usa el formato HH:MM (ej. 08:00)."))
    cierra = fields.String(required=True, validate=validate.Regexp(HORA_CIERRE, error="Usa el formato HH:MM (ej. 19:00 o 24:00)."))


def opcional(campo):
    """Campo de texto que puede venir vacío o null."""
    campo.allow_none = True
    return campo


class PuntoEntradaSchema(ma.Schema):
    class Meta:
        unknown = "raise"  # un campo mal escrito (ej. "nombr") se reporta como error

    nombre = fields.String(required=True, validate=validate.Length(2, 150))
    tipo = fields.String(required=True, validate=validate.OneOf(list(TIPOS)))
    descripcion = opcional(fields.String(validate=validate.Length(max=2000)))
    direccion = fields.String(required=True, validate=validate.Length(3, 200))
    barrio = opcional(fields.String(validate=validate.Length(max=100)))
    localidad = opcional(fields.String(validate=validate.Length(max=100)))
    ciudad = fields.String(validate=validate.Length(2, 100))
    lat = fields.Float(required=True, validate=validate.Range(-5, 14, error="La latitud debe estar dentro de Colombia (entre -5 y 14)."))
    lng = fields.Float(required=True, validate=validate.Range(-82, -66, error="La longitud debe estar dentro de Colombia (entre -82 y -66)."))
    telefono = opcional(fields.String(validate=validate.Regexp(TELEFONO, error="Teléfono no válido.")))
    whatsapp = opcional(fields.String(validate=validate.Regexp(TELEFONO, error="Número no válido.")))
    correo = opcional(fields.Email())
    sitio_web = opcional(fields.URL(schemes={"http", "https"}))
    imagen = opcional(fields.String(validate=validate.Length(max=255)))
    gratuito = fields.Boolean()
    costo_detalle = opcional(fields.String(validate=validate.Length(max=200)))
    confianza = fields.Float(validate=validate.Range(0, 5))
    verificacion = fields.String(validate=validate.OneOf(list(VERIFICACION)))
    fuente = opcional(fields.String(validate=validate.Length(max=150)))
    capacidad = opcional(fields.Integer(validate=validate.Range(min=0)))
    cupos_disponibles = opcional(fields.Integer(validate=validate.Range(min=0)))
    horario = fields.List(fields.Nested(FranjaSchema))
    servicios = fields.List(fields.String(validate=validate.OneOf(list(SERVICIOS))))

    @validates_schema
    def validar_cupos(self, datos, **kwargs):
        cap, cupos = datos.get("capacidad"), datos.get("cupos_disponibles")
        if cap is not None and cupos is not None and cupos > cap:
            raise ValidationError("No puede haber más cupos disponibles que la capacidad.", "cupos_disponibles")


punto_entrada_schema = PuntoEntradaSchema()


# ---------------------------------------------------------------------------
# Parámetros de búsqueda de GET /api/puntos
# ---------------------------------------------------------------------------
class FiltrosSchema(ma.Schema):
    class Meta:
        unknown = EXCLUDE  # parámetros desconocidos se ignoran

    q = fields.String(validate=validate.Length(max=100))
    tipo = fields.List(fields.String(validate=validate.OneOf(list(TIPOS))), load_default=list)
    servicio = fields.List(fields.String(validate=validate.OneOf(list(SERVICIOS))), load_default=list)
    verificacion = fields.List(fields.String(validate=validate.OneOf(list(VERIFICACION))), load_default=list)
    abierto_ahora = fields.Boolean(load_default=False)
    gratuito = fields.Boolean(load_default=False)
    con_cupos = fields.Boolean(load_default=False)
    confianza_min = fields.Float(validate=validate.Range(0, 5))
    ids = fields.String(validate=validate.Regexp(r"^\s*\d*(\s*,\s*\d+)*\s*$", error="Usa IDs separados por coma: 1,2,3"))
    lat = fields.Float(validate=validate.Range(-90, 90))
    lng = fields.Float(validate=validate.Range(-180, 180))
    radio_km = fields.Float(validate=validate.Range(min=0, max=100, min_inclusive=False))
    orden = fields.String(validate=validate.OneOf(["relevancia", "distancia", "confianza", "nombre"]))
    limite = fields.Integer(load_default=100, validate=validate.Range(1, 500))
    offset = fields.Integer(load_default=0, validate=validate.Range(min=0))

    @validates_schema
    def validar_ubicacion(self, datos, **kwargs):
        if ("lat" in datos) != ("lng" in datos):
            raise ValidationError("Envía lat y lng juntos.", "lat")
        if "lat" not in datos and ("radio_km" in datos or datos.get("orden") == "distancia"):
            raise ValidationError("radio_km y orden=distancia necesitan lat y lng.", "radio_km")


filtros_schema = FiltrosSchema()

LISTAS = ("tipo", "servicio", "verificacion")


def leer_filtros(args) -> dict:
    """Convierte los parámetros de la URL (?tipo=a&tipo=b…) y los valida."""
    datos = {k: v for k, v in args.items() if k not in LISTAS}
    for clave in LISTAS:
        if clave in args:
            datos[clave] = args.getlist(clave)
    return filtros_schema.load(datos)
