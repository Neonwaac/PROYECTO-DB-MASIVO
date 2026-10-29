# Guia paso a paso: Data Warehouse en BigQuery Sandbox

Esta guia separa los roles de la arquitectura:

```text
MongoDB Atlas = OLTP / fuente operacional
BigQuery      = Data Warehouse / analitica OLAP
Python ETL    = lectura de MongoDB + carga de BigQuery
```

El script no modifica MongoDB. Solo lee `dim_cliente`, `dim_producto`, `dim_fecha` y `fact_ventas`.

## 1. Crear o seleccionar proyecto Google Cloud

1. Entra a https://console.cloud.google.com/
2. Inicia sesion con tu cuenta Google.
3. En la barra superior pulsa el selector de proyecto.
4. Pulsa **New Project**.
5. En **Project name**, escribe:

```text
heavycult-data-warehouse
```

6. Pulsa **Create**.
7. Vuelve al selector de proyecto y selecciona el proyecto nuevo.
8. Copia el **Project ID**, no solo el nombre visible. Sera una cadena parecida a:

```text
heavycult-data-warehouse-123456
```

Necesitaras ese ID para ejecutar el script.

## 2. Abrir BigQuery Sandbox

1. En la barra de busqueda de Google Cloud escribe `BigQuery`.
2. Selecciona **BigQuery**.
3. Si aparece la opcion de activar **BigQuery Sandbox**, aceptala.
4. No agregues tarjeta si quieres permanecer en Sandbox.
5. Si Google solicita habilitar la API, pulsa **Enable**.

El Sandbox tiene limites gratuitos. No intentes cargar terabytes ni ejecutes consultas sin filtros sobre volúmenes grandes.

## 3. Crear el dataset

Puedes hacerlo desde la interfaz:

1. En BigQuery Explorer selecciona tu proyecto.
2. Pulsa los tres puntos del proyecto.
3. Selecciona **Create dataset**.
4. En **Dataset ID**, escribe:

```text
heavycult_dw
```

5. En **Data location**, selecciona:

```text
US (multiple regions in United States)
```

6. Deja el resto de opciones por defecto.
7. Pulsa **Create dataset**.

El script tambien puede crearlo automáticamente, pero es recomendable verlo creado en la interfaz antes de ejecutar el ETL.

## 4. Preparar autenticacion local

La opcion recomendada para una practica local es Google Cloud CLI con Application Default Credentials.

Instala Google Cloud CLI desde:

```text
https://cloud.google.com/sdk/docs/install
```

Cierra y abre PowerShell despues de instalarlo. Comprueba:

```powershell
gcloud --version
```

Inicia sesion:

```powershell
gcloud auth login
```

Se abrira el navegador. Autoriza la cuenta Google que tiene el proyecto.

Selecciona el proyecto:

```powershell
gcloud config set project TU_PROJECT_ID
```

Crea las credenciales que usara `google-cloud-bigquery`:

```powershell
gcloud auth application-default login
```

Autoriza nuevamente en el navegador.

Comprueba la configuracion:

```powershell
gcloud config get-value project
```

No subas archivos de credenciales ni tokens al repositorio.

## 5. Configurar el proyecto Python

Activa el entorno:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instala las dependencias:

```powershell
python -m pip install -r requirements.txt
```

Comprueba BigQuery:

```powershell
python -c "from google.cloud import bigquery; print('BigQuery OK')"
```

## 6. Asegurar el modelo dimensional en MongoDB

Antes del ETL hacia BigQuery, las cuatro colecciones deben existir y tener datos:

```powershell
python scripts\data_warehouse.py
```

Este comando reconstruye solamente el Data Warehouse dentro de MongoDB:

```text
dim_cliente
dim_producto
dim_fecha
fact_ventas
```

## 7. Ejecutar el ETL MongoDB -> BigQuery

1. El Project ID queda configurado en `.env` mediante `GCP_PROJECT_ID`. Ejecuta simplemente:

```powershell
python scripts/data_warehouse_bigquery.py
```

2. Si alguna vez necesitas sobrescribirlo temporalmente:

1. Hace ping a MongoDB Atlas.
python scripts/data_warehouse_bigquery.py --project OTRO_PROJECT_ID
3. Crea `heavycult_dw` si no existe.
4. Crea o reemplaza las cuatro tablas BigQuery.
5. Aplica esquemas tipados.
6. Muestra las filas cargadas.

Salida esperada:

```text
[BQ] Dataset listo: TU_PROJECT_ID.heavycult_dw (US)
[BQ] Fuente MongoDB dim_cliente: ... filas
[BQ] Fuente MongoDB dim_producto: ... filas
[BQ] Fuente MongoDB dim_fecha: ... filas
[BQ] Fuente MongoDB fact_ventas: ... filas
[BQ] TU_PROJECT_ID.heavycult_dw.dim_cliente: ... filas
[BQ] ...
[BQ] Data Warehouse exportado correctamente desde MongoDB.
```

El modo `WRITE_TRUNCATE` reemplaza las tablas de BigQuery en cada ejecución y evita duplicar filas. No borra las colecciones de MongoDB.

## 8. Validar las tablas en BigQuery

En BigQuery Explorer abre:

```text
TU_PROJECT_ID
└── heavycult_dw
    ├── dim_cliente
    ├── dim_producto
    ├── dim_fecha
    └── fact_ventas
```

Abre cada tabla y revisa la pestaña **Schema** y el número de filas.

## 9. Consultas de demostracion

En el SQL editor de BigQuery ejecuta, reemplazando `TU_PROJECT_ID`:

### Ventas por método de pago

```sql
SELECT metodo_pago,
       SUM(total_venta) AS total_ventas,
       COUNT(*) AS lineas
FROM `TU_PROJECT_ID.heavycult_dw.fact_ventas`
GROUP BY metodo_pago
ORDER BY total_ventas DESC;
```

### Ventas por ciudad

```sql
SELECT c.departamento,
       c.ciudad,
       SUM(f.total_venta) AS ingresos,
       SUM(f.ganancia_neta) AS ganancia
FROM `TU_PROJECT_ID.heavycult_dw.fact_ventas` AS f
JOIN `TU_PROJECT_ID.heavycult_dw.dim_cliente` AS c
  ON f.cliente_key = c.cliente_key
GROUP BY c.departamento, c.ciudad
ORDER BY ingresos DESC;
```

### Evolución mensual

```sql
SELECT d.anio,
       d.mes,
       SUM(f.total_venta) AS ingresos,
       SUM(f.cantidad) AS unidades
FROM `TU_PROJECT_ID.heavycult_dw.fact_ventas` AS f
JOIN `TU_PROJECT_ID.heavycult_dw.dim_fecha` AS d
  ON f.fecha_key = d.fecha_key
GROUP BY d.anio, d.mes
ORDER BY d.anio, d.mes;
```

### Validación de volúmenes

```sql
SELECT 'fact_ventas' AS tabla, COUNT(*) AS filas
FROM `TU_PROJECT_ID.heavycult_dw.fact_ventas`
UNION ALL
SELECT 'dim_cliente', COUNT(*)
FROM `TU_PROJECT_ID.heavycult_dw.dim_cliente`
UNION ALL
SELECT 'dim_producto', COUNT(*)
FROM `TU_PROJECT_ID.heavycult_dw.dim_producto`
UNION ALL
SELECT 'dim_fecha', COUNT(*)
FROM `TU_PROJECT_ID.heavycult_dw.dim_fecha`;
```

## 10. Evidencia para la presentación

Muestra:

1. Proyecto Google Cloud activo.
2. BigQuery Sandbox habilitado.
3. Dataset `heavycult_dw`.
4. Las cuatro tablas creadas.
5. La terminal ejecutando `data_warehouse_bigquery.py`.
6. El esquema de `fact_ventas`.
7. Una consulta con `JOIN` entre hechos y dimensión.
8. Los conteos coincidentes con MongoDB.

Explicación recomendada:

> MongoDB Atlas conserva el procesamiento transaccional OLTP y BigQuery aloja una copia dimensional para analítica OLAP. Un ETL en Python lee las dimensiones y la tabla de hechos desde MongoDB, aplica esquemas tipados y las carga en BigQuery con reemplazo controlado. De esta forma, las escrituras operacionales y las consultas analíticas se ejecutan en plataformas separadas.

## 11. Límites y seguridad

- El Sandbox de BigQuery tiene límites gratuitos; no es una cuenta empresarial ilimitada.
- Revisa el estimador de costos antes de consultas grandes.
- No subas credenciales JSON al repositorio.
- No uses la cuenta root de Google Cloud para automatización permanente.
- No ejecutes `WRITE_TRUNCATE` sobre tablas que contengan datos manuales; este ETL es dueño de las cuatro tablas del dataset `heavycult_dw`.
