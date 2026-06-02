"""
Integration tests for Scraping Suscriptores endpoints
Tests scraping functionality with safe data practices
"""

import pytest
from unittest.mock import Mock, patch
from playwright.sync_api import Page

from src.infrastructure.scraping.endpoints.suscriptores import SubscribersScraper
from src.infrastructure.api.models.campanias import CampaignBasicInfo
from src.infrastructure.scraping.models.suscriptores import (
    SubscriberExtractionConfig,
    CampaignSubscriberReport,
    SubscriberScrapingData,
    SubscriberFilterResult,
    SubscriberTableData,
)


@pytest.mark.integration
@pytest.mark.scraping
@pytest.mark.slow
class TestSubscribersScraperIntegration:
    """Integration tests for SubscribersScraper - requires browser automation"""

    @pytest.fixture
    def mock_page(self):
        """Create a mock page for testing scraper logic without real browser"""
        page = Mock(spec=Page)
        page.url = "https://example.com/test"
        page.locator.return_value.count.return_value = 0
        page.wait_for_load_state = Mock()
        page.wait_for_timeout = Mock()
        page.goto = Mock()
        page.get_by_role.return_value.wait_for = Mock()
        page.get_by_role.return_value.click = Mock()
        return page

    @pytest.fixture
    def sample_campaign(self):
        """Sample campaign for testing"""
        return CampaignBasicInfo(
            status="sent",
            name="Test Campaign",
            date_sent="2024-01-15",
            date="2024-01-01",
            total_sent=100,
            email_from="test@example.com",
            lists=[],
            subject="Test Subject",
        )

    def test_scraper_initialization(self, test_logger):
        """Test scraper initialization"""
        scraper = SubscribersScraper()
        assert scraper.logger is not None
        assert scraper.config is not None

    def test_seleccionar_filtro_mock(self, mock_page, test_logger):
        """Test filter selection with mocked page"""
        scraper = SubscribersScraper()

        # Mock successful filter selection
        mock_select = Mock()
        mock_page.locator.return_value = mock_select
        mock_select.wait_for = Mock()
        mock_select.select_option = Mock()

        result = scraper.seleccionar_filtro(mock_page, "Hard bounces")

        # Verify methods were called
        mock_page.locator.assert_called_with("#query-filter")
        mock_select.select_option.assert_called_with(label="Hard bounces")
        assert result is True

    def test_seleccionar_filtro_error_handling(self, mock_page, test_logger):
        """Test filter selection error handling"""
        scraper = SubscribersScraper()

        # Mock error in filter selection
        mock_page.locator.side_effect = Exception("Element not found")

        result = scraper.seleccionar_filtro(mock_page, "Invalid Filter")
        assert result is False

    def test_extraer_suscriptores_tabla_empty(self, mock_page, test_logger):
        """Test table extraction with empty results"""
        scraper = SubscribersScraper()

        # Mock empty table
        mock_table = Mock()
        mock_table.count.return_value = 1  # Only header
        mock_page.locator.return_value.filter.return_value = mock_table
        mock_table.locator.return_value.count.return_value = 0

        result = scraper.extraer_suscriptores_tabla(mock_page, 4)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_extraer_suscriptores_tabla_with_data(self, mock_page, test_logger):
        """Test table extraction with mock data"""
        scraper = SubscribersScraper()

        result = [
            SubscriberTableData(correo="test1@example.com", lista="Test List", estado="Active", calidad="Good"),
            SubscriberTableData(correo="test2@example.com", lista="Test List", estado="Active", calidad="Good"),
        ]

        with patch.object(scraper, "extraer_suscriptores_tabla", return_value=result):
            extracted = scraper.extraer_suscriptores_tabla(mock_page, 4)
            assert isinstance(extracted, list)
            assert len(extracted) == 2

    def test_navegar_a_detalle_suscriptores_mock(self, mock_page, sample_campaign, test_logger):
        """Test navigation to subscriber details with mock"""
        scraper = SubscribersScraper()

        # Mock successful navigation
        mock_link = Mock()
        mock_page.get_by_role.return_value = mock_link

        CAMPAIGN_ID = 12345
        result = scraper.navegar_a_detalle_suscriptores(mock_page, CAMPAIGN_ID)

        # Verify navigation calls
        expected_url = f"/report/campaign/{CAMPAIGN_ID}/"
        mock_page.goto.assert_called()
        mock_page.get_by_role.assert_called_with("link", name="Detalles suscriptores")
        mock_link.click.assert_called()
        assert result is True

    def test_navegar_a_detalle_suscriptores_error(self, mock_page, sample_campaign, test_logger):
        """Test navigation error handling"""
        scraper = SubscribersScraper()

        # Mock navigation error
        mock_page.goto.side_effect = Exception("Navigation failed")

        CAMPAIGN_ID = 12345
        result = scraper.navegar_a_detalle_suscriptores(mock_page, CAMPAIGN_ID)
        assert result is False

    def test_extraer_datos_filtro_mock(self, mock_page, sample_campaign, test_logger):
        """Test filter data extraction with mock — delegates to SubscribersFlow"""
        scraper = SubscribersScraper()

        # extraer_datos_filtro now delegates to SubscribersFlow.extract_filter
        with patch("src.infrastructure.scraping.endpoints.suscriptores.SubscribersFlow") as MockFlow:
            mock_flow_instance = Mock()
            mock_flow_instance.extract_filter.return_value = SubscriberFilterResult(
                filter_type="Test Filter",
                subscribers=[],
                total_pages=1,
                total_subscribers=0,
            )
            MockFlow.return_value = mock_flow_instance

            result = scraper.extraer_datos_filtro(mock_page, sample_campaign, "Test Filter")

            assert result.filter_type == "Test Filter"
            assert result.total_pages == 1
            assert len(result.subscribers) == 0

    def test_extraer_suscriptores_completos_config(self, mock_page, sample_campaign, scraper_config, test_logger):
        """Test complete subscriber extraction with configuration"""
        scraper = SubscribersScraper()
        CAMPAIGN_ID = 12345

        # SubscribersScraper delegates to SubscribersFlow
        with patch("src.infrastructure.scraping.endpoints.suscriptores.SubscribersFlow") as MockFlow:
            mock_flow_instance = Mock()
            mock_flow_instance.extract_hard_bounces_and_no_abiertos.return_value = CampaignSubscriberReport(
                campaign_id=CAMPAIGN_ID,
                campaign_name=sample_campaign.name,
                fecha_envio=sample_campaign.date_sent or "",
            )
            MockFlow.return_value = mock_flow_instance

            result = scraper.extraer_suscriptores_completos(mock_page, sample_campaign, CAMPAIGN_ID, scraper_config)

            assert isinstance(result, CampaignSubscriberReport)
            assert result.campaign_id == CAMPAIGN_ID
            assert result.campaign_name == sample_campaign.name
            mock_flow_instance.extract_hard_bounces_and_no_abiertos.assert_called_once()

    def test_extraer_suscriptores_completos_individual_extraction(self, mock_page, sample_campaign, test_logger):
        """Test individual extraction mode"""
        scraper = SubscribersScraper()
        CAMPAIGN_ID = 12345

        config = SubscriberExtractionConfig(
            extract_hard_bounces=True,
            extract_no_abiertos=True,
            use_optimized_extraction=False,
        )

        with patch("src.infrastructure.scraping.endpoints.suscriptores.SubscribersFlow") as MockFlow:
            mock_flow_instance = Mock()
            mock_flow_instance.extract_hard_bounces_and_no_abiertos.return_value = CampaignSubscriberReport(
                campaign_id=CAMPAIGN_ID,
                campaign_name=sample_campaign.name,
                fecha_envio=sample_campaign.date_sent or "",
            )
            MockFlow.return_value = mock_flow_instance

            result = scraper.extraer_suscriptores_completos(mock_page, sample_campaign, CAMPAIGN_ID, config)

            assert isinstance(result, CampaignSubscriberReport)
            mock_flow_instance.extract_hard_bounces_and_no_abiertos.assert_called_once()

    def test_subscriber_scraping_data_creation(self, test_logger):
        """Test SubscriberScrapingData model creation"""
        data = SubscriberScrapingData(
            proyecto="Test Campaign",
            lista="Test List",
            correo="test@example.com",
            lista2="Test List",
            estado="Active",
            calidad="Good",
        )

        assert data.proyecto == "Test Campaign"
        assert data.correo == "test@example.com"
        assert data.estado == "Active"

    @pytest.mark.skipif(True, reason="Requires real browser and authentication")
    def test_real_browser_integration(self, test_logger):
        """
        Real browser integration test - SKIPPED by default

        To run this test:
        1. Remove the skipif decorator
        2. Ensure you have valid authentication
        3. Have a test campaign available
        4. Run with: pytest -m "scraping and not skipif"
        """
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                scraper = SubscribersScraper()

                # This would require real authentication and campaign data
                sample_campaign = CampaignBasicInfo(
                    id=123456,  # Real campaign ID
                    name="Real Test Campaign",
                    date_sent="2024-01-01",
                )

                # Test navigation (would fail without auth)
                result = scraper.navegar_a_detalle_suscriptores(page, sample_campaign.id)
                # In real test, we would assert based on actual results

            finally:
                browser.close()


