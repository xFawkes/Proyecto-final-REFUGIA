# Mapa y accesibilidad

API en **Python (FastAPI + SQLite)** y frontend en **JavaScript** para la sección *Mapa* de REFUGIA:
muestra albergues, centros de salud, hospitales, centros de acopio y otros puntos de ayuda sobre un
mapa de **Leaflet + OpenStreetMap** (gratuito, sin API key ni facturación), con búsqueda, filtros, panel de detalle, acciones (Cómo llegar, Guardar, Contactar,
Compartir), "Cerca de mí" y un módulo de **accesibilidad reutilizable** en todas las páginas.

> **Los datos de ejemplo son ficticios** (26 puntos en Bogotá). Los teléfonos usan el prefijo
> `601 000` y los correos y páginas web el dominio `example.org`, para no apuntar a personas o
> entidades reales.

---

## 1. El mapa: Leaflet + OpenStreetMap

- No necesita API key, registro ni cuenta de facturación.
- `mapa.html` carga Leaflet 1.9.4 desde el CDN unpkg, con verificación de integridad (SRI).
- Las imágenes del mapa (teselas) vienen de los servidores de OpenStreetMap. Su política de uso
  permite proyectos con poco tráfico como este, siempre que se muestre la atribución
  "© OpenStreetMap" (ya aparece en la esquina del mapa). Si algún día el sitio tuviera mucho
  tráfico, se cambia la URL de las teselas en `mapa.js` por la de un proveedor comercial.
- Si no hay conexión al CDN, la página muestra un aviso y el buscador, los filtros y el panel de
  detalle siguen funcionando.

---

## 2. Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/puntos` | Busca y filtra puntos (parámetros abajo) |
| GET | `/api/puntos/{id}` | Detalle de un punto (`?lat=&lng=` agrega la distancia) |
| GET | `/api/tipos` | Tipos de lugar con su cantidad |
| GET | `/api/servicios` | Servicios por los que se puede filtrar |
| GET | `/api/verificacion` | Niveles de verificación |

### Parámetros de `/api/puntos`

| Parámetro | Ejemplo | Qué hace |
|---|---|---|
| `q` | `centros de salud suba` | Texto libre. Ignora tildes y mayúsculas, entiende plurales y sinónimos (*refugio* → albergues, *urgencias* → hospitales). Busca en nombre, tipo, descripción, dirección, barrio, localidad y servicios. |
| `tipo` | `tipo=hospital&tipo=centro_salud` | Uno o varios de: `albergue`, `centro_salud`, `hospital`, `centro_acopio`, `otro` |
| `servicio` | `servicio=refugio&servicio=mascotas` | El lugar debe ofrecer **todos** los servicios indicados |
| `verificacion` | `verificacion=oficial` | `oficial`, `comunitaria`, `sin_confirmar` |
| `abierto_ahora` | `true` | Abierto en este momento (hora de Colombia, incluye horarios que cruzan la medianoche) |
| `gratuito` | `true` | Sin costo |
| `con_cupos` | `true` | Albergues con cupos disponibles |
| `confianza_min` | `4.5` | Índice de confianza mínimo (0 a 5) |
| `ids` | `1,5,9` | Solo esos IDs (lo usa el filtro "mis lugares guardados") |
| `lat`, `lng` | `4.7392`, `-74.0987` | Ubicación del usuario: agrega `distancia_km` a cada resultado |
| `radio_km` | `5` | Solo lugares a esa distancia o menos (requiere `lat` y `lng`) |
| `orden` | `distancia` | `relevancia`, `distancia`, `confianza` o `nombre`. Por defecto: relevancia si hay texto, distancia si hay ubicación, si no confianza |
| `limite`, `offset` | `20`, `40` | Paginación |

Ejemplo: albergues gratuitos con cupos a menos de 3 km que admitan mascotas:

```
/api/puntos?tipo=albergue&gratuito=true&con_cupos=true&servicio=mascotas&lat=4.74&lng=-74.1&radio_km=3
```

Las respuestas van comprimidas con gzip: la lista completa pesa unos 4 KB.

---

## 3. Módulo de accesibilidad en las demás páginas

`js/accesibilidad.js` no depende del mapa. Para usarlo en `noticias.html`, `foro.html`, etc.:

**1.** En el `<head>`, **sin `defer`** (así el contraste y el tamaño se aplican antes de pintar):

```html
<link rel="stylesheet" href="css/accesibilidad.css">
<script src="js/accesibilidad.js"></script>
```

**2.** Usa los mismos `id` de los botones de `mapa.html` (`btn-lector-voz`, `btn-contraste`,
`btn-zoom`), o el atributo `data-a11y="voz"`, `data-a11y="contraste"`, `data-a11y="zoom"`.

**3.** (Opcional) Pon `data-a11y-leer` en la sección que se debe leer. Si no hay ninguna, se lee el
`<main>`.

Funcionamiento:

- **Leer en voz alta**: lee el texto seleccionado; si no hay selección, la zona marcada o el `<main>`.
  Un segundo clic o la tecla `Escape` detienen la lectura. En el mapa se lee la información del lugar
  seleccionado en frases completas.
- **Alto contraste**: redefine las variables de color del proyecto (`--azul`, `--amarillo`, etc.) a
  negro, blanco y amarillo intenso. Funciona en las páginas que usan esas variables. Los colores
  escritos directamente en el CSS (`#111`, `#dfe6e9`…) no cambian.
- **Ampliar texto**: 100 % → 115 % → 130 % → 150 % → 100 %. Escala lo que esté en `rem`/`em`; lo que esté
  en `px` no cambia.
- Las preferencias se guardan en el navegador y se mantienen al cambiar de página.
- Si el sistema operativo pide más contraste (`prefers-contrast: more`), se activa solo la primera vez.

Desde otros scripts puedes usar `Accesibilidad.anunciar("Mensaje")` para mostrar un aviso que
también lee el lector de pantalla, y `Accesibilidad.definirLectura(() => "texto")` para decidir qué
se lee en esa página.

---

## 4. Comportamiento de la página del mapa

- **Buscador**: muestra sugerencias mientras escribes. Se puede manejar con el teclado (↑ ↓ Enter
  Escape) y con lector de pantalla (patrón *combobox*). Los marcadores del mapa se filtran al mismo
  tiempo.
- **Filtros**: tipo de lugar, abierto ahora, cupos, sin costo, guardados, cerca de mí con radio,
  confianza mínima, nivel de verificación y servicios. El botón del embudo muestra cuántos filtros
  están activos.
- **Detalle**: además de los campos de la maqueta, muestra el tipo, el nivel de verificación, la
  descripción, la distancia, si está abierto ahora, los cupos (albergues), los servicios, la fuente
  y la fecha de actualización.
- **Cómo llegar**: abre la ruta en Google Maps (en el celular, en la app). Es un enlace normal, no
  usa la API de Google, así que no necesita clave ni facturación.
- **Guardar**: guarda el lugar en este navegador (`localStorage`). Cuando exista el inicio de sesión
  (RF 7) se puede pasar a la base de datos.
- **Contactar**: si el lugar tiene un solo canal, lo abre; si tiene varios, muestra un menú con
  Llamar, WhatsApp y Correo.
- **Compartir**: usa el menú de compartir del celular; en computador copia el enlace. El enlace
  (`mapa.html?punto=12`) abre la página con ese lugar seleccionado.
- **Marcadores**: se pueden recorrer con `Tab` y abrir con `Enter` o `Espacio`.
- **Cerca de mí**: botón en el mapa o casilla en los filtros. El navegador solo da la ubicación en
  `localhost` o en sitios con HTTPS.

---

## 5. Dónde está el código y los datos

| Qué | Archivo |
|---|---|
| Endpoints | `api/mapa/rutas.py` |
| Búsqueda y filtros | `api/mapa/busqueda.py` |
| Tablas y carga inicial | `api/mapa/tablas.py` |
| Los 26 puntos de ejemplo | `api/mapa/datos_ejemplo.py` |
| Tipos, servicios y niveles de verificación | `api/mapa/catalogos.py` |
| Horarios, distancias y búsqueda sin tildes | `api/utilidades.py` |
| Frontend | `mapa.html`, `js/mapa.js`, `css/mapa.css` |

Los datos se copian a `api/refugia.db` la primera vez que arranca el servidor. Si editas
`datos_ejemplo.py`, detén el servidor, borra `api/refugia.db` y vuelve a iniciarlo.
