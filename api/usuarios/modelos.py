"""Usuarios: modelo (la tabla "usuarios" en MySQL), como la clase Categoria del tutorial.

La contraseña NUNCA se guarda tal cual: se guarda su "hash" (un resumen que no se puede
devolver a la contraseña original). Para revisar si una contraseña es correcta se calcula
el hash otra vez y se compara (funciones de werkzeug, que ya viene instalado con Flask).
"""

from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from ..extensiones import db
from ..utilidades import ZONA_COLOMBIA

# Catálogo de roles
ROLES = {
    "usuario": "Usuario",               # publica en el foro y edita su perfil
    "administrador": "Administrador",   # entra al panel de administración (admin/)
}


def ahora_colombia() -> datetime:
    """Fecha y hora de Colombia sin zona (MySQL DATETIME no guarda la zona)."""
    return datetime.now(ZONA_COLOMBIA).replace(tzinfo=None, microsecond=0)


class Usuario(db.Model):  # se crea la clase que genera la tabla
    __tablename__ = "usuarios"

    id_usuario = db.Column(db.Integer, primary_key=True)                        # llave primaria
    nombre_usuario = db.Column(db.String(30), nullable=False, unique=True)      # "ana.gomez" (en minúsculas)
    correo = db.Column(db.String(120), nullable=False, unique=True)             # en minúsculas
    contrasena = db.Column(db.String(255), nullable=False)                      # hash, nunca la contraseña
    rol = db.Column(db.String(20), nullable=False, default="usuario", index=True)
    nombre = db.Column(db.String(80))                                           # nombre para mostrar (opcional)
    telefono = db.Column(db.String(20))                                         # opcional (Mi perfil)
    ubicacion = db.Column(db.String(100))                                       # opcional (Mi perfil)
    activo = db.Column(db.Boolean, nullable=False, default=True)                # False = no puede iniciar sesión
    # Cambia cada vez que se cambia la contraseña o se desactiva la cuenta:
    # así se cierran las sesiones que estaban abiertas con los datos anteriores.
    version_sesion = db.Column(db.Integer, nullable=False, default=0)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_colombia)
    ultimo_acceso = db.Column(db.DateTime)                                      # último inicio de sesión

    # ---- Contraseña ----
    def cambiar_contrasena(self, contrasena: str) -> None:
        self.contrasena = generate_password_hash(contrasena)
        self.version_sesion = (self.version_sesion or 0) + 1

    def revisar_contrasena(self, contrasena: str) -> bool:
        return check_password_hash(self.contrasena, contrasena)

    @property
    def es_admin(self) -> bool:
        return self.rol == "administrador"

    @property
    def nombre_visible(self) -> str:
        """Lo que se muestra como autor en el foro y en el menú de usuario."""
        return self.nombre or self.nombre_usuario
