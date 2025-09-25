"""
E2E test configuration and fixtures
"""
import pytest
import os
import tempfile
import time
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd

from src.core.config.config_manager import ConfigManager
from src.shared.logging import get_logger
from src.infrastructure.browser.browser_manager import BrowserManager


@pytest.fixture(scope="session")
def e2e_config():
    """Load E2E test configuration"""
    try:
        config_manager = ConfigManager()
        config = config_manager.get_config()

        # Verify E2E test requirements
        required_keys = ['url', 'user', 'password', 'api']
        for key in required_keys:
            if key not in config:
                pytest.skip(f"E2E tests require '{key}' in configuration")

        return config
    except Exception as e:
        pytest.skip(f"E2E tests require valid configuration: {e}")


@pytest.fixture(scope="session")
def e2e_logger():
    """Logger for E2E tests"""
    return get_logger()


@pytest.fixture
def browser_manager(e2e_config):
    """Browser manager for E2E tests"""
    return BrowserManager()


@pytest.fixture
def test_data_manager():
    """Manager for E2E test data"""
    created_items = []
    test_files = []

    class E2ETestDataManager:
        def __init__(self):
            self.created_items = created_items
            self.test_files = test_files
            self.test_prefix = f"E2E_TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        def create_test_name(self, base_name: str) -> str:
            """Create unique test name"""
            return f"{self.test_prefix}_{base_name}"

        def create_test_excel_file(self, data: List[Dict]) -> str:
            """Create temporary Excel file for testing"""
            df = pd.DataFrame(data)

            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
                df.to_excel(f.name, index=False)
                temp_path = f.name

            self.test_files.append(temp_path)
            return temp_path

        def register_created_item(self, item_type: str, item_id: Any, item_name: str):
            """Register created item for cleanup"""
            self.created_items.append({
                'type': item_type,
                'id': item_id,
                'name': item_name,
                'created_at': datetime.now()
            })

        def cleanup_all(self):
            """Clean up all test data"""
            logger = get_logger()

            # Clean up test files
            for file_path in self.test_files:
                try:
                    if os.path.exists(file_path):
                        os.unlink(file_path)
                        logger.info(f"Cleaned up test file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup file {file_path}: {e}")

            # Note: API cleanup should be handled by specific test cleanup
            self.test_files.clear()
            self.created_items.clear()

    manager = E2ETestDataManager()
    yield manager
    manager.cleanup_all()


@pytest.fixture
def sample_subscriber_list():
    """Sample subscriber list for E2E testing"""
    return [
        {
            "email": "e2etest1@example.com",
            "nombre": "E2E Test User 1",
            "apellido": "Lastname 1",
            "telefono": "+34600000001"
        },
        {
            "email": "e2etest2@example.com",
            "nombre": "E2E Test User 2",
            "apellido": "Lastname 2",
            "telefono": "+34600000002"
        },
        {
            "email": "e2etest3@example.com",
            "nombre": "E2E Test User 3",
            "apellido": "Lastname 3",
            "telefono": "+34600000003"
        }
    ]


@pytest.fixture
def campaign_search_terms():
    """Sample campaign search terms for E2E testing"""
    return [
        {
            "Buscar": "Newsletter",
            "Nombre": "Weekly Newsletter",
            "Tipo": "Newsletter",
            "Fecha envío": "2024-12-01",
            "Listas": "",
            "Emails": "",
            "Abiertos": "",
            "Clics": ""
        },
        {
            "Buscar": "Promotion",
            "Nombre": "Holiday Promotion",
            "Tipo": "Promoción",
            "Fecha envío": "2024-12-15",
            "Listas": "",
            "Emails": "",
            "Abiertos": "",
            "Clics": ""
        }
    ]


@pytest.fixture
def list_configuration():
    """Default list configuration for E2E tests"""
    return {
        "sender_email": "e2etest@example.com",
        "company": "E2E Test Company",
        "country": "España",
        "city": "Madrid",
        "address": "Calle Test 123",
        "phone": "+34 900 123 456"
    }


@pytest.fixture
def performance_monitor():
    """Performance monitoring for E2E tests"""
    class PerformanceMonitor:
        def __init__(self):
            self.timings = {}
            self.checkpoints = []

        def start_timing(self, operation: str):
            """Start timing an operation"""
            self.timings[operation] = {'start': time.time()}

        def end_timing(self, operation: str):
            """End timing an operation"""
            if operation in self.timings:
                self.timings[operation]['end'] = time.time()
                self.timings[operation]['duration'] = (
                    self.timings[operation]['end'] - self.timings[operation]['start']
                )

        def add_checkpoint(self, name: str, details: str = ""):
            """Add a performance checkpoint"""
            self.checkpoints.append({
                'name': name,
                'timestamp': time.time(),
                'details': details
            })

        def get_report(self) -> Dict[str, Any]:
            """Get performance report"""
            return {
                'timings': self.timings,
                'checkpoints': self.checkpoints,
                'total_operations': len(self.timings),
                'total_checkpoints': len(self.checkpoints)
            }

    return PerformanceMonitor()


