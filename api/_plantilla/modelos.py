"""Modelo: la tabla de la sección (como la clase Categoria del tutorial)."""

from ..extensiones import db


class Elemento(db.Model):  # se crea la clase que genera la tabla
    __tablename__ = "elementos"  # nombre de la tabla en MySQL (usa uno propio de tu sección)

    id_elemento = db.Column(db.Integer, primary_key=True)  # llave primaria
    titulo = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.String(255))

    def __init__(self, titulo, descripcion):  # constructor: permite crear Elemento("título", "descripción")
        self.titulo = titulo
        self.descripcion = descripcion
