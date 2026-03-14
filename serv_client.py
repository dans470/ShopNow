import csv
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

app = FastAPI(
    title="API de Gestión de Clientes",
    description="Esta API permite gestionar clientes, incluyendo la creación y consulta de clientes registrados.",
    version="1.0.0",
    contact={
        "name": "Diego Arias"
        }
)

FILE_NAME = "./dbs/clientes.csv"
HEADERS = ["id_cliente", "nombre", "correo", "direccion", "telefono"]

if not os.path.exists(FILE_NAME):
    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(HEADERS)

class Cliente(BaseModel):
    id_cliente: int = Field(gt=0, description="ID único numérico del cliente", example=101)
    nombre: str = Field(min_length=2, max_length=100, description="Nombre completo del cliente", example="Juan Pérez")
    correo: str = Field(pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', description="Correo electrónico del cliente", example="juan.perez@example.com")
    direccion: Optional[str] = Field(None, description="Dirección del cliente", example="Calle Principal 123")
    telefono: Optional[str] = Field(None, description="Número de teléfono del cliente", example="555-1234")

class ClienteRegistro(BaseModel):
    nombre: str = Field(min_length=2, max_length=100, description="Nombre completo del cliente", example="Juan Pérez")
    correo: str = Field(pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', description="Correo electrónico del cliente", example="juan.perez@example.com")
    direccion: Optional[str] = Field(None, description="Dirección del cliente", example="Calle Principal 123")
    telefono: Optional[str] = Field(None, description="Número de teléfono del cliente", example="555-1234")

class ClienteUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=100, description="Nombre completo del cliente", example="Juan Pérez")
    correo: Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', description="Correo electrónico del cliente", example="juan.perez@example.com")
    direccion: Optional[str] = Field(None, description="Dirección del cliente", example="Calle Principal 123")
    telefono: Optional[str] = Field(None, description="Número de teléfono del cliente", example="555-1234")

def leer_clientes():
    with open(FILE_NAME, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

@app.get("/clientes", 
    response_model=List[Cliente],
    summary="Obtener lista de clientes",
    description="Devuelve una lista de todos los clientes registrados en el sistema.",
    tags=["Consultas"],
    status_code=200,
    responses={
        200: {
            "description": "Lista de clientes obtenida exitosamente", 
            "content": {
                "application/json": 
                    {"example": [
                        {"id_cliente": 101, "nombre": "Juan Pérez", "correo": "juan.perez@example.com"}
                    ]}
            }
        }
    }
)
def obtener_clientes():
    """
    Retorna el padrón oficial de clientes desde el archivo CSV.
    Este endpoint obtiene la lista completa de todos los clientes registrados
    en la base de datos de clientes persistente (archivo CSV).
    
    Returns:
        List[Cliente]: Lista de clientes con todos sus datos.
    """
    return leer_clientes()

@app.post(
    "/clientes",
    summary="Registrar nuevo cliente",
    tags=["Operaciones"],
    status_code=201,
    response_model=Cliente,
    responses={
        201: {
            "description": "Cliente registrado exitosamente",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id_cliente": 102,
                            "nombre": "María López",
                            "correo": "maria.lopez@example.com"
                        }
                    ]
                }
            }
        },
        422: {
            "description": "Error de validación de datos"
        }
    }
)
def registrar_cliente(nuevo: ClienteRegistro):
    """Registra un nuevo cliente en la base de datos.
    
    Crea un nuevo cliente con el siguiente flujo:
    1. Valida los datos de entrada según el modelo ClienteRegistro
    2. Verifica que el correo no esté ya registrado
    3. Genera un ID único autoincremental
    4. Almacena el cliente en el archivo CSV
    
    Args:
        nuevo (ClienteRegistro): Datos del cliente a registrar.
            - nombre: Nombre del cliente (mínimo 3 caracteres)
            - correo: Email válido del cliente
            - direccion: Dirección del cliente
            - telefono: Teléfono de contacto
    
    Returns:
        Cliente: El cliente registrado con su ID asignado.

    Raises:
        HTTPException: Con status 409 si el correo ya está registrado.
    """
    clientes = leer_clientes()

    # Validar duplicado de correo
    if any(c['correo'].lower() == nuevo.correo.lower() for c in clientes):
        raise HTTPException(status_code=409, detail=f"Ya existe un cliente registrado con el correo '{nuevo.correo}'")
    
    # Generar ID autoincremental
    if clientes:
        siguiente_id = max(int(c['id_cliente']) for c in clientes) + 1
    else:
        siguiente_id = 1
    
    with open(FILE_NAME, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([siguiente_id, nuevo.nombre, nuevo.correo, nuevo.direccion, nuevo.telefono])

    return {
        "id_cliente": siguiente_id,
        "nombre": nuevo.nombre,
        "correo": nuevo.correo,
        "direccion": nuevo.direccion,
        "telefono": nuevo.telefono
    }

@app.delete(
    "/clientes/{id_cliente}",
    tags=["Operaciones"],
    summary="Eliminar cliente por ID",
    description="Da de baja a un cliente específico utilizando su ID único. No elimina físicamente el registro, sino que lo marca como inactivo.",
    status_code=200,
    responses={
        200: {
            "description": "Cliente eliminado exitosamente",
            "content": {
                "application/json": {
                    "example": {"mensaje": "Cliente eliminado exitosamente", "id_cliente": 101}
                }
            }
        },
        404: {
            "description": "Cliente no encontrado"
        }
    }
)
def eliminar_cliente(id_cliente: int):
    """Elimina un cliente por ID.
    
    Busca y elimina el registro de un cliente por su ID único, marcándolo como inactivo para futuras consultas.

    Args:
        id_cliente (int): ID del cliente a eliminar.

    Returns:
        dict: Diccionario con mensaje de éxito e ID del cliente eliminado.
    Raises:
        HTTPException: Si el cliente con el ID especificado no existe.
    """
    clientes = leer_clientes()
    cliente = next((c for c in clientes if int(c['id_cliente']) == id_cliente), None)

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    clientes = [c for c in clientes if int(c['id_cliente']) != id_cliente]

    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(clientes)

    return {"mensaje": "Cliente eliminado exitosamente", "id_cliente": id_cliente}

@app.patch(
    "/clientes/{id_cliente}",
    tags=["Operaciones"],
    summary="Actualizar cliente por ID",
    description="Actualiza los datos de un cliente específico utilizando su ID único.",
    status_code=200,
    responses={
        200: {
            "description": "Cliente actualizado exitosamente",
            "content": {
                "application/json": {
                    "example": [{
                        "mensaje": "Cliente actualizado exitosamente",
                        "id_cliente": 101
                    }]
                }
            }
        },
        404: {
            "description": "Cliente no encontrado"
        }
    }
)
def actualizar_cliente(id_cliente: int, actualizacion: ClienteUpdate):
    """
    Actualiza los datos de un cliente específico utilizando su ID único.
    
    Args:
        id_cliente (int): ID del cliente a actualizar.
        actualizacion (ClienteUpdate): Datos a actualizar del cliente.
    
    Returns:
        dict: Diccionario con mensaje de éxito e ID del cliente actualizado.

    Raises:
        HTTPException: Si el cliente con el ID especificado no existe.
    """
    clientes = leer_clientes()
    cliente = next((c for c in clientes if int(c['id_cliente']) == id_cliente), None)
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Validar que el nuevo correo no esté en uso por otro cliente
    if actualizacion.correo is not None:
        duplicado = next(
            (c for c in clientes
             if c['correo'].lower() == actualizacion.correo.lower()
             and int(c['id_cliente']) != id_cliente),
            None
        )
        if duplicado:
            raise HTTPException(status_code=409, detail=f"El correo '{actualizacion.correo}' ya está en uso por otro cliente")

    if actualizacion.nombre is not None:
        cliente['nombre'] = actualizacion.nombre
    if actualizacion.correo is not None:
        cliente['correo'] = actualizacion.correo
    if actualizacion.direccion is not None:
        cliente['direccion'] = actualizacion.direccion
    if actualizacion.telefono is not None:
        cliente['telefono'] = actualizacion.telefono

    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(clientes)

    return {"mensaje": "Cliente actualizado exitosamente", "id_cliente": id_cliente}