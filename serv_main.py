import httpx # type: ignore
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

CLIENTES_URL  = "http://localhost:8000"
PRODUCTOS_URL = "http://localhost:8001"
PEDIDOS_URL   = "http://localhost:8002"
INVENTARIO_URL = "http://localhost:8003"

app = FastAPI(
    title="Servicio Principal - API Gateway",
    description=(
        "Punto central de integración para la gestión de clientes, productos y pedidos de ShopNow.\n\n"
        "Este gateway **no almacena datos propios** — actúa como intermediario que enruta, "
        "valida y consolida las respuestas de los servicios internos.\n\n"
        "| Servicio   | Puerto |\n"
        "|------------|--------|\n"
        "| Clientes   | 8000   |\n"
        "| Productos  | 8001   |\n"
        "| Pedidos    | 8002   |\n"
        "| **Gateway**| **8888** |\n\n"
        "Asegurarse de que todos los servicios estén activos antes de usar este gateway."
    ),
    version="1.0.0",
    contact={"name": "Diego Arias"},
)

# ─────────────────────────────────────────────
# Modelos
# ─────────────────────────────────────────────

class ClienteRegistro(BaseModel):
    nombre:    str            = Field(..., min_length=2, max_length=100, example="Juan Pérez")
    correo:    str            = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', example="juan@shopnow.mx")
    direccion: Optional[str]  = Field(None, example="Calle Hidalgo 22 Col. Centro")
    telefono:  Optional[str]  = Field(None, example="442-123-4567")

class ClienteUpdate(BaseModel):
    nombre:    Optional[str] = Field(None, min_length=2, max_length=100)
    correo:    Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    direccion: Optional[str] = None
    telefono:  Optional[str] = None

class ProductoRegistro(BaseModel):
    descripcion: str   = Field(..., min_length=3, example="RTX 5090 32GB GDDR7")
    precio:      float = Field(..., gt=0,         example=39999.0)

class ProductoUpdate(BaseModel):
    descripcion: Optional[str]   = Field(None, min_length=3)
    precio:      Optional[float] = Field(None, gt=0)

class PedidoRegistro(BaseModel):
    id_cliente:  int = Field(..., gt=0, example=1)
    id_producto: int = Field(..., gt=0, example=11)
    cantidad:    int = Field(..., gt=0, example=1)

class PedidoUpdate(BaseModel):
    id_cliente:  Optional[int] = Field(None, gt=0)
    id_producto: Optional[int] = Field(None, gt=0)
    cantidad:    Optional[int] = Field(None, gt=0)

class InventarioRegistro(BaseModel):
    id_producto: int = Field(..., example=1)
    stock:       int = Field(..., ge=0, example=10)

class InventarioUpdate(BaseModel):
    stock: Optional[int] = Field(None, ge=0, example=10)
# ─────────────────────────────────────────────
# Helper: reenviar errores del microservicio
# ─────────────────────────────────────────────

def _raise(response: httpx.Response):
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        raise HTTPException(status_code=response.status_code, detail=detail)

# ═════════════════════════════════════════════
# GENERAL
# ═════════════════════════════════════════════

@app.get("/", tags=["General"], summary="Estado del Gateway")
def root():
    """Verifica que el API Gateway esté activo."""
    return {
        "mensaje": "API Gateway de ShopNow operativo 🚀",
        "servicios": {
            "clientes":  f"{CLIENTES_URL}/docs",
            "productos": f"{PRODUCTOS_URL}/docs",
            "pedidos":   f"{PEDIDOS_URL}/docs",
            "inventario": f"{INVENTARIO_URL}/docs"
        }
    }

# ═════════════════════════════════════════════
# CLIENTES  →  proxy a :8000
# ═════════════════════════════════════════════

@app.get("/clientes", tags=["Clientes"], summary="Listar todos los clientes", status_code=200)
def obtener_clientes():
    """Obtiene el padrón completo de clientes desde el servicio de Clientes."""
    r = httpx.get(f"{CLIENTES_URL}/clientes")
    _raise(r)
    return r.json()

@app.post("/clientes", tags=["Clientes"], summary="Registrar nuevo cliente", status_code=201)
def registrar_cliente(cliente: ClienteRegistro):
    """Registra un nuevo cliente enviando los datos al servicio de Clientes."""
    r = httpx.post(f"{CLIENTES_URL}/clientes", json=cliente.model_dump())
    _raise(r)
    return r.json()

@app.patch("/clientes/{id_cliente}", tags=["Clientes"], summary="Actualizar cliente", status_code=200)
def actualizar_cliente(id_cliente: int, datos: ClienteUpdate):
    """Actualiza parcialmente un cliente por ID."""
    r = httpx.patch(f"{CLIENTES_URL}/clientes/{id_cliente}", json=datos.model_dump(exclude_none=True))
    _raise(r)
    return r.json()

@app.delete("/clientes/{id_cliente}", tags=["Clientes"], summary="Eliminar cliente", status_code=200)
def eliminar_cliente(id_cliente: int):
    """Elimina un cliente por ID."""
    r = httpx.delete(f"{CLIENTES_URL}/clientes/{id_cliente}")
    _raise(r)
    return r.json()

# ═════════════════════════════════════════════
# PRODUCTOS  →  proxy a :8001
# ═════════════════════════════════════════════

