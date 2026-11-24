"""
REFUGIA — servidor del proyecto: API + páginas del sitio.

Ejecutar desde la carpeta raíz del proyecto (donde está inicio.html):

    uvicorn api.main:app --reload

  • Sitio:                    http://127.0.0.1:8000/
  • Documentación de la API:  http://127.0.0.1:8000/docs

Para agregar una sección nueva (noticias, donaciones…): copia la carpeta
api/_plantilla, renómbrala y agrégala a la lista SECCIONES de abajo.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import database, mapa

# ---------------------------------------------------------------------------
# Secciones de la API. Para agregar una: from . import noticias  y  SECCIONES = [mapa, noticias]
# ---------------------------------------------------------------------------
SECCIONES = [mapa]

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Configuración (.env opcional en la raíz del proyecto)
# ---------------------------------------------------------------------------
def cargar_env(ruta: Path = RAIZ_PROYECTO / ".env") -> None:
    """Lee un archivo .env sencillo (CLAVE=valor) sin dependencias extra."""
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


cargar_env()


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    database.inicializar_bd(SECCIONES)
    yield


app = FastAPI(
    title="REFUGIA — API",
    description="API de la plataforma de ayuda humanitaria REFUGIA.",
    version="1.1.0",
    lifespan=ciclo_de_vida,
)

# Comprime las respuestas (bajo consumo de datos)
app.add_middleware(GZipMiddleware, minimum_size=500)

# Permite llamar la API desde Live Server de VS Code (puerto 5500)
origenes = ["http://localhost:5500", "http://127.0.0.1:5500"]
origenes += [o.strip() for o in os.environ.get("REFUGIA_CORS", "").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origenes, allow_methods=["GET"], allow_headers=["*"])

for seccion in SECCIONES:
    app.include_router(seccion.router)


# ---------------------------------------------------------------------------
# Páginas del sitio. IMPORTANTE: esta parte va después de los routers.
# Solo se publican las carpetas y extensiones del frontend: nunca .env,
# la base de datos, el código de la API ni el entorno virtual.
# ---------------------------------------------------------------------------
for carpeta in ("css", "js", "img", "admin"):
    if (RAIZ_PROYECTO / carpeta).is_dir():
        app.mount(f"/{carpeta}", StaticFiles(directory=RAIZ_PROYECTO / carpeta, html=True), name=carpeta)

EXTENSIONES_PUBLICAS = {".html", ".webmanifest", ".ico", ".png", ".svg"}
ARCHIVOS_PUBLICOS = {"sw.js", "service-worker.js", "manifest.json"}


@app.get("/", include_in_schema=False)
def inicio():
    return RedirectResponse("/inicio.html")


@app.api_route("/{archivo}", methods=["GET", "HEAD"], include_in_schema=False)
def archivo_raiz(archivo: str):
    ruta = (RAIZ_PROYECTO / archivo).resolve()
    publico = ruta.suffix.lower() in EXTENSIONES_PUBLICAS or ruta.name in ARCHIVOS_PUBLICOS
    if not publico or ruta.parent != RAIZ_PROYECTO or not ruta.is_file():
        error = RAIZ_PROYECTO / "error.html"
        if error.is_file() and archivo.endswith(".html"):
            return FileResponse(error, status_code=404)  # página 404 del proyecto
        raise HTTPException(404, "Página no encontrada")
    return FileResponse(ruta)
