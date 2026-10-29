# Guia paso a paso: migrar Spark a Databricks

Esta migracion no modifica `scripts/spark_jobs.py`, el Data Lake local ni MongoDB. Usa el notebook independiente `databricks/spark_jobs_databricks.py`.

## 1. Preparar el archivo de entrada

Primero verifica que exista localmente:

```powershell
Test-Path data_lake\processed\ventas_procesadas.parquet
```

Debe devolver `True`. Si no existe, genera el Data Lake local:

```powershell
.\.venv\Scripts\python.exe data_lake.py
```

## 2. Crear el workspace

1. Entra a Databricks y crea un workspace gratuito disponible para tu cuenta.
2. Abre **Workspace**.
3. Crea una carpeta para el proyecto, por ejemplo `HeavyCult`.
4. Usa **Import** para subir `databricks/spark_jobs_databricks.py`.
5. Al importarlo, Databricks reconocerá los bloques `# COMMAND ----------` como celdas.

Los nombres de menú pueden variar entre Community Edition y Free Edition.

## 3. Usar Serverless Compute

En Databricks Free Edition normalmente no puedes crear clusters clásicos. Eso es normal: utiliza **Serverless Compute**.

1. Abre el notebook.
2. En la parte superior busca **Connect**, **Compute** o el selector de ejecución.
3. Selecciona **Serverless**.
4. Ejecuta la primera celda y espera a que el entorno esté listo.

No necesitas instalar `pyspark`, `winutils.exe`, `hadoop.dll` ni Java manualmente: el runtime serverless los proporciona.

## 4. Crear un volumen Unity Catalog

El error `DBFS_DISABLED` significa que `/FileStore` está bloqueado en tu workspace. Usa un volumen.

1. Abre **Catalog**.
2. Selecciona el catálogo `workspace` o el catálogo que exista en tu cuenta.
3. Abre el schema `default`.
4. Pulsa **Create** y selecciona **Volume**.
5. Crea un volumen administrado llamado `heavycult`.

La ruta resultante será:

```text
/Volumes/workspace/default/heavycult/
```

Si tu catálogo no se llama `workspace`, reemplázalo en todas las rutas.

También puedes comprobar o crear el volumen desde una celda Python del notebook:

```python
spark.sql("SHOW VOLUMES IN workspace.default").show(truncate=False)
spark.sql("CREATE VOLUME IF NOT EXISTS workspace.default.heavycult")
```

Si `CREATE VOLUME` devuelve un error de permisos, créalo desde **Catalog > workspace > default > Create > Volume** o utiliza el catálogo y schema que tu cuenta permita.

Si aparece `PATH_NOT_FOUND`, ejecuta primero estas consultas para encontrar los nombres reales:

```python
spark.sql("SHOW CATALOGS").show(truncate=False)
spark.sql("SHOW SCHEMAS IN workspace").show(truncate=False)
spark.sql("SHOW VOLUMES IN workspace.default").show(truncate=False)
```

Si `workspace` no aparece en `SHOW CATALOGS`, cambia `catalogo = "workspace"` en la celda de preparación por el catálogo que sí aparezca. Si `heavycult` no aparece en `SHOW VOLUMES`, crea el volumen y vuelve a ejecutar desde la celda de preparación:

```python
spark.sql("CREATE VOLUME workspace.default.heavycult")
```

## 5. Subir el Parquet

Entra al volumen `heavycult`, pulsa **Upload files** y sube:

```text
data_lake/processed/ventas_procesadas.parquet
```

La ruta final debe ser:

```text
/Volumes/workspace/default/heavycult/processed/ventas_procesadas.parquet
```

La ruta siempre conserva este formato:

```text
/Volumes/<catalogo>/<schema>/<volumen>/processed/ventas_procesadas.parquet
```

Si Databricks crea una ruta distinta, conserva la ruta que muestre la interfaz y úsala en el widget `input_path` del notebook.

