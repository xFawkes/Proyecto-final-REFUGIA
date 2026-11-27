"""Cuentas de PRUEBA para iniciar sesión (datos ficticios).

Se insertan solo la primera vez (si la tabla "usuarios" está vacía). Las contraseñas se
guardan como hash, igual que las de las cuentas que se crean desde registro.html.

    Rol             Usuario             Contraseña
    Administrador   admin               Admin2026*
    Administrador   coordinacion        Admin2026*
    Usuario         ana.gomez           Usuario2026*
    Usuario         carlos.rojas        Usuario2026*
    Usuario         cuenta.inactiva     Usuario2026*   (desactivada: no puede entrar)

También se puede entrar con el correo en lugar del nombre de usuario.
IMPORTANTE: son solo para probar. Si el sitio se publica, cambien estas contraseñas
(Mi perfil) o eliminen las cuentas desde el panel (admin/usuarios.html).
"""

CONTRASENA_ADMIN = "Admin2026*"
CONTRASENA_USUARIO = "Usuario2026*"

USUARIOS = [
    {
        "nombre_usuario": "admin",
        "correo": "admin@refugia.test",
        "nombre": "Administración REFUGIA",
        "rol": "administrador",
        "contrasena": CONTRASENA_ADMIN,
    },
    {
        "nombre_usuario": "coordinacion",
        "correo": "coordinacion@refugia.test",
        "nombre": "Coordinación de voluntariado",
        "rol": "administrador",
        "ubicacion": "Bogotá",
        "contrasena": CONTRASENA_ADMIN,
    },
    {
        "nombre_usuario": "ana.gomez",
        "correo": "ana.gomez@refugia.test",
        "nombre": "Ana Gómez",
        "rol": "usuario",
        "telefono": "3001234567",
        "ubicacion": "Manizales, Caldas",
        "contrasena": CONTRASENA_USUARIO,
    },
    {
        "nombre_usuario": "carlos.rojas",
        "correo": "carlos.rojas@refugia.test",
        "nombre": "Carlos Rojas",
        "rol": "usuario",
        "ubicacion": "Quibdó, Chocó",
        "contrasena": CONTRASENA_USUARIO,
    },
    {
        "nombre_usuario": "cuenta.inactiva",
        "correo": "cuenta.inactiva@refugia.test",
        "nombre": "Cuenta desactivada",
        "rol": "usuario",
        "activo": False,
        "contrasena": CONTRASENA_USUARIO,
    },
]
