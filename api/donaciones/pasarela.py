"""Pasarela de pagos SIMULADA.

Imita el flujo de una pasarela real (Wompi, ePayco, PayU…) en su modo de pruebas:
  1. La página crea la donación  → queda "pendiente" con una referencia.
  2. La página envía el pago     → la pasarela responde "aprobada" o "rechazada".
  3. La página muestra el comprobante.

No cobra dinero ni se conecta con ningún banco. Solo acepta los datos de prueba de
catalogos.py: cualquier otra tarjeta, banco o celular se rechaza con un error 400, y
nunca se guarda el número completo de la tarjeta ni el CVV.

Para conectar una pasarela real habría que cambiar solo procesar_pago() por la llamada
a la API del proveedor (con sus llaves de prueba) y recibir su confirmación (webhook).
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from marshmallow import ValidationError

from .catalogos import BANCOS_PRUEBA, BILLETERAS_PRUEBA, TARJETAS_PRUEBA

AVISO_PRUEBA = "Esta pasarela es de prueba: usa uno de los datos de prueba (nunca datos reales)."


@dataclass
class ResultadoPago:
    aprobada: bool
    detalle: str        # lo que se guarda del medio de pago (sin datos sensibles)
    mensaje: str
    codigo: str | None  # código de autorización (solo si se aprueba)


def codigo_autorizacion() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def procesar_pago(pago: dict) -> ResultadoPago:
    """Recibe los datos ya validados por PagoSchema y decide el resultado."""
    metodo = pago["metodo"]

    if metodo == "tarjeta":
        numero = pago["tarjeta"]["numero"]
        prueba = TARJETAS_PRUEBA.get(numero)
        if prueba is None:
            raise ValidationError({"tarjeta": {"numero": [AVISO_PRUEBA]}})
        detalle = f"{prueba['franquicia']} terminada en {numero[-4:]}"
    elif metodo == "transferencia":
        prueba = BANCOS_PRUEBA[pago["banco"]]  # PagoSchema ya revisó que sea un banco de prueba
        detalle = prueba["nombre"]
    else:  # billetera
        celular = pago["celular"]
        prueba = BILLETERAS_PRUEBA.get(celular)
        if prueba is None:
            raise ValidationError({"celular": [AVISO_PRUEBA]})
        detalle = f"Billetera digital ***{celular[-4:]}"

    return ResultadoPago(
        aprobada=prueba["aprobada"],
        detalle=detalle,
        mensaje=prueba["mensaje"],
        codigo=codigo_autorizacion() if prueba["aprobada"] else None,
    )
