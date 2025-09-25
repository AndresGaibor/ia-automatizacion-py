"""
Unit test configuration and fixtures
"""
import pytest
import os
import tempfile
import yaml
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List
import pandas as pd

from src.shared.logging import get_logger
from src.core.config.config_manager import ConfigManager


@pytest.fixture
def mock_config():
    """Mock configuration for unit tests"""
    return {
        'url': 'https://acumbamail.com/app/newsletter/',
        'url_base': 'https://acumbamail.com',
        'user': 'test@example.com',
        'password': 'testpass',
        'headless': True,
        'debug': False,
        'api': {
            'base_url': 'https://acumbamail.com/api/1/',
            'api_key': 'test_api_key'
        },
        'logging': {
            'enabled': True,
            'level': 'normal',
            'console_output': False,
            'file_output': True,
            'performance_tracking': True,
            'emoji_style': True,
            'structured_format': False
        }
    }


@pytest.fixture
def mock_logger():
    """Mock logger for testing"""
    logger = Mock()
    logger.info = Mock()
    logger.error = Mock()
    logger.warning = Mock()
    logger.debug = Mock()
    logger.start_timer = Mock()
    logger.end_timer = Mock()
    logger.print_performance_report = Mock()
    return logger


@pytest.fixture
def temp_config_file(mock_config):
    """Create temporary config file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(mock_config, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    os.unlink(temp_path)


@pytest.fixture
def temp_excel_file():
    """Create temporary Excel file for testing"""
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        df = pd.DataFrame([
            {"email": "test1@example.com", "nombre": "Test 1", "apellido": "User 1"},
            {"email": "test2@example.com", "nombre": "Test 2", "apellido": "User 2"},
            {"email": "test3@example.com", "nombre": "Test 3", "apellido": "User 3"}
        ])
        df.to_excel(tmp.name, index=False, sheet_name="Test_Sheet")
        yield tmp.name
        os.unlink(tmp.name)


@pytest.fixture
def mock_browser_context():
    """Mock browser context for testing"""
    context = Mock()
    context.new_page = Mock()
    context.close = Mock()
    context.storage_state = Mock(return_value={})
    return context


@pytest.fixture
def mock_browser_page():
    """Mock browser page for testing"""
    page = Mock()
    page.goto = Mock()
    page.get_by_role = Mock()
    page.get_by_text = Mock()
    page.locator = Mock()
    page.fill = Mock()
    page.click = Mock()
    page.wait_for_load_state = Mock()
    page.screenshot = Mock()
    page.close = Mock()
    return page


@pytest.fixture
def mock_playwright():
    """Mock Playwright instance for testing"""
    playwright = Mock()
    browser = Mock()
    browser.new_context = Mock()
    playwright.chromium.launch = Mock(return_value=browser)
    return playwright


@pytest.fixture
def sample_campaign_data():
    """Sample campaign data for testing"""
    return {
        'id': '12345',
        'name': 'Test Campaign',
        'subject': 'Test Subject',
        'sender_name': 'Test Sender',
        'sender_email': 'sender@test.com',
        'created_at': '2025-01-01T12:00:00Z',
        'status': 'sent',
        'recipients': 1000,
        'opens': 250,
        'clicks': 50,
        'bounces': 10
    }


@pytest.fixture
def sample_subscriber_data():
    """Sample subscriber data for testing"""
    return {
        'email': 'test@example.com',
        'nombre': 'Test',
        'apellido': 'User',
        'telefono': '+34123456789',
        'empresa': 'Test Company',
        'campo_personalizado': 'Custom Value'
    }


@pytest.fixture
def mock_api_response():
    """Mock API response for testing"""
    def create_response(data: Any, status_code: int = 200):
        response = Mock()
        response.status_code = status_code
        response.json = Mock(return_value=data)
        response.text = str(data)
        response.ok = status_code < 400
        return response
    return create_response


@pytest.fixture
def mock_httpx_client(mock_api_response):
    """Mock HTTPX client for API testing"""
    client = Mock()

    # Default success responses
    client.get = Mock(return_value=mock_api_response({'status': 'success', 'data': []}))
    client.post = Mock(return_value=mock_api_response({'status': 'success', 'id': 123}))
    client.put = Mock(return_value=mock_api_response({'status': 'success'}))
    client.delete = Mock(return_value=mock_api_response({'status': 'success'}))

    return client


# Pytest configuration for unit tests
def pytest_configure(config):
    """Configure pytest markers for unit tests"""
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "mock: marks tests using mocks")
    config.addinivalue_line("markers", "fast: marks tests as fast running")


def pytest_collection_modifyitems(config, items):
    """Auto-mark unit tests"""
    for item in items:
        if "unit" in item.nodeid:
            item.add_marker(pytest.mark.unit)
            item.add_marker(pytest.mark.fast)
        if "mock" in item.name.lower():
            item.add_marker(pytest.mark.mock)