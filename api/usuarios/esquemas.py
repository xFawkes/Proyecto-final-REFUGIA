"""Usuarios: esquemas de Marshmallow.

  • UsuarioSchema           → convierte un Usuario a JSON (nunca incluye la contraseña).
  • RegistroSchema          → valida POST /api/usuarios (crear cuenta).
  • InicioSesionSchema      → valida POST /api/sesion (iniciar sesión).
  • PerfilSchema            → valida PUT /api/usuarios/yo (la persona edita sus datos).
  • CambioContrasenaSchema  → valida PUT /api/usuarios/yo/contrasena.
  • UsuarioAdminSchema      → valida PUT /api/usuarios/<id> (el administrador cambia rol o estado).
  • FiltrosSchema           → valida los parámetros de GET /api/usuarios (?q=…&rol=…).
"""

from __future__ import annotations

import re

from marshmallow import EXCLUDE, ValidationError, fields, pre_load, validate

from ..extensiones import ma
from ..utilidades import ZONA_COLOMBIA
from .modelos import ROLES, Usuario

OPCIONALES = ("nombre", "telefono", "ubicacion")

# 3 a 30 caracteres: letras sin tilde, números, punto, guion o guion bajo; empieza por letra o número
PATRON_USUARIO = re.compile(r"^[a-z0-9][a-z0-9._-]{2,29}$")
PATRON_TELEFONO = re.compile(r"^\+?[0-9 ()-]{7,20}$")


def validar_contrasena(valor: str) -> None:
    """Contraseña segura: al menos una letra y un número (la longitud la revisa validate.Length)."""
    if not re.search(r"[^\W\d_]", valor) or not re.search(r"\d", valor):
        raise ValidationError("Debe tener al menos una letra y un número.")


def campo_contrasena(**kwargs) -> fields.String:
    return fields.String(validate=[validate.Length(min=8, max=128), validar_contrasena], **kwargs)


def limpiar(datos, minusculas=("nombre_usuario", "correo")):
    """Quita espacios sobrantes, pasa a minúsculas el usuario y el correo, y convierte "" en null."""
    if not isinstance(datos, dict):
        return datos
    limpios = {}
    for campo, valor in datos.items():
        if isinstance(valor, str) and campo not in ("contrasena", "actual", "nueva"):  # contraseñas tal cual
            valor = valor.strip()
            if campo in minusculas:
                valor = valor.lower()
            if valor == "" and campo in OPCIONALES:
                valor = None
        limpios[campo] = valor
    return limpios


# ---------------------------------------------------------------------------
# Respuesta (salida)
# ---------------------------------------------------------------------------
class UsuarioSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Usuario
        fields = (  # orden en que aparecen los campos en el JSON (sin la contraseña)
            "id_usuario", "nombre_usuario", "correo", "nombre", "nombre_visible", "telefono", "ubicacion",
            "rol", "rol_nombre", "activo", "creado_en", "ultimo_acceso",
        )

    nombre_visible = fields.Method("obtener_nombre_visible")
    rol_nombre = fields.Method("obtener_rol_nombre")
    creado_en = fields.Method("obtener_creado_en")
    ultimo_acceso = fields.Method("obtener_ultimo_acceso")

    def obtener_nombre_visible(self, usuario):
        return usuario.nombre_visible

    def obtener_rol_nombre(self, usuario):
        return ROLES.get(usuario.rol, usuario.rol)

    def obtener_creado_en(self, usuario):
        return usuario.creado_en.replace(tzinfo=ZONA_COLOMBIA).isoformat(timespec="minutes")

    def obtener_ultimo_acceso(self, usuario):
        if usuario.ultimo_acceso is None:
            return None
        return usuario.ultimo_acceso.replace(tzinfo=ZONA_COLOMBIA).isoformat(timespec="minutes")


usuario_schema = UsuarioSchema()
usuarios_schema = UsuarioSchema(many=True)


# ---------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------
NOMBRE_USUARIO = dict(validate=validate.Regexp(
    PATRON_USUARIO,
    error="Entre 3 y 30 caracteres: letras sin tilde, números, punto, guion o guion bajo (sin espacios).",
))
CORREO = dict(validate=validate.Length(max=120))
NOMBRE = dict(allow_none=True, validate=validate.Length(min=2, max=80))
TELEFONO = dict(allow_none=True, validate=validate.Regexp(
    PATRON_TELEFONO, error="Escribe solo números (puede empezar por +), entre 7 y 20 caracteres."))
UBICACION = dict(allow_none=True, validate=validate.Length(max=100))


class RegistroSchema(ma.Schema):
    nombre_usuario = fields.String(required=True, **NOMBRE_USUARIO)
    correo = fields.Email(required=True, **CORREO)
    contrasena = campo_contrasena(required=True)
    nombre = fields.String(**NOMBRE)

    @pre_load
    def limpiar_textos(self, datos, **kwargs):
        return limpiar(datos)


class InicioSesionSchema(ma.Schema):
    # "usuario" acepta el nombre de usuario o el correo
    usuario = fields.String(required=True, validate=validate.Length(min=1, max=120,
                                                                     error="Escribe tu usuario o correo."))
    contrasena = fields.String(required=True, validate=validate.Length(min=1, max=128,
                                                                       error="Escribe tu contraseña."))

    @pre_load
    def limpiar_textos(self, datos, **kwargs):
        if isinstance(datos, dict) and isinstance(datos.get("usuario"), str):
            datos = {**datos, "usuario": datos["usuario"].strip().lower()}
        return datos


class PerfilSchema(ma.Schema):
    nombre = fields.String(**NOMBRE)
    correo = fields.Email(**CORREO)
    telefono = fields.String(**TELEFONO)
    ubicacion = fields.String(**UBICACION)

    @pre_load
    def limpiar_textos(self, datos, **kwargs):
        return limpiar(datos)


class CambioContrasenaSchema(ma.Schema):
    actual = fields.String(required=True, validate=validate.Length(min=1, max=128,
                                                                   error="Escribe tu contraseña actual."))
    nueva = campo_contrasena(required=True)


class UsuarioAdminSchema(PerfilSchema):
    rol = fields.String(validate=validate.OneOf(list(ROLES)))
    activo = fields.Boolean()


registro_schema = RegistroSchema()
inicio_sesion_schema = InicioSesionSchema()
perfil_schema = PerfilSchema()
cambio_contrasena_schema = CambioContrasenaSchema()
usuario_admin_schema = UsuarioAdminSchema()


# ---------------------------------------------------------------------------
# Parámetros de búsqueda (GET /api/usuarios)
# ---------------------------------------------------------------------------
class FiltrosSchema(ma.Schema):
    class Meta:
        unknown = EXCLUDE  # se ignoran parámetros que no conocemos

    q = fields.String(load_default=None, validate=validate.Length(max=100))
    rol = fields.String(load_default=None, validate=validate.OneOf(list(ROLES)))
    activo = fields.Boolean(load_default=None)
    limite = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))
    offset = fields.Integer(load_default=0, validate=validate.Range(min=0))


def leer_filtros(args) -> dict:
    """Convierte request.args en un diccionario validado (los parámetros vacíos, ej. ?rol=, se ignoran)."""
    return FiltrosSchema().load({clave: valor for clave, valor in args.items() if valor != ""})
