import sys
from pathlib import Path

# Configurar package para imports consistentes y PyInstaller compatibility
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "src"

from .excel_utils import agregar_datos, crear_o_cargar_libro_excel, obtener_o_crear_hoja, limpiar_hoja_desde_fila
from .shared.utils.legacy_utils import data_path
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
BATCH_SIZE = 10  # Cada cuántas campañas guardar progreso (listado y URLs)

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
        encabezados = ["Buscar", "Nombre", "ID Campaña", "Fecha", "Total enviado", "Abierto", "No abierto", "URL de Correo"]

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


def _guardar_progreso_listado(campanias_acumuladas: list[list[str]], encabezados: list[str]):
    """
    Guarda el progreso del listado de campañas en el Excel.
    Sobreescribe el archivo con las campañas acumuladas hasta el momento.
    """
    try:
        wb = crear_o_cargar_libro_excel(None)
        ws = wb.active
        if ws is None:
            ws = wb.create_sheet("Sheet")

        # Limpiar y escribir encabezados
        ws.delete_rows(1, ws.max_row)
        ws.append(encabezados)

        # Agregar campañas acumuladas
        for campania in campanias_acumuladas:
            ws.append(campania)

        # Ajustar ancho de columnas
        from openpyxl.utils import get_column_letter
        for col_idx in range(1, ws.max_column + 1):
            max_length = 0
            column_letter = get_column_letter(col_idx)
            for row_idx in range(1, ws.max_row + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                try:
                    if cell.value and len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except Exception:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width

        wb.save(ARCHIVO_BUSQUEDA)
        wb.close()
        logger.debug(f"💾 Progreso guardado: {len(campanias_acumuladas)} campañas en Excel")

    except Exception as e:
        logger.error(f"❌ Error guardando progreso: {e}")


def procesar_todas_las_paginas(page: Page, batch_size: int = 10) -> list[list[str]]:
    """
    Procesa todas las páginas de reportes y extrae todas las campañas (sin duplicados globales).
    Guarda el progreso cada 'batch_size' campañas para poder retomar si algo falla.

    Args:
        page: Página de Playwright
        batch_size: Cada cuántas campañas guardar el progreso (default: 10)

    Returns:
        Lista con todos los datos de campañas únicas
    """
    import os
    logger.info(f"🔍 Iniciando procesamiento de todas las páginas (batch_size={batch_size})")

    encabezados = ["Buscar", "Nombre", "ID Campaña", "Fecha", "Total enviado", "Abierto", "No abierto", "URL de Correo"]

    # Intentar cargar campañas ya listadas del Excel existente
    campanias_existentes = []
    if os.path.exists(ARCHIVO_BUSQUEDA):
        try:
            existentes, _ = leer_urls_faltantes_del_excel()
            # Filtrar solo las que tienen ID (campañas válidas listadas)
            campanias_existentes = [c for c in existentes if len(c) >= 3 and c[2]]
            if campanias_existentes:
                logger.info(f"📂 Excel encontrado con {len(campanias_existentes)} campañas ya listadas")
        except Exception:
            pass

    todas_campanias = list(campanias_existentes)
    ids_globales = set(c[2] for c in campanias_existentes if len(c) >= 3 and c[2])
    pendientes_guardar = 0

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
                        # Asegurar que tenga 8 columnas (agregar URL vacía)
                        while len(campania) < 8:
                            campania.append("")
                        todas_campanias.append(campania)
                        campanias_nuevas += 1
                        pendientes_guardar += 1
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

            # Guardar progreso si alcanzó el batch_size
            if pendientes_guardar >= batch_size:
                logger.info(f"💾 Guardando progreso del listado: {pendientes_guardar} campañas nuevas...")
                _guardar_progreso_listado(todas_campanias, encabezados)
                pendientes_guardar = 0
                logger.success(f"✅ Progreso guardado: {len(todas_campanias)} campañas totales")

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

        # Guardar resto pendiente
        if pendientes_guardar > 0:
            logger.info(f"💾 Guardando último lote de {pendientes_guardar} campañas...")
            _guardar_progreso_listado(todas_campanias, encabezados)
            logger.success(f"✅ Progreso final guardado: {len(todas_campanias)} campañas totales")

        logger.success(
            f"🎉 Procesamiento completo: {len(todas_campanias)} campañas extraídas de {pagina_actual} páginas"
        )

    except Exception as e:
        logger.error(f"❌ Error procesando páginas: {e}")
        # Guardar lo que se haya procesado antes del error
        if todas_campanias:
            logger.info("💾 Guardando campañas procesadas antes del error...")
            _guardar_progreso_listado(todas_campanias, encabezados)

    return todas_campanias


def extraer_url_correo_rapido(page: Page, campaign_id: int) -> str:
    """
    Extrae la URL del correo de una campaña de forma ultra-rápida.
    Navega sin esperar networkidle, apenas cargue extrae la URL del regex.
    """
    import re
    from playwright.sync_api import TimeoutError as PWTimeoutError

    try:
        url = f"https://acumbamail.com/report/campaign/{campaign_id}/subscribers/"

        # Navegar sin esperar a que todo cargue (commit = apenas responde el servidor)
        page.goto(url, wait_until="commit", timeout=30000)

        # Esperar solo a que el botón "Ver email" aparezca (no esperar toda la página)
        try:
            email_link = page.get_by_text("Ver email").get_attribute("href", timeout=3000)
            if email_link and "clickacm.com" in email_link:
                return email_link
        except PWTimeoutError:
            pass

        # Fallback: buscar URL de clickacm.com directamente en el HTML crudo
        try:
            page_content = page.content()
            pattern = r'(https://clickacm\.com/show/[a-zA-Z0-9-]+/)'
            matches = re.findall(pattern, page_content)
            if matches:
                return matches[0]
        except Exception:
            pass

        return ""

    except Exception:
        return ""


def leer_urls_faltantes_del_excel() -> tuple[list[list[str]], int]:
    """
    Lee el Excel de Busqueda.xlsx y retorna:
    - Lista completa de campañas (con URLs si ya existen, vacías si no)
    - Cantidad de campañas con URL pendiente

    Si el archivo no existe o no tiene la columna URL, retorna todo pendiente.
    """
    import os
    from openpyxl import load_workbook

    if not os.path.exists(ARCHIVO_BUSQUEDA):
        return [], 0

    try:
        wb = load_workbook(ARCHIVO_BUSQUEDA)
        ws = wb.active

        filas = list(ws.iter_rows(values_only=True))

        if not filas:
            return [], 0

        encabezados = list(filas[0])

        # Verificar si tiene la columna URL de Correo
        idx_url = None
        if "URL de Correo" in encabezados:
            idx_url = encabezados.index("URL de Correo")

        # Reconstruir campañas desde las filas (omitir encabezados)
        campanias = []
        pendientes = 0

        for fila in filas[1:]:
            valores = list(fila)

            # Si no tiene columna URL o está vacía, está pendiente
            if idx_url is None:
                # Agregar columna URL vacía
                valores.append("")
                pendientes += 1
            elif idx_url < len(valores) and (not valores[idx_url] or str(valores[idx_url]).strip() == ""):
                pendientes += 1
            elif idx_url >= len(valores):
                # Fila incompleta, agregar vacía
                while len(valores) < 8:
                    valores.append("")
                pendientes += 1

            campanias.append(valores)

        wb.close()
        return campanias, pendientes

    except Exception as e:
        logger.warning(f"⚠️ Error leyendo Excel existente, procesando desde cero: {e}")
        return [], 0


def actualizar_urls_en_excel(campanias_actualizadas: list[list[str]]):
    """
    Actualiza las URLs de correo en el Excel sin reescribir todo.
    """
    import os
    from openpyxl import load_workbook

    if not os.path.exists(ARCHIVO_BUSQUEDA):
        return

    try:
        wb = load_workbook(ARCHIVO_BUSQUEDA)
        ws = wb.active

        encabezados = [c.value for c in ws[1]]
        if "URL de Correo" not in encabezados:
            wb.close()
            return

        idx_url = encabezados.index("URL de Correo")

        for i, campania in enumerate(campanias_actualizadas, start=2):  # start=2 (omitir encabezados)
            if i <= ws.max_row and idx_url < len(campania):
                celda = ws.cell(row=i, column=idx_url + 1)
                celda.value = campania[idx_url]

        wb.save(ARCHIVO_BUSQUEDA)
        wb.close()

    except Exception as e:
        logger.error(f"❌ Error actualizando Excel: {e}")


def extraer_urls_de_campanias(page: Page, campanias: list[list[str]], batch_size: int = 10) -> list[list[str]]:
    """
    Extrae URLs de correo en tandas de 'batch_size' campañas.
    Después de cada tanda guarda las URLs en el Excel.
    Si ya tiene URL, la omite y pasa a la siguiente.

    Args:
        page: Página de Playwright
        campanias: Lista de campañas con sus datos
        batch_size: Cantidad de campañas a procesar antes de guardar (default: 10)

    Returns:
        Lista de campañas con URLs actualizadas
    """
    total_campanias = len(campanias)
    total_pendientes = sum(1 for c in campanias if (len(c) <= 7) or (len(c) > 7 and not c[7]))

    if total_pendientes == 0:
        logger.success("✅ Todas las campañas ya tienen URL, saltando extracción")
        return campanias

    logger.info(f"📧 Extrayendo URLs: {total_pendientes}/{total_campanias} campañas pendientes")

    procesadas = 0
    batch = []

    for i, campania in enumerate(campanias):
        id_campania = campania[2] if len(campania) > 2 else ""

        # Si ya tiene URL, saltar
        if len(campania) > 7 and campania[7] and str(campania[7]).strip():
            logger.debug(f"⏭️ [{i+1}/{total_campanias}] URL ya existente para '{campania[1]}', saltando")
            continue

        if not id_campania:
            logger.warning(f"⚠️ Campaña {i+1} sin ID, marcando como vacía")
            while len(campania) < 8:
                campania.append("")
            continue

        try:
            logger.info(f"📧 [{i+1}/{total_campanias}] Extrayendo URL de '{campania[1]}' (ID: {id_campania})")

            url_correo = extraer_url_correo_rapido(page, int(id_campania))

            if url_correo:
                logger.success(f"✅ URL encontrada: {url_correo}")
            else:
                logger.warning(f"⚠️ No se encontró URL para campaña '{campania[1]}'")

            # Asegurar que la campaña tenga 8 columnas y asignar URL
            while len(campania) < 7:
                campania.append("")
            if len(campania) == 7:
                campania.append(url_correo)  # Columna 7 (índice 7) = URL de Correo
            else:
                campania[7] = url_correo

            procesadas += 1
            batch.append(campania)

            # Guardar en Excel cada 'batch_size' campañas
            if len(batch) >= batch_size:
                logger.info(f"💾 Guardando tanda de {len(batch)} URLs en Excel...")
                actualizar_urls_en_excel(campanias)
                logger.success(f"✅ Tanda guardada. Progreso: {procesadas}/{total_pendientes}")
                batch = []

            # Verificar si sesión expiró
            if is_on_login_page(page):
                logger.warning("⚠️ Sesión expirada durante extracción de URLs, re-autenticando...")
                login(page, page.context)
                navegar_a_reportes(page)

        except Exception as e:
            logger.error(f"❌ Error extrayendo URL de campaña '{campania[1]}': {e}")
            while len(campania) < 8:
                campania.append("")
            campania[7] = ""

    # Guardar resto pendiente
    if batch:
        logger.info(f"💾 Guardando última tanda de {len(batch)} URLs en Excel...")
        actualizar_urls_en_excel(campanias)
        logger.success(f"✅ Última tanda guardada. Total: {procesadas}/{total_pendientes}")

    logger.success(f"✅ Extracción de URLs completada: {procesadas}/{total_pendientes} procesadas")
    return campanias


def main():
    """
    Función principal del programa de listado de campañas.

    Flujo inteligente:
    - Si el Excel ya existe: solo procesa URLs pendientes (no re-lista campañas)
    - Si el Excel no existe: lista todas las campañas + extrae URLs
    """
    import os
    logger.info("🚀 Iniciando programa de listado de campañas")

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
            page.wait_for_timeout(3000)
            logger.debug("✅ Página cargada completamente")

            # Verificar si ya existe el Excel con campañas
            excel_existe = os.path.exists(ARCHIVO_BUSQUEDA)

            if excel_existe:
                # Leer campañas existentes y verificar cuántas URLs faltan
                logger.info("📂 Excel encontrado, leyendo campañas existentes...")
                informe, pendientes = leer_urls_faltantes_del_excel()

                if not informe:
                    logger.warning("⚠️ Excel vacío o ilegible, procesando desde cero")
                    excel_existe = False
                elif pendientes == 0:
                    logger.success(f"✅ Todas las campañas ({len(informe)}) ya tienen URL, terminado")
                    browser.close()
                    return
                else:
                    # Tiene campañas pero faltan URLs - verificar si faltan campañas por listar
                    tienen_id = sum(1 for c in informe if len(c) >= 3 and c[2])
                    logger.info(f"📧 {pendientes}/{len(informe)} campañas sin URL, procesando solo pendientes...")
                    # Si todas tienen ID, ir directo a URLs. Si no, re-listar para capturar nuevas
                    if tienen_id == len(informe):
                        excel_existe = True  # Solo ir a Fase 3
                    else:
                        excel_existe = False  # Re-listar todo
            else:
                logger.info("📂 Excel no encontrado, se creará desde cero")

            if not excel_existe:
                # Fase 1: Listar todas las campañas desde cero (guarda progreso cada BATCH_SIZE)
                logger.info(f"📥 Fase 1: Extrayendo lista de campañas (progreso cada {BATCH_SIZE})")
                informe = procesar_todas_las_paginas(page, batch_size=BATCH_SIZE)
                logger.success(f"✅ Fase 1 completada: {len(informe)} campañas encontradas")

                if not informe:
                    logger.warning("⚠️ No se encontraron campañas, terminando")
                    browser.close()
                    return

            # Fase 2: Extraer URLs de correo SOLO las pendientes en tandas de BATCH_SIZE
            logger.info(f"📧 Fase 2: Extrayendo URLs de correo pendientes en tandas de {BATCH_SIZE}")
            informe = extraer_urls_de_campanias(page, informe, batch_size=BATCH_SIZE)
            logger.success(f"✅ Fase 2 completada: todas las URLs procesadas")

            # Guardar resultado final completo
            logger.info("💾 Guardando Excel final con todas las URLs...")
            guardar_datos_en_excel(informe, ARCHIVO_BUSQUEDA)
            logger.success("✅ Programa completado exitosamente")

            # Cerrar navegador
            logger.debug("🔚 Cerrando navegador")
            browser.close()
            logger.info("✅ Navegador cerrado correctamente")

    except Exception as e:
        logger.error(f"❌ Error crítico en el programa: {e}", extra={"error": str(e)})
        raise


if __name__ == "__main__":
    main()
