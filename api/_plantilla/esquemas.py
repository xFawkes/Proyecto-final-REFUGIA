"""Esquema: convierte los registros a JSON y valida los datos que llegan (Marshmallow)."""

from marshmallow import fields, validate

from ..extensiones import ma
from .modelos import Elemento


class ElementoSchema(ma.SQLAlchemyAutoSchema):  # cuando se consulta, el esquema dice qué datos mostrar
    class Meta:
        model = Elemento
        load_instance = True

    # Validaciones de los datos que llegan en POST y PUT
    titulo = fields.String(required=True, validate=validate.Length(min=2, max=255))
    descripcion = fields.String(allow_none=True, validate=validate.Length(max=255))


elemento_schema = ElementoSchema()             # respuesta cuando es un elemento
elementos_schema = ElementoSchema(many=True)   # respuesta cuando son varios elementos
