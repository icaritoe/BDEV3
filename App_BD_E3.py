"""
App_BD_E3.py
============
Gestor de Eventos e Invitados - Evaluación Sumativa 4 (TI3032).

Aplicación de consola en Python que se conecta a una base de datos
MongoDB para administrar eventos e invitados. Cubre operaciones CRUD
completas (crear, leer, modificar y eliminar) además de consultas de
negocio (búsquedas, cruces y estadísticas) usando el framework de
agregación de MongoDB.

Requiere: pymongo, python-dotenv (ver requirements.txt)
Configuración: variables MONGO_URI y MONGO_DB_NAME en un archivo .env
(ver .env.example).
"""

import os
import re
import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError, ConfigurationError

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ==========================================
# CONFIGURACIÓN
# ==========================================
DB_NAME = os.getenv("MONGO_DB_NAME", "prueba3")  # nombre de la BD en MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")


def waitput():
    """Pausa la ejecución hasta que el usuario presione Enter."""
    try:
        input("\nPresione ENTER para continuar...")
    except (EOFError, KeyboardInterrupt):
        print()


def pedir_texto(mensaje):
    """input() seguro: nunca lanza excepción no controlada y siempre
    devuelve un string (vacío si el usuario cancela)."""
    try:
        return input(mensaje).strip()
    except (EOFError, KeyboardInterrupt):
        print("\n[AVISO] Entrada cancelada.")
        return ""


def texto_regex_seguro(texto):
    """Escapa caracteres especiales de regex en la entrada del usuario
    antes de usarla en una consulta $regex de MongoDB. Esto evita que un
    texto con caracteres como '.', '*' o '(' provoque errores o resultados
    inesperados (buena práctica de seguridad al construir consultas con
    entrada de usuario)."""
    return re.escape(texto)


# ==========================================
# CONEXIÓN Y DETECCIÓN AUTOMÁTICA DE COLECCIONES
# ==========================================
def conectar_base_datos():
    """
    Se conecta a MongoDB y detecta automáticamente cuáles colecciones
    dentro de DB_NAME contienen los datos de "eventos" e "invitados",
    sin importar el nombre exacto que se les haya puesto al importarlas.
    """
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
    except ConnectionFailure:
        print(f"\n[ERROR] No se pudo conectar a MongoDB en '{MONGO_URI}'.")
        print(
            "Verifique que el servicio de MongoDB esté corriendo y que la URI sea correcta.")
        sys.exit(1)
    except ConfigurationError as e:
        print(f"\n[ERROR] La URI de MongoDB no es válida: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR INESPERADO al conectar] {e}")
        sys.exit(1)

    try:
        db = client[DB_NAME]
        colecciones_existentes = db.list_collection_names()

        col_eventos = ""
        col_invitados = ""
        for c in colecciones_existentes:
            cantidad = db[c].count_documents({})
            if cantidad > 0:
                nombre_lower = c.lower()
                if "evento" in nombre_lower:
                    col_eventos = c
                elif "invitado" in nombre_lower:
                    col_invitados = c

        if not col_eventos or not col_invitados:
            print(
                "\n[ERROR CRÍTICO] La base de datos no tiene colecciones válidas con datos.")
            print(f"Base de datos: '{DB_NAME}'")
            print(f"Colecciones detectadas: {colecciones_existentes}")
            print("\nSugerencia: importe los archivos eventos.json e invitados.json con")
            print(
                "'mongoimport' o ejecute el script cargar_datos.py incluido en este proyecto.")
            client.close()
            sys.exit(1)

        print(f"\n[SISTEMA OK] Conectado a la base '{DB_NAME}'.")
        print(f"  - Colección de eventos:   '{col_eventos}'")
        print(f"  - Colección de invitados: '{col_invitados}'")
        return client, db, col_eventos, col_invitados

    except PyMongoError as e:
        print(f"\n[ERROR] No se pudo leer la base de datos: {e}")
        client.close()
        sys.exit(1)


