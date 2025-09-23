"""
Módulo para descargar listas de suscriptores desde Acumbamail.
Extrae datos de suscriptores de listas marcadas en Busqueda_Listas.xlsx.
"""
import os
import pandas as pd
from typing import List, Dict, Tuple
import re

from .utils import data_path, load_config, crear_contexto_navegador, configurar_navegador, obtener_total_paginas, navegar_siguiente_pagina
from .autentificacion import login
from .logger import get_logger
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError
from .api import API

logger = get_logger()

ARCHIVO_BUSQUEDA_LISTAS = data_path("Busqueda_Listas.xlsx")
DIRECTORIO_LISTAS = data_path("listas")

def extraer_ids_marcados() -> List[Tuple[int, str]]:
    """
    Extrae los IDs de las listas marcadas con 'x' en la primera columna de Busqueda_Listas.xlsx

    Returns:
        Lista de tuplas (id_lista, nombre_lista) marcadas para descarga
    """
    logger.info("Extrayendo IDs marcados de Busqueda_Listas.xlsx")

    if not os.path.exists(ARCHIVO_BUSQUEDA_LISTAS):
        logger.error(f"Archivo no encontrado: {ARCHIVO_BUSQUEDA_LISTAS}")
        return []

    try:
        df = pd.read_excel(ARCHIVO_BUSQUEDA_LISTAS)

        # Verificar columnas necesarias
        columnas_requeridas = ['Buscar', 'ID_LISTA', 'NOMBRE LISTA']
        if not all(col in df.columns for col in columnas_requeridas):
            logger.error(f"Columnas requeridas no encontradas: {columnas_requeridas}")
            return []

        # Filtrar filas marcadas con 'x' en la columna 'Buscar'
        marcadas = df[df['Buscar'].astype(str).str.lower().str.strip() == 'x']

        ids_extraidos = []
        for _, row in marcadas.iterrows():
            id_lista = row['ID_LISTA']
            nombre_lista = row['NOMBRE LISTA']

            if pd.notna(id_lista) and pd.notna(nombre_lista):
                ids_extraidos.append((int(id_lista), str(nombre_lista)))

        logger.info(f"Encontradas {len(ids_extraidos)} listas marcadas para descarga")
        return ids_extraidos

    except Exception as e:
        logger.error(f"Error leyendo archivo Busqueda_Listas.xlsx: {e}")
        return []


def scrape_subscriber_list(page: Page, list_id: int, nombre_lista: str) -> List[Dict[str, str]]:
    """
    Extrae datos de suscriptores de una lista específica usando Playwright con paginación
    Usa los patrones exactos probados de utils.py
    """
    logger.info(f"Iniciando scraping de lista {list_id}: {nombre_lista}")

    url = f"https://acumbamail.com/app/list/{list_id}/subscriber/list/"
    suscriptores = []

    try:
        # Navegar a la página de suscriptores
        logger.info(f"Navegando a: {url}")
        page.goto(url, wait_until="networkidle", timeout=60000)

        # Esperar a que la página se cargue completamente
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(2000)

        # Verificar que la tabla está presente
        table_present = page.locator("ul li").count() > 0
        if not table_present:
            logger.error(f"No se encontró tabla de suscriptores para lista {list_id}")
            return []

        # Usar la función probada de utils.py para obtener total de páginas
        # Esta función ya incluye la optimización automática de elementos por página
        total_paginas = obtener_total_paginas(page)
        logger.info(f"📄 Total de páginas a procesar: {total_paginas}")

        # Procesar cada página usando la navegación probada
        for numero_pagina in range(1, total_paginas + 1):
            logger.info(f"📃 Procesando página {numero_pagina}/{total_paginas}")

            try:
                # Extraer suscriptores de la página actual
                suscriptores_pagina = extraer_suscriptores_tabla_lista(page, nombre_lista, list_id)
                logger.info(f"✅ Página {numero_pagina}: {len(suscriptores_pagina)} suscriptores extraídos")

                suscriptores.extend(suscriptores_pagina)

                # Navegar a siguiente página usando la función probada de utils.py
                if numero_pagina < total_paginas:
                    if not navegar_siguiente_pagina(page, numero_pagina):
                        logger.error(f"No se pudo navegar a página {numero_pagina + 1}")
                        break

            except Exception as e:
                logger.error(f"Error procesando página {numero_pagina}: {e}")
                continue

        logger.info(f"✅ Scraping completado - Total: {len(suscriptores)} suscriptores de lista {list_id}")
        return suscriptores

    except Exception as e:
        logger.error(f"Error en scraping de lista {list_id}: {e}")
        return []