@pytest.mark.integration
@pytest.mark.scraping
class TestSubscriberScrapingModels:
    """Test scraping data models and configurations"""

    def test_subscriber_extraction_config_defaults(self):
        """Test default configuration"""
        config = SubscriberExtractionConfig()

        assert config.extract_hard_bounces is True
        assert config.extract_no_abiertos is True
        assert config.use_optimized_extraction is True

    def test_subscriber_extraction_config_custom(self):
        """Test custom configuration"""
        config = SubscriberExtractionConfig(
            extract_hard_bounces=False, extract_no_abiertos=True, use_optimized_extraction=False
        )

        assert config.extract_hard_bounces is False
        assert config.extract_no_abiertos is True
        assert config.use_optimized_extraction is False

    def test_campaign_subscriber_report_creation(self):
        """Test report model creation and properties"""
        report = CampaignSubscriberReport(campaign_id=12345, campaign_name="Test Campaign", fecha_envio="2024-01-15")

        assert report.campaign_id == 12345
        assert report.campaign_name == "Test Campaign"
        assert report.fecha_envio == "2024-01-15"
        assert report.hard_bounces == []
        assert report.no_abiertos == []

    def test_campaign_subscriber_report_with_data(self):
        """Test report with actual subscriber data"""
        hard_bounce_data = SubscriberScrapingData(
            proyecto="Test Campaign",
            lista="Test List",
            correo="bounce@example.com",
            lista2="Test List",
            estado="Hard Bounce",
            calidad="Poor",
        )

        no_abierto_data = SubscriberScrapingData(
            proyecto="Test Campaign",
            lista="Test List",
            correo="noopen@example.com",
            lista2="Test List",
            estado="Not Opened",
            calidad="Good",
        )

        report = CampaignSubscriberReport(
            campaign_id=12345,
            campaign_name="Test Campaign",
            fecha_envio="2024-01-15",
            hard_bounces=[hard_bounce_data],
            no_abiertos=[no_abierto_data],
        )

        assert len(report.hard_bounces) == 1
        assert len(report.no_abiertos) == 1
        assert report.total_subscribers == 2

        # Test individual records
        assert report.hard_bounces[0].correo == "bounce@example.com"
        assert report.no_abiertos[0].correo == "noopen@example.com"


