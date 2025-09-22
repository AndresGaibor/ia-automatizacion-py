"""
Integration tests for Scraping Suscriptores endpoints
Tests scraping functionality with safe data practices
"""
import pytest
from unittest.mock import Mock, patch
from playwright.sync_api import Page

from src.scraping.endpoints.suscriptores import SubscribersScraper
from src.api.models.campanias import CampaignBasicInfo
from src.scraping.models.suscriptores import (
    SubscriberExtractionConfig,
    CampaignSubscriberReport,
    SubscriberScrapingData
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
            id=12345,
            name="Test Campaign",
            date_sent="2024-01-15"
        )

    @pytest.fixture
    def scraper_config(self):
        """Scraper configuration for tests"""
        return SubscriberExtractionConfig(
            extract_hard_bounces=True,
            extract_no_abiertos=True,
            use_optimized_extraction=True
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

        # Mock table with data
        mock_table = Mock()
        mock_table.count.return_value = 1
        mock_page.locator.return_value.filter.return_value = mock_table

        # Mock table rows
        mock_rows = Mock()
        mock_rows.count.return_value = 3  # Header + 2 data rows
        mock_table.locator.return_value = mock_rows

        # Mock individual row data
        mock_row_data = Mock()
        mock_row_data.count.return_value = 4
        mock_row_data.nth.return_value.inner_text.side_effect = [
            "test@example.com", "Test List", "Active", "Good"
        ]
        mock_rows.nth.return_value.locator.return_value = mock_row_data

        result = scraper.extraer_suscriptores_tabla(mock_page, 4)
        assert isinstance(result, list)
        # Should extract 2 rows (excluding header)
        assert len(result) == 2

    def test_navegar_a_detalle_suscriptores_mock(self, mock_page, sample_campaign, test_logger):
        """Test navigation to subscriber details with mock"""
        scraper = SubscribersScraper()

        # Mock successful navigation
        mock_link = Mock()
        mock_page.get_by_role.return_value = mock_link

        result = scraper.navegar_a_detalle_suscriptores(mock_page, sample_campaign.id)

        # Verify navigation calls
        expected_url = f"/report/campaign/{sample_campaign.id}/"
        mock_page.goto.assert_called()
        mock_page.get_by_role.assert_called_with("link", name="Detalles suscriptores")
        mock_link.click.assert_called()
        assert result is True

    def test_navegar_a_detalle_suscriptores_error(self, mock_page, sample_campaign, test_logger):
        """Test navigation error handling"""
        scraper = SubscribersScraper()

        # Mock navigation error
        mock_page.goto.side_effect = Exception("Navigation failed")

        result = scraper.navegar_a_detalle_suscriptores(mock_page, sample_campaign.id)
        assert result is False

    def test_extraer_datos_filtro_mock(self, mock_page, sample_campaign, test_logger):
        """Test filter data extraction with mock"""
        scraper = SubscribersScraper()

        # Mock pagination
        with patch('src.scraping.endpoints.suscriptores.obtener_total_paginas') as mock_paginas:
            mock_paginas.return_value = 1

            # Mock table extraction
            with patch.object(scraper, 'extraer_suscriptores_tabla') as mock_extract:
                mock_extract.return_value = []

                result = scraper.extraer_datos_filtro(mock_page, sample_campaign, "Test Filter")

                assert result.filter_type == "Test Filter"
                assert result.total_pages == 1
                assert len(result.subscribers) == 0

    def test_extraer_suscriptores_completos_config(self, mock_page, sample_campaign, scraper_config, test_logger):
        """Test complete subscriber extraction with configuration"""
        scraper = SubscribersScraper()

        # Mock the optimized extraction method
        with patch.object(scraper, 'extraer_suscriptores_optimizado') as mock_optimized:
            mock_optimized.return_value = ([], [])  # Empty hard bounces and no abiertos

            result = scraper.extraer_suscriptores_completos(
                mock_page, sample_campaign, sample_campaign.id, scraper_config
            )

            assert isinstance(result, CampaignSubscriberReport)
            assert result.campaign_id == sample_campaign.id
            assert result.campaign_name == sample_campaign.name
            mock_optimized.assert_called_once()

    def test_extraer_suscriptores_completos_individual_extraction(self, mock_page, sample_campaign, test_logger):
        """Test individual extraction mode"""
        scraper = SubscribersScraper()

        # Configure for individual extraction
        config = SubscriberExtractionConfig(
            extract_hard_bounces=True,
            extract_no_abiertos=True,
            use_optimized_extraction=False  # Individual extraction
        )

        # Mock individual extraction methods
        with patch.object(scraper, 'extraer_hard_bounces') as mock_hard_bounces:
            with patch.object(scraper, 'extraer_no_abiertos') as mock_no_abiertos:
                mock_hard_bounces.return_value = []
                mock_no_abiertos.return_value = []

                result = scraper.extraer_suscriptores_completos(
                    mock_page, sample_campaign, sample_campaign.id, config
                )

                assert isinstance(result, CampaignSubscriberReport)
                mock_hard_bounces.assert_called_once()
                mock_no_abiertos.assert_called_once()

    def test_subscriber_scraping_data_creation(self, test_logger):
        """Test SubscriberScrapingData model creation"""
        data = SubscriberScrapingData(
            proyecto="Test Campaign",
            lista="Test List",
            correo="test@example.com",
            lista2="Test List",
            estado="Active",
            calidad="Good"
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
                    date_sent="2024-01-01"
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
            extract_hard_bounces=False,
            extract_no_abiertos=True,
            use_optimized_extraction=False
        )

        assert config.extract_hard_bounces is False
        assert config.extract_no_abiertos is True
        assert config.use_optimized_extraction is False

    def test_campaign_subscriber_report_creation(self):
        """Test report model creation and properties"""
        report = CampaignSubscriberReport(
            campaign_id=12345,
            campaign_name="Test Campaign",
            fecha_envio="2024-01-15"
        )

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
            calidad="Poor"
        )

        no_abierto_data = SubscriberScrapingData(
            proyecto="Test Campaign",
            lista="Test List",
            correo="noopen@example.com",
            lista2="Test List",
            estado="Not Opened",
            calidad="Good"
        )

        report = CampaignSubscriberReport(
            campaign_id=12345,
            campaign_name="Test Campaign",
            fecha_envio="2024-01-15",
            hard_bounces=[hard_bounce_data],
            no_abiertos=[no_abierto_data]
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

    def test_pagination_helpers_mock(self, mock_page, test_logger):
        """Test pagination helper functions with mocks"""
        from src.utils import obtener_total_paginas, navegar_siguiente_pagina

        # Mock pagination elements
        mock_pagination = Mock()
        mock_pagination.count.return_value = 5
        mock_page.locator.return_value = mock_pagination

        # Mock pagination logic (simplified)
        with patch('src.utils.obtener_total_paginas') as mock_get_pages:
            mock_get_pages.return_value = 3

            pages = obtener_total_paginas(mock_page)
            assert pages == 3

    def test_navigation_helpers_mock(self, mock_page, test_logger):
        """Test navigation helper functions with mocks"""
        from src.utils import navegar_siguiente_pagina

        # Mock next page navigation
        mock_next_button = Mock()
        mock_page.locator.return_value = mock_next_button

        with patch('src.utils.navegar_siguiente_pagina') as mock_nav:
            mock_nav.return_value = True

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

        # Mock large pagination
        with patch('src.scraping.endpoints.suscriptores.obtener_total_paginas') as mock_pages:
            mock_pages.return_value = 100  # Simulate 100 pages

            # Mock efficient table extraction
            with patch.object(scraper, 'extraer_suscriptores_tabla') as mock_extract:
                # Simulate 50 subscribers per page
                mock_subscribers = [
                    Mock(correo=f"user{i}@example.com", lista="Test", estado="Active", calidad="Good")
                    for i in range(50)
                ]
                mock_extract.return_value = mock_subscribers

                # Mock navigation
                with patch('src.scraping.endpoints.suscriptores.navegar_siguiente_pagina') as mock_nav:
                    mock_nav.return_value = True

                    result = scraper.extraer_datos_filtro(mock_page, sample_campaign, "Large Dataset")

                    # Should handle large dataset efficiently
                    assert result.total_pages == 100
                    # Should call extract for each page
                    assert mock_extract.call_count == 100

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
                calidad="Good"
            )
            large_subscriber_list.append(subscriber)

        # Test that we can handle large lists
        assert len(large_subscriber_list) == 10000
        assert all(sub.correo.startswith("user") for sub in large_subscriber_list[:100])

        # Test memory cleanup simulation
        del large_subscriber_list