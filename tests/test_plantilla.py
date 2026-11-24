"""Verifica que la plantilla api/_plantilla funciona (CRUD como en el tutorial), para que copiarla sea seguro."""

from flask import Flask

from api import _plantilla
from api.extensiones import db, ma


def test_plantilla_crud_completo():
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite:///:memory:", TESTING=True)
    db.init_app(app)
    ma.init_app(app)
    app.register_blueprint(_plantilla.bp)
    with app.app_context():
        db.create_all()
        _plantilla.cargar_datos_ejemplo()
    c = app.test_client()

    assert len(c.get("/api/elementos").json) == 2                              # GET todos
    nuevo = c.post("/api/elementos", json={"titulo": "Hogar", "descripcion": "Nueva información"})
    assert nuevo.status_code == 201                                            # POST
    id_ = nuevo.json["id_elemento"]
    assert c.get(f"/api/elementos/{id_}").json["titulo"] == "Hogar"           # GET por id
    r = c.put(f"/api/elementos/{id_}", json={"titulo": "Hogar", "descripcion": "Información actualizada"})
    assert r.json["descripcion"] == "Información actualizada"                  # PUT
    assert c.delete(f"/api/elementos/{id_}").status_code == 200                # DELETE
    assert c.get(f"/api/elementos/{id_}").status_code == 404
    assert c.post("/api/elementos", json={"descripcion": "sin título"}).status_code == 400