Este paso es obligatorio. Crear el volumen no sube automáticamente los archivos locales. Debes comprobar que el archivo aparece dentro de `processed` antes de ejecutar Spark.

Verifica desde una celda temporal:

```python
display(dbutils.fs.ls("/Volumes/workspace/default/heavycult/processed"))
```

Debe aparecer un elemento cuyo nombre termine en:

```text
ventas_procesadas.parquet
```

## 6. Crear y ejecutar el notebook

1. Abre el notebook importado.
2. Conéctalo a **Serverless Compute**.
3. Ejecuta la primera celda de widgets.
4. Confirma estos valores:

```text
input_path:
    /Volumes/workspace/default/heavycult

output_root:
    /Volumes/workspace/default/heavycult/curated/spark
```

5. Ejecuta **Run All**.

El notebook buscará automáticamente el Parquet de forma recursiva dentro de `heavycult`, tanto si lo subes directamente al volumen como dentro de `processed`. Si no encuentra ningún Parquet, se detendrá con un mensaje indicando que debes subir el archivo; las celdas posteriores no se ejecutarán con una entrada inexistente.

El notebook ejecuta tres jobs:

- `job1_metodo_pago`.
- `job2_segmentacion_clientes`.
- `job3_analisis_temporal`.

La escritura usa exclusivamente Spark nativo:

```python
df.write.mode("overwrite").parquet("/Volumes/workspace/default/heavycult/curated/spark")
```

No usa el fallback de Pandas de Windows.

## 7. Verificar resultados

Ejecuta en una celda nueva:

```python
for ruta in [
    "/Volumes/workspace/default/heavycult/curated/spark/job1_metodo_pago",
    "/Volumes/workspace/default/heavycult/curated/spark/job2_segmentacion_clientes",
    "/Volumes/workspace/default/heavycult/curated/spark/job3_analisis_temporal",
]:
    print(ruta)
    display(spark.read.parquet(ruta))
```

También puedes listar las salidas:

```python
display(dbutils.fs.ls("/Volumes/workspace/default/heavycult/curated/spark"))
```

## 8. Evidencia para la presentación

Toma capturas de:

1. El notebook conectado a **Serverless Compute**.
2. El notebook con el esquema y el conteo de filas.
3. La salida de `job1_metodo_pago`.
4. La salida de `job2_segmentacion_clientes`.
5. La salida de `job3_analisis_temporal`.
6. El volumen Unity Catalog con las tres salidas Parquet.
7. El código de escritura nativa `.write.parquet(...)`.

Explicación recomendada:

> En Windows se utilizó PySpark local con `local[*]` y un fallback de Pandas para resolver la incompatibilidad de Hadoop nativo. Para el entorno cloud se preparó un notebook Databricks que reutiliza las mismas transformaciones, pero ejecuta Spark mediante Serverless Compute y escribe directamente en un volumen Unity Catalog mediante Parquet nativo. Así se separan las limitaciones del entorno de desarrollo de la arquitectura de producción.

## 9. Relación con el proyecto local

```text
MongoDB Atlas
    |
    v
Data Lake local: data_lake/processed/ventas_procesadas.parquet
    |
    v
Subida controlada a Unity Catalog Volume
    |
    v
Databricks Spark nativo
    |
    v
/Volumes/workspace/default/heavycult/curated/spark/
```

El streaming MongoDB Change Streams permanece independiente. No se debe enviar `.env` ni credenciales a Databricks para este ejercicio, porque el notebook procesa el Parquet ya exportado.

## 10. Qué no debes hacer

- No reemplazar el job local que ya funciona.
- No subir `.env` al workspace.
- No ejecutar `crear_estructura.py` desde Databricks.
- No ejecutar `generar_datos_masivos.py` desde Databricks.
- No usar rutas `C:\...` dentro del notebook.
- No usar `/FileStore` ni `dbfs:/FileStore` en este workspace.
- No usar `toPandas()` para escribir las salidas cloud.
- No eliminar los Parquet locales hasta verificar las salidas en DBFS.
