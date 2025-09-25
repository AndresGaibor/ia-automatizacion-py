"""
Pytest configuration and shared fixtures for integration tests
"""
import pytest
import os
import tempfile
import time
from datetime import datetime
import pandas as pd

from src.api import API
from src.utils import load_config
from src.logger import get_logger


@pytest.fixture(scope="session")
def test_config():
    """Load test configuration"""
    config = load_config()
    if not config:
        pytest.skip("No configuration file found")
    return config


@pytest.fixture(scope="session")
def api_client(test_config):
    """Create API client for tests"""
    api = API()
    yield api
    api.close()


@pytest.fixture
def test_logger():
    """Get logger for tests"""
    return get_logger()


@pytest.fixture
def test_data_manager():
    """Manager for creating and cleaning up test data"""
    created_lists = []
    created_subscribers = []

    class TestDataManager:
        def __init__(self):
            self.created_lists = created_lists
            self.created_subscribers = created_subscribers
            self.test_prefix = f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        def create_test_list_name(self, base_name: str) -> str:
            """Create a unique test list name"""
            return f"{self.test_prefix}_{base_name}"

        def create_test_email(self, base_email: str) -> str:
            """Create a unique test email"""
            local, domain = base_email.split('@')
            return f"{local}+{self.test_prefix}@{domain}"

        def register_created_list(self, list_id: int, list_name: str):
            """Register a list for cleanup"""
            self.created_lists.append({"id": list_id, "name": list_name})

        def register_created_subscriber(self, list_id: int, email: str):
            """Register a subscriber for cleanup"""
            self.created_subscribers.append({"list_id": list_id, "email": email})

        def cleanup_test_data(self, api: API):
            """Clean up all test data"""
            logger = get_logger()

            # Clean up subscribers first
            for sub in self.created_subscribers:
                try:
                    api.suscriptores.delete_subscriber(sub["list_id"], sub["email"])
                    logger.info(f"Cleaned up subscriber: {sub['email']} from list {sub['list_id']}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup subscriber {sub['email']}: {e}")

            # Clean up lists
            for lst in self.created_lists:
                try:
                    api.suscriptores.delete_list(lst["id"])
                    logger.info(f"Cleaned up list: {lst['name']} (ID: {lst['id']})")
                except Exception as e:
                    logger.warning(f"Failed to cleanup list {lst['name']}: {e}")

    manager = TestDataManager()
    yield manager

    # Cleanup after test
    try:
        api = API()
        manager.cleanup_test_data(api)
        api.close()
    except Exception as e:
        print(f"Warning: Failed to cleanup test data: {e}")


@pytest.fixture
def sample_subscriber_data():
    """Sample subscriber data for testing"""
    return {
        "email": "test@example.com",
        "nombre": "Test User",
        "apellido": "Lastname",
        "telefono": "+34123456789"
    }


@pytest.fixture
def sample_excel_data():
    """Create sample Excel data for testing"""
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        df = pd.DataFrame([
            {"email": "test1@example.com", "nombre": "Test 1", "apellido": "User"},
            {"email": "test2@example.com", "nombre": "Test 2", "apellido": "User"},
            {"email": "test3@example.com", "nombre": "Test 3", "apellido": "User"}
        ])
        df.to_excel(tmp.name, index=False, sheet_name="Test_Sheet")
        yield tmp.name
        os.unlink(tmp.name)


@pytest.fixture
def list_config():
    """Default list configuration for tests"""
    return {
        "sender_email": "test@example.com",
        "company": "Test Company",
        "country": "España",
        "city": "Madrid",
        "address": "Test Address 123",
        "phone": "+34 900 000 000"
    }


@pytest.fixture
def rate_limit_helper():
    """Helper to respect API rate limits during tests"""
    class RateLimitHelper:
        def __init__(self):
            self.last_call = {}

        def wait_if_needed(self, endpoint: str, min_interval: float = 0.2):
            """Wait if needed to respect rate limits"""
            now = time.time()
            if endpoint in self.last_call:
                elapsed = now - self.last_call[endpoint]
                if elapsed < min_interval:
                    time.sleep(min_interval - elapsed)
            self.last_call[endpoint] = time.time()

    return RateLimitHelper()


@pytest.fixture
def integration_test_marker():
    """Mark test as integration test"""
    return pytest.mark.integration


@pytest.fixture
def destructive_test_marker():
    """Mark test as potentially destructive (creates/deletes data)"""
    return pytest.mark.destructive


@pytest.fixture
def slow_test_marker():
    """Mark test as slow (might take longer to run)"""
    return pytest.mark.slow


# Pytest configuration
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "destructive: marks tests as potentially destructive")
    config.addinivalue_line("markers", "slow: marks tests as slow running")
    config.addinivalue_line("markers", "api: marks tests for API endpoints")
    config.addinivalue_line("markers", "scraping: marks tests for scraping endpoints")


def pytest_collection_modifyitems(config, items):
    """Auto-mark integration tests"""
    for item in items:
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        if "test_api" in item.nodeid:
            item.add_marker(pytest.mark.api)
        if "test_scraping" in item.nodeid:
            item.add_marker(pytest.mark.scraping)