"""
Módulo mejorado para crear listas de suscriptores con selección automática
Funcionalidades:
1. Selección automática de archivo Excel
2. Uso automático de la hoja "Datos"
3. Nombre de lista = nombre del archivo
4. Subida automática sin confirmación
5. Validación de diferencias entre hojas "Datos" y "Cambios"
"""

from .utils import data_path, notify, load_config
from .api import API
from .api.models.suscriptores import SubscriberData, FieldType
from .logger import get_logger
from .excel_helper import ExcelHelper
import pandas as pd
import os
import tkinter as tk
from tkinter import messagebox, filedialog
from typing import Optional, Dict, Any
from pathlib import Path
import shutil
import re

def extraer_id_desde_nombre_archivo(nombre_archivo: str) -> Optional[int]:
    """
    Extrae el ID de lista desde el nombre del archivo con formato -ID-[numero].xlsx

    Args:
        nombre_archivo: Nombre del archivo (ej: "MiLista-ID-12345.xlsx")

    Returns:
        ID de la lista como entero o None si no se encuentra
    """
    # Patrón para capturar -ID-[numero] antes de la extensión
    patron = r'-ID-(\d+)(?:_\d+)?\.xlsx?$'
    match = re.search(patron, nombre_archivo, re.IGNORECASE)

    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass

    return None

def tiene_formato_id_existente(archivo: str) -> bool:
    """
    Verifica si el archivo tiene formato de ID existente

    Args:
        archivo: Ruta completa del archivo

    Returns:
        True si tiene formato -ID-[numero].xlsx
    """
    nombre_archivo = os.path.basename(archivo)
    return extraer_id_desde_nombre_archivo(nombre_archivo) is not None

def verificar_lista_existe_remota(list_id: int, api: API) -> bool:
    """
    Verifica si una lista existe en el servidor remoto

    Args:
        list_id: ID de la lista a verificar
        api: Instancia de API

    Returns:
        True si la lista existe, False en caso contrario
    """
    logger = get_logger()

    try:
        # Obtener todas las listas y verificar si existe el ID
        listas = api.suscriptores.get_lists()

        for lista in listas:
            if lista.id == list_id:
                logger.info(f"Lista {list_id} '{lista.name}' existe en el servidor")
                return True

        logger.info(f"Lista {list_id} no existe en el servidor")
        return False

    except Exception as e:
        logger.warning(f"Error verificando lista {list_id}: {e}")
        # Si hay error, asumimos que no existe
        return False

def obtener_suscriptores_remotos(list_id: int, api: API) -> set:
    """
    Obtiene los emails de suscriptores de una lista remota

    Args:
        list_id: ID de la lista
        api: Instancia de API

    Returns:
        Set con los emails de los suscriptores remotos
    """
    logger = get_logger()

    try:
        # Obtener suscriptores de la lista - la función devuelve List[ActualSubscriber]
        subscribers = api.suscriptores.get_subscribers(list_id)

        emails_remotos = set()
        if subscribers:
            for subscriber in subscribers:
                if subscriber.email:
                    emails_remotos.add(subscriber.email.lower())

        logger.info(f"Lista {list_id}: {len(emails_remotos)} suscriptores remotos encontrados")
        return emails_remotos

    except Exception as e:
        logger.error(f"Error obteniendo suscriptores de lista {list_id}: {e}")
        return set()

