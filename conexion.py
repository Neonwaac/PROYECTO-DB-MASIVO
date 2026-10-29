import os
import pymongo
from dotenv import load_dotenv
from pymongo.errors import ConnectionFailure, ConfigurationError, OperationFailure

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("MONGO_DATABASE", "heavycult")

def conectar_mongodb():
    if not MONGO_URI or "<usuario>" in MONGO_URI:
        print("[ERROR] MONGO_URI no configurado. Edita el archivo .env con tu connection string de Atlas.")
        return None, None
    try:
        print("[CLIQUEANDO] Intentando conectar a MongoDB Atlas...")
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print("[OK] Conexion exitosa a MongoDB Atlas!")
        db = client[DATABASE_NAME]
        return client, db
    except ConnectionFailure:
        print("[ERROR] Error: No se pudo contactar al servidor.")
    except ConfigurationError as e:
        print(f"[ERROR] Error de configuracion: {e}")
    except OperationFailure as e:
        print(f"[ERROR] Error de autenticacion: {e}")
    return None, None

if __name__ == "__main__":
    client, db = conectar_mongodb()
    if client:
        client.close()
        print("[CANDADO] Conexion cerrada.")
