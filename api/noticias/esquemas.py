"""Noticias: esquemas de Marshmallow.

  • NoticiaSchema         → convierte una Noticia a JSON (como CategoriaSchema del tutorial).
  • NoticiaEntradaSchema  → valida los datos que llegan en POST y PUT.
  • FiltrosSchema         → valida los parámetros de GET /api/noticias (?q=…&verificacion=…).
"""

from __future__ import annotations

from marshmallow import EXCLUDE, ValidationError, fields, pre_load, validate, validates_schema

from ..extensiones import ma
from ..imagenes import RUTA_IMAGEN
from ..utilidades import ZONA_COLOMBIA
from .modelos import VERIFICACION, Noticia

OPCIONALES = ("enlace", "imagen", "imagen_alt")


# ---------------------------------------------------------------------------
# Respuesta (salida)
# ---------------------------------------------------------------------------
class NoticiaSchema(ma.SQLAlchemyAutoSchema):  # cuando se consulta, el esquema dice qué datos mostrar
    class Meta:
        model = Noticia
        load_instance = True
        fields = (  # orden en que aparecen los campos en el JSON
            "id_noticia", "titulo", "contenido", "fuente", "enlace", "imagen", "imagen_alt",
            "verificacion", "verificacion_nombre", "destacada", "publicada", "fecha_publicacion", "actualizado_en",
        )

    verificacion_nombre = fields.Method("obtener_verificacion_nombre")
    fecha_publicacion = fields.Date()
    actualizado_en = fields.Method("obtener_actualizado_en")

    def obtener_verificacion_nombre(self, noticia):
        return VERIFICACION.get(noticia.verificacion, noticia.verificacion)

    def obtener_actualizado_en(self, noticia):
        return noticia.actualizado_en.replace(tzinfo=ZONA_COLOMBIA).isoformat(timespec="minutes")


noticia_schema = NoticiaSchema()             # una noticia
noticias_schema = NoticiaSchema(many=True)   # varias noticias


# ---------------------------------------------------------------------------
# Entrada (POST y PUT)
# ---------------------------------------------------------------------------
class NoticiaEntradaSchema(ma.Schema):
    titulo = fields.String(required=True, validate=validate.Length(min=5, max=200))
    contenido = fields.String(required=True, validate=validate.Length(min=10, max=5000))
    fuente = fields.String(required=True, validate=validate.Length(min=2, max=150))
    enlace = fields.Url(allow_none=True, schemes={"http", "https"}, validate=validate.Length(max=500))
    imagen = fields.String(
        allow_none=True,
        validate=[
            validate.Length(max=300),
            validate.Regexp(RUTA_IMAGEN, error="Debe ser una imagen del proyecto (img/…) o un enlace https://."),
        ],
    )
    imagen_alt = fields.String(allow_none=True, validate=validate.Length(max=200))
    verificacion = fields.String(validate=validate.OneOf(list(VERIFICACION)))
    destacada = fields.Boolean()
    publicada = fields.Boolean()
    fecha_publicacion = fields.Date()  # formato AAAA-MM-DD; si no llega, se usa la fecha de hoy

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
    def revisar_imagen(self, datos, partial=None, **kwargs):
        if ".." in (datos.get("imagen") or ""):
            raise ValidationError({"imagen": ["Ruta de imagen no válida."]})
        # Con imagen, la descripción es obligatoria (la leen los lectores de pantalla y la exige WAVE)
        if not partial and datos.get("imagen") and not datos.get("imagen_alt"):
            raise ValidationError({"imagen_alt": ["Describe la imagen: es obligatorio cuando hay imagen."]})


noticia_entrada_schema = NoticiaEntradaSchema()


# ---------------------------------------------------------------------------
# Parámetros de búsqueda (GET /api/noticias)
# ---------------------------------------------------------------------------
class FiltrosSchema(ma.Schema):
    class Meta:
        unknown = EXCLUDE  # se ignoran parámetros que no conocemos

    q = fields.String(load_default=None, validate=validate.Length(max=100))
    verificacion = fields.List(fields.String(validate=validate.OneOf(list(VERIFICACION))), load_default=list)
    destacada = fields.Boolean(load_default=None)
    publicada = fields.Boolean(load_default=None)          # false = solo borradores
    incluir_ocultas = fields.Boolean(load_default=False)   # true = publicadas y borradores (panel de admin)
    limite = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))
    offset = fields.Integer(load_default=0, validate=validate.Range(min=0))


def leer_filtros(args) -> dict:
    """Convierte request.args en un diccionario validado.

    Las listas aceptan ?verificacion=oficial&verificacion=en_verificacion o ?verificacion=oficial,en_verificacion
    """
    datos = {}
    for clave in args:
        if clave == "verificacion":
            datos[clave] = [v for valor in args.getlist(clave) for v in valor.split(",") if v]
        else:
            datos[clave] = args.get(clave)
    return FiltrosSchema().load(datos)
