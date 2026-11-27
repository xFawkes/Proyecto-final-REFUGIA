"""Voluntariados de ejemplo: los mismos que tenía voluntariado.html cuando era HTML fijo.

Se insertan solo la primera vez (si la tabla está vacía). La organización, la ubicación y
los enlaces son de relleno: cámbienlos desde el panel de administración
(admin/voluntariados.html) por los datos reales de cada voluntariado.
"""

ORGANIZACION = "Red de voluntarios REFUGIA"

VOLUNTARIADOS = [
    {
        "actividad": "Voluntariado en distribución de ayudas",
        "descripcion": (
            "Apoya la entrega de alimentos, ropa, agua y productos de primera necesidad a las "
            "personas afectadas por desastres naturales."
        ),
        "modalidad": "presencial",
        "ubicacion": "Bogotá",
        "imagen": "img/voluntariado/caja-alimentos.png",
        "imagen_alt": "Caja con frutas y alimentos para entregar como ayuda",
    },
    {
        "actividad": "Voluntariado en centros de acopio",
        "descripcion": (
            "Ayuda a clasificar, organizar y empacar las donaciones para garantizar que los "
            "recursos lleguen a quienes más los necesitan."
        ),
        "modalidad": "presencial",
        "ubicacion": "Bogotá",
        "imagen": "img/voluntariado/voluntarios-centro-acopio.png",
        "imagen_alt": "Voluntarios con camisetas rojas y credenciales en un centro de acopio",
    },
    {
        "actividad": "Voluntariado en reconstrucción",
        "descripcion": (
            "Participa en jornadas comunitarias de limpieza y recuperación de espacios afectados, "
            "siguiendo las indicaciones de las organizaciones responsables."
        ),
        "modalidad": "presencial",
        "ubicacion": "Bogotá",
        "imagen": "img/voluntariado/retiro-escombros.png",
        "imagen_alt": "Personas retirando escombros en una jornada de reconstrucción",
    },
    {
        "actividad": "Voluntariado de acompañamiento",
        "descripcion": (
            "Brinda compañía, escucha y apoyo humano a las personas damnificadas, en coordinación "
            "con equipos capacitados."
        ),
        "modalidad": "presencial",
        "ubicacion": "Bogotá",
        "imagen": "img/voluntariado/acompanamiento-damnificado.png",
        "imagen_alt": "Voluntario acompañando y saludando a una persona damnificada",
    },
    {
        "actividad": "Voluntariado en logística",
        "descripcion": (
            "Colabora con la organización y el transporte de suministros para facilitar que las "
            "ayudas lleguen a las zonas afectadas."
        ),
        "modalidad": "presencial",
        "ubicacion": "Bogotá",
        "imagen": "img/voluntariado/carga-suministros.png",
        "imagen_alt": "Voluntarios cargando suministros en una camioneta",
    },
    {
        "actividad": "Voluntariado digital",
        "descripcion": (
            "Utiliza tus habilidades para difundir información verificada, apoyar campañas "
            "solidarias y compartir oportunidades de ayuda en medios digitales."
        ),
        "modalidad": "virtual",
        "imagen": "img/voluntariado/voluntarios-donaciones.png",
        "imagen_alt": "Voluntarios trabajando con un portátil junto a cajas de donaciones",
    },
]
