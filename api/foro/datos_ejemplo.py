"""Publicaciones de ejemplo del foro (reemplazan el "Lorem ipsum" que tenía foro.html).

Son FICTICIAS: personas, lugares y situaciones inventadas para que el foro y el panel de
moderación no aparezcan vacíos. Se insertan solo la primera vez (si la tabla está vacía).
"""

PUBLICACIONES = [
    {
        "titulo": "Busco a mi tío: lo vieron por última vez cerca del albergue de Kennedy",
        "contenido": (
            "Mi tío salió el martes en la mañana y no ha regresado. Tiene 72 años, usa bastón y llevaba "
            "una chaqueta azul. Si alguien lo ha visto, por favor respondan aquí o avisen en el albergue."
        ),
        "categoria": "desaparecidos",
        "ubicacion": "Bogotá, Kennedy",
        "autor": "Usuario de ejemplo",
        "verificacion": "confirmada",
        "validaciones": 4,
        "respuestas": [
            ("Voluntaria del albergue", "Ya compartimos la información con el equipo de registro del albergue."),
            ("Vecino de Patio Bonito", "Lo compartí en el grupo del barrio. Mucha fuerza."),
        ],
    },
    {
        "titulo": "Albergue en Bosa necesita cobijas, pañales y leche para bebés",
        "contenido": (
            "En el albergue temporal hay 40 familias, varias con bebés. Hacen falta cobijas, pañales de "
            "las tallas 2 y 3 y leche de fórmula. Se reciben en la portería de 8:00 a. m. a 6:00 p. m."
        ),
        "categoria": "necesidades",
        "ubicacion": "Bogotá, Bosa",
        "autor": "Coordinación de albergue (ejemplo)",
        "verificacion": "confirmada",
        "validaciones": 7,
        "respuestas": [("Ana (ejemplo)", "Mañana llevo dos paquetes de pañales talla 3.")],
    },
    {
        "titulo": "Ofrezco transporte para llevar donaciones el sábado",
        "contenido": (
            "Tengo una camioneta y el sábado puedo llevar donaciones desde el norte de Bogotá hasta los "
            "centros de acopio del sur. Escriban aquí qué necesitan mover."
        ),
        "categoria": "ofrecimientos",
        "ubicacion": "Bogotá",
        "autor": "Carlos (ejemplo)",
        "verificacion": "sin_confirmar",
        "validaciones": 1,
        "respuestas": [],
    },
    {
        "titulo": "Deslizamiento en la vía: tránsito cerrado desde la madrugada",
        "contenido": (
            "Un conductor contó que la vía está cerrada por un deslizamiento. Todavía no hay un comunicado "
            "oficial. Si alguien tiene información confirmada, por favor compártala."
        ),
        "categoria": "alertas",
        "ubicacion": "Cundinamarca",
        "autor": "Usuario de ejemplo",
        "verificacion": "sin_confirmar",
        "validaciones": 0,
        "respuestas": [],
        "denuncias": [("falsa", "No encontré ningún reporte oficial de este cierre.")],
    },
    {
        "titulo": "¿Cómo saber si un centro de acopio es confiable?",
        "contenido": (
            "Quiero donar ropa y alimentos, pero no sé cómo verificar que un centro de acopio sea serio. "
            "¿Qué recomiendan revisar antes de llevar las donaciones?"
        ),
        "categoria": "general",
        "ubicacion": None,
        "autor": "Usuario de ejemplo",
        "verificacion": "confirmada",
        "validaciones": 2,
        "respuestas": [
            ("Moderación REFUGIA", "Revisa en el mapa de REFUGIA si el centro aparece como verificado y busca "
                                    "que tenga respaldo de una entidad oficial o de una organización reconocida."),
        ],
    },
]