def extraer_suscriptores_tabla_lista(page: Page, nombre_lista: str, list_id: int) -> List[Dict[str, str]]:
    """
    Extrae suscriptores de la tabla responsive de Acumbamail usando selectores modernos de Playwright.
    Basado en la estructura: ul.am-responsive-table > li.am-responsive-table-row
    """
    logger.start_timer("extraer_suscriptores_tabla_lista")
    suscriptores = []

    try:
        print(f"🔍 Extrayendo datos completos de lista: {nombre_lista}")

        # Esperar a que la tabla esté visible
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(2000)

        # Buscar el contenedor principal usando selectores modernos de Playwright
        tabla_container = page.locator("#newsletter-subscribers").or_(
            page.locator("div.am-responsive-table-wrapper")
        ).first

        if tabla_container.count() == 0:
            print("❌ No se encontró el contenedor de la tabla")
            return []

        # Buscar la lista UL principal
        lista_principal = tabla_container.locator("ul.am-responsive-table").first
        
        if lista_principal.count() == 0:
            print("❌ No se encontró la lista principal")
            return []

        # Obtener todas las filas de datos (items, excluyendo header)
        filas_datos = lista_principal.locator("li.item.am-responsive-table-row")
        total_filas = filas_datos.count()
        
        print(f"📊 Total de filas de datos: {total_filas}")

        if total_filas == 0:
            print("⚠️ No hay datos para extraer")
            return []

        # Mapeo de posiciones de columnas basado en la estructura HTML observada
        columnas_map = {
            0: "email",           # Correo electrónico (con checkbox y link)
            1: "estado",          # Estado (span con am-tag)
            2: "fecha_de_alta",   # Fecha de alta
            3: "email_1",         # EMAIL.1 (campo personalizado)
            4: "nuevos_correos",  # NUEVOS CORREOS (campo personalizado)
            5: "sede",            # SEDE (campo personalizado)
            6: "organo",          # ORGANO (campo personalizado)
            7: "n_organo",        # N ORGANO (campo personalizado)
            8: "calidad",         # Calidad (formato XX/100)
            # 9 sería "detalles" (columna de acciones) - la ignoramos
        }

        # Procesar cada fila de datos
        for i in range(total_filas):
            try:
                fila = filas_datos.nth(i)
                suscriptor = {"lista": nombre_lista}

                # Obtener todas las celdas de la fila
                celdas = fila.locator("div.am-responsive-table-cell")
                total_celdas = celdas.count()

                for j in range(total_celdas):
                    try:
                        celda = celdas.nth(j)
                        campo_nombre = columnas_map.get(j, f"campo_{j}")

                        if campo_nombre == "email":
                            # Extraer email del link usando get_by_role moderno
                            link_email = celda.get_by_role("link").or_(celda.locator("a")).first
                            if link_email.count() > 0:
                                email = link_email.inner_text().strip()
                                if email and "@" in email:
                                    suscriptor["email"] = email

                        elif campo_nombre == "estado":
                            # Extraer estado usando localizador por clase
                            estado_tag = celda.locator("span.am-tag")
                            if estado_tag.count() > 0:
                                suscriptor["estado"] = estado_tag.inner_text().strip()

                        elif j < 9:  # Ignorar última columna (detalles/acciones)
                            # Para otros campos, extraer el texto usando get_by_text si es posible
                            # o fallback a span
                            span_texto = celda.locator("span").first
                            if span_texto.count() > 0:
                                texto = span_texto.inner_text().strip()
                                if texto and texto != "":
                                    suscriptor[campo_nombre] = texto

                    except Exception as e:
                        print(f"⚠️ Error en celda {j} de fila {i}: {e}")
                        continue

                # Solo agregar si tiene email válido
                if suscriptor.get("email") and "@" in suscriptor["email"]:
                    suscriptores.append(suscriptor)
                    
                    # Debug: mostrar primeros registros
                    if len(suscriptores) <= 3:
                        print(f"✅ Suscriptor {len(suscriptores)}: {suscriptor}")

            except Exception as e:
                print(f"❌ Error procesando fila {i}: {e}")
                continue

        print(f"📊 Total suscriptores extraídos: {len(suscriptores)}")
        logger.end_timer("extraer_suscriptores_tabla_lista", f"Extraídos {len(suscriptores)} suscriptores")
        return suscriptores

    except Exception as e:
        error_msg = f"Error en extracción: {e}"
        print(f"❌ {error_msg}")
        logger.error(error_msg)
        logger.end_timer("extraer_suscriptores_tabla_lista", "Error")
        return []