# ==========================================
# 1. LISTADO DE EVENTOS (filtro simple)
# ==========================================
def listar_eventos(db, col_eventos):
    print("\n=== LISTADO DE EVENTOS ===")
    try:
        eventos = db[col_eventos].find(
            {}, {"_id": 0, "codigo": 1, "nombre": 1, "fecha": 1, "lugar": 1, "categoria": 1}
        )
        cuenta = 0
        for ev in eventos:
            cuenta += 1
            print(f"\nCódigo:    {ev.get('codigo', 'N/A')}")
            print(f"Nombre:    {ev.get('nombre', 'N/A')}")
            print(f"Fecha:     {ev.get('fecha', 'N/A')}")
            print(f"Lugar:     {ev.get('lugar', 'N/A')}")
            print(f"Categoría: {ev.get('categoria', 'N/A')}")
            print("-" * 30)

        if cuenta == 0:
            print("No se encontraron eventos registrados en la base de datos.")
        else:
            print(f"\nTotal de eventos encontrados: {cuenta}")

    except PyMongoError as e:
        print(f"[ERROR] Ocurrió un problema al consultar los eventos: {e}")


# ==========================================
# 2. BÚSQUEDA DE INVITADOS POR NOMBRE (REGEX)
# ==========================================
def buscar_invitados_por_nombre(db, col_invitados):
    """Busca invitados cuyo nombre coincida total o parcialmente con el
    término ingresado (búsqueda insensible a mayúsculas/minúsculas)."""
    print("\n=== BUSCAR INVITADOS POR NOMBRE ===")
    termino = pedir_texto("Ingrese nombre completo o parcial a buscar: ")

    if not termino:
        print(
            "[AVISO] No ingresó ningún término de búsqueda. No se realizó la consulta.")
        return

    try:
        query = {"nombre": {"$regex": texto_regex_seguro(termino), "$options": "i"}}
        invitados = db[col_invitados].find(
            query, {"_id": 0, "nombre": 1,
                    "correo": 1, "estado": 1, "empresa": 1}
        )
        cuenta = 0
        for inv in invitados:
            cuenta += 1
            print(
                f"- {inv.get('nombre', 'N/A')} ({inv.get('correo', 'N/A')}) "
                f"| Empresa: {inv.get('empresa', 'N/A')} | Estado: {inv.get('estado', 'N/A')}"
            )

        if cuenta == 0:
            print(
                f"No se encontraron invitados cuyo nombre coincida con '{termino}'.")
        else:
            print(f"\nTotal de coincidencias: {cuenta}")

    except PyMongoError as e:
        print(f"[ERROR] Ocurrió un problema al buscar invitados: {e}")


# ==========================================
# 2b. BÚSQUEDA DE INVITADOS POR DOMINIO DE CORREO (REGEX)
# ==========================================
def buscar_invitados_por_dominio(db, col_invitados):
    """Busca invitados cuyo correo contenga el dominio ingresado, de forma
    total (ej: 'empresa.cl') o parcial (ej: 'cl'). La búsqueda se ancla
    después del '@' para no confundir el dominio con el nombre de usuario
    del correo."""
    print("\n=== BUSCAR INVITADOS POR DOMINIO DE CORREO ===")
    dominio = pedir_texto("Ingrese el dominio de correo, total o parcial (ej: empresa.cl): ")

    if not dominio:
        print("[AVISO] No ingresó ningún dominio. No se realizó la consulta.")
        return

    try:
        patron = f"@.*{texto_regex_seguro(dominio)}"
        query = {"correo": {"$regex": patron, "$options": "i"}}
        invitados = db[col_invitados].find(
            query, {"_id": 0, "nombre": 1,
                    "correo": 1, "estado": 1, "empresa": 1}
        )
        cuenta = 0
        for inv in invitados:
            cuenta += 1
            print(
                f"- {inv.get('nombre', 'N/A')} ({inv.get('correo', 'N/A')}) "
                f"| Empresa: {inv.get('empresa', 'N/A')} | Estado: {inv.get('estado', 'N/A')}"
            )

        if cuenta == 0:
            print(f"No se encontraron invitados con dominio de correo '{dominio}'.")
        else:
            print(f"\nTotal de coincidencias: {cuenta}")

    except PyMongoError as e:
        print(f"[ERROR] Ocurrió un problema al buscar por dominio de correo: {e}")


