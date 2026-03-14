# ShopNow — Sistema de Microservicios

Sistema de gestión de una tienda en línea construido con una arquitectura de **microservicios** en Python usando **FastAPI**. Cada servicio es independiente, expone su propia API REST y se comunica con los demás mediante llamadas HTTP.

> **Tecnológico Nacional de México — Campus Querétaro** 
> Materia: Arquitectura Orientada a Servicios 
> Autor: Diego Arias

---

## Tabla de contenido

- [Descripción general](#descripción-general)
- [Arquitectura](#arquitectura)
- [Servicios](#servicios)
- [Diagramas de clases](#diagramas-de-clases)
- [Diagrama de secuencia — Registrar pedido](#diagrama-de-secuencia--registrar-pedido)
- [Estructura de archivos](#estructura-de-archivos)
- [Validaciones implementadas](#validaciones-implementadas)
- [Instalación local](#instalación-local)
- [Despliegue en la nube](#despliegue-en-la-nube)
- [Endpoints disponibles](#endpoints-disponibles)

---

## Descripción general

ShopNow simula el backend de una tienda en línea dividido en cuatro departamentos autónomos. Cada microservicio:

- Corre en su propio puerto.
- Tiene su propia base de datos persistida en CSV.
- Valida sus datos de entrada con **Pydantic v2**.
- Se comunica con otros servicios vía **httpx** cuando necesita validar información cruzada.

---

## Arquitectura

```mermaid
graph TD
Cliente[" Cliente / Frontend"]

Cliente -->|HTTP| SC["serv_client\n:8000"]
Cliente -->|HTTP| SP["serv_productos\n:8001"]
Cliente -->|HTTP| SPed["serv_pedidos\n:8002"]
Cliente -->|HTTP| SI["serv_inventario\n:8003"]

SPed -->|"Valida cliente"| SC
SPed -->|"Valida producto"| SP
SPed -->|"Valida stock"| SI
SI -->|"Valida producto"| SP

SC --- DBC[("clientes.csv")]
SP --- DBP[("productos.csv")]
SPed --- DBPed[("pedidos.csv")]
SI --- DBI[("inventario.csv")]
```

---

## Servicios

| Servicio | Archivo | Puerto | Responsabilidad |
|---|---|---|---|
| Clientes | `serv_client.py` | `8000` | CRUD de clientes, validación de correo único |
| Productos | `serv_productos.py` | `8001` | CRUD del catálogo de productos, validación de descripción única |
| Pedidos | `serv_pedidos.py` | `8002` | Registro de pedidos con validación cruzada de cliente, producto y stock |
| Inventario | `serv_inventario.py` | `8003` | Control de stock por producto, valida existencia en catálogo |

---

## Diagramas de clases

### `serv_client.py`

```mermaid
classDiagram
class Cliente {
+int id_cliente
+str nombre
+str correo
+str direccion
+str telefono
}
class ClienteRegistro {
+str nombre
+str correo
+str direccion
+str telefono
}
class ClienteUpdate {
+str nombre
+str correo
+str direccion
+str telefono
}
ClienteRegistro --> Cliente : crea
ClienteUpdate --> Cliente : modifica
```

### `serv_productos.py`

```mermaid
classDiagram
class Producto {
+int id_producto
+str descripcion
+float precio
}
class ProductoRegistro {
+str descripcion
+float precio
}
class ProductoUpdate {
+str descripcion
+float precio
}
ProductoRegistro --> Producto : crea
ProductoUpdate --> Producto : modifica
```

### `serv_pedidos.py`

```mermaid
classDiagram
class Pedido {
+int id_pedido
+int id_cliente
+int id_producto
+int cantidad
}
class PedidoRegistro {
+int id_cliente
+int id_producto
+int cantidad
}
class PedidoUpdate {
+int id_cliente
+int id_producto
+int cantidad
}
PedidoRegistro --> Pedido : crea
PedidoUpdate --> Pedido : modifica
```

### `serv_inventario.py`

```mermaid
classDiagram
class Inventario {
+int id_producto
+int stock
}
class InventarioUpdate {
+int stock
}
InventarioUpdate --> Inventario : modifica
```

---

## Diagrama de secuencia — Registrar pedido

El flujo más complejo del sistema: al registrar un pedido, `serv_pedidos` coordina validaciones con tres servicios antes de persistir el dato.

```mermaid
sequenceDiagram
actor U as Usuario
participant P as serv_pedidos :8002
participant C as serv_clientes :8000
participant PR as serv_productos :8001
participant I as serv_inventario :8003
participant DB as pedidos.csv

U->>P: POST /pedidos {id_cliente, id_producto, cantidad}
P->>C: GET /clientes
C-->>P: 200 lista de clientes
P->>P: ¿id_cliente existe?
alt Cliente no existe
P-->>U: 404 "El cliente no existe"
end

P->>PR: GET /productos
PR-->>P: 200 lista de productos
P->>P: ¿id_producto existe?
alt Producto no existe
P-->>U: 404 "El producto no existe en el catálogo"
end

P->>I: GET /inventario
I-->>P: 200 lista de inventario
P->>P: ¿stock >= cantidad?
alt Stock insuficiente
P-->>U: 409 "Stock insuficiente. Disponible: X, solicitado: Y"
end

P->>DB: Escribe nuevo pedido (CSV)
P-->>U: 201 {id_pedido, id_cliente, id_producto, cantidad}
```

---

## Estructura de archivos

```
ShopNow/
├── serv_client.py # Microservicio de Clientes (puerto 8000)
├── serv_productos.py # Microservicio de Productos (puerto 8001)
├── serv_pedidos.py # Microservicio de Pedidos (puerto 8002)
├── serv_inventario.py # Microservicio de Inventario (puerto 8003)
├── serv_main.py # Punto de entrada / orquestador
├── requirements.txt # Dependencias Python
├── docker-compose.yml # Configuración para correr con Docker
├── start.sh # Script para levantar todos los servicios localmente
├── .gitignore
├── README.md
└── dbs/ # Bases de datos persistentes (CSV)
├── clientes.csv
├── productos.csv
├── pedidos.csv
└── inventario.csv
```

> **Nota:** la carpeta `dbs/` está en `.gitignore` — cada instancia genera sus propios archivos CSV al arrancar por primera vez.

---

## Validaciones implementadas

Cada servicio aplica dos niveles de validación: validaciones de **modelo** (realizadas automáticamente por Pydantic al recibir la petición) y validaciones de **negocio** (lógica propia del servicio, aplicada antes de escribir en el CSV).

---

### `serv_client.py` — Servicio de Clientes

**Validaciones de modelo (Pydantic)**

El modelo `Cliente` y sus variantes definen restricciones declarativas sobre cada campo:

- `nombre`: mínimo 2 caracteres, máximo 100.
- `correo`: debe cumplir el patrón de un correo electrónico válido (`usuario@dominio.tld`). Pydantic rechaza automáticamente cualquier valor que no coincida con la expresión regular definida, retornando `422 Unprocessable Entity`.
- `id_cliente`: debe ser un entero mayor a 0.
- `direccion` y `telefono`: opcionales, sin restricciones de formato.

**Validaciones de negocio**

- `POST /clientes`: antes de registrar, se recorre el CSV y se verifica que ningún cliente existente tenga el mismo correo (comparación case-insensitive). Si se detecta duplicado, se retorna `409 Conflict` con un mensaje que indica el correo en conflicto.
- `PATCH /clientes/{id}`: si el cuerpo incluye un nuevo correo, se verifica que no pertenezca a ningún otro cliente (excluyendo al cliente que se está modificando). Retorna `409 Conflict` en caso de conflicto.
- `DELETE /clientes/{id}` y `PATCH /clientes/{id}`: verifican que el cliente con el ID dado exista en el CSV antes de proceder. Retornan `404 Not Found` si no se encuentra.

---

### `serv_productos.py` — Servicio de Productos

**Validaciones de modelo (Pydantic)**

- `descripcion`: mínimo 3 caracteres.
- `precio`: debe ser un número de punto flotante estrictamente mayor a 0. Pydantic rechaza valores negativos o iguales a cero con `422`.
- `id_producto`: entero sin restricciones adicionales (generado internamente).

**Validaciones de negocio**

- `POST /productos`: verifica que no exista otro producto con la misma descripción (comparación case-insensitive). Si existe, retorna `409 Conflict`. Esto previene registros duplicados que confundirían al sistema de inventario y pedidos.
- `PATCH /productos/{id}`: si se proporciona una nueva descripción, verifica que ningún otro producto (distinto al que se edita) la tenga registrada. Retorna `409 Conflict` en caso de colisión.
- `DELETE /productos/{id}` y `PATCH /productos/{id}`: retornan `404 Not Found` si el ID no existe.
- Si se envía un `PATCH` con body vacío (ningún campo), el servicio responde `200` sin modificar nada, ya que todos los campos del modelo `ProductoUpdate` son opcionales.

---

### `serv_pedidos.py` — Servicio de Pedidos

Este es el servicio con mayor complejidad de validación, ya que actúa como orquestador y depende de los otros tres servicios para garantizar la integridad de cada pedido.

**Validaciones de modelo (Pydantic)**

- `id_cliente`, `id_producto`: enteros mayores a 0.
- `cantidad`: entero estrictamente mayor a 0. No se puede registrar un pedido con cantidad cero o negativa.

**Validaciones de negocio — validación cruzada**

Al recibir `POST /pedidos`, el servicio realiza tres consultas HTTP secuenciales antes de escribir en el CSV:

1. **Existencia del cliente**: consulta `GET /clientes` en el servicio de Clientes (`:8000`) y verifica que el `id_cliente` proporcionado exista en la respuesta. Si no existe, retorna `404 Not Found` con el mensaje `"El cliente con ID X no existe"`.

2. **Existencia del producto**: consulta `GET /productos` en el servicio de Productos (`:8001`) y verifica que el `id_producto` exista en el catálogo. Si no existe, retorna `404 Not Found` con el mensaje `"El producto con ID X no existe en el catálogo"`.

3. **Suficiencia de stock**: consulta `GET /inventario` en el servicio de Inventario (`:8003`) y verifica que el producto tenga un registro de inventario y que el stock disponible sea mayor o igual a la cantidad solicitada. Si no hay registro, retorna `409 Conflict`. Si el stock es insuficiente, retorna `409 Conflict` indicando el stock disponible y la cantidad solicitada.

Si cualquiera de los servicios dependientes no responde (timeout o conexión rechazada), se retorna `503 Service Unavailable` indicando qué servicio falló y en qué puerto esperaba encontrarlo.

**`PATCH /pedidos/{id}`**: revalida únicamente los campos que cambian. Si solo se modifica la cantidad, no se vuelve a consultar la existencia del cliente ni del producto — solo se revalida el stock para el producto y la nueva cantidad. Esto reduce las llamadas innecesarias entre servicios.

---

### `serv_inventario.py` — Servicio de Inventario

**Validaciones de modelo (Pydantic)**

- `stock`: entero mayor o igual a 0 (`ge=0`). Se acepta stock 0 (producto agotado), pero no valores negativos.
- `id_producto`: entero sin restricciones adicionales.

**Validaciones de negocio**

- `POST /inventario`: antes de registrar o actualizar el stock de un producto, consulta `GET /productos` en el servicio de Productos (`:8001`) para verificar que el `id_producto` exista en el catálogo. Si el producto no existe, retorna `404 Not Found`. Si el servicio de Productos no responde, retorna `503 Service Unavailable`.
- `PATCH /inventario/{id}`: valida explícitamente que el nuevo valor de stock no sea negativo, retornando `400 Bad Request` si se intenta asignar un valor menor a 0 (aunque Pydantic ya lo impide a nivel de modelo, la validación manual en el handler sirve como segunda barrera).
- `DELETE /inventario/{id}` y `PATCH /inventario/{id}`: retornan `404 Not Found` si el producto no tiene registro en el inventario.

---

## Instalación local

### Requisitos

- Python 3.11+
- pip

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/dans470/ShopNow.git
cd ShopNow

# 2. Crear entorno virtual e instalar dependencias
python -m venv venv
source venv/bin/activate # Linux/macOS
# venv\Scripts\activate # Windows

pip install -r requirements.txt

# 3. Crear carpeta de bases de datos
mkdir -p dbs

# 4. Levantar cada servicio en una terminal distinta
uvicorn serv_client:app --reload --port 8000
uvicorn serv_productos:app --reload --port 8001
uvicorn serv_pedidos:app --reload --port 8002
uvicorn serv_inventario:app --reload --port 8003
```

O usar el script incluido:

```bash
bash start.sh
```

### Documentación interactiva (Swagger)

Una vez levantados los servicios, accede a la documentación en:

| Servicio | URL |
|---|---|
| Clientes | http://localhost:8000/docs |
| Productos | http://localhost:8001/docs |
| Pedidos | http://localhost:8002/docs |
| Inventario | http://localhost:8003/docs |

---

## Despliegue en la nube

El proyecto puede desplegarse en cualquier plataforma que soporte Python (Railway, Fly.io, Render, etc.). Cada microservicio se despliega como un servicio web independiente con su propio proceso.

Las URLs entre servicios se pasan como variables de entorno para que funcionen en cualquier entorno:

| Variable | Usado en | Apunta a |
|---|---|---|
| `CLIENTES_URL` | `serv_pedidos` | URL pública de serv-clientes |
| `PRODUCTOS_URL` | `serv_pedidos`, `serv_inventario` | URL pública de serv-productos |
| `INVENTARIO_URL` | `serv_pedidos` | URL pública de serv-inventario |

Si no se definen, los servicios usan `localhost` por defecto (entorno de desarrollo local).

---

## Endpoints disponibles

### Clientes `:8000`
| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/clientes` | Lista todos los clientes |
| `POST` | `/clientes` | Registra un nuevo cliente |
| `PATCH` | `/clientes/{id}` | Actualiza datos de un cliente |
| `DELETE` | `/clientes/{id}` | Elimina un cliente |

### Productos `:8001`
| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/productos` | Lista el catálogo completo |
| `POST` | `/productos` | Registra un nuevo producto |
| `PATCH` | `/productos/{id}` | Actualiza un producto |
| `DELETE` | `/productos/{id}` | Elimina un producto |

### Pedidos `:8002`
| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/pedidos` | Lista todos los pedidos |
| `POST` | `/pedidos` | Registra un pedido (con validación cruzada) |
| `PATCH` | `/pedidos/{id}` | Actualiza un pedido |
| `DELETE` | `/pedidos/{id}` | Cancela un pedido |

### Inventario `:8003`
| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/inventario` | Lista el inventario completo |
| `POST` | `/inventario` | Registra o actualiza stock de un producto |
| `PATCH` | `/inventario/{id}` | Actualiza el stock de un producto |
| `DELETE` | `/inventario/{id}` | Elimina un producto del inventario |

---

## Stack tecnológico

| Tecnología | Uso |
|---|---|
| [FastAPI](https://fastapi.tiangolo.com/) | Framework web para las APIs REST |
| [Pydantic v2](https://docs.pydantic.dev/) | Validación de modelos de datos |
| [Uvicorn](https://www.uvicorn.org/) | Servidor ASGI |
| [httpx](https://www.python-httpx.org/) | Cliente HTTP para comunicación entre servicios |
| CSV | Persistencia de datos ligera |