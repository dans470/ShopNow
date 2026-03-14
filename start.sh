#!/bin/bash

# ╔═════════════════════════════════════════════════════╗
# ║             ShopNow - Lanzador de Servicios         ║
# ║   Clientes :8000 | Productos :8001 | Pedidos :8002  ║
# ╚═════════════════════════════════════════════════════0╝

echo "Iniciando servicios ShopNow..."

fuser -k 8000/tcp 2>/dev/null
fuser -k 8001/tcp 2>/dev/null
fuser -k 8002/tcp 2>/dev/null

sleep 1

uvicorn serv_client:app --port 8000 --reload &
PID_CLIENTES=$!
echo "Clientes   corriendo en http://localhost:8000  (PID: $PID_CLIENTES)"

uvicorn serv_productos:app --port 8001 --reload &
PID_PRODUCTOS=$!
echo "Productos  corriendo en http://localhost:8001  (PID: $PID_PRODUCTOS)"

uvicorn serv_pedidos:app --port 8002 --reload &
PID_PEDIDOS=$!
echo "Pedidos    corriendo en http://localhost:8002  (PID: $PID_PEDIDOS)"

uvicorn serv_inventario:app --port 8003 --reload &
PID_INVENTARIO=$!
echo "Inventario corriendo en http://localhost:8003  (PID: $PID_INVENTARIO)"

uvicorn serv_main:app --port 8888 --reload &
PID_MAIN=$!
echo "API Gateway corriendo en http://localhost:8888  (PID: $PID_MAIN)"

echo ""
echo "Docs disponibles en:"
echo "   http://localhost:8000/docs  → Clientes"
echo "   http://localhost:8001/docs  → Productos"
echo "   http://localhost:8002/docs  → Pedidos"
echo ""
echo "Para detener todo: Ctrl+C"

wait $PID_CLIENTES $PID_PRODUCTOS $PID_PEDIDOS