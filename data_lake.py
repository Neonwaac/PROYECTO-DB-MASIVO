import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import pymongo
from bson import ObjectId
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("MONGO_DATABASE", "heavycult")
DATA_LAKE_ROOT = BASE_DIR / os.getenv("DATA_LAKE_ROOT", "data_lake")
ZONES = {
    "raw": DATA_LAKE_ROOT / "raw",
    "processed": DATA_LAKE_ROOT / "processed",
    "curated": DATA_LAKE_ROOT / "curated",
}


def convertir_valores(valor):
    """Convierte tipos BSON que Parquet no puede serializar directamente."""
    if isinstance(valor, ObjectId):
        return str(valor)
    if isinstance(valor, dict):
        return {clave: convertir_valores(elemento) for clave, elemento in valor.items()}
    if isinstance(valor, list):
        return [convertir_valores(elemento) for elemento in valor]
    return valor


def documentos_a_dataframe(documentos):
    documentos = [convertir_valores(documento) for documento in documentos]
    return pd.json_normalize(documentos) if documentos else pd.DataFrame()


def guardar_parquet(dataframe, ruta):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_parquet(
        ruta,
        index=False,
        compression="snappy",
        coerce_timestamps="ms",
        allow_truncated_timestamps=True,
    )
    return ruta


def exportar_coleccion(db, coleccion, nombre_archivo):
    documentos = list(db[coleccion].find({}))
    dataframe = documentos_a_dataframe(documentos)
    ruta = guardar_parquet(dataframe, ZONES["raw"] / nombre_archivo)
    print(f"[RAW] {coleccion}: {len(dataframe):,} documentos -> {ruta}")
    return documentos, dataframe


def generar_processed(documentos_ordenes):
    documentos = [convertir_valores(documento) for documento in documentos_ordenes]
    ventas = pd.json_normalize(
        documentos,
        record_path="items",
        meta=["_id", "order_number", "customer_id", "total_amount", "products_cost_total",
              "shipping_cost", "order_profit", "payment_method", "status", "created_at"],
        errors="ignore",
        sep="_",
    )

    if "status" not in ventas.columns:
        raise ValueError("Los pedidos no contienen el campo requerido 'status'.")

    # En este proyecto, 'delivered' representa una venta completada.
    ventas = ventas[ventas["status"] == "delivered"].copy()
    if "created_at" in ventas.columns:
        ventas["created_at"] = pd.to_datetime(ventas["created_at"], errors="coerce")
        ventas["anio"] = ventas["created_at"].dt.year
        ventas["mes"] = ventas["created_at"].dt.month
    ventas["fecha_procesamiento"] = datetime.now()

    ruta = guardar_parquet(ventas, ZONES["processed"] / "ventas_procesadas.parquet")
    print(f"[PROCESSED] ventas completadas: {len(ventas):,} filas -> {ruta}")
    return ventas


def generar_curated(db):
    documentos = list(db["ventas_analiticas"].find({}))
    if not documentos:
        raise ValueError(
            "La coleccion 'ventas_analiticas' esta vacia. "
            "Ejecuta primero scripts/transformar_oltp_a_olap.py."
        )
    dataframe = documentos_a_dataframe(documentos)
    ruta = guardar_parquet(dataframe, ZONES["curated"] / "ventas_analiticas.parquet")
    print(f"[CURATED] ventas_analiticas: {len(dataframe):,} filas -> {ruta}")
    return dataframe


def mostrar_estadisticas():
    archivos = [ruta for zona in ZONES.values() for ruta in zona.glob("*.parquet")]
    total_bytes = sum(ruta.stat().st_size for ruta in archivos)
    print("\n[RESUMEN] Data Lake")
    for nombre, zona in ZONES.items():
        archivos_zona = list(zona.glob("*.parquet"))
        print(f"  {nombre.upper()}: {len(archivos_zona)} archivos")
    print(f"  TOTAL: {len(archivos)} archivos")
    print(f"  ESPACIO: {total_bytes / (1024 * 1024):.2f} MB")


def generar_data_lake_completo():
    if not MONGO_URI:
        raise RuntimeError("MONGO_URI no esta configurado en .env.")

    for zona in ZONES.values():
        zona.mkdir(parents=True, exist_ok=True)
        print(f"[ESTRUCTURA] Zona lista: {zona}")

    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
        db = client[DATABASE_NAME]
        print(f"[OK] Conexion a MongoDB Atlas: base '{DATABASE_NAME}'")

        exportar_coleccion(db, "customers", "clientes.parquet")
        exportar_coleccion(db, "products", "productos.parquet")
        ordenes, _ = exportar_coleccion(db, "orders", "ventas.parquet")
        generar_processed(ordenes)
        generar_curated(db)
        mostrar_estadisticas()
    finally:
        client.close()


if __name__ == "__main__":
    generar_data_lake_completo()