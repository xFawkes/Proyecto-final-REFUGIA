"""Pruebas del servidor de páginas: que todo el sitio cargue y que no se expongan archivos privados."""

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
PAGINAS = sorted(p.relative_to(RAIZ).as_posix() for p in [*RAIZ.glob("*.html"), *RAIZ.glob("admin/*.html")])


def test_inicio_redirige(cliente):
    r = cliente.get("/", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/inicio.html"


@pytest.mark.parametrize("pagina", PAGINAS)
def test_pagina_y_sus_recursos_locales_cargan(cliente, pagina):
    r = cliente.get(f"/{pagina}")
    assert r.status_code == 200, pagina
    base = "/" + pagina.rsplit("/", 1)[0] + "/" if "/" in pagina else "/"
    for ref in re.findall(r'(?:href|src|poster)="([^"#?]+)', r.text):
        if ref.startswith(("http", "mailto:", "tel:", "data:", "javascript:")):
            continue
        ruta = ref if ref.startswith("/") else base + ref
        ruta = re.sub(r"[^/]+/\.\./", "", ruta)
        assert cliente.head(ruta).status_code == 200, f"{pagina} → {ref}"


def test_imagenes_de_los_css(cliente):
    for css in RAIZ.glob("css/**/*.css"):
        base = "/" + css.parent.relative_to(RAIZ).as_posix() + "/"
        for ref in re.findall(r'url\(["\']?([^"\')]+)', css.read_text(encoding="utf-8")):
            if ref.startswith(("http", "data:")):
                continue
            ruta = re.sub(r"[^/]+/\.\./", "", base + ref)
            assert cliente.head(ruta).status_code == 200, f"{css.name} → {ref}"


def test_pagina_inexistente_muestra_error_html(cliente):
    r = cliente.get("/no-existe.html")
    assert r.status_code == 404 and "Página no encontrada" in r.text


@pytest.mark.parametrize(
    "ruta", ["/.env", "/.env.example", "/requirements.txt", "/api/main.py", "/api/refugia.db",
             "/..%2F.env", "/.git/config", "/tests/conftest.py", "/README.md"],
)
def test_no_expone_archivos_privados(cliente, ruta):
    assert cliente.get(ruta).status_code == 404, ruta
