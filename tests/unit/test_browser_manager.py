"""
Unit tests for Browser Manager
"""
import pytest
from unittest.mock import patch, Mock

from src.infrastructure.browser.browser_manager import BrowserManager
from src.core.errors.exceptions import BrowserError


@pytest.mark.unit
class TestBrowserManager:
    """Unit tests for browser automation functionality"""

    def test_browser_manager_initialization(self, mock_config):
        """Test browser manager initialization"""
        with patch('src.infrastructure.browser.browser_manager.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            browser_manager = BrowserManager()
            assert browser_manager.headless == mock_config['headless']
            assert browser_manager.debug == mock_config['debug']

    @patch('playwright.sync_api.sync_playwright')
    def test_browser_launch_success(self, mock_playwright, mock_config):
        """Test successful browser launch"""
        with patch('src.infrastructure.browser.browser_manager.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            # Setup mocks
            mock_playwright_instance = Mock()
            mock_browser = Mock()
            mock_context = Mock()
            mock_page = Mock()

            mock_playwright.return_value.__enter__.return_value = mock_playwright_instance
            mock_playwright_instance.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page

            browser_manager = BrowserManager()
            page = browser_manager.launch_browser()

            assert page is not None
            mock_playwright_instance.chromium.launch.assert_called_once()

    @patch('playwright.sync_api.sync_playwright')
    def test_browser_launch_failure(self, mock_playwright, mock_config):
        """Test browser launch failure"""
        with patch('src.infrastructure.browser.browser_manager.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            mock_playwright.side_effect = Exception("Browser launch failed")

            browser_manager = BrowserManager()

            with pytest.raises(BrowserError, match="Browser launch failed"):
                browser_manager.launch_browser()

    def test_browser_configuration(self, mock_config):
        """Test browser configuration options"""
        with patch('src.infrastructure.browser.browser_manager.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            browser_manager = BrowserManager()
            config = browser_manager._get_browser_config()

            assert isinstance(config, dict)
            assert 'headless' in config
            assert config['headless'] == mock_config['headless']

    def test_user_agent_setup(self, mock_config):
        """Test custom user agent setup"""
        with patch('src.infrastructure.browser.browser_manager.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            browser_manager = BrowserManager()
            user_agent = browser_manager._get_user_agent()

            assert isinstance(user_agent, str)
            assert 'Chrome' in user_agent  # Should use Chrome-like user agent

    @patch('playwright.sync_api.sync_playwright')
    def test_context_creation_with_storage_state(self, mock_playwright, mock_config):
        """Test browser context creation with storage state"""
        with patch('src.infrastructure.browser.browser_manager.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            # Setup mocks
            mock_playwright_instance = Mock()
            mock_browser = Mock()
            mock_context = Mock()

            mock_playwright.return_value.__enter__.return_value = mock_playwright_instance
            mock_playwright_instance.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context

            storage_state = {'cookies': [], 'localStorage': []}

            browser_manager = BrowserManager()
            context = browser_manager.create_context(storage_state=storage_state)

            assert context is not None
            # Verify storage state was passed
            mock_browser.new_context.assert_called_once()
            call_args = mock_browser.new_context.call_args
            assert 'storage_state' in call_args[1]

    def test_viewport_configuration(self, mock_config):
        """Test viewport configuration"""
        with patch('src.infrastructure.browser.browser_manager.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            browser_manager = BrowserManager()
            viewport = browser_manager._get_viewport()

            assert viewport['width'] > 0
            assert viewport['height'] > 0

    @patch('playwright.sync_api.sync_playwright')
    def test_page_navigation(self, mock_playwright, mock_config, mock_browser_page):
        """Test page navigation functionality"""
        with patch('src.infrastructure.browser.browser_manager.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            # Setup complete mock chain
            mock_playwright_instance = Mock()
            mock_browser = Mock()
            mock_context = Mock()

            mock_playwright.return_value.__enter__.return_value = mock_playwright_instance
            mock_playwright_instance.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_browser_page

            browser_manager = BrowserManager()
            page = browser_manager.launch_browser()

            # Test navigation
            url = "https://example.com"
            browser_manager.navigate_to(page, url)

            mock_browser_page.goto.assert_called_with(url, wait_until='networkidle')

    def test_page_navigation_timeout(self, mock_browser_page, mock_config):
        """Test page navigation timeout handling"""
        with patch('src.infrastructure.browser.browser_manager.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            mock_browser_page.goto.side_effect = Exception("Navigation timeout")

            browser_manager = BrowserManager()

            with pytest.raises(BrowserError, match="Navigation failed"):
                browser_manager.navigate_to(mock_browser_page, "https://example.com")

    def test_element_interaction(self, mock_browser_page, mock_config):
        """Test element interaction methods"""
        with patch('src.infrastructure.browser.browser_manager.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            mock_element = Mock()
            mock_browser_page.get_by_role.return_value = mock_element

            browser_manager = BrowserManager()

            # Test clicking element
            browser_manager.click_element(mock_browser_page, "button", "Submit")
            mock_browser_page.get_by_role.assert_called_with("button", name="Submit")
            mock_element.click.assert_called_once()

    def test_form_filling(self, mock_browser_page, mock_config):
        """Test form filling functionality"""
        with patch('src.infrastructure.browser.browser_manager.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            mock_element = Mock()
            mock_browser_page.get_by_label.return_value = mock_element

            browser_manager = BrowserManager()

            # Test filling input field
            browser_manager.fill_input(mock_browser_page, "Email", "test@example.com")
            mock_browser_page.get_by_label.assert_called_with("Email")
            mock_element.fill.assert_called_with("test@example.com")

    def test_wait_for_element(self, mock_browser_page, mock_config):
        """Test waiting for element functionality"""
        with patch('src.infrastructure.browser.browser_manager.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            mock_element = Mock()
            mock_browser_page.get_by_text.return_value = mock_element

            browser_manager = BrowserManager()

            # Test waiting for element
            result = browser_manager.wait_for_element(mock_browser_page, "Loading complete")
            mock_browser_page.get_by_text.assert_called_with("Loading complete")
            mock_element.wait_for.assert_called_once()

    def test_element_not_found(self, mock_browser_page, mock_config):
        """Test element not found handling"""
        with patch('src.infrastructure.browser.browser_manager.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            mock_browser_page.get_by_text.side_effect = Exception("Element not found")

            browser_manager = BrowserManager()

            with pytest.raises(BrowserError, match="Element not found"):
                browser_manager.wait_for_element(mock_browser_page, "Non-existent text")

    def test_screenshot_capture(self, mock_browser_page, mock_config):
        """Test screenshot capture functionality"""
        with patch('src.infrastructure.browser.browser_manager.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            mock_browser_page.screenshot.return_value = b"fake_screenshot_data"

            browser_manager = BrowserManager()
            screenshot_data = browser_manager.take_screenshot(mock_browser_page, "test_screenshot.png")

            assert screenshot_data is not None
            mock_browser_page.screenshot.assert_called_with(path="test_screenshot.png")

    def test_storage_state_management(self, mock_browser_context, mock_config):
        """Test storage state management"""
        with patch('src.infrastructure.browser.browser_manager.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            mock_storage_state = {'cookies': [{'name': 'test', 'value': 'value'}]}
            mock_browser_context.storage_state.return_value = mock_storage_state

            browser_manager = BrowserManager()
            storage_state = browser_manager.get_storage_state(mock_browser_context)

            assert storage_state == mock_storage_state
            mock_browser_context.storage_state.assert_called_once()

    def test_cookies_management(self, mock_browser_context, mock_config):
        """Test cookies management"""
        with patch('src.infrastructure.browser.browser_manager.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            mock_cookies = [{'name': 'session', 'value': 'abc123', 'domain': 'example.com'}]
            mock_browser_context.cookies.return_value = mock_cookies

            browser_manager = BrowserManager()
            cookies = browser_manager.get_cookies(mock_browser_context)

            assert cookies == mock_cookies
            mock_browser_context.cookies.assert_called_once()

    def test_browser_cleanup(self, mock_browser_context, mock_config):
        """Test browser cleanup functionality"""
        with patch('src.infrastructure.browser.browser_manager.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            browser_manager = BrowserManager()
            browser_manager.cleanup_browser(mock_browser_context)

            mock_browser_context.close.assert_called_once()

    def test_download_handling(self, mock_browser_page, mock_config):
        """Test download handling functionality"""
        with patch('src.infrastructure.browser.browser_manager.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            mock_download = Mock()
            mock_download.path = "/tmp/downloaded_file.xlsx"
            mock_browser_page.expect_download.return_value.__enter__.return_value = mock_download

            browser_manager = BrowserManager()

            with browser_manager.handle_download(mock_browser_page) as download:
                assert download is not None

    def test_error_handling_with_screenshots(self, mock_browser_page, mock_config, mock_logger):
        """Test error handling with automatic screenshots"""
        with patch('src.infrastructure.browser.browser_manager.load_config') as mock_load_config, \
             patch('src.infrastructure.browser.browser_manager.get_logger') as mock_get_logger:

            mock_load_config.return_value = mock_config
            mock_get_logger.return_value = mock_logger

            mock_browser_page.get_by_text.side_effect = Exception("Element error")
            mock_browser_page.screenshot.return_value = b"error_screenshot"

            browser_manager = BrowserManager(capture_on_error=True)

            with pytest.raises(BrowserError):
                browser_manager.wait_for_element(mock_browser_page, "Element")

            # Should have taken a screenshot on error
            mock_browser_page.screenshot.assert_called()

    def test_mobile_viewport_emulation(self, mock_config):
        """Test mobile viewport emulation"""
        mobile_config = mock_config.copy()
        mobile_config['mobile_emulation'] = True
        mobile_config['device'] = 'iPhone 12'

        with patch('src.infrastructure.browser.browser_manager.load_config') as mock_load_config:
            mock_load_config.return_value = mobile_config

            browser_manager = BrowserManager()
            context_config = browser_manager._get_context_config()

            # Should have mobile viewport settings
            assert 'viewport' in context_config
            assert context_config['viewport']['width'] <= 414  # iPhone 12 width

    def test_custom_timeout_configuration(self, mock_config):
        """Test custom timeout configuration"""
        timeout_config = mock_config.copy()
        timeout_config['timeouts'] = {
            'navigation': 30000,
            'element_wait': 10000,
            'action': 5000
        }

        with patch('src.infrastructure.browser.browser_manager.load_config') as mock_load_config:
            mock_load_config.return_value = timeout_config

            browser_manager = BrowserManager()
            timeouts = browser_manager.get_timeouts()

            assert timeouts['navigation'] == 30000
            assert timeouts['element_wait'] == 10000
            assert timeouts['action'] == 5000

    def test_proxy_configuration(self, mock_config):
        """Test proxy configuration"""
        proxy_config = mock_config.copy()
        proxy_config['proxy'] = {
            'server': 'http://proxy.example.com:8080',
            'username': 'user',
            'password': 'pass'
        }

        with patch('src.infrastructure.browser.browser_manager.load_config') as mock_load_config:
            mock_load_config.return_value = proxy_config

            browser_manager = BrowserManager()
            browser_config = browser_manager._get_browser_config()

            assert 'proxy' in browser_config
            assert browser_config['proxy']['server'] == 'http://proxy.example.com:8080'