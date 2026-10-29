import glob
import os
import platform
import shutil
from pathlib import Path

import pandas as pd
from py4j.protocol import Py4JJavaError
from pyspark.sql import SparkSession, functions as F


BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = BASE_DIR / "data_lake" / "processed"
CURATED_DIR = BASE_DIR / "data_lake" / "curated" / "spark"


def obtener_archivo_parquet(ruta_carpeta):
    archivos = glob.glob(os.path.join(str(ruta_carpeta), "*.parquet"))
    if not archivos:
        raise FileNotFoundError(f"No se encontro ningun Parquet en: {ruta_carpeta}")
    return max(archivos, key=os.path.getmtime)


def crear_spark_session():
    if platform.system() == "Windows":
        hadoop_home = os.environ.get("HADOOP_HOME") or r"C:\hadoop"
        hadoop_home_path = Path(hadoop_home)
        winutils = hadoop_home_path / "bin" / "winutils.exe"
        hadoop_dll = hadoop_home_path / "bin" / "hadoop.dll"
        if not winutils.is_file() or not hadoop_dll.is_file():
            raise RuntimeError(
                "En Windows Spark necesita winutils.exe y hadoop.dll para escribir Parquet. "
                "Configura HADOOP_HOME apuntando a una carpeta que contenga ambos "
                "archivos dentro de bin."
            )
        os.environ["HADOOP_HOME"] = str(hadoop_home_path)
        os.environ["hadoop.home.dir"] = str(hadoop_home_path)
        os.environ["PATH"] = str(hadoop_home_path / "bin") + os.pathsep + os.environ["PATH"]
    os.environ.setdefault("PYSPARK_SUBMIT_ARGS", "--master local[*] pyspark-shell")
    os.environ.setdefault("SPARK_LOCAL_HOSTNAME", "localhost")
    return (
        SparkSession.builder
        .appName("HeavyCult-Spark-Jobs")
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.driver.memory", "2g")
        .getOrCreate()
    )


def validar_columnas(dataframe, columnas, nombre_job):
    faltantes = sorted(set(columnas) - set(dataframe.columns))
    if faltantes:
        raise ValueError(f"{nombre_job}: faltan columnas requeridas: {', '.join(faltantes)}")


def guardar_resultado(dataframe, nombre_job):
    ruta = CURATED_DIR / nombre_job
    if ruta.exists():
        shutil.rmtree(ruta)
    ruta.mkdir(parents=True, exist_ok=True)
    try:
        dataframe.coalesce(1).write.mode("overwrite").parquet(str(ruta), compression="snappy")
        print(f"[SPARK] {nombre_job}: {dataframe.count():,} filas -> {ruta}")
    except Py4JJavaError as error:
        if "NativeIO$Windows" not in str(error.java_exception):
            raise
        ruta.mkdir(parents=True, exist_ok=True)
        salida = ruta / "part-00000.parquet"
        pandas_resultado = dataframe.toPandas()
        pandas_resultado.to_parquet(salida, index=False, compression="snappy")
        print(
            f"[SPARK] {nombre_job}: {len(pandas_resultado):,} filas -> {ruta} "
            "(escritura local alternativa por incompatibilidad Hadoop/Windows)"
        )


def job1_ventas_por_metodo_pago(ventas):
    validar_columnas(ventas, ["payment_method", "total_amount"], "job1")
    resultado = (
        ventas
        .groupBy("payment_method")
        .agg(
            F.count("*").alias("compras"),
            F.sum("total_amount").alias("ingresos_totales"),
            F.avg("total_amount").alias("ticket_promedio"),
        )
        .orderBy(F.desc("ingresos_totales"))
    )
    guardar_resultado(resultado, "job1_metodo_pago")
    resultado.show(truncate=False)


def job2_segmentacion_clientes(ventas):
    validar_columnas(ventas, ["customer_id", "total_amount"], "job2")
    resultado = (
        ventas
        .groupBy("customer_id")
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
    guardar_resultado(resultado, "job2_segmentacion_clientes")
    resultado.show(20, truncate=False)


def job3_ventas_por_tiempo(ventas):
    validar_columnas(ventas, ["created_at", "total_amount"], "job3")
    resultado = (
        ventas
        .withColumn("fecha", F.to_timestamp("created_at"))
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
    guardar_resultado(resultado, "job3_analisis_temporal")
    resultado.show(truncate=False)


def ejecutar_jobs():
    archivo_entrada = obtener_archivo_parquet(PROCESSED_DIR)
    print(f"[SPARK] Archivo de entrada: {archivo_entrada}")
    spark = crear_spark_session()
    try:
        ventas = spark.read.parquet(archivo_entrada)
        print(f"[SPARK] Particiones de entrada: {ventas.rdd.getNumPartitions()}")
        ventas.printSchema()
        job1_ventas_por_metodo_pago(ventas)
        job2_segmentacion_clientes(ventas)
        job3_ventas_por_tiempo(ventas)
    finally:
        spark.stop()
        print("[SPARK] Sesion cerrada.")


if __name__ == "__main__":
    ejecutar_jobs()