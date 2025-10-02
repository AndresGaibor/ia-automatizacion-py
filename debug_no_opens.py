#!/usr/bin/env python3
"""
Script de prueba para debuggear la extracción de no opens
"""
import sys
sys.path.append('src')

from playwright.sync_api import sync_playwright
from src.infrastructure.api.client import AcumbaClient
from src.config import load_config
from src.logger import get_logger
from src.structured_logger import log_info, log_success, log_error
from src.scrapping.endpoints.subscriber_details import SubscriberDetailsService
from src.infrastructure.api.models.campanias import CampaignBasicInfo

def test_no_opens_extraction():
    """Prueba la extracción de no opens para debuggear"""
    config = load_config()
    client = AcumbaClient(config)
    logger = get_logger()

    campaign_id = 3378410
    campaign = CampaignBasicInfo(
        id=campaign_id,
        name="[COM-9596] COMUNICADO NUEVA VERSIÓN DE LEXNET",
        sent_date="20250910"
    )

    log_info("Iniciando prueba de extracción de no opens", campaign_id=campaign_id)

    with sync_playwright() as p:
        try:
            # Iniciar browser
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )

            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )

            page = context.new_page()

            # Login
            log_info("Realizando login...")
            client.login_with_session(page)

            # Crear servicio
            service = SubscriberDetailsService(page)

            # Navegar a detalles
            log_info("Navegando a detalles de suscriptores...")
            service.navigate_to_subscriber_details(campaign_id)

            # Extraer no opens
            log_info("Extrayendo no opens...")
            no_opens = service.extract_no_opens(campaign, campaign_id)

            log_success("Extracción completada",
                       total_no_opens=len(no_opens),
                       campaign_id=campaign_id)

            # Mostrar estadísticas por página
            page_stats = {}
            for subscriber in no_opens:
                page = subscriber.page_number
                if page not in page_stats:
                    page_stats[page] = 0
                page_stats[page] += 1

            log_info("Estadísticas por página:", page_stats=page_stats)

            browser.close()

        except Exception as e:
            log_error("Error en prueba", error=str(e), error_type=type(e).__name__)
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_no_opens_extraction()