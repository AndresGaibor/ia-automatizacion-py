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
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from .utils import data_path, load_config, crear_contexto_navegador, storage_state_path
from .logger import get_logger
from .excel_helper import ExcelHelper
from .api import API

logger = get_logger()

# Rutas de archivos
ARCHIVO_SEGMENTOS = data_path("Segmentos.xlsx")
CARPETA_LISTAS = data_path("listas")

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

    # Procesar cada fila
    for _, row in df.iterrows():
        nombre_lista = row['NOMBRE LISTA']

        if pd.isna(nombre_lista):
            continue

        # Crear tupla con los valores que nos interesan
        valores = (
            row.get('NOMBRE SEGMENTO', ''),
            row.get('SEDE', ''),
            row.get('ORGANO', ''),
            row.get('N ORGANO', ''),
            row.get('ROL USUARIO', ''),
            row.get('PERFIL USUARIO', '')
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

    logger.info(f"Aplicando condiciones para segmento '{condiciones[0]}': {condiciones}")
    logger.info(f"Columnas disponibles en DataFrame: {list(df.columns)}")

    # Aplicar cada condición con AND
    for i, (valor, columna) in enumerate(zip(condiciones[1:], headers[1:]), 1):  # Saltar NOMBRE SEGMENTO
        if columna not in df.columns:
            logger.warning(f"Columna '{columna}' no existe en DataFrame")
            continue

        # Ignorar valores None, vacíos o NaN
        if pd.isna(valor) or valor == '' or valor is None:
            logger.info(f"Saltando condición para '{columna}': valor vacío/nulo")
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

        # Extraer nombres de campos según el formato de respuesta
        if hasattr(campos_existentes, 'merge_fields'):
            if isinstance(campos_existentes.merge_fields, dict):
                # Los nombres son las claves del diccionario
                nombres_campos = list(campos_existentes.merge_fields.keys())
            else:
                # Es una lista de objetos con atributo name
                nombres_campos = [campo.name for campo in campos_existentes.merge_fields if hasattr(campo, 'name')]
        else:
            # Respuesta directa como dict o lista
            if isinstance(campos_existentes, dict):
                nombres_campos = list(campos_existentes.keys())
            else:
                nombres_campos = []

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

def crear_segmento_individual(context, list_id: int, nombre_segmento: str) -> bool:
    """
    Crea un segmento individual usando un contexto de navegador existente.
    
    Args:
        context: Contexto del navegador de Playwright
        list_id: ID de la lista en Acumbamail
        nombre_segmento: Nombre del segmento a crear
        
    Returns:
        True si el segmento se creó exitosamente
    """
    logger.info(f"Creando segmento '{nombre_segmento}' en lista {list_id}")
    
    try:
        page = context.new_page()
        
        try:
            # Navegar a la página de segmentos
            segments_url = f"https://acumbamail.com/app/list/{list_id}/segments/"
            logger.info(f"Navegando a: {segments_url}")
            page.goto(segments_url, wait_until="domcontentloaded")
            
            # Esperar a que la página cargue completamente
            page.wait_for_load_state("networkidle")
            
            # Buscar el botón "Nuevo segmento" - probamos ambos locators
            nuevo_segmento_button = None
            
            try:
                # Primer intento: botón en estado vacío
                empty_state_button = page.locator("#empty-state-add-segment-button").get_by_text("Nuevo segmento")
                if empty_state_button.is_visible(timeout=5000):
                    nuevo_segmento_button = empty_state_button
                    logger.info("Encontrado botón en estado vacío")
            except PlaywrightTimeoutError:
                pass
            
            if not nuevo_segmento_button:
                try:
                    # Segundo intento: botón normal
                    normal_button = page.locator("#new-segment-button").get_by_text("Nuevo segmento")
                    if normal_button.is_visible(timeout=5000):
                        nuevo_segmento_button = normal_button
                        logger.info("Encontrado botón normal")
                except PlaywrightTimeoutError:
                    pass
            
            if not nuevo_segmento_button:
                # Último intento: buscar cualquier botón con el texto
                try:
                    nuevo_segmento_button = page.get_by_role("button", name="Nuevo segmento")
                    if nuevo_segmento_button.is_visible(timeout=5000):
                        logger.info("Encontrado botón por rol")
                    else:
                        nuevo_segmento_button = None
                except PlaywrightTimeoutError:
                    nuevo_segmento_button = None
            
            if not nuevo_segmento_button:
                logger.error("No se pudo encontrar el botón 'Nuevo segmento'")
                return False
            
            # Hacer clic en el botón
            nuevo_segmento_button.click()
            logger.info("Clic en 'Nuevo segmento'")
            
            # Esperar a que aparezca el formulario
            page.wait_for_selector("#field-value-1", timeout=10000)
            
            # Llenar el nombre del segmento
            nombre_input = page.locator("#field-value-1")
            nombre_input.fill(nombre_segmento)
            logger.info(f"Nombre del segmento configurado: {nombre_segmento}")
            
            # Configurar el campo "Segmentos" con condición "contiene"
            try:
                # Seleccionar el campo "Segmentos"
                campo_select = page.locator("select[name*='field']").first
                campo_select.select_option(label="Segmentos")
                logger.info("Campo 'Segmentos' seleccionado")
                
                # Cambiar la condición a "contiene" (no "igual que")
                condicion_select = page.locator("select[name*='condition']").first
                condicion_select.select_option(label="contiene")
                logger.info("Condición 'contiene' seleccionada")
                
                # Llenar el valor con el nombre del segmento
                valor_input = page.locator("input[name*='value']").first
                valor_input.fill(nombre_segmento)
                logger.info(f"Valor de condición configurado: {nombre_segmento}")
                
            except Exception as e:
                logger.warning(f"Error configurando condiciones específicas: {e}")
                # Si falla, intentar con selectores más generales
                try:
                    page.get_by_text("Segmentos").click()
                    page.get_by_text("contiene").click()
                    page.locator("input[type='text']").last.fill(nombre_segmento)
                except Exception as e2:
                    logger.error(f"Error en configuración alternativa: {e2}")
            
            # Guardar el segmento
            try:
                # Buscar botón de guardar
                save_button = page.get_by_role("button", name="Guardar")
                if not save_button.is_visible():
                    save_button = page.get_by_role("button", name="Crear")
                if not save_button.is_visible():
                    save_button = page.locator("button[type='submit']").first
                
                save_button.click()
                logger.info("Clic en guardar segmento")
                
                # Esperar confirmación o redirección
                page.wait_for_load_state("networkidle", timeout=15000)
                
                logger.info(f"Segmento '{nombre_segmento}' creado exitosamente")
                return True
                
            except Exception as e:
                logger.error(f"Error guardando segmento: {e}")
                return False
                
        finally:
            # Cerrar página
            try:
                page.close()
            except:
                pass
        
    except Exception as e:
        logger.error(f"Error creando segmento individual: {e}")
        return False

def crear_segmento_con_scraping(list_id: int, nombre_segmento: str, api_client: API) -> bool:
    """
    Crea un segmento usando scraping de Playwright en Acumbamail.
    Primero verifica si el segmento ya existe usando la API.
    
    Args:
        list_id: ID de la lista en Acumbamail
        nombre_segmento: Nombre del segmento a crear
        api_client: Cliente de API para verificar segmentos existentes
        
    Returns:
        True si el segmento se creó exitosamente o ya existe
    """
    logger.info(f"Verificando si segmento '{nombre_segmento}' ya existe en lista {list_id}")
    
    # Verificar si el segmento ya existe usando la API
    try:
        segmentos_existentes = api_client.suscriptores.get_list_segments(list_id)
        # Los segmentos pueden venir como tuplas (name, id) o como objetos con atributo name
        if segmentos_existentes:
            nombres_existentes = []
            for seg in segmentos_existentes:
                if isinstance(seg, tuple):
                    nombres_existentes.append(seg[0])  # Primer elemento de la tupla es el nombre
                elif hasattr(seg, 'name'):
                    nombres_existentes.append(seg.name)
                else:
                    nombres_existentes.append(str(seg))
        else:
            nombres_existentes = []
        
        if nombre_segmento in nombres_existentes:
            logger.info(f"Segmento '{nombre_segmento}' ya existe en la lista")
            return True
            
    except Exception as e:
        logger.warning(f"Error verificando segmentos existentes: {e}. Procederé a crear el segmento.")
    
    logger.info(f"Creando segmento '{nombre_segmento}' en lista {list_id} usando scraping")
    
    try:
        config = load_config()
        
        with sync_playwright() as playwright:
            # Crear navegador y contexto
            browser = playwright.chromium.launch(headless=False)
            context = crear_contexto_navegador(browser)
            page = context.new_page()
            
            try:
                # Navegar a la página de segmentos
                segments_url = f"https://acumbamail.com/app/list/{list_id}/segments/"
                logger.info(f"Navegando a: {segments_url}")
                page.goto(segments_url, wait_until="domcontentloaded")
                
                # Esperar a que la página cargue completamente
                page.wait_for_load_state("networkidle")
                
                # Buscar el botón "Nuevo segmento" - probamos ambos locators
                nuevo_segmento_button = None
                
                try:
                    # Primer intento: botón en estado vacío
                    empty_state_button = page.locator("#empty-state-add-segment-button").get_by_text("Nuevo segmento")
                    if empty_state_button.is_visible(timeout=5000):
                        nuevo_segmento_button = empty_state_button
                        logger.info("Encontrado botón en estado vacío")
                except PlaywrightTimeoutError:
                    pass
                
                if not nuevo_segmento_button:
                    try:
                        # Segundo intento: botón normal
                        normal_button = page.locator("#new-segment-button").get_by_text("Nuevo segmento")
                        if normal_button.is_visible(timeout=5000):
                            nuevo_segmento_button = normal_button
                            logger.info("Encontrado botón normal")
                    except PlaywrightTimeoutError:
                        pass
                
                if not nuevo_segmento_button:
                    # Último intento: buscar cualquier botón con el texto
                    try:
                        nuevo_segmento_button = page.get_by_role("button", name="Nuevo segmento")
                        if nuevo_segmento_button.is_visible(timeout=5000):
                            logger.info("Encontrado botón por rol")
                        else:
                            nuevo_segmento_button = None
                    except PlaywrightTimeoutError:
                        nuevo_segmento_button = None
                
                if not nuevo_segmento_button:
                    logger.error("No se pudo encontrar el botón 'Nuevo segmento'")
                    return False
                
                # Hacer clic en el botón
                nuevo_segmento_button.click()
                logger.info("Clic en 'Nuevo segmento'")
                
                # Esperar a que aparezca el formulario y llenar el nombre del segmento
                page.wait_for_selector("#field-value-1", timeout=10000)
                
                # Usar el locator específico para el nombre del segmento
                nombre_input = page.get_by_role("textbox", name="Nombre del segmento")
                nombre_input.fill(nombre_segmento)
                logger.info(f"Nombre del segmento configurado: {nombre_segmento}")
                
                # Configurar el campo usando los locators específicos
                try:
                    # Seleccionar el campo "Segmentos" usando #field-name-1
                    campo_select = page.locator("#field-name-1")
                    campo_select.select_option(label="Segmentos")
                    logger.info("Campo 'Segmentos' seleccionado con #field-name-1")
                    
                    # Cambiar la condición a "contiene" usando #field-type-1
                    condicion_select = page.locator("#field-type-1")
                    condicion_select.select_option(label="contiene")
                    logger.info("Condición 'contiene' seleccionada con #field-type-1")
                    
                    # Llenar el valor con el nombre del segmento usando #field-value-1
                    valor_input = page.locator("#field-value-1")
                    valor_input.fill(nombre_segmento)
                    logger.info(f"Valor de condición configurado: {nombre_segmento}")
                    
                except Exception as e:
                    logger.error(f"Error configurando condiciones específicas: {e}")
                    return False
                
                # Guardar el segmento usando #segment-button-text
                try:
                    save_button = page.locator("#segment-button-text")
                    save_button.click()
                    logger.info("Clic en guardar segmento usando #segment-button-text")
                    
                    # Esperar 5 segundos como se solicita
                    page.wait_for_timeout(5000)
                    logger.info("Esperando 5 segundos después de guardar")
                    
                    logger.info(f"Segmento '{nombre_segmento}' creado exitosamente")
                    return True
                    
                except Exception as e:
                    logger.error(f"Error guardando segmento: {e}")
                    return False
                    
            finally:
                # Cerrar página y contexto de manera segura
                try:
                    page.close()
                    context.close()
                    browser.close()
                except:
                    pass
            
    except Exception as e:
        logger.error(f"Error creando segmento con scraping: {e}")
        return False

def crear_segmentos_con_scraping_batch(list_id: int, segmentos_nombres: List[str], api_client: API) -> bool:
    """
    Crea múltiples segmentos en Acumbamail usando scraping de Playwright.
    Optimizado para verificar existencia via API antes de crear con scraping.
    
    Args:
        list_id: ID de la lista en Acumbamail
        segmentos_nombres: Lista de nombres de segmentos únicos a crear
        api_client: Cliente de API para verificar segmentos existentes
        
    Returns:
        True si todos los segmentos se crearon exitosamente o ya existían
    """
    if not segmentos_nombres:
        logger.info("No hay segmentos para crear")
        print("  ℹ️  No hay segmentos para crear")
        return True
        
    logger.info(f"Verificando segmentos existentes para lista {list_id}")
    print(f"  🔍 Verificando segmentos existentes en lista {list_id}...")
    
    # Verificar qué segmentos ya existen usando la API
    try:
        segmentos_existentes = api_client.suscriptores.get_list_segments(list_id)
        # Los segmentos pueden venir como tuplas (name, id) o como objetos con atributo name
        if segmentos_existentes:
            nombres_existentes = []
            for seg in segmentos_existentes:
                if isinstance(seg, tuple):
                    nombres_existentes.append(seg[0])  # Primer elemento de la tupla es el nombre
                elif hasattr(seg, 'name'):
                    nombres_existentes.append(seg.name)
                else:
                    nombres_existentes.append(str(seg))
        else:
            nombres_existentes = []
            
        logger.info(f"Segmentos existentes: {nombres_existentes}")
        
        # Filtrar solo los segmentos que no existen
        segmentos_por_crear = [nombre for nombre in segmentos_nombres if nombre not in nombres_existentes]
        segmentos_ya_existentes = [nombre for nombre in segmentos_nombres if nombre in nombres_existentes]
        
        # Mostrar información detallada al usuario
        if segmentos_ya_existentes:
            print(f"  ✅ {len(segmentos_ya_existentes)} segmento(s) ya existe(n): {segmentos_ya_existentes}")
        
        if not segmentos_por_crear:
            logger.info("Todos los segmentos ya existen")
            print(f"  ✅ Todos los segmentos ya existen, no es necesario crear ninguno")
            return True
            
        print(f"  🚀 Creando {len(segmentos_por_crear)} segmento(s) nuevo(s): {segmentos_por_crear}")
        logger.info(f"Creando {len(segmentos_por_crear)} segmentos nuevos: {segmentos_por_crear}")
    except Exception as e:
        logger.warning(f"Error verificando segmentos existentes: {e}. Procederé a crear todos los segmentos.")
        print(f"  ⚠️  Error verificando segmentos existentes. Creando todos los segmentos por seguridad.")
        segmentos_por_crear = segmentos_nombres
        segmentos_ya_existentes = []
    
    # Crear cada segmento individualmente usando scraping
    exito_total = True
    segmentos_creados = 0
    
    for i, nombre_segmento in enumerate(segmentos_por_crear):
        print(f"      📝 Creando segmento {i+1}/{len(segmentos_por_crear)}: '{nombre_segmento}'")
        logger.info(f"Creando segmento {i+1}/{len(segmentos_por_crear)}: {nombre_segmento}")
        
        # Crear el segmento individual
        exito = crear_segmento_con_scraping(list_id, nombre_segmento, api_client)
        
        if not exito:
            print(f"      ❌ Error creando segmento '{nombre_segmento}'")
            logger.error(f"Error creando segmento '{nombre_segmento}'")
            exito_total = False
        else:
            print(f"      ✅ Segmento '{nombre_segmento}' creado exitosamente")
            logger.info(f"✅ Segmento '{nombre_segmento}' creado exitosamente")
            segmentos_creados += 1
            
        # Si hay más segmentos por crear, hacer una pequeña pausa
        if i < len(segmentos_por_crear) - 1:
            logger.info("Esperando antes del siguiente segmento...")
            import time
            time.sleep(2)
    
    # Mostrar resumen final
    total_segmentos = len(segmentos_nombres)
    existentes = len(segmentos_ya_existentes) if 'segmentos_ya_existentes' in locals() else 0
    
    print(f"  📊 Resumen de segmentos:")
    print(f"      • Total solicitados: {total_segmentos}")
    print(f"      • Ya existían: {existentes}")
    print(f"      • Creados nuevos: {segmentos_creados}")
    print(f"      • Errores: {len(segmentos_por_crear) - segmentos_creados}")
    
    return exito_total

def procesar_lista_individual(nombre_lista: str, segmentos_data: List[List[Any]], headers: List[str]) -> bool:
    """
    Procesa una lista individual aplicando todos sus segmentos usando la API de Acumbamail.

    Args:
        nombre_lista: Nombre de la lista a procesar
        segmentos_data: Datos de segmentos para esta lista
        headers: Headers de las columnas

    Returns:
        True si se procesó exitosamente
    """
    logger.info(f"Procesando lista: {nombre_lista}")

    try:
        # Configurar cliente API
        config = load_config()
        api_client = API()

        # Buscar ID de la lista en Acumbamail
        list_id = obtener_id_lista_por_nombre(nombre_lista, api_client)
        if not list_id:
            # Si no existe, crear la lista en Acumbamail
            logger.info(f"Lista '{nombre_lista}' no existe en Acumbamail. Creando...")
            print(f"📝 Lista '{nombre_lista}' no existe. Creando en Acumbamail...")

            try:
                # Obtener configuración para creación de lista
                lista_config = config.get('lista', {})

                list_id = api_client.suscriptores.create_list(
                    sender_email=lista_config.get('sender_email', 'correo@empresa.com'),
                    name=nombre_lista,
                    company=lista_config.get('company', 'Empresa'),
                    country=lista_config.get('country', 'España'),
                    city=lista_config.get('city', 'Madrid'),
                    address=lista_config.get('address', 'Dirección'),
                    phone=lista_config.get('phone', '+34 900 000 000')
                )

                logger.info(f"Lista '{nombre_lista}' creada exitosamente con ID: {list_id}")
                print(f"✅ Lista '{nombre_lista}' creada exitosamente (ID: {list_id})")

            except Exception as e:
                logger.error(f"Error creando lista '{nombre_lista}': {e}")
                print(f"❌ Error creando lista '{nombre_lista}': {e}")
                return False

        print(f"📋 Lista encontrada: {nombre_lista} (ID: {list_id})")

        # Verificar y crear campos necesarios
        if not verificar_y_crear_campos_segmentacion(list_id, headers, api_client):
            logger.error(f"No se pudieron crear los campos necesarios para lista {nombre_lista}")
            return False

        # Obtener usuarios existentes en Acumbamail
        usuarios_existentes = obtener_usuarios_existentes_con_segmentos(list_id, api_client)

        # Obtener TODOS los usuarios de la lista (no solo los que tienen segmentos)
        try:
            todos_usuarios_acumba = api_client.suscriptores.get_subscribers(list_id, all_fields=1, complete_json=1)
            emails_en_acumba = {usuario.email for usuario in todos_usuarios_acumba}
            logger.info(f"Encontrados {len(emails_en_acumba)} usuarios en Acumbamail")
        except Exception as e:
            # Lista recién creada o vacía - esto es normal
            if "No subscribers" in str(e):
                logger.info(f"Lista {list_id} está vacía (recién creada)")
                emails_en_acumba = set()
            else:
                logger.warning(f"Error obteniendo usuarios de Acumbamail: {e}")
                emails_en_acumba = set()

        # Obtener ruta del archivo local
        ruta_archivo = obtener_ruta_archivo_lista(nombre_lista)

        # Verificar si el archivo local existe
        if not os.path.exists(ruta_archivo):
            logger.warning(f"Archivo local no existe: {ruta_archivo}")
            # Crear archivo básico con estructura mínima
            columnas_base = ['email'] + headers[1:]  # email + columnas de segmentación
            df_vacio = pd.DataFrame(columns=columnas_base)
            if not ExcelHelper.escribir_excel(df_vacio, ruta_archivo):
                logger.error(f"No se pudo crear archivo para lista {nombre_lista}")
                return False
            logger.info(f"Creado archivo nuevo para lista: {nombre_lista}")
            return True  # Archivo vacío creado, procesamiento completado

        # Leer archivo existente
        df = ExcelHelper.leer_excel(ruta_archivo)

        if df.empty:
            logger.warning(f"Lista {nombre_lista} está vacía")
            return True

        # Verificar compatibilidad para segmentación
        es_compatible, columnas_disponibles = verificar_columnas_compatibles(df, headers)

        # Si no es compatible pero tiene email, subir usuarios sin segmentación
        if not es_compatible:
            if 'email' in df.columns:
                print(f"⚠️  Lista {nombre_lista} no tiene columnas para segmentación, pero se subirán los usuarios")

                # Identificar usuarios nuevos
                emails_locales = set(df['email'].dropna())
                usuarios_nuevos = emails_locales - emails_en_acumba

                if usuarios_nuevos:
                    print(f"📤 Subiendo {len(usuarios_nuevos)} usuarios nuevos a Acumbamail...")
                    df_nuevos = df[df['email'].isin(usuarios_nuevos)]
                    usuarios_subidos = subir_usuarios_actualizados(df_nuevos, list_id, api_client)
                    print(f"✅ {usuarios_subidos} usuarios nuevos subidos")

                logger.info(f"Lista {nombre_lista} procesada sin segmentación")
                return True
            else:
                columnas_faltantes = ['email'] + [h for h in headers[1:] if h not in df.columns]
                error_msg = f"Lista {nombre_lista} no es compatible. Faltan columnas: {', '.join(columnas_faltantes)}. Columnas disponibles: {', '.join(df.columns.tolist())}"
                logger.warning(error_msg)
                print(f"❌ {error_msg}")
                return False

        logger.info(f"Lista {nombre_lista}: {len(df)} filas, columnas disponibles: {columnas_disponibles}")

        # Identificar y subir usuarios nuevos antes de la segmentación
        emails_locales = set(df['email'].dropna())
        usuarios_nuevos = emails_locales - emails_en_acumba

        if usuarios_nuevos:
            print(f"📤 Subiendo {len(usuarios_nuevos)} usuarios nuevos a Acumbamail...")
            df_nuevos = df[df['email'].isin(usuarios_nuevos)]
            usuarios_subidos = subir_usuarios_actualizados(df_nuevos, list_id, api_client)
            print(f"✅ {usuarios_subidos} usuarios nuevos subidos")

        # Guardar estado original para detectar cambios
        df_original = df.copy()

        # Procesar cada segmento
        total_modificaciones = 0
        usuarios_a_eliminar = set()
        usuarios_a_subir = []
        # Usar un conjunto para evitar duplicados desde el principio
        segmentos_creados = set()

        for segmento_condiciones in segmentos_data:
            nombre_segmento = segmento_condiciones[0]

            logger.info(f"Aplicando segmento: {nombre_segmento}")

            # Aplicar condiciones
            mask = aplicar_condiciones_segmento(df, segmento_condiciones, headers)

            if mask.any():
                # Actualizar segmentos
                df, filas_modificadas = actualizar_columna_segmentos(df, mask, nombre_segmento)
                total_modificaciones += len(filas_modificadas)

                # Marcar usuarios para re-subir
                for idx in filas_modificadas:
                    email = df.loc[idx, 'email']
                    usuarios_a_eliminar.add(email)

                print(f"  ✅ Segmento '{nombre_segmento}': {len(filas_modificadas)} usuarios asignados")
                
                # Agregar a la lista de segmentos únicos que necesitan ser creados en Acumbamail
                segmentos_creados.add(nombre_segmento)
                
            else:
                print(f"  ⚠️  Segmento '{nombre_segmento}': 0 usuarios cumplen las condiciones")
                logger.warning(f"No hay usuarios que cumplan las condiciones para el segmento '{nombre_segmento}': {segmento_condiciones}")

        # Detectar cambios
        df_cambios = detectar_cambios_segmentos(df_original, df)

        # Procesar usuarios que cambiaron de segmento
        if usuarios_a_eliminar:
            print(f"🔄 Actualizando {len(usuarios_a_eliminar)} usuarios en Acumbamail...")

            # Eliminar usuarios que cambiaron
            emails_a_eliminar = list(usuarios_a_eliminar)
            if eliminar_usuarios_de_lista(emails_a_eliminar, list_id, api_client):
                print(f"  ✅ Eliminados {len(emails_a_eliminar)} usuarios para actualización")

                # Preparar datos de usuarios para re-subir
                df_usuarios_actualizados = df[df['email'].isin(emails_a_eliminar)]

                # Subir usuarios actualizados
                usuarios_subidos = subir_usuarios_actualizados(df_usuarios_actualizados, list_id, api_client)
                print(f"  ✅ Re-subidos {usuarios_subidos} usuarios con segmentos actualizados")

        # Guardar archivo principal local
        if total_modificaciones > 0:
            if ExcelHelper.escribir_excel(df, ruta_archivo, 'Datos', reemplazar=True):
                logger.info(f"Guardado archivo principal: {nombre_lista} ({total_modificaciones} modificaciones)")
            else:
                logger.error(f"Error guardando archivo principal: {nombre_lista}")
                return False

        # Guardar hoja de cambios si hay cambios
        if not df_cambios.empty:
            if ExcelHelper.escribir_excel(df_cambios, ruta_archivo, 'Cambios', reemplazar=False):
                logger.info(f"Guardada hoja de cambios: {nombre_lista} ({len(df_cambios)} cambios)")
            else:
                logger.warning(f"Error guardando hoja de cambios: {nombre_lista}")

        print(f"📊 Lista '{nombre_lista}' procesada: {total_modificaciones} modificaciones, {len(df_cambios)} cambios detectados")

        # Crear segmentos en Acumbamail (verificando existencia primero)
        if segmentos_creados:
            # Convertir el conjunto a lista ordenada para procesamiento
            segmentos_unicos = sorted(list(segmentos_creados))
            print(f"🎯 Procesando {len(segmentos_unicos)} segmento(s) únicos: {segmentos_unicos}")
            
            # Usar la función batch que verifica existencia y maneja múltiples segmentos
            exito_segmentos = crear_segmentos_con_scraping_batch(list_id, segmentos_unicos, api_client)
            
            if exito_segmentos:
                print(f"  ✅ Procesamiento de segmentos completado exitosamente")
            else:
                print(f"  ⚠️  Algunos segmentos pudieron no haberse procesado correctamente")
                logger.warning(f"Error procesando algunos segmentos para lista '{nombre_lista}'")
        else:
            print("  ℹ️  No hay segmentos nuevos para crear")

        # Cerrar conexión API
        # No client to close for API class

        return True

    except Exception as e:
        logger.error(f"Error procesando lista {nombre_lista}: {e}")
        print(f"❌ Error procesando lista '{nombre_lista}': {e}")
        return False

def mapear_segmentos_completo() -> Dict[str, Any]:
    """
    Función principal para mapear todos los segmentos.

    Returns:
        Diccionario con estadísticas del proceso
    """
    logger.info("Iniciando mapeo completo de segmentos")

    # Verificar que existe el archivo de segmentos
    if not os.path.exists(ARCHIVO_SEGMENTOS):
        logger.error(f"Archivo de segmentos no encontrado: {ARCHIVO_SEGMENTOS}")
        return {"error": "Archivo de segmentos no encontrado"}

    print("🔄 Iniciando mapeo de segmentos...")

    # Procesar archivo de segmentos
    headers, grouped_data = procesar_excel_segmentos(ARCHIVO_SEGMENTOS)

    if not grouped_data:
        logger.warning("No se encontraron datos de segmentos para procesar")
        return {"error": "No hay datos de segmentos para procesar"}

    print(f"📋 Encontradas {len(grouped_data)} lista(s) con segmentos:")
    for lista_info in grouped_data:
        nombre_lista = lista_info[0]
        segmentos = lista_info[1]
        print(f"  • {nombre_lista}: {len(segmentos)} segmento(s)")

    # Procesar cada lista
    estadisticas = {
        "listas_procesadas": [],
        "listas_fallidas": [],
        "total_listas": len(grouped_data),
        "headers": headers
    }

    for lista_info in grouped_data:
        nombre_lista = lista_info[0]
        segmentos_data = lista_info[1]

        print(f"\n🔄 Procesando lista: {nombre_lista}")

        if procesar_lista_individual(nombre_lista, segmentos_data, headers):
            estadisticas["listas_procesadas"].append(nombre_lista)
        else:
            estadisticas["listas_fallidas"].append(nombre_lista)

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