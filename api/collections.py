from fastapi import APIRouter, HTTPException, Depends
from typing import List
from pydantic import BaseModel
import uuid

router = APIRouter()

class CollectionResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str

@router.get("/collections", response_model=List[CollectionResponse], summary="Listar todas las colecciones")
async def get_collections():
    """
    Obtiene una lista de todas las colecciones.
    """
    # Esto es un placeholder. En una implementación real, aquí se obtendrían las colecciones de la base de datos.
    return [
        CollectionResponse(id=uuid.uuid4(), name="Colección de ejemplo 1", description="Descripción de la colección 1"),
        CollectionResponse(id=uuid.uuid4(), name="Colección de ejemplo 2", description="Descripción de la colección 2"),
    ]
