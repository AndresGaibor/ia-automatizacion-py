"""
Módulo para mapear segmentos de Excel a archivos de listas individuales.
Procesa el archivo Segmentos.xlsx y aplica las condiciones a los archivos de listas correspondientes.
"""
import pandas as pd
from collections import defaultdict
import os
import time
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
# from playwright.sync_api import TimeoutError as PlaywrightTimeoutError  # no longer used

from .utils import data_path, load_config, notify
from .logger import get_logger
from .excel_helper import ExcelHelper
from .api import API
from .crear_lista_mejorado import extraer_id_desde_nombre_archivo
from .scrapping.endpoints import SegmentsScrapingService

logger = get_logger()

# Rutas de archivos
ARCHIVO_SEGMENTOS = data_path("Segmentos.xlsx")
CARPETA_LISTAS = data_path("listas")

def obtener_id_lista_desde_archivo(nombre_lista: str) -> Optional[int]:
    """
    Obtiene el ID de una lista buscando archivos con formato -ID-[numero].xlsx en /data/listas/

    Args:
        nombre_lista: Nombre de la lista a buscar

    Returns:
        ID de la lista si se encuentra, None si no existe o no tiene ID
    """
    if not os.path.exists(CARPETA_LISTAS):
        return None

    # Buscar archivos que coincidan con el nombre de la lista
    for archivo in os.listdir(CARPETA_LISTAS):
        if archivo.endswith('.xlsx'):
            # Verificar si el archivo corresponde a esta lista
            archivo_sin_extension = os.path.splitext(archivo)[0]

            # Buscar patrón: nombre-ID-[numero]
            if archivo_sin_extension.startswith(nombre_lista + '-ID-'):
                list_id = extraer_id_desde_nombre_archivo(archivo)
                if list_id is not None:
                    logger.info(f"ID encontrado para lista '{nombre_lista}': {list_id}")
                    return list_id

            # También buscar archivos que coincidan exactamente con el nombre (sin ID)
            elif archivo_sin_extension == nombre_lista:
                logger.info(f"Archivo encontrado para lista '{nombre_lista}' pero sin ID")
                return None

    logger.info(f"No se encontró archivo para lista '{nombre_lista}'")
    return None

def asegurar_nombre_archivo_con_id(nombre_lista: str, list_id: int) -> str:
    """
    Asegura que el archivo local de la lista use el formato
    "[Nombre Lista]-ID-[ID de Lista].xlsx". Si existe un archivo sin ID,
    se renombra al formato con ID.

    Args:
        nombre_lista: Nombre de la lista
        list_id: ID de la lista

    Returns:
        Ruta absoluta del archivo con el nombre correcto (con ID)
    """
    os.makedirs(CARPETA_LISTAS, exist_ok=True)

    nombre_con_id = f"{nombre_lista}-ID-{list_id}.xlsx"
    ruta_con_id = os.path.join(CARPETA_LISTAS, nombre_con_id)

    nombre_sin_id = f"{nombre_lista}.xlsx"
    ruta_sin_id = os.path.join(CARPETA_LISTAS, nombre_sin_id)

    try:
        if os.path.exists(ruta_con_id):
            # Ya existe el archivo con ID; opcionalmente advertir si hay duplicado sin ID
            if os.path.exists(ruta_sin_id):
                logger.warning(
                    f"Existe también archivo sin ID para '{nombre_lista}'. Usando '{ruta_con_id}'."
                )
            return ruta_con_id

        # Si existe el archivo sin ID, renombrar
        if os.path.exists(ruta_sin_id):
            os.rename(ruta_sin_id, ruta_con_id)
            logger.info(f"Archivo renombrado: '{ruta_sin_id}' → '{ruta_con_id}'")
            print(f"🔤 Archivo renombrado a: {nombre_con_id}")
            return ruta_con_id

        # Si no existe ninguno, devolver ruta esperada con ID (se creará luego)
        return ruta_con_id
    except Exception as e:
        logger.error(f"Error asegurando nombre de archivo con ID para '{nombre_lista}': {e}")
        # Fallback al nombre sin ID para no bloquear el proceso
        return ruta_sin_id

def actualizar_id_en_segmentos(nombre_lista: str, list_id: int) -> bool:
    """
    Actualiza el ID de una lista en el archivo Segmentos.xlsx

    Args:
        nombre_lista: Nombre de la lista
        list_id: ID de la lista a asignar

    Returns:
        True si se actualizó exitosamente
    """
    logger.info(f"Actualizando ID {list_id} para lista '{nombre_lista}' en Segmentos.xlsx")

    try:
        if not os.path.exists(ARCHIVO_SEGMENTOS):
            logger.warning(f"Archivo Segmentos.xlsx no existe: {ARCHIVO_SEGMENTOS}")
            return False

        # Leer archivo de segmentos
        df = pd.read_excel(ARCHIVO_SEGMENTOS)

        # Eliminar columna "CREACION SEGMENTO" si existe
        if 'CREACION SEGMENTO' in df.columns:
            df = df.drop(columns=['CREACION SEGMENTO'])
            logger.info("Columna 'CREACION SEGMENTO' eliminada de Segmentos.xlsx (actualización de ID)")

        # Asegurar que existe la columna ID Lista
        if 'ID Lista' not in df.columns:
            df.insert(0, 'ID Lista', None)
            logger.info("Columna 'ID Lista' agregada al archivo Segmentos.xlsx")

        # Actualizar filas que coincidan con el nombre de la lista
        mask = df['NOMBRE LISTA'] == nombre_lista
        filas_actualizadas = mask.sum()

        if filas_actualizadas > 0:
            df.loc[mask, 'ID Lista'] = list_id

            # Guardar archivo actualizado
            df.to_excel(ARCHIVO_SEGMENTOS, index=False)
            logger.info(f"Actualizado ID {list_id} en {filas_actualizadas} filas para lista '{nombre_lista}'")
            print(f"✅ ID {list_id} actualizado en Segmentos.xlsx para lista '{nombre_lista}' ({filas_actualizadas} filas)")
            return True
        else:
            logger.warning(f"No se encontraron filas para la lista '{nombre_lista}' en Segmentos.xlsx")
            return False

    except Exception as e:
        logger.error(f"Error actualizando ID en Segmentos.xlsx: {e}")
        print(f"❌ Error actualizando ID en Segmentos.xlsx: {e}")
        return False

def obtener_id_desde_segmentos(nombre_lista: str) -> Optional[int]:
    """
    Obtiene el ID de una lista desde el archivo Segmentos.xlsx

    Args:
        nombre_lista: Nombre de la lista

    Returns:
        ID de la lista si existe en Segmentos.xlsx, None si no existe
    """
    try:
        if not os.path.exists(ARCHIVO_SEGMENTOS):
            return None

        df = pd.read_excel(ARCHIVO_SEGMENTOS)

        if 'ID Lista' not in df.columns:
            return None

        # Buscar la primera fila que coincida con el nombre de la lista
        mask = df['NOMBRE LISTA'] == nombre_lista
        if mask.any():
            id_valor = df.loc[mask, 'ID Lista'].iloc[0]
            if pd.notna(id_valor):
                return int(id_valor)

        return None

    except Exception as e:
        logger.error(f"Error leyendo ID desde Segmentos.xlsx: {e}")
        return None

