# Guia de demostracion: Data Lake, Streaming y Spark

Esta guia asume que la estructura OLTP y los datos ya existen. No ejecutes `crear_estructura.py` ni `generar_datos_masivos.py`.

## 1. Data Lake

Desde la raiz del proyecto:

```powershell
python data_lake.py
```

Evidencia que debes mostrar:

```powershell
Get-ChildItem data_lake -Recurse
```

Deben existir como minimo estos archivos:

```text
data_lake/raw/clientes.parquet
data_lake/raw/productos.parquet
data_lake/raw/ventas.parquet
data_lake/processed/ventas_procesadas.parquet
data_lake/curated/ventas_analiticas.parquet
```

Comprueba que los Parquet se pueden leer y que PROCESSED contiene solamente ventas entregadas:

```powershell
python -c "import pandas as pd; p='data_lake/processed/ventas_procesadas.parquet'; df=pd.read_parquet(p); print(df.shape); print(df['status'].value_counts())"
```

La salida debe mostrar solo `delivered` en la columna `status`. Para evidenciar Snappy:

```powershell
python -c "import pyarrow.parquet as pq; print(pq.ParquetFile('data_lake/processed/ventas_procesadas.parquet').metadata.created_by)"
```

## 2. Streaming en tiempo real

Abre dos terminales en la raiz del proyecto.

Terminal 1, receptor:

```powershell
python scripts/escuchar_ventas_stream.py
```

Debe quedar esperando con un mensaje que indique que escucha `heavycult.orders`.

Terminal 2, emisor:

```powershell
python scripts/enviar_ventas_stream.py --cantidad 5 --intervalo 3
```

Evidencia que debes mostrar:

- La Terminal 2 muestra cinco ventas enviadas.
- La Terminal 1 muestra las mismas ventas casi inmediatamente.
- El archivo `data_lake/raw/streaming_ventas.jsonl` crece con cada evento.

Comprueba el archivo:

```powershell
Get-Content data_lake/raw/streaming_ventas.jsonl | Select-Object -Last 5
```

Para la demostracion continua usa el emisor sin `--cantidad` y detenlo con `Ctrl+C`.

## 3. Spark

Spark se instala y configura por separado. Cuando el comando `python -c "import pyspark; print(pyspark.__version__)"` funcione, ejecuta:

```powershell
python scripts/spark_jobs.py
```

El job lee el Parquet mas reciente de `data_lake/processed`, crea una SparkSession local y ejecuta:

- `job1_metodo_pago`: compras, ingresos y ticket promedio por método.
- `job2_segmentacion_clientes`: gasto por cliente y segmento.
- `job3_analisis_temporal`: ingresos y compras por año y mes.

Evidencia que debes mostrar en la terminal:

- La ruta del Parquet de entrada.
- El esquema de Spark.
- Las tablas impresas por cada job.
- El mensaje `Sesion cerrada`.

Comprueba las salidas generadas:

```powershell
Get-ChildItem data_lake/curated/spark -Recurse
```

Deben existir estas carpetas, cada una con un `part-*.parquet`:

```text
data_lake/curated/spark/job1_metodo_pago
data_lake/curated/spark/job2_segmentacion_clientes
data_lake/curated/spark/job3_analisis_temporal
```

En Windows, si la libreria nativa de Hadoop no es compatible con PySpark, el job conserva los calculos en Spark y guarda el resultado con PyArrow como fallback. La terminal mostrara `escritura local alternativa por incompatibilidad Hadoop/Windows`.

Lee una salida para obtener evidencia independiente de Spark:

```powershell
python -c "import pandas as pd; print(pd.read_parquet('data_lake/curated/spark/job1_metodo_pago').to_string(index=False))"
```

## Orden recomendado para la presentacion

1. Mostrar las zonas y los cinco Parquet del Data Lake.
2. Mostrar una fila de `processed` y explicar que es la capa transformada.
3. Abrir las dos terminales y enviar cinco ventas.
4. Mostrar que el receptor recibe los eventos en tiempo real y escribe JSONL.
5. Ejecutar Spark sobre `processed`.
6. Abrir las tres carpetas de resultados en `curated/spark`.
7. Explicar que MongoDB Change Streams resuelve la captura en tiempo real y Spark realiza el procesamiento distribuido batch sobre Parquet.

## Problemas frecuentes durante la demostracion

- `No se encontro ningun Parquet`: ejecuta primero `python data_lake.py`.
- `No module named pyspark`: la instalacion de Spark todavía no terminó; no es un error del job.
- `JAVA_HOME is not set`: configura Java y `JAVA_HOME` antes de ejecutar Spark.
- `Spark necesita winutils.exe`: en Windows crea una carpeta Hadoop, coloca `winutils.exe` dentro de `bin` y configura `$env:HADOOP_HOME` a esa carpeta antes de ejecutar Spark. Java 17 es compatible con este proyecto.
- `Change stream is not supported`: verifica que Atlas use un replica set o cluster compatible con Change Streams.
- `SSL handshake failed`: confirmar la IP en Atlas > Network Access, desactivar temporalmente VPN/proxy/inspeccion HTTPS o probar otra red. No desactivar la validacion TLS.
- El emisor dice que no hay clientes o productos: las colecciones existentes están vacías y deben contener datos previamente cargados.
