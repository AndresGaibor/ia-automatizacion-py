"""
POM Smoke Tests — verify migrated Page Object Model flows are importable
and their delegation chains are correctly wired.

Covers: AuthFlow, ReportListingFlow, SubscribersFlow, and their components.
Mock-based only — no real browser execution.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from playwright.sync_api import Page

# --- Flows ---
from src.infrastructure.scraping.flows.auth_flow import AuthFlow, ScrapingSession
from src.infrastructure.scraping.flows.report_listing_flow import ReportListingFlow
from src.infrastructure.scraping.flows.subscribers_flow import SubscribersFlow

# --- Pages ---
from src.infrastructure.scraping.pages.login_page import LoginPage
from src.infrastructure.scraping.pages.reports_page import ReportsPage
from src.infrastructure.scraping.pages.subscribers_page import SubscribersPage

# --- Components ---
from src.infrastructure.scraping.components.filter_selector import FilterSelectorComponent
from src.infrastructure.scraping.components.subscriber_row import SubscriberRowComponent
from src.infrastructure.scraping.components.campaign_row import CampaignRow
from src.infrastructure.scraping.components.session_guard import SessionGuardComponent

# --- Models ---
from src.infrastructure.api.models.campanias import CampaignBasicInfo
from src.infrastructure.scraping.models.suscriptores import (
    SubscriberExtractionConfig,
    SubscriberScrapingData,
    SubscriberFilterResult,
    CampaignSubscriberReport,
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
class TestAuthFlowSmoke:
    """Smoke tests for AuthFlow and related POM components."""

    def test_auth_flow_initializes(self, mock_page, mock_context):
        """AuthFlow initializes with page and context."""
        flow = AuthFlow(mock_page, mock_context)
        assert flow._page is mock_page
        assert flow._context is mock_context

    def test_scraping_session_initializes(self):
        """ScrapingSession initializes with default retry count."""
        session = ScrapingSession()
        assert session._max_retries == 2

    def test_scraping_session_custom_retries(self):
        """ScrapingSession accepts custom max_retries."""
        session = ScrapingSession(max_retries=3)
        assert session._max_retries == 3


# ============================================================================
# LOGIN PAGE — cookie banner, login form
# ============================================================================


@pytest.mark.integration
@pytest.mark.scraping
class TestLoginPageSmoke:
    """Smoke tests for LoginPage and SessionGuardComponent."""

    def test_login_page_initializes(self, mock_page):
        """LoginPage initializes with page and url_base."""
        lp = LoginPage(mock_page, "https://acumbamail.com")
        assert lp._page is mock_page

    def test_session_guard_initializes(self, mock_page):
        """SessionGuardComponent initializes with page."""
        sg = SessionGuardComponent(mock_page)
        assert sg._page is mock_page

    @patch("src.infrastructure.scraping.pages.login_page.LoginPage.handle_cookies")
    def test_ensure_authenticated_raises_on_missing_config(self, mock_handle_cookies, mock_page, mock_context):
        """AuthFlow.ensure_authenticated raises ValueError when credentials not set."""
        with patch("src.infrastructure.scraping.flows.auth_flow.load_config") as mock_config:
            mock_config.return_value = {"user": "", "password": ""}
            flow = AuthFlow(mock_page, mock_context)
            with pytest.raises(ValueError, match="no configurado"):
                flow.ensure_authenticated()


# ============================================================================
# REPORTS PAGE — reports listing, campaign rows
# ============================================================================


@pytest.mark.integration
@pytest.mark.scraping
class TestReportsPageSmoke:
    """Smoke tests for ReportsPage and CampaignRowComponent."""

    def test_reports_page_initializes(self, mock_page):
        """ReportsPage initializes with page."""
        rp = ReportsPage(mock_page)
        assert rp._page is mock_page

    def test_campaign_row_component_initializes(self, mock_page):
        """CampaignRow can be constructed from a locator."""
        locator = mock_page.locator("div")
        row = CampaignRow(locator, mock_page)
        assert row._element is locator

    def test_reports_page_pagination_returns_int(self, mock_page):
        """ReportsPage.get_total_pages returns an integer page count."""
        rp = ReportsPage(mock_page)
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
class TestSubscribersPageSmoke:
    """Smoke tests for SubscribersPage, FilterSelectorComponent, SubscriberRowComponent."""

    def test_subscribers_page_initializes(self, mock_page):
        """SubscribersPage initializes with page."""
        sp = SubscribersPage(mock_page)
        assert sp._page is mock_page

    def test_filter_selector_initializes(self, mock_page):
        """FilterSelectorComponent initializes with page and selectors."""
        fs = FilterSelectorComponent(mock_page)
        assert fs._page is mock_page
        assert hasattr(fs, "_selectors")

    def test_subscriber_row_component_initializes(self, mock_page):
        """SubscriberRowComponent can be constructed from a locator."""
        locator = mock_page.locator("li")
        row = SubscriberRowComponent(locator, mock_page)
        assert row._element is locator

    def test_filter_selector_select_filter_returns_bool(self, mock_page):
        """FilterSelectorComponent.select_filter returns True on success."""
        fs = FilterSelectorComponent(mock_page)
        mock_page.locator.return_value.select_option = Mock(return_value=True)
        mock_page.locator.return_value.wait_for = Mock()
        result = fs.select_filter("Hard bounces")
        assert isinstance(result, bool)

    def test_filter_selector_named_methods(self, mock_page):
        """FilterSelectorComponent named filter methods exist and are callable."""
        fs = FilterSelectorComponent(mock_page)
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
class TestSubscribersFlowSmoke:
    """Smoke tests for SubscribersFlow POM delegation chain."""

    def test_subscribers_flow_initializes(self, mock_page, sample_campaign):
        """SubscribersFlow initializes with page and creates POM components."""
        flow = SubscribersFlow(mock_page)
        assert flow._page is mock_page
        assert isinstance(flow._subscribers_page, SubscribersPage)
        assert isinstance(flow._filter_selector, FilterSelectorComponent)

    def test_extract_filter_returns_subscriber_filter_result(self, mock_page, sample_campaign):
        """SubscribersFlow.extract_filter returns SubscriberFilterResult."""
        mock_page.locator.return_value.select_option = Mock(return_value=True)
        mock_page.locator.return_value.wait_for = Mock()
        mock_page.locator.return_value.count.return_value = 0

        flow = SubscribersFlow(mock_page)
        with patch.object(flow._subscribers_page, "wait_for_table", return_value=True):
            with patch.object(flow._subscribers_page, "get_total_pages", return_value=0):
                result = flow.extract_filter(sample_campaign, 12345, "Hard bounces")
        assert isinstance(result, SubscriberFilterResult)
        assert result.filter_type == "Hard bounces"

    def test_extract_filter_calls_filter_selector(self, mock_page, sample_campaign):
        """SubscribersFlow.extract_filter calls the filter selector before pagination."""
        mock_page.locator.return_value.select_option = Mock(return_value=True)
        mock_page.locator.return_value.wait_for = Mock()
        mock_page.locator.return_value.count.return_value = 0

        flow = SubscribersFlow(mock_page)
        with patch.object(flow._filter_selector, "select_hard_bounces", return_value=True) as mock_sel:
            with patch.object(flow._subscribers_page, "wait_for_table", return_value=True):
                with patch.object(flow._subscribers_page, "get_total_pages", return_value=0):
                    flow.extract_filter(sample_campaign, 12345, "Hard bounces")
        mock_sel.assert_called_once()

    def test_extract_hard_bounces_and_no_abiertos_returns_report(self, mock_page, sample_campaign):
        """SubscribersFlow.extract_hard_bounces_and_no_abiertos returns CampaignSubscriberReport."""
        mock_page.locator.return_value.select_option = Mock(return_value=True)
        mock_page.locator.return_value.wait_for = Mock()
        mock_page.locator.return_value.count.return_value = 0

        flow = SubscribersFlow(mock_page)
        config = SubscriberExtractionConfig(
            extract_hard_bounces=True,
            extract_no_abiertos=True,
            use_optimized_extraction=True,
        )
        with patch.object(flow._subscribers_page, "navigate_to_detail", return_value=True):
            with patch.object(flow._subscribers_page, "wait_for_table", return_value=True):
                with patch.object(flow._subscribers_page, "get_total_pages", return_value=0):
                    report = flow.extract_hard_bounces_and_no_abiertos(sample_campaign, 12345, config)
        assert isinstance(report, CampaignSubscriberReport)

    def test_subscribers_scraper_delegates_to_flow(self, mock_page, sample_campaign):
        """SubscribersScraper.public_api delegates to SubscribersFlow."""
        from src.infrastructure.scraping.endpoints.suscriptores import SubscribersScraper

        mock_page.locator.return_value.select_option = Mock(return_value=True)
        mock_page.locator.return_value.wait_for = Mock()
        mock_page.locator.return_value.count.return_value = 0

        scraper = SubscribersScraper(mock_page)
        config = SubscriberExtractionConfig(
            extract_hard_bounces=True,
            extract_no_abiertos=True,
            use_optimized_extraction=True,
        )
        with patch("src.infrastructure.scraping.endpoints.suscriptores.SubscribersFlow") as MockFlow:
            mock_flow_instance = Mock()
            mock_flow_instance.extract_hard_bounces_and_no_abiertos.return_value = CampaignSubscriberReport(
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
class TestReportListingFlowSmoke:
    """Smoke tests for ReportListingFlow POM delegation chain."""

    def test_report_listing_flow_initializes(self, mock_page):
        """ReportListingFlow initializes with page and creates ReportsPage."""
        flow = ReportListingFlow(mock_page, batch_size=5)
        assert flow._page is mock_page
        assert isinstance(flow._reports_page, ReportsPage)
        assert flow._batch_size == 5

    @patch("src.infrastructure.scraping.pages.reports_page.ReportsPage.optimize_items_per_page")
    @patch("src.infrastructure.scraping.pages.reports_page.ReportsPage.get_total_pages")
    @patch("src.infrastructure.scraping.pages.reports_page.ReportsPage.navigate_to_next_page")
    @patch("src.infrastructure.scraping.pages.reports_page.ReportsPage.get_valid_campaign_rows")
    def test_execute_calls_reports_page_methods(self, mock_rows, mock_nav, mock_total, mock_opt, mock_page):
        """ReportListingFlow.execute calls ReportsPage methods in sequence."""
        mock_page.locator.return_value.count.return_value = 0

        flow = ReportListingFlow(mock_page)
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
