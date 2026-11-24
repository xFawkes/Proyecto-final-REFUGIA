# API de noticias

Sección `api/noticias` (Flask + Flask-SQLAlchemy + Marshmallow), hecha a partir de `api/_plantilla`.
Tabla en MySQL: **`noticias`** (se crea sola al iniciar `python main.py`, con 5 noticias de ejemplo).

## Quién la usa

| Página | JavaScript | Qué hace con la API |
|---|---|---|
| `noticias.html` | `js/noticias.js` | **GET**: muestra las noticias publicadas, con búsqueda, filtro por verificación y "Ver más" |
| `admin/noticias.html` | `js/admin/noticias.js` | **CRUD completo**: crear, editar, aprobar/ocultar y eliminar, y subir la imagen |
| `admin/inicio.html` | `js/admin/panel.js` | **GET**: número de borradores de noticias |

Las tres usan `js/api.js`, el cliente común de la API (sirve también para las demás secciones).

## Rutas

| Método | Ruta | Qué hace | Respuesta |
|---|---|---|---|
| GET | `/api/noticias` | Lista, busca y filtra | `{ total, limite, offset, resultados: [...] }` |
| GET | `/api/noticias/<id>` | Una noticia | la noticia, o 404 |
| POST | `/api/noticias` | Crea una noticia | 201 + la noticia creada |
| PUT | `/api/noticias/<id>` | Actualiza (se pueden enviar solo los campos que cambian) | la noticia actualizada |
| DELETE | `/api/noticias/<id>` | Elimina (y borra su imagen si se subió desde el panel) | la noticia eliminada |
| GET | `/api/noticias/verificacion` | Niveles de verificación | `[{ clave, nombre }]` |
| POST | `/api/noticias/imagen` | Sube una imagen (*multipart*, campo `imagen`) | 201 + `{ "imagen": "img/subidas/noticias/….png" }` |

### Parámetros de `GET /api/noticias`

| Parámetro | Ejemplo | Qué hace |
|---|---|---|
| `q` | `?q=sismo caldas` | Cada palabra debe aparecer en el título, el contenido o la fuente |
| `verificacion` | `?verificacion=oficial,en_verificacion` | Uno o varios niveles |
| `destacada` | `?destacada=true` | Solo la destacada |
| `publicada` | `?publicada=false` | `false` = solo borradores; `true` = solo publicadas |
| `incluir_ocultas` | `?incluir_ocultas=true` | Publicadas **y** borradores (lo usa el panel) |
| `limite`, `offset` | `?limite=9&offset=9` | Paginación (límite de 1 a 100, por defecto 20) |

Sin parámetros responde **solo las publicadas**, la destacada primero y luego de la más reciente a la más antigua.

## Campos (POST y PUT)

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---|---|
| `titulo` | texto | sí | 5 a 200 caracteres |
| `contenido` | texto | sí | 10 a 5000 caracteres. Una línea en blanco separa los párrafos |
| `fuente` | texto | sí | 2 a 150 caracteres (UNGRD, IDIGER…) |
| `enlace` | URL | no | debe empezar por `http://` o `https://` |
| `imagen` | texto | no | `img/…` (imagen del proyecto o subida) o un enlace `https://` |
| `imagen_alt` | texto | **sí, si hay imagen** | descripción para lectores de pantalla (máx. 200) |
| `verificacion` | texto | no | `oficial` (por defecto), `en_verificacion` o `sin_verificar` |
| `destacada` | booleano | no | solo puede haber una: al marcar una, las demás se desmarcan |
| `publicada` | booleano | no | `true` por defecto; `false` = borrador (no sale en `noticias.html`) |
| `fecha_publicacion` | fecha | no | `AAAA-MM-DD`; si no llega, la de hoy |

Los textos vacíos (`""`) de los campos opcionales se guardan como `null`. Un campo desconocido
responde 400, para detectar errores de escritura.

Ejemplo de POST:

```json
{
  "titulo": "Alerta por lluvias en Bogotá",
  "contenido": "El IDIGER recomienda evitar zonas de ladera.\n\nSegundo párrafo.",
  "fuente": "IDIGER",
  "enlace": "https://www.idiger.gov.co",
  "verificacion": "oficial",
  "publicada": false
}
```

Error de validación (400):

```json
{
  "error": "Los datos enviados no son válidos.",
  "detalles": { "titulo": ["Debe tener entre 5 y 200 caracteres."] }
}
```

## Imágenes subidas

- Se aceptan PNG, JPG, WEBP y GIF de hasta 5 MB. Se revisa el contenido del archivo, no solo la extensión.
- Se guardan en `img/subidas/noticias/` con un nombre aleatorio. Esa carpeta **no se sube a GitHub**
  (está en `.gitignore`), igual que la base de datos: cada integrante tiene las suyas.

## Pendiente

POST, PUT, DELETE y la subida de imágenes todavía no piden inicio de sesión. Se protegerán cuando
se implementen las sesiones del panel de administración.