def comparar_suscriptores_local_vs_remoto(df_local: pd.DataFrame, emails_remotos: set) -> Dict[str, Any]:
    """
    Compara suscriptores locales vs remotos para encontrar nuevos

    Args:
        df_local: DataFrame con suscriptores locales
        emails_remotos: Set con emails remotos

    Returns:
        Dict con información de la comparación
    """
    logger = get_logger()

    # Detectar columna de email automáticamente
    email_column = None
    possible_email_columns = ['email', 'Email', 'EMAIL', 'Correo Electrónico', 'Correo', 'correo', 'e-mail', 'E-mail']

    for col_name in possible_email_columns:
        if col_name in df_local.columns:
            email_column = col_name
            break

    if not email_column:
        print(f"⚠️ No se encontró columna de email. Columnas disponibles: {list(df_local.columns)}")
        return {
            'total_locales': 0,
            'total_remotos': len(emails_remotos),
            'emails_nuevos': set(),
            'cantidad_nuevos': 0,
            'df_nuevos': pd.DataFrame(),
            'tiene_nuevos': False,
            'error': f'No se encontró columna de email en: {list(df_local.columns)}'
        }

    print(f"📧 Usando columna de email: '{email_column}'")

    # Obtener emails locales
    emails_locales = set()
    emails_locales = set(df_local[email_column].dropna().astype(str).str.lower())

    # Encontrar emails nuevos (locales que no están en remotos)
    emails_nuevos = emails_locales - emails_remotos

    # Crear DataFrame solo con usuarios nuevos
    df_nuevos = pd.DataFrame()
    if emails_nuevos:
        # Filtrar DataFrame para incluir solo emails nuevos
        mask = df_local[email_column].astype(str).str.lower().isin(emails_nuevos)
        df_nuevos = df_local[mask].copy()

        # Renombrar columna de email a 'email' para compatibilidad con API
        if email_column != 'email':
            df_nuevos = df_nuevos.rename(columns={email_column: 'email'})

    resultado = {
        'total_locales': len(emails_locales),
        'total_remotos': len(emails_remotos),
        'emails_nuevos': emails_nuevos,
        'cantidad_nuevos': len(emails_nuevos),
        'df_nuevos': df_nuevos,
        'tiene_nuevos': len(emails_nuevos) > 0,
        'email_column_used': email_column
    }

    logger.info(f"Comparación: {resultado['total_locales']} locales, "
               f"{resultado['total_remotos']} remotos, "
               f"{resultado['cantidad_nuevos']} nuevos")

    return resultado

def procesar_archivo_con_id_existente(archivo: str, list_id: int, api: API) -> Optional[Dict[str, Any]]:
    """
    Procesa un archivo que ya tiene ID de lista en el nombre

    Args:
        archivo: Ruta del archivo Excel
        list_id: ID extraído del nombre del archivo
        api: Instancia de API

    Returns:
        Dict con resultado del procesamiento
    """
    print(f"🔍 Archivo con ID existente detectado: {list_id}")

    # Verificar si la lista existe
    if not verificar_lista_existe_remota(list_id, api):
        print(f"❌ Lista {list_id} no existe en el servidor")
        print("📝 Creando nueva lista...")

        # La lista no existe, procesar como archivo nuevo
        return crear_lista_automatica(archivo, validar_cambios=True)

    print(f"✅ Lista {list_id} existe en el servidor")

    # Leer datos locales con detección automática de hoja
    try:
        hojas = ExcelHelper.obtener_hojas(archivo)

        # Intentar encontrar hoja de datos (preferencia: Datos > Sheet1 > primera hoja)
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

    # Obtener suscriptores remotos
    print("🔍 Obteniendo suscriptores remotos...")
    emails_remotos = obtener_suscriptores_remotos(list_id, api)
    print(f"📊 Lista remota: {len(emails_remotos)} suscriptores")

    # Comparar local vs remoto
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

    # Crear campos personalizados para los nuevos datos
    crear_campos_personalizados(list_id, comparacion['df_nuevos'], api)

    # Agregar solo los suscriptores nuevos
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

        # Mostrar notificación
        notify("Lista actualizada", f"Se agregaron {suscriptores_agregados} nuevos suscriptores a la lista {list_id}")
    else:
        print("❌ Error en actualización incremental")

    return resultado

def seleccionar_archivo_excel(directorio_inicial: str = None) -> Optional[str]:
    """
    Abre diálogo para seleccionar archivo Excel
    """
    root = tk.Tk()
    root.withdraw()

    if not directorio_inicial:
        directorio_inicial = data_path("listas")

    archivo = filedialog.askopenfilename(
        title="Seleccionar archivo Excel",
        initialdir=directorio_inicial,
        filetypes=[
            ("Archivos Excel", "*.xlsx"),
            ("Archivos Excel antiguos", "*.xls"),
            ("Todos los archivos", "*.*")
        ]
    )

    root.destroy()
    return archivo if archivo else None