def _normalizar_nombre_columna(nombre: str) -> str:
    """
    Normaliza nombres de columnas para crear claves consistentes en los diccionarios
    """
    # Mapeo de nombres comunes a claves estándar
    mapeo = {
        'estado': 'estado',
        'fecha de alta': 'fecha_de_alta',
        'calidad': 'calidad',
        'detalles': 'detalles',
        'email.1': 'email_1',
        'nuevos correos': 'nuevos_correos',
        'sede': 'sede',
        'órgano': 'organo',
        'organo': 'organo',
        'n órgano': 'n_organo',
        'n organo': 'n_organo'
    }

    nombre_lower = nombre.lower().strip()
    return mapeo.get(nombre_lower, nombre_lower.replace(' ', '_').replace('.', '_').replace('ó', 'o').replace('í', 'i'))

def generar_nombre_archivo(nombre_lista: str, list_id: int) -> str:
    """
    Genera nombre de archivo con formato [Nombre Lista]-ID-[ID].xlsx
    Si el archivo existe, agrega sufijo _v1, _v2, etc.

    Args:
        nombre_lista: Nombre de la lista
        list_id: ID de la lista

    Returns:
        Ruta completa del archivo a crear
    """
    # Crear directorio si no existe
    os.makedirs(DIRECTORIO_LISTAS, exist_ok=True)

    # Limpiar nombre de lista para uso en archivos
    nombre_limpio = re.sub(r'[<>:"/\\|?*]', '_', nombre_lista)

    # Formato base
    nombre_base = f"{nombre_limpio}-ID-{list_id}"
    archivo_base = os.path.join(DIRECTORIO_LISTAS, f"{nombre_base}.xlsx")

    # Si no existe, usar nombre base
    if not os.path.exists(archivo_base):
        return archivo_base

    # Si existe, buscar siguiente versión disponible
    contador = 1
    while True:
        nombre_version = f"{nombre_base}_v{contador}.xlsx"
        archivo_version = os.path.join(DIRECTORIO_LISTAS, nombre_version)

        if not os.path.exists(archivo_version):
            return archivo_version

        contador += 1