# ==========================================
# 3. VALIDACIÓN DE ACCESO A UN EVENTO
#    (correo + código de evento -> permitido / denegado)
# ==========================================
def validar_acceso_evento(db, col_eventos, col_invitados):
    print("\n=== VALIDACIÓN DE ACCESO A EVENTO ===")
    correo = pedir_texto(
        "Ingrese el correo del invitado (ej: ana.martinez@empresa.cl): ")
    codigo_evento = pedir_texto(
        "Ingrese el código del evento (ej: EVT-2025-001): ")

    if not correo or not codigo_evento:
        print(
            "[AVISO] Debe ingresar correo y código de evento. No se realizó la validación.")
        return

    try:
        pipeline = [
            {"$match": {"codigo": codigo_evento}},
            {"$unwind": "$invitados"},
            {
                "$lookup": {
                    "from": col_invitados,
                    "localField": "invitados.rut",
                    "foreignField": "rut",
                    "as": "datos_invitado",
                }
            },
            {"$unwind": "$datos_invitado"},
            {
                "$match": {
                    "datos_invitado.correo": {"$regex": f"^{texto_regex_seguro(correo)}$", "$options": "i"}
                }
            },
        ]

        resultado = list(db[col_eventos].aggregate(pipeline))

        if not resultado:
            print(
                f"\n[ACCESO DENEGADO] No existe el evento '{codigo_evento}', o el invitado")
            print(f"con correo '{correo}' no está registrado en dicho evento.")
            return

        invitado = resultado[0]
        estado_global = invitado["datos_invitado"].get("estado", "desconocido")
        estado_evento = invitado["invitados"].get("estado", "desconocido")
        nombre = invitado["datos_invitado"].get("nombre", "N/A")

        print(f"\nInvitado:          {nombre}")
        print(f"Estado de cuenta:  {estado_global}")
        print(f"Estado invitación: {estado_evento}")

        if estado_global != "activo":
            print("\n[ACCESO DENEGADO] El invitado se encuentra bloqueado.")
        elif estado_evento != "confirmado":
            print(
                f"\n[ACCESO DENEGADO] La invitación está '{estado_evento}', no confirmada.")
        else:
            print("\n[ACCESO PERMITIDO] El invitado puede ingresar al evento.")

    except PyMongoError as e:
        print(f"[ERROR] Ocurrió un problema al validar el acceso: {e}")


