import os
import pymongo
from dotenv import load_dotenv
import time

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

def transformar_datos():
    print("[CLIQUEANDO] Transformando OLTP a OLAP en HeavyCult...\n")
    client = pymongo.MongoClient(MONGO_URI)
    db = client["heavycult"]
    inicio = time.time()

    pipeline = [
        {"$lookup": {"from": "customers", "localField": "customer_id", "foreignField": "_id", "as": "cliente_info"}},
        {"$unwind": "$cliente_info"},
        {"$unwind": "$items"},
        {"$lookup": {"from": "products", "localField": "items.product_id", "foreignField": "_id", "as": "producto_info"}},
        {"$unwind": "$producto_info"},
        {"$project": {
            "_id": 0,
            "fecha_venta": "$created_at",
            "anio": {"$year": "$created_at"},
            "mes": {"$month": "$created_at"},
            "dia": {"$dayOfMonth": "$created_at"},
            "order_number": 1,
            "cliente": {
                "id": "$cliente_info._id",
                "nombre": "$cliente_info.name",
                "telefono": "$cliente_info.phone",
                "ciudad": "$cliente_info.city",
                "departamento": "$cliente_info.department"
            },
            "producto": {
                "id": "$producto_info._id",
                "nombre": "$items.product_name",
                "sku": "$items.sku",
                "categoria": "$producto_info.category"
            },
            "cantidad": "$items.quantity",
            "precio_unitario": "$items.unit_price",
            "total_venta": "$total_amount",
            "costo_proveedor": "$products_cost_total",
            "costo_flete": "$shipping_cost",
            "ganancia_neta": "$order_profit",
            "metodo_pago": "$payment_method",
            "estado": "$status"
        }},
        {"$merge": {"into": "ventas_analiticas", "whenNotMatched": "insert"}}
    ]

    print("[ENGRAJE] Ejecutando Aggregation Pipeline ETL...")
    db.ventas_analiticas.delete_many({})
    db.orders.aggregate(pipeline, allowDiskUse=True)
    tiempo_total = time.time() - inicio
    total_analitico = db.ventas_analiticas.count_documents({})

    print("="*60)
    print("[CELEBRAR] TRANSFORMACION DE DATOS COMPLETA")
    print(f"[CRONOMETRO] Tiempo de procesamiento: {tiempo_total:.2f} segundos")
    print(f"[GRAFICO] Registros creados en ventas_analiticas: {total_analitico}")
    print("="*60)
    client.close()

if __name__ == "__main__":
    transformar_datos()