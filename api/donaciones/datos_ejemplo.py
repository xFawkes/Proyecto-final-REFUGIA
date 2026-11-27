"""Organizaciones de ejemplo: las mismas que tenía donaciones.html cuando era HTML fijo.

Se insertan solo la primera vez (si la tabla está vacía). Los enlaces están vacíos:
complétenlos con la página oficial de cada organización (aquí o desde el panel admin/donaciones.html).
No se crean donaciones de ejemplo: se generan al probar el formulario de donaciones.html.
"""

ORGANIZACIONES = [
    {
        "nombre": "Cruz Roja Colombia",
        "descripcion": (
            "Organización humanitaria con presencia en gran parte del país. Atiende emergencias y desastres "
            "con primeros auxilios, atención en salud, ayuda en albergues y entrega de kits de emergencia."
        ),
        "impacto": "llevar atención de primera respuesta y suministros básicos a las familias afectadas.",
        "imagen": "img/donaciones/cruz-roja.png",
        "imagen_alt": "Voluntario de la Cruz Roja Colombiana entregando ayuda",
    },
    {
        "nombre": "UNICEF Colombia",
        "descripcion": (
            "Agencia de las Naciones Unidas dedicada a proteger los derechos de niños, niñas y adolescentes. "
            "En emergencias trabaja para garantizar agua potable, salud, nutrición, educación y protección infantil."
        ),
        "impacto": "proteger a la infancia durante y después de un desastre.",
        "imagen": "img/donaciones/unicef.png",
        "imagen_alt": "Personal de UNICEF atendiendo a un niño",
    },
    {
        "nombre": "TECHO Colombia",
        "descripcion": (
            "Organización que trabaja junto a comunidades en situación de vulnerabilidad para mejorar su hábitat "
            "y acceso a vivienda digna. Moviliza voluntarios y apoya a las familias que perdieron sus hogares."
        ),
        "impacto": "construir soluciones de vivienda y fortalecer a las comunidades afectadas.",
        "imagen": "img/donaciones/techo.png",
        "imagen_alt": "Voluntarios de TECHO con la bandera de Colombia",
    },
]
