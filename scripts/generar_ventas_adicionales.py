import argparse
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pymongo
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")
MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("MONGO_DATABASE", "heavycult")
ESTADOS = ["delivered", "delivered", "delivered", "shipped", "novelty", "cancelled"]
METODOS_PAGO = ["Pago Contra Entrega", "Pago Contra Entrega", "PSE", "Nequi", "DaviPlata"]
CIUDADES_FLETE = {
    "Bogota": 14000.0,
    "Bogotá": 14000.0,
    "Medellin": 15000.0,
    "Medellín": 15000.0,
    "Cali": 16000.0,
    "Barranquilla": 18000.0,
    "Bucaramanga": 15000.0,
    "Pasto": 19000.0,
}


def generar_lote(clientes, productos, cantidad):
    ahora = datetime.now(timezone.utc)
    ordenes = []
    for _ in range(cantidad):
        cliente = random.choice(clientes)
        producto = random.choice(productos)
        variantes = [item for item in producto.get("variants", []) if item.get("is_active", True)]
        if not variantes:
            continue
        variante = random.choice(variantes)
        cantidad_producto = random.randint(1, 2)
        costo = float(producto["pricing"]["supplier_cost"]) * cantidad_producto
        precio = float(producto["pricing"]["sale_price"]) * cantidad_producto
        flete = CIUDADES_FLETE.get(cliente.get("city"), 15000.0)
        fecha = ahora - timedelta(days=random.randint(0, 730), seconds=random.randint(0, 86400))
        identificador = uuid.uuid4().hex
        ordenes.append({
            "order_number": f"HC-EXTRA-{identificador}",
            "customer_id": cliente["_id"],
            "dropi_order_id": f"DP-EXTRA-{identificador}",
            "items": [{
                "product_id": producto["_id"],
                "product_name": producto["name"],
                "sku": variante["sku"],
                "quantity": cantidad_producto,
                "unit_price": float(producto["pricing"]["sale_price"]),
                "supplier_cost": float(producto["pricing"]["supplier_cost"]),
            }],
            "total_amount": round(precio, 2),
            "products_cost_total": round(costo, 2),
            "shipping_cost": flete,
            "order_profit": round(precio - costo - flete, 2),
            "payment_method": random.choice(METODOS_PAGO),
            "status": random.choice(ESTADOS),
            "created_at": fecha,
            "source": "additional_volume_demo",
        })
    return ordenes


def generar_ventas(cantidad, batch_size):
    if not MONGO_URI:
        raise RuntimeError("MONGO_URI no esta configurado en .env.")
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
    try:
        client.admin.command("ping")
        db = client[DATABASE_NAME]
        clientes = list(db.customers.find({}, {"_id": 1, "city": 1}))
        productos = list(db.products.find({}, {"_id": 1, "name": 1, "pricing": 1, "variants": 1}))
        if not clientes or not productos:
            raise RuntimeError("Se necesitan clientes y productos existentes.")
        creadas = 0
        for inicio in range(0, cantidad, batch_size):
            lote = generar_lote(clientes, productos, min(batch_size, cantidad - inicio))
            if lote:
                db.orders.insert_many(lote, ordered=False)
                creadas += len(lote)
                print(f"[EXTRA] Progreso: {creadas:,}/{cantidad:,} ordenes")
        print(f"[EXTRA] Ordenes adicionales creadas: {creadas:,}")
        print(f"[EXTRA] Total actual en orders: {db.orders.count_documents({}):,}")
    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agrega ordenes unicas para ampliar el Data Lake.")
    parser.add_argument("--ventas", type=int, default=100000, help="Numero de ordenes nuevas.")
    parser.add_argument("--batch-size", type=int, default=1000, help="Tamaño de lote MongoDB.")
    args = parser.parse_args()
    generar_ventas(args.ventas, args.batch_size)
