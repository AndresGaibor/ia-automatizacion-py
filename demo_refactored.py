"""Refactored demo module using new architecture."""
from playwright.sync_api import sync_playwright
from datetime import datetime
from typing import List
from pathlib import Path

# Imports for script executed from root level
from src.core.authentication.authentication_service import AuthenticationService, FileSessionStorage
from src.core.config.config_manager import ConfigManager
from src.core.services.campaign_service import CampaignService
from src.infrastructure.browser.browser_manager import BrowserManager
from src.infrastructure.excel.excel_manager import ExcelManager
from src.shared.utils import data_path, storage_state_path
from src.shared.logging import get_logger

logger = get_logger()


def main():
    """Main function using refactored architecture."""
    try:
        logger.info("🚀 Starting subscriber extraction with refactored architecture")

        # Initialize configuration manager
        config_manager = ConfigManager()
        config_path = Path("config.yaml")
        config = config_manager.load(config_path)

        # Initialize services
        campaign_service = CampaignService()
        excel_manager = ExcelManager()

        # Load campaigns to process
        campaigns = campaign_service.load_campaigns_to_search()
        logger.info(f"📊 Loaded {len(campaigns)} campaigns for processing")

        if not campaigns:
            logger.warning("⚠️ No campaigns marked for processing")
            return

        # Initialize browser manager
        browser_manager = BrowserManager(config_manager)

        # Initialize authentication service
        session_storage = FileSessionStorage(storage_state_path())
        auth_service = AuthenticationService(config_manager, session_storage)

        # Initialize hybrid data service
        # hybrid_service = HybridDataService()  # Skip for now due to complexity

        # Process campaigns
        with browser_manager as browser:
            context = browser.create_context(storage_state_path())
            page = browser.new_page()

            # Authenticate
            auth_service.authenticate(page, context)

            # Process each campaign
            general_data = []
            all_detailed_data = {
                'opened': [],
                'not_opened': [],
                'clicked': [],
                'hard_bounces': [],
                'soft_bounces': []
            }

            for campaign_id, campaign_name in campaigns:
                logger.info(f"📈 Processing campaign: {campaign_name} (ID: {campaign_id})")

                try:
                    # For now, create sample data to demonstrate the new architecture
                    # This would be replaced by actual data extraction logic
                    general_row = [
                        campaign_name,
                        'Newsletter',
                        datetime.now().strftime("%Y-%m-%d"),
                        'Lista ejemplo',
                        '1000',  # emails sent
                        '250',   # opened
                        '50',    # clicked
                        f'https://example.com/campaign/{campaign_id}'
                    ]
                    general_data.append(general_row)

                    logger.success(f"✅ Campaign processed successfully: {campaign_name}")

                except Exception as e:
                    logger.error(f"❌ Error processing campaign {campaign_name}: {e}")
                    continue

            # Create Excel report if we have data
            if general_data:
                # Generate filename based on first campaign
                first_campaign = campaigns[0]
                report_filename = campaign_service.generate_report_filename(
                    first_campaign[1],
                    datetime.now().strftime("%Y%m%d")
                )

                # Create Excel report
                excel_manager.create_campaign_report(
                    general_data,
                    all_detailed_data,
                    report_filename
                )

                logger.success(f"✅ Report created successfully: {report_filename}")
            else:
                logger.warning("⚠️ No data to export - no Excel file created")

    except Exception as e:
        logger.error(f"❌ Fatal error in main process: {e}")
        raise


if __name__ == "__main__":
    main()