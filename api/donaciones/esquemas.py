"""Donaciones: esquemas de Marshmallow.

  Organizaciones:  OrganizacionSchema (salida) y OrganizacionEntradaSchema (POST/PUT)
  Donaciones:      DonacionSchema (salida), DonacionEntradaSchema (POST), DonacionCambioSchema (PUT)
  Pasarela:        PagoSchema (datos del pago simulado)
  Filtros:         FiltrosDonacionesSchema (GET /api/donaciones)
"""

from __future__ import annotations

import re
from datetime import date

from marshmallow import EXCLUDE, ValidationError, fields, pre_load, validate, validates_schema

from ..extensiones import ma
from ..imagenes import RUTA_IMAGEN
from ..utilidades import ZONA_COLOMBIA
from .catalogos import (BANCOS_PRUEBA, ESTADOS, FRECUENCIAS, METODOS, MONTO_MAXIMO, MONTO_MINIMO)
from .modelos import Donacion, Organizacion


def fecha_iso(valor):
    return valor.replace(tzinfo=ZONA_COLOMBIA).isoformat(timespec="minutes") if valor else None


def limpiar(datos, opcionales):
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


# ===========================================================================
# Organizaciones
# ===========================================================================
class OrganizacionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Organizacion
        load_instance = True
        fields = ("id_organizacion", "nombre", "descripcion", "impacto", "enlace", "imagen", "imagen_alt", "activa")


organizacion_schema = OrganizacionSchema()
organizaciones_schema = OrganizacionSchema(many=True)


class OrganizacionEntradaSchema(ma.Schema):
    nombre = fields.String(required=True, validate=validate.Length(min=2, max=150))
    descripcion = fields.String(required=True, validate=validate.Length(min=10, max=1000))
    impacto = fields.String(allow_none=True, validate=validate.Length(max=300))
    enlace = fields.Url(allow_none=True, schemes={"http", "https"}, validate=validate.Length(max=500))
    imagen = fields.String(
        allow_none=True,
        validate=[
            validate.Length(max=300),
            validate.Regexp(RUTA_IMAGEN, error="Debe ser una imagen del proyecto (img/…) o un enlace https://."),
        ],
    )
    imagen_alt = fields.String(allow_none=True, validate=validate.Length(max=200))
    activa = fields.Boolean()

    @pre_load
    def limpiar_textos(self, datos, **kwargs):
        return limpiar(datos, ("impacto", "enlace", "imagen", "imagen_alt"))

    @validates_schema
    def revisar_imagen(self, datos, partial=None, **kwargs):
        if ".." in (datos.get("imagen") or ""):
            raise ValidationError({"imagen": ["Ruta de imagen no válida."]})
        if not partial and datos.get("imagen") and not datos.get("imagen_alt"):
            raise ValidationError({"imagen_alt": ["Describe la imagen: es obligatorio cuando hay imagen."]})


organizacion_entrada_schema = OrganizacionEntradaSchema()


# ===========================================================================
# Donaciones
# ===========================================================================
class DonacionSchema(ma.SQLAlchemyAutoSchema):
    """Respuesta completa (panel de administración)."""

    class Meta:
        model = Donacion
        load_instance = True
        include_fk = True
        fields = (
            "referencia", "id_organizacion", "destino", "monto", "frecuencia", "frecuencia_nombre",
            "nombre_donante", "correo", "estado", "estado_nombre", "metodo_pago", "metodo_pago_nombre",
            "detalle_pago", "codigo_autorizacion", "mensaje_pasarela", "nota", "creado_en", "pagado_en",
            "simulada",
        )

    frecuencia_nombre = fields.Method("obtener_frecuencia")
    estado_nombre = fields.Method("obtener_estado")
    metodo_pago_nombre = fields.Method("obtener_metodo")
    creado_en = fields.Method("obtener_creado_en")
    pagado_en = fields.Method("obtener_pagado_en")
    simulada = fields.Constant(True)  # recordatorio en cada respuesta: no hubo cobro real

    def obtener_frecuencia(self, d):
        return FRECUENCIAS.get(d.frecuencia, d.frecuencia)

    def obtener_estado(self, d):
        return ESTADOS.get(d.estado, d.estado)

    def obtener_metodo(self, d):
        return METODOS.get(d.metodo_pago) if d.metodo_pago else None

    def obtener_creado_en(self, d):
        return fecha_iso(d.creado_en)

    def obtener_pagado_en(self, d):
        return fecha_iso(d.pagado_en)


donacion_schema = DonacionSchema()
donaciones_schema = DonacionSchema(many=True)


def ocultar_correo(correo: str) -> str:
    """david@correo.com → d***@correo.com (el comprobante público no muestra el correo completo)."""
    usuario, _, dominio = correo.partition("@")
    return f"{usuario[:1]}***@{dominio}"


def comprobante(donacion: Donacion) -> dict:
    """Lo que ve el donante (y cualquiera que tenga la referencia): sin el correo completo ni la nota."""
    datos = donacion_schema.dump(donacion)
    datos["correo"] = ocultar_correo(donacion.correo)
    datos.pop("nota", None)
    return datos