def generar_archivo_excel(suscriptores: List[Dict[str, str]], nombre_archivo: str) -> bool:
    """
    Genera archivo Excel con los datos de suscriptores con todas las columnas

    Args:
        suscriptores: Lista de datos de suscriptores
        nombre_archivo: Ruta del archivo a crear

    Returns:
        True si se creó exitosamente
    """
    try:
        if not suscriptores:
            logger.warning("No hay datos de suscriptores para generar archivo")
            return False

        # Convertir a DataFrame
        df = pd.DataFrame(suscriptores)

        # Identificar columna de email de forma más robusta
        email_column = None
        for col in df.columns:
            if 'email' in col.lower():
                email_column = col
                break
            # También verificar si alguna fila contiene @ (posible email)
            elif len(df) > 0:
                sample_values = df[col].dropna().astype(str)
                if any('@' in str(val) for val in sample_values.head()):
                    email_column = col
                    break

        # Si no encontramos email, usar la primera columna
        if not email_column and len(df.columns) > 0:
            email_column = df.columns[0]
            logger.warning(f"No se encontró columna de email, usando primera columna: {email_column}")

        # Reordenar columnas: email primero, luego todas las demás alfabéticamente
        if email_column:
            todas_columnas = [col for col in df.columns if col != email_column]
            todas_columnas.sort()
            columnas_ordenadas = [email_column] + todas_columnas
            df = df.reindex(columns=columnas_ordenadas)

        # Renombrar columnas para formato legible
        nuevos_nombres = []
        for col in df.columns:
            if col == email_column:
                nuevos_nombres.append('Correo Electrónico')
            else:
                # Formatear nombres de columnas dinámicamente
                nombre_formateado = col.replace('_', ' ')
                palabras = nombre_formateado.split()
                palabras_formateadas = []

                for palabra in palabras:
                    # Mantener acrónimos como EMAIL, SEDE, etc. en mayúsculas
                    if palabra.isupper() and len(palabra) > 1:
                        palabras_formateadas.append(palabra)
                    else:
                        palabras_formateadas.append(palabra.capitalize())

                nombre_final = ' '.join(palabras_formateadas)
                nuevos_nombres.append(nombre_final)

        df.columns = nuevos_nombres

        # Crear directorio si no existe
        os.makedirs(os.path.dirname(nombre_archivo), exist_ok=True)

        # Guardar archivo Excel
        df.to_excel(nombre_archivo, index=False)

        logger.info(f"✅ Archivo Excel creado: {nombre_archivo} con {len(suscriptores)} suscriptores")
        print(f"✅ Archivo guardado: {os.path.basename(nombre_archivo)}")
        return True

    except Exception as e:
        logger.error(f"Error creando archivo Excel {nombre_archivo}: {e}")
        print(f"❌ Error creando archivo Excel: {e}")
        return False

def obtener_suscriptores_via_scraping(page: Page, list_id: int, nombre_lista: str) -> List[Dict[str, str]]:
    """
    Obtiene suscriptores de la lista usando scraping web con Playwright.
    Usa los patrones probados de utils.py para paginación optimizada.
    """
    resultado: List[Dict[str, str]] = []
    try:
        logger.info(f"🔍 Iniciando scraping para lista {list_id}: {nombre_lista}")
        
        # Navegar a la URL de la lista
        url = f"https://acumbamail.com/app/list/{list_id}/subscriber/list/"
        logger.info(f"📍 Navegando a: {url}")
        
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(2000)

        # Usar la función probada de utils.py para obtener total de páginas
        # Esta función ya incluye la optimización de elementos por página
        total_paginas = obtener_total_paginas(page)
        logger.info(f"📄 Total de páginas a procesar: {total_paginas}")

        # Procesar cada página usando la navegación probada de utils.py
        for numero_pagina in range(1, total_paginas + 1):
            try:
                logger.info(f"📃 Procesando página {numero_pagina}/{total_paginas}")
                
                # Extraer datos de la página actual
                datos_pagina = extraer_suscriptores_tabla_lista(page, nombre_lista, list_id)
                
                if datos_pagina:
                    resultado.extend(datos_pagina)
                    logger.info(f"✅ Página {numero_pagina}: {len(datos_pagina)} suscriptores extraídos")
                else:
                    logger.warning(f"⚠️ Página {numero_pagina}: No se extrajeron datos")

                # Navegar a la siguiente página usando la función probada de utils.py
                if numero_pagina < total_paginas:
                    exito_navegacion = navegar_siguiente_pagina(page, numero_pagina)
                    if not exito_navegacion:
                        logger.error(f"❌ No se pudo navegar a página {numero_pagina + 1}")
                        break

            except Exception as e:
                logger.error(f"❌ Error procesando página {numero_pagina}: {e}")
                # Continuar con la siguiente página en caso de error
                continue

        logger.info(f"✅ Scraping completado - Total: {len(resultado)} suscriptores de lista {list_id}")
        return resultado

    except Exception as e:
        logger.error(f"❌ Error en scraping de lista {list_id}: {e}")
        return []

