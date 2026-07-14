"""Creación de listas: lógica principal de creación y procesamiento de hojas."""

import os
from typing import Optional, Dict, Any

from tkinter import messagebox

from ....utils import load_config, notify
from ....infrastructure.api import API
from ....infrastructure.excel import ExcelHelper
from ....shared.logging.logger import get_logger
from .file_utils import obtener_nombre_lista_desde_archivo, renombrar_archivo_con_id
from .sheet_validation import validar_diferencias_hojas
from .subscriber_ops import crear_lista_via_api, crear_campos_personalizados, agregar_suscriptores_via_api


def cargar_configuracion_lista() -> Dict[str, str]:
    """
    Carga la configuración de la lista desde config.yaml o valores por defecto
    """
    config = load_config()
    lista_config = config.get('lista', {}) if config else {}

    return {
        'sender_email': lista_config.get('sender_email', 'admin@example.com'),
        'company': lista_config.get('company', 'Mi Empresa'),
        'country': lista_config.get('country', 'España'),
        'city': lista_config.get('city', 'Madrid'),
        'address': lista_config.get('address', 'Calle Principal 123'),
        'phone': lista_config.get('phone', '+34 900 000 000')
    }


def procesar_hoja_excel(archivo: str, nombre_hoja: str, config_lista: Dict[str, str],
                       api: API, nombre_lista_custom: str = None) -> Optional[Dict[str, Any]]:
    """
    Procesa una hoja de Excel: crea lista y agrega suscriptores

    Args:
        archivo: Ruta del archivo Excel
        nombre_hoja: Nombre de la hoja a procesar
        config_lista: Configuración de la lista
        api: Instancia de API reutilizable
        nombre_lista_custom: Nombre personalizado para la lista

    Returns:
        Dict con resultado del procesamiento o None si error
    """
    logger = get_logger()

    try:
        df = ExcelHelper.leer_excel(archivo, nombre_hoja)

        if df.empty:
            logger.warning(f"Hoja '{nombre_hoja}' está vacía")
            return None

        nombre_lista = nombre_lista_custom or nombre_hoja

        print(f"📄 Procesando hoja '{nombre_hoja}' con {len(df)} filas -> Lista '{nombre_lista}'")

        list_id = crear_lista_via_api(nombre_lista, config_lista, api)
        if not list_id:
            return None

        print("🔧 Paso 1: Creando campos personalizados...")
        crear_campos_personalizados(list_id, df, api)

        print("👥 Paso 2: Agregando suscriptores...")
        suscriptores_agregados = agregar_suscriptores_via_api(list_id, df, api)

        resultado = {
            'nombre_lista': nombre_lista,
            'list_id': list_id,
            'total_filas': len(df),
            'suscriptores_agregados': suscriptores_agregados,
            'exitoso': suscriptores_agregados > 0
        }

        return resultado

    except Exception as e:
        logger.error(f"Error procesando hoja {nombre_hoja}: {e}")
        print(f"❌ Error procesando hoja {nombre_hoja}: {e}")
        return None


def crear_lista_automatica_interna(archivo: str, api: API, validar_cambios: bool = True) -> Optional[Dict[str, Any]]:
    """
    Versión interna de crear_lista_automatica que acepta una instancia de API existente
    """
    if not os.path.exists(archivo):
        print(f"❌ Archivo no encontrado: {archivo}")
        return None

    nombre_lista = obtener_nombre_lista_desde_archivo(archivo)
    print(f"📝 Nombre de lista: '{nombre_lista}'")

    if validar_cambios:
        validacion = validar_diferencias_hojas(archivo)
        print(f"🔍 {validacion['mensaje']}")

        if validacion['es_problematico']:
            respuesta = messagebox.askyesno(
                "Problema detectado",
                f"{validacion['mensaje']}\n\n¿Desea continuar de todas formas?",
                icon="warning"
            )
            if not respuesta:
                print("❌ Proceso cancelado por el usuario")
                return None

    hojas = ExcelHelper.obtener_hojas(archivo)
    if 'Datos' not in hojas:
        print(f"❌ No se encontró la hoja 'Datos' en el archivo. Hojas disponibles: {hojas}")
        return None

    config_lista = cargar_configuracion_lista()

    resultado = procesar_hoja_excel(archivo, 'Datos', config_lista, api, nombre_lista)

    if resultado and resultado['exitoso']:
        print(f"🎉 Lista '{nombre_lista}' creada exitosamente!")
        print(f"   📊 ID: {resultado['list_id']}")
        print(f"   👥 Suscriptores: {resultado['suscriptores_agregados']}/{resultado['total_filas']}")

        print("📁 Renombrando archivo...")
        renombrar_exitoso = renombrar_archivo_con_id(archivo, nombre_lista, resultado['list_id'])
        resultado['archivo_renombrado'] = renombrar_exitoso

        notify("Lista creada", f"Lista '{nombre_lista}' creada con {resultado['suscriptores_agregados']} suscriptores")
    else:
        print(f"❌ Error creando lista '{nombre_lista}'")

    return resultado


def crear_lista_automatica(archivo: str, validar_cambios: bool = True) -> Optional[Dict[str, Any]]:
    """
    Crea lista automáticamente:
    1. Usa nombre del archivo como nombre de lista
    2. Procesa solo la hoja "Datos"
    3. Valida inconsistencias con "Cambios" si existe
    4. Renombra el archivo con el ID de la lista creada

    Args:
        archivo: Ruta del archivo Excel
        validar_cambios: Si validar diferencias con hoja "Cambios"

    Returns:
        Dict con resultado del procesamiento
    """
    if not os.path.exists(archivo):
        print(f"❌ Archivo no encontrado: {archivo}")
        return None

    nombre_lista = obtener_nombre_lista_desde_archivo(archivo)
    print(f"📝 Nombre de lista: '{nombre_lista}'")

    if validar_cambios:
        validacion = validar_diferencias_hojas(archivo)
        print(f"🔍 {validacion['mensaje']}")

        if validacion['es_problematico']:
            respuesta = messagebox.askyesno(
                "Problema detectado",
                f"{validacion['mensaje']}\n\n¿Desea continuar de todas formas?",
                icon="warning"
            )
            if not respuesta:
                print("❌ Proceso cancelado por el usuario")
                return None

    hojas = ExcelHelper.obtener_hojas(archivo)
    if 'Datos' not in hojas:
        print(f"❌ No se encontró la hoja 'Datos' en el archivo. Hojas disponibles: {hojas}")
        return None

    config_lista = cargar_configuracion_lista()

    try:
        api = API()
    except Exception as e:
        print(f"❌ Error inicializando API: {e}")
        return None

    try:
        resultado = procesar_hoja_excel(archivo, 'Datos', config_lista, api, nombre_lista)

        if resultado and resultado['exitoso']:
            print(f"🎉 Lista '{nombre_lista}' creada exitosamente!")
            print(f"   📊 ID: {resultado['list_id']}")
            print(f"   👥 Suscriptores: {resultado['suscriptores_agregados']}/{resultado['total_filas']}")

            print("📁 Renombrando archivo...")
            renombrar_exitoso = renombrar_archivo_con_id(archivo, nombre_lista, resultado['list_id'])
            resultado['archivo_renombrado'] = renombrar_exitoso

            notify("Lista creada", f"Lista '{nombre_lista}' creada con {resultado['suscriptores_agregados']} suscriptores")
        else:
            print(f"❌ Error creando lista '{nombre_lista}'")

        return resultado

    finally:
        api.close()
