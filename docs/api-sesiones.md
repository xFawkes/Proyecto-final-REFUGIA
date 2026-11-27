# API de usuarios y sesiones

Sección `api/usuarios` (Flask + Flask-SQLAlchemy + Marshmallow) y el archivo compartido
`api/autenticacion.py`. Crea una tabla en MySQL:

- **`usuarios`**: las cuentas, con su **rol** (`usuario` o `administrador`). La contraseña se guarda
  como **hash** (con `werkzeug.security`, que ya viene con Flask): nunca se guarda ni se devuelve
  la contraseña escrita.

## Cuentas de prueba

Se crean solas la primera vez que se inicia el servidor (si la tabla `usuarios` está vacía).
Son ficticias y solo sirven para probar:

| Rol | Usuario | Correo | Contraseña | Al entrar va a… |
|---|---|---|---|---|
| Administrador | `admin` | admin@refugia.test | `Admin2026*` | `admin/inicio.html` |
| Administrador | `coordinacion` | coordinacion@refugia.test | `Admin2026*` | `admin/inicio.html` |
| Usuario | `ana.gomez` | ana.gomez@refugia.test | `Usuario2026*` | `inicio.html` |
| Usuario | `carlos.rojas` | carlos.rojas@refugia.test | `Usuario2026*` | `inicio.html` |
| Usuario (desactivada) | `cuenta.inactiva` | cuenta.inactiva@refugia.test | `Usuario2026*` | No puede entrar |

Se puede escribir el **nombre de usuario o el correo**. Si el sitio se publica, cambien estas
contraseñas (en *Mi perfil*) o eliminen las cuentas (en `admin/usuarios.html`).

## Quién la usa

| Página | JavaScript | Qué hace con la API |
|---|---|---|
| `iniciar-sesion.html` | `js/acceso.js` | Iniciar sesión; lleva al panel (admin) o al inicio (usuario) |
| `registro.html` | `js/acceso.js` | Crear una cuenta de usuario (queda con la sesión iniciada) |
| Todas las páginas | `js/sesion.js` | Nombre en el menú de usuario, opciones según la sesión y *Cerrar sesión* |
| `perfil.html` | `js/perfil.js` | Ver y editar mis datos; cambiar mi contraseña |
| `foro.html` | `js/foro.js` | Publicar y responder piden sesión; el autor es quien inició sesión |
| `donaciones.html` | `js/donaciones.js` | Si hay sesión, llena el nombre y el correo del donante |
| `admin/usuarios.html` | `js/admin/usuarios.js` | Listar cuentas, cambiar rol, activar/desactivar, contraseña temporal, eliminar |
| `admin/*.html` | `js/sesion.js` | Solo para administradores; enlace *Cerrar sesión* |

## Cómo funciona la sesión

1. `POST /api/sesion` revisa el usuario y la contraseña. Si son correctos, Flask guarda el id del
   usuario en una **cookie firmada** (`refugia_sesion`) con la `SECRET_KEY`. La cookie es
   `HttpOnly` (JavaScript no la puede leer) y `SameSite=Lax` (otros sitios no la pueden usar).
2. En cada petición, `api/autenticacion.py` lee la cookie y busca al usuario en la base de datos.
   Si lo desactivaron o le cambiaron la contraseña, la sesión deja de servir.
3. La sesión dura **12 horas**; después hay que volver a entrar. `DELETE /api/sesion` la cierra.
4. La `SECRET_KEY` se lee de `CLAVE_SECRETA` en el `.env`. Si no está, se crea una al azar en el
   archivo `.clave_secreta` (no se sube a GitHub). Si se borra ese archivo, todas las sesiones se cierran.

Con Live Server (puerto 5500) también funciona: `js/api.js` envía la cookie (`credentials: "include"`)
y la API lo permite (`supports_credentials=True` en CORS). Abran Live Server y la API con el mismo
nombre: `127.0.0.1` con `127.0.0.1` (o `localhost` con `localhost`).

### Proteger una ruta

```python
from ..autenticacion import requiere_admin, requiere_sesion, usuario_actual

@bp.route("", methods=["POST"])
@requiere_admin                  # 401 sin sesión, 403 si no es administrador
def insert_noticia(): ...

@bp.route("/publicaciones", methods=["POST"])
@requiere_sesion                 # cualquier persona con sesión iniciada
def insert_publicacion():
    autor = usuario_actual().nombre_visible
```

### Qué rutas están protegidas

| Sección | Solo administradores | Con sesión | Abiertas a todos |
|---|---|---|---|
| Mapa | POST, PUT, DELETE `/api/puntos` | — | Consultas |
| Noticias | POST, PUT, DELETE, imagen; `?publicada=…` e `?incluir_ocultas=true`; ver un borrador | — | Noticias publicadas |
| Voluntariado | POST, PUT, DELETE, imagen; `?estado=cerrado` o `todos` | — | Voluntariados activos |
| Donaciones | Organizaciones (POST, PUT, DELETE, imagen, `?incluir_inactivas=true`); listado, resumen, anular y eliminar donaciones | — | Donar, pagar y ver el comprobante |
| Foro | Moderación (`?moderacion=true`, PUT, DELETE) | Publicar y responder | Leer, confirmar y denunciar |
| Usuarios | Listar, ver, editar, eliminar y contraseña temporal | Mi perfil y mi contraseña | Registro, iniciar y cerrar sesión |

