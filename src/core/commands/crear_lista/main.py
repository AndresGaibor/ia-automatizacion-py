"""Puntos de entrada: main_automatico y main_lote."""

import os

from ....utils import data_path
from ....infrastructure.api import API
from ....shared.logging.logger import get_logger
from .file_utils import extraer_id_desde_nombre_archivo, tiene_formato_id_existente
from .remote_ops import verificar_lista_existe_remota, obtener_suscriptores_remotos, comparar_suscriptores_local_vs_remoto
from .sheet_validation import seleccionar_archivo_excel
from .list_creation import crear_lista_automatica, crear_lista_automatica_interna
from .subscriber_ops import crear_campos_personalizados, agregar_suscriptores_via_api


def procesar_archivo_con_id_existente(archivo: str, list_id: int, api: API):
    """
    Procesa un archivo que ya tiene ID de lista en el nombre
    """
    from ....utils import notify
    from ....infrastructure.excel import ExcelHelper

    print(f"🔍 Archivo con ID existente detectado: {list_id}")

    if not verificar_lista_existe_remota(list_id, api):
        print(f"❌ Lista {list_id} no existe en el servidor")
        print("📝 Creando nueva lista...")
        return crear_lista_automatica(archivo, validar_cambios=True)

    print(f"✅ Lista {list_id} existe en el servidor")

    try:
        hojas = ExcelHelper.obtener_hojas(archivo)

        hoja_datos = None
        if 'Datos' in hojas:
            hoja_datos = 'Datos'
        elif 'Sheet1' in hojas:
            hoja_datos = 'Sheet1'
        elif len(hojas) > 0:
            hoja_datos = hojas[0]
        else:
            print("❌ No se encontraron hojas en el archivo")
            return None

        print(f"📄 Usando hoja: '{hoja_datos}'")
        df_local = ExcelHelper.leer_excel(archivo, hoja_datos)
        if df_local.empty:
            print(f"❌ La hoja '{hoja_datos}' está vacía")
            return None

        print(f"📊 Archivo local: {len(df_local)} suscriptores")
        print(f"📋 Columnas disponibles: {list(df_local.columns)}")

    except Exception as e:
        print(f"❌ Error leyendo archivo local: {e}")
        return None

    print("🔍 Obteniendo suscriptores remotos...")
    emails_remotos = obtener_suscriptores_remotos(list_id, api)
    print(f"📊 Lista remota: {len(emails_remotos)} suscriptores")

    comparacion = comparar_suscriptores_local_vs_remoto(df_local, emails_remotos)

    if not comparacion['tiene_nuevos']:
        print("✅ No hay suscriptores nuevos que agregar")
        print("🎯 Lista ya está actualizada")

        return {
            'nombre_lista': os.path.splitext(os.path.basename(archivo))[0],
            'list_id': list_id,
            'total_filas': comparacion['total_locales'],
            'suscriptores_agregados': 0,
            'exitoso': True,
            'ya_actualizada': True
        }

    print(f"🆕 Encontrados {comparacion['cantidad_nuevos']} suscriptores nuevos")
    print("📤 Agregando solo los nuevos suscriptores...")

    crear_campos_personalizados(list_id, comparacion['df_nuevos'], api)
    suscriptores_agregados = agregar_suscriptores_via_api(list_id, comparacion['df_nuevos'], api)

    resultado = {
        'nombre_lista': os.path.splitext(os.path.basename(archivo))[0],
        'list_id': list_id,
        'total_filas': comparacion['total_locales'],
        'suscriptores_agregados': suscriptores_agregados,
        'exitoso': suscriptores_agregados > 0,
        'actualizacion_incremental': True,
        'total_remotos_previo': comparacion['total_remotos'],
        'nuevos_agregados': comparacion['cantidad_nuevos']
    }

    if resultado['exitoso']:
        print("✅ Actualización incremental exitosa:")
        print(f"   📊 Total en archivo: {resultado['total_filas']}")
        print(f"   📊 Remotos previos: {resultado['total_remotos_previo']}")
        print(f"   🆕 Nuevos agregados: {resultado['suscriptores_agregados']}")

        notify("Lista actualizada", f"Se agregaron {suscriptores_agregados} nuevos suscriptores a la lista {list_id}")
    else:
        print("❌ Error en actualización incremental")

    return resultado


