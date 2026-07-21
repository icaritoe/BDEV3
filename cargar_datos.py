import os
import sys
import json
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DB_NAME = os.getenv("MONGO_DB_NAME", "prueba3")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))
RUTA_INVITADOS = os.path.join(CARPETA_ACTUAL, "invitados.json")
RUTA_EVENTOS = os.path.join(CARPETA_ACTUAL, "eventos.json")


def cargar_json(ruta):
    if not os.path.exists(ruta):
        print(f"[ERROR] No se encontró el archivo: {ruta}")
        sys.exit(1)
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"[ERROR] El archivo '{ruta}' no es un JSON válido: {e}")
        sys.exit(1)


def main():
    print(f"Conectando a MongoDB en '{MONGO_URI}' ...")
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
    except ConnectionFailure:
        print("[ERROR] No se pudo conectar a MongoDB. ¿Está corriendo el servicio?")
        sys.exit(1)

    db = client[DB_NAME]

    invitados = cargar_json(RUTA_INVITADOS)
    eventos = cargar_json(RUTA_EVENTOS)

    try:
        db["invitados"].delete_many({})
        db["eventos"].delete_many({})

        if invitados:
            db["invitados"].insert_many(invitados)
        if eventos:
            db["eventos"].insert_many(eventos)

        # Índices recomendados para las consultas de la app
        db["invitados"].create_index("rut", unique=True)
        db["invitados"].create_index("correo")
        db["eventos"].create_index("codigo", unique=True)
        db["eventos"].create_index("invitados.rut")

        print(f"\n[OK] Base de datos '{DB_NAME}' poblada correctamente:")
        print(
            f"  - invitados: {db['invitados'].count_documents({})} documentos")
        print(f"  - eventos:   {db['eventos'].count_documents({})} documentos")

    except PyMongoError as e:
        print(f"[ERROR] Ocurrió un problema al insertar los datos: {e}")
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
