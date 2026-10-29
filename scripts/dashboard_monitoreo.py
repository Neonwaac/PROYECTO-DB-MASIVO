import json
import os
import time
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pymongo
from dotenv import load_dotenv
from matplotlib.ticker import FuncFormatter


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("MONGO_DATABASE", "heavycult")
OUTPUT_DIR = BASE_DIR / "dashboards"
SLA_MS = float(os.getenv("DASHBOARD_SLA_MS", "500"))
MONGO_TIER = os.getenv("MONGO_TIER", "M10")
MONTHLY_COST = float(os.getenv("MONGO_MONTHLY_COST", "57.04"))


def crear_indices(db):
    coleccion = db.ventas_analiticas
    coleccion.create_index([("anio", 1), ("mes", 1)], name="idx_fecha_completa")
    coleccion.create_index([("producto.categoria", 1), ("ganancia_neta", -1)], name="idx_categoria_ganancia")
    coleccion.create_index([("estado", 1), ("cliente.ciudad", 1), ("metodo_pago", 1)], name="idx_estado_ciudad_pago")
    coleccion.create_index([("cliente.id", 1), ("cliente.ciudad", 1)], name="idx_cliente_ciudad")
    coleccion.create_index([("producto.nombre", 1), ("cantidad", -1)], name="idx_producto_rotacion")


def ejecutar_consulta(coleccion, nombre, pipeline):
    inicio = time.perf_counter()
    resultados = list(coleccion.aggregate(pipeline, allowDiskUse=True))
    latencia = (time.perf_counter() - inicio) * 1000
    print(f"[DASHBOARD] {nombre}: {latencia:.2f} ms | filas={len(resultados):,}")
    return resultados, latencia


def consultas_analiticas(coleccion):
    consultas = [
        ("1. Ventas totales mensuales", [{"$group": {"_id": {"anio": "$anio", "mes": "$mes"}, "ingresos": {"$sum": "$total_venta"}, "transacciones": {"$sum": 1}}}, {"$sort": {"_id.anio": 1, "_id.mes": 1}}]),
        ("2. Top productos rentables por categoria", [{"$group": {"_id": {"categoria": "$producto.categoria", "producto": "$producto.nombre"}, "ingresos": {"$sum": "$total_venta"}, "ganancia": {"$sum": "$ganancia_neta"}}}, {"$sort": {"ganancia": -1}}, {"$limit": 10}]),
        ("3. Rendimiento por segmento y ciudad", [{"$group": {"_id": {"cliente": "$cliente.id", "ciudad": "$cliente.ciudad"}, "ingresos": {"$sum": "$total_venta"}, "compras": {"$sum": 1}}}, {"$set": {"segmento": {"$switch": {"branches": [{"case": {"$gt": ["$ingresos", 50000000]}, "then": "VIP"}, {"case": {"$gt": ["$ingresos", 10000000]}, "then": "Premium"}, {"case": {"$gt": ["$ingresos", 1000000]}, "then": "Frecuente"}], "default": "Regular"}}}}, {"$group": {"_id": {"segmento": "$segmento", "ciudad": "$_id.ciudad"}, "ingresos": {"$sum": "$ingresos"}, "clientes": {"$sum": 1}}}, {"$sort": {"ingresos": -1}}]),
        ("4. Ticket por metodo de pago", [{"$group": {"_id": "$metodo_pago", "ticket_promedio": {"$avg": "$total_venta"}, "transacciones": {"$sum": 1}, "ingresos": {"$sum": "$total_venta"}}}, {"$sort": {"ingresos": -1}}]),
        ("5. Tendencia por dia de semana", [{"$set": {"dia_semana": {"$dayOfWeek": "$fecha_venta"}}}, {"$group": {"_id": "$dia_semana", "ingresos": {"$sum": "$total_venta"}, "ventas": {"$sum": 1}}}, {"$sort": {"_id": 1}}]),
        ("6. Tasa de cancelacion por pago", [{"$group": {"_id": "$metodo_pago", "canceladas": {"$sum": {"$cond": [{"$in": ["$estado", ["cancelled", "cancelado"]]}, 1, 0]}}, "total": {"$sum": 1}}}, {"$set": {"tasa_cancelacion_pct": {"$multiply": [{"$divide": ["$canceladas", "$total"]}, 100]}}}, {"$sort": {"tasa_cancelacion_pct": -1}}]),
        ("7. Top clientes por gasto", [{"$group": {"_id": "$cliente.id", "nombre": {"$first": "$cliente.nombre"}, "compras": {"$sum": 1}, "gasto_total": {"$sum": "$total_venta"}}}, {"$sort": {"gasto_total": -1}}, {"$limit": 10}]),
        ("8. Ventas trimestrales", [{"$group": {"_id": {"anio": "$anio", "trimestre": {"$ceil": {"$divide": ["$mes", 3]}}}, "ingresos": {"$sum": "$total_venta"}, "ventas": {"$sum": 1}}}, {"$sort": {"_id.anio": 1, "_id.trimestre": 1}}]),
        ("9. Ticket por ciudad y estado", [{"$group": {"_id": {"ciudad": "$cliente.ciudad", "estado": "$estado"}, "ticket_promedio": {"$avg": "$total_venta"}, "transacciones": {"$sum": 1}}}, {"$sort": {"ticket_promedio": -1}}, {"$limit": 15}]),
        ("10. Productos con mayor rotacion", [{"$group": {"_id": "$producto.nombre", "unidades": {"$sum": "$cantidad"}, "ingresos": {"$sum": "$total_venta"}}}, {"$sort": {"unidades": -1}}, {"$limit": 10}]),
    ]
    resultados = {}
    latencias = []
    for nombre, pipeline in consultas:
        datos, latencia = ejecutar_consulta(coleccion, nombre, pipeline)
        resultados[nombre] = datos
        latencias.append({"consulta": nombre, "latencia_ms": round(latencia, 2), "filas": len(datos)})
    return resultados, latencias