def validar_diferencias_hojas(archivo: str) -> Dict[str, Any]:
    """
    Valida diferencias entre hojas "Datos" y "Cambios"

    Returns:
        Dict con información de validación:
        - tiene_datos: bool
        - tiene_cambios: bool
        - emails_solo_datos: Set[str]
        - emails_solo_cambios: Set[str]
        - es_problematico: bool
        - mensaje: str
    """
    logger = get_logger()
    resultado = {
        'tiene_datos': False,
        'tiene_cambios': False,
        'emails_solo_datos': set(),
        'emails_solo_cambios': set(),
        'es_problematico': False,
        'mensaje': ''
    }

    try:
        hojas = ExcelHelper.obtener_hojas(archivo)

        # Verificar si tiene hojas "Datos" y "Cambios"
        resultado['tiene_datos'] = 'Datos' in hojas
        resultado['tiene_cambios'] = 'Cambios' in hojas

        if not resultado['tiene_datos']:
            resultado['mensaje'] = "❌ No se encontró la hoja 'Datos'"
            resultado['es_problematico'] = True
            return resultado

        if not resultado['tiene_cambios']:
            resultado['mensaje'] = "✅ Solo tiene hoja 'Datos' - Procesamiento normal"
            return resultado

        # Leer ambas hojas
        df_datos = ExcelHelper.leer_excel(archivo, 'Datos')
        df_cambios = ExcelHelper.leer_excel(archivo, 'Cambios')

        # Verificar que tengan columna email
        if 'email' not in df_datos.columns:
            resultado['mensaje'] = "❌ Hoja 'Datos' no tiene columna 'email'"
            resultado['es_problematico'] = True
            return resultado

        if 'email' not in df_cambios.columns:
            resultado['mensaje'] = "⚠️  Hoja 'Cambios' no tiene columna 'email'"
            return resultado

        # Obtener sets de emails
        emails_datos = set(df_datos['email'].dropna().astype(str))
        emails_cambios = set(df_cambios['email'].dropna().astype(str))

        resultado['emails_solo_datos'] = emails_datos - emails_cambios
        resultado['emails_solo_cambios'] = emails_cambios - emails_datos

        # Evaluar si es problemático
        if len(resultado['emails_solo_cambios']) > 0:
            resultado['es_problematico'] = True
            resultado['mensaje'] = (
                f"🚨 PROBLEMA: La hoja 'Cambios' tiene {len(resultado['emails_solo_cambios'])} "
                f"emails que NO están en 'Datos'. Esto puede indicar inconsistencia."
            )
        else:
            resultado['mensaje'] = (
                f"✅ Validación OK: 'Cambios' es un subconjunto de 'Datos' "
                f"({len(emails_cambios)} de {len(emails_datos)} emails)"
            )

        logger.info(f"Validación hojas: Datos={len(emails_datos)}, Cambios={len(emails_cambios)}, "
                   f"Solo en Datos={len(resultado['emails_solo_datos'])}, "
                   f"Solo en Cambios={len(resultado['emails_solo_cambios'])}")

    except Exception as e:
        logger.error(f"Error validando hojas: {e}")
        resultado['mensaje'] = f"❌ Error validando hojas: {e}"
        resultado['es_problematico'] = True

    return resultado

def obtener_nombre_lista_desde_archivo(archivo: str) -> str:
    """
    Obtiene el nombre de la lista basado en el nombre del archivo
    """
    nombre_base = Path(archivo).stem  # Sin extensión

    # Limpiar caracteres especiales que puedan causar problemas
    caracteres_permitidos = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_. "
    nombre_limpio = "".join(c for c in nombre_base if c in caracteres_permitidos)

    # Truncar si es muy largo (límite de API)
    if len(nombre_limpio) > 50:
        nombre_limpio = nombre_limpio[:47] + "..."

    return nombre_limpio.strip()

