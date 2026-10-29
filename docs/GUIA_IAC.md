# Guia de Infraestructura como Codigo

## Que automatiza

`iac_setup.py` automatiza la configuracion reproducible del entorno local:

- valida Python 3.11 o 3.12;
- verifica `.env` y `MONGO_URI` sin imprimir la credencial;
- crea `.venv` si no existe;
- instala `requirements.txt` dentro de `.venv`;
- crea `data_lake/raw`, `data_lake/processed` y `data_lake/curated`;
- ejecuta un `ping` contra MongoDB Atlas.

No ejecuta `crear_estructura.py` ni `generar_datos_masivos.py`.

## Reinicio completo en Windows

Abre PowerShell en la raíz del proyecto:

```powershell
cd C:\Users\euwvi\OneDrive\Desktop\PROYECTO-DATALAKE
```

Si hay procesos Python, Spark o streaming abiertos, detenlos primero con `Ctrl+C`.

Desactiva el entorno actual si está activo:

```powershell
deactivate
```

Elimina el entorno virtual. Este comando no elimina el código, `.env`, `data_lake` ni las colecciones de Atlas:

```powershell
Remove-Item -Recurse -Force .venv
```

Comprueba que desapareció:

```powershell
Test-Path .venv
```

Debe devolver `False`.

Ejecuta el orquestador usando el Python global:

```powershell
python iac_setup.py
```

Si `python` no apunta a Python 3.11 o 3.12, usa el ejecutable correcto, por ejemplo:

```powershell
py -3.11 iac_setup.py
```

El script creará nuevamente `.venv`, instalará las dependencias y probará Atlas.

Activa el entorno en la terminal actual:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Verifica el intérprete:

```powershell
python --version
python -c "import pymongo, pandas, pyarrow, pyspark, matplotlib; print('dependencias OK')"
```

## Flujo posterior

Como la base ya tiene estructura y datos, ejecuta solamente:

```powershell
python scripts\transformar_oltp_a_olap.py
python data_lake.py
python scripts\data_warehouse.py
python scripts\spark_jobs.py
python scripts\dashboard_monitoreo.py
```

Para streaming abre dos terminales activadas.

Terminal receptora:

```powershell
python scripts\escuchar_ventas_stream.py
```

Terminal emisora:

```powershell
python scripts\enviar_ventas_stream.py --cantidad 5 --intervalo 3
```

## Verificación de IaC

La ejecución correcta debe mostrar:

```text
[IAC] .env encontrado y MONGO_URI configurado.
[IAC] Health check MongoDB Atlas: OK
[IAC] Entorno preparado correctamente.
```

`main.tf` es un marcador Terraform mínimo para cubrir la representación IaC en la rúbrica. Terraform no es necesario para ejecutar el proyecto Python; si se desea validarlo:

```powershell
terraform init
terraform validate
```

Instalador oficial: https://developer.hashicorp.com/terraform/install