@pytest.fixture
def screenshot_manager():
    """Screenshot management for E2E tests"""
    class ScreenshotManager:
        def __init__(self):
            self.screenshots = []
            self.screenshot_dir = os.path.join(os.getcwd(), "data", "e2e_screenshots")
            os.makedirs(self.screenshot_dir, exist_ok=True)

        def take_screenshot(self, page, name: str, step: str = "") -> str:
            """Take and save screenshot"""
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{step}_{timestamp}.png" if step else f"{name}_{timestamp}.png"
            filepath = os.path.join(self.screenshot_dir, filename)

            page.screenshot(path=filepath)
            self.screenshots.append(filepath)

            return filepath

        def cleanup_screenshots(self):
            """Clean up all screenshots"""
            for screenshot_path in self.screenshots:
                try:
                    if os.path.exists(screenshot_path):
                        os.unlink(screenshot_path)
                except Exception:
                    pass  # Ignore cleanup errors
            self.screenshots.clear()

    manager = ScreenshotManager()
    yield manager
    manager.cleanup_screenshots()


@pytest.fixture
def workflow_validator():
    """Validator for E2E workflow results"""
    class WorkflowValidator:
        def __init__(self):
            self.validations = []

        def validate_excel_output(self, file_path: str, expected_columns: List[str]) -> bool:
            """Validate Excel output file"""
            try:
                df = pd.read_excel(file_path)

                # Check if file has data
                has_data = len(df) > 0

                # Check required columns
                has_columns = all(col in df.columns for col in expected_columns)

                # Check for valid email format in email column
                has_valid_emails = True
                if 'email' in df.columns:
                    has_valid_emails = df['email'].str.contains('@').all()

                validation_result = {
                    'file_exists': True,
                    'has_data': has_data,
                    'has_required_columns': has_columns,
                    'has_valid_emails': has_valid_emails,
                    'row_count': len(df),
                    'column_count': len(df.columns)
                }

                self.validations.append(validation_result)
                return all([has_data, has_columns, has_valid_emails])

            except Exception as e:
                validation_result = {
                    'file_exists': False,
                    'error': str(e)
                }
                self.validations.append(validation_result)
                return False

        def validate_campaign_data(self, data: Dict[str, Any]) -> bool:
            """Validate campaign data structure"""
            required_fields = ['name', 'subject', 'status', 'recipients']
            has_required_fields = all(field in data for field in required_fields)

            # Validate data types
            valid_types = (
                isinstance(data.get('recipients'), (int, str)) and
                isinstance(data.get('name'), str) and
                len(data.get('name', '')) > 0
            )

            validation_result = {
                'has_required_fields': has_required_fields,
                'valid_types': valid_types,
                'data': data
            }

            self.validations.append(validation_result)
            return has_required_fields and valid_types

        def get_validation_summary(self) -> Dict[str, Any]:
            """Get summary of all validations"""
            return {
                'total_validations': len(self.validations),
                'validations': self.validations
            }

    return WorkflowValidator()


# Pytest configuration for E2E tests
def pytest_configure(config):
    """Configure pytest markers for E2E tests"""
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end tests")
    config.addinivalue_line("markers", "slow_e2e: marks tests as slow E2E tests")
    config.addinivalue_line("markers", "browser_required: marks tests requiring browser automation")
    config.addinivalue_line("markers", "data_dependent: marks tests requiring specific test data")


def pytest_collection_modifyitems(config, items):
    """Auto-mark E2E tests"""
    for item in items:
        if "e2e" in item.nodeid:
            item.add_marker(pytest.mark.e2e)
        if "browser" in item.name.lower():
            item.add_marker(pytest.mark.browser_required)
        if any(keyword in item.name.lower() for keyword in ['complete', 'full', 'workflow']):
            item.add_marker(pytest.mark.slow_e2e)


# Session-scoped fixtures cleanup
@pytest.fixture(scope="session", autouse=True)
def cleanup_e2e_session():
    """Clean up E2E test session"""
    yield

    # Clean up any remaining test data
    logger = get_logger()
    logger.info("E2E test session cleanup completed")