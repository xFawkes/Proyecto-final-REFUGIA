"""Sección Usuarios: cuentas, inicio de sesión y roles (usuario / administrador).

Hecha a partir de api/_plantilla. Como toda sección, expone dos cosas que usa api/__init__.py:
  • bp                    → el Blueprint con sus rutas (rutas.py)
  • cargar_datos_ejemplo  → crea las cuentas de prueba la primera vez (si la tabla está vacía)

La consumen:
  • iniciar-sesion.html y registro.html   con js/acceso.js
  • todas las páginas                       con js/sesion.js (menú de usuario y cerrar sesión)
  • perfil.html                             con js/perfil.js (editar mis datos y contraseña)
  • admin/usuarios.html                     con js/admin/usuarios.js (CRUD de cuentas)

Para proteger las rutas de las demás secciones se usa api/autenticacion.py.
"""

from ..extensiones import db
from .datos_ejemplo import USUARIOS
from .modelos import Usuario
from .rutas import bp


def cargar_datos_ejemplo() -> None:
    if db.session.scalar(db.select(db.func.count()).select_from(Usuario)):
        return  # ya hay cuentas
    for datos in USUARIOS:
        datos = dict(datos)
        contrasena = datos.pop("contrasena")
        usuario = Usuario(**datos)
        usuario.cambiar_contrasena(contrasena)
        db.session.add(usuario)
    db.session.commit()


__all__ = ["bp", "cargar_datos_ejemplo"]
