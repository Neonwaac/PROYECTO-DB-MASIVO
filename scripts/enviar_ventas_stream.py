import argparse
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pymongo
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("MONGO_DATABASE", "heavycult")


def crear_venta(db, numero):
    cliente = db.customers.find_one({}, {"_id": 1, "city": 1})
    producto = db.products.find_one({}, {"_id": 1, "name": 1, "pricing": 1, "variants": 1})
    if not cliente or not producto:
        raise RuntimeError("No hay clientes o productos existentes para crear la venta.")

    variante = next((item for item in producto.get("variants", []) if item.get("is_active", True)), None)
    if not variante:
        raise RuntimeError("El producto seleccionado no tiene una variante activa.")

    cantidad = 1
    precio = float(producto["pricing"]["sale_price"])
    costo = float(producto["pricing"]["supplier_cost"])
    flete = 15000.0

    return {
        "order_number": f"STREAM-{int(time.time())}-{numero}",
        "customer_id": cliente["_id"],
        "dropi_order_id": f"STREAM-{int(time.time() * 1000)}-{numero}",
        "items": [{
            "product_id": producto["_id"],
            "product_name": producto["name"],
            "sku": variante["sku"],
            "quantity": cantidad,
            "unit_price": precio,
            "supplier_cost": costo,
        }],
        "total_amount": precio,
        "products_cost_total": costo,
        "shipping_cost": flete,
        "order_profit": precio - costo - flete,
        "payment_method": "STREAMING",
        "status": "delivered",
        "created_at": datetime.now(timezone.utc),
        "source": "stream_demo",
    }


def enviar_ventas(cantidad, intervalo):
    if not MONGO_URI:
        raise RuntimeError("MONGO_URI no esta configurado en .env.")

    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
        db = client[DATABASE_NAME]
        print(f"[EMISOR] Conectado a '{DATABASE_NAME}'. Ctrl+C para detener.")
        numero = 1
        while cantidad == 0 or numero <= cantidad:
            venta = crear_venta(db, numero)
            resultado = db.orders.insert_one(venta)
            print(
                f"[EMISOR] Venta enviada: {venta['order_number']} | "
                f"_id={resultado.inserted_id}"
            )
            numero += 1
            if cantidad == 0 or numero <= cantidad:
                time.sleep(intervalo)
    except KeyboardInterrupt:
        print("\n[EMISOR] Detenido por el usuario.")
    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Envia ventas de prueba a MongoDB.")
    parser.add_argument("--cantidad", type=int, default=0, help="Ventas a enviar; 0 significa infinito.")
    parser.add_argument("--intervalo", type=float, default=3.0, help="Segundos entre ventas.")
    args = parser.parse_args()
    enviar_ventas(args.cantidad, args.intervalo)