import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pymongo
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("MONGO_DATABASE", "heavycult")
WAREHOUSE_COLLECTIONS = ["dim_cliente", "dim_producto", "dim_fecha", "fact_ventas"]


def fecha_como_datetime(valor):
    if isinstance(valor, datetime):
        return valor
    if isinstance(valor, str):
        return datetime.fromisoformat(valor.replace("Z", "+00:00"))
    return datetime.now(timezone.utc)


def clave_fecha(fecha):
    return int(fecha.strftime("%Y%m%d"))


def cargar_fuentes(db):
    clientes = {doc["_id"]: doc for doc in db.customers.find({})}
    productos = {doc["_id"]: doc for doc in db.products.find({})}
    ordenes = list(db.orders.find({}))
    if not ordenes:
        raise RuntimeError("No hay documentos en orders para construir el Data Warehouse.")
    return clientes, productos, ordenes


def construir_modelo(clientes, productos, ordenes):
    dim_clientes = []
    for cliente_id, cliente in clientes.items():
        dim_clientes.append({
            "cliente_key": str(cliente_id),
            "cliente_id": str(cliente_id),
            "telefono": cliente.get("phone"),
            "nombre": cliente.get("name"),
            "ciudad": cliente.get("city"),
            "departamento": cliente.get("department"),
            "direccion": cliente.get("address"),
            "fecha_registro": cliente.get("created_at"),
        })

    dim_productos = []
    for producto_id, producto in productos.items():
        dim_productos.append({
            "producto_key": str(producto_id),
            "producto_id": str(producto_id),
            "dropi_product_id": producto.get("dropi_product_id"),
            "nombre": producto.get("name"),
            "categoria": producto.get("category"),
            "costo_proveedor": producto.get("pricing", {}).get("supplier_cost"),
            "precio_venta": producto.get("pricing", {}).get("sale_price"),
            "activo": producto.get("is_active"),
        })

    dim_fechas = {}
    fact_ventas = []
    for orden in ordenes:
        fecha = fecha_como_datetime(orden.get("created_at"))
        date_key = clave_fecha(fecha)
        dim_fechas[date_key] = {
            "fecha_key": date_key,
            "fecha": fecha,
            "anio": fecha.year,
            "trimestre": ((fecha.month - 1) // 3) + 1,
            "mes": fecha.month,
            "nombre_mes": fecha.strftime("%B"),
            "dia": fecha.day,
            "dia_semana": fecha.isoweekday(),
        }

        items = orden.get("items", [])
        for indice, item in enumerate(items):
            cantidad = item.get("quantity", 0)
            precio_unitario = item.get("unit_price", 0)
            fact_ventas.append({
                "venta_key": f"{orden.get('order_number', str(orden['_id']))}_{indice}",
                "order_id": str(orden["_id"]),
                "order_number": orden.get("order_number"),
                "fecha_key": date_key,
                "cliente_key": str(orden.get("customer_id")),
                "producto_key": str(item.get("product_id")),
                "sku": item.get("sku"),
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "total_venta": round(cantidad * precio_unitario, 2),
                "total_orden": orden.get("total_amount"),
                "costo_proveedor": orden.get("products_cost_total"),
                "costo_flete": orden.get("shipping_cost"),
                "ganancia_neta": orden.get("order_profit"),
                "metodo_pago": orden.get("payment_method"),
                "estado": orden.get("status"),
                "fecha_venta": fecha,
            })

    return dim_clientes, dim_productos, list(dim_fechas.values()), fact_ventas


def reemplazar_coleccion(db, nombre, documentos):
    db[nombre].delete_many({})
    if documentos:
        db[nombre].insert_many(documentos, ordered=False)
    print(f"[DW] {nombre}: {len(documentos):,} documentos")


def crear_indices(db):
    db.dim_cliente.create_index("cliente_key", unique=True)
    db.dim_producto.create_index("producto_key", unique=True)
    db.dim_fecha.create_index("fecha_key", unique=True)
    db.fact_ventas.create_index("venta_key", unique=True)
    db.fact_ventas.create_index([("fecha_key", 1), ("metodo_pago", 1)])
    db.fact_ventas.create_index([("cliente_key", 1), ("producto_key", 1)])


def construir_data_warehouse():
    if not MONGO_URI:
        raise RuntimeError("MONGO_URI no esta configurado en .env.")

    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
    try:
        client.admin.command("ping")
        db = client[DATABASE_NAME]
        print(f"[DW] Conectado a MongoDB Atlas: {DATABASE_NAME}")
        clientes, productos, ordenes = cargar_fuentes(db)
        modelo = construir_modelo(clientes, productos, ordenes)
        for nombre, documentos in zip(WAREHOUSE_COLLECTIONS, modelo):
            reemplazar_coleccion(db, nombre, documentos)
        crear_indices(db)
        print("[DW] Data Warehouse dimensional construido correctamente.")
        print("[DW] Grano de fact_ventas: una fila por item de pedido.")
    finally:
        client.close()


if __name__ == "__main__":
    construir_data_warehouse()