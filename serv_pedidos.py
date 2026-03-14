import csv
import os
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

import os

CLIENTES_URL   = os.getenv("CLIENTES_URL",   "http://localhost:8000")
PRODUCTOS_URL  = os.getenv("PRODUCTOS_URL",  "http://localhost:8001")
INVENTARIO_URL = os.getenv("INVENTARIO_URL", "http://localhost:8003")

app = FastAPI(
    title="Departamento de Pedidos",
    description="Servicio encargado de la custodia y registro oficial de los pedidos de la empresa.\n\n"
    "Este servicio actúa como el punto central de integración para la gestión de pedidos en los procesos de venta.\n\n"
    "Ejecutar en puerto **8002** y asegurarse de que los servicios de Clientes (8000) y Productos (8001) estén activos para su correcto funcionamiento.",
    version="1.0.0",
    contact={
        "name": "Diego Arias"
    }
)

FILE_NAME = "./dbs/pedidos.csv"
HEADERS = ["id_pedido", "id_cliente", "id_producto", "cantidad"]

if not os.path.exists(FILE_NAME):
    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(HEADERS)

class Pedido(BaseModel):
    id_pedido: int = Field(gt=0, description="ID único numérico del pedido", example=1)
    id_cliente: int = Field(gt=0, description="ID del cliente que realiza el pedido", example=1)
    id_producto: int = Field(gt=0, description="ID del producto asociado al pedido", example=1)
    cantidad: int = Field(gt=0, description="Cantidad de productos solicitados", example=2)

class PedidoRegistro(BaseModel):
    id_cliente: int = Field(gt=0, description="ID del cliente que realiza el pedido", example=1)
    id_producto: int = Field(gt=0, description="ID del producto asociado al pedido", example=1)
    cantidad: int = Field(gt=0, description="Cantidad de productos solicitados", example=2)

class PedidoUpdate(BaseModel):
    id_cliente: Optional[int] = Field(None, gt=0, description="ID del cliente", example=1)
    id_producto: Optional[int] = Field(None, gt=0, description="ID del producto", example=1)
    cantidad: Optional[int] = Field(None, gt=0, description="Cantidad de productos", example=2)

def leer_pedidos():
    with open(FILE_NAME, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def _get_json(url: str, servicio: str) -> list:
    """Helper: hace GET y retorna JSON, lanza 503 si el servicio no responde."""
    try:
        r = httpx.get(url, timeout=5.0)
        r.raise_for_status()
        return r.json()
    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail=f"No se pudo conectar al servicio de {servicio}. Verifica que esté activo."
        )

def validar_cliente(id_cliente: int):
    clientes = _get_json(f"{CLIENTES_URL}/clientes", "Clientes (puerto 8000)")
    if not any(int(c["id_cliente"]) == id_cliente for c in clientes):
        raise HTTPException(status_code=404, detail=f"El cliente con ID {id_cliente} no existe")

def validar_producto(id_producto: int):
    productos = _get_json(f"{PRODUCTOS_URL}/productos", "Productos (puerto 8001)")
    if not any(int(p["id_producto"]) == id_producto for p in productos):
        raise HTTPException(status_code=404, detail=f"El producto con ID {id_producto} no existe en el catálogo")

def validar_stock(id_producto: int, cantidad: int):
    inventario = _get_json(f"{INVENTARIO_URL}/inventario", "Inventario (puerto 8003)")
    item = next((i for i in inventario if int(i["id_producto"]) == id_producto), None)
    if not item:
        raise HTTPException(status_code=409, detail=f"El producto con ID {id_producto} no tiene registro en inventario")
    stock_disponible = int(item["stock"])
    if stock_disponible < cantidad:
        raise HTTPException(
            status_code=409,
            detail=f"Stock insuficiente para el producto {id_producto}. Disponible: {stock_disponible}, solicitado: {cantidad}"
        )

@app.get(
    "/pedidos",
    response_model=List[Pedido],
    summary="Obtener lista de pedidos",
    description="Devuelve una lista de todos los pedidos registrados en el sistema.",
    tags=["Consultas"],
    status_code=200,
    responses={
        200: {
            "description": "Lista de pedidos obtenida exitosamente",
            "content": {
                "application/json": {
                    "example": [
                        {"id_pedido": 1, "id_cliente": 1, "id_producto": 1, "cantidad": 2}
                    ]
                }
            }
        }
    }
)
def obtener_pedidos():
    """**Retorna el registro oficial de pedidos desde el archivo CSV.**

    Este endpoint obtiene la lista completa de todos los pedidos registrados
    en la base de datos persistente (archivo CSV).

    **Returns**:

        List[Pedido]:
            Lista de pedidos con todos sus datos (ID, cliente, producto, cantidad).
    """
    return leer_pedidos()

