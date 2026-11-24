"""Noticias de ejemplo: las mismas que tenía noticias.html cuando era HTML fijo.

Se insertan solo la primera vez (si la tabla está vacía). Las fuentes y fechas son
aproximadas y los enlaces están vacíos: complétenlos desde el panel de administración
(admin/noticias.html) con el enlace oficial de cada noticia.
"""

from datetime import date

NOTICIAS = [
    {
        "titulo": "Colombia continúa la recuperación tras el terremoto de magnitud 7,4 en Chocó",
        "contenido": (
            "El sismo ocurrido el 10 de agosto de 2026, con epicentro en San José del Palmar, Chocó, afectó "
            "a comunidades de distintas regiones del país. Según el balance oficial de octubre, más de "
            "778.000 personas resultaron afectadas y cientos de miles de viviendas sufrieron daños o "
            "quedaron destruidas.\n\n"
            "Las labores de recuperación incluyen la atención a las familias damnificadas, la "
            "rehabilitación de viviendas y la recuperación de infraestructura educativa…"
        ),
        "fuente": "UNGRD",
        "imagen": "img/noticias/terremoto-choco.png",
        "imagen_alt": "Edificios destruidos tras el terremoto en Chocó",
        "verificacion": "oficial",
        "destacada": True,
        "fecha_publicacion": date(2026, 10, 20),
    },
    {
        "titulo": "Más de 105.000 personas participan en el Simulacro Nacional de Emergencias",
        "contenido": (
            "La jornada puso a prueba medidas de autoprotección y protocolos de respuesta ante "
            "diferentes escenarios, incluidos sismos, inundaciones e incendios…"
        ),
        "fuente": "UNGRD",
        "imagen": "img/noticias/simulacro-plaza-bolivar.png",
        "imagen_alt": "Multitud participando en el simulacro en la Plaza de Bolívar",
        "verificacion": "oficial",
        "fecha_publicacion": date(2026, 10, 16),
    },
    {
        "titulo": "UNGRD destina recursos para apoyar a familias damnificadas en Caldas",
        "contenido": (
            "La Unidad Nacional para la Gestión del Riesgo de Desastres anunció más de $3.647 millones "
            "para apoyar económicamente a familias afectadas por el sismo ocurrido en agosto…"
        ),
        "fuente": "UNGRD",
        "imagen": "img/noticias/ayudas-caldas.png",
        "imagen_alt": "Familias damnificadas recibiendo ayudas en Caldas",
        "verificacion": "oficial",
        "fecha_publicacion": date(2026, 10, 14),
    },
    {
        "titulo": "Continúa la recuperación de las comunidades afectadas por el sismo de agosto",
        "contenido": (
            "Dos meses después del terremoto con epicentro en Chocó, los reportes de la UNGRD daban "
            "cuenta de cientos de miles de personas damnificadas y numerosas viviendas averiadas…"
        ),
        "fuente": "UNGRD",
        "imagen": "img/noticias/vivienda-averiada.png",
        "imagen_alt": "Personas conversando frente a una vivienda averiada por el sismo",
        "verificacion": "oficial",
        "fecha_publicacion": date(2026, 10, 10),
    },
    {
        "titulo": "Lluvias dejan emergencias en varios municipios de Cundinamarca",
        "contenido": (
            "Durante los primeros trece días de octubre se reportaron inundaciones, vendavales, "
            "deslizamientos y crecientes súbitas. Las autoridades atendieron afectaciones en viviendas "
            "y vías…"
        ),
        "fuente": "Gestión del riesgo de Cundinamarca",
        "imagen": "img/noticias/deslizamiento-cundinamarca.png",
        "imagen_alt": "Maquinaria despejando un deslizamiento en una vía de Cundinamarca",
        "verificacion": "en_verificacion",
        "fecha_publicacion": date(2026, 10, 14),
    },
]
