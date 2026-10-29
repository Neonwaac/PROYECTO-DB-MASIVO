# Databricks notebook source
# MAGIC %md
# MAGIC # HeavyCult - Jobs Spark en Databricks
# MAGIC
# MAGIC Esta version usa Spark nativo en la nube. No necesita winutils.exe ni Pandas para escribir Parquet.

# COMMAND ----------
from pyspark.sql import functions as F

# COMMAND ----------
# El volumen debe existir antes de leer o escribir Parquet.
# Si tu catalogo no se llama workspace, cambia estas tres variables.
catalogo = "workspace"
schema = "default"
volumen = "heavycult"
print("Catalogos disponibles:")
spark.sql("SHOW CATALOGS").show(truncate=False)
print(f"Schemas disponibles en {catalogo}:")
spark.sql(f"SHOW SCHEMAS IN `{catalogo}`").show(truncate=False)
spark.sql(f"CREATE VOLUME IF NOT EXISTS `{catalogo}`.`{schema}`.`{volumen}`")
print(f"Volumenes disponibles en {catalogo}.{schema}:")
spark.sql(f"SHOW VOLUMES IN `{catalogo}`.`{schema}`").show(truncate=False)
print(f"Volumen listo: /Volumes/{catalogo}/{schema}/{volumen}")

# COMMAND ----------
dbutils.widgets.text(
    "input_path",
    "/Volumes/workspace/default/heavycult",
    "Parquet de entrada",
)
dbutils.widgets.text(
    "output_root",
    "/Volumes/workspace/default/heavycult/curated/spark",
    "Carpeta de salida",
)

input_path = dbutils.widgets.get("input_path")
output_root = dbutils.widgets.get("output_root").rstrip("/")
print(f"Entrada: {input_path}")
print(f"Salidas: {output_root}")

# COMMAND ----------
def buscar_parquet(ruta):
    try:
        elementos = dbutils.fs.ls(ruta)
    except Exception as error:
        raise FileNotFoundError(
            f"No se puede leer {ruta}. Crea el volumen y sube ventas_procesadas.parquet "
            "antes de ejecutar este notebook."
        ) from error

    archivos = []
    for elemento in elementos:
        if elemento.path.endswith(".parquet"):
            archivos.append(elemento.path)
        elif elemento.path.endswith("/"):
            try:
                archivos.extend(buscar_parquet(elemento.path))
            except FileNotFoundError:
                continue
    if archivos:
        return sorted(archivos)[-1]
    if input_path.endswith(".parquet"):
        raise FileNotFoundError(
            f"No existe el archivo {input_path}. Sube el Parquet al volumen y vuelve a ejecutar."
        )
    raise FileNotFoundError(
        f"No hay archivos Parquet dentro de {ruta}. Sube data_lake/processed/ventas_procesadas.parquet "
        "a esa carpeta del volumen."
    )


archivo_entrada = buscar_parquet(input_path)
print(f"Parquet seleccionado: {archivo_entrada}")
ventas = spark.read.parquet(archivo_entrada)
columnas_requeridas = {"payment_method", "total_amount", "customer_id", "created_at"}
faltantes = sorted(columnas_requeridas - set(ventas.columns))
if faltantes:
    raise ValueError(f"Faltan columnas requeridas: {', '.join(faltantes)}")

print(f"Filas de entrada: {ventas.count():,}")
ventas.printSchema()
display(ventas.limit(10))

# COMMAND ----------
# Job 1: ventas agrupadas por metodo de pago.
job1_metodo_pago = (
    ventas.groupBy("payment_method")
    .agg(
        F.count("*").alias("compras"),
        F.sum("total_amount").alias("ingresos_totales"),
        F.avg("total_amount").alias("ticket_promedio"),
    )
    .orderBy(F.desc("ingresos_totales"))
)
job1_metodo_pago.write.mode("overwrite").option("compression", "snappy").parquet(
    f"{output_root}/job1_metodo_pago"
)
display(job1_metodo_pago)

# COMMAND ----------
# Job 2: segmentacion de clientes por gasto acumulado.
job2_segmentacion_clientes = (
    ventas.groupBy("customer_id")
    .agg(
        F.count("*").alias("compras"),
        F.sum("total_amount").alias("gasto_total"),
        F.avg("total_amount").alias("ticket_promedio"),
    )
    .withColumn(
        "segmento",
        F.when(F.col("gasto_total") > 50000000, "VIP")
        .when(F.col("gasto_total") > 10000000, "Premium")
        .when(F.col("gasto_total") > 1000000, "Frecuente")
        .otherwise("Regular"),
    )
    .orderBy(F.desc("gasto_total"))
)
job2_segmentacion_clientes.write.mode("overwrite").option("compression", "snappy").parquet(
    f"{output_root}/job2_segmentacion_clientes"
)
display(job2_segmentacion_clientes.limit(20))

# COMMAND ----------
# Job 3: evolucion mensual de ventas.
job3_analisis_temporal = (
    ventas.withColumn("fecha", F.to_timestamp("created_at"))
    .withColumn("anio", F.year("fecha"))
    .withColumn("mes", F.month("fecha"))
    .groupBy("anio", "mes")
    .agg(
        F.sum("total_amount").alias("ingresos_totales"),
        F.count("*").alias("compras"),
        F.avg("total_amount").alias("ticket_promedio"),
    )
    .orderBy("anio", "mes")
)
job3_analisis_temporal.write.mode("overwrite").option("compression", "snappy").parquet(
    f"{output_root}/job3_analisis_temporal"
)
display(job3_analisis_temporal)

# COMMAND ----------
# Evidencia final: las tres salidas existen y son legibles por Spark.
for nombre_job in [
    "job1_metodo_pago",
    "job2_segmentacion_clientes",
    "job3_analisis_temporal",
]:
    ruta = f"{output_root}/{nombre_job}"
    print(f"{nombre_job}: {spark.read.parquet(ruta).count():,} filas -> {ruta}")