def obtener_o_buscar_id_lista(nombre_lista: str) -> Optional[int]:
    """
    Obtiene el ID de una lista siguiendo esta prioridad:
    1. Desde Segmentos.xlsx (si ya está registrado)
    2. Desde archivos en /data/listas/ (si existe archivo con ID)
    3. None si no se encuentra

    Args:
        nombre_lista: Nombre de la lista

    Returns:
        ID de la lista o None si no se encuentra
    """
    # 1. Primero buscar en Segmentos.xlsx
    id_segmentos = obtener_id_desde_segmentos(nombre_lista)
    if id_segmentos is not None:
        logger.info(f"ID {id_segmentos} encontrado en Segmentos.xlsx para lista '{nombre_lista}'")
        return id_segmentos

    # 2. Buscar en archivos de listas
    id_archivo = obtener_id_lista_desde_archivo(nombre_lista)
    if id_archivo is not None:
        # Si lo encontramos en archivo pero no en Segmentos.xlsx, actualizar
        logger.info(f"ID {id_archivo} encontrado en archivo, actualizando Segmentos.xlsx")
        actualizar_id_en_segmentos(nombre_lista, id_archivo)
        return id_archivo

    logger.info(f"No se encontró ID para lista '{nombre_lista}'")
    return None

def mostrar_estado_listas_segmentos() -> None:
    """
    Muestra el estado actual de las listas en Segmentos.xlsx y sus IDs
    """
    print("📊 Estado actual de listas en Segmentos.xlsx:")
    print("-" * 50)

    try:
        if not os.path.exists(ARCHIVO_SEGMENTOS):
            print("❌ Archivo Segmentos.xlsx no existe")
            return

        df = pd.read_excel(ARCHIVO_SEGMENTOS)

        if df.empty:
            print("📝 Archivo Segmentos.xlsx está vacío")
            return

        # Obtener listas únicas
        if 'NOMBRE LISTA' not in df.columns:
            print("❌ Columna 'NOMBRE LISTA' no encontrada")
            return

        listas_unicas = df['NOMBRE LISTA'].dropna().unique()

        for nombre_lista in listas_unicas:
            # Obtener ID de la lista
            list_id = obtener_o_buscar_id_lista(nombre_lista)

            # Contar segmentos para esta lista
            segmentos_count = len(df[df['NOMBRE LISTA'] == nombre_lista])

            # Status
            if list_id:
                status = f"✅ ID: {list_id}"
            else:
                status = "❌ Sin ID"

            print(f"  {nombre_lista:<30} {status:<15} ({segmentos_count} segmentos)")

    except Exception as e:
        print(f"❌ Error mostrando estado: {e}")

    print("-" * 50)

def generar_datos_prueba_segmentos() -> pd.DataFrame:
    """
    Genera datos de prueba para el archivo Segmentos.xlsx
    
    Returns:
        DataFrame con datos de ejemplo
    """
    datos_ejemplo = [
        {
            'ID Lista': None,
            'NOMBRE LISTA': 'Lista_Ejemplo_Madrid',
            'NOMBRE SEGMENTO': 'Juzgados_Madrid_Civil',
            'SEDE': 'Madrid',
            'ORGANO': 'Juzgado Civil',
            'N ORGANO': '1',
            'ROL USUARIO': 'Secretario',
            'PERFIL USUARIO': 'Administrativo'
        },
        {
            'ID Lista': None,
            'NOMBRE LISTA': 'Lista_Ejemplo_Madrid',
            'NOMBRE SEGMENTO': 'Juzgados_Madrid_Penal',
            'SEDE': 'Madrid',
            'ORGANO': 'Juzgado Penal',
            'N ORGANO': '2',
            'ROL USUARIO': 'Juez',
            'PERFIL USUARIO': 'Judicial'
        },
        {
            'ID Lista': None,
            'NOMBRE LISTA': 'Lista_Ejemplo_Barcelona',
            'NOMBRE SEGMENTO': 'Juzgados_Barcelona_Civil',
            'SEDE': 'Barcelona',
            'ORGANO': 'Juzgado Civil',
            'N ORGANO': '1',
            'ROL USUARIO': 'Secretario',
            'PERFIL USUARIO': 'Administrativo'
        },
        {
            'ID Lista': None,
            'NOMBRE LISTA': 'Lista_Ejemplo_Valencia',
            'NOMBRE SEGMENTO': 'Juzgados_Valencia_Mercantil',
            'SEDE': 'Valencia',
            'ORGANO': 'Juzgado Mercantil',
            'N ORGANO': '1',
            'ROL USUARIO': 'Letrado',
            'PERFIL USUARIO': 'Legal'
        }
    ]
    
    return pd.DataFrame(datos_ejemplo)

def inicializar_archivo_segmentos() -> bool:
    """
    Inicializa el archivo Segmentos.xlsx con la estructura correcta si no existe.
    Si no existe, crea uno con datos de prueba.

    Returns:
        True si se inicializó o ya existía
    """
    try:
        if os.path.exists(ARCHIVO_SEGMENTOS):
            # Verificar que tenga la columna ID Lista y eliminar columna de creación de segmento si está
            df = pd.read_excel(ARCHIVO_SEGMENTOS)

            if 'CREACION SEGMENTO' in df.columns:
                df = df.drop(columns=['CREACION SEGMENTO'])
                logger.info("Columna 'CREACION SEGMENTO' eliminada de Segmentos.xlsx")
                notify("Actualización", "Columna 'CREACION SEGMENTO' eliminada del archivo Segmentos.xlsx", "info")

            if 'ID Lista' not in df.columns:
                # Agregar columna ID Lista al principio
                df.insert(0, 'ID Lista', None)
                logger.info("Columna 'ID Lista' agregada al archivo Segmentos.xlsx existente")
                notify("Actualización", "Columna 'ID Lista' agregada al archivo Segmentos.xlsx", "info")

            # Guardar ajustes si hubo cambios
            df.to_excel(ARCHIVO_SEGMENTOS, index=False)
            
            # Validar que el archivo tenga datos
            if len(df) == 0:
                logger.warning("Archivo Segmentos.xlsx existe pero está vacío")
                # Agregar datos de prueba si está vacío
                datos_prueba = generar_datos_prueba_segmentos()
                df = pd.concat([df, datos_prueba], ignore_index=True)
                df.to_excel(ARCHIVO_SEGMENTOS, index=False)
                notify("Datos de Prueba", "Archivo Segmentos.xlsx estaba vacío. Se agregaron datos de ejemplo.", "info")
            
            return True
        else:
            # Crear archivo con estructura básica y datos de prueba
            datos_prueba = generar_datos_prueba_segmentos()

            os.makedirs(os.path.dirname(ARCHIVO_SEGMENTOS), exist_ok=True)
            datos_prueba.to_excel(ARCHIVO_SEGMENTOS, index=False)
            logger.info(f"Archivo Segmentos.xlsx creado con datos de prueba en: {ARCHIVO_SEGMENTOS}")
            notify("Archivo Creado", f"Archivo Segmentos.xlsx creado con datos de ejemplo en: {ARCHIVO_SEGMENTOS}", "info")
            return True

    except Exception as e:
        logger.error(f"Error inicializando archivo Segmentos.xlsx: {e}")
        notify("Error", f"Error inicializando archivo Segmentos.xlsx: {e}", "error")
        return False

