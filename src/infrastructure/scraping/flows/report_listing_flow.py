"""
ReportListingFlow - Flujo de extracción multi-página de campañas.

Orquesta extracción de todas las páginas de reportes con:
- Deduplicación global (set de IDs entre páginas)
- Progreso incremental (guardar cada batch_size campañas)
- Recovery desde Excel existente
"""

import os
from playwright.sync_api import Page
from src.infrastructure.scraping.pages.reports_page import ReportsPage
from src.infrastructure.excel.campaign_report_exporter import (
    CAMPAIGN_REPORT_HEADERS,
    load_campaign_listing_progress,
    save_campaign_listing_progress,
)
from src.shared.logging.logger import get_logger
from src.shared.utils.legacy_utils import data_path

logger = get_logger()

ARCHIVO_BUSQUEDA = data_path("Busqueda.xlsx")


class ReportListingFlow:
    def __init__(self, page: Page, batch_size: int = 10):
        self._page = page
        self._reports_page = ReportsPage(page)
        self._batch_size = batch_size

    def execute(self) -> list[list[str]]:
        """Ejecuta extracción completa de todas las campañas.

        Returns:
            Lista de listas con 8 elementos por fila (compatible con guardar_datos_en_excel).
        """
        logger.info(f"🔍 ReportListingFlow: inicio (batch_size={self._batch_size})")

        # Optimizar items/página
        self._reports_page.optimize_items_per_page()

        # Cargar progreso existente
        todas_campanias, ids_globales = self._load_existing_progress()

        try:
            total_paginas = self._reports_page.get_total_pages()
            logger.info(f"📚 Total páginas a procesar: {total_paginas}")

            pendientes_guardar = 0

            for pagina_actual in range(1, total_paginas + 1):
                logger.info(f"📖 === PÁGINA {pagina_actual} DE {total_paginas} ===")

                campanias_nuevas = self._extract_page(pagina_actual, total_paginas, ids_globales)
                todas_campanias.extend(campanias_nuevas)
                pendientes_guardar += len(campanias_nuevas)

                if pendientes_guardar >= self._batch_size:
                    self._save_progress(todas_campanias)
                    pendientes_guardar = 0

                if pagina_actual < total_paginas:
                    if not self._reports_page.navigate_to_next_page(pagina_actual):
                        logger.warning(f"⚠️ No se pudo navegar a página {pagina_actual + 1}")
                        break

            if pendientes_guardar > 0:
                self._save_progress(todas_campanias)

            logger.success(f"🎉 Extracción completa: {len(todas_campanias)} campañas")
            return todas_campanias

        except Exception as e:
            logger.error(f"❌ Error en ReportListingFlow: {e}")
            if todas_campanias:
                self._save_progress(todas_campanias)
            raise

    # --- Private methods ---

    def _load_existing_progress(self) -> tuple[list[list[str]], set[str]]:
        campanias, ids = load_campaign_listing_progress(ARCHIVO_BUSQUEDA)
        if campanias:
            logger.info(f"📂 Recovery: {len(campanias)} campañas existentes")
        return campanias, ids

    def _extract_page(self, pagina_actual: int, total_paginas: int, ids_globales: set[str]) -> list[list[str]]:
        """Extrae campañas de la página actual, filtrando duplicados globales."""
        valid_rows = self._reports_page.get_valid_campaign_rows()
        nuevas = []

        for row in valid_rows:
            datos = row.extract_data()
            if datos and len(datos) >= 3:
                id_campania = datos[2]
                if id_campania not in ids_globales:
                    ids_globales.add(id_campania)
                    while len(datos) < 8:
                        datos.append("")
                    nuevas.append(datos)
                    logger.info(f"✅ Campaña {len(nuevas)}: {datos[1]} (ID: {datos[2]})")
                else:
                    logger.debug(f"⚠️ Duplicado global omitido (ID: {id_campania})")

        logger.info(f"✅ Página {pagina_actual}: {len(nuevas)} nuevas, {len(ids_globales)} total únicas")
        return nuevas

    def _save_progress(self, campanias: list[list[str]]) -> None:
        try:
            save_campaign_listing_progress(ARCHIVO_BUSQUEDA, campanias, CAMPAIGN_REPORT_HEADERS)
            logger.debug(f"💾 Progreso guardado: {len(campanias)} campañas")
        except Exception as e:
            logger.error(f"❌ Error guardando progreso: {e}")