# ==========================================
# 4. CONSULTAS CRUZADAS (submenú)
# ==========================================
def consultas_cruzadas(db, col_eventos, col_invitados):
    print("\n=== CONSULTAS DE EVENTOS E INVITADOS ===")
    print("1. Mostrar eventos confirmados de un correo")
    print("2. Mostrar invitados confirmados de un evento")
    opcion = pedir_texto("Seleccione una opción (1-2): ")

    if opcion not in ("1", "2"):
        print(f"[AVISO] Opción '{opcion}' inválida. Debe ingresar 1 o 2.")
        return

    try:
        if opcion == "1":
            correo = pedir_texto("Ingrese el correo: ")
            if not correo:
                print("[AVISO] Debe ingresar un correo. No se realizó la consulta.")
                return

            pipeline = [
                {"$unwind": "$invitados"},
                {
                    "$lookup": {
                        "from": col_invitados,
                        "localField": "invitados.rut",
                        "foreignField": "rut",
                        "as": "datos_invitado",
                    }
                },
                {"$unwind": "$datos_invitado"},
                {
                    "$match": {
                        "datos_invitado.correo": {"$regex": f"^{texto_regex_seguro(correo)}$", "$options": "i"},
                        "invitados.estado": "confirmado",
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "codigo": 1,
                        "nombre": 1,
                        "fecha": 1,
                        "lugar": 1,
                        "categoria": 1,
                    }
                },
            ]

            resultados = list(db[col_eventos].aggregate(pipeline))

            if not resultados:
                print(
                    f"No existen eventos confirmados para el correo '{correo}'.")
                return

            print(f"\nEventos confirmados para {correo}:")
            for evento in resultados:
                print("-" * 40)
                print(f"Código:    {evento.get('codigo', 'N/A')}")
                print(f"Nombre:    {evento.get('nombre', 'N/A')}")
                print(f"Fecha:     {evento.get('fecha', 'N/A')}")
                print(f"Lugar:     {evento.get('lugar', 'N/A')}")
                print(f"Categoría: {evento.get('categoria', 'N/A')}")

        else:  # opcion == "2"
            codigo_evento = pedir_texto("Ingrese el código del evento: ")
            if not codigo_evento:
                print(
                    "[AVISO] Debe ingresar un código de evento. No se realizó la consulta.")
                return

            pipeline = [
                {"$match": {"codigo": codigo_evento}},
                {"$unwind": "$invitados"},
                {"$match": {"invitados.estado": "confirmado"}},
                {
                    "$lookup": {
                        "from": col_invitados,
                        "localField": "invitados.rut",
                        "foreignField": "rut",
                        "as": "datos_invitado",
                    }
                },
                {"$unwind": "$datos_invitado"},
                {
                    "$project": {
                        "_id": 0,
                        "rut": "$datos_invitado.rut",
                        "nombre": "$datos_invitado.nombre",
                        "correo": "$datos_invitado.correo",
                        "empresa": "$datos_invitado.empresa",
                    }
                },
            ]

            resultados = list(db[col_eventos].aggregate(pipeline))

            if not resultados:
                print(
                    f"No se encontraron invitados confirmados para el evento '{codigo_evento}'.")
                print("(Verifique que el código de evento exista.)")
                return

            print(f"\nInvitados confirmados para {codigo_evento}:")
            for invitado in resultados:
                print("-" * 40)
                print(f"Nombre:  {invitado.get('nombre', 'N/A')}")
                print(f"RUT:     {invitado.get('rut', 'N/A')}")
                print(f"Correo:  {invitado.get('correo', 'N/A')}")
                print(f"Empresa: {invitado.get('empresa', 'N/A')}")

    except PyMongoError as e:
        print(f"[ERROR] Ocurrió un problema al ejecutar la consulta: {e}")


# ==========================================
# 5. TOP 3 EVENTOS CON MÁS CONFIRMADOS
# ==========================================
def top_eventos_confirmados(db, col_eventos):
    print("\n=== TOP 3 EVENTOS CON MÁS CONFIRMADOS ===")
    try:
        pipeline = [
            {"$unwind": "$invitados"},
            {"$match": {"invitados.estado": "confirmado"}},
            {
                "$group": {
                    "_id": {"codigo": "$codigo", "nombre": "$nombre"},
                    "total_confirmados": {"$sum": 1},
                }
            },
            {"$sort": {"total_confirmados": -1}},
            {"$limit": 3},
        ]
        resultados = list(db[col_eventos].aggregate(pipeline))

        if not resultados:
            print("No hay eventos con asistentes confirmados.")
            return

        for idx, ev in enumerate(resultados, 1):
            info_evento = ev.get("_id", {})
            print(
                f"{idx}. Evento: {info_evento.get('nombre', 'N/A')} "
                f"(Cód: {info_evento.get('codigo', 'N/A')}) - "
                f"Confirmados: {ev.get('total_confirmados', 0)}"
            )

    except PyMongoError as e:
        print(
            f"[ERROR] Ocurrió un problema al calcular el top de eventos: {e}")


