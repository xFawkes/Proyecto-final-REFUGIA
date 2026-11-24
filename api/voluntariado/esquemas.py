"""Voluntariado: esquemas de Marshmallow.

  • VoluntariadoSchema         → convierte un Voluntariado a JSON (como CategoriaSchema del tutorial).
  • VoluntariadoEntradaSchema  → valida los datos que llegan en POST y PUT.
  • FiltrosSchema              → valida los parámetros de GET /api/voluntariados (?q=…&modalidad=…).
"""

from __future__ import annotations

from marshmallow import EXCLUDE, ValidationError, fields, pre_load, validate, validates_schema

from ..extensiones import ma
from ..imagenes import RUTA_IMAGEN
from ..utilidades import ZONA_COLOMBIA
from .modelos import ESTADOS, MODALIDADES, Voluntariado

OPCIONALES = ("requisitos", "ubicacion", "enlace", "imagen", "imagen_alt")


# ---------------------------------------------------------------------------
# Respuesta (salida)
# ---------------------------------------------------------------------------
class VoluntariadoSchema(ma.SQLAlchemyAutoSchema):  # cuando se consulta, el esquema dice qué datos mostrar
    class Meta:
        model = Voluntariado
        load_instance = True
        fields = (  # orden en que aparecen los campos en el JSON
            "id_voluntariado", "actividad", "organizacion", "descripcion", "requisitos",
            "modalidad", "modalidad_nombre", "ubicacion", "enlace", "imagen", "imagen_alt",
            "estado", "estado_nombre", "creado_en", "actualizado_en",
        )

    modalidad_nombre = fields.Method("obtener_modalidad_nombre")
    estado_nombre = fields.Method("obtener_estado_nombre")
    creado_en = fields.Method("obtener_creado_en")
    actualizado_en = fields.Method("obtener_actualizado_en")

    def obtener_modalidad_nombre(self, voluntariado):
        return MODALIDADES.get(voluntariado.modalidad, voluntariado.modalidad)

    def obtener_estado_nombre(self, voluntariado):
        return ESTADOS.get(voluntariado.estado, voluntariado.estado)

    def obtener_creado_en(self, voluntariado):
        return voluntariado.creado_en.replace(tzinfo=ZONA_COLOMBIA).isoformat(timespec="minutes")

    def obtener_actualizado_en(self, voluntariado):
        return voluntariado.actualizado_en.replace(tzinfo=ZONA_COLOMBIA).isoformat(timespec="minutes")


voluntariado_schema = VoluntariadoSchema()              # un voluntariado
voluntariados_schema = VoluntariadoSchema(many=True)    # varios voluntariados


# ---------------------------------------------------------------------------
# Entrada (POST y PUT)
# ---------------------------------------------------------------------------
class VoluntariadoEntradaSchema(ma.Schema):
    actividad = fields.String(required=True, validate=validate.Length(min=5, max=150))
    organizacion = fields.String(required=True, validate=validate.Length(min=2, max=150))
    descripcion = fields.String(required=True, validate=validate.Length(min=10, max=2000))
    requisitos = fields.String(allow_none=True, validate=validate.Length(max=2000))
    modalidad = fields.String(validate=validate.OneOf(list(MODALIDADES)))
    ubicacion = fields.String(allow_none=True, validate=validate.Length(max=150))
    enlace = fields.Url(allow_none=True, schemes={"http", "https"}, validate=validate.Length(max=500))
    imagen = fields.String(
        allow_none=True,
        validate=[
            validate.Length(max=300),
            validate.Regexp(RUTA_IMAGEN, error="Debe ser una imagen del proyecto (img/…) o un enlace https://."),
        ],
    )
    imagen_alt = fields.String(allow_none=True, validate=validate.Length(max=200))
    estado = fields.String(validate=validate.OneOf(list(ESTADOS)))

    @pre_load
    def limpiar_textos(self, datos, **kwargs):
        """Quita espacios sobrantes y convierte "" en null en los campos opcionales (útil con formularios)."""
        if not isinstance(datos, dict):
            return datos
        limpios = {}
        for campo, valor in datos.items():
            if isinstance(valor, str):
                valor = valor.strip()
                if valor == "" and campo in OPCIONALES:
                    valor = None
            limpios[campo] = valor
        return limpios

    @validates_schema
    def revisar_reglas(self, datos, partial=None, **kwargs):
        if ".." in (datos.get("imagen") or ""):
            raise ValidationError({"imagen": ["Ruta de imagen no válida."]})
        if partial:
            return  # en PUT estas reglas se revisan en la ruta, con los datos ya guardados
        errores = revisar_coherencia(datos)
        if errores:
            raise ValidationError(errores)


def revisar_coherencia(datos: dict) -> dict:
    """Reglas que dependen de varios campos (se usan en POST y en PUT)."""
    errores = {}
    if datos.get("imagen") and not datos.get("imagen_alt"):
        errores["imagen_alt"] = ["Describe la imagen: es obligatorio cuando hay imagen."]
    if datos.get("modalidad", "presencial") != "virtual" and not datos.get("ubicacion"):
        errores["ubicacion"] = ["Indica dónde se realiza (obligatorio si no es virtual)."]
    return errores


voluntariado_entrada_schema = VoluntariadoEntradaSchema()


# ---------------------------------------------------------------------------
# Parámetros de búsqueda (GET /api/voluntariados)
# ---------------------------------------------------------------------------
class FiltrosSchema(ma.Schema):
    class Meta:
        unknown = EXCLUDE  # se ignoran parámetros que no conocemos

    q = fields.String(load_default=None, validate=validate.Length(max=100))
    modalidad = fields.List(fields.String(validate=validate.OneOf(list(MODALIDADES))), load_default=list)
    # Por defecto solo los activos (lo que ve voluntariado.html); "todos" lo usa el panel
    estado = fields.String(load_default="activo", validate=validate.OneOf([*ESTADOS, "todos"]))
    limite = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))
    offset = fields.Integer(load_default=0, validate=validate.Range(min=0))


def leer_filtros(args) -> dict:
    """Convierte request.args en un diccionario validado.

    modalidad acepta ?modalidad=presencial&modalidad=mixta o ?modalidad=presencial,mixta
    """
    datos = {}
    for clave in args:
        if clave == "modalidad":
            datos[clave] = [v for valor in args.getlist(clave) for v in valor.split(",") if v]
        else:
            datos[clave] = args.get(clave)
    return FiltrosSchema().load(datos)