@app.get("/productos", tags=["Productos"], summary="Listar todos los productos", status_code=200)
def obtener_productos():
    """Obtiene el catálogo completo de productos desde el servicio de Productos."""
    r = httpx.get(f"{PRODUCTOS_URL}/productos")
    _raise(r)
    return r.json()

@app.post("/productos", tags=["Productos"], summary="Registrar nuevo producto", status_code=201)
def registrar_producto(producto: ProductoRegistro):
    """Registra un nuevo producto en el catálogo."""
    r = httpx.post(f"{PRODUCTOS_URL}/productos", json=producto.model_dump())
    _raise(r)
    return r.json()

@app.patch("/productos/{id_producto}", tags=["Productos"], summary="Actualizar producto", status_code=200)
def actualizar_producto(id_producto: int, datos: ProductoUpdate):
    """Actualiza parcialmente un producto por ID."""
    r = httpx.patch(f"{PRODUCTOS_URL}/productos/{id_producto}", json=datos.model_dump(exclude_none=True))
    _raise(r)
    return r.json()

@app.delete("/productos/{id_producto}", tags=["Productos"], summary="Eliminar producto", status_code=200)
def eliminar_producto(id_producto: int):
    """Elimina un producto por ID."""
    r = httpx.delete(f"{PRODUCTOS_URL}/productos/{id_producto}")
    _raise(r)
    return r.json()

# ═════════════════════════════════════════════
# PEDIDOS  →  proxy a :8002
# ═════════════════════════════════════════════

@app.get("/pedidos", tags=["Pedidos"], summary="Listar todos los pedidos", status_code=200)
def obtener_pedidos():
    """Obtiene el registro completo de pedidos desde el servicio de Pedidos."""
    r = httpx.get(f"{PEDIDOS_URL}/pedidos")
    _raise(r)
    return r.json()

@app.post("/pedidos", tags=["Pedidos"], summary="Registrar nuevo pedido", status_code=201)
def registrar_pedido(pedido: PedidoRegistro):
    """Registra un nuevo pedido. Valida que cliente y producto existan antes de crearlo."""
    # Validar cliente
    rc = httpx.get(f"{CLIENTES_URL}/clientes")
    clientes = rc.json()
    if not any(int(c["id_cliente"]) == pedido.id_cliente for c in clientes):
        raise HTTPException(status_code=404, detail=f"Cliente {pedido.id_cliente} no encontrado")

    # Validar producto
    rp = httpx.get(f"{PRODUCTOS_URL}/productos")
    productos = rp.json()
    if not any(int(p["id_producto"]) == pedido.id_producto for p in productos):
        raise HTTPException(status_code=404, detail=f"Producto {pedido.id_producto} no encontrado")

    # Crear pedido
    r = httpx.post(f"{PEDIDOS_URL}/pedidos", json=pedido.model_dump())
    _raise(r)
    return r.json()

@app.patch("/pedidos/{id_pedido}", tags=["Pedidos"], summary="Actualizar pedido", status_code=200)
def actualizar_pedido(id_pedido: int, datos: PedidoUpdate):
    """Actualiza parcialmente un pedido por ID."""
    r = httpx.patch(f"{PEDIDOS_URL}/pedidos/{id_pedido}", json=datos.model_dump(exclude_none=True))
    _raise(r)
    return r.json()

@app.delete("/pedidos/{id_pedido}", tags=["Pedidos"], summary="Eliminar pedido", status_code=200)
def eliminar_pedido(id_pedido: int):
    """Elimina un pedido por ID."""
    r = httpx.delete(f"{PEDIDOS_URL}/pedidos/{id_pedido}")
    _raise(r)
    return r.json()

# ═════════════════════════════════════════════
# INVENTARIO  →  proxy a :8003
# ═════════════════════════════════════════════

@app.get("/inventario", tags=["Inventario"], summary="Listar stock de productos", status_code=200)
def obtener_inventario():
    """Obtiene el stock actual de todos los productos desde el servicio de Inventario."""
    r = httpx.get(f"{INVENTARIO_URL}/inventario")
    _raise(r)
    return r.json()

@app.post("/inventario", tags=["Inventario"], summary="Registrar o actualizar stock de producto", status_code=200)
def registrar_actualizar_stock(inventario: InventarioRegistro):
    """Registra o actualiza el stock de un producto en el inventario."""
    r = httpx.post(f"{INVENTARIO_URL}/inventario", json=inventario.model_dump())
    _raise(r)
    return r.json()

@app.patch("/inventario/{id_producto}", tags=["Inventario"], summary="Actualizar stock de producto", status_code=200)
def actualizar_stock(id_producto: int, actualizacion: InventarioUpdate):
    """Actualiza el stock de un producto específico en el inventario."""
    r = httpx.patch(f"{INVENTARIO_URL}/inventario/{id_producto}", json=actualizacion.model_dump(exclude_none=True))
    _raise(r)
    return r.json()

@app.delete("/inventario/{id_producto}", tags=["Inventario"], summary="Eliminar producto del inventario", status_code=200)
def eliminar_producto_inventario(id_producto: int):
    """Elimina un producto del inventario por ID.

    **Args**:
        id_producto (int): ID del producto a eliminar del inventario.
    **Returns**:
        dict: Diccionario con mensaje de éxito e ID del producto eliminado del inventario.
    Raises:
        HTTPException: Si el producto con el ID especificado no existe en el inventario.
    """
    r = httpx.delete(f"{INVENTARIO_URL}/inventario/{id_producto}")
    _raise(r)
    return r.json()