def procesar_excel_segmentos(archivo_excel: str) -> Tuple[List[str], List[List[Any]]]:
    """
    Procesa un archivo Excel y agrupa los datos por NOMBRE LISTA,
    eliminando duplicados en las condiciones.

    Args:
        archivo_excel (str): Ruta al archivo Excel

    Returns:
        tuple: (headers, grouped_data)
    """
    logger.info(f"Procesando archivo de segmentos: {archivo_excel}")

    # Leer el archivo Excel
    df = pd.read_excel(archivo_excel)

    # Eliminar columna "CREACION SEGMENTO" si existe
    if 'CREACION SEGMENTO' in df.columns:
        df = df.drop(columns=['CREACION SEGMENTO'])
        logger.info("Columna 'CREACION SEGMENTO' ignorada al procesar segmentos")

    if df.empty:
        logger.warning("Archivo de segmentos está vacío")
        return [], []

    # Definir las cabeceras que queremos (excluyendo campos de control)
    headers = ['NOMBRE SEGMENTO', 'SEDE', 'ORGANO', 'N ORGANO', 'ROL USUARIO', 'PERFIL USUARIO']

    # Verificar que las columnas necesarias existen
    columnas_requeridas = ['NOMBRE LISTA', 'NOMBRE SEGMENTO']
    tiene_columnas, faltantes = ExcelHelper.verificar_columnas(df, columnas_requeridas)

    if not tiene_columnas:
        logger.error(f"Columnas requeridas faltantes: {faltantes}")
        return [], []

    # Diccionario para agrupar por NOMBRE LISTA
    grouped_data = defaultdict(set)

    # Función helper para limpiar valores NaN
    def get_clean_value(row, col):
        """Obtiene valor limpio, convirtiendo NaN a None"""
        val = row.get(col)
        return None if pd.isna(val) else val

    # Procesar cada fila
    for _, row in df.iterrows():
        nombre_lista = row['NOMBRE LISTA']

        if pd.isna(nombre_lista):
            continue

        # Crear tupla con los valores que nos interesan, convirtiendo NaN a None
        valores = (
            get_clean_value(row, 'NOMBRE SEGMENTO'),
            get_clean_value(row, 'SEDE'),
            get_clean_value(row, 'ORGANO'),
            get_clean_value(row, 'N ORGANO'),
            get_clean_value(row, 'ROL USUARIO'),
            get_clean_value(row, 'PERFIL USUARIO')
        )

        # Añadir al set (automáticamente elimina duplicados)
        grouped_data[nombre_lista].add(valores)

    # Convertir sets a listas para el formato final
    resultado_final = []
    for nombre_lista, valores_set in grouped_data.items():
        valores_lista = [list(tupla) for tupla in valores_set]
        resultado_final.append([nombre_lista, valores_lista])

    logger.info(f"Procesadas {len(resultado_final)} listas con segmentos")
    return headers, resultado_final

def obtener_ruta_archivo_lista(nombre_lista: str) -> str:
    """
    Obtiene la ruta del archivo para una lista específica.

    Args:
        nombre_lista: Nombre de la lista

    Returns:
        Ruta del archivo de la lista
    """
    # Crear carpeta listas si no existe
    os.makedirs(CARPETA_LISTAS, exist_ok=True)

    # Normalizar nombre del archivo
    nombre_archivo = f"{nombre_lista}.xlsx"
    return os.path.join(CARPETA_LISTAS, nombre_archivo)

def verificar_columnas_compatibles(df: pd.DataFrame, headers: List[str]) -> Tuple[bool, List[str]]:
    """
    Verifica que el archivo de lista tenga columnas compatibles para aplicar segmentos.

    Args:
        df: DataFrame de la lista
        headers: Headers requeridos para segmentación

    Returns:
        (es_compatible, columnas_disponibles)
    """
    # Verificar que existe email (obligatorio)
    if 'email' not in df.columns and 'Email' not in df.columns and 'EMAIL' not in df.columns:
        return False, []

    # Verificar qué columnas de segmentación están disponibles
    columnas_disponibles = []
    for header in headers[1:]:  # Excluir NOMBRE SEGMENTO
        if header in df.columns:
            columnas_disponibles.append(header)

    # Necesita al menos una columna para poder segmentar
    es_compatible = len(columnas_disponibles) > 0

    return es_compatible, columnas_disponibles

def aplicar_condiciones_segmento(df: pd.DataFrame, condiciones: List[Any], headers: List[str]) -> pd.Series:
    """
    Aplica condiciones de segmento usando lógica AND.

    Args:
        df: DataFrame de la lista
        condiciones: Lista de valores de condición [nombre_segmento, sede, organo, n_organo, rol, perfil]
        headers: Lista de nombres de columnas correspondientes

    Returns:
        Serie booleana indicando qué filas cumplen las condiciones
    """
    if len(condiciones) != len(headers):
        logger.warning(f"Longitud de condiciones ({len(condiciones)}) no coincide con headers ({len(headers)})")
        return pd.Series([False] * len(df))

    # Empezar con todas las filas como True
    mask = pd.Series([True] * len(df))
    condiciones_aplicadas = 0

    # Filtrar condiciones válidas para logging
    condiciones_limpias = []
    for i, (valor, columna) in enumerate(zip(condiciones, headers)):
        if i == 0:  # NOMBRE SEGMENTO siempre se incluye
            condiciones_limpias.append(f"{columna}: '{valor}'")
        elif not (pd.isna(valor) or valor == '' or valor is None or str(valor).lower() == 'nan'):
            condiciones_limpias.append(f"{columna}: '{valor}'")
        else:
            condiciones_limpias.append(f"{columna}: [IGNORADO - NaN/vacío]")

    logger.info(f"Aplicando condiciones para segmento '{condiciones[0]}':")
    for condicion in condiciones_limpias:
        logger.info(f"  - {condicion}")
    logger.info(f"Columnas disponibles en DataFrame: {list(df.columns)}")

    # Aplicar cada condición con AND
    for i, (valor, columna) in enumerate(zip(condiciones[1:], headers[1:]), 1):  # Saltar NOMBRE SEGMENTO
        if columna not in df.columns:
            logger.warning(f"Columna '{columna}' no existe en DataFrame")
            continue

        # Ignorar valores None, vacíos, NaN o string 'nan'
        if pd.isna(valor) or valor == '' or valor is None or str(valor).lower() == 'nan':
            logger.info(f"Saltando condición para '{columna}': valor vacío/nulo (valor: {repr(valor)})")
            continue

        # Mostrar valores únicos en la columna para debugging
        valores_unicos = df[columna].dropna().unique()[:10]  # Primeros 10 valores
        logger.info(f"Valores únicos en '{columna}': {valores_unicos}")

        # Aplicar condición
        if isinstance(valor, (int, float)) and not pd.isna(valor):
            # Para números, comparación exacta considerando tipos mixtos
            # Convertir a número tanto el valor como la columna para comparar
            try:
                valor_num = float(valor)
                condicion = (pd.to_numeric(df[columna], errors='coerce') == valor_num)
                logger.info(f"Aplicando condición numérica: {columna} == {valor_num}")
            except (ValueError, TypeError):
                # Si no se puede convertir a número, usar comparación de string
                condicion = (df[columna].astype(str) == str(valor))
                logger.info(f"Aplicando condición texto (fallback): {columna} == '{valor}'")
        else:
            # Para texto, comparación de string
            condicion = (df[columna].astype(str) == str(valor))
            logger.info(f"Aplicando condición texto: {columna} == '{valor}'")

        coincidencias_antes = mask.sum()
        mask &= condicion
        coincidencias_despues = mask.sum()
        condiciones_aplicadas += 1

        logger.info(f"Condición '{columna}' == '{valor}': {coincidencias_antes} → {coincidencias_despues} filas")

    filas_coincidentes = mask.sum()
    logger.info(f"Total condiciones aplicadas: {condiciones_aplicadas}, filas finales coincidentes: {filas_coincidentes}")

    return mask