def procesar_lista_individual(page: Page, list_id: int, nombre_lista: str) -> bool:
    """
    Procesa una lista individual completa: scraping + generación de archivo

    Args:
        page: Página de Playwright autenticada
        list_id: ID de la lista
        nombre_lista: Nombre de la lista

    Returns:
        True si se procesó exitosamente
    """
    logger.info(f"Procesando lista {list_id}: {nombre_lista}")

    try:
        # 1) Usar scraping como método principal para obtener todos los campos
        suscriptores = obtener_suscriptores_via_scraping(page, list_id, nombre_lista)

        # 2) Fallback a extracción básica si el scraping completo falla
        if not suscriptores:
            logger.info("Scraping completo falló, intentando extracción básica...")
            suscriptores = scrape_subscriber_list(page, list_id, nombre_lista)

        if not suscriptores:
            logger.warning(f"No se obtuvieron datos para lista {list_id}")
            return False

        # Generar archivo
        nombre_archivo = generar_nombre_archivo(nombre_lista, list_id)
        exitoso = generar_archivo_excel(suscriptores, nombre_archivo)

        if exitoso:
            print(f"✅ Lista {nombre_lista} (ID: {list_id}): {len(suscriptores)} suscriptores → {os.path.basename(nombre_archivo)}")
        else:
            print(f"❌ Error generando archivo para lista {nombre_lista}")

        return exitoso

    except Exception as e:
        logger.error(f"Error procesando lista {list_id}: {e}")
        print(f"❌ Error procesando lista {nombre_lista}: {e}")
        return False

def main():
    """
    Función principal para descargar todas las listas marcadas
    """
    logger.info("Iniciando descarga de listas de suscriptores")
    print("🔄 Iniciando descarga de listas de suscriptores...")

    try:
        # Cargar configuración
        config = load_config()
        headless = bool(config.get("headless", False))

        # Extraer IDs marcados
        ids_marcados = extraer_ids_marcados()

        if not ids_marcados:
            print("❌ No se encontraron listas marcadas para descarga")
            print("💡 Marca las listas que deseas descargar con 'x' en la columna 'Buscar' de Busqueda_Listas.xlsx")
            return

        print(f"📋 Encontradas {len(ids_marcados)} lista(s) marcadas:")
        for list_id, nombre in ids_marcados:
            print(f"  • {nombre} (ID: {list_id})")

        # Configurar Playwright
        with sync_playwright() as p:
            browser = configurar_navegador(p, headless)
            context = crear_contexto_navegador(browser, headless)
            page = context.new_page()

            # Autenticación
            login(page, context=context)

            # Procesar cada lista
            exitosas = 0
            fallidas = 0

            for list_id, nombre_lista in ids_marcados:
                print(f"\n🔄 Procesando {exitosas + fallidas + 1}/{len(ids_marcados)}: {nombre_lista}")

                if procesar_lista_individual(page, list_id, nombre_lista):
                    exitosas += 1
                else:
                    fallidas += 1

            # Cerrar navegador
            browser.close()

            # Resumen final
            print("\n📊 Resumen de descarga:")
            print(f"   ✅ Exitosas: {exitosas}")
            print(f"   ❌ Fallidas: {fallidas}")
            print(f"   📁 Archivos guardados en: {DIRECTORIO_LISTAS}")

            if exitosas > 0:
                print("🎉 Descarga completada exitosamente")
            else:
                print("⚠️ No se pudieron descargar listas")

            logger.info(f"Descarga completada: {exitosas} exitosas, {fallidas} fallidas")

    except Exception as e:
        logger.error(f"Error en proceso principal: {e}")
        print(f"❌ Error durante la descarga: {e}")

if __name__ == "__main__":
    main()