Las páginas del panel (`admin/*.html`) también se protegen: si Flask sirve el sitio, `api/paginas.py`
lleva a `iniciar-sesion.html?siguiente=/admin/…` a quien no es administrador; con Live Server lo hace
`js/sesion.js` (`<body data-requiere="admin">`). `perfil.html` pide sesión (`data-requiere="sesion"`).

## Rutas

### Sesión

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/api/sesion` | ¿Quién soy? `{"autenticado": true, "usuario": {...}}` o `{"autenticado": false, "usuario": null}` |
| POST | `/api/sesion` | Iniciar sesión `{"usuario": "admin", "contrasena": "Admin2026*"}` |
| DELETE | `/api/sesion` | Cerrar sesión |

Respuesta de `POST /api/sesion` (200):

```json
{
  "mensaje": "Hola, Administración REFUGIA.",
  "usuario": {
    "id_usuario": 1, "nombre_usuario": "admin", "correo": "admin@refugia.test",
    "nombre": "Administración REFUGIA", "nombre_visible": "Administración REFUGIA",
    "telefono": null, "ubicacion": null, "rol": "administrador", "rol_nombre": "Administrador",
    "activo": true, "creado_en": "2026-11-27T17:20-05:00", "ultimo_acceso": "2026-11-27T17:32-05:00"
  },
  "redireccion": "admin/inicio.html"
}
```

| Código | Cuándo |
|---|---|
| 401 | `"Usuario o contraseña incorrectos."` (el mismo mensaje si el usuario no existe, para no revelar qué cuentas hay) |
| 403 | La cuenta está desactivada |
| 400 | Falta el usuario o la contraseña |

### Cuenta propia

| Método | Ruta | Qué hace |
|---|---|---|
| POST | `/api/usuarios` | Registro: `{"nombre_usuario", "correo", "contrasena", "nombre" (opcional)}`. Crea un **usuario** (nunca administrador) e inicia su sesión. 201 |
| PUT | `/api/usuarios/yo` | Editar mis datos: `nombre`, `correo`, `telefono`, `ubicacion` (solo los que cambian; `""` borra los opcionales) |
| PUT | `/api/usuarios/yo/contrasena` | `{"actual": "…", "nueva": "…"}`. Cierra mis sesiones en otros dispositivos |

Reglas:

- **Nombre de usuario**: 3 a 30 caracteres, letras sin tilde, números, punto, guion o guion bajo.
  Se guarda en minúsculas (`Ana.Gomez` → `ana.gomez`). No se puede repetir.
- **Correo**: válido, en minúsculas, no se puede repetir.
- **Contraseña**: 8 a 128 caracteres, con al menos una letra y un número.
- **Teléfono** (opcional): 7 a 20 caracteres, solo números, espacios, `+`, `-` y paréntesis.

### Panel de administración

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/api/usuarios/catalogos` | Roles (para formularios y filtros) |
| GET | `/api/usuarios` | Listar: `?q=ana&rol=administrador&activo=false&limite=20&offset=0`. Primero los administradores |
| GET | `/api/usuarios/<id>` | Una cuenta |
| PUT | `/api/usuarios/<id>` | Cambiar `rol`, `activo`, `nombre`, `correo`, `telefono` o `ubicacion`. Desactivar cierra su sesión |
| DELETE | `/api/usuarios/<id>` | Eliminar la cuenta (sus publicaciones del foro se conservan con su nombre) |
| POST | `/api/usuarios/<id>/contrasena-temporal` | Genera una contraseña temporal de 10 caracteres y la responde **una sola vez** |

Un administrador **no puede** quitarse su propio rol, desactivarse ni eliminarse (409): así el panel
nunca se queda sin administradores.

### Recuperar la contraseña

No se envían correos. En *¿Olvidaste tu nombre de usuario o contraseña?* se explica que se puede
entrar con el correo, y que un administrador genera una **contraseña temporal** desde
`admin/usuarios.html`; la persona entra con ella y la cambia en *Mi perfil*.

## Tabla `usuarios`

| Columna | Tipo | Notas |
|---|---|---|
| `id_usuario` | INT | Llave primaria |
| `nombre_usuario` | VARCHAR(30) | Único, en minúsculas |
| `correo` | VARCHAR(120) | Único, en minúsculas |
| `contrasena` | VARCHAR(255) | **Hash** de la contraseña (nunca la contraseña) |
| `rol` | VARCHAR(20) | `usuario` o `administrador` |
| `nombre`, `telefono`, `ubicacion` | VARCHAR | Opcionales (Mi perfil) |
| `activo` | BOOLEAN | `false` = no puede iniciar sesión |
| `version_sesion` | INT | Cambia al cambiar la contraseña o desactivar: cierra las sesiones abiertas |
| `creado_en`, `ultimo_acceso` | DATETIME | Hora de Colombia |

Para volver a las cuentas de prueba: en MySQL Workbench borra la tabla `usuarios`
(`DROP TABLE usuarios;`) y reinicia el servidor.

## Postman

En la colección (`docs/REFUGIA.postman_collection.json`), la carpeta **Sesión y usuarios** va
primero: ejecuta **Iniciar sesión (admin)** antes de probar las rutas de crear, editar o borrar de
las demás carpetas. Postman guarda la cookie de sesión y la envía sola en las siguientes peticiones.
**Cerrar sesión** la borra (las rutas protegidas vuelven a responder 401).
