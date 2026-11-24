# API de donaciones y pasarela de pagos simulada

Sección `api/donaciones` (Flask + Flask-SQLAlchemy + Marshmallow). Crea dos tablas en MySQL:

- **`organizaciones`**: las ONG que reciben donaciones (con 3 de ejemplo: Cruz Roja, UNICEF y TECHO).
- **`donaciones`**: cada donación y el resultado de su pago. Se relaciona con `organizaciones`
  (llave foránea `id_organizacion`).

> **La pasarela es una simulación con fines académicos.** No cobra dinero, no se conecta con
> ningún banco y solo acepta los datos de prueba de abajo. Cualquier otra tarjeta se rechaza con
> un error 400, así que nadie puede escribir (ni guardar) una tarjeta real. Del medio de pago solo
> se guarda la franquicia y los últimos 4 dígitos, como hacen las pasarelas reales.

## Quién la usa

| Página | JavaScript | Qué hace con la API |
|---|---|---|
| `donaciones.html` | `js/donaciones.js` | Muestra las organizaciones, crea la donación, la paga en la pasarela y muestra el comprobante |
| `admin/donaciones.html` | `js/admin/donaciones.js` | Resumen de lo recaudado, listado de donaciones (anular / eliminar) y CRUD de organizaciones |

## Flujo de una donación (como una pasarela real)

```
donaciones.html                        API                                  MySQL
 1. "Donar"          → POST /api/donaciones                   → INSERT  (estado: pendiente, referencia RFG-…)
 2. "Pagar"          → POST /api/donaciones/<referencia>/pago → UPDATE  (estado: aprobada o rechazada)
 3. Comprobante      ← respuesta del paso 2 (o GET /api/donaciones/<referencia>)
```

Si el pago se rechaza, se puede intentar otra vez con otro medio. Una donación aprobada no se
puede pagar de nuevo (409).

### Datos de prueba

| Medio | Dato | Resultado |
|---|---|---|
| Tarjeta | `4242 4242 4242 4242` (Visa) | Aprobada |
| Tarjeta | `5555 5555 5555 4444` (Mastercard) | Aprobada |
| Tarjeta | `4000 0000 0000 0002` (Visa) | Rechazada: fondos insuficientes |
| Transferencia | `banco_aprueba` | Aprobada |
| Transferencia | `banco_rechaza` | Rechazada |
| Billetera digital | celular `3001234567` | Aprobada |
| Billetera digital | celular `3009999999` | Rechazada |

Con tarjeta: vencimiento futuro en formato `MM/AA` (ej. `12/30`) y cualquier CVV de 3 dígitos.
El número también debe cumplir el algoritmo de Luhn (el dígito de control de las tarjetas).
En la página, "Ver datos de prueba" tiene un botón **Usar** que los llena solo.

## Rutas

### Organizaciones (CRUD)

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/api/organizaciones` | Las activas (`?incluir_inactivas=true` para todas) |
| GET | `/api/organizaciones/<id>` | Una organización |
| POST | `/api/organizaciones` | Crear (`nombre` y `descripcion` obligatorios; el nombre no se puede repetir) |
| PUT | `/api/organizaciones/<id>` | Actualizar (ej. `{"activa": false}` para ocultarla) |
| DELETE | `/api/organizaciones/<id>` | Eliminar. Sus donaciones se conservan con el nombre guardado en `destino` |
| POST | `/api/organizaciones/imagen` | Subir una imagen (*multipart*, campo `imagen`) |

### Donaciones

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/api/donaciones/pasarela` | Medios de pago, montos permitidos y datos de prueba |
| POST | `/api/donaciones` | Crear la donación (queda `pendiente`) |
| POST | `/api/donaciones/<referencia>/pago` | Pagar en la pasarela simulada |
| GET | `/api/donaciones/<referencia>` | Comprobante (el correo sale oculto: `a***@correo.com`) |
| GET | `/api/donaciones` | Listado para el panel (`?estado=aprobada&q=Ana&limite=20&offset=0`) |
| GET | `/api/donaciones/resumen` | Total recaudado (solo aprobadas), cantidad por estado y por destino |
| PUT | `/api/donaciones/<referencia>` | Anular una aprobada (`{"estado": "anulada"}`, simula un reembolso) o agregar una `nota` |
| DELETE | `/api/donaciones/<referencia>` | Eliminar (no se puede si está aprobada: primero se anula) |

### Campos de `POST /api/donaciones`

| Campo | Obligatorio | Reglas |
|---|---|---|
| `monto` | sí | entero en pesos, de 10.000 a 20.000.000 |
| `frecuencia` | no | `unica` (por defecto) o `mensual` (simulada: solo se registra el primer pago) |
| `id_organizacion` | no | una organización activa; `null` = "Donde más se necesite" |
| `nombre_donante` | sí | 2 a 120 caracteres |
| `correo` | sí | correo válido (se guarda en minúsculas) |

### Cuerpo de `POST /api/donaciones/<referencia>/pago`

```json
{ "metodo": "tarjeta", "tarjeta": { "titular": "Ana Pérez", "numero": "4242 4242 4242 4242", "vencimiento": "12/30", "cvv": "123" } }
{ "metodo": "transferencia", "banco": "banco_aprueba" }
{ "metodo": "billetera", "celular": "3001234567" }
```

## Cómo se conectaría una pasarela real

Todo lo simulado está en `api/donaciones/pasarela.py`, en la función `procesar_pago()`. Para usar una
pasarela real (Wompi, ePayco, PayU…) habría que reemplazar esa función por la llamada a la API del
proveedor con sus llaves de prueba, y recibir su confirmación en una ruta nueva (*webhook*). Con una
pasarela real, los datos de la tarjeta no pasan por nuestro servidor: los recibe directamente el
formulario o widget del proveedor.

## Pendiente

Las rutas del panel (listar, anular y eliminar donaciones, y el CRUD de organizaciones) todavía no
piden inicio de sesión. Se protegerán cuando se implementen las sesiones del panel de administración.
