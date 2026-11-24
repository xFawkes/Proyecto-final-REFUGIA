"""Donaciones: catálogos y datos de prueba de la pasarela de pagos SIMULADA.

La pasarela no cobra nada ni se conecta con ningún banco. Solo acepta los datos de prueba
de este archivo, para que nadie escriba (ni se guarde) una tarjeta real.
"""

FRECUENCIAS = {
    "unica": "Una vez",
    "mensual": "Mensual",
}

ESTADOS = {
    "pendiente": "Pendiente de pago",
    "aprobada": "Aprobada",
    "rechazada": "Rechazada",
    "anulada": "Anulada",  # el administrador la anuló (simula un reembolso)
}

METODOS = {
    "tarjeta": "Tarjeta de crédito o débito",
    "transferencia": "Transferencia bancaria (simulación de PSE)",
    "billetera": "Billetera digital",
}

MONTO_MINIMO = 10_000
MONTO_MAXIMO = 20_000_000
DESTINO_GENERAL = "Donde más se necesite"

# ---------------------------------------------------------------------------
# Datos de prueba (los mismos que usan las pasarelas reales en su "modo sandbox")
# ---------------------------------------------------------------------------
TARJETAS_PRUEBA = {
    "4242424242424242": {"franquicia": "Visa", "aprobada": True, "mensaje": "Pago aprobado."},
    "5555555555554444": {"franquicia": "Mastercard", "aprobada": True, "mensaje": "Pago aprobado."},
    "4000000000000002": {"franquicia": "Visa", "aprobada": False, "mensaje": "Pago rechazado: fondos insuficientes."},
}

BANCOS_PRUEBA = {
    "banco_aprueba": {"nombre": "Banco de pruebas (aprueba el pago)", "aprobada": True,
                      "mensaje": "Transferencia aprobada."},
    "banco_rechaza": {"nombre": "Banco de pruebas (rechaza el pago)", "aprobada": False,
                      "mensaje": "Transferencia rechazada por el banco."},
}

BILLETERAS_PRUEBA = {
    "3001234567": {"aprobada": True, "mensaje": "Pago aprobado desde la billetera."},
    "3009999999": {"aprobada": False, "mensaje": "Pago rechazado: el usuario no aceptó la solicitud."},
}