def actualizar_columna_segmentos(df: pd.DataFrame, mask: pd.Series, nombre_segmento: str) -> Tuple[pd.DataFrame, List[int]]:
    """
    Actualiza la columna Segmentos para las filas que coinciden.

    Args:
        df: DataFrame a actualizar
        mask: Máscara booleana de filas a actualizar
        nombre_segmento: Nombre del segmento a asignar

    Returns:
        (DataFrame actualizado, índices de filas modificadas)
    """
    # Agregar columna Segmentos si no existe
    df = ExcelHelper.agregar_columna_si_no_existe(df, 'Segmentos', '')

    filas_modificadas = []

    for idx in df[mask].index:
        valor_actual = str(df.loc[idx, 'Segmentos']).strip()

        if valor_actual == '' or pd.isna(valor_actual):
            # Primera asignación
            df.loc[idx, 'Segmentos'] = nombre_segmento
            filas_modificadas.append(idx)
        else:
            # Verificar si ya tiene este segmento
            segmentos_existentes = valor_actual.split(';')
            if nombre_segmento not in segmentos_existentes:
                # Concatenar nuevo segmento
                df.loc[idx, 'Segmentos'] = f"{valor_actual};{nombre_segmento}"
                filas_modificadas.append(idx)

    logger.info(f"Actualizadas {len(filas_modificadas)} filas con segmento '{nombre_segmento}'")
    return df, filas_modificadas

