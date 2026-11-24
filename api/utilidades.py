"""Funciones de apoyo: normalización de texto, distancias y horarios."""

from __future__ import annotations

import math
import unicodedata
from datetime import datetime, timedelta, timezone

# Colombia no tiene horario de verano: UTC-5 fijo.
# Se usa un offset fijo para no depender del paquete tzdata en Windows.
ZONA_COLOMBIA = timezone(timedelta(hours=-5), name="America/Bogota")

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def normalizar(texto: str | None) -> str:
    """Minúsculas y sin tildes, para que 'clinica' encuentre 'Clínica'."""
    if not texto:
        return ""
    sin_tildes = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    return " ".join(sin_tildes.lower().split())


def distancia_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distancia en línea recta (fórmula de Haversine)."""
    radio_tierra = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radio_tierra * math.asin(math.sqrt(a))


# ---------------------------------------------------------------------------
# Horarios
# Formato guardado: lista de franjas
#   [{"dias": [0, 1, 2, 3, 4], "abre": "08:00", "cierra": "19:00"}]
# 0 = lunes ... 6 = domingo. "24:00" como cierre = medianoche.
# Si cierra < abre, la franja cruza la medianoche (ej. 20:00 a 06:00).
# ---------------------------------------------------------------------------

def _minutos(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def esta_abierto(franjas: list[dict], ahora: datetime | None = None) -> bool:
    ahora = (ahora or datetime.now(ZONA_COLOMBIA)).astimezone(ZONA_COLOMBIA)
    dia = ahora.weekday()
    minuto = ahora.hour * 60 + ahora.minute
    dia_anterior = (dia - 1) % 7

    for franja in franjas:
        abre, cierra = _minutos(franja["abre"]), _minutos(franja["cierra"])
        if abre < cierra:
            if dia in franja["dias"] and abre <= minuto < cierra:
                return True
        else:  # cruza la medianoche
            if dia in franja["dias"] and minuto >= abre:
                return True
            if dia_anterior in franja["dias"] and minuto < cierra:
                return True
    return False


def _hora_legible(hhmm: str) -> str:
    minutos = _minutos(hhmm)
    if minutos in (0, 1440):
        return "12:00 a. m."
    h, m = divmod(minutos, 60)
    sufijo = "a. m." if h < 12 else "p. m."
    h12 = h % 12 or 12
    return f"{h12}:{m:02d} {sufijo}"


def _dias_legibles(dias: list[int]) -> str:
    dias = sorted(set(dias))
    if dias == list(range(7)):
        return "Todos los días"
    # Agrupar días consecutivos: [0,1,2,3,4] -> "lunes a viernes"
    grupos: list[list[int]] = []
    for d in dias:
        if grupos and d == grupos[-1][-1] + 1:
            grupos[-1].append(d)
        else:
            grupos.append([d])
    partes = []
    for g in grupos:
        if len(g) >= 3:
            partes.append(f"{DIAS[g[0]]} a {DIAS[g[-1]]}")
        else:
            partes.extend(DIAS[d] for d in g)
    texto = partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " y " + partes[-1]
    return texto[0].upper() + texto[1:]


def horario_legible(franjas: list[dict]) -> str:
    """[{dias:[0..4], abre:'08:00', cierra:'19:00'}] -> 'Lunes a viernes, de 8:00 a. m. a 7:00 p. m.'"""
    if not franjas:
        return "Horario no informado"
    textos = []
    for f in franjas:
        dias = _dias_legibles(f["dias"])
        if f["abre"] == "00:00" and f["cierra"] in ("24:00", "00:00"):
            textos.append(f"{dias}, 24 horas")
        else:
            textos.append(f"{dias}, de {_hora_legible(f['abre'])} a {_hora_legible(f['cierra'])}")
    # Cada franja termina en punto ("p. m." ya lo trae)
    return " ".join(t if t.endswith(".") else t + "." for t in textos)
