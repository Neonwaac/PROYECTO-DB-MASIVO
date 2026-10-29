import os
import pymongo
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

def crear_estructura_heavycult():
    client = pymongo.MongoClient(MONGO_URI)
    db = client["heavycult"]

    print("[CONSTRUCCION] Creando estructura de base de datos HeavyCult...\n")

    print("[CAJA] Creando colecciones OLTP...")
    colecciones_oltp = ["customers", "products", "orders", "whatsapp_logs"]
    existentes = db.list_collection_names()
    for col in colecciones_oltp:
        if col in existentes:
            print(f"   [OK] Coleccion '{col}' ya existe - se omite")
        else:
            db.create_collection(col)
            print(f"   [OK] Coleccion '{col}' creada")

    print("\n[BUSCAR] Creando indices...")
    db.customers.create_index([("phone", 1)], unique=True)
    db.products.create_index([("dropi_product_id", 1)], unique=True)
    db.products.create_index([("variants.sku", 1)])
    db.orders.create_index([("order_number", 1)], unique=True)
    db.orders.create_index([("customer_id", 1)])
    db.orders.create_index([("created_at", -1)])
    db.whatsapp_logs.create_index([("phone", 1)])
    print("   [OK] Indices creados")

    print("\n[NOTA] Insertando datos de prueba iniciales...")
    
    cliente_ejemplo = {
        "phone": "573001234567",
        "name": "David Medina",
        "city": "Bogotá",
        "department": "Cundinamarca",
        "address": "Calle 100 #15-20",
        "created_at": datetime.now()
    }
    db.customers.insert_one(cliente_ejemplo)
    
    producto_ejemplo = {
        "dropi_product_id": "DROPI_101",
        "name": "Botas Tácticas Impermeables",
        "category": "Calzado Táctico",
        "pricing": {
            "supplier_cost": 65000.0,
            "sale_price": 129900.0
        },
        "variants": [
            {"sku": "BOT-TAC-40-NG", "color": "Negro", "size": "40", "stock": 15, "is_active": True}
        ],
        "is_active": True
    }
    db.products.insert_one(producto_ejemplo)

    print("\n[GRAFICO] Creando coleccion analitica (OLAP)...")
    if "ventas_analiticas" in db.list_collection_names():
        print("   [OK] Coleccion 'ventas_analiticas' ya existe - se omite")
    else:
        db.create_collection("ventas_analiticas")
        print("   [OK] Coleccion 'ventas_analiticas' creada")

    print("\n[OK] Estructura HeavyCult configurada con exito!")
    client.close()

if __name__ == "__main__":
    crear_estructura_heavycult()