# REFUGIA

Plataforma web de ayuda humanitaria para personas afectadas por desastres naturales en Colombia.
Reúne en un solo lugar albergues, centros de salud, centros de acopio, donaciones, voluntariados,
noticias verificadas y un foro comunitario.

Proyecto de Tecnologías del Internet — Universidad Militar Nueva Granada, 2026.

---

## Estructura del proyecto

```
REFUGIA/
├── inicio.html, mapa.html, noticias.html, voluntariado.html,
│   donaciones.html, foro.html, ayuda.html, perfil.html, error.html   ← páginas del sitio
├── admin/                    páginas del panel de administración
│   ├── inicio.html, noticias.html, foro.html, voluntariados.html
├── css/                      un archivo por página (mismo nombre que el .html)
│   ├── admin/                estilos del panel de administración
│   ├── menu-usuario.css      menú del perfil (compartido)
│   └── accesibilidad.css     alto contraste, tamaño de texto y avisos (compartido)
├── js/
│   ├── accesibilidad.js      voz, contraste y tamaño de texto (todas las páginas)
│   └── mapa.js               mapa, buscador y filtros
├── img/                      imágenes compartidas (logo…) y una carpeta por sección
│   ├── inicio/  mapa/  noticias/  voluntariado/  donaciones/
├── api/                      servidor y API en Python (FastAPI + SQLite)
│   ├── main.py               arranca el servidor y registra las secciones
│   ├── database.py           conexión a la base de datos (compartida)
│   ├── utilidades.py         funciones comunes (tildes, distancias, horarios)
│   ├── mapa/                 sección Mapa: rutas, tablas, búsqueda, datos de ejemplo
│   └── _plantilla/           punto de partida para crear una sección nueva
├── tests/                    pruebas automáticas (python -m pytest)
├── docs/
│   └── api-mapa.md           detalle de la API del mapa y del módulo de accesibilidad
├── requirements.txt          dependencias de Python
└── .env.example              configuración opcional
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

No se necesita XAMPP ni otro servidor: Uvicorn sirve las páginas y la API, y la base de datos es
el archivo `api/refugia.db`, que se crea solo.

### La primera vez (en Windows, desde la carpeta del proyecto)

```powershell
python -m venv entorno_API
.\entorno_API\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Si PowerShell bloquea el script de activación, ejecuta antes:
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`

### Cada vez que vayas a trabajar

```powershell
.\entorno_API\Scripts\Activate.ps1
uvicorn api.main:app --reload
```

| Qué | Dirección |
|---|---|
| Sitio | http://127.0.0.1:8000/ |
| Panel de administración | http://127.0.0.1:8000/admin/inicio.html |
| Documentación de la API | http://127.0.0.1:8000/docs |

El sitio solo funciona mientras la terminal con `uvicorn` esté abierta. Si mueves o renombras la
carpeta del proyecto, borra `entorno_API` y créalo de nuevo (los entornos virtuales guardan su ruta).

---

## Agregar una sección a la API (noticias, donaciones, voluntariado, foro…)

Cada sección es una carpeta dentro de `api/` con cuatro archivos:

| Archivo | Para qué |
|---|---|
| `rutas.py` | Los endpoints (`/api/noticias`, `/api/noticias/{id}`…) |
| `tablas.py` | Las tablas de la base de datos y la carga de datos de ejemplo |
| `modelos.py` | La forma del JSON que devuelve cada endpoint |
| `__init__.py` | Expone `router` e `inicializar` para que `main.py` los registre |

Pasos, con "noticias" como ejemplo:

1. Copia `api/_plantilla` y renómbrala `api/noticias`.
2. En sus archivos cambia `elemento`/`elementos` por `noticia`/`noticias` y ajusta las columnas.
3. En `api/main.py`:
   ```python
   from . import database, mapa, noticias
   SECCIONES = [mapa, noticias]
   ```
4. Borra `api/refugia.db` si cambiaste tablas existentes y reinicia `uvicorn`.
   Los endpoints nuevos aparecen en http://127.0.0.1:8000/docs.

La sección **Mapa** (`api/mapa/`) es un ejemplo completo con búsqueda, filtros y paginación.
Su documentación está en [`docs/api-mapa.md`](docs/api-mapa.md).

---

## Pruebas

```powershell
python -m pytest
```

Además de la API del mapa, las pruebas recorren todas las páginas y verifican que carguen sus CSS,
scripts e imágenes. Si renombras o mueves un archivo y olvidas actualizar una ruta, fallan.

---

## Trabajo en equipo con Git

- Trabaja cada funcionalidad en una rama (`feature/api-noticias`) y únela a `main` con un pull request.
- No se suben: `entorno_API/`, `api/refugia.db`, `.env` ni `__pycache__/` (ya están en `.gitignore`).
  Cada integrante crea su entorno y su base de datos al ejecutar el proyecto.
- Antes de subir cambios, corre `python -m pytest`.
