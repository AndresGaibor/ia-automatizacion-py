"""Refactored main application entry point using new architecture."""
from pathlib import Path

# Import new architecture components
from core.config.config_manager import ConfigManager
from core.authentication.authentication_service import AuthenticationService, FileSessionStorage
from core.services.campaign_service import CampaignService
from core.services.segment_service import SegmentService
from infrastructure.browser.browser_manager import BrowserManager
from infrastructure.excel.excel_manager import ExcelManager
from shared.utils import data_path, storage_state_path

# Backward compatibility imports
from utils import load_config
from logger import get_logger

logger = get_logger()


def main_with_new_architecture():
    """Main function using the new refactored architecture."""
    try:
        logger.info("🚀 Starting application with refactored architecture")

        # Initialize configuration manager
        config_manager = ConfigManager()
        config_path = Path("config.yaml")
        config = config_manager.load(config_path)

        # Initialize services
        campaign_service = CampaignService()
        segment_service = SegmentService()

        # Initialize browser manager
        browser_manager = BrowserManager(config_manager)

        # Initialize authentication service
        session_storage = FileSessionStorage(storage_state_path())
        auth_service = AuthenticationService(config_manager, session_storage)

        # Initialize Excel manager
        excel_manager = ExcelManager()

        logger.success("✅ All services initialized successfully")

        # Example usage - can be extended based on specific operations needed
        with browser_manager as browser:
            context = browser.create_context(storage_state_path())
            page = browser.new_page()

            # Authenticate
            auth_service.authenticate(page, context)

            # Load campaigns to process
            campaigns = campaign_service.load_campaigns_to_search()
            logger.info(f"📊 Loaded {len(campaigns)} campaigns for processing")

            # Process each campaign (example - actual implementation would vary)
            for campaign_id, campaign_name in campaigns:
                logger.info(f"📈 Processing campaign: {campaign_name} (ID: {campaign_id})")

                # Generate report filename
                report_filename = campaign_service.generate_report_filename(
                    campaign_name,
                    "20240101"  # This would come from actual data
                )

                logger.info(f"📄 Report will be saved as: {report_filename}")

        logger.success("✅ Application completed successfully")

    except Exception as e:
        logger.error(f"❌ Application failed: {e}")
        raise


if __name__ == "__main__":
    main_with_new_architecture()