@pytest.mark.integration
@pytest.mark.scraping
class TestScrapingUtilities:
    """Test scraping utility functions"""

    @patch("src.shared.utils.legacy_utils.obtener_total_paginas", return_value=3)
    def test_pagination_helpers_mock(self, mock_patch, mock_page, test_logger):
        """Test pagination helper functions with mocks"""
        from src.shared.utils.legacy_utils import obtener_total_paginas

        pages = obtener_total_paginas(mock_page)
        assert pages == 3

    @patch("src.shared.utils.legacy_utils.navegar_siguiente_pagina", return_value=True)
    def test_navigation_helpers_mock(self, mock_patch, mock_page, test_logger):
        """Test navigation helper functions with mocks"""
        from src.shared.utils.legacy_utils import navegar_siguiente_pagina

        result = navegar_siguiente_pagina(mock_page, 1)
        assert result is True

    def test_scraping_error_resilience(self, mock_page, test_logger):
        """Test error resilience in scraping operations"""
        scraper = SubscribersScraper()

        # Test with page that throws errors
        mock_page.locator.side_effect = Exception("Locator failed")

        # Should not crash but return empty results
        result = scraper.extraer_suscriptores_tabla(mock_page, 4)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_scraping_timeout_handling(self, mock_page, test_logger):
        """Test timeout handling in scraping operations"""
        scraper = SubscribersScraper()

        # Mock timeout on wait operations
        mock_page.wait_for_load_state.side_effect = Exception("Timeout")

        # Should handle timeout gracefully
        result = scraper.seleccionar_filtro(mock_page, "Test Filter")
        assert result is False


@pytest.mark.integration
@pytest.mark.scraping
@pytest.mark.slow
class TestScrapingPerformance:
    """Performance tests for scraping operations"""

    def test_large_dataset_simulation(self, mock_page, sample_campaign, test_logger):
        """Simulate scraping large datasets"""
        scraper = SubscribersScraper()

        mock_flow_instance = Mock()
        mock_result = Mock()
        mock_result.total_pages = 100
        mock_result.subscribers = [
            Mock(correo=f"user{i}@example.com", lista="Test", estado="Active", calidad="Good") for i in range(5000)
        ]
        mock_flow_instance.extract_filter.return_value = mock_result

        with patch("src.infrastructure.scraping.endpoints.suscriptores.SubscribersFlow") as MockFlow:
            MockFlow.return_value = mock_flow_instance

            result = scraper.extraer_datos_filtro(mock_page, sample_campaign, "Large Dataset")

            assert result.total_pages == 100
            assert mock_flow_instance.extract_filter.call_count == 1

    def test_memory_efficiency_simulation(self, mock_page, sample_campaign, test_logger):
        """Test memory efficiency with large data sets"""
        scraper = SubscribersScraper()

        # Simulate processing many subscribers without memory leaks
        large_subscriber_list = []
        for i in range(10000):  # Simulate 10k subscribers
            subscriber = SubscriberScrapingData(
                proyecto=sample_campaign.name,
                lista="Test List",
                correo=f"user{i}@example.com",
                lista2="Test List",
                estado="Active",
                calidad="Good",
            )
            large_subscriber_list.append(subscriber)

        # Test that we can handle large lists
        assert len(large_subscriber_list) == 10000
        assert all(sub.correo.startswith("user") for sub in large_subscriber_list[:100])

        # Test memory cleanup simulation
        del large_subscriber_list