def renombrar_archivo_con_id(archivo_original: str, nombre_lista: str, list_id: int) -> bool:
    """
    Renombra el archivo original con el formato [Nombre de lista]-ID-[ID_LISTA].xlsx

    Args:
        archivo_original: Ruta del archivo original
        nombre_lista: Nombre de la lista creada
        list_id: ID de la lista asignado por la API

    Returns:
        bool: True si se renombró exitosamente
    """
    logger = get_logger()

    try:
        archivo_path = Path(archivo_original)
        directorio = archivo_path.parent
        extension = archivo_path.suffix

        # Crear nuevo nombre con formato solicitado
        nuevo_nombre = f"{nombre_lista}-ID-{list_id}{extension}"
        nueva_ruta = directorio / nuevo_nombre

        # Verificar si el archivo destino ya existe
        if nueva_ruta.exists():
            print(f"⚠️  El archivo ya existe: {nuevo_nombre}")
            # Agregar sufijo para evitar sobrescribir
            contador = 1
            while nueva_ruta.exists():
                nuevo_nombre = f"{nombre_lista}-ID-{list_id}_{contador}{extension}"
                nueva_ruta = directorio / nuevo_nombre
                contador += 1
            print(f"📝 Usando nombre alternativo: {nuevo_nombre}")

        # Renombrar archivo
        shutil.move(str(archivo_path), str(nueva_ruta))

        print("✅ Archivo renombrado:")
        print(f"   Anterior: {archivo_path.name}")
        print(f"   Nuevo: {nuevo_nombre}")

        logger.info(f"Archivo renombrado: {archivo_path.name} -> {nuevo_nombre}")
        return True

    except Exception as e:
        logger.error(f"Error renombrando archivo: {e}")
        print(f"❌ Error renombrando archivo: {e}")
        return False

def crear_lista_automatica_interna(archivo: str, api: API, validar_cambios: bool = True) -> Optional[Dict[str, Any]]:
    """
    Versión interna de crear_lista_automatica que acepta una instancia de API existente
    """
    if not os.path.exists(archivo):
        print(f"❌ Archivo no encontrado: {archivo}")
        return None

    # Obtener nombre de lista desde archivo
    nombre_lista = obtener_nombre_lista_desde_archivo(archivo)
    print(f"📝 Nombre de lista: '{nombre_lista}'")

    # Validar hojas si está habilitado
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

    # Verificar que existe hoja "Datos"
    hojas = ExcelHelper.obtener_hojas(archivo)
    if 'Datos' not in hojas:
        print(f"❌ No se encontró la hoja 'Datos' en el archivo. Hojas disponibles: {hojas}")
        return None

    # Cargar configuración
    config_lista = cargar_configuracion_lista()

    # Procesar solo la hoja "Datos"
    resultado = procesar_hoja_excel(archivo, 'Datos', config_lista, api, nombre_lista)

    if resultado and resultado['exitoso']:
        print(f"🎉 Lista '{nombre_lista}' creada exitosamente!")
        print(f"   📊 ID: {resultado['list_id']}")
        print(f"   👥 Suscriptores: {resultado['suscriptores_agregados']}/{resultado['total_filas']}")

        # Renombrar archivo con el ID de la lista
        print("📁 Renombrando archivo...")
        renombrar_exitoso = renombrar_archivo_con_id(archivo, nombre_lista, resultado['list_id'])
        resultado['archivo_renombrado'] = renombrar_exitoso

        # Mostrar notificación
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

    # Obtener nombre de lista desde archivo
    nombre_lista = obtener_nombre_lista_desde_archivo(archivo)
    print(f"📝 Nombre de lista: '{nombre_lista}'")

    # Validar hojas si está habilitado
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

    # Verificar que existe hoja "Datos"
    hojas = ExcelHelper.obtener_hojas(archivo)
    if 'Datos' not in hojas:
        print(f"❌ No se encontró la hoja 'Datos' en el archivo. Hojas disponibles: {hojas}")
        return None

    # Cargar configuración
    config_lista = cargar_configuracion_lista()

    # Crear API
    try:
        api = API()
    except Exception as e:
        print(f"❌ Error inicializando API: {e}")
        return None

    try:
        # Procesar solo la hoja "Datos"
        resultado = procesar_hoja_excel(archivo, 'Datos', config_lista, api, nombre_lista)

        if resultado and resultado['exitoso']:
            print(f"🎉 Lista '{nombre_lista}' creada exitosamente!")
            print(f"   📊 ID: {resultado['list_id']}")
            print(f"   👥 Suscriptores: {resultado['suscriptores_agregados']}/{resultado['total_filas']}")

            # Renombrar archivo con el ID de la lista
            print("📁 Renombrando archivo...")
            renombrar_exitoso = renombrar_archivo_con_id(archivo, nombre_lista, resultado['list_id'])
            resultado['archivo_renombrado'] = renombrar_exitoso

            # Mostrar notificación
            notify("Lista creada", f"Lista '{nombre_lista}' creada con {resultado['suscriptores_agregados']} suscriptores")
        else:
            print(f"❌ Error creando lista '{nombre_lista}'")

        return resultado

    finally:
        api.close()

