import csv
import os
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

import os

PRODUCTOS_URL = os.getenv("PRODUCTOS_URL", "http://localhost:8001")

app = FastAPI(
    title="Departamento de Inventario",
    description="Servicio encargado de la custodia y registro oficial del inventario de productos de la empresa.\n\n" \
    "Este servicio actúa como el punto central de integración para la validación de stock en los procesos de venta y gestión de pedidos. \n\n" \
    "Ejecutar en puerto **8003** y asegurarse de que los servicios de Pedidos (8002), Productos (8001) y Clientes (8000) estén activos para su correcto funcionamiento.",
    version="1.0.0",
    contact={
        "name": "Diego Arias",
    }
)

FILE_NAME = "./dbs/inventario.csv"
HEADERS = ["id_producto", "stock"]

if not os.path.exists(FILE_NAME):
    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(HEADERS)

class Inventario(BaseModel):
    id_producto: int = Field(..., example=1) # type: ignore
    stock: int = Field(..., ge=0, example=10) # type: ignore

class InventarioUpdate(BaseModel):
    stock: Optional[int] = Field(None, ge=0, example=10) # type: ignore

def leer_inventario():
    with open(FILE_NAME, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def validar_producto_existe(id_producto: int):
    """Consulta al servicio de Productos si el id_producto existe."""
    try:
        response = httpx.get(f"{PRODUCTOS_URL}/productos", timeout=5.0)
        response.raise_for_status()
        productos = response.json()
        if not any(int(p["id_producto"]) == id_producto for p in productos):
            raise HTTPException(
                status_code=404,
                detail=f"El producto con ID {id_producto} no existe en el catálogo de Productos"
            )
    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="No se pudo conectar al servicio de Productos (puerto 8001). Verifica que esté activo."
        )
    
@app.get(
    "/inventario",
    response_model=List[Inventario],
    tags=["Consultas"],
    summary="Obtener lista de inventario",
    status_code=200,
    responses={
        200: {
            "description": "Lista de inventario obtenida exitosamente",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id_producto": 1,
                            "stock": 10
                        }
                    ]
                }
            }
        }
    }
)
def get_inventario():
    return leer_inventario()

@app.post(
    "/inventario",
    response_model=Inventario,
    tags=["Gestión"],
    summary="Registrar o actualizar stock de producto",
    status_code=200,
    responses={
        200: {
            "description": "Stock registrado o actualizado exitosamente",
            "content": {
                "application/json": {
                    "example": [{
                        "id_producto": 1,
                        "stock": 10
                    }]
                }
            }
        }
    }
)
def registrar_actualizar_stock(inventario: Inventario):
    validar_producto_existe(inventario.id_producto)
    inventarios = leer_inventario()
    for item in inventarios:
        if int(item["id_producto"]) == inventario.id_producto:
            item["stock"] = str(inventario.stock)
            break
    else:
        inventarios.append({"id_producto": str(inventario.id_producto), "stock": str(inventario.stock)})
    
    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(inventarios)
    
    return inventario

@app.patch(
    "/inventario/{id_producto}",
    response_model=Inventario,
    tags=["Gestión"],
    summary="Actualizar stock de producto",
    status_code=200,
    responses={
        200: {
            "description": "Stock actualizado exitosamente",
            "content": {
                "application/json": {
                    "example": [{
                        "id_producto": 1,
                        "stock": 10
                    }]
                }
            }
        },
        404: {
            "description": "Producto no encontrado en inventario"
        }
    }
)
def actualizar_stock(id_producto: int, actualizacion: InventarioUpdate):
    """**Actualiza el stock de un producto específico en el inventario.**

    Valida que el producto exista en el inventario y que el nuevo stock no sea negativo.
    Si se pasa stock 0, se acepta (producto agotado).

    **Args**:

        id_producto (int): ID único del producto a actualizar.
        actualizacion (InventarioUpdate): Nuevo valor de stock (mayor o igual a 0).

    **Returns**:

        Inventario:
            El producto con su stock actualizado.

    **Raises**:

        HTTPException 404: Si el producto no existe en el inventario.
        HTTPException 400: Si el stock proporcionado es negativo.
    """
    inventarios = leer_inventario()

    item = next((i for i in inventarios if int(i["id_producto"]) == id_producto), None)
    if not item:
        raise HTTPException(status_code=404, detail="Producto no encontrado en inventario")

    if actualizacion.stock is not None:
        if actualizacion.stock < 0:
            raise HTTPException(status_code=400, detail="El stock no puede ser negativo")
        item["stock"] = str(actualizacion.stock)

    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(inventarios)

    return {"id_producto": id_producto, "stock": int(item["stock"])}

@app.delete(
    "/inventario/{id_producto}",
    tags=["Gestión"],
    summary="Eliminar producto del inventario",
    description="Desactiva un producto del inventario eliminando su registro. Esto no elimina el producto del catálogo, solo lo marca como no disponible en el inventario.",
    status_code=200,
    responses={
        200: {
            "description": "Producto eliminado del inventario exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "mensaje": "Producto eliminado del inventario exitosamente",
                        "id_producto": 1
                    }
                }
            }
        },
        404: {
            "description": "Producto no encontrado en inventario"
        }
    }
)
def eliminar_producto_inventario(id_producto: int):
    """**Elimina un producto del inventario.**
    Busca y elimina el registro de un producto por su ID único, marcándolo como no disponible para futuras consultas de stock.

    **Args**:

        id_producto (int): ID único del producto a eliminar del inventario.
    """
    
    inventarios = leer_inventario()
    item = next((i for i in inventarios if int(i["id_producto"]) == id_producto), None)
    if not item:
        raise HTTPException(status_code=404, detail="Producto no encontrado en inventario")
    
    inventarios = [i for i in inventarios if int(i["id_producto"]) != id_producto]

    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(inventarios)

    return {"mensaje": "Producto eliminado del inventario exitosamente", "id_producto": id_producto}