# Guia CI/CD DataOps con GitHub Actions

El workflow está en `.github/workflows/deploy.yml`.

## Qué ejecuta automáticamente

En cada `push` o `pull_request` hacia `main` o `master`:

1. Configura Python 3.11.
2. Instala `requirements.txt`.
3. Compila todos los scripts Python.
4. Verifica imports principales.
5. Instala Terraform 1.16.4.
6. Ejecuta `terraform fmt -check`.
7. Ejecuta `terraform init`.
8. Ejecuta `terraform validate`.
9. Ejecuta `terraform plan`.

El workflow no ejecuta `data_lake.py`, `generar_datos_masivos.py`, el streaming ni cargas contra MongoDB. Esto evita que un push modifique datos reales o consuma servicios cloud automáticamente.

## 1. Publicar el repositorio en GitHub

Desde PowerShell, en la raíz:

```powershell
git status
git add .
git commit -m "Add DataOps CI/CD workflow"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git
git push -u origin main
```

Si el remoto ya existe, no repitas `git remote add origin`; usa solamente:

```powershell
git add .
git commit -m "Add DataOps CI/CD workflow"
git push
```

No subas `.env`, `.venv`, `*.tfstate`, Parquet ni claves cloud. El `.gitignore` ya cubre esos artefactos principales.

## 2. Ver el pipeline

1. Abre el repositorio en GitHub.
2. Pulsa la pestaña **Actions**.
3. Busca el workflow **HeavyCult DataOps**.
4. Abre la ejecución asociada al commit.
5. Revisa los jobs:
   - `Validar Python`;
   - `Validar Terraform`.

Cada job debe aparecer en verde.

## 3. Qué evidencia mostrar

En `Validar Python` muestra:

```text
Dependencias principales OK
```

En `Validar Terraform` muestra:

```text
Success! The configuration is valid.
```

Y el resultado del plan:

```text
Plan: 1 to add, 0 to change, 0 to destroy.
```

Esto demuestra que GitHub Actions valida automáticamente el código y la infraestructura declarativa.

## 4. Ejecutar el apply manual

El apply no se ejecuta en cada push. Para demostrarlo:

1. En GitHub entra a **Actions**.
2. Selecciona **HeavyCult DataOps**.
3. Pulsa **Run workflow**.
4. Selecciona la rama `main`.
5. En `Aplicar Terraform manualmente`, selecciona `true`.
6. Pulsa **Run workflow**.

El job `Aplicar Terraform manualmente` se ejecutará solamente después de que Python y Terraform pasen.

En la primera ejecución GitHub puede pedir configurar el environment `production`. Para una práctica académica puedes crear el environment sin reglas adicionales; para un entorno real conviene exigir aprobación de un responsable.

## 5. Importante sobre el Terraform actual

El `main.tf` actual usa `terraform_data` como marcador académico. Por tanto, GitHub Actions demostrará correctamente:

- validación IaC;
- generación de plan;
- aplicación del estado Terraform.

Pero todavía no provisiona un bucket S3, un proyecto BigQuery ni un cluster MongoDB. Para que el pipeline cree infraestructura cloud real habría que reemplazar el marcador por proveedores y recursos Terraform, además de guardar secretos en **GitHub Secrets**.

## 6. Secretos para una futura infraestructura cloud

Nunca pongas credenciales en el workflow. Usa:

```text
Settings > Secrets and variables > Actions > New repository secret
```

Ejemplos futuros:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
GOOGLE_CREDENTIALS
MONGO_URI
```

El workflow actual no requiere esos secretos porque solo valida Terraform y código local.
