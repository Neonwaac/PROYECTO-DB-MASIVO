# Parcial BD Primer Corte - Sistema de Ventas con MongoDB Atlas

Guia practica del documento `PARCIAL BD PRIMER CORTE.docx`.

## Estructura
```
.
├── .env                            # MONGO_URI (no se sube a git)
├── requirements.txt
├── conexion.py                     # Fase 1 - prueba de conexion
├── iac_setup.py                    # Configuracion reproducible del entorno
├── main.tf                         # Marcador Terraform para la entrega IaC
├── data_lake.py                    # Exportacion RAW/PROCESSED/CURATED a Parquet
└── scripts/
    ├── crear_estructura.py         # Fase 2 - OLTP + OLAP
    ├── generar_datos_masivos.py    # Fase 3 - 5k clientes / 1k productos / 50k ventas
    ├── transformar_oltp_a_olap.py  # Fase 4 - Aggregation Pipeline ETL
   ├── benchmarking_consultas.py   # Fase 5 - indices compuestos + consultas
   ├── enviar_ventas_stream.py     # Emisor de ventas en tiempo real
   ├── escuchar_ventas_stream.py   # Receptor MongoDB Change Streams
   ├── spark_jobs.py               # Tres jobs PySpark sobre el Data Lake
   ├── data_warehouse.py           # Modelo dimensional para Atlas SQL Interface
   ├── dashboard_monitoreo.py      # Dashboard PNG y métricas de monitoreo
   └── generar_catalogo.py         # Catálogo automatizado en Excel
```

## Requisitos
- Python 3.12
- Cuenta MongoDB Atlas (cluster M0 gratis)
- `pip install -r requirements.txt`
- PyArrow para escribir archivos Parquet con compresion Snappy

## Infraestructura como Codigo

El script `iac_setup.py` automatiza la configuracion local: valida Python, crea `.venv`, instala las dependencias, crea las zonas del Data Lake y comprueba la conexion a MongoDB Atlas. No crea nuevamente las colecciones OLTP ni genera datos masivos.

Para reconstruir el entorno desde cero en Windows, consulta [docs/GUIA_IAC.md](docs/GUIA_IAC.md).

## Catalogo automatizado de datos

El catálogo inspecciona la base `heavycult`, aplana documentos anidados, estandariza tipos BSON, identifica PK/FK e índices y clasifica las colecciones como OLTP, OLAP o Data Warehouse.

Ejecuta:

```powershell
python scripts\generar_catalogo.py
```

Se genera `Catalogo_Datos_VentasDB_YYYYMMDD.xlsx` en la raíz, con las hojas `Resumen Arquitectonico` y `Diccionario de Datos`.

### Justificación académica

En una arquitectura de datos moderna, el Data Discovery es tan crítico como el almacenamiento. Para garantizar el gobierno de los datos y facilitar el onboarding de nuevos analistas o científicos de datos, se implementó un script de generación automatizada de catálogos (`generar_catalogo.py`). El proceso inspecciona la estructura real de MongoDB, documenta campos anidados, tipos, relaciones e índices, y produce un inventario Excel reproducible. Esto reduce la dependencia del conocimiento tribal, mejora la trazabilidad y permite mantener actualizado el diccionario técnico cuando evolucionan las colecciones.