class DonacionEntradaSchema(ma.Schema):
    """POST /api/donaciones: la intención de donar (todavía sin pagar)."""

    monto = fields.Integer(required=True, strict=False,
                           validate=validate.Range(min=MONTO_MINIMO, max=MONTO_MAXIMO,
                                                   error="Debe estar entre $10.000 y $20.000.000."))
    frecuencia = fields.String(load_default="unica", validate=validate.OneOf(list(FRECUENCIAS)))
    id_organizacion = fields.Integer(allow_none=True, load_default=None)  # null = donde más se necesite
    nombre_donante = fields.String(required=True, validate=validate.Length(min=2, max=120))
    correo = fields.Email(required=True, validate=validate.Length(max=150))

    @pre_load
    def limpiar_textos(self, datos, **kwargs):
        datos = limpiar(datos, ("id_organizacion",))
        if isinstance(datos, dict) and isinstance(datos.get("correo"), str):
            datos["correo"] = datos["correo"].lower()
        return datos


donacion_entrada_schema = DonacionEntradaSchema()


class DonacionCambioSchema(ma.Schema):
    """PUT /api/donaciones/<referencia>: lo único que puede cambiar el administrador."""

    estado = fields.String(validate=validate.OneOf(["anulada"], error="Solo se puede cambiar a: anulada."))
    nota = fields.String(allow_none=True, validate=validate.Length(max=300))

    @pre_load
    def limpiar_textos(self, datos, **kwargs):
        return limpiar(datos, ("nota",))

    @validates_schema
    def algo_que_cambiar(self, datos, **kwargs):
        if not datos:
            raise ValidationError("Envía al menos uno de estos campos: estado, nota.")


donacion_cambio_schema = DonacionCambioSchema()


# ===========================================================================
# Pasarela simulada
# ===========================================================================
class TarjetaSchema(ma.Schema):
    titular = fields.String(required=True, validate=validate.Length(min=3, max=80))
    numero = fields.String(required=True)
    vencimiento = fields.String(required=True)  # MM/AA
    cvv = fields.String(required=True, validate=validate.Regexp(r"^\d{3,4}$", error="Debe tener 3 o 4 dígitos."))

    @pre_load
    def limpiar_numero(self, datos, **kwargs):
        if isinstance(datos, dict) and isinstance(datos.get("numero"), str):
            datos = {**datos, "numero": re.sub(r"[\s-]", "", datos["numero"])}
        return datos

    @validates_schema
    def revisar_tarjeta(self, datos, **kwargs):
        errores = {}
        numero = datos.get("numero", "")
        if not re.fullmatch(r"\d{13,19}", numero) or not cumple_luhn(numero):
            errores["numero"] = ["Número de tarjeta no válido."]
        coincide = re.fullmatch(r"(0[1-9]|1[0-2])/(\d{2})", datos.get("vencimiento", ""))
        if not coincide:
            errores["vencimiento"] = ["Usa el formato MM/AA."]
        else:
            mes, anio = int(coincide.group(1)), 2000 + int(coincide.group(2))
            hoy = date.today()
            if (anio, mes) < (hoy.year, hoy.month):
                errores["vencimiento"] = ["La tarjeta está vencida."]
        if errores:
            raise ValidationError(errores)


def cumple_luhn(numero: str) -> bool:
    """Algoritmo de Luhn: el dígito de control que tienen todas las tarjetas."""
    suma = 0
    for i, digito in enumerate(reversed(numero)):
        d = int(digito)
        if i % 2 == 1:
            d = d * 2 - 9 if d > 4 else d * 2
        suma += d
    return suma % 10 == 0


class PagoSchema(ma.Schema):
    """POST /api/donaciones/<referencia>/pago"""

    metodo = fields.String(required=True, validate=validate.OneOf(list(METODOS)))
    tarjeta = fields.Nested(TarjetaSchema)
    banco = fields.String(validate=validate.OneOf(list(BANCOS_PRUEBA)))
    celular = fields.String(validate=validate.Regexp(r"^3\d{9}$", error="Debe ser un celular de 10 dígitos que empiece por 3."))

    @validates_schema
    def datos_del_metodo(self, datos, **kwargs):
        requerido = {"tarjeta": "tarjeta", "transferencia": "banco", "billetera": "celular"}.get(datos.get("metodo"))
        if requerido and requerido not in datos:
            raise ValidationError({requerido: ["Este campo es obligatorio para este medio de pago."]})


pago_schema = PagoSchema()


# ===========================================================================
# Filtros de GET /api/donaciones (panel)
# ===========================================================================
class FiltrosDonacionesSchema(ma.Schema):
    class Meta:
        unknown = EXCLUDE

    q = fields.String(load_default=None, validate=validate.Length(max=100))  # referencia, donante o correo
    estado = fields.List(fields.String(validate=validate.OneOf(list(ESTADOS))), load_default=list)
    id_organizacion = fields.Integer(load_default=None)
    limite = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))
    offset = fields.Integer(load_default=0, validate=validate.Range(min=0))


def leer_filtros(args) -> dict:
    datos = {}
    for clave in args:
        if clave == "estado":
            datos[clave] = [v for valor in args.getlist(clave) for v in valor.split(",") if v]
        else:
            datos[clave] = args.get(clave)
    return FiltrosDonacionesSchema().load(datos)
