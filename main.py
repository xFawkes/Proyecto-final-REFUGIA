"""
REFUGIA — inicia el servidor (como en el tutorial: python main.py).

    python main.py

  • Sitio:  http://127.0.0.1:5000/
  • API:    http://127.0.0.1:5000/api/puntos   (pruébala en Postman)

Antes, configura la conexión a MySQL en el archivo .env (copia .env.example).
"""

from api import crear_app

app = crear_app()

if __name__ == "__main__":
    # debug=True: se reinicia solo al guardar cambios y muestra los errores en detalle
    app.run(host="127.0.0.1", port=5000, debug=True)