def procesar_hoja_excel(archivo: str, nombre_hoja: str, config_lista: Dict[str, str],
                       api: API, nombre_lista_custom: str = None) -> Optional[Dict[str, Any]]:
    """
    Procesa una hoja de Excel: crea lista y agrega suscriptores

    Args:
        archivo: Ruta del archivo Excel
        nombre_hoja: Nombre de la hoja a procesar
        config_lista: Configuración de la lista
        api: Instancia de API reutilizable
        nombre_lista_custom: Nombre personalizado para la lista (si no se proporciona, usa nombre_hoja)

    Returns:
        Dict con resultado del procesamiento o None si error
    """
    logger = get_logger()

    try:
        # Leer hoja de Excel
        df = ExcelHelper.leer_excel(archivo, nombre_hoja)

        if df.empty:
            logger.warning(f"Hoja '{nombre_hoja}' está vacía")
            return None

        # Usar nombre personalizado o nombre de hoja
        nombre_lista = nombre_lista_custom or nombre_hoja

        print(f"📄 Procesando hoja '{nombre_hoja}' con {len(df)} filas -> Lista '{nombre_lista}'")

        # Crear lista
        list_id = crear_lista_via_api(nombre_lista, config_lista, api)
        if not list_id:
            return None

        # Crear campos personalizados automáticamente
        print("🔧 Paso 1: Creando campos personalizados...")
        crear_campos_personalizados(list_id, df, api)

        # Agregar suscriptores
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

def crear_campos_personalizados(list_id: int, df_suscriptores: pd.DataFrame, api: API) -> bool:
    """
    Crea campos personalizados en la lista basándose en las columnas del DataFrame

    Args:
        list_id: ID de la lista
        df_suscriptores: DataFrame con los datos de suscriptores
        api: Instancia de API

    Returns:
        bool: True si se crearon exitosamente
    """
    logger = get_logger()

    try:
        # Obtener columnas que no sean 'email'
        campos_personalizados = [col for col in df_suscriptores.columns if col != 'email']

        if not campos_personalizados:
            logger.info("No hay campos personalizados para crear")
            return True

        print(f"🔧 Creando {len(campos_personalizados)} campos personalizados...")

        campos_creados = 0
        campos_fallidos = 0

        for campo in campos_personalizados:
            try:
                # Normalizar nombre del campo
                campo_normalizado = campo.replace(' ', '_').replace('-', '_')

                # Crear campo usando la API
                api.suscriptores.add_merge_tag(
                    list_id=list_id,
                    field_name=campo_normalizado,
                    field_type=FieldType.TEXT
                )

                campos_creados += 1
                print(f"   ✅ {campo} -> {campo_normalizado}")
                logger.info(f"Campo '{campo_normalizado}' creado exitosamente")

            except Exception as e:
                campos_fallidos += 1
                print(f"   ❌ {campo}: {e}")
                logger.warning(f"Error creando campo '{campo}': {e}")

        print(f"📊 Resultado: {campos_creados} exitosos, {campos_fallidos} fallidos")
        return campos_creados > 0

    except Exception as e:
        logger.error(f"Error general creando campos personalizados: {e}")
        print(f"❌ Error creando campos personalizados: {e}")
        return False

