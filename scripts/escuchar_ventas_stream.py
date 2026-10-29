import json
import os
from datetime import date, datetime, timezone
from pathlib import Path

import pymongo
from bson import ObjectId
from dotenv import load_dotenv
from pymongo.errors import ConfigurationError, ConnectionFailure, ServerSelectionTimeoutError


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("MONGO_DATABASE", "heavycult")
STREAM_FILE = BASE_DIR / "data_lake" / "raw" / "streaming_ventas.jsonl"


def convertir_valores(valor):
    if isinstance(valor, ObjectId):
        return str(valor)
    if isinstance(valor, dict):
        return {clave: convertir_valores(elemento) for clave, elemento in valor.items()}
    if isinstance(valor, list):
        return [convertir_valores(elemento) for elemento in valor]
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    return valor


def escuchar_ventas():
    if not MONGO_URI:
        raise RuntimeError("MONGO_URI no esta configurado en .env.")

    STREAM_FILE.parent.mkdir(parents=True, exist_ok=True)
    client = pymongo.MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
        socketTimeoutMS=20000,
    )
    try:
        client.admin.command("ping")
        coleccion = client[DATABASE_NAME]["orders"]
        pipeline = [{"$match": {"operationType": "insert"}}]
        print(f"[RECEPTOR] Escuchando nuevas ventas en '{DATABASE_NAME}.orders'. Ctrl+C para detener.")
        with coleccion.watch(pipeline, full_document="default") as cambios:
            for cambio in cambios:
                venta = convertir_valores(cambio["fullDocument"])
                evento = {
                    "recibido_en": datetime.now(timezone.utc).isoformat(),
                    "operacion": cambio["operationType"],
                    "venta": venta,
                }
                with STREAM_FILE.open("a", encoding="utf-8") as archivo:
                    archivo.write(json.dumps(evento, ensure_ascii=False) + "\n")
                print(
                    f"[RECEPTOR] Venta recibida: {venta.get('order_number')} | "
                    f"estado={venta.get('status')} | guardada en {STREAM_FILE.name}"
                )
    except ServerSelectionTimeoutError as error:
        detalle = str(error).split("Timeout:", 1)[0].strip()
        print("[ERROR] No se pudo establecer la conexion TLS con MongoDB Atlas.")
        print(f"[DETALLE] {detalle}")
        print("[REVISA] Atlas Network Access, VPN/antivirus/proxy y la fecha del sistema.")
        print("[REVISA] Prueba tambien desde otra red, por ejemplo un hotspot movil.")
    except (ConnectionFailure, ConfigurationError) as error:
        print(f"[ERROR] Fallo de conexion/configuracion de MongoDB: {error}")
    except KeyboardInterrupt:
        print("\n[RECEPTOR] Detenido por el usuario.")
    finally:
        client.close()


if __name__ == "__main__":
    escuchar_ventas()