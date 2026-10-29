import os
import random
import pymongo
from dotenv import load_dotenv
from faker import Faker
import time

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
fake = Faker('es_CO')

NUM_CLIENTES = 5000
NUM_PRODUCTOS = 500
NUM_VENTAS = 30000
BATCH_SIZE = 1000

CIUDADES_COLOMBIA = [
    {"ciudad": "Bogotá", "depto": "Cundinamarca", "flete": 14000},
    {"ciudad": "Medellín", "depto": "Antioquia", "flete": 15000},
    {"ciudad": "Cali", "depto": "Valle del Cauca", "flete": 16000},
    {"ciudad": "Barranquilla", "depto": "Atlántico", "flete": 18000},
    {"ciudad": "Bucaramanga", "depto": "Santander", "flete": 15000},
    {"ciudad": "Pasto", "depto": "Nariño", "flete": 19000}
]

CATEGORIAS = ["Calzado Táctico", "Ropa Oversize", "Accesorios Tácticos", "Maletas y Morrales"]

def conectar_bd():
    client = pymongo.MongoClient(MONGO_URI)
    return client["heavycult"]

def insertar_en_lotes(coleccion, datos, nombre_entidad):
    total = len(datos)
    print(f"[CAJA] Insertando {total} {nombre_entidad} en lotes de {BATCH_SIZE}...")
    for i in range(0, total, BATCH_SIZE):
        lote = datos[i:i + BATCH_SIZE]
        try:
            coleccion.insert_many(lote, ordered=False)
            progreso = min(i + BATCH_SIZE, total)
            print(f"   [FLECHA] Progreso: {progreso}/{total} ({(progreso/total)*100:.1f}%)")
        except pymongo.errors.BulkWriteError as e:
            insertados = e.details.get('nInserted', 0)
            progreso = min(i + BATCH_SIZE, total)
            print(f"   [ADVERTENCIA] Progreso: {progreso}/{total} (Se omitieron {len(lote) - insertados} duplicados)")
    print(f"   [OK] Proceso de {nombre_entidad} finalizado.\n")

def generar_datos():
    print("[LANZAR] Generando datos masivos de HeavyCult Dropshipping...\n")
    db = conectar_bd()
    inicio_total = time.time()

    print("CLIENTES - Generando directorio de clientes...")
    clientes = []
    for _ in range(NUM_CLIENTES):
        ubicacion = random.choice(CIUDADES_COLOMBIA)
        clientes.append({
            "phone": f"573{random.randint(10000000, 99999999)}",
            "name": fake.name(),
            "city": ubicacion["ciudad"],
            "department": ubicacion["depto"],
            "address": fake.street_address(),
            "created_at": fake.date_time_between(start_date='-1y', end_date='now')
        })
    insertar_en_lotes(db.customers, clientes, "clientes")
    clientes_db = list(db.customers.find({}, {"_id": 1, "city": 1, "department": 1}))

    print("PRODUCTOS - Generando catalogo de Dropi...")
    productos = []
    for i in range(NUM_PRODUCTOS):
        costo_prov = round(random.uniform(30000, 90000), 2)
        precio_venta = round(costo_prov + random.uniform(40000, 80000), 2)
        
        productos.append({
            "dropi_product_id": f"DROPI_{random.randint(10000, 99999)}",
            "name": f"{random.choice(['Botas', 'Camiseta', 'Chaquetón', 'Morral'])} {fake.word().capitalize()} HeavyCult",
            "category": random.choice(CATEGORIAS),
            "pricing": {
                "supplier_cost": costo_prov,
                "sale_price": precio_venta
            },
            "variants": [
                {
                    "sku": f"SKU-{i}-{tam}",
                    "size": str(tam),
                    "stock": random.randint(10, 100),
                    "is_active": True
                } for tam in ["S", "M", "L", "XL"]
            ],
            "is_active": True
        })
    insertar_en_lotes(db.products, productos, "productos")
    productos_db = list(db.products.find({}, {"_id": 1, "name": 1, "pricing": 1, "variants": 1, "category": 1}))

    print("ORDENES - Generando ventas con flujo de transporte Dropi...")
    estados_dropshipping = ["delivered", "delivered", "delivered", "shipped", "novelty", "cancelled"]
    metodos_pago = ["Pago Contra Entrega", "Pago Contra Entrega", "PSE", "Nequi"]
    
    ordenes = []
    for idx in range(NUM_VENTAS):
        cliente = random.choice(clientes_db)
        producto = random.choice(productos_db)
        variante = random.choice(producto["variants"])
        
        cantidad = random.randint(1, 2)
        costo_productos = producto["pricing"]["supplier_cost"] * cantidad
        precio_productos = producto["pricing"]["sale_price"] * cantidad
        
        flete = next((item["flete"] for item in CIUDADES_COLOMBIA if item["ciudad"] == cliente["city"]), 15000)
        total_orden = precio_productos
        ganancia_neta = total_orden - (costo_productos + flete)

        ordenes.append({
            "order_number": f"HC-2026-{idx+10000}",
            "customer_id": cliente["_id"],
            "dropi_order_id": f"DP-{random.randint(100000, 999999)}",
            "items": [{
                "product_id": producto["_id"],
                "product_name": producto["name"],
                "sku": variante["sku"],
                "quantity": cantidad,
                "unit_price": producto["pricing"]["sale_price"],
                "supplier_cost": producto["pricing"]["supplier_cost"]
            }],
            "total_amount": round(total_orden, 2),
            "products_cost_total": round(costo_productos, 2),
            "shipping_cost": float(flete),
            "order_profit": round(ganancia_neta, 2),
            "payment_method": random.choice(metodos_pago),
            "status": random.choice(estados_dropshipping),
            "created_at": fake.date_time_between(start_date='-1y', end_date='now')
        })

        if len(ordenes) >= BATCH_SIZE:
            insertar_en_lotes(db.orders, ordenes, "ordenes (lote)")
            ordenes = []

    if len(ordenes) > 0:
        insertar_en_lotes(db.orders, ordenes, "ordenes (lote final)")

    tiempo_total = time.time() - inicio_total
    print("="*50)
    print(f"[CELEBRAR] PROCESO FINALIZADO EN {tiempo_total:.2f} SEGUNDOS")
    print(f"[MONEDA] Ordenes creadas: {db.orders.count_documents({})}")
    print("="*50)
    db.client.close()

if __name__ == "__main__":
    generar_datos()