def crear_lista_via_api(nombre_lista: str, config_lista: Dict[str, str], api: API) -> Optional[int]:
    """
    Crea una lista usando la API de suscriptores
    """
    logger = get_logger()

    try:
        list_id = api.suscriptores.create_list(
            sender_email=config_lista.get('sender_email', 'admin@example.com'),
            name=nombre_lista,
            company=config_lista.get('company', 'Mi Empresa'),
            country=config_lista.get('country', 'España'),
            city=config_lista.get('city', 'Madrid'),
            address=config_lista.get('address', 'Calle Principal 123'),
            phone=config_lista.get('phone', '+34 900 000 000')
        )

        logger.info(f"Lista creada exitosamente: {nombre_lista} (ID: {list_id})")
        return list_id

    except Exception as e:
        logger.error(f"Error creando lista {nombre_lista}: {e}")
        print(f"Error creando lista {nombre_lista}: {e}")
        return None

def verificar_y_mostrar_campos(list_id: int, df_suscriptores: pd.DataFrame, api: API) -> bool:
    """
    Verifica los campos de la lista después de agregar suscriptores
    """
    logger = get_logger()

    try:
        print(f"🔍 Verificando campos de la lista {list_id}...")

        # Obtener campos existentes en la lista
        campos_respuesta = api.suscriptores.get_merge_fields(list_id)

        if hasattr(campos_respuesta, 'merge_fields') and campos_respuesta.merge_fields:
            campos_existentes = list(campos_respuesta.merge_fields.keys())
            print(f"📋 Campos existentes en la lista: {campos_existentes}")

            # Verificar si faltan campos (considerar normalización)
            campos_esperados = [col.replace(' ', '_').replace('-', '_') for col in df_suscriptores.columns if col != 'email']
            campos_faltantes = [c for c in campos_esperados if c not in campos_existentes]

            if campos_faltantes:
                print(f"⚠️  Campos faltantes en la lista: {campos_faltantes}")
                print("💡 Esto puede indicar que los campos no se enviaron correctamente")
            else:
                print(f"✅ Todos los campos esperados están presentes: {campos_esperados}")

        else:
            print(f"⚠️  No se encontraron merge fields en la lista {list_id}")

        return True

    except Exception as e:
        logger.warning(f"Error verificando campos de lista {list_id}: {e}")
        print(f"⚠️  No se pudieron verificar los campos de la lista: {e}")
        return False

def agregar_suscriptores_via_api(list_id: int, df_suscriptores: pd.DataFrame, api: API) -> int:
    """
    Agrega suscriptores a una lista usando la API con procesamiento en lotes
    Primero define los campos personalizados, luego agrega los suscriptores
    """
    logger = get_logger()
    suscriptores_agregados = 0

    if df_suscriptores.empty:
        logger.warning("DataFrame de suscriptores está vacío")
        return 0

    # Verificar que tenga columna email
    tiene_email, faltantes = ExcelHelper.verificar_columnas(df_suscriptores, ['email'])
    if not tiene_email:
        logger.error(f"Columna 'email' requerida no encontrada. Columnas disponibles: {list(df_suscriptores.columns)}")
        return 0

    try:
        # PASO 1: Agregar suscriptores (la API debería crear campos automáticamente)
        print("👥 Agregando suscriptores con campos personalizados...")

        # Preparar datos para procesamiento en lotes
        subscribers_batch = []
        batch_size = 100  # Procesar en lotes de 100

        for _, fila in df_suscriptores.iterrows():
            # Preparar campos del suscriptor
            merge_fields = {}

            for columna, valor in fila.items():
                if pd.notna(valor) and str(valor).strip():  # Solo valores no vacíos
                    # Normalizar nombre de campo (sin espacios, formato Acumbamail)
                    campo_normalizado = columna.replace(' ', '_').replace('-', '_')
                    merge_fields[campo_normalizado] = str(valor).strip()

            # Verificar que tenga email
            if 'email' not in merge_fields or not merge_fields['email']:
                logger.warning(f"Fila sin email válido: {fila.to_dict()}")
                continue

            # Crear SubscriberData tipado
            try:
                # Debug: mostrar datos que se van a enviar
                if len(subscribers_batch) == 0:  # Solo mostrar para el primer suscriptor
                    print("📤 Datos del primer suscriptor:")
                    for k, v in merge_fields.items():
                        print(f"   {k}: '{v}'")

                subscriber_data = SubscriberData(
                    email=merge_fields['email'],
                    **{k: v for k, v in merge_fields.items() if k != 'email'}
                )

                # Debug: verificar el objeto creado
                if len(subscribers_batch) == 0:
                    subscriber_dict = subscriber_data.model_dump()
                    print("📦 SubscriberData creado:")
                    for k, v in subscriber_dict.items():
                        if v is not None:
                            print(f"   {k}: '{v}'")

                subscribers_batch.append(subscriber_data)

                # Procesar lote cuando alcance el tamaño
                if len(subscribers_batch) >= batch_size:
                    result = api.suscriptores.batch_add_subscribers(
                        list_id=list_id,
                        subscribers_data=subscribers_batch,
                        update_subscriber=1,  # Actualizar si existe
                        complete_json=1
                    )
                    suscriptores_agregados += result.success_count
                    logger.info(f"Lote procesado: {result.success_count} exitosos, {result.error_count} errores")
                    subscribers_batch.clear()

            except Exception as e:
                logger.warning(f"Error preparando suscriptor {merge_fields.get('email', 'sin email')}: {e}")
                continue

        # Procesar último lote si queda alguno
        if subscribers_batch:
            result = api.suscriptores.batch_add_subscribers(
                list_id=list_id,
                subscribers_data=subscribers_batch,
                update_subscriber=1,  # Actualizar si existe
                complete_json=1
            )
            suscriptores_agregados += result.success_count
            logger.info(f"Último lote procesado: {result.success_count} exitosos, {result.error_count} errores")

        logger.info(f"Agregados {suscriptores_agregados} suscriptores a lista {list_id}")

        # PASO 2: Verificar campos después de agregar suscriptores
        if suscriptores_agregados > 0:
            print("🔍 Verificando campos de la lista...")
            verificar_y_mostrar_campos(list_id, df_suscriptores, api)

    except Exception as e:
        logger.error(f"Error en proceso de agregar suscriptores: {e}")

    return suscriptores_agregados

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