def obtener_estadisticas(db):
    nombres = db.list_collection_names()
    conteos = {nombre: db[nombre].count_documents({}) for nombre in nombres}
    almacenamiento = sum(db.command("collStats", nombre).get("storageSize", 0) for nombre in nombres)
    return conteos, almacenamiento


def construir_figura(conteos, almacenamiento, resultados, latencias):
    plt.style.use("seaborn-v0_8-whitegrid")
    figura = plt.figure(figsize=(16, 10), constrained_layout=True)
    figura.suptitle("DASHBOARD DE MONITOREO - Arquitectura de Datos", fontsize=18, fontweight="bold")
    ejes = figura.subplot_mosaic([["colecciones", "rendimiento", "costos"], ["tendencia", "almacenamiento", "resumen"]])

    nombres = list(conteos)
    valores = list(conteos.values())
    ejes["colecciones"].bar(range(len(nombres)), valores, color="#ef6c63")
    ejes["colecciones"].set_title("Documentos por colección")
    ejes["colecciones"].set_ylabel("Documentos")
    ejes["colecciones"].set_xticks(range(len(nombres)), nombres, rotation=35, ha="right", fontsize=8)

    etiquetas_latencia = ["Q" + str(i + 1) for i in range(len(latencias))]
    valores_latencia = [item["latencia_ms"] for item in latencias]
    ejes["rendimiento"].bar(etiquetas_latencia, valores_latencia, color="#2fc875")
    ejes["rendimiento"].axhline(SLA_MS, color="#55a85c", linestyle="--", label=f"SLA < {SLA_MS:.0f} ms")
    ejes["rendimiento"].set_title("Rendimiento de 10 consultas")
    ejes["rendimiento"].set_ylabel("Tiempo (ms)")
    ejes["rendimiento"].legend(fontsize=8)

    ejes["costos"].pie([MONTHLY_COST, max(MONTHLY_COST * 0.001, 0.01)], labels=[f"Base {MONGO_TIER}", "Almacenamiento"], autopct="%.2f%%", colors=["#3498db", "#f5b041"])
    ejes["costos"].set_title("Estimación de costos mensuales")

    meses = resultados["1. Ventas totales mensuales"]
    etiquetas = [f"{item['_id']['anio']}-{item['_id']['mes']:02d}" for item in meses]
    ingresos = [item["ingresos"] for item in meses]
    ejes["tendencia"].plot(etiquetas, ingresos, marker="o", color="#f04b3a")
    ejes["tendencia"].set_title("Tendencia de ventas mensuales")
    ejes["tendencia"].set_ylabel("Ingresos")
    ejes["tendencia"].tick_params(axis="x", rotation=45, labelsize=8)
    ejes["tendencia"].yaxis.set_major_formatter(FuncFormatter(lambda valor, _: f"{valor / 1_000_000:.0f}M"))

    ejes["almacenamiento"].bar(["Documentos", "GB", "Meses"], [sum(valores), almacenamiento / 1_000_000_000, len(meses)], color="#3498db")
    ejes["almacenamiento"].set_title("Métricas de almacenamiento")
    ejes["almacenamiento"].set_ylabel("Valor")

    promedio = sum(valores_latencia) / len(valores_latencia)
    resumen = f"RESUMEN EJECUTIVO\n\nTotal documentos: {sum(valores):,}\nAlmacenamiento: {almacenamiento / 1_000_000_000:.3f} GB\nLatencia promedio: {promedio:.2f} ms\nConsultas bajo SLA: {sum(valor < SLA_MS for valor in valores_latencia)}/{len(valores_latencia)}\nColecciones activas: {len(conteos)}\nEstado: OPERATIVO"
    ejes["resumen"].text(0.5, 0.5, resumen, ha="center", va="center", fontsize=11, family="monospace", bbox={"boxstyle": "round,pad=1", "facecolor": "#fff4dc", "edgecolor": "#777"})
    ejes["resumen"].axis("off")
    return figura


def generar_dashboard():
    if not MONGO_URI:
        raise RuntimeError("MONGO_URI no esta configurado en .env.")
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
    try:
        client.admin.command("ping")
        db = client[DATABASE_NAME]
        crear_indices(db)
        conteos, almacenamiento = obtener_estadisticas(db)
        resultados, latencias = consultas_analiticas(db.ventas_analiticas)
        figura = construir_figura(conteos, almacenamiento, resultados, latencias)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        marca = datetime.now().strftime("%Y%m%d_%H%M%S")
        imagen = OUTPUT_DIR / f"dashboard_monitoreo_{marca}.png"
        metricas = OUTPUT_DIR / f"dashboard_monitoreo_{marca}.json"
        figura.savefig(imagen, dpi=150, bbox_inches="tight")
        plt.close(figura)
        promedio = sum(item["latencia_ms"] for item in latencias) / len(latencias)
        metricas.write_text(json.dumps({"conteos": conteos, "almacenamiento_bytes": almacenamiento, "latencias": latencias, "latencia_promedio_ms": round(promedio, 2), "sla_ms": SLA_MS, "costo_mensual_estimado": MONTHLY_COST}, indent=2, default=str), encoding="utf-8")
        print(f"[DASHBOARD] Imagen generada: {imagen}")
        print(f"[DASHBOARD] Métricas guardadas: {metricas}")
    finally:
        client.close()


if __name__ == "__main__":
    generar_dashboard()