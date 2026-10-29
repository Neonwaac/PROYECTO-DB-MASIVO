import os
import pymongo
from dotenv import load_dotenv
import time
import json

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

def asegurar_indice(coleccion, claves, nombre):
    claves = list(claves)
    for indice in coleccion.list_indexes():
        if list(indice["key"].items()) == claves:
            print(f"   [OK] Indice equivalente disponible: {indice['name']}")
            return indice["name"]
    return coleccion.create_index(claves, name=nombre)

def ejecutar_benchmark():
    print("[LANZAR] Iniciando Benchmarking Analitico de HeavyCult...\n")
    client = pymongo.MongoClient(MONGO_URI)
    db = client["heavycult"]
    coleccion = db["ventas_analiticas"]

    print("[LLAVE] Aplicando estrategias de indexacion analitica...")
    asegurar_indice(coleccion, [("anio", 1), ("mes", 1)], "idx_fecha")
    asegurar_indice(coleccion, [("producto.categoria", 1), ("ganancia_neta", -1)], "idx_cat_ganancia")
    asegurar_indice(coleccion, [("estado", 1), ("cliente.ciudad", 1)], "idx_estado_ciudad")
    print("[OK] Indices analiticos creados.\n")

    consultas = [
        {
            "nombre": "1. Facturacion y Ganancia Neta Mensual",
            "pipeline": [
                {"$group": {
                    "_id": {"anio": "$anio", "mes": "$mes"},
                    "ventas_totales": {"$sum": "$total_venta"},
                    "ganancia_neta_total": {"$sum": "$ganancia_neta"},
                    "pedidos": {"$sum": 1}
                }},
                {"$sort": {"_id.anio": 1, "_id.mes": 1}}
            ]
        },
        {
            "nombre": "2. Top 5 Productos Mas Rentables por Categoria",
            "pipeline": [
                {"$group": {
                    "_id": {"categoria": "$producto.categoria", "sku": "$producto.sku"},
                    "ganancia": {"$sum": "$ganancia_neta"},
                    "unidades": {"$sum": "$cantidad"}
                }},
                {"$sort": {"_id.categoria": 1, "ganancia": -1}},
                {"$group": {
                    "_id": "$_id.categoria",
                    "top_skus": {"$push": {"sku": "$_id.sku", "ganancia": "$ganancia", "unidades": "$unidades"}}
                }},
                {"$project": {"categoria": "$_id", "ranking": {"$slice": ["$top_skus", 5]}, "_id": 0}}
            ]
        },
        {
            "nombre": "3. Rentabilidad y Novedades por Ciudad/Departamento",
            "pipeline": [
                {"$group": {
                    "_id": {"depto": "$cliente.departamento", "ciudad": "$cliente.ciudad"},
                    "ingresos": {"$sum": "$total_venta"},
                    "ganancia_neta": {"$sum": "$ganancia_neta"},
                    "novedades_o_cancelados": {
                        "$sum": {"$cond": [{"$in": ["$estado", ["novelty", "cancelled"]]}, 1, 0]}
                    }
                }},
                {"$sort": {"ingresos": -1}}
            ]
        },
        {
            "nombre": "4. Proporcion de Entregas Exitosas vs Novedades (COD)",
            "pipeline": [
                {"$group": {
                    "_id": "$estado",
                    "total_pedidos": {"$sum": 1},
                    "monto_acumulado": {"$sum": "$total_venta"}
                }},
                {"$sort": {"total_pedidos": -1}}
            ]
        },
        {
            "nombre": "5. Tendencia de Ventas por Dia de la Semana",
            "pipeline": [
                {"$group": {
                    "_id": {"$dayOfWeek": "$fecha_venta"},
                    "ingresos": {"$sum": "$total_venta"},
                    "ventas": {"$sum": 1}
                }},
                {"$sort": {"_id": 1}}
            ]
        },
        {
            "nombre": "6. Tasa de Cancelacion por Metodo de Pago",
            "pipeline": [
                {"$group": {
                    "_id": "$metodo_pago",
                    "canceladas": {
                        "$sum": {
                            "$cond": [
                                {"$in": ["$estado", ["novelty", "cancelled"]]},
                                1,
                                0
                            ]
                        }
                    },
                    "total_ventas": {"$sum": 1}
                }},
                {"$project": {
                    "_id": 0,
                    "metodo_pago": "$_id",
                    "canceladas": 1,
                    "total_ventas": 1,
                    "tasa_cancelacion_pct": {
                        "$multiply": [
                            {"$divide": ["$canceladas", "$total_ventas"]},
                            100
                        ]
                    }
                }},
                {"$sort": {"tasa_cancelacion_pct": -1}}
            ]
        },
        {
            "nombre": "7. Top 10 Clientes por Gasto Acumulado",
            "pipeline": [
                {"$group": {
                    "_id": "$cliente.id",
                    "nombre": {"$first": "$cliente.nombre"},
                    "compras": {"$sum": 1},
                    "gasto_total": {"$sum": "$total_venta"}
                }},
                {"$sort": {"gasto_total": -1}},
                {"$limit": 10}
            ]
        },
        {
            "nombre": "8. Ventas Trimestrales y Analisis Estacional",
            "pipeline": [
                {"$group": {
                    "_id": {
                        "anio": "$anio",
                        "trimestre": {"$ceil": {"$divide": ["$mes", 3]}}
                    },
                    "ingresos": {"$sum": "$total_venta"},
                    "ventas": {"$sum": 1}
                }},
                {"$project": {
                    "_id": 0,
                    "anio": "$_id.anio",
                    "trimestre": {"$concat": ["Q", {"$toString": "$_id.trimestre"}]},
                    "ingresos": 1,
                    "ventas": 1
                }},
                {"$sort": {"anio": 1, "trimestre": 1}}
            ]
        },
        {
            "nombre": "9. Ticket Promedio por Ciudad y Estado",
            "pipeline": [
                {"$group": {
                    "_id": {
                        "ciudad": "$cliente.ciudad",
                        "estado": "$estado"
                    },
                    "ticket_promedio": {"$avg": "$total_venta"},
                    "transacciones": {"$sum": 1}
                }},
                {"$project": {
                    "_id": 0,
                    "ciudad": "$_id.ciudad",
                    "estado": "$_id.estado",
                    "ticket_promedio": 1,
                    "transacciones": 1
                }},
                {"$sort": {"ticket_promedio": -1}},
                {"$limit": 15}
            ]
        },
        {
            "nombre": "10. Top 10 Productos con Mayor Rotacion",
            "pipeline": [
                {"$group": {
                    "_id": "$producto.nombre",
                    "unidades_vendidas": {"$sum": "$cantidad"},
                    "ingresos_generados": {"$sum": "$total_venta"}
                }},
                {"$sort": {"unidades_vendidas": -1}},
                {"$limit": 10}
            ]
        }
    ]

    print("[ENGRAJE] Ejecutando benchmark de consultas...\n" + "-"*70)
    tiempos = []

    for consulta in consultas:
        print(f"[PLAY] {consulta['nombre']}")
        inicio = time.perf_counter()
        resultados = list(coleccion.aggregate(consulta['pipeline'], allowDiskUse=True))
        fin = time.perf_counter()
        tiempo_ms = (fin - inicio) * 1000
        tiempos.append(tiempo_ms)
        
        print(f"    [CRONOMETRO] Latencia: {tiempo_ms:.2f} ms | Resultados: {len(resultados)}")
        if len(resultados) > 0:
            muestra = json.loads(json.dumps(resultados[0], default=str))
            print(f"    [BOMBILLA] Muestra: {muestra}")
        print("-" * 70)

    promedio = sum(tiempos) / len(tiempos)
    print("\n" + "="*70)
    print("[GRAFICO] RESUMEN DE RENDIMIENTO DE CONSULTAS")
    print("="*70)
    print(f"[CRONOMETRO] Latencia promedio: {promedio:.2f} ms")
    print(f"[LANZAR] Latencia maxima: {max(tiempos):.2f} ms")
    print(f"[CAJA] Documentos procesados: {coleccion.count_documents({})}")
    print("="*70)
    client.close()

if __name__ == "__main__":
    ejecutar_benchmark()