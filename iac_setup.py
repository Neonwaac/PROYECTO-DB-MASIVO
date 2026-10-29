import os
import platform
import subprocess
import sys
import venv
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
VENV_DIR = BASE_DIR / ".venv"
REQUIREMENTS_FILE = BASE_DIR / "requirements.txt"
DATA_LAKE_DIR = BASE_DIR / "data_lake"
ZONES = ("raw", "processed", "curated")
MIN_PYTHON = (3, 11)
MAX_PYTHON = (3, 13)


def ejecutar(comando, descripcion):
    print(f"[IAC] {descripcion}")
    subprocess.run(comando, cwd=BASE_DIR, check=True)


def python_del_venv():
    if platform.system() == "Windows":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def validar_python():
    version = sys.version_info[:2]
    print(f"[IAC] Python detectado: {sys.version.split()[0]}")
    if not (MIN_PYTHON <= version < MAX_PYTHON):
        raise RuntimeError(
            f"Se requiere Python >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]} y < "
            f"{MAX_PYTHON[0]}.{MAX_PYTHON[1]}."
        )


def crear_entorno_virtual():
    interprete = python_del_venv()
    if not interprete.exists():
        print(f"[IAC] Creando entorno virtual: {VENV_DIR}")
        venv.EnvBuilder(with_pip=True, clear=False).create(VENV_DIR)
    else:
        print(f"[IAC] Entorno virtual existente: {VENV_DIR}")
    return interprete


def instalar_dependencias(interprete):
    if not REQUIREMENTS_FILE.exists():
        raise FileNotFoundError(f"No existe {REQUIREMENTS_FILE}")
    ejecutar([str(interprete), "-m", "pip", "install", "--upgrade", "pip"], "Actualizando pip")
    ejecutar(
        [str(interprete), "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)],
        "Instalando requirements.txt",
    )


def crear_estructura_local():
    for zona in ZONES:
        ruta = DATA_LAKE_DIR / zona
        ruta.mkdir(parents=True, exist_ok=True)
        print(f"[IAC] Zona lista: {ruta}")


def validar_env():
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        raise RuntimeError("No existe .env. Crea MONGO_URI antes del health check.")

    variables = {}
    for linea in env_file.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        nombre, valor = linea.split("=", 1)
        variables[nombre.strip()] = valor.strip().strip('"').strip("'")

    if not variables.get("MONGO_URI"):
        raise RuntimeError(".env no contiene MONGO_URI.")
    print("[IAC] .env encontrado y MONGO_URI configurado.")


def health_check(interprete):
    health_code = """
from pathlib import Path
from dotenv import load_dotenv
import os
import pymongo

load_dotenv(Path.cwd() / ".env")
uri = os.getenv("MONGO_URI")
if not uri:
    raise RuntimeError("MONGO_URI no configurado")
client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=10000)
client.admin.command("ping")
print("[IAC] Health check MongoDB Atlas: OK")
client.close()
"""
    ejecutar([str(interprete), "-c", health_code], "Probando conexión con MongoDB Atlas")


def mostrar_siguientes_pasos(interprete):
    if platform.system() == "Windows":
        activar = r".\.venv\Scripts\Activate.ps1"
    else:
        activar = "source .venv/bin/activate"
    print("\n[IAC] Entorno preparado correctamente.")
    print(f"[IAC] Intérprete configurado: {interprete}")
    print("[IAC] Para activarlo en una nueva terminal:")
    print(f"      {activar}")
    print("[IAC] Después ejecuta, según tu flujo:")
    print("      python data_lake.py")
    print("      python scripts/dashboard_monitoreo.py")
    print("      python scripts/spark_jobs.py")


def main():
    print("=" * 64)
    print("HeavyCult - Infrastructure/Configuration as Code")
    print("=" * 64)
    validar_python()
    validar_env()
    interprete = crear_entorno_virtual()
    instalar_dependencias(interprete)
    crear_estructura_local()
    health_check(interprete)
    mostrar_siguientes_pasos(interprete)


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"[IAC][ERROR] {error}")
        sys.exit(1)