def main_automatico():
    """
    Función principal para procesar lista automáticamente
    1. Pide seleccionar archivo Excel
    2. Detecta si tiene ID existente en el nombre
    3. Si tiene ID: verifica lista remota y actualiza incrementalmente
    4. Si no tiene ID: crea nueva lista
    """
    print("🚀 Iniciando procesamiento automático de lista de suscriptores")

    # Seleccionar archivo
    archivo = seleccionar_archivo_excel()
    if not archivo:
        print("❌ No se seleccionó archivo")
        return

    nombre_archivo = os.path.basename(archivo)
    print(f"📁 Archivo seleccionado: {nombre_archivo}")

    # Crear API
    try:
        api = API()
    except Exception as e:
        print(f"❌ Error inicializando API: {e}")
        return

    try:
        # Verificar si el archivo tiene formato de ID existente
        if tiene_formato_id_existente(archivo):
            list_id = extraer_id_desde_nombre_archivo(nombre_archivo)
            if list_id is not None:
                print(f"🔍 Archivo con ID detectado: {list_id}")
                # Procesar archivo con ID existente
                resultado = procesar_archivo_con_id_existente(archivo, list_id, api)
            else:
                print("❌ Error extrayendo ID del nombre del archivo")
                resultado = None
        else:
            print("📝 Archivo sin ID detectado - creando nueva lista")

            # Procesar como archivo nuevo (reutilizar la función existente pero sin crear nueva API)
            resultado = crear_lista_automatica_interna(archivo, api, validar_cambios=True)

        # Mostrar resultado
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

    # Buscar archivos Excel
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

    # Procesar cada archivo
    exitosos = 0
    fallidos = 0

    # Crear API una vez para todos los archivos
    try:
        api = API()
    except Exception as e:
        print(f"❌ Error inicializando API: {e}")
        return

    try:
        for i, archivo in enumerate(archivos_excel, 1):
            nombre_archivo = os.path.basename(archivo)
            print(f"\n🔄 Procesando {i}/{len(archivos_excel)}: {nombre_archivo}")

            # Detectar si tiene ID existente
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

    # Resumen
    print("\n📊 Resumen del procesamiento en lote:")
    print(f"   ✅ Exitosos: {exitosos}")
    print(f"   ❌ Fallidos: {fallidos}")
    print(f"   📊 Total: {len(archivos_excel)}")

if __name__ == "__main__":
    # Por defecto ejecuta modo automático individual
    main_automatico()