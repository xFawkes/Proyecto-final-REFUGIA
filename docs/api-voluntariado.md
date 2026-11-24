# API de voluntariado

Sección `api/voluntariado` (Flask + Flask-SQLAlchemy + Marshmallow), hecha a partir de `api/_plantilla`.
Tabla en MySQL: **`voluntariados`** (se crea sola al iniciar `python main.py`, con 6 voluntariados de ejemplo).

## Quién la usa

| Página | JavaScript | Qué hace con la API |
|---|---|---|
| `voluntariado.html` | `js/voluntariado.js` | **GET**: muestra los voluntariados activos, con búsqueda, filtro por modalidad y "Ver más" |
| `admin/voluntariados.html` | `js/admin/voluntariados.js` | **CRUD completo**: publicar ("Aprobar"), revisar y editar, cerrar o reabrir, eliminar y subir la imagen |
| `admin/inicio.html` | `js/admin/panel.js` | **GET**: número de voluntariados activos |

## Rutas

| Método | Ruta | Qué hace | Respuesta |
|---|---|---|---|
| GET | `/api/voluntariados` | Lista, busca y filtra | `{ total, limite, offset, resultados: [...] }` |
| GET | `/api/voluntariados/<id>` | Un voluntariado | el voluntariado, o 404 |
| POST | `/api/voluntariados` | Crea un voluntariado | 201 + el voluntariado creado |
| PUT | `/api/voluntariados/<id>` | Actualiza (se pueden enviar solo los campos que cambian) | el voluntariado actualizado |
| DELETE | `/api/voluntariados/<id>` | Elimina (y borra su imagen si se subió desde el panel) | el voluntariado eliminado |
| GET | `/api/voluntariados/catalogos` | Modalidades y estados | `{ modalidades: [...], estados: [...] }` |
| POST | `/api/voluntariados/imagen` | Sube una imagen (*multipart*, campo `imagen`) | 201 + `{ "imagen": "img/subidas/voluntariado/….png" }` |

### Parámetros de `GET /api/voluntariados`

| Parámetro | Ejemplo | Qué hace |
|---|---|---|
| `q` | `?q=acopio bogota` | Cada palabra debe aparecer en la actividad, la organización, la descripción o la ubicación |
| `modalidad` | `?modalidad=presencial,mixta` | Una o varias: `presencial`, `virtual`, `mixta` |
| `estado` | `?estado=todos` | `activo` (por defecto), `cerrado` o `todos` |
| `limite`, `offset` | `?limite=8&offset=8` | Paginación (límite de 1 a 100, por defecto 20) |

Sin parámetros responde **solo los activos**, del más reciente al más antiguo.

## Campos (POST y PUT)

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---|---|
| `actividad` | texto | sí | 5 a 150 caracteres |
| `organizacion` | texto | sí | 2 a 150 caracteres |
| `descripcion` | texto | sí | 10 a 2000 caracteres (texto de la tarjeta) |
| `requisitos` | texto | no | uno por línea; en la página se muestran como lista |
| `modalidad` | texto | no | `presencial` (por defecto), `virtual` o `mixta` |
| `ubicacion` | texto | **sí, si no es virtual** | ciudad o lugar (máx. 150) |
| `enlace` | URL | no | enlace de inscripción; debe empezar por `http://` o `https://` |
| `imagen` | texto | no | `img/…` (imagen del proyecto o subida) o un enlace `https://` |
| `imagen_alt` | texto | **sí, si hay imagen** | descripción para lectores de pantalla (máx. 200) |
| `estado` | texto | no | `activo` (por defecto) o `cerrado` |

En PUT, las reglas que dependen de varios campos (ubicación según la modalidad, descripción de la
imagen) se revisan con lo que ya estaba guardado más lo que llega. Si no se cumplen, responde 400 y
no guarda nada.

Ejemplo de POST:

```json
{
  "actividad": "Apoyo en ollas comunitarias",
  "organizacion": "Junta de Acción Comunal",
  "descripcion": "Prepara y sirve alimentos para familias damnificadas.",
  "requisitos": "Mayor de edad\nCarné de manipulación de alimentos",
  "modalidad": "presencial",
  "ubicacion": "Bogotá, Kennedy",
  "enlace": "https://example.org/inscripcion"
}
```

## Cerrar o eliminar

- **Cerrar** (`PUT {"estado": "cerrado"}`): el voluntariado deja de aparecer en la página pero se
  conserva en el panel y se puede reabrir. Es lo recomendado cuando ya no recibe voluntarios.
- **Eliminar** (`DELETE`): lo borra de la base de datos.

## Pendiente

POST, PUT, DELETE y la subida de imágenes todavía no piden inicio de sesión. Se protegerán cuando
se implementen las sesiones del panel de administración.