@app.post(
    "/pedidos",
    summary="Registrar nuevo pedido",
    tags=["Operaciones"],
    status_code=201,
    response_model=Pedido,
    responses={
        201: {
            "description": "Pedido registrado exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "id_pedido": 1,
                        "id_cliente": 1,
                        "id_producto": 1,
                        "cantidad": 2
                    }
                }
            }
        },
        422: {"description": "Datos de entrada inválidos o formato incorrecto"}
    }
)
def registrar_pedido(nuevo: PedidoRegistro):
    """**Registra un nuevo pedido en la base de datos.**

    Crea un nuevo pedido con el siguiente flujo:
        1. Valida los datos de entrada según el modelo PedidoRegistro
        2. Genera un ID único autoincremental
        3. Almacena el pedido en el archivo CSV

    **Args**:

        nuevo (PedidoRegistro): Datos del pedido a registrar.
            - id_cliente: ID del cliente que realiza el pedido
            - id_producto: ID del producto solicitado
            - cantidad: Cantidad de productos (debe ser mayor a 0)

    **Returns**:

        Pedido:
            El pedido registrado con su ID asignado.
    """
    pedidos = leer_pedidos()

    # Validaciones cruzadas
    validar_cliente(nuevo.id_cliente)
    validar_producto(nuevo.id_producto)
    validar_stock(nuevo.id_producto, nuevo.cantidad)

    if pedidos:
        siguiente_id = max(int(p['id_pedido']) for p in pedidos) + 1
    else:
        siguiente_id = 1

    with open(FILE_NAME, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([siguiente_id, nuevo.id_cliente, nuevo.id_producto, nuevo.cantidad])

    return {"id_pedido": siguiente_id, "id_cliente": nuevo.id_cliente, "id_producto": nuevo.id_producto, "cantidad": nuevo.cantidad}

@app.delete(
    "/pedidos/{id_pedido}",
    tags=["Operaciones"],
    summary="Eliminar pedido por ID",
    description="Cancela un pedido específico utilizando su ID único. No elimina físicamente el registro, sino que lo marca como cancelado.",
    status_code=200,
    responses={
        200: {
            "description": "Pedido cancelado exitosamente",
            "content": {
                "application/json": {
                    "example": {"mensaje": "Pedido cancelado exitosamente", "id_pedido": 1}
                }
            }
        },
        404: {"description": "Pedido no encontrado"}
    }
)
def eliminar_pedido(id_pedido: int):
    """**Cancela un pedido específico utilizando su ID único.**

    Este endpoint no elimina físicamente el registro del pedido, sino que lo marca como cancelado para mantener la integridad histórica de los datos.

    **Args**:

        id_pedido (int): ID del pedido a cancelar.
    **Returns**:
        dict:
            Diccionario con mensaje de confirmación de cancelación.
    **Raises**:
        HTTPException:
            Con status 404 si el pedido no existe.
    """
    pedidos = leer_pedidos()
    pedido = next((p for p in pedidos if int(p['id_pedido']) == id_pedido), None)

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    pedidos = [p for p in pedidos if int(p['id_pedido']) != id_pedido]

    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(pedidos)

    return {"mensaje": "Pedido cancelado exitosamente", "id_pedido": id_pedido}

@app.patch(
    "/pedidos/{id_pedido}",
    tags=["Operaciones"],
    summary="Actualizar pedido por ID",
    description="Actualiza los datos de un pedido específico utilizando su ID único.",
    status_code=200,
    responses={
        200: {
            "description": "Pedido actualizado exitosamente",
            "content": {
                "application/json": {
                    "example": {"mensaje": "Pedido actualizado exitosamente", "id_pedido": 1}
                }
            }
        },
        404: {"description": "Pedido no encontrado"}
    }
)
def actualizar_pedido(id_pedido: int, actualizacion: PedidoUpdate):
    """**Actualiza parcialmente un pedido existente.**

    **Args**:

        id_pedido (int): ID único del pedido a actualizar.
        actualizacion (PedidoUpdate): Datos opcionales a actualizar.
            - id_cliente (opcional): Nuevo ID de cliente
            - id_producto (opcional): Nuevo ID de producto
            - cantidad (opcional): Nueva cantidad (mayor a 0)

    **Returns**:

        dict:
            Diccionario con mensaje de confirmación de actualización.

    **Raises**:

        HTTPException:
            Con status 404 si el pedido no existe.
    """
    pedidos = leer_pedidos()
    pedido = next((p for p in pedidos if int(p['id_pedido']) == id_pedido), None)

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    # Revalidar campos que cambian
    nuevo_id_cliente  = actualizacion.id_cliente  if actualizacion.id_cliente  is not None else int(pedido['id_cliente'])
    nuevo_id_producto = actualizacion.id_producto if actualizacion.id_producto is not None else int(pedido['id_producto'])
    nueva_cantidad    = actualizacion.cantidad     if actualizacion.cantidad     is not None else int(pedido['cantidad'])

    if actualizacion.id_cliente is not None:
        validar_cliente(nuevo_id_cliente)
    if actualizacion.id_producto is not None:
        validar_producto(nuevo_id_producto)
    if actualizacion.id_producto is not None or actualizacion.cantidad is not None:
        validar_stock(nuevo_id_producto, nueva_cantidad)

    if actualizacion.id_cliente is not None:
        pedido['id_cliente'] = actualizacion.id_cliente
    if actualizacion.id_producto is not None:
        pedido['id_producto'] = actualizacion.id_producto
    if actualizacion.cantidad is not None:
        pedido['cantidad'] = actualizacion.cantidad

    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(pedidos)

    return {"mensaje": "Pedido actualizado exitosamente", "id_pedido": id_pedido}