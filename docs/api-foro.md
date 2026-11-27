# API del foro

Sección `api/foro` (Flask + Flask-SQLAlchemy + Marshmallow). Crea tres tablas en MySQL, relacionadas
con llaves foráneas:

- **`publicaciones`**: cada tema del foro (con 5 publicaciones de ejemplo, ficticias).
- **`respuestas`**: los mensajes de cada tema (`id_publicacion`, se borran con la publicación).
- **`denuncias`**: los reportes de los usuarios (`id_publicacion`, se borran con la publicación).

## Quién la usa

| Página | JavaScript | Qué hace con la API |
|---|---|---|
| `foro.html` | `js/foro.js` | Listar, buscar y filtrar por tema; ver un tema (`foro.html?publicacion=3`); publicar, responder, confirmar y denunciar |
| `admin/foro.html` | `js/admin/foro.js` | Moderación: aprobar, ocultar, mostrar y eliminar publicaciones y respuestas; ver las denuncias |
| `admin/inicio.html` | `js/admin/panel.js` | Tarjeta "Reportes" y tabla "Tareas pendientes" |

## Cómo funciona la moderación

1. Toda publicación nueva queda **sin confirmar**. Se ve en el foro con esa etiqueta y un aviso.
2. Cualquier persona puede **confirmar** la información (contador de validaciones) o **denunciarla**.
3. Con **3 denuncias sin revisar**, la publicación se **oculta** sola hasta que la revise un moderador.
4. El moderador ve en "Por revisar" las publicaciones sin confirmar, con denuncias o ocultas (primero
   las denunciadas). Puede:
   - **Aprobar**: queda confirmada y visible, y sus denuncias quedan revisadas.
   - **Ocultar / Mostrar**, **Eliminar** la publicación o **eliminar respuestas** sueltas.

Para **publicar y responder** hay que iniciar sesión: el `autor` es el nombre de quien inició sesión
(no se puede publicar a nombre de otra persona). **Confirmar y denunciar** siguen abiertos a todos;
la página evita que el mismo navegador lo haga dos veces (con `localStorage`). La **moderación** es
solo para administradores.

## Rutas

### Comunidad (`foro.html`)

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/api/foro/catalogos` | Categorías, niveles de verificación y motivos de denuncia |
| GET | `/api/foro/publicaciones` | Listar (no incluye las ocultas). Ordena por la actividad más reciente |
| GET | `/api/foro/publicaciones/<id>` | Una publicación con sus respuestas (404 si está oculta) |
| POST | `/api/foro/publicaciones` | Crear (queda sin confirmar). **Con sesión** |
| POST | `/api/foro/publicaciones/<id>/respuestas` | Responder (el tema sube al primer lugar). **Con sesión** |
| POST | `/api/foro/publicaciones/<id>/validar` | Confirmar la información (+1) |
| POST | `/api/foro/publicaciones/<id>/denuncias` | Denunciar (`motivo` y `detalle` opcional) |

### Moderación (`admin/foro.html`, solo administradores)

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/api/foro/publicaciones?moderacion=true&revision=pendiente` | Lo que hay que revisar (`revision=ocultas` para las ocultas) |
| GET | `/api/foro/publicaciones/<id>?moderacion=true` | Incluye las denuncias y funciona aunque esté oculta |
| PUT | `/api/foro/publicaciones/<id>` | Aprobar `{"verificacion": "confirmada", "oculta": false}`, ocultar `{"oculta": true}` o corregir título, contenido, tema o ubicación |
| DELETE | `/api/foro/publicaciones/<id>` | Eliminar con sus respuestas y denuncias |
| DELETE | `/api/foro/respuestas/<id>` | Eliminar una respuesta |

### Parámetros de `GET /api/foro/publicaciones`

| Parámetro | Ejemplo | Qué hace |
|---|---|---|
| `q` | `?q=albergue bosa` | Cada palabra debe aparecer en el título, el contenido, la ubicación o el autor |
| `categoria` | `?categoria=desaparecidos,alertas` | `desaparecidos`, `necesidades`, `ofrecimientos`, `alertas`, `general` |
| `verificacion` | `?verificacion=confirmada` | `sin_confirmar` o `confirmada` |
| `moderacion` | `?moderacion=true` | Incluye las ocultas (panel) |
| `revision` | `?revision=pendiente` | `pendiente` u `ocultas` (con `moderacion=true`) |
| `limite`, `offset` | `?limite=10&offset=10` | Paginación (límite de 1 a 100, por defecto 20) |

## Campos

**Publicación (POST):** `titulo` (5 a 150), `contenido` (10 a 3000), `categoria` (por defecto `general`),
y `ubicacion` (opcional, máx. 150). El `autor` no se envía: la API usa el nombre de quien inició sesión
(si se envía, se ignora). El público no puede enviar `verificacion`: una publicación no se puede
confirmar a sí misma.

**Respuesta:** `contenido` (2 a 2000); el autor también sale de la sesión.

**Denuncia:** `motivo` (`falsa`, `ofensiva`, `datos_personales`, `spam`, `otro`) y `detalle` (opcional, máx. 300).

## Sesiones

Sin sesión, `POST` de publicaciones y respuestas responde **401**; las rutas de moderación responden
**401** sin sesión y **403** a un usuario que no es administrador. Ver qué rutas piden sesión en [`api-sesiones.md`](api-sesiones.md).