def detectar_cambios_segmentos(df_original: pd.DataFrame, df_nuevo: pd.DataFrame) -> pd.DataFrame:
    """
    Detecta usuarios que cambiaron de segmento.

    Args:
        df_original: DataFrame antes de aplicar cambios
        df_nuevo: DataFrame después de aplicar cambios

    Returns:
        DataFrame con los usuarios que cambiaron
    """
    if df_original.empty or df_nuevo.empty:
        return pd.DataFrame()

    # Asegurar que ambos DataFrames tienen columna Segmentos
    if 'Segmentos' not in df_original.columns:
        df_original = df_original.copy()
        df_original['Segmentos'] = ''

    if 'Segmentos' not in df_nuevo.columns:
        df_nuevo = df_nuevo.copy()
        df_nuevo['Segmentos'] = ''

    # Verificar que tienen los mismos índices
    if len(df_original) != len(df_nuevo):
        logger.warning("DataFrames tienen diferentes longitudes para comparar cambios")
        return pd.DataFrame()

    # Comparar columnas de segmentos
    try:
        cambios = df_original['Segmentos'].fillna('') != df_nuevo['Segmentos'].fillna('')

        if cambios.any():
            df_cambios = df_nuevo[cambios].copy()
            df_cambios['Segmentos_Anterior'] = df_original.loc[cambios, 'Segmentos'].fillna('')
            df_cambios['Fecha_Cambio'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')

            logger.info(f"Detectados {len(df_cambios)} usuarios con cambios de segmento")
            return df_cambios
    except Exception as e:
        logger.error(f"Error detectando cambios de segmentos: {e}")
        return pd.DataFrame()

    return pd.DataFrame()

def obtener_id_lista_por_nombre(nombre_lista: str, api_client: API) -> Optional[int]:
    """
    Busca el ID de una lista por su nombre usando la API.

    Args:
        nombre_lista: Nombre de la lista a buscar
        api_client: Cliente de la API

    Returns:
        ID de la lista o None si no se encuentra
    """
    try:
        listas = api_client.suscriptores.get_lists()

        for lista in listas:
            if lista.name == nombre_lista:
                return lista.id

        logger.warning(f"Lista '{nombre_lista}' no encontrada en Acumbamail")
        return None

    except Exception as e:
        logger.error(f"Error buscando lista '{nombre_lista}': {e}")
        return None

def verificar_y_crear_campos_segmentacion(list_id: int, headers: List[str], api_client: API) -> bool:
    """
    Verifica que existan los campos necesarios para segmentación en la lista.
    Si no existen, los crea usando add_merge_tag.

    Args:
        list_id: ID de la lista
        headers: Headers requeridos para segmentación
        api_client: Cliente de la API

    Returns:
        True si los campos están disponibles
    """
    try:
        # Obtener campos existentes
        campos_existentes = api_client.suscriptores.get_merge_fields(list_id)

        # Extraer nombres de campos según el formato de respuesta (robusto)
        nombres_campos = []
        if hasattr(campos_existentes, 'merge_fields'):
            mf = getattr(campos_existentes, 'merge_fields')
            if isinstance(mf, dict):
                nombres_campos = list(mf.keys())
            elif isinstance(mf, list):
                for campo in mf:
                    if isinstance(campo, dict):
                        name_val = campo.get('name')  # type: ignore[attr-defined]
                        if name_val:
                            nombres_campos.append(str(name_val))
                    elif hasattr(campo, 'name'):
                        try:
                            nombres_campos.append(str(getattr(campo, 'name')))
                        except Exception:
                            continue
        else:
            # Respuesta directa como dict o lista
            if isinstance(campos_existentes, dict):
                nombres_campos = list(campos_existentes.keys())
            elif isinstance(campos_existentes, list):
                for campo in campos_existentes:
                    if isinstance(campo, dict):
                        name_val = campo.get('name')  # type: ignore[attr-defined]
                        if name_val:
                            nombres_campos.append(str(name_val))
                    elif hasattr(campo, 'name'):
                        try:
                            nombres_campos.append(str(getattr(campo, 'name')))
                        except Exception:
                            continue

        logger.info(f"Campos existentes en lista {list_id}: {nombres_campos}")

        # Verificar qué campos necesitamos crear
        campos_a_crear = []

        # Siempre crear el campo Segmentos si no existe
        if "Segmentos" not in nombres_campos:
            campos_a_crear.append(("Segmentos", "text"))

        # Verificar otros campos de segmentación (opcional)
        for header in headers[1:]:  # Saltar NOMBRE SEGMENTO
            if header not in nombres_campos:
                # Usar tipo text para todos los campos (Acumbamail no acepta "number")
                tipo_campo = "text"
                campos_a_crear.append((header, tipo_campo))

        # Crear campos faltantes
        for nombre_campo, tipo_campo in campos_a_crear:
            try:
                logger.info(f"Creando campo '{nombre_campo}' tipo '{tipo_campo}' en lista {list_id}")
                api_client.suscriptores.add_merge_tag(list_id, nombre_campo, tipo_campo)
                print(f"  ✅ Campo '{nombre_campo}' creado exitosamente")
            except Exception as e:
                logger.error(f"Error creando campo '{nombre_campo}': {e}")
                print(f"  ❌ Error creando campo '{nombre_campo}': {e}")

        if campos_a_crear:
            logger.info(f"Creados {len(campos_a_crear)} campos en lista {list_id}")
        else:
            logger.info(f"Todos los campos necesarios ya existen en lista {list_id}")

        return True

    except Exception as e:
        logger.error(f"Error verificando/creando campos en lista {list_id}: {e}")
        return False

def obtener_usuarios_existentes_con_segmentos(list_id: int, api_client: API) -> Dict[str, str]:
    """
    Obtiene todos los usuarios existentes de una lista que ya tienen segmentos asignados.

    Args:
        list_id: ID de la lista
        api_client: Cliente de la API

    Returns:
        Diccionario {email: segmentos_actuales}
    """
    try:
        usuarios_con_segmentos = {}

        # Obtener todos los suscriptores
        block_index = 0
        while True:
            try:
                suscriptores = api_client.suscriptores.get_subscribers(
                    list_id=list_id,
                    block_index=block_index,
                    all_fields=1,
                    complete_json=1
                )
            except Exception as e:
                if "No subscribers" in str(e):
                    logger.info(f"Lista {list_id} está vacía")
                    break
                else:
                    raise e

            if not suscriptores:
                break

            for suscriptor in suscriptores:
                email = suscriptor.email
                # Verificar si el suscriptor tiene campo Segmentos usando getattr
                try:
                    segmentos = getattr(suscriptor, 'Segmentos', None) or ''
                    # También intentar con minúsculas por si el campo se llama diferente
                    if not segmentos:
                        segmentos = getattr(suscriptor, 'segmentos', None) or ''
                except AttributeError:
                    segmentos = ''

                if segmentos and segmentos.strip():  # Solo usuarios que ya tienen segmentos no vacíos
                    usuarios_con_segmentos[email] = segmentos

            # Si hay menos de 1000 usuarios, hemos terminado
            if len(suscriptores) < 1000:
                break

            block_index += 1

        logger.info(f"Encontrados {len(usuarios_con_segmentos)} usuarios con segmentos existentes")
        return usuarios_con_segmentos

    except Exception as e:
        if "No subscribers" in str(e):
            logger.info(f"Lista {list_id} está vacía (sin suscriptores)")
            return {}
        else:
            logger.error(f"Error obteniendo usuarios con segmentos: {e}")
            return {}

def eliminar_usuarios_de_lista(emails: List[str], list_id: int, api_client: API) -> bool:
    """
    Elimina usuarios específicos de una lista.

    Args:
        emails: Lista de emails a eliminar
        list_id: ID de la lista
        api_client: Cliente de la API

    Returns:
        True si se eliminaron exitosamente
    """
    try:
        if not emails:
            return True

        logger.info(f"Eliminando {len(emails)} usuarios de lista {list_id}")

        for email in emails:
            try:
                api_client.suscriptores.delete_subscriber(list_id, email)
            except Exception as e:
                logger.warning(f"Error eliminando usuario {email}: {e}")

        logger.info(f"Proceso de eliminación completado para {len(emails)} usuarios")
        return True

    except Exception as e:
        logger.error(f"Error eliminando usuarios: {e}")
        return False

def subir_usuarios_actualizados(df: pd.DataFrame, list_id: int, api_client: API) -> int:
    """
    Sube usuarios con sus segmentos actualizados a la lista usando procesamiento en lotes.

    Args:
        df: DataFrame con usuarios y segmentos
        list_id: ID de la lista
        api_client: Cliente de la API

    Returns:
        Número de usuarios subidos exitosamente
    """
    try:
        from .api.models.suscriptores import SubscriberData
        
        usuarios_subidos = 0
        subscribers_batch = []
        batch_size = 100  # Procesar en lotes de 100

        for _, row in df.iterrows():
            try:
                # Preparar merge fields
                merge_fields = {"email": str(row["email"]).strip()}

                # Añadir campo Segmentos si existe
                if "Segmentos" in df.columns and pd.notna(row["Segmentos"]) and str(row["Segmentos"]).strip():
                    merge_fields["Segmentos"] = str(row["Segmentos"]).strip()

                # Añadir otros campos disponibles
                for col in df.columns:
                    if col not in ["email", "Segmentos"] and pd.notna(row[col]) and str(row[col]).strip():
                        merge_fields[col] = str(row[col]).strip()

                # Verificar que tenga email válido
                if not merge_fields.get("email"):
                    logger.warning(f"Fila sin email válido: {row.to_dict()}")
                    continue

                # Crear SubscriberData tipado
                subscriber_data = SubscriberData(
                    email=merge_fields["email"],
                    **{k: v for k, v in merge_fields.items() if k != "email"}
                )
                subscribers_batch.append(subscriber_data)

                # Procesar lote cuando alcance el tamaño
                if len(subscribers_batch) >= batch_size:
                    result = api_client.suscriptores.batch_add_subscribers(
                        list_id=list_id,
                        subscribers_data=subscribers_batch,
                        update_subscriber=1,  # Actualizar si existe
                        complete_json=1
                    )
                    usuarios_subidos += result.success_count
                    logger.info(f"Lote procesado: {result.success_count} exitosos, {result.error_count} errores")
                    subscribers_batch.clear()

            except Exception as e:
                logger.warning(f"Error preparando usuario {row.get('email', 'unknown')}: {e}")
                continue

        # Procesar último lote si queda alguno
        if subscribers_batch:
            result = api_client.suscriptores.batch_add_subscribers(
                list_id=list_id,
                subscribers_data=subscribers_batch,
                update_subscriber=1,  # Actualizar si existe
                complete_json=1
            )
            usuarios_subidos += result.success_count
            logger.info(f"Último lote procesado: {result.success_count} exitosos, {result.error_count} errores")

        logger.info(f"Subidos {usuarios_subidos} usuarios a lista {list_id} usando procesamiento en lotes")
        return usuarios_subidos

    except Exception as e:
        logger.error(f"Error subiendo usuarios: {e}")
        return 0

def crear_segmentos_con_scraping_batch(list_id: int, segmentos_nombres: List[str], api_client: API) -> bool:
    """
    Delegado al servicio SegmentsScrapingService para crear segmentos por scraping.
    Mantener firma para compatibilidad con flujo existente.
    """
    service = SegmentsScrapingService()
    return service.create_segments_batch(list_id, segmentos_nombres, api_client)

def procesar_lista_individual(nombre_lista: str, segmentos_data: List[List[Any]], headers: List[str]) -> bool:
    """
    Procesa una lista individual aplicando todos sus segmentos usando la API de Acumbamail.
    Función robusta con manejo de errores y validaciones.

    Args:
        nombre_lista: Nombre de la lista a procesar
        segmentos_data: Datos de segmentos para esta lista
        headers: Headers de las columnas

    Returns:
        True si se procesó exitosamente
    """
    logger.info(f"Procesando lista: {nombre_lista}")

    try:
        # Validaciones previas
        if not nombre_lista or not nombre_lista.strip():
            logger.error("Nombre de lista vacío o inválido")
            notify("Error", "Nombre de lista vacío o inválido", "error")
            return False

        if not segmentos_data:
            logger.warning(f"No hay datos de segmentos para la lista: {nombre_lista}")
            notify("Advertencia", f"No hay datos de segmentos para la lista: {nombre_lista}", "warning")
            return False

        # Configurar cliente API con validaciones
        try:
            config = load_config()
            if not config:
                logger.error("No se pudo cargar la configuración")
                notify("Error", "No se pudo cargar la configuración", "error")
                return False

            api_client = API()
        except Exception as e:
            logger.error(f"Error configurando cliente API: {e}")
            notify("Error API", f"Error configurando cliente API: {e}", "error")
            return False

        # 1. Primero buscar ID en nuestros archivos locales (con manejo de errores)
        list_id = None
        try:
            list_id = obtener_o_buscar_id_lista(nombre_lista)
        except Exception as e:
            logger.warning(f"Error buscando ID local para {nombre_lista}: {e}")

        if list_id:
            print(f"ID {list_id} encontrado para lista '{nombre_lista}'")
            # Verificar que la lista aún existe en el servidor (con timeout y reintentos)
            try:
                listas_remotas = api_client.suscriptores.get_lists()
                lista_existe = any(lista.id == list_id for lista in listas_remotas)

                if not lista_existe:
                    logger.warning(f"Lista con ID {list_id} no existe en el servidor, será recreada")
                    print(f"Lista ID {list_id} no existe en servidor, creando nueva")
                    list_id = None
                else:
                    logger.info(f"Lista ID {list_id} confirmada en servidor")
            except Exception as e:
                logger.warning(f"Error verificando lista en servidor: {e}")
                notify("Advertencia", f"No se pudo verificar lista en servidor: {e}", "warning")
                # Si hay error verificando, intentaremos usar el ID que tenemos

        if not list_id:
            # 2. Si no tenemos ID o la lista no existe, buscar por nombre en servidor
            try:
                list_id = obtener_id_lista_por_nombre(nombre_lista, api_client)
            except Exception as e:
                logger.warning(f"Error buscando lista por nombre en servidor: {e}")
                notify("Advertencia", f"Error buscando lista por nombre: {e}", "warning")

            if list_id:
                # Si encontramos la lista en servidor pero no en nuestros archivos, actualizar
                print(f"Lista '{nombre_lista}' encontrada en servidor (ID: {list_id})")
                try:
                    actualizar_id_en_segmentos(nombre_lista, list_id)
                except Exception as e:
                    logger.warning(f"Error actualizando ID en segmentos: {e}")
            else:
                # 3. Si no existe en ningún lado, saltar este segmento
                logger.info(f"Lista '{nombre_lista}' no existe en carpeta /listas ni en servidor. Saltando...")
                print(f"⚠️ Lista '{nombre_lista}' no existe en /listas. Saltando segmento.")
                notify("Lista No Encontrada", f"Lista '{nombre_lista}' no existe en /listas. Segmento saltado.", "warning")
                return False  # Retornar False para indicar que se saltó

        if not list_id:
            logger.error(f"No se pudo obtener ID válido para lista: {nombre_lista}")
            notify("Error", f"No se pudo obtener ID válido para lista: {nombre_lista}", "error")
            return False

        print(f"Lista encontrada: {nombre_lista} (ID: {list_id})")

        # Verificar y crear campos necesarios (con manejo de errores)
        try:
            if not verificar_y_crear_campos_segmentacion(list_id, headers, api_client):
                logger.error(f"No se pudieron crear los campos necesarios para lista {nombre_lista}")
                notify("Error", f"No se pudieron crear campos para lista {nombre_lista}", "error")
                return False
        except Exception as e:
            logger.error(f"Error verificando campos para lista {nombre_lista}: {e}")
            notify("Error", f"Error verificando campos: {e}", "error")
            return False

        # Obtener usuarios existentes en Acumbamail (con manejo de errores)
        try:
            usuarios_existentes = obtener_usuarios_existentes_con_segmentos(list_id, api_client)
        except Exception as e:
            logger.warning(f"Error obteniendo usuarios existentes: {e}")
            usuarios_existentes = {}

        # Obtener TODOS los usuarios de la lista (con manejo robusto de errores)
        try:
            todos_usuarios_acumba = api_client.suscriptores.get_subscribers(list_id, all_fields=1, complete_json=1)
            emails_en_acumba = {usuario.email for usuario in todos_usuarios_acumba}
            logger.info(f"Encontrados {len(emails_en_acumba)} usuarios en Acumbamail")
        except Exception as e:
            # Lista recién creada o vacía - esto es normal
            if "No subscribers" in str(e) or "not found" in str(e).lower():
                logger.info(f"Lista {list_id} está vacía (recién creada)")
                emails_en_acumba = set()
            else:
                logger.warning(f"Error obteniendo usuarios de Acumbamail: {e}")
                emails_en_acumba = set()

        # Obtener/asegurar ruta del archivo local con ID en el nombre (con validaciones)
        try:
            ruta_archivo = asegurar_nombre_archivo_con_id(nombre_lista, list_id)
            if not ruta_archivo:
                logger.error(f"No se pudo determinar ruta de archivo para lista {nombre_lista}")
                notify("Error", f"No se pudo determinar ruta de archivo para lista {nombre_lista}", "error")
                return False
        except Exception as e:
            logger.error(f"Error determinando ruta de archivo: {e}")
            notify("Error", f"Error determinando ruta de archivo: {e}", "error")
            return False

        # Verificar si el archivo local existe
        if not os.path.exists(ruta_archivo):
            logger.warning(f"Archivo local no existe: {ruta_archivo}")
            # Crear archivo básico con estructura mínima
            try:
                columnas_base = ['email'] + headers[1:]  # email + columnas de segmentación
                df_vacio = pd.DataFrame(columns=columnas_base)
                if not ExcelHelper.escribir_excel(df_vacio, ruta_archivo):
                    logger.error(f"No se pudo crear archivo para lista {nombre_lista}")
                    notify("Error", f"No se pudo crear archivo para lista {nombre_lista}", "error")
                    return False
                logger.info(f"Creado archivo nuevo para lista: {nombre_lista}")
                notify("Archivo Creado", f"Creado archivo nuevo para lista: {nombre_lista}", "info")
                return True  # Archivo vacío creado, procesamiento completado
            except Exception as e:
                logger.error(f"Error creando archivo para lista {nombre_lista}: {e}")
                notify("Error", f"Error creando archivo: {e}", "error")
                return False

        # Leer archivo existente (con validaciones)
        try:
            df = ExcelHelper.leer_excel(ruta_archivo)
            if df is None:
                logger.error(f"No se pudo leer archivo: {ruta_archivo}")
                notify("Error", f"No se pudo leer archivo: {ruta_archivo}", "error")
                return False
        except Exception as e:
            logger.error(f"Error leyendo archivo {ruta_archivo}: {e}")
            notify("Error", f"Error leyendo archivo: {e}", "error")
            return False

        if df.empty:
            logger.warning(f"Lista {nombre_lista} está vacía")
            notify("Advertencia", f"Lista {nombre_lista} está vacía", "warning")
            return True

        # Verificar compatibilidad para segmentación (con validaciones mejoradas)
        try:
            es_compatible, columnas_disponibles = verificar_columnas_compatibles(df, headers)
        except Exception as e:
            logger.error(f"Error verificando compatibilidad de columnas: {e}")
            notify("Error", f"Error verificando compatibilidad: {e}", "error")
            return False

        # Si no es compatible pero tiene email, subir usuarios sin segmentación
        if not es_compatible:
            if 'email' in df.columns:
                logger.info(f"Lista {nombre_lista} no tiene columnas para segmentación, procesando solo usuarios")
                notify("Sin Segmentación", f"Lista {nombre_lista} no tiene campos de segmentación, procesando solo usuarios", "warning")

                # Identificar usuarios nuevos (con manejo de errores)
                try:
                    emails_locales = set(df['email'].dropna())
                    usuarios_nuevos = emails_locales - emails_en_acumba

                    if usuarios_nuevos:
                        print(f"Subiendo {len(usuarios_nuevos)} usuarios nuevos a Acumbamail...")
                        df_nuevos = df[df['email'].isin(usuarios_nuevos)]
                        try:
                            usuarios_subidos = subir_usuarios_actualizados(df_nuevos, list_id, api_client)
                            print(f"{usuarios_subidos} usuarios nuevos subidos")
                            notify("Usuarios Subidos", f"{usuarios_subidos} usuarios nuevos subidos a {nombre_lista}", "info")
                        except Exception as e:
                            logger.error(f"Error subiendo usuarios nuevos: {e}")
                            notify("Error Subida", f"Error subiendo usuarios: {e}", "error")
                    else:
                        notify("Sin Usuarios Nuevos", f"No hay usuarios nuevos para subir a {nombre_lista}", "info")
                except Exception as e:
                    logger.error(f"Error procesando usuarios sin segmentación: {e}")
                    notify("Error", f"Error procesando usuarios: {e}", "error")
                    return False

                logger.info(f"Lista {nombre_lista} procesada sin segmentación")
                return True
            else:
                columnas_faltantes = ['email'] + [h for h in headers[1:] if h not in df.columns]
                error_msg = f"Lista {nombre_lista} no es compatible. Faltan columnas: {', '.join(columnas_faltantes)}. Columnas disponibles: {', '.join(df.columns.tolist())}"
                logger.warning(error_msg)
                notify("Lista Incompatible", error_msg, "error")
                return False

        logger.info(f"Lista {nombre_lista}: {len(df)} filas, columnas disponibles: {columnas_disponibles}")

        # Identificar y subir usuarios nuevos antes de la segmentación (con manejo robusto)
        try:
            emails_locales = set(df['email'].dropna())
            usuarios_nuevos = emails_locales - emails_en_acumba

            if usuarios_nuevos:
                print(f"Subiendo {len(usuarios_nuevos)} usuarios nuevos a Acumbamail...")
                notify("Subiendo Usuarios", f"Subiendo {len(usuarios_nuevos)} usuarios nuevos", "info")
                df_nuevos = df[df['email'].isin(usuarios_nuevos)]
                try:
                    usuarios_subidos = subir_usuarios_actualizados(df_nuevos, list_id, api_client)
                    print(f"{usuarios_subidos} usuarios nuevos subidos")
                    notify("Usuarios Subidos", f"{usuarios_subidos} usuarios nuevos subidos", "info")
                except Exception as e:
                    logger.error(f"Error subiendo usuarios nuevos: {e}")
                    notify("Error Subida", f"Error subiendo usuarios nuevos: {e}", "error")
                    # Continuar con segmentación aunque falle la subida de nuevos usuarios
        except Exception as e:
            logger.error(f"Error identificando usuarios nuevos: {e}")
            notify("Error", f"Error identificando usuarios nuevos: {e}", "warning")
            # Continuar con segmentación aunque falle esta parte

        # Guardar estado original para detectar cambios (con validación)
        try:
            df_original = df.copy()
        except Exception as e:
            logger.error(f"Error copiando DataFrame: {e}")
            notify("Error", f"Error copiando datos: {e}", "error")
            return False

        # Procesar cada segmento con notificaciones de progreso
        total_modificaciones = 0
        usuarios_a_eliminar = set()
        usuarios_a_subir = []
        # Usar un conjunto para evitar duplicados desde el principio
        segmentos_creados = set()

        notify("Procesando Segmentos", f"Iniciando procesamiento de {len(segmentos_data)} segmentos", "info")

        for i, segmento_condiciones in enumerate(segmentos_data, 1):
            nombre_segmento = segmento_condiciones[0]

            logger.info(f"Aplicando segmento {i}/{len(segmentos_data)}: {nombre_segmento}")

            # Aplicar condiciones con manejo de errores
            try:
                mask = aplicar_condiciones_segmento(df, segmento_condiciones, headers)
            except Exception as e:
                logger.error(f"Error aplicando condiciones del segmento {nombre_segmento}: {e}")
                notify("Error Segmento", f"Error en segmento {nombre_segmento}: {e}", "warning")
                continue  # Continuar con el siguiente segmento

            if mask.any():
                # Actualizar segmentos con manejo de errores
                try:
                    df, filas_modificadas = actualizar_columna_segmentos(df, mask, nombre_segmento)
                    total_modificaciones += len(filas_modificadas)

                    # Marcar usuarios para re-subir
                    for idx in filas_modificadas:
                        try:
                            email = df.loc[idx, 'email']
                            usuarios_a_eliminar.add(email)
                        except Exception as e:
                            logger.warning(f"Error procesando usuario en índice {idx}: {e}")

                    print(f"  Segmento '{nombre_segmento}': {len(filas_modificadas)} usuarios asignados")
                    
                    # Agregar a la lista de segmentos únicos que necesitan ser creados en Acumbamail
                    segmentos_creados.add(nombre_segmento)
                except Exception as e:
                    logger.error(f"Error actualizando segmento {nombre_segmento}: {e}")
                    notify("Error Actualización", f"Error actualizando segmento {nombre_segmento}: {e}", "warning")
                    continue
                
            else:
                print(f"  Segmento '{nombre_segmento}': 0 usuarios cumplen las condiciones")
                logger.warning(f"No hay usuarios que cumplan las condiciones para el segmento '{nombre_segmento}': {segmento_condiciones}")

        # Detectar cambios con manejo de errores
        try:
            df_cambios = detectar_cambios_segmentos(df_original, df)
        except Exception as e:
            logger.error(f"Error detectando cambios: {e}")
            notify("Error", f"Error detectando cambios: {e}", "warning")
            df_cambios = None

        # Procesar usuarios que cambiaron de segmento con manejo robusto
        if usuarios_a_eliminar:
            print(f"Actualizando {len(usuarios_a_eliminar)} usuarios en Acumbamail...")
            notify("Actualizando Usuarios", f"Actualizando {len(usuarios_a_eliminar)} usuarios en Acumbamail", "info")

            try:
                # Eliminar usuarios que cambiaron
                emails_a_eliminar = list(usuarios_a_eliminar)
                if eliminar_usuarios_de_lista(emails_a_eliminar, list_id, api_client):
                    print(f"  Eliminados {len(emails_a_eliminar)} usuarios para actualización")

                    # Preparar datos de usuarios para re-subir
                    try:
                        df_usuarios_actualizados = df[df['email'].isin(emails_a_eliminar)]

                        # Subir usuarios actualizados
                        usuarios_subidos = subir_usuarios_actualizados(df_usuarios_actualizados, list_id, api_client)
                        print(f"  Re-subidos {usuarios_subidos} usuarios con segmentos actualizados")
                        notify("Usuarios Actualizados", f"Re-subidos {usuarios_subidos} usuarios", "info")
                    except Exception as e:
                        logger.error(f"Error re-subiendo usuarios: {e}")
                        notify("Error Re-subida", f"Error re-subiendo usuarios: {e}", "error")
                else:
                    logger.warning("No se pudieron eliminar usuarios para actualización")
                    notify("Advertencia", "No se pudieron eliminar usuarios para actualización", "warning")
            except Exception as e:
                logger.error(f"Error en proceso de actualización de usuarios: {e}")
                notify("Error Actualización", f"Error actualizando usuarios: {e}", "error")

        # Guardar archivo principal local con validaciones
        if total_modificaciones > 0:
            try:
                if ExcelHelper.escribir_excel(df, ruta_archivo, 'Datos', reemplazar=True):
                    logger.info(f"Guardado archivo principal: {nombre_lista} ({total_modificaciones} modificaciones)")
                    notify("Archivo Guardado", f"Guardado archivo con {total_modificaciones} modificaciones", "info")
                else:
                    logger.error(f"Error guardando archivo principal: {nombre_lista}")
                    notify("Error Guardado", f"Error guardando archivo: {nombre_lista}", "error")
            except Exception as e:
                logger.error(f"Error escribiendo archivo {ruta_archivo}: {e}")
                notify("Error Archivo", f"Error escribiendo archivo: {e}", "error")
                logger.error(f"Error guardando archivo principal: {nombre_lista}")
                return False

        # Guardar hoja de cambios si hay cambios (con validación de None)
        if df_cambios is not None and not df_cambios.empty:
            try:
                if ExcelHelper.escribir_excel(df_cambios, ruta_archivo, 'Cambios', reemplazar=False):
                    logger.info(f"Guardada hoja de cambios: {nombre_lista} ({len(df_cambios)} cambios)")
                    notify("Cambios Guardados", f"Guardados {len(df_cambios)} cambios detectados", "info")
                else:
                    logger.warning(f"Error guardando hoja de cambios: {nombre_lista}")
                    notify("Error Cambios", f"Error guardando hoja de cambios: {nombre_lista}", "warning")
            except Exception as e:
                logger.error(f"Error escribiendo hoja de cambios: {e}")
                notify("Error", f"Error escribiendo hoja de cambios: {e}", "warning")

        # Determinar cantidad de cambios para reporte
        num_cambios = len(df_cambios) if df_cambios is not None else 0
        print(f"Lista '{nombre_lista}' procesada: {total_modificaciones} modificaciones, {num_cambios} cambios detectados")
        notify("Lista Procesada", f"Lista '{nombre_lista}' procesada: {total_modificaciones} modificaciones", "info")

        # Crear segmentos en Acumbamail (verificando existencia primero)
        if segmentos_creados:
            # Convertir el conjunto a lista ordenada para procesamiento
            segmentos_unicos = sorted(list(segmentos_creados))
            print(f"Procesando {len(segmentos_unicos)} segmento(s) únicos: {segmentos_unicos}")
            notify("Creando Segmentos", f"Procesando {len(segmentos_unicos)} segmentos únicos", "info")
            
            # Usar la función batch que verifica existencia y maneja múltiples segmentos
            try:
                exito_segmentos = crear_segmentos_con_scraping_batch(list_id, segmentos_unicos, api_client)
                
                if exito_segmentos:
                    print(f"  Procesamiento de segmentos completado exitosamente")
                    notify("Segmentos Creados", "Procesamiento de segmentos completado exitosamente", "info")
                else:
                    print(f"  Algunos segmentos pudieron no haberse procesado correctamente")
                    logger.warning(f"Error procesando algunos segmentos para lista '{nombre_lista}'")
                    notify("Advertencia Segmentos", "Algunos segmentos pudieron no procesarse correctamente", "warning")
            except Exception as e:
                logger.error(f"Error creando segmentos: {e}")
                notify("Error Segmentos", f"Error creando segmentos: {e}", "error")
        else:
            print("  No hay segmentos nuevos para crear")
            notify("Sin Segmentos", "No hay segmentos nuevos para crear", "info")

        # Cerrar conexión API - No es necesario para la clase API actual
        # No client to close for API class

        logger.info(f"Lista {nombre_lista} procesada exitosamente")
        return True

    except Exception as e:
        logger.error(f"Error procesando lista {nombre_lista}: {e}")
        notify("Error Procesamiento", f"Error procesando lista '{nombre_lista}': {e}", "error")
        return False

def mapear_segmentos_completo() -> Dict[str, Any]:
    """
    Función principal para mapear todos los segmentos.
    Incluye validaciones robustas y manejo de errores.

    Returns:
        Diccionario con estadísticas del proceso
    """
    logger.info("Iniciando mapeo completo de segmentos")
    notify("Iniciando", "Iniciando mapeo de segmentos", "info")

    try:
        # Inicializar archivo de segmentos si es necesario
        if not inicializar_archivo_segmentos():
            error_msg = "No se pudo inicializar archivo de segmentos"
            notify("Error", error_msg, "error")
            return {"error": error_msg}

        # Mostrar estado actual (con manejo de errores)
        try:
            mostrar_estado_listas_segmentos()
        except Exception as e:
            logger.warning(f"Error mostrando estado de listas: {e}")
            notify("Advertencia", f"No se pudo mostrar el estado de listas: {e}", "warning")

        # Verificar que existe el archivo de segmentos
        if not os.path.exists(ARCHIVO_SEGMENTOS):
            error_msg = f"Archivo de segmentos no encontrado: {ARCHIVO_SEGMENTOS}"
            logger.error(error_msg)
            notify("Error", error_msg, "error")
            return {"error": error_msg}

        # Procesar archivo de segmentos con validaciones
        try:
            headers, grouped_data = procesar_excel_segmentos(ARCHIVO_SEGMENTOS)
        except Exception as e:
            error_msg = f"Error procesando archivo de segmentos: {e}"
            logger.error(error_msg)
            notify("Error", error_msg, "error")
            return {"error": error_msg}

        if not grouped_data:
            error_msg = "No se encontraron datos de segmentos para procesar"
            logger.warning(error_msg)
            notify("Advertencia", error_msg, "warning")
            return {"error": error_msg}

        # Notificar listas encontradas
        notify("Listas Encontradas", f"Se encontraron {len(grouped_data)} lista(s) con segmentos", "info")
        
        print(f"Encontradas {len(grouped_data)} lista(s) con segmentos:")
        for lista_info in grouped_data:
            nombre_lista = lista_info[0]
            segmentos = lista_info[1]
            # Mostrar ID si está disponible
            try:
                list_id = obtener_o_buscar_id_lista(nombre_lista)
                if list_id:
                    print(f"  • {nombre_lista} (ID: {list_id}): {len(segmentos)} segmento(s)")
                else:
                    print(f"  • {nombre_lista} (sin ID): {len(segmentos)} segmento(s)")
            except Exception as e:
                logger.warning(f"Error obteniendo ID para lista {nombre_lista}: {e}")
                print(f"  • {nombre_lista} (ID desconocido): {len(segmentos)} segmento(s)")

        # Procesar cada lista con manejo robusto de errores
        estadisticas = {
            "listas_procesadas": [],
            "listas_fallidas": [],
            "total_listas": len(grouped_data),
            "headers": headers,
            "errores_detallados": []
        }

        for i, lista_info in enumerate(grouped_data, 1):
            nombre_lista = lista_info[0]
            segmentos_data = lista_info[1]

            print(f"\nProcesando lista {i}/{len(grouped_data)}: {nombre_lista}")
            notify("Progreso", f"Procesando lista {i}/{len(grouped_data)}: {nombre_lista}", "info")

            try:
                if procesar_lista_individual(nombre_lista, segmentos_data, headers):
                    estadisticas["listas_procesadas"].append(nombre_lista)
                    logger.info(f"Lista procesada exitosamente: {nombre_lista}")
                else:
                    estadisticas["listas_fallidas"].append(nombre_lista)
                    estadisticas["errores_detallados"].append(f"{nombre_lista}: Error en procesamiento")
                    logger.warning(f"Lista falló en procesamiento: {nombre_lista}")
            except Exception as e:
                estadisticas["listas_fallidas"].append(nombre_lista)
                error_detalle = f"{nombre_lista}: {str(e)}"
                estadisticas["errores_detallados"].append(error_detalle)
                logger.error(f"Error procesando lista {nombre_lista}: {e}")
                notify("Error Lista", f"Error procesando {nombre_lista}: {e}", "warning")

        # Resumen final sin emojis
        print(f"\nResumen del mapeo:")
        print(f"   Listas procesadas: {len(estadisticas['listas_procesadas'])}")
        for lista in estadisticas["listas_procesadas"]:
            print(f"      • {lista}")

        print(f"   Listas fallidas: {len(estadisticas['listas_fallidas'])}")
        for lista in estadisticas["listas_fallidas"]:
            print(f"      • {lista}")

        # Notificación de resultado final
        if estadisticas["listas_procesadas"]:
            notify("Mapeo Completado", 
                f"Mapeo finalizado: {len(estadisticas['listas_procesadas'])} listas exitosas, {len(estadisticas['listas_fallidas'])} fallidas", 
                "info")
        else:
            notify("Mapeo Sin Éxito", "No se procesaron listas correctamente", "warning")

        logger.info(f"Mapeo completado: {len(estadisticas['listas_procesadas'])} exitosas, {len(estadisticas['listas_fallidas'])} fallidas")

        return estadisticas

    except Exception as e:
        error_msg = f"Error crítico en mapeo de segmentos: {e}"
        logger.error(error_msg)
        notify("Error Crítico", error_msg, "error")
        return {"error": error_msg}

    # Resumen final
    print(f"\n📊 Resumen del mapeo:")
    print(f"   ✅ Listas procesadas: {len(estadisticas['listas_procesadas'])}")
    for lista in estadisticas["listas_procesadas"]:
        print(f"      • {lista}")

    print(f"   ❌ Listas fallidas: {len(estadisticas['listas_fallidas'])}")
    for lista in estadisticas["listas_fallidas"]:
        print(f"      • {lista}")

    logger.info(f"Mapeo completado: {len(estadisticas['listas_procesadas'])} exitosas, {len(estadisticas['listas_fallidas'])} fallidas")

    return estadisticas

def main():
    """Función principal para ejecutar el mapeo desde línea de comandos"""
    try:
        resultado = mapear_segmentos_completo()

        if "error" in resultado:
            print(f"❌ {resultado['error']}")
            return False

        if resultado["listas_procesadas"]:
            print("🎉 Mapeo de segmentos completado exitosamente")
            return True
        else:
            print("⚠️ No se procesaron listas correctamente")
            return False

    except Exception as e:
        logger.error(f"Error en mapeo de segmentos: {e}")
        print(f"❌ Error durante el mapeo: {e}")
        return False

if __name__ == "__main__":
    main()