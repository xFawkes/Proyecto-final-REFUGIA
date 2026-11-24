"""Pruebas de la sección Mapa.  Ejecutar desde la raíz del proyecto:  python -m pytest"""

from datetime import datetime

import pytest

from api.utilidades import ZONA_COLOMBIA, esta_abierto, horario_legible


def nombres(respuesta):
    return [p["nombre"] for p in respuesta.json()["resultados"]]


def test_lista_todos(cliente):
    r = cliente.get("/api/puntos")
    assert r.status_code == 200
    assert r.json()["total"] == 26


def test_busqueda_sin_tildes_y_en_plural(cliente):
    assert "Centro de Salud Engativá" in nombres(cliente.get("/api/puntos", params={"q": "centros de salud engativa"}))
    assert all("Hospital" in n for n in nombres(cliente.get("/api/puntos", params={"q": "hospitales"})))


def test_busqueda_por_sinonimo_y_direccion(cliente):
    assert nombres(cliente.get("/api/puntos", params={"q": "refugio bosa"}))[0] == "Albergue Polideportivo Bosa"
    assert nombres(cliente.get("/api/puntos", params={"q": "calle 132"})) == ["Centro de Acopio Tibabuyes"]


def test_busqueda_con_caracteres_especiales(cliente):
    assert cliente.get("/api/puntos", params={"q": "100%_"}).json()["total"] == 0


def test_filtro_por_varios_tipos(cliente):
    datos = cliente.get("/api/puntos", params=[("tipo", "hospital"), ("tipo", "centro_salud")]).json()
    assert datos["total"] == 9
    assert {p["tipo"] for p in datos["resultados"]} == {"hospital", "centro_salud"}


def test_filtro_cupos_excluye_albergues_llenos(cliente):
    datos = cliente.get("/api/puntos", params={"con_cupos": True}).json()
    assert datos["total"] > 0
    assert all(p["cupos_disponibles"] > 0 for p in datos["resultados"])
    assert "Albergue Coliseo Engativá" not in [p["nombre"] for p in datos["resultados"]]


def test_filtro_servicios_exige_todos(cliente):
    datos = cliente.get("/api/puntos", params=[("servicio", "refugio"), ("servicio", "mascotas")]).json()
    for p in datos["resultados"]:
        claves = {s["clave"] for s in p["servicios"]}
        assert {"refugio", "mascotas"} <= claves


def test_filtro_gratuito_confianza_y_verificacion(cliente):
    datos = cliente.get(
        "/api/puntos", params={"gratuito": True, "confianza_min": 4.5, "verificacion": "oficial"}
    ).json()
    assert datos["total"] > 0
    for p in datos["resultados"]:
        assert p["gratuito"] and p["confianza"] >= 4.5 and p["verificacion"] == "oficial"


def test_cerca_de_mi_ordena_por_distancia(cliente):
    datos = cliente.get("/api/puntos", params={"lat": 4.7392, "lng": -74.0987, "radio_km": 2}).json()
    distancias = [p["distancia_km"] for p in datos["resultados"]]
    assert distancias == sorted(distancias)
    assert all(d <= 2 for d in distancias)
    assert datos["resultados"][0]["nombre"] == "Centro de Acopio Tibabuyes"


def test_ids_guardados(cliente):
    datos = cliente.get("/api/puntos", params={"ids": "1,3"}).json()
    assert sorted(p["id"] for p in datos["resultados"]) == [1, 3]
    assert cliente.get("/api/puntos", params={"ids": ""}).json()["total"] == 0


def test_paginacion(cliente):
    datos = cliente.get("/api/puntos", params={"limite": 5, "offset": 5, "orden": "nombre"}).json()
    assert datos["total"] == 26 and len(datos["resultados"]) == 5


@pytest.mark.parametrize(
    "params",
    [
        {"radio_km": 5},                 # radio sin ubicación
        {"orden": "distancia"},          # orden por distancia sin ubicación
        {"lat": 4.6},                    # lat sin lng
        {"servicio": "inventado"},
        {"tipo": "inventado"},
        {"confianza_min": 9},
        {"ids": "1,a"},
    ],
)
def test_parametros_invalidos(cliente, params):
    assert cliente.get("/api/puntos", params=params).status_code == 422


def test_detalle(cliente):
    p = cliente.get("/api/puntos/1", params={"lat": 4.74, "lng": -74.1}).json()
    assert p["nombre"] == "Centro de Acopio Tibabuyes"
    assert p["horario_texto"] == "Lunes a viernes, de 8:00 a. m. a 7:00 p. m."
    assert p["distancia_km"] is not None
    assert cliente.get("/api/puntos/9999").status_code == 404


def test_catalogos(cliente):
    tipos = cliente.get("/api/tipos").json()
    assert sum(t["total"] for t in tipos) == 26
    assert len(cliente.get("/api/servicios").json()) == 12


# ---------------- Horarios ----------------
def momento(dia_semana, hora, minuto=0):
    # 2026-11-23 fue lunes
    return datetime(2026, 11, 23 + dia_semana, hora, minuto, tzinfo=ZONA_COLOMBIA)


def test_horario_normal():
    lv = [{"dias": [0, 1, 2, 3, 4], "abre": "08:00", "cierra": "19:00"}]
    assert esta_abierto(lv, momento(0, 8))
    assert not esta_abierto(lv, momento(0, 19))
    assert not esta_abierto(lv, momento(5, 10))  # sábado


def test_horario_que_cruza_medianoche():
    noche = [{"dias": [4], "abre": "18:00", "cierra": "07:00"}]  # viernes 6 p. m. a sábado 7 a. m.
    assert esta_abierto(noche, momento(4, 23))
    assert esta_abierto(noche, momento(5, 6, 59))
    assert not esta_abierto(noche, momento(5, 7))
    assert not esta_abierto(noche, momento(3, 2))


def test_horario_24_horas_y_texto():
    h24 = [{"dias": list(range(7)), "abre": "00:00", "cierra": "24:00"}]
    assert esta_abierto(h24, momento(6, 23, 59))
    assert horario_legible(h24) == "Todos los días, 24 horas."
