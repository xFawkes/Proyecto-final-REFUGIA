"""Endpoints de la sección. Quedan en /api/elementos y /api/elementos/{id}."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from .. import database
from .modelos import Elemento, ListaElementos

router = APIRouter(prefix="/api/elementos", tags=["Elementos"])


@router.get("", response_model=ListaElementos, summary="Listar elementos")
def listar(
    q: Annotated[str | None, Query(max_length=100, description="Buscar en el título")] = None,
    limite: Annotated[int, Query(ge=1, le=200)] = 50,
):
    sql = "SELECT * FROM elementos"
    parametros: list = []
    if q:
        sql += " WHERE titulo LIKE ?"
        parametros.append(f"%{q}%")
    sql += " ORDER BY creado_en DESC LIMIT ?"
    parametros.append(limite)

    with database.conectar() as conexion:
        filas = conexion.execute(sql, parametros).fetchall()
    resultados = [dict(f) for f in filas]
    return {"total": len(resultados), "resultados": resultados}


@router.get("/{elemento_id}", response_model=Elemento, summary="Detalle de un elemento")
def detalle(elemento_id: int):
    with database.conectar() as conexion:
        fila = conexion.execute("SELECT * FROM elementos WHERE id = ?", (elemento_id,)).fetchone()
    if fila is None:
        raise HTTPException(404, "No existe un elemento con ese ID.")
    return dict(fila)