## Uso paso a paso (orden del documento)
1. Editar `.env` con tu connection string:
   ```
   MONGO_URI=mongodb+srv://usuario:password@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
2. Verificar conexion:
   ```
   python conexion.py
   ```
3. Transformar OLTP -> OLAP (la estructura y los datos ya deben existir):
   ```
   python scripts/transformar_oltp_a_olap.py
   ```
4. Generar el Data Lake:
   ```
   python data_lake.py
   ```
5. Benchmarking:
   ```
   python scripts/benchmarking_consultas.py
   ```

## Generacion del Data Lake

Despues de crear los datos y ejecutar la transformacion OLTP -> OLAP, ejecuta:

```bash
python data_lake.py
```

El script crea las zonas si no existen y genera cinco archivos:

- `data_lake/raw/clientes.parquet`
- `data_lake/raw/productos.parquet`
- `data_lake/raw/ventas.parquet`
- `data_lake/processed/ventas_procesadas.parquet` (solo pedidos `delivered`, equivalente a completados)
- `data_lake/curated/ventas_analiticas.parquet`

La base de datos usada por defecto es `heavycult`. Puede cambiarse sin editar el script con `MONGO_DATABASE` en `.env`.

## Apache Spark

La dependencia `pyspark` queda declarada en `requirements.txt`, pero su instalacion y configuracion pueden realizarse por separado. Tambien necesitas Java configurado para ejecutar Spark.

El job busca automáticamente el Parquet más reciente de `data_lake/processed` y ejecuta tres transformaciones:

1. Ventas agrupadas por método de pago.
2. Segmentación de clientes por gasto total: `VIP`, `Premium`, `Frecuente` y `Regular`.
3. Evolución mensual de ventas usando año y mes.

Ejecuta:

```powershell
python scripts/spark_jobs.py
```

Los resultados quedan en `data_lake/curated/spark/`. Spark escribe cada resultado como una carpeta Parquet con archivos `part-*`; esto es normal en un procesamiento distribuido.

Para la demostracion completa de Data Lake, streaming y Spark consulta [docs/GUIA_DEMOSTRACION.md](docs/GUIA_DEMOSTRACION.md).

Para migrar el procesamiento Spark a Databricks sin modificar el job local, usa [databricks/spark_jobs_databricks.py](databricks/spark_jobs_databricks.py) y sigue [docs/GUIA_DATABRICKS.md](docs/GUIA_DATABRICKS.md).

Para publicar el Data Lake en AWS S3 usa [scripts/data_lake_s3.py](scripts/data_lake_s3.py) y sigue [docs/GUIA_S3.md](docs/GUIA_S3.md). El lector [scripts/leer_data_lake_s3.py](scripts/leer_data_lake_s3.py) verifica que un Parquet remoto pueda descargarse y leerse correctamente.

El publicador usa por defecto el bucket `abp-data-lake-neonwaac-2026`, región `us-east-1`, perfil AWS `heavycult` y prefijo `heavycult`, por lo que basta ejecutar `python scripts\\data_lake_s3.py`. Para ampliar datos de forma real usa `python scripts\\generar_ventas_adicionales.py --ventas 100000` y luego reconstruye OLAP, Data Lake y S3.

Para separar el Data Warehouse de MongoDB y cargarlo en BigQuery Sandbox usa [scripts/data_warehouse_bigquery.py](scripts/data_warehouse_bigquery.py) y sigue [docs/GUIA_BIGQUERY.md](docs/GUIA_BIGQUERY.md). El proyecto usa `GCP_PROJECT_ID`, `BQ_DATASET` y `BQ_LOCATION` desde `.env`, por lo que basta ejecutar `python scripts\\data_warehouse_bigquery.py`.

## CI/CD DataOps

El workflow [deploy.yml](.github/workflows/deploy.yml) valida Python y Terraform automáticamente en cada push o pull request. El plan Terraform se ejecuta en CI; el apply queda reservado para una ejecución manual desde GitHub Actions. Consulta [docs/GUIA_CICD.md](docs/GUIA_CICD.md) para publicar el repositorio y demostrar el pipeline.

## Streaming en tiempo real

El streaming usa MongoDB Change Streams sobre `heavycult.orders`. No ejecuta la generacion masiva ni crea colecciones.

No es necesario ejecutar `scripts/crear_estructura.py` ni `scripts/generar_datos_masivos.py`: ambos deben haber sido ejecutados previamente y el emisor solo utiliza clientes y productos que ya existan.

Abre dos terminales en la raiz del proyecto. En la primera inicia el receptor:

```bash
python scripts/escuchar_ventas_stream.py
```

En la segunda inicia el emisor. Para una demostracion de cinco ventas:

```bash
python scripts/enviar_ventas_stream.py --cantidad 5 --intervalo 3
```

Para dejarlo enviando hasta detenerlo con `Ctrl+C`:

```bash
python scripts/enviar_ventas_stream.py
```

Cada venta insertada en `orders` debe aparecer casi inmediatamente en la terminal del receptor y quedar registrada en `data_lake/raw/streaming_ventas.jsonl`.

## Dashboard de monitoreo

El dashboard ejecuta 10 consultas analíticas sobre `ventas_analiticas`, mide la latencia de cada una, verifica índices compuestos y genera una imagen con:

- documentos por colección;
- rendimiento de las 10 consultas frente al SLA de 500 ms;
- estimación de costos mensuales;
- tendencia mensual de ventas;
- métricas de almacenamiento;
- resumen ejecutivo del sistema.

La dependencia gráfica está incluida en `requirements.txt`. Para instalarla en el entorno virtual y generar el dashboard:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\dashboard_monitoreo.py
```

Los resultados se guardan en `dashboards/`:

```text
dashboard_monitoreo_YYYYMMDD_HHMMSS.png
dashboard_monitoreo_YYYYMMDD_HHMMSS.json
```

La imagen PNG es la evidencia visual para la presentación. El JSON conserva las latencias, cantidades y métricas usadas para construirla. El costo por defecto es ilustrativo para M10 y puede ajustarse con `MONGO_TIER`, `MONGO_MONTHLY_COST` y `DASHBOARD_SLA_MS` en `.env`.

## Data Warehouse dimensional

Construye las dimensiones y la tabla de hechos a partir de las colecciones existentes. Este paso no ejecuta la generacion masiva ni crea la estructura OLTP:

```powershell
python scripts/data_warehouse.py
```

Se crean cuatro colecciones consultables como tablas desde DBCode o Atlas SQL Interface:

- `dim_cliente`
- `dim_producto`
- `dim_fecha`
- `fact_ventas`

El grano de `fact_ventas` es una fila por item de pedido. Las consultas de demostracion estan en [docs/data_warehouse_queries.sql](docs/data_warehouse_queries.sql).

## Troubleshooting (del documento)
- `bad auth : authentication failed` -> restablecer password en Atlas > Database Access
- `E11000 duplicate key` -> ya manejado con `ordered=False`
- `$cond takes exactly 3 arguments` -> anidar `$cond`
- Consultas lentas -> revisar indices compuestos
- `SSL handshake failed` -> confirmar la IP en Atlas > Network Access, desactivar temporalmente VPN/proxy/inspeccion HTTPS o probar otra red. No usar `tlsAllowInvalidCertificates=true`.
