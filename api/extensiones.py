"""Extensiones de Flask compartidas por todas las secciones (como en el tutorial).

  db → SQLAlchemy: crea las tablas y consulta la base de datos con clases de Python.
  ma → Marshmallow: convierte los registros a JSON y valida los datos que llegan.
"""

from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
ma = Marshmallow()
