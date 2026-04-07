import sys
from pathlib import Path

# Configurar package para imports consistentes y PyInstaller compatibility
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "src"

from .excel_utils import agregar_datos, crear_o_cargar_libro_excel, obtener_o_crear_hoja, limpiar_hoja_desde_fila
from .shared.utils.legacy_utils import data_path, notify
from .shared.logging.logger import get_logger
from .utils import (
    crear_contexto_navegador,
    configurar_navegador,
    navegar_a_reportes,
    obtener_total_paginas,
    navegar_siguiente_pagina,
)
from .autentificacion import login, manejar_popup_cookies
from .infrastructure.api import API
from .shared.utils.legacy_utils import is_on_login_page
from .core.authentication.exceptions import SessionExpiredError, AuthenticationFailedError

from playwright.sync_api import sync_playwright, Page
import re
import time
from functools import wraps

# Rutas
ARCHIVO_BUSQUEDA = data_path("Busqueda.xlsx")

logger = get_logger()


def with_session_retry(max_retries: int = 2):
    """
    Decorator para manejo de expiración de sesión con reintentos automáticos.

    Args:
            max_retries: Número máximo de reintentos después de re-autenticación
    """

    def decorator(func):
        @wraps(func)
        def wrapper(page, *args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    # Verificar si estamos en página de login antes de ejecutar
                    if attempt > 0 and is_on_login_page(page):
                        logger.warning(f"🔄 Sesión expirada detectada (intento {attempt + 1}), re-autenticando...")

                        # Importar login aquí para evitar import circular
                        from .autentificacion import login

                        # Necesitamos el contexto para re-autenticar - usar el contexto de la página
                        context = page.context

                        # Re-autenticar agresivamente con manejo de cookies
                        login(page, context)

                        logger.success(f"✅ Re-autenticación completada (intento {attempt + 1})")

                        # Navegar de vuelta a reportes si es necesario
                        navegar_a_reportes(page)
                        logger.info("📊 Navegación a reportes post re-autenticación completada")

                    # Ejecutar la función original
                    result = func(page, *args, **kwargs)

                    # Si llegamos aquí, todo fue exitoso
                    if attempt > 0:
                        logger.success(f"✅ Operación recuperada exitosamente después de {attempt} reintentos")

                    return result

                except Exception as e:
                    last_exception = e
                    error_msg = str(e).lower()

                    # Verificar si es un error de sesión
                    is_session_error = (
                        "session expired" in error_msg
                        or "login" in error_msg
                        or "unauthorized" in error_msg
                        or "timeout" in error_msg
                        or is_on_login_page(page)
                    )

                    if is_session_error and attempt < max_retries:
                        logger.warning(f"⚠️ Error de sesión detectado en intento {attempt + 1}: {e}")
                        logger.info(f"🔄 Reintentando operación después de re-autenticación...")
                        time.sleep(2)  # Pequeña espera antes de reintentar
                        continue
                    else:
                        # Si no es error de sesión o ya no hay reintentos, propagar el error
                        logger.error(f"❌ Error en operación (intento {attempt + 1}): {e}")
                        break

            # Si llegamos aquí, todos los intentos fallaron
            raise last_exception

        return wrapper

    return decorator


def extraer_id_de_url(url: str) -> str:
    """
    Extrae el ID de campaña de una URL

    Ejemplo: /report/campaign/12345/ -> 12345
    """
    match = re.search(r"/campaign/(\d+)", url)
    if match:
        return match.group(1)
    return ""


def extraer_datos_campania_de_listitem(listitem_locator, page: Page) -> list[str]:
    """
    Extrae los datos de una campaña desde un listitem usando selectores modernos de Playwright

    Args:
        listitem_locator: Locator del listitem de la página de informes
        page: Página de Playwright

    Returns:
        Lista con los datos: ['', nombre, id, fecha, total_enviado, abierto, no_abierto]
    """
    try:
        logger.debug("🔍 Iniciando extracción de datos de listitem con selectores modernos")

        # 1. NOMBRE DE CAMPAÑA (primer link con href /report/campaign/)
        campaign_link = listitem_locator.locator('a[href*="/report/campaign/"]').first
        if campaign_link.count() == 0:
            logger.warning("⚠️ No se encontró link de campaña")
            return []

        nombre = campaign_link.inner_text().strip()
        href = campaign_link.get_attribute("href") or ""
        id_campania = extraer_id_de_url(href)

        logger.debug(f"📝 Nombre: {nombre}, ID: {id_campania}")

        # 2. FECHA (tercer div.am-responsive-table-cell)
        fecha_cell = listitem_locator.locator("div.am-responsive-table-cell").nth(2)
        fecha = fecha_cell.locator("span").inner_text().strip()
        logger.debug(f"📅 Fecha: {fecha}")

        # 3. TOTAL ENVIADO (quinto div = índice 4)
        # Puede ser <a> o texto plano dentro de <span>
        emails_cell = listitem_locator.locator("div.am-responsive-table-cell").nth(4)
        emails_link = emails_cell.locator("a")
        if emails_link.count() > 0:
            total_enviado = emails_link.inner_text().strip().replace(".", "")
        else:
            total_enviado = emails_cell.locator("span").inner_text().strip().replace(".", "")

        logger.debug(f"📧 Total enviado: {total_enviado}")

        # 4. ABIERTO (sexto div = índice 5)
        abiertos_cell = listitem_locator.locator("div.am-responsive-table-cell").nth(5)
        abiertos_link = abiertos_cell.locator("a")
        if abiertos_link.count() > 0:
            abierto = abiertos_link.inner_text().strip().replace(".", "")
        else:
            abierto = abiertos_cell.locator("span").inner_text().strip().replace(".", "")

        logger.debug(f"👁️ Abiertos: {abierto}")

        # 5. CLICS (séptimo div = índice 6) - Extraído pero no usado en output
        clics_cell = listitem_locator.locator("div.am-responsive-table-cell").nth(6)
        clics_link = clics_cell.locator("a")
        if clics_link.count() > 0:
            clics = clics_link.inner_text().strip().replace(".", "")
        else:
            clics = clics_cell.locator("span").inner_text().strip().replace(".", "")

        logger.debug(f"🖱️ Clics: {clics}")

        # 6. CALCULAR "NO ABIERTO"
        try:
            no_abierto = str(int(total_enviado) - int(abierto))
        except ValueError:
            logger.warning(f"⚠️ Error calculando 'No abierto': enviado={total_enviado}, abierto={abierto}")
            no_abierto = "0"

        logger.debug(
            f"✅ Datos extraídos exitosamente con selectores directos",
            extra={
                "nombre": nombre,
                "id": id_campania,
                "fecha": fecha,
                "total_enviado": total_enviado,
                "abierto": abierto,
                "no_abierto": no_abierto,
            },
        )

        return ["", nombre, id_campania, fecha, total_enviado, abierto, no_abierto]

    except Exception as e:
        logger.error(f"❌ Error extrayendo datos de campaña: {e}", extra={"error": str(e)})
        return []


@with_session_retry(max_retries=2)
def navegar_siguiente_pagina_con_recuperacion(page: Page, pagina_actual: int) -> bool:
    """
    Wrapper para navegar_siguiente_pagina con recuperación de sesión
    """
    # Usar la función original pero con el decorador para recuperación
    return navegar_siguiente_pagina(page, pagina_actual)


@with_session_retry(max_retries=2)
def extraer_campanias_de_pagina(page: Page) -> list[list[str]]:
    """
    Extrae todas las campañas de la página actual de informes con recuperación de sesión

    Args:
        page: Página de Playwright

    Returns:
        Lista de campañas con sus datos (sin duplicados por ID)
    """
    logger.info("🔍 Iniciando extracción de campañas de la página actual")
    campanias = []
    ids_vistos = set()  # Para evitar duplicados

    try:
        # Esperar a que la lista se cargue
        logger.debug("⏳ Esperando a que se cargue la lista de informes")
        page.wait_for_selector("ul li", timeout=15000)
        page.wait_for_timeout(1000)  # Espera adicional para asegurar carga completa

        logger.debug("✅ Lista de informes cargada")

        # Usar selectores modernos de Playwright
        # Estrategia: buscar todos los li que contienen un link a /report/campaign/
        # y excluir el primero que es el encabezado
        all_items = page.locator("li").filter(has=page.locator('a[href*="/report/campaign/"]'))

        # Obtener el count
        count = all_items.count()
        logger.info(f"✅ Total de elementos con links de campañas: {count}")

        # Obtener todos los elementos y filtrar manualmente los que son campañas reales
        # Estrategia mejorada: buscar elementos que tengan el patrón completo de una fila de campaña
        campaign_listitems = []
        for i in range(count):
            item = all_items.nth(i)
            text = item.inner_text()

            # Criterios para identificar una fila de campaña real:
            # 1. Debe tener una fecha en formato DD/MM/YY (obligatorio - identifica campañas reales)
            # 2. Debe tener al menos 1 número al final (pueden ser 0 0 0, o 1234, etc.)
            # 3. Debe tener longitud suficiente y no ser solo un fragmento
            tiene_fecha = bool(re.search(r"\d{2}/\d{2}/\d{2}", text))
            tiene_numeros_final = bool(re.search(r"\d+[\s,]*\d*[\s,]*\d*\s*$", text))
            longitud_suficiente = len(text.strip()) > 30

            # Verificar que NO sea un elemento anidado (no debe tener saltos de línea múltiples)
            no_es_anidado = text.count("\n") <= 3

            if tiene_fecha and tiene_numeros_final and longitud_suficiente and no_es_anidado:
                campaign_listitems.append(item)
                logger.debug(f"✅ Campaña válida encontrada en índice {i}: {text[:50]}...")
            else:
                # Logging detallado para debug - mostrar en consola los descartados
                if tiene_fecha and longitud_suficiente:  # Candidatos válidos que fueron descartados
                    print(
                        f"⚠️ DESCARTADO [{i}]: fecha={tiene_fecha}, numeros={tiene_numeros_final}, longitud={len(text.strip())}, saltos={text.count(chr(10))}"
                    )
                    print(f"   Texto: {text[:100]}")
                logger.debug(
                    f"⚠️ Elemento descartado en índice {i}: tiene_fecha={tiene_fecha}, tiene_numeros={tiene_numeros_final}, longitud={len(text.strip())}, saltos_linea={text.count(chr(10))}"
                )

        logger.info(f"✅ Listitems de campañas reales encontrados: {len(campaign_listitems)}")

        for i, listitem in enumerate(campaign_listitems, 1):
            try:
                logger.debug(f"📖 Procesando campaña {i}/{len(campaign_listitems)}")
                datos = extraer_datos_campania_de_listitem(listitem, page)

                if datos and len(datos) >= 3:  # Validar que tiene datos suficientes
                    id_campania = datos[2]  # El ID está en la posición 2

                    # Verificar si ya vimos este ID (evitar duplicados)
                    if id_campania in ids_vistos:
                        logger.warning(f"⚠️ Campaña duplicada detectada (ID: {id_campania}), omitiendo...")
                        continue

                    ids_vistos.add(id_campania)
                    campanias.append(datos)
                    logger.info(f"✅ Campaña {len(campanias)} extraída: {datos[1]} (ID: {datos[2]})")
                else:
                    logger.warning(f"⚠️ No se pudieron extraer datos válidos de la campaña {i}")

            except Exception as e:
                logger.warning(f"⚠️ Error procesando listitem {i}: {e}")
                continue

        logger.success(f"✅ Extracción completada: {len(campanias)} campañas únicas extraídas de la página")

    except Exception as e:
        logger.error(f"❌ Error extrayendo campañas de la página: {e}")

    return campanias


def guardar_datos_en_excel(informe_detalle: list[list[str]], archivo_busqueda: str):
    """
    Guarda los datos en el archivo Excel, usando la primera hoja por defecto
    y ajusta automáticamente el ancho de las columnas
    """
    try:
        logger.info(
            "🚀 Iniciando guardado de datos en Excel",
            extra={"archivo": archivo_busqueda, "registros": len(informe_detalle)},
        )

        wb = crear_o_cargar_libro_excel(archivo_busqueda)
        encabezados = ["Buscar", "Nombre", "ID Campaña", "Fecha", "Total enviado", "Abierto", "No abierto"]

        # Obtener o crear la hoja "Sheet"
        ws = obtener_o_crear_hoja(wb, "Sheet")
        logger.info(f"📝 Hoja obtenida/creada: {ws.title}")

        # Limpiar hoja desde la primera fila
        logger.info("🧹 Limpiando hoja")
        limpiar_hoja_desde_fila(ws, fila_inicial=1)

        # Agregar encabezados
        logger.info("🏷️ Agregando encabezados")
        ws.append(encabezados)

        # Agregar datos
        registros_agregados = agregar_datos(ws, datos=informe_detalle)
        logger.info(f"📊 Datos agregados: {registros_agregados} registros")

        # Ajustar automáticamente el ancho de las columnas
        from openpyxl.utils import get_column_letter

        # Iterar por cada columna usando índices
        logger.info("📐 Ajustando ancho de columnas")
        for col_idx in range(1, ws.max_column + 1):
            max_length = 0
            column_letter = get_column_letter(col_idx)

            # Revisar todas las celdas de esta columna
            for row_idx in range(1, ws.max_row + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                try:
                    if cell.value and len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass

            # Ajustar el ancho (agregar un poco de padding)
            adjusted_width = min(max_length + 2, 50)  # Máximo 50 caracteres
            ws.column_dimensions[column_letter].width = adjusted_width

        wb.save(archivo_busqueda)
        logger.success(f"✅ Archivo guardado exitosamente: {archivo_busqueda}")
        logger.info(f"📈 Se agregaron {registros_agregados} registros al archivo")

    except Exception as e:
        logger.error(f"❌ Error guardando archivo Excel: {e}")
        print(f"Error guardando archivo Excel: {e}")


def procesar_todas_las_paginas(page: Page) -> list[list[str]]:
    """
    Procesa todas las páginas de reportes y extrae todas las campañas (sin duplicados globales)

    Args:
        page: Página de Playwright

    Returns:
        Lista con todos los datos de campañas únicas
    """
    logger.info("🔍 Iniciando procesamiento de todas las páginas")
    todas_campanias = []
    ids_globales = set()  # Para evitar duplicados entre páginas

    try:
        # Obtener número total de páginas
        logger.debug("📄 Obteniendo número total de páginas")
        total_paginas = obtener_total_paginas(page)
        logger.info(f"📚 Total de páginas a procesar: {total_paginas}")

        # Procesar cada página
        for pagina_actual in range(1, total_paginas + 1):
            logger.info(f"📖 === PROCESANDO PÁGINA {pagina_actual} DE {total_paginas} ===")

            # Extraer campañas de la página actual
            campanias_pagina = extraer_campanias_de_pagina(page)

            # Filtrar duplicados globales (entre páginas)
            campanias_nuevas = 0
            for campania in campanias_pagina:
                if len(campania) >= 3:
                    id_campania = campania[2]
                    if id_campania not in ids_globales:
                        ids_globales.add(id_campania)
                        todas_campanias.append(campania)
                        campanias_nuevas += 1
                    else:
                        logger.debug(f"⚠️ Campaña duplicada entre páginas (ID: {id_campania}), omitiendo...")

            logger.info(
                f"✅ Página {pagina_actual} completada",
                extra={
                    "campanias_en_pagina": len(campanias_pagina),
                    "campanias_nuevas": campanias_nuevas,
                    "total_acumulado": len(todas_campanias),
                },
            )

            # Navegar a la siguiente página si no es la última
            if pagina_actual < total_paginas:
                logger.debug(f"➡️ Navegando a página {pagina_actual + 1} con recuperación de sesión")
                exito = navegar_siguiente_pagina_con_recuperacion(page, pagina_actual)
                if not exito:
                    logger.warning(f"⚠️ No se pudo navegar a página {pagina_actual + 1}, finalizando procesamiento")
                    break

                # Espera adicional después de navegar
                page.wait_for_timeout(2000)
                logger.debug(f"✅ Navegación a página {pagina_actual + 1} completada")

        logger.success(
            f"🎉 Procesamiento completo: {len(todas_campanias)} campañas extraídas de {pagina_actual} páginas"
        )

    except Exception as e:
        logger.error(f"❌ Error procesando páginas: {e}")

    return todas_campanias


def main():
    """
    Función principal del programa de listado de campañas
    Usa API para obtener IDs y scraping para completar los datos
    """
    logger.info("🚀 Iniciando programa de listado de campañas (modo híbrido: API + Scraping)")

    try:
        with sync_playwright() as p:
            # Configurar navegador
            logger.info("🌐 Configurando navegador Playwright")
            browser = configurar_navegador(p, extraccion_oculta=False)
            context = crear_contexto_navegador(browser, extraccion_oculta=False)
            page = context.new_page()
            logger.success("✅ Navegador configurado correctamente")

            # Login
            logger.info("🔐 Iniciando proceso de autenticación")
            login(page, context)
            logger.success("✅ Sesión iniciada correctamente")

            # Navegar a reportes
            logger.info("📊 Navegando a sección de reportes")
            navegar_a_reportes(page)
            logger.success("✅ Navegación a reportes completada")

            # Esperar a que la página cargue completamente
            logger.debug("⏳ Esperando carga completa de la página")
            page.wait_for_load_state("networkidle", timeout=60000)
            page.wait_for_timeout(3000)  # Espera adicional para asegurar carga completa
            logger.debug("✅ Página cargada completamente")

            # Procesar todas las páginas y extraer campañas con scraping
            logger.info("📥 Iniciando extracción de campañas mediante scraping")
            informe = procesar_todas_las_paginas(page)
            logger.info(f"📊 Total de campañas extraídas mediante scraping: {len(informe)}")

            # Guardar en Excel
            if informe:
                logger.info("💾 Guardando datos en archivo Excel")
                guardar_datos_en_excel(informe, ARCHIVO_BUSQUEDA)
                logger.success("✅ Programa completado exitosamente")
                notify("Listado de Campañas", f"Se extrajeron {len(informe)} campañas correctamente", "info")
            else:
                logger.warning("⚠️ No se encontraron campañas para guardar")
                notify("Listado de Campañas", "No se encontraron campañas", "warning")

            # Cerrar navegador
            logger.debug("🔚 Cerrando navegador")
            browser.close()
            logger.info("✅ Navegador cerrado correctamente")

    except Exception as e:
        logger.error(f"❌ Error crítico en el programa: {e}", extra={"error": str(e)})
        print(f"Error crítico en el programa: {e}")
        notify("Error", f"Error crítico: {e}", "error")
        raise


if __name__ == "__main__":
    main()
