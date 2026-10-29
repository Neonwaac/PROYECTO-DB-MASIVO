import argparse
import os
from datetime import date, datetime
from pathlib import Path

import pymongo
from bson import ObjectId
from dotenv import load_dotenv
from google.cloud import bigquery


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "heavycult")
BQ_DATASET = os.getenv("BQ_DATASET", "heavycult_dw")
BQ_LOCATION = os.getenv("BQ_LOCATION", "US")


SCHEMAS = {
    "dim_cliente": [
        bigquery.SchemaField("cliente_key", "STRING"),
        bigquery.SchemaField("cliente_id", "STRING"),
        bigquery.SchemaField("telefono", "STRING"),
        bigquery.SchemaField("nombre", "STRING"),
        bigquery.SchemaField("ciudad", "STRING"),
        bigquery.SchemaField("departamento", "STRING"),
        bigquery.SchemaField("direccion", "STRING"),
        bigquery.SchemaField("fecha_registro", "TIMESTAMP"),
    ],
    "dim_producto": [
        bigquery.SchemaField("producto_key", "STRING"),
        bigquery.SchemaField("producto_id", "STRING"),
        bigquery.SchemaField("dropi_product_id", "STRING"),
        bigquery.SchemaField("nombre", "STRING"),
        bigquery.SchemaField("categoria", "STRING"),
        bigquery.SchemaField("costo_proveedor", "FLOAT64"),
        bigquery.SchemaField("precio_venta", "FLOAT64"),
        bigquery.SchemaField("activo", "BOOL"),
    ],
    "dim_fecha": [
        bigquery.SchemaField("fecha_key", "INT64"),
        bigquery.SchemaField("fecha", "TIMESTAMP"),
        bigquery.SchemaField("anio", "INT64"),
        bigquery.SchemaField("trimestre", "INT64"),
        bigquery.SchemaField("mes", "INT64"),
        bigquery.SchemaField("nombre_mes", "STRING"),
        bigquery.SchemaField("dia", "INT64"),
        bigquery.SchemaField("dia_semana", "INT64"),
    ],
    "fact_ventas": [
        bigquery.SchemaField("venta_key", "STRING"),
        bigquery.SchemaField("order_id", "STRING"),
        bigquery.SchemaField("order_number", "STRING"),
        bigquery.SchemaField("fecha_key", "INT64"),
        bigquery.SchemaField("cliente_key", "STRING"),
        bigquery.SchemaField("producto_key", "STRING"),
        bigquery.SchemaField("sku", "STRING"),
        bigquery.SchemaField("cantidad", "INT64"),
        bigquery.SchemaField("precio_unitario", "FLOAT64"),
        bigquery.SchemaField("total_venta", "FLOAT64"),
        bigquery.SchemaField("total_orden", "FLOAT64"),
        bigquery.SchemaField("costo_proveedor", "FLOAT64"),
        bigquery.SchemaField("costo_flete", "FLOAT64"),
        bigquery.SchemaField("ganancia_neta", "FLOAT64"),
        bigquery.SchemaField("metodo_pago", "STRING"),
        bigquery.SchemaField("estado", "STRING"),
        bigquery.SchemaField("fecha_venta", "TIMESTAMP"),
    ],
}


def convertir_valor(valor):
    if isinstance(valor, ObjectId):
        return str(valor)
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    return valor


def normalizar_documento(documento):
    return {clave: convertir_valor(valor) for clave, valor in documento.items() if clave != "_id"}


def cargar_documentos_mongo():
    if not MONGO_URI:
        raise RuntimeError("MONGO_URI no esta configurado en .env.")
    cliente = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
    try:
        cliente.admin.command("ping")
        db = cliente[MONGO_DATABASE]
        documentos = {}
        for nombre in SCHEMAS:
            documentos[nombre] = [normalizar_documento(doc) for doc in db[nombre].find({})]
            if not documentos[nombre]:
                raise RuntimeError(f"La coleccion {nombre} esta vacia en MongoDB.")
            print(f"[BQ] Fuente MongoDB {nombre}: {len(documentos[nombre]):,} filas")
        return documentos
    finally:
        cliente.close()


def cargar_tabla(client, project_id, dataset_id, nombre, filas):
    table_id = f"{project_id}.{dataset_id}.{nombre}"
    job_config = bigquery.LoadJobConfig(
        schema=SCHEMAS[nombre],
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )
    job = client.load_table_from_json(filas, table_id, job_config=job_config)
    job.result()
    tabla = client.get_table(table_id)
    print(f"[BQ] {table_id}: {tabla.num_rows:,} filas")


def exportar_bigquery(project_id, dataset_id, location):
    client = bigquery.Client(project=project_id)
    dataset_ref = bigquery.Dataset(f"{project_id}.{dataset_id}")
    dataset_ref.location = location
    client.create_dataset(dataset_ref, exists_ok=True)
    print(f"[BQ] Dataset listo: {project_id}.{dataset_id} ({location})")
    documentos = cargar_documentos_mongo()
    for nombre, filas in documentos.items():
        cargar_tabla(client, project_id, dataset_id, nombre, filas)
    print("[BQ] Data Warehouse exportado correctamente desde MongoDB.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Exporta el Data Warehouse de MongoDB a BigQuery.")
    parser.add_argument("--project", default=os.getenv("GCP_PROJECT_ID"), required=False)
    parser.add_argument("--dataset", default=BQ_DATASET)
    parser.add_argument("--location", default=BQ_LOCATION)
    args = parser.parse_args()
    if not args.project:
        parser.error("Indica --project o configura GCP_PROJECT_ID en .env.")
    exportar_bigquery(args.project, args.dataset, args.location)