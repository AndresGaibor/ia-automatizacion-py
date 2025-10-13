"""
Módulo para descargar listas de suscriptores desde Acumbamail.
Extrae datos de suscriptores de listas marcadas en Busqueda_Listas.xlsx.
"""
import os
import pandas as pd
from typing import List, Dict, Tuple
import re
from pathlib import Path
import sys

# Configurar package para imports consistentes y PyInstaller compatibility
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "src"

from .utils import data_path, load_config, crear_contexto_navegador, configurar_navegador, obtener_total_paginas, navegar_siguiente_pagina
from .autentificacion import login
from .logger import get_logger
from playwright.sync_api import sync_playwright, Page

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
    Extrae suscriptores de la tabla de Acumbamail usando selectores CSS estándar.
    Detecta automáticamente todas las columnas basándose en la estructura HTML real.
    """
    logger.start_timer("extraer_suscriptores_tabla_lista")
    suscriptores = []

    try:
        print(f"🔍 Extrayendo datos completos de lista: {nombre_lista}")

        # Esperar a que la tabla esté visible
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(2000)

        # Buscar la tabla usando JavaScript con enfoque directo en la estructura HTML
        resultado = page.evaluate("""
            () => {
                // Buscar todas las listas UL
                const listas = document.querySelectorAll('ul');

                // Buscar la lista que contenga enlaces de suscriptores
                let listaTabla = null;
                for (let ul of listas) {
                    const items = ul.querySelectorAll('li');
                    if (items.length > 5) {
                        const enlaces = ul.querySelectorAll('a[href*="subscriber/detail"]');
                        if (enlaces.length > 0) {
                            listaTabla = ul;
                            break;
                        }
                    }
                }

                if (!listaTabla) return { error: "No se encontró la tabla de suscriptores" };

                const filas = listaTabla.querySelectorAll('li');

                // Extraer encabezados de la primera fila usando spans y divs específicos
                const encabezados = [];
                if (filas.length > 0) {
                    const filaHeader = filas[0];

                    // Buscar spans que contengan texto de encabezados (excluyendo botones y controles)
                    const elementos = filaHeader.querySelectorAll('span, div');
                    for (let elem of elementos) {
                        const text = elem.textContent.trim();
                        // Filtrar solo los textos que parecen encabezados de columna
                        if (text && text.length > 2 && text.length < 50 &&
                            !text.includes('checkbox') && !text.includes('button') &&
                            !text.match(/^\\d+$/) && !encabezados.includes(text)) {
                            encabezados.push(text);
                        }
                    }
                }

                // Extraer datos de cada fila de manera más directa evitando duplicados
                const datosFilas = [];
                const emailsYaProcesados = new Set();

                for (let i = 1; i < filas.length; i++) {
                    const fila = filas[i];

                    // Buscar email en los enlaces para identificar filas de suscriptores reales
                    const linkEmail = fila.querySelector('a[href*="subscriber/detail"]');
                    let emailEncontrado = null;
                    if (linkEmail) {
                        emailEncontrado = linkEmail.textContent.trim();
                    }

                    // Solo procesar si hay email y no lo hemos procesado antes
                    if (!emailEncontrado || emailsYaProcesados.has(emailEncontrado)) {
                        continue;
                    }

                    emailsYaProcesados.add(emailEncontrado);

                    // Extraer datos usando selectores más específicos
                    const celdas = [];

                    // Método 1: Buscar spans que contengan los datos (excluyendo controles)
                    const spans = fila.querySelectorAll('span');
                    for (let span of spans) {
                        const text = span.textContent.trim();
                        if (text && text.length > 0 &&
                            !text.includes('checkbox') && !text.includes('button') &&
                            !text.includes('Ver') && !text.includes('Editar') &&
                            !text.includes('Eliminar') && !text.includes('✓') &&
                            !text.includes('×') && !text.match(/^\\d+$/) && text.length < 100) {
                            celdas.push(text);
                        }
                    }

                    // Si no hay suficientes celdas con spans, intentar con divs
                    if (celdas.length < 5) {
                        const divs = fila.querySelectorAll('div');
                        for (let div of divs) {
                            const text = div.textContent.trim();
                            if (text && text.length > 0 &&
                                !text.includes('checkbox') && !text.includes('button') &&
                                !text.includes('Ver') && !text.includes('Editar') &&
                                !text.includes('Eliminar') && !text.includes('✓') &&
                                !text.includes('×') && !text.match(/^\\d+$/) &&
                                !celdas.includes(text) && text.length < 100) {
                                celdas.push(text);
                            }
                        }
                    }

                    datosFilas.push({
                        email: emailEncontrado,
                        textos: celdas
                    });
                }

                return {
                    totalFilas: filas.length,
                    encabezados: encabezados,
                    datosFilas: datosFilas,
                    debug: {
                        primeraFilaDatos: datosFilas.length > 0 ? datosFilas[0] : null
                    }
                };
            }
        """)

        if resultado.get("error"):
            print(f"❌ {resultado['error']}")
            return []

        encabezados = resultado["encabezados"]
        datos_filas = resultado["datosFilas"]
        total_filas = resultado["totalFilas"]

        print(f"📊 Total de filas encontradas: {total_filas}")
        print(f"📋 {len(encabezados)} encabezados detectados:")
        for i, header in enumerate(encabezados):
            nombre_normalizado = _normalizar_nombre_columna(header)
            print(f"   {i}: '{header}' -> '{nombre_normalizado}'")

        # Debug información de la primera fila
        debug_info = resultado.get("debug", {})
        primera_fila = debug_info.get("primeraFilaDatos")
        if primera_fila:
            print("🔍 DEBUG - Primera fila de datos:")
            print(f"   Email: {primera_fila.get('email', 'NO ENCONTRADO')}")
            print(f"   Textos ({len(primera_fila.get('textos', []))}):")
            for j, texto in enumerate(primera_fila.get('textos', [])):
                print(f"      {j}: '{texto}'")

        print(f"📊 Procesando {len(datos_filas)} filas de datos...")

        # Procesar cada fila de datos
        for fila_idx, datos_fila in enumerate(datos_filas):
            try:
                suscriptor = {"lista": nombre_lista}

                # Agregar el email si se encontró
                if datos_fila["email"] and "@" in datos_fila["email"]:
                    suscriptor["email"] = datos_fila["email"]

                # Mapear textos con encabezados (excluyendo el email que ya está procesado)
                textos = datos_fila["textos"]

                # Estrategia de mapeo inteligente - saltar el primer header (email) ya que ya lo tenemos
                texto_idx = 0
                for i, header in enumerate(encabezados):
                    nombre_columna = _normalizar_nombre_columna(header)

                    # Saltar el email - ya se agregó arriba
                    if nombre_columna == "correo_electronico":
                        continue

                    # Para otros campos, mapear con los textos disponibles
                    if texto_idx < len(textos):
                        valor = textos[texto_idx]
                        if valor and valor != "" and valor != "0" and valor != suscriptor.get("email", ""):
                            suscriptor[nombre_columna] = valor
                        texto_idx += 1

                # Solo agregar si tiene email válido
                if suscriptor.get("email") and "@" in suscriptor["email"]:
                    suscriptores.append(suscriptor)

                    # Debug: mostrar primeros registros
                    if len(suscriptores) <= 3:
                        print(f"✅ Suscriptor {len(suscriptores)}: {suscriptor}")

                # Progreso cada 50 registros
                if (fila_idx + 1) % 50 == 0:
                    print(f"   📊 Procesadas {fila_idx + 1}/{len(datos_filas)} filas, {len(suscriptores)} suscriptores extraídos")

            except Exception as e:
                print(f"❌ Error procesando fila {fila_idx}: {e}")
                continue

        print(f"📊 Total suscriptores extraídos: {len(suscriptores)} de {len(datos_filas)} filas de datos")
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
    Normaliza nombres de columnas para crear claves consistentes en los diccionarios.
    Incluye mapeo completo basado en la estructura real de Acumbamail.
    """
    # Mapeo de nombres completos observados en la tabla real
    mapeo = {
        'correo electrónico': 'correo_electronico',
        'correo electronico': 'correo_electronico',
        'estado': 'estado',
        'fecha de alta': 'fecha_de_alta',
        'n organo': 'n_organo',
        'n órgano': 'n_organo',
        'observaciones': 'observaciones',
        'creacion': 'creacion',
        'creación': 'creacion',
        'activo (si/no)': 'activo_si_no',
        'activo si/no': 'activo_si_no',
        'perfil usuario': 'perfil_usuario',
        'funcion usuario': 'funcion_usuario',
        'función usuario': 'funcion_usuario',
        'id': 'id',
        'primer apellido': 'primer_apellido',
        'segundo apellido': 'segundo_apellido',
        'login': 'login',
        'rol usuario': 'rol_usuario',
        'fecha revision': 'fecha_revision',
        'fecha revisión': 'fecha_revision',
        'sede': 'sede',
        'organo': 'organo',
        'órgano': 'organo',
        'nombre': 'nombre',
        'calidad': 'calidad',
        'detalles': 'detalles'
    }

    nombre_lower = nombre.lower().strip()
    nombre_normalizado = mapeo.get(nombre_lower)

    if nombre_normalizado:
        return nombre_normalizado

    # Si no está en el mapeo, normalizar automáticamente
    resultado = nombre_lower
    resultado = resultado.replace(' ', '_')
    resultado = resultado.replace('.', '_')
    resultado = resultado.replace('(', '')
    resultado = resultado.replace(')', '')
    resultado = resultado.replace('/', '_')
    resultado = resultado.replace('ó', 'o')
    resultado = resultado.replace('í', 'i')
    resultado = resultado.replace('á', 'a')
    resultado = resultado.replace('é', 'e')
    resultado = resultado.replace('ú', 'u')
    resultado = resultado.replace('ñ', 'n')

    return resultado

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