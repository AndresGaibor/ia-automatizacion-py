import sys
from pathlib import Path

# Configurar package para imports consistentes y PyInstaller compatibility
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "src"

from ...shared.utils.legacy_utils import (
    data_path,
    crear_contexto_navegador,
    configurar_navegador,
    is_on_login_page,
    navegar_a_reportes,
)
from ...autentificacion import login
from ...shared.logging.logger import get_logger
from ...infrastructure.api import API
from ...core.authentication.exceptions import SessionExpiredError, AuthenticationFailedError
from ...infrastructure.scraping.flows.report_listing_flow import ReportListingFlow
from ...infrastructure.scraping.flows.auth_flow import AuthFlow
from ...infrastructure.scraping.pages.reports_page import ReportsPage
from ...infrastructure.excel.campaign_report_exporter import CampaignReportExporter

from playwright.sync_api import sync_playwright, Page

# Rutas
ARCHIVO_BUSQUEDA = data_path("Busqueda.xlsx")
BATCH_SIZE = 10

logger = get_logger()





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
    Actualiza las URLs de correo en el Excel reescribiendo todo el archivo.
    """
    try:
        from openpyxl import Workbook

        encabezados = [
            "Buscar",
            "Nombre",
            "ID Campaña",
            "Fecha",
            "Total enviado",
            "Abierto",
            "No abierto",
            "URL de Correo",
        ]

        wb = Workbook()
        ws = wb.active
        ws.title = "Sheet"

        # Encabezados
        ws.append(encabezados)

        # Todas las campañas con sus URLs
        for campania in campanias_actualizadas:
            # Asegurar 8 columnas
            fila = list(campania)
            while len(fila) < 8:
                fila.append("")
            ws.append(fila)

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
            logger.debug(f"⏭️ [{i + 1}/{total_campanias}] URL ya existente para '{campania[1]}', saltando")
            continue

        if not id_campania:
            logger.warning(f"⚠️ Campaña {i + 1} sin ID, marcando como vacía")
            while len(campania) < 8:
                campania.append("")
            continue

        try:
            logger.info(f"📧 [{i + 1}/{total_campanias}] Extrayendo URL de '{campania[1]}' (ID: {id_campania})")

            reports_page = ReportsPage(page)
            url_correo = reports_page.extract_email_url_quick(int(id_campania))

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

            logger.info("🔐 Iniciando proceso de autenticación con AuthFlow")
            auth_flow = AuthFlow(page, context)
            auth_flow.ensure_authenticated()
            logger.success("✅ Sesión autenticada correctamente")

            logger.info("📊 Navegando a sección de reportes con ReportsPage")
            reports_page = ReportsPage(page)
            reports_page.navigate_to()
            logger.success("✅ Página de reportes lista")

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
                flow = ReportListingFlow(page, batch_size=BATCH_SIZE)
                informe = flow.execute()
                logger.success(f"✅ Fase 1 completada: {len(informe)} campañas encontradas")

                if not informe:
                    logger.warning("⚠️ No se encontraron campañas, terminando")
                    browser.close()
                    return

            # Fase 2: Extraer URLs de correo SOLO las pendientes en tandas de BATCH_SIZE
            logger.info(f"📧 Fase 2: Extrayendo URLs de correo pendientes en tandas de {BATCH_SIZE}")
            informe = extraer_urls_de_campanias(page, informe, batch_size=BATCH_SIZE)
            logger.success(f"✅ Fase 2 completada: todas las URLs procesadas")

            # Exportar resultado final con CampaignReportExporter
            logger.info("💾 Exportando Excel final con CampaignReportExporter...")
            exporter = CampaignReportExporter()
            exporter.export(informe, ARCHIVO_BUSQUEDA)
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
