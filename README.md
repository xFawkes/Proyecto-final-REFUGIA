# REFUGIA

Plataforma web de ayuda humanitaria para personas afectadas por desastres naturales en Colombia.
Reúne en un solo lugar albergues, centros de salud, centros de acopio, donaciones, voluntariados,
noticias verificadas y un foro comunitario.

Proyecto de Tecnologías del Internet — Universidad Militar Nueva Granada, 2026.

**Tecnologías:** HTML, CSS y JavaScript en el frontend; API REST en Python con **Flask**,
**Flask-SQLAlchemy**, **Marshmallow** y **MySQL** (PyMySQL), siguiendo el tutorial de la materia.

---

## Estructura del proyecto

```
REFUGIA/
├── main.py                   ← inicia el servidor:  python main.py
├── inicio.html, mapa.html, noticias.html, voluntariado.html,
│   donaciones.html, foro.html, ayuda.html, perfil.html, error.html   ← páginas del sitio
├── admin/                    páginas del panel de administración
├── css/                      un archivo por página (mismo nombre que el .html)
│   ├── admin/                estilos del panel de administración
│   ├── menu-usuario.css      menú del perfil (compartido)
│   └── accesibilidad.css     alto contraste, tamaño de texto y avisos (compartido)
├── js/
│   ├── accesibilidad.js      voz, contraste y tamaño de texto (todas las páginas)
│   ├── api.js                cliente de la API (fetch, errores, fechas) para todas las páginas
│   ├── mapa.js               mapa, buscador y filtros
│   ├── noticias.js           pinta las noticias desde la API, con búsqueda
│   ├── voluntariado.js       pinta los voluntariados desde la API, con búsqueda
│   ├── donaciones.js         organizaciones, formulario de donación y pasarela de pagos simulada
│   ├── foro.js               foro: temas, respuestas, confirmar y denunciar
│   └── admin/                JavaScript del panel (un CRUD por página; panel.js: contadores)
├── img/                      imágenes compartidas (logo…) y una carpeta por sección
├── api/                      API en Flask
│   ├── __init__.py           arma la app: conexión a MySQL, secciones y páginas
│   ├── config.py             lee los datos de conexión del archivo .env
│   ├── extensiones.py        db (SQLAlchemy) y ma (Marshmallow), como en el tutorial
│   ├── errores.py            errores en JSON y en español
│   ├── paginas.py            sirve el HTML, CSS, JS e imágenes
│   ├── utilidades.py         funciones comunes (tildes, distancias, horarios)
│   ├── imagenes.py           subida de imágenes desde el panel (la usan todas las secciones)
│   ├── mapa/                 sección Mapa: modelos, esquemas, rutas (GET/POST/PUT/DELETE)
│   ├── noticias/             sección Noticias: igual, más subida de imágenes
│   ├── voluntariado/         sección Voluntariado: igual
│   ├── donaciones/           sección Donaciones: organizaciones (CRUD), donaciones y pasarela simulada
│   ├── foro/                 sección Foro: publicaciones, respuestas, denuncias y moderación
│   └── _plantilla/           punto de partida para crear una sección nueva
├── tests/                    pruebas automáticas (python -m pytest)
├── docs/
│   ├── api-mapa.md           detalle de la API del mapa y del módulo de accesibilidad
│   ├── api-noticias.md       detalle de la API de noticias y del panel de administración
│   ├── api-voluntariado.md   detalle de la API de voluntariado y de su panel
│   ├── api-donaciones.md     detalle de la API de donaciones y de la pasarela simulada (datos de prueba)
│   ├── api-foro.md           detalle de la API del foro y de la moderación
│   └── REFUGIA.postman_collection.json   peticiones listas para importar en Postman
├── requirements.txt          librerías de Python
└── .env.example              plantilla de la configuración de MySQL
```

### Convenciones

- **Nombres de archivo** en minúsculas, sin tildes ni espacios, con guiones: `fondo-portada.png`.
- **Imágenes**: van en `img/<sección>/`. Las que usan varias páginas (logo) van directo en `img/`.
- **CSS**: un archivo por página con el mismo nombre (`noticias.html` → `css/noticias.css`).
- **Accesibilidad**: toda página nueva lleva en el `<head>`:
  ```html
  <link rel="stylesheet" href="css/accesibilidad.css">
  <script src="js/accesibilidad.js"></script>
  ```
  y los botones con `id="btn-lector-voz"`, `id="btn-contraste"` e `id="btn-zoom"`.

---

## Cómo ejecutarlo

### 1. Requisitos (una sola vez)

- **Python 3.10 o superior.**
- **MySQL Server** y **MySQL Workbench** (los mismos del tutorial). Anota la contraseña del
  usuario `root` que pongas al instalarlo.

### 2. Entorno e instalación (una sola vez, en Windows, desde la carpeta del proyecto)

```powershell
python -m venv entorno_API
.\entorno_API\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Si PowerShell bloquea el script de activación, ejecuta antes:
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`

### 3. Configurar la conexión a MySQL (una sola vez)

Copia `.env.example` como `.env` y escribe tu contraseña de MySQL:

```
USUARIO_BD=root
PASSWORD_BD=tu_contraseña
SERVIDOR_BD=localhost
PUERTO_BD=3306
NOMBRE_BD=refugia
```

El archivo `.env` **no se sube a GitHub** (cada integrante tiene el suyo).
No hace falta crear la base de datos: si `refugia` no existe, el servidor la crea, crea las
tablas (`db.create_all()`, como en el tutorial) y carga los datos de ejemplo. En MySQL Workbench,
en *SCHEMAS*, haz clic en actualizar para verla.

### 4. Cada vez que vayas a trabajar

```powershell
.\entorno_API\Scripts\Activate.ps1
python main.py
```

| Qué | Dirección |
|---|---|
| Sitio | http://127.0.0.1:5000/ |
| Panel de administración | http://127.0.0.1:5000/admin/inicio.html |
| API (ejemplo) | http://127.0.0.1:5000/api/puntos |

Abre siempre el sitio desde `http://127.0.0.1:5000/`, no con doble clic sobre el `.html`: así el mapa
encuentra la API y OpenStreetMap no bloquea las imágenes. El sitio solo funciona mientras la
terminal con `python main.py` esté abierta (`Ctrl+C` lo detiene).

---

## La API

