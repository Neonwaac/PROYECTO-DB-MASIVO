# Guia paso a paso: Data Lake en AWS S3

Esta migracion conserva el Data Lake local y publica una copia en S3. No modifica MongoDB, el streaming ni Databricks.

## 1. Generar los Parquet locales

Desde PowerShell, en la raíz:

```powershell
.\.venv\Scripts\python.exe data_lake.py
```

Verifica:

```powershell
Get-ChildItem data_lake -Recurse -Filter *.parquet
```

Debe existir como minimo:

```text
data_lake/raw/clientes.parquet
data_lake/raw/productos.parquet
data_lake/raw/ventas.parquet
data_lake/processed/ventas_procesadas.parquet
data_lake/curated/ventas_analiticas.parquet
```

## 2. Crear el bucket en AWS

1. Entra a la consola de AWS.
2. Abre **S3**.
3. Pulsa **Create bucket**.
4. Usa un nombre globalmente único, por ejemplo:

```text
abp-data-lake-neonwaac-2026
```

El nombre exacto `abp-data-lake-juanpablo` puede estar ocupado por otra cuenta. Si AWS lo rechaza, cambia el sufijo.

5. Selecciona la misma región que usarás en AWS CLI.
6. Mantén activado **Block all public access**.
7. Mantén el cifrado del lado del servidor con **SSE-S3**.
8. Crea el bucket.

No habilites acceso público para este proyecto.

## 3. Crear permisos mínimos

Usa un usuario o rol IAM con acceso limitado al bucket, no la cuenta root. Para una demostración puedes crear una política restringida al bucket:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::abp-data-lake-neonwaac-2026"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:HeadObject"],
      "Resource": "arn:aws:s3:::abp-data-lake-neonwaac-2026/*"
    }
  ]
}
```

Sustituye el nombre del bucket por el tuyo. Nunca guardes `AWS_ACCESS_KEY_ID` o `AWS_SECRET_ACCESS_KEY` dentro del código ni los subas a GitHub.

## 4. Configurar credenciales localmente

Instala AWS CLI si todavía no la tienes. Después, configura un perfil:

```powershell
aws configure --profile heavycult
```

Introduce cuando lo solicite:

```text
AWS Access Key ID
AWS Secret Access Key
Default region name: us-east-1
Default output format: json
```

Las credenciales quedan en la carpeta de configuración de AWS del usuario y no en el repositorio.

Comprueba identidad:

```powershell
aws sts get-caller-identity --profile heavycult
```

Comprueba el bucket:

```powershell
aws s3 ls s3://abp-data-lake-neonwaac-2026 --profile heavycult
```

## 5. Instalar boto3

Con el entorno virtual activo:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

La dependencia añadida es `boto3`.

## 6. Publicar el Data Lake

El proyecto ya tiene configurados por defecto el bucket `abp-data-lake-neonwaac-2026`, la región `us-east-1`, el perfil `heavycult` y el prefijo `heavycult`. Por eso puedes ejecutar simplemente:

```powershell
python scripts\data_lake_s3.py
```

También puedes sobrescribir los valores explícitamente:

```powershell
python scripts\data_lake_s3.py --bucket abp-data-lake-neonwaac-2026 --prefix heavycult --region us-east-1 --profile heavycult
```

El script:

- descubre todos los `.parquet` debajo de `data_lake`;
- valida filas, columnas, tamaño y Parquet antes de subir;
- conserva las zonas `raw`, `processed` y `curated`;
- cifra cada objeto con SSE-S3;
- verifica el tamaño remoto;
- genera `heavycult/manifest.json`.

## 6.1 Aumentar el volumen de datos de forma real

Los 3.6 MiB actuales son coherentes con unas 30.000 órdenes y la compresión Snappy. Para crecer sin duplicar artificialmente archivos, agrega órdenes nuevas con identificadores únicos:

```powershell
python scripts\generar_ventas_adicionales.py --ventas 100000 --batch-size 1000
```

Después reconstruye la capa analítica y vuelve a exportar:

```powershell
python scripts\transformar_oltp_a_olap.py
python data_lake.py
python scripts\data_lake_s3.py
```

El valor `100000` es una demostración razonable. Puedes usar `500000` o más si tu cluster y el límite de costos lo permiten. No es necesario llenar 5 GB para demostrar la arquitectura; S3 almacenará el tamaño real comprimido de los datos.

Las rutas quedan así:

```text
s3://abp-data-lake-neonwaac-2026/heavycult/raw/clientes.parquet
s3://abp-data-lake-neonwaac-2026/heavycult/raw/productos.parquet
s3://abp-data-lake-neonwaac-2026/heavycult/raw/ventas.parquet
s3://abp-data-lake-neonwaac-2026/heavycult/processed/ventas_procesadas.parquet
s3://abp-data-lake-neonwaac-2026/heavycult/curated/ventas_analiticas.parquet
```

## 7. Verificar en AWS

```powershell
aws s3 ls s3://abp-data-lake-neonwaac-2026/heavycult/ --recursive --human-readable --summarize --profile heavycult
```

En la consola S3 muestra:

- el bucket;
- las carpetas `raw`, `processed` y `curated`;
- los objetos Parquet;
- el tamaño de cada objeto;
- el cifrado SSE-S3.

## 8. Leer un Parquet desde S3

El lector descarga un objeto temporalmente y lo abre con Pandas/PyArrow para demostrar que el archivo remoto es legible:

```powershell
python scripts\leer_data_lake_s3.py `
  --bucket abp-data-lake-neonwaac-2026 `
  --key heavycult/processed/ventas_procesadas.parquet `
  --region us-east-1 `
  --profile heavycult
```

Salida esperada:

```text
[S3] s3://.../processed/ventas_procesadas.parquet
[S3] Filas: ...
[S3] Columnas: [...]
```

## 9. Evidencia para la presentación

Muestra, en este orden:

1. Bucket privado creado en S3.
2. Bloqueo de acceso público activado.
3. Objetos organizados por `raw`, `processed` y `curated`.
4. Ejecución de `data_lake_s3.py` con los Parquet validados.
5. `manifest.json` generado.
6. `aws s3 ls --recursive` mostrando los objetos.
7. `leer_data_lake_s3.py` leyendo `ventas_procesadas.parquet` desde S3.
8. El tamaño remoto coincidiendo con la verificación del publicador.

Explicación recomendada:

> El Data Lake local se conserva como fuente de desarrollo, pero se publica en Amazon S3 como almacenamiento de objetos. El script mantiene las zonas Raw, Processed y Curated, valida los Parquet antes de cargarlos, cifra los objetos y verifica que la transferencia haya terminado correctamente. La computación permanece separada del almacenamiento, como en una arquitectura cloud real.

## 10. Costos y seguridad

AWS Free Tier y sus condiciones pueden cambiar. Revisa la página de precios y configura una alerta de presupuesto. No subas secretos al repositorio, no habilites acceso público y elimina el bucket cuando termines la práctica si no necesitas conservarlo.