# ==========================================
# 6. CONSULTAR EVENTO POR NOMBRE -> INVITADOS Y EMPRESA
# ==========================================
def consultar_invitados_empresa_por_evento(db, col_eventos, col_invitados):
    print("\n=== INVITADOS Y EMPRESA POR NOMBRE DE EVENTO ===")
    nombre_evento = pedir_texto(
        "Ingrese el nombre (o parte del nombre) o el código del evento: ")

    if not nombre_evento:
        print(
            "[AVISO] Debe ingresar un nombre o código de evento. No se realizó la consulta.")
        return

    try:
        pipeline = [
            {"$match": {"$or": [
                {"nombre": {"$regex": texto_regex_seguro(nombre_evento), "$options": "i"}},
                {"codigo": {"$regex": texto_regex_seguro(nombre_evento), "$options": "i"}},
            ]}},
            {"$unwind": "$invitados"},
            {
                "$lookup": {
                    "from": col_invitados,
                    "localField": "invitados.rut",
                    "foreignField": "rut",
                    "as": "datos_invitado",
                }
            },
            {"$unwind": "$datos_invitado"},
            {
                "$project": {
                    "_id": 0,
                    "codigo": 1,
                    "nombre": 1,
                    "nombre_invitado": "$datos_invitado.nombre",
                    "empresa": "$datos_invitado.empresa",
                }
            },
        ]

        resultados = list(db[col_eventos].aggregate(pipeline))

        if not resultados:
            print(
                f"No se encontraron eventos que coincidan con nombre o código '{nombre_evento}'.")
            return

        evento_actual = None
        for r in resultados:
            if r.get("codigo") != evento_actual:
                evento_actual = r.get("codigo")
                print(f"\nEvento: {r.get('nombre', 'N/A')} (Cód: {evento_actual})")
                print("-" * 40)
            print(
                f"- {r.get('nombre_invitado', 'N/A')} | Empresa: {r.get('empresa', 'N/A')}"
            )

        print(f"\nTotal de invitados encontrados: {len(resultados)}")

    except PyMongoError as e:
        print(f"[ERROR] Ocurrió un problema al ejecutar la consulta: {e}")


# ==========================================
# 7. CONSULTAR EVENTO POR NOMBRE -> INVITADOS Y LUGAR
# ==========================================
def consultar_invitados_lugar_por_evento(db, col_eventos, col_invitados):
    print("\n=== INVITADOS Y LUGAR POR NOMBRE DE EVENTO ===")
    nombre_evento = pedir_texto(
        "Ingrese el nombre (o parte del nombre) o el código del evento: ")

    if not nombre_evento:
        print(
            "[AVISO] Debe ingresar un nombre o código de evento. No se realizó la consulta.")
        return

    try:
        pipeline = [
            {"$match": {"$or": [
                {"nombre": {"$regex": texto_regex_seguro(nombre_evento), "$options": "i"}},
                {"codigo": {"$regex": texto_regex_seguro(nombre_evento), "$options": "i"}},
            ]}},
            {"$unwind": "$invitados"},
            {
                "$lookup": {
                    "from": col_invitados,
                    "localField": "invitados.rut",
                    "foreignField": "rut",
                    "as": "datos_invitado",
                }
            },
            {"$unwind": "$datos_invitado"},
            {
                "$project": {
                    "_id": 0,
                    "codigo": 1,
                    "nombre": 1,
                    "lugar": 1,
                    "nombre_invitado": "$datos_invitado.nombre",
                }
            },
        ]

        resultados = list(db[col_eventos].aggregate(pipeline))

        if not resultados:
            print(
                f"No se encontraron eventos que coincidan con nombre o código '{nombre_evento}'.")
            return

        evento_actual = None
        for r in resultados:
            if r.get("codigo") != evento_actual:
                evento_actual = r.get("codigo")
                print(
                    f"\nEvento: {r.get('nombre', 'N/A')} (Cód: {evento_actual}) "
                    f"- Lugar: {r.get('lugar', 'N/A')}"
                )
                print("-" * 40)
            print(f"- {r.get('nombre_invitado', 'N/A')}")

        print(f"\nTotal de invitados encontrados: {len(resultados)}")

    except PyMongoError as e:
        print(f"[ERROR] Ocurrió un problema al ejecutar la consulta: {e}")


# ==========================================
# 8. CREAR EVENTO (CREATE)
# ==========================================
def crear_evento(db, col_eventos):
    """Crea un nuevo evento en la colección, solicitando sus datos
    principales. El evento se crea sin invitados asociados; estos se
    incorporan más adelante (por ejemplo, mediante cargar_datos.py o
    procesos de inscripción)."""
    print("\n=== CREAR NUEVO EVENTO ===")
    codigo = pedir_texto("Código del evento (ej: EVT-2025-010): ")
    if not codigo:
        print("[AVISO] Debe ingresar un código de evento. No se creó el evento.")
        return

    nombre = pedir_texto("Nombre del evento: ")
    fecha = pedir_texto("Fecha (formato ISO, ej: 2025-12-25T20:00:00Z): ")
    lugar = pedir_texto("Lugar: ")
    categoria = pedir_texto("Categoría: ")

    if not all([nombre, fecha, lugar, categoria]):
        print("[AVISO] Todos los campos son obligatorios. No se creó el evento.")
        return

    try:
        if db[col_eventos].find_one({"codigo": codigo}):
            print(f"\n[ERROR] Ya existe un evento con el código '{codigo}'. No se creó.")
            return

        nuevo_evento = {
            "codigo": codigo,
            "nombre": nombre,
            "fecha": fecha,
            "lugar": lugar,
            "categoria": categoria,
            "invitados": [],
        }
        resultado = db[col_eventos].insert_one(nuevo_evento)

        if resultado.acknowledged:
            print(f"\n[ÉXITO] Evento '{nombre}' (Cód: {codigo}) creado correctamente.")
        else:
            print("\n[ERROR] No se pudo confirmar la creación del evento.")

    except PyMongoError as e:
        print(f"[ERROR] Ocurrió un problema al crear el evento: {e}")


# ==========================================
# 9. MODIFICAR EVENTO (UPDATE)
#    - Un evento en particular, o todos sin distinción
# ==========================================
def modificar_evento(db, col_eventos):
    """Modifica un campo de un evento en particular, o el mismo campo
    para TODOS los eventos sin distinción (actualización masiva)."""
    print("\n=== MODIFICAR EVENTO ===")
    print("1. Modificar un evento en particular")
    print("2. Modificar el mismo campo para TODOS los eventos")
    alcance = pedir_texto("Seleccione el alcance (1-2): ")

    if alcance not in ("1", "2"):
        print(f"[AVISO] Opción '{alcance}' inválida. Debe ingresar 1 o 2.")
        return

    campos_validos = ("nombre", "fecha", "lugar", "categoria")
    campo = pedir_texto(f"Campo a modificar {campos_validos}: ").lower()

    if campo not in campos_validos:
        print(f"[AVISO] Campo '{campo}' no válido. Campos permitidos: {campos_validos}.")
        return

    nuevo_valor = pedir_texto(f"Nuevo valor para '{campo}': ")
    if not nuevo_valor:
        print("[AVISO] Debe ingresar un valor. No se realizó la modificación.")
        return

    try:
        if alcance == "1":
            codigo = pedir_texto("Código del evento a modificar: ")
            if not codigo:
                print("[AVISO] Debe ingresar un código de evento.")
                return

            resultado = db[col_eventos].update_one(
                {"codigo": codigo}, {"$set": {campo: nuevo_valor}}
            )
            if resultado.matched_count == 0:
                print(f"\n[ERROR] No se encontró ningún evento con código '{codigo}'.")
            elif resultado.modified_count > 0:
                print(f"\n[ÉXITO] Evento '{codigo}' actualizado: {campo} = '{nuevo_valor}'.")
            else:
                print(f"\n[AVISO] El evento ya tenía ese valor en '{campo}'. Sin cambios.")

        else:  # alcance == "2"
            confirmar = pedir_texto(
                f"¿Confirma actualizar '{campo}' a '{nuevo_valor}' en TODOS los eventos? (s/n): "
            ).lower()
            if confirmar != "s":
                print("[AVISO] Operación cancelada por el usuario.")
                return

            resultado = db[col_eventos].update_many({}, {"$set": {campo: nuevo_valor}})
            print(
                f"\n[ÉXITO] Se actualizaron {resultado.modified_count} de "
                f"{resultado.matched_count} eventos (campo '{campo}')."
            )

    except PyMongoError as e:
        print(f"[ERROR] Ocurrió un problema al modificar el evento: {e}")


# ==========================================
# 10. ELIMINAR EVENTO O CAMPO (DELETE)
# ==========================================
def eliminar_evento(db, col_eventos):
    """Elimina un campo específico de un evento (conservando el resto del
    documento), o elimina el evento completo de la colección. Por
    seguridad, solo se permite eliminar campos secundarios ('lugar' y
    'categoria'); 'codigo' y 'nombre' no son eliminables porque son
    identificadores del evento."""
    print("\n=== ELIMINAR EVENTO / CAMPO DE UN EVENTO ===")
    print("1. Eliminar un campo de un evento")
    print("2. Eliminar el evento completo")
    opcion = pedir_texto("Seleccione una opción (1-2): ")

    if opcion not in ("1", "2"):
        print(f"[AVISO] Opción '{opcion}' inválida. Debe ingresar 1 o 2.")
        return

    codigo = pedir_texto("Código del evento: ")
    if not codigo:
        print("[AVISO] Debe ingresar un código de evento.")
        return

    try:
        if opcion == "1":
            campos_eliminables = ("lugar", "categoria")
            campo = pedir_texto(f"Campo a eliminar {campos_eliminables}: ").lower()

            if campo not in campos_eliminables:
                print(
                    f"[AVISO] Campo '{campo}' no válido o no eliminable. "
                    f"Permitidos: {campos_eliminables}."
                )
                return

            resultado = db[col_eventos].update_one(
                {"codigo": codigo}, {"$unset": {campo: ""}}
            )
            if resultado.matched_count == 0:
                print(f"\n[ERROR] No se encontró ningún evento con código '{codigo}'.")
            else:
                print(f"\n[ÉXITO] Campo '{campo}' eliminado del evento '{codigo}'.")

        else:  # opcion == "2"
            confirmar = pedir_texto(
                f"¿Confirma eliminar el evento '{codigo}' por completo? Esta acción no se puede deshacer (s/n): "
            ).lower()
            if confirmar != "s":
                print("[AVISO] Operación cancelada por el usuario.")
                return

            resultado = db[col_eventos].delete_one({"codigo": codigo})
            if resultado.deleted_count == 0:
                print(f"\n[ERROR] No se encontró ningún evento con código '{codigo}'.")
            else:
                print(f"\n[ÉXITO] Evento '{codigo}' eliminado correctamente.")

    except PyMongoError as e:
        print(f"[ERROR] Ocurrió un problema al eliminar: {e}")


# ==========================================
# 11. MARCAR CHECK-IN DE UN INVITADO
# ==========================================
def marcar_checkin(db, col_eventos):
    """Marca el checkin de un invitado dentro de un evento como True,
    registrando su asistencia real. Este dato permite luego calcular
    estadísticas de asistencia efectiva (ver opción 'Ver asistentes')."""
    print("\n=== MARCAR CHECK-IN DE INVITADO ===")
    codigo_evento = pedir_texto("Código del evento: ")
    rut = pedir_texto("RUT del invitado (ej: 11.009.876-3): ")

    if not codigo_evento or not rut:
        print("[AVISO] Debe ingresar código de evento y RUT del invitado.")
        return

    try:
        resultado = db[col_eventos].update_one(
            {"codigo": codigo_evento, "invitados.rut": rut},
            {"$set": {"invitados.$.checkin": True}},
        )
        if resultado.matched_count == 0:
            print(
                f"\n[ERROR] No se encontró al invitado con RUT '{rut}' "
                f"en el evento '{codigo_evento}'."
            )
        elif resultado.modified_count > 0:
            print(
                f"\n[ÉXITO] Check-in registrado para el invitado '{rut}' "
                f"en el evento '{codigo_evento}'."
            )
        else:
            print("\n[AVISO] El invitado ya tenía el check-in registrado.")

    except PyMongoError as e:
        print(f"[ERROR] Ocurrió un problema al registrar el check-in: {e}")


# ==========================================
# 12. VER ASISTENTES (CHECK-IN) DE UN EVENTO
# ==========================================
def ver_asistentes_checkin(db, col_eventos):
    """Muestra el número y detalle de invitados con checkin=True para un
    evento, es decir, quienes efectivamente asistieron."""
    print("\n=== ASISTENTES (CHECK-IN) DE UN EVENTO ===")
    codigo_evento = pedir_texto("Código del evento: ")

    if not codigo_evento:
        print("[AVISO] Debe ingresar un código de evento.")
        return

    try:
        evento = db[col_eventos].find_one({"codigo": codigo_evento})
        if not evento:
            print(f"\n[ERROR] No se encontró ningún evento con código '{codigo_evento}'.")
            return

        asistentes = [i for i in evento.get("invitados", []) if i.get("checkin") is True]

        print(f"\nEvento: {evento.get('nombre', 'N/A')} (Cód: {codigo_evento})")
        if not asistentes:
            print("Aún no hay invitados con check-in registrado para este evento.")
            return

        for a in asistentes:
            print(f"- RUT: {a.get('rut', 'N/A')}")
        print(f"\nTotal de asistentes confirmados (checkin=True): {len(asistentes)}")

    except PyMongoError as e:
        print(f"[ERROR] Ocurrió un problema al consultar los asistentes: {e}")


# ==========================================
# MENÚ PRINCIPAL
# ==========================================
def menu():
    client, db, col_eventos, col_invitados = conectar_base_datos()
    try:
        while True:
            print("\n" + "=" * 45)
            print("      GESTOR DE EVENTOS E INVITADOS")
            print("=" * 45)
            print(" -- Consultas --")
            print("1. Listar todos los eventos")
            print("2. Buscar invitados por nombre")
            print("3. Buscar invitados por dominio de correo")
            print("4. Validar acceso a un evento")
            print("5. Consultas cruzadas")
            print("6. Ver Top 3 eventos con más confirmados")
            print("7. Buscar evento por nombre: invitados y empresa")
            print("8. Buscar evento por nombre: invitados y lugar")
            print(" -- Administración (CRUD) --")
            print("9. Crear evento")
            print("10. Modificar evento")
            print("11. Eliminar evento / campo de un evento")
            print("12. Marcar check-in de un invitado")
            print("13. Ver asistentes (check-in) de un evento")
            print("14. Salir")
            print("=" * 45)

            opcion = pedir_texto("Seleccione una opción (1-14): ")

            try:
                if opcion == "1":
                    listar_eventos(db, col_eventos)
                elif opcion == "2":
                    buscar_invitados_por_nombre(db, col_invitados)
                elif opcion == "3":
                    buscar_invitados_por_dominio(db, col_invitados)
                elif opcion == "4":
                    validar_acceso_evento(db, col_eventos, col_invitados)
                elif opcion == "5":
                    consultas_cruzadas(db, col_eventos, col_invitados)
                elif opcion == "6":
                    top_eventos_confirmados(db, col_eventos)
                elif opcion == "7":
                    consultar_invitados_empresa_por_evento(
                        db, col_eventos, col_invitados)
                elif opcion == "8":
                    consultar_invitados_lugar_por_evento(
                        db, col_eventos, col_invitados)
                elif opcion == "9":
                    crear_evento(db, col_eventos)
                elif opcion == "10":
                    modificar_evento(db, col_eventos)
                elif opcion == "11":
                    eliminar_evento(db, col_eventos)
                elif opcion == "12":
                    marcar_checkin(db, col_eventos)
                elif opcion == "13":
                    ver_asistentes_checkin(db, col_eventos)
                elif opcion == "14":
                    print("\nSaliendo del sistema...")
                    break
                else:
                    print(
                        f"\n[AVISO] Opción '{opcion}' inválida. Ingrese un número del 1 al 14.")
            except PyMongoError as e:
                # Cualquier error de MongoDB que no haya sido atrapado dentro
                # de la función específica no debe cerrar la aplicación.
                print(f"\n[ERROR DE BASE DE DATOS] {e}")
            except Exception as e:
                # Red de seguridad final: cualquier error inesperado se
                # informa y el programa sigue funcionando.
                print(f"\n[ERROR INESPERADO] {e}")

            if opcion != "7":
                waitput()

    except KeyboardInterrupt:
        print("\n\nCerrando el sistema (Ctrl+C detectado)...")
    finally:
        client.close()
        print("Conexión a MongoDB cerrada. ¡Hasta luego!")


if __name__ == "__main__":
    menu()