Cada sección tiene las operaciones del tutorial: **GET** (consultar), **POST** (crear),
**PUT** (actualizar) y **DELETE** (eliminar). Para probarlas en **Postman**, importa
`docs/REFUGIA.postman_collection.json` (*Import* → arrastra el archivo): trae todas las
peticiones listas, con ejemplos de JSON.

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/api/puntos` | Lista y filtra los puntos del mapa (`?q=albergue&tipo=hospital…`) |
| GET | `/api/puntos/<id>` | Un punto |
| POST | `/api/puntos` | Crea un punto (JSON en el *Body* → *raw* → *JSON*) |
| PUT | `/api/puntos/<id>` | Actualiza un punto; se pueden enviar solo los campos que cambian |
| DELETE | `/api/puntos/<id>` | Elimina un punto |
| GET | `/api/tipos`, `/api/servicios`, `/api/verificacion` | Catálogos para los filtros |
| GET | `/api/noticias` | Lista y busca noticias (`?q=sismo&verificacion=oficial&publicada=false`) |
| GET | `/api/noticias/<id>` | Una noticia |
| POST | `/api/noticias` | Crea una noticia |
| PUT | `/api/noticias/<id>` | Actualiza una noticia (ej. `{"publicada": true}` para aprobar un borrador) |
| DELETE | `/api/noticias/<id>` | Elimina una noticia |
| POST | `/api/noticias/imagen` | Sube una imagen (formulario *multipart*, campo `imagen`) |
| GET | `/api/voluntariados` | Lista y busca voluntariados (`?q=acopio&modalidad=virtual&estado=todos`) |
| GET | `/api/voluntariados/<id>` | Un voluntariado |
| POST | `/api/voluntariados` | Crea un voluntariado |
| PUT | `/api/voluntariados/<id>` | Actualiza un voluntariado (ej. `{"estado": "cerrado"}`) |
| DELETE | `/api/voluntariados/<id>` | Elimina un voluntariado |
| GET / POST | `/api/voluntariados/catalogos`, `/api/voluntariados/imagen` | Modalidades y estados; subir imagen |
| GET, POST, PUT, DELETE | `/api/organizaciones` y `/api/organizaciones/<id>` | CRUD de las organizaciones que reciben donaciones |
| POST | `/api/donaciones` | Crea una donación (queda pendiente de pago) |
| POST | `/api/donaciones/<referencia>/pago` | Paga en la **pasarela simulada** (no cobra dinero real) |
| GET | `/api/donaciones/<referencia>` | Comprobante de una donación |
| GET | `/api/donaciones`, `/api/donaciones/resumen` | Listado y total recaudado (panel de administración) |
| PUT, DELETE | `/api/donaciones/<referencia>` | Anular una donación aprobada o eliminar una no aprobada |
| GET, POST | `/api/foro/publicaciones` | Listar y crear temas del foro |
| GET, PUT, DELETE | `/api/foro/publicaciones/<id>` | Un tema con sus respuestas; moderar (aprobar u ocultar); eliminar |
| POST | `/api/foro/publicaciones/<id>/respuestas`, `/validar`, `/denuncias` | Responder, confirmar la información y denunciar |
| DELETE | `/api/foro/respuestas/<id>` | Eliminar una respuesta (moderación) |

Si los datos no son válidos, la API responde **400** con el detalle de cada campo en español.
Si el id no existe, responde **404**. El detalle de los campos y filtros está en
[`docs/api-mapa.md`](docs/api-mapa.md), [`docs/api-noticias.md`](docs/api-noticias.md),
[`docs/api-voluntariado.md`](docs/api-voluntariado.md), [`docs/api-donaciones.md`](docs/api-donaciones.md)
(con los datos de prueba de la pasarela de pagos) y [`docs/api-foro.md`](docs/api-foro.md).

> Las rutas POST, PUT y DELETE todavía no piden inicio de sesión. Cuando exista el login
> (requisito RF 7), hay que restringirlas a los administradores.

---

## Agregar una sección a la API (noticias, donaciones, voluntariado, foro…)

Cada sección es una carpeta dentro de `api/`, con las mismas piezas del tutorial:

| Archivo | Para qué | En el tutorial |
|---|---|---|
| `modelos.py` | La tabla, como clase de Python | `class Categoria(db.Model)` |
| `esquemas.py` | Convierte a JSON y valida | `CategoriaSchema`, `categoria_schema`, `categorias_schema` |
| `rutas.py` | GET, GET por id, POST, PUT, DELETE | las funciones `@app.route(...)` |
| `__init__.py` | Expone `bp` y `cargar_datos_ejemplo` | los `INSERT` de prueba en Workbench |

`api/noticias`, `api/voluntariado`, `api/donaciones` y `api/foro` son ejemplos completos hechos a partir de la plantilla (con
búsqueda, filtros, paginación, subida de imágenes y su página de administración en `admin/`).

Pasos, con una sección nueva "alertas" como ejemplo:

1. Copia `api/_plantilla` y renómbrala `api/alertas`.
2. En sus archivos cambia `Elemento`/`elementos` por `Alerta`/`alertas` y ajusta las columnas.
3. En `api/__init__.py`:
   ```python
   from . import alertas, donaciones, foro, mapa, noticias, paginas, voluntariado
   SECCIONES = [mapa, noticias, voluntariado, donaciones, foro, alertas]
   ```
4. Reinicia el servidor (`python main.py`). La tabla se crea sola en MySQL.

`db.create_all()` crea las tablas que faltan, pero **no modifica las que ya existen**. Si cambias
las columnas de una tabla que ya se creó, bórrala en MySQL Workbench (clic derecho → *Drop Table*)
y reinicia el servidor para que se cree de nuevo.

---

## Pruebas

```powershell
python -m pytest
```

Las pruebas usan una base SQLite temporal en memoria, así que no tocan tu base de MySQL ni necesitan
MySQL encendido. Para correrlas contra MySQL, usa una base **de pruebas**, que se borra y se crea de nuevo:

```powershell
$env:REFUGIA_TEST_DB = "mysql+pymysql://root:tu_contraseña@localhost:3306/refugia_pruebas"
python -m pytest
```

Prueban la búsqueda y los filtros, el CRUD completo (incluidos datos inválidos) y que todas las páginas
carguen sus CSS, scripts e imágenes.

---

## Trabajo en equipo con Git

- Trabaja cada funcionalidad en una rama (`feature/api-noticias`) y únela con un pull request.
- No se suben: `entorno_API/`, `.env` ni `__pycache__/` (ya están en `.gitignore`).
- Antes de subir cambios, corre `python -m pytest`.
- Si cambian las librerías, actualiza `requirements.txt`; los demás corren
  `python -m pip install -r requirements.txt` después de traer los cambios.
