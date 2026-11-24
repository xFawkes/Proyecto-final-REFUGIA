"""Mapa: catálogos fijos: tipos de lugar, servicios y niveles de verificación.

Las 'palabras_clave' se agregan al texto de búsqueda de cada punto, para que
buscar 'refugio' encuentre albergues o 'urgencias' encuentre hospitales.
"""

TIPOS = {
    "albergue": {
        "nombre": "Albergue",
        "plural": "Albergues",
        "palabras_clave": "albergue refugio alojamiento dormir techo",
    },
    "centro_salud": {
        "nombre": "Centro de salud",
        "plural": "Centros de salud",
        "palabras_clave": "centro de salud puesto de salud medico atencion medica clinica",
    },
    "hospital": {
        "nombre": "Hospital",
        "plural": "Hospitales",
        "palabras_clave": "hospital urgencias salud clinica medico",
    },
    "centro_acopio": {
        "nombre": "Centro de acopio",
        "plural": "Centros de acopio",
        "palabras_clave": "centro de acopio donaciones donar entregar ayudas",
    },
    "otro": {
        "nombre": "Otro punto de ayuda",
        "plural": "Otros puntos de ayuda",
        "palabras_clave": "punto de ayuda apoyo",
    },
}

SERVICIOS = {
    "refugio": "Refugio temporal",
    "alimentos": "Alimentos",
    "agua": "Agua potable",
    "atencion_medica": "Atención médica",
    "urgencias": "Urgencias 24 horas",
    "apoyo_psicosocial": "Apoyo psicosocial",
    "kits_aseo": "Kits de aseo",
    "ropa": "Ropa y cobijas",
    "recepcion_donaciones": "Recibe donaciones",
    "mascotas": "Admite mascotas",
    "carga_celulares": "Carga de celulares",
    "accesible": "Acceso para silla de ruedas",
}

# Niveles de confiabilidad definidos en el documento del proyecto
VERIFICACION = {
    "oficial": "Información oficial",
    "comunitaria": "Información comunitaria",
    "sin_confirmar": "Sin confirmar",
}
