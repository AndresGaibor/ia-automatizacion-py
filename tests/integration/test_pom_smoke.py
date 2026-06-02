"""
POM Smoke Tests — verify migrated Page Object Model flows are importable
and their delegation chains are correctly wired.

Covers: FlujoAutenticacion, FlujoListadoReportes, FlujoSuscriptores, and their components.
Mock-based only — no real browser execution.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from playwright.sync_api import Page

# --- Flows ---
from src.infrastructure.scraping.flows.auth_flow import FlujoAutenticacion, SesionScraping
from src.infrastructure.scraping.flows.report_listing_flow import FlujoListadoReportes
from src.infrastructure.scraping.flows.subscribers_flow import FlujoSuscriptores

# --- Pages ---
from src.infrastructure.scraping.pages.login_page import PaginaLogin
from src.infrastructure.scraping.pages.reports_page import PaginaReportes
from src.infrastructure.scraping.pages.subscribers_page import PaginaSuscriptores

# --- Components ---
from src.infrastructure.scraping.components.filter_selector import ComponenteSelectorFiltro
from src.infrastructure.scraping.components.subscriber_row import ComponenteFilaSuscriptor
from src.infrastructure.scraping.components.campaign_row import FilaCampania
from src.infrastructure.scraping.components.session_guard import ComponenteGuardiaSesion

# --- Models ---
from src.infrastructure.api.models.campanias import CampaignBasicInfo
from src.infrastructure.scraping.models.suscriptores import (
    SubscriberExtractionConfig,
    DatosScrapingSuscriptor,
    ResultadoFiltroSuscriptor,
    InformeSubscriptorCampania,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_page():
    """Minimal mock Playwright page with required spec."""
    page = Mock(spec=Page)
    page.url = "https://example.com"
    page.locator.return_value.count.return_value = 0
    page.locator.return_value.wait_for = Mock()
    page.locator.return_value.select_option = Mock()
    page.locator.return_value.inner_text = Mock(return_value="")
    page.wait_for_load_state = Mock()
    page.wait_for_timeout = Mock()
    page.goto = Mock()
    page.click = Mock()
    page.get_by_role.return_value.wait_for = Mock()
    page.get_by_role.return_value.click = Mock()
    page.get_by_role.return_value.inner_text = Mock(return_value="")
    page.get_by_label.return_value.wait_for = Mock()
    page.get_by_label.return_value.fill = Mock()
    return page


@pytest.fixture
def mock_context():
    ctx = MagicMock()
    ctx.storage_state = Mock()
    return ctx


@pytest.fixture
def sample_campaign():
    return CampaignBasicInfo(
        status="sent",
        date_sent="2024-01-15",
        name="Test Campaign",
        date="2024-01-01",
        total_sent=100,
        email_from="test@example.com",
        lists=[],
        subject="Test Subject",
    )


# ============================================================================
# AUTH FLOW — login/shared nav
# ============================================================================


@pytest.mark.integration
@pytest.mark.scraping
class TestFlujoAutenticacionSmoke:
    """Smoke tests for FlujoAutenticacion and related POM components."""

    def test_auth_flow_initializes(self, mock_page, mock_context):
        """FlujoAutenticacion initializes with page and context."""
        flow = FlujoAutenticacion(mock_page, mock_context)
        assert flow._page is mock_page
        assert flow._context is mock_context

    def test_scraping_session_initializes(self):
        """SesionScraping initializes with default retry count."""
        session = SesionScraping()
        assert session._max_retries == 2

    def test_scraping_session_custom_retries(self):
        """SesionScraping accepts custom max_retries."""
        session = SesionScraping(max_retries=3)
        assert session._max_retries == 3


# ============================================================================
# LOGIN PAGE — cookie banner, login form
# ============================================================================


@pytest.mark.integration
@pytest.mark.scraping
class TestPaginaLoginSmoke:
    """Smoke tests for PaginaLogin and ComponenteGuardiaSesion."""

    def test_login_page_initializes(self, mock_page):
        """PaginaLogin initializes with page and url_base."""
        lp = PaginaLogin(mock_page, "https://acumbamail.com")
        assert lp._page is mock_page

    def test_session_guard_initializes(self, mock_page):
        """ComponenteGuardiaSesion initializes with page."""
        sg = ComponenteGuardiaSesion(mock_page)
        assert sg._page is mock_page

    @patch("src.infrastructure.scraping.pages.login_page.PaginaLogin.handle_cookies")
    def test_ensure_authenticated_raises_on_missing_config(self, mock_handle_cookies, mock_page, mock_context):
        """FlujoAutenticacion.ensure_authenticated raises ValueError when credentials not set."""
        with patch("src.infrastructure.scraping.flows.auth_flow.load_config") as mock_config:
            mock_config.return_value = {"user": "", "password": ""}
            flow = FlujoAutenticacion(mock_page, mock_context)
            with pytest.raises(ValueError, match="no configurado"):
                flow.ensure_authenticated()


# ============================================================================
# REPORTS PAGE — reports listing, campaign rows
# ============================================================================


@pytest.mark.integration
@pytest.mark.scraping
class TestPaginaReportesSmoke:
    """Smoke tests for PaginaReportes and FilaCampaniaComponent."""

    def test_reports_page_initializes(self, mock_page):
        """PaginaReportes initializes with page."""
        rp = PaginaReportes(mock_page)
        assert rp._page is mock_page

    def test_campaign_row_component_initializes(self, mock_page):
        """FilaCampania can be constructed from a locator."""
        locator = mock_page.locator("div")
        row = FilaCampania(locator, mock_page)
        assert row._element is locator

    def test_reports_page_pagination_returns_int(self, mock_page):
        """PaginaReportes.get_total_pages returns an integer page count."""
        rp = PaginaReportes(mock_page)
        mock_page.wait_for_selector = Mock()
        mock_page.wait_for_timeout = Mock()
        mock_page.locator.return_value.count.return_value = 1
        mock_page.locator.return_value.first.inner_text = Mock(return_value="5")
        result = rp.get_total_pages()
        assert isinstance(result, int)
        assert result >= 1


# ============================================================================
# SUBSCRIBERS PAGE — filter selector, subscriber row
# ============================================================================


@pytest.mark.integration
@pytest.mark.scraping
class TestPaginaSuscriptoresSmoke:
    """Smoke tests for PaginaSuscriptores, ComponenteSelectorFiltro, ComponenteFilaSuscriptor."""

    def test_subscribers_page_initializes(self, mock_page):
        """PaginaSuscriptores initializes with page."""
        sp = PaginaSuscriptores(mock_page)
        assert sp._page is mock_page

    def test_filter_selector_initializes(self, mock_page):
        """ComponenteSelectorFiltro initializes with page and selectors."""
        fs = ComponenteSelectorFiltro(mock_page)
        assert fs._page is mock_page
        assert hasattr(fs, "_selectors")

    def test_subscriber_row_component_initializes(self, mock_page):
        """ComponenteFilaSuscriptor can be constructed from a locator."""
        locator = mock_page.locator("li")
        row = ComponenteFilaSuscriptor(locator, mock_page)
        assert row._element is locator

    def test_filter_selector_select_filter_returns_bool(self, mock_page):
        """ComponenteSelectorFiltro.select_filter returns True on success."""
        fs = ComponenteSelectorFiltro(mock_page)
        mock_page.locator.return_value.select_option = Mock(return_value=True)
        mock_page.locator.return_value.wait_for = Mock()
        result = fs.select_filter("Hard bounces")
        assert isinstance(result, bool)

    def test_filter_selector_named_methods(self, mock_page):
        """ComponenteSelectorFiltro named filter methods exist and are callable."""
        fs = ComponenteSelectorFiltro(mock_page)
        mock_page.locator.return_value.select_option = Mock(return_value=True)
        mock_page.locator.return_value.wait_for = Mock()
        assert callable(fs.select_hard_bounces)
        assert callable(fs.select_no_abiertos)
        assert callable(fs.select_abiertos)


# ============================================================================
# SUBSCRIBERS FLOW — POM delegation smoke
# ============================================================================


@pytest.mark.integration
@pytest.mark.scraping
class TestFlujoSuscriptoresSmoke:
    """Smoke tests for FlujoSuscriptores POM delegation chain."""

    def test_subscribers_flow_initializes(self, mock_page, sample_campaign):
        """FlujoSuscriptores initializes with page and creates POM components."""
        flow = FlujoSuscriptores(mock_page)
        assert flow._page is mock_page
        assert isinstance(flow._subscribers_page, PaginaSuscriptores)
        assert isinstance(flow._filter_selector, ComponenteSelectorFiltro)

    def test_extract_filter_returns_subscriber_filter_result(self, mock_page, sample_campaign):
        """FlujoSuscriptores.extract_filter returns ResultadoFiltroSuscriptor."""
        mock_page.locator.return_value.select_option = Mock(return_value=True)
        mock_page.locator.return_value.wait_for = Mock()
        mock_page.locator.return_value.count.return_value = 0

        flow = FlujoSuscriptores(mock_page)
        with patch.object(flow._subscribers_page, "wait_for_table", return_value=True):
            with patch.object(flow._subscribers_page, "get_total_pages", return_value=0):
                result = flow.extract_filter(sample_campaign, 12345, "Hard bounces")
        assert isinstance(result, ResultadoFiltroSuscriptor)
        assert result.filter_type == "Hard bounces"

    def test_extract_filter_calls_filter_selector(self, mock_page, sample_campaign):
        """FlujoSuscriptores.extract_filter calls the filter selector before pagination."""
        mock_page.locator.return_value.select_option = Mock(return_value=True)
        mock_page.locator.return_value.wait_for = Mock()
        mock_page.locator.return_value.count.return_value = 0

        flow = FlujoSuscriptores(mock_page)
        with patch.object(flow._filter_selector, "select_hard_bounces", return_value=True) as mock_sel:
            with patch.object(flow._subscribers_page, "wait_for_table", return_value=True):
                with patch.object(flow._subscribers_page, "get_total_pages", return_value=0):
                    flow.extract_filter(sample_campaign, 12345, "Hard bounces")
        mock_sel.assert_called_once()

    def test_extract_hard_bounces_and_no_abiertos_returns_report(self, mock_page, sample_campaign):
        """FlujoSuscriptores.extract_hard_bounces_and_no_abiertos returns InformeSubscriptorCampania."""
        mock_page.locator.return_value.select_option = Mock(return_value=True)
        mock_page.locator.return_value.wait_for = Mock()
        mock_page.locator.return_value.count.return_value = 0

        flow = FlujoSuscriptores(mock_page)
        config = SubscriberExtractionConfig(
            extract_hard_bounces=True,
            extract_no_abiertos=True,
            use_optimized_extraction=True,
        )
        with patch.object(flow._subscribers_page, "navigate_to_detail", return_value=True):
            with patch.object(flow._subscribers_page, "wait_for_table", return_value=True):
                with patch.object(flow._subscribers_page, "get_total_pages", return_value=0):
                    report = flow.extract_hard_bounces_and_no_abiertos(sample_campaign, 12345, config)
        assert isinstance(report, InformeSubscriptorCampania)

    def test_subscribers_scraper_delegates_to_flow(self, mock_page, sample_campaign):
        """SubscribersScraper.public_api delegates to FlujoSuscriptores."""
        from src.infrastructure.scraping.endpoints.suscriptores import ScraperSuscriptores

        mock_page.locator.return_value.select_option = Mock(return_value=True)
        mock_page.locator.return_value.wait_for = Mock()
        mock_page.locator.return_value.count.return_value = 0

        scraper = ScraperSuscriptores(mock_page)
        config = SubscriberExtractionConfig(
            extract_hard_bounces=True,
            extract_no_abiertos=True,
            use_optimized_extraction=True,
        )
        with patch("src.infrastructure.scraping.endpoints.suscriptores.FlujoSuscriptores") as MockFlow:
            mock_flow_instance = Mock()
            mock_flow_instance.extract_hard_bounces_and_no_abiertos.return_value = InformeSubscriptorCampania(
                campaign_id=12345,
                campaign_name="Test Campaign",
                fecha_envio="2024-01-15",
            )
            MockFlow.return_value = mock_flow_instance

            report = scraper.extraer_suscriptores_completos(mock_page, sample_campaign, 12345, config)
            MockFlow.assert_called_once_with(mock_page)
            mock_flow_instance.extract_hard_bounces_and_no_abiertos.assert_called_once()


# ============================================================================
# REPORT LISTING FLOW — POM delegation smoke
# ============================================================================


@pytest.mark.integration
@pytest.mark.scraping
class TestFlujoListadoReportesSmoke:
    """Smoke tests for FlujoListadoReportes POM delegation chain."""

    def test_report_listing_flow_initializes(self, mock_page):
        """FlujoListadoReportes initializes with page and creates PaginaReportes."""
        flow = FlujoListadoReportes(mock_page, batch_size=5)
        assert flow._page is mock_page
        assert isinstance(flow._reports_page, PaginaReportes)
        assert flow._batch_size == 5

    @patch("src.infrastructure.scraping.pages.reports_page.PaginaReportes.optimize_items_per_page")
    @patch("src.infrastructure.scraping.pages.reports_page.PaginaReportes.get_total_pages")
    @patch("src.infrastructure.scraping.pages.reports_page.PaginaReportes.navigate_to_next_page")
    @patch("src.infrastructure.scraping.pages.reports_page.PaginaReportes.get_valid_campaign_rows")
    def test_execute_calls_reports_page_methods(self, mock_rows, mock_nav, mock_total, mock_opt, mock_page):
        """FlujoListadoReportes.execute calls PaginaReportes methods in sequence."""
        mock_page.locator.return_value.count.return_value = 0

        flow = FlujoListadoReportes(mock_page)
        mock_opt.return_value = None
        mock_total.return_value = 1
        mock_nav.return_value = False
        mock_rows.return_value = []

        with patch.object(flow, "_save_progress"):
            result = flow.execute()
        mock_opt.assert_called_once()
        mock_total.assert_called()
        mock_rows.assert_called()
        assert isinstance(result, list)