def main_automatico():
    """
    Función principal para procesar lista automáticamente
    1. Pide seleccionar archivo Excel
    2. Detecta si tiene ID existente en el nombre
    3. Si tiene ID: verifica lista remota y actualiza incrementalmente
    4. Si no tiene ID: crea nueva lista
    """
    print("🚀 Iniciando procesamiento automático de lista de suscriptores")

    archivo = seleccionar_archivo_excel()
    if not archivo:
        print("❌ No se seleccionó archivo")
        return

    nombre_archivo = os.path.basename(archivo)
    print(f"📁 Archivo seleccionado: {nombre_archivo}")

    try:
        api = API()
    except Exception as e:
        print(f"❌ Error inicializando API: {e}")
        return

    try:
        if tiene_formato_id_existente(archivo):
            list_id = extraer_id_desde_nombre_archivo(nombre_archivo)
            if list_id is not None:
                print(f"🔍 Archivo con ID detectado: {list_id}")
                resultado = procesar_archivo_con_id_existente(archivo, list_id, api)
            else:
                print("❌ Error extrayendo ID del nombre del archivo")
                resultado = None
        else:
            print("📝 Archivo sin ID detectado - creando nueva lista")
            resultado = crear_lista_automatica_interna(archivo, api, validar_cambios=True)

        if resultado:
            if resultado.get('ya_actualizada'):
                print("✅ Lista ya estaba actualizada - no se requieren cambios")
            elif resultado.get('actualizacion_incremental'):
                print("✅ Actualización incremental completada exitosamente")
            else:
                print("✅ Nueva lista creada exitosamente")
        else:
            print("❌ Proceso falló")

    finally:
        api.close()


def main_lote():
    """
    Procesa múltiples archivos en el directorio data/listas/
    """
    print("🚀 Iniciando procesamiento en lote")

    directorio_listas = data_path("listas")
    if not os.path.exists(directorio_listas):
        print(f"❌ Directorio no encontrado: {directorio_listas}")
        return

    archivos_excel = []
    for archivo in os.listdir(directorio_listas):
        if archivo.endswith('.xlsx') and not archivo.startswith('~$'):
            archivos_excel.append(os.path.join(directorio_listas, archivo))

    if not archivos_excel:
        print(f"❌ No se encontraron archivos Excel en {directorio_listas}")
        return

    print(f"📋 Se procesarán {len(archivos_excel)} archivos:")
    for i, archivo in enumerate(archivos_excel, 1):
        print(f"  {i}. {os.path.basename(archivo)}")

    exitosos = 0
    fallidos = 0

    try:
        api = API()
    except Exception as e:
        print(f"❌ Error inicializando API: {e}")
        return

    try:
        for i, archivo in enumerate(archivos_excel, 1):
            nombre_archivo = os.path.basename(archivo)
            print(f"\n🔄 Procesando {i}/{len(archivos_excel)}: {nombre_archivo}")

            if tiene_formato_id_existente(archivo):
                list_id = extraer_id_desde_nombre_archivo(nombre_archivo)
                if list_id is not None:
                    print(f"   🔍 Archivo con ID detectado: {list_id}")
                    resultado = procesar_archivo_con_id_existente(archivo, list_id, api)
                else:
                    print("   ❌ Error extrayendo ID del nombre del archivo")
                    resultado = None
            else:
                print("   📝 Archivo sin ID - creando nueva lista")
                resultado = crear_lista_automatica_interna(archivo, api, validar_cambios=True)

            if resultado and resultado['exitoso']:
                exitosos += 1

                if resultado.get('ya_actualizada'):
                    print("   ✅ Lista ya estaba actualizada")
                elif resultado.get('actualizacion_incremental'):
                    print("   ✅ Actualización incremental exitosa")
                elif resultado.get('archivo_renombrado'):
                    print("   ✅ Nueva lista creada y archivo renombrado")
                else:
                    print("   ✅ Proceso exitoso")
            else:
                fallidos += 1

    finally:
        api.close()

    print("\n📊 Resumen del procesamiento en lote:")
    print(f"   ✅ Exitosos: {exitosos}")
    print(f"   ❌ Fallidos: {fallidos}")
    print(f"   📊 Total: {len(archivos_excel)}")
