"""
Componente CampaignRow para extracción de datos de fila individual.

Encapsula la lógica de extracción de datos de una campaña desde un listitem
del DOM de la página de reportes de Acumbamail.
"""

import re
from playwright.sync_api import Page, Locator
from src.shared.logging.logger import get_logger

logger = get_logger()


class FilaCampania:
    """Representa una fila individual de campaña en la página de reportes.

    Extrae nombre, ID, fecha, total enviado, abiertos y calcula "no abierto".
    NO filtra Locator fuera del componente; devuelve datos crudos o lista vacía si no es válida.
    """

    # Criterios de validación (idénticos a legacy extraer_campanias_de_pagina)
    FECHA_REGEX = re.compile(r"\d{2}/\d{2}/\d{2}")
    NUMEROS_FINAL_REGEX = re.compile(r"\d+[\s,]*\d*[\s,]*\d*\s*$")

    def __init__(self, element: Locator, page: Page):
        self._element = element
        self._page = page

    def is_valid_row(self) -> bool:
        """Verifica si el elemento es una fila de campaña real (no header, no fragmento).

        Criterios (preservados del legacy):
        1. Debe tener fecha en formato DD/MM/YY
        2. Debe tener al menos 1 número al final
        3. Longitud del texto > 30 caracteres
        4. No debe tener más de 3 saltos de línea (no es anidado)
        """
        try:
            text = self._element.inner_text()
        except Exception:
            return False

        tiene_fecha = bool(self.FECHA_REGEX.search(text))
        tiene_numeros_final = bool(self.NUMEROS_FINAL_REGEX.search(text))
        longitud_suficiente = len(text.strip()) > 30
        no_es_anidado = text.count("\n") <= 3

        return tiene_fecha and tiene_numeros_final and longitud_suficiente and no_es_anidado

    def extract_data(self) -> list[str]:
        """Extrae datos de la campaña y devuelve lista para Excel.

        Returns:
            Lista con 7 elementos: ["", nombre, id, fecha, total_enviado, abierto, no_abierto]
            Lista vacía si no se pudo extraer.
        """
        try:
            # 1. NOMBRE + ID (primer link con href /report/campaign/)
            campaign_link = self._element.locator('a[href*="/report/campaign/"]').first
            if campaign_link.count() == 0:
                logger.warning("⚠️ CampaignRow: no se encontró link de campaña")
                return []

            nombre = campaign_link.inner_text().strip()
            href = campaign_link.get_attribute("href") or ""
            id_campania = self._extraer_id_de_url(href)

            logger.debug(f"📝 CampaignRow: nombre={nombre}, id={id_campania}")

            # 2. FECHA (tercer div.am-responsive-table-cell = índice 2)
            fecha_cell = self._element.locator("div.am-responsive-table-cell").nth(2)
            fecha = fecha_cell.locator("span").inner_text().strip()

            # 3. TOTAL ENVIADO (Emails = índice 5, columna "Listas" está en 4)
            emails_cell = self._element.locator("div.am-responsive-table-cell").nth(5)
            total_enviado = self._extraer_valor_celda(emails_cell)

            # 4. ABIERTO (índice 6)
            abiertos_cell = self._element.locator("div.am-responsive-table-cell").nth(6)
            abierto = self._extraer_valor_celda(abiertos_cell)

            # 5. CALCULAR "NO ABIERTO" (sin clamping, puede ser negativo)
            try:
                no_abierto = str(int(total_enviado) - int(abierto))
            except ValueError:
                logger.warning(
                    f"⚠️ CampaignRow: error calculando 'No abierto': enviado={total_enviado}, abierto={abierto}"
                )
                no_abierto = "0"

            logger.debug(
                f"✅ CampaignRow: datos extraídos",
                extra={
                    "nombre": nombre,
                    "id": id_campania,
                    "fecha": fecha,
                    "total_enviado": total_enviado,
                    "abierto": abierto,
                    "no_abierto": no_abierto,
                },
            )

            # Formato para Excel: 7 columnas (la 8va "URL de Correo" se agrega después)
            return ["", nombre, id_campania, fecha, total_enviado, abierto, no_abierto]

        except Exception as e:
            logger.error(f"❌ CampaignRow: error extrayendo datos: {e}")
            return []

    # --- Private helpers ---

    @staticmethod
    def _extraer_id_de_url(url: str) -> str:
        """Extrae ID de campaña de URL: /report/campaign/12345/ -> 12345"""
        match = re.search(r"/campaign/(\d+)", url)
        return match.group(1) if match else ""

    @staticmethod
    def _extraer_valor_celda(cell: Locator) -> str:
        """Extrae valor numérico de una celda (puede ser <a> o <span>).

        Elimina puntos de separación de miles.
        """
        link = cell.locator("a")
        if link.count() > 0:
            return link.inner_text().strip().replace(".", "")
        return cell.locator("span").inner_text().strip().replace(".", "")
