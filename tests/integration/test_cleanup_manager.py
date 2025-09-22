"""
Tests for cleanup and data isolation mechanisms
"""
import pytest
import time
from datetime import datetime

from src.api import API
from src.api.models.suscriptores import SubscriberData


@pytest.mark.integration
@pytest.mark.destructive
class TestCleanupMechanisms:
    """Test the cleanup and data isolation mechanisms"""

    def test_test_data_manager_list_lifecycle(self, api_client: API, test_data_manager, list_config, rate_limit_helper):
        """Test complete lifecycle of test data manager for lists"""

        # Create unique test list name
        list_name = test_data_manager.create_test_list_name("cleanup_test")

        # Verify test name is unique and has prefix
        assert test_data_manager.test_prefix in list_name
        assert "cleanup_test" in list_name

        rate_limit_helper.wait_if_needed("create_list", 1.0)

        # Create list
        list_id = api_client.suscriptores.create_list(
            sender_email=list_config["sender_email"],
            name=list_name,
            company=list_config["company"],
            country=list_config["country"],
            city=list_config["city"],
            address=list_config["address"],
            phone=list_config["phone"]
        )

        # Register for cleanup
        test_data_manager.register_created_list(list_id, list_name)

        # Verify registration
        assert len(test_data_manager.created_lists) == 1
        assert test_data_manager.created_lists[0]["id"] == list_id
        assert test_data_manager.created_lists[0]["name"] == list_name

        rate_limit_helper.wait_if_needed("get_lists", 0.5)

        # Verify list exists
        lists = api_client.suscriptores.get_lists()
        created_list = next((l for l in lists if l.id == list_id), None)
        assert created_list is not None

        # Manual cleanup test
        test_data_manager.cleanup_test_data(api_client)

        rate_limit_helper.wait_if_needed("get_lists", 0.5)

        # Verify list was deleted
        lists_after_cleanup = api_client.suscriptores.get_lists()
        remaining_list = next((l for l in lists_after_cleanup if l.id == list_id), None)
        assert remaining_list is None

    def test_test_data_manager_subscriber_lifecycle(self, api_client: API, test_data_manager, list_config, sample_subscriber_data, rate_limit_helper):
        """Test complete lifecycle of test data manager for subscribers"""

        # Create test list first
        list_name = test_data_manager.create_test_list_name("subscriber_cleanup")

        rate_limit_helper.wait_if_needed("create_list", 1.0)

        list_id = api_client.suscriptores.create_list(
            sender_email=list_config["sender_email"],
            name=list_name,
            company=list_config["company"],
            country=list_config["country"],
            city=list_config["city"],
            address=list_config["address"],
            phone=list_config["phone"]
        )

        test_data_manager.register_created_list(list_id, list_name)

        # Create unique test email
        test_email = test_data_manager.create_test_email(sample_subscriber_data["email"])

        # Verify email is unique and has prefix
        assert test_data_manager.test_prefix in test_email
        assert "@" in test_email

        # Add subscriber
        subscriber_fields = {
            "email": test_email,
            "nombre": sample_subscriber_data["nombre"],
            "apellido": sample_subscriber_data["apellido"]
        }

        rate_limit_helper.wait_if_needed("add_subscriber", 0.5)

        subscriber_id = api_client.suscriptores.add_subscriber(
            list_id=list_id,
            merge_fields=subscriber_fields,
            double_optin=0,
            update_subscriber=1
        )

        # Register subscriber for cleanup
        test_data_manager.register_created_subscriber(list_id, test_email)

        # Verify registration
        assert len(test_data_manager.created_subscribers) == 1
        assert test_data_manager.created_subscribers[0]["list_id"] == list_id
        assert test_data_manager.created_subscribers[0]["email"] == test_email

        rate_limit_helper.wait_if_needed("get_subscribers", 1.0)

        # Verify subscriber exists
        subscribers = api_client.suscriptores.get_subscribers(list_id, status=None)
        found_subscriber = next((s for s in subscribers if s.email == test_email), None)
        assert found_subscriber is not None

        # Cleanup will be handled by fixture automatically

    def test_test_data_isolation(self, test_data_manager):
        """Test that test data is properly isolated"""

        # Create multiple test names
        name1 = test_data_manager.create_test_list_name("test1")
        name2 = test_data_manager.create_test_list_name("test2")

        # Should be different
        assert name1 != name2

        # Should both contain the same prefix (timestamp)
        assert test_data_manager.test_prefix in name1
        assert test_data_manager.test_prefix in name2

        # Create multiple test emails
        email1 = test_data_manager.create_test_email("test1@example.com")
        email2 = test_data_manager.create_test_email("test2@example.com")

        # Should be different
        assert email1 != email2

        # Should both contain the same prefix
        assert test_data_manager.test_prefix in email1
        assert test_data_manager.test_prefix in email2

        # Should preserve domain
        assert "@example.com" in email1
        assert "@example.com" in email2

    def test_multiple_test_sessions(self, api_client: API, list_config, rate_limit_helper):
        """Test that multiple test sessions don't interfere with each other"""

        from tests.conftest import TestDataManager

        # Create two separate test data managers (simulating different test sessions)
        manager1 = TestDataManager()
        manager2 = TestDataManager()

        # Should have different prefixes
        assert manager1.test_prefix != manager2.test_prefix

        # Create lists with each manager
        list_name1 = manager1.create_test_list_name("session1")
        list_name2 = manager2.create_test_list_name("session2")

        # Should be completely different
        assert list_name1 != list_name2

        # Create actual lists
        rate_limit_helper.wait_if_needed("create_list", 1.0)

        list_id1 = api_client.suscriptores.create_list(
            sender_email=list_config["sender_email"],
            name=list_name1,
            company=list_config["company"],
            country=list_config["country"],
            city=list_config["city"],
            address=list_config["address"],
            phone=list_config["phone"]
        )

        rate_limit_helper.wait_if_needed("create_list", 1.0)

        list_id2 = api_client.suscriptores.create_list(
            sender_email=list_config["sender_email"],
            name=list_name2,
            company=list_config["company"],
            country=list_config["country"],
            city=list_config["city"],
            address=list_config["address"],
            phone=list_config["phone"]
        )

        # Register with respective managers
        manager1.register_created_list(list_id1, list_name1)
        manager2.register_created_list(list_id2, list_name2)

        # Each manager should only know about its own data
        assert len(manager1.created_lists) == 1
        assert len(manager2.created_lists) == 1
        assert manager1.created_lists[0]["id"] != manager2.created_lists[0]["id"]

        # Cleanup both managers
        manager1.cleanup_test_data(api_client)
        manager2.cleanup_test_data(api_client)

    def test_cleanup_resilience(self, api_client: API, test_data_manager, list_config, rate_limit_helper):
        """Test that cleanup is resilient to errors"""

        # Create a test list
        list_name = test_data_manager.create_test_list_name("resilience_test")

        rate_limit_helper.wait_if_needed("create_list", 1.0)

        list_id = api_client.suscriptores.create_list(
            sender_email=list_config["sender_email"],
            name=list_name,
            company=list_config["company"],
            country=list_config["country"],
            city=list_config["city"],
            address=list_config["address"],
            phone=list_config["phone"]
        )

        test_data_manager.register_created_list(list_id, list_name)

        # Also register a non-existent list (should fail gracefully)
        test_data_manager.register_created_list(999999999, "nonexistent_list")

        # Register a non-existent subscriber (should fail gracefully)
        test_data_manager.register_created_subscriber(list_id, "nonexistent@example.com")

        # Cleanup should not crash even with invalid data
        # It should log warnings but continue
        test_data_manager.cleanup_test_data(api_client)

        # The valid list should still be cleaned up
        rate_limit_helper.wait_if_needed("get_lists", 0.5)
        lists = api_client.suscriptores.get_lists()
        remaining_list = next((l for l in lists if l.id == list_id), None)
        assert remaining_list is None

    def test_batch_cleanup_efficiency(self, api_client: API, test_data_manager, list_config, rate_limit_helper):
        """Test cleanup efficiency with multiple items"""

        # Create multiple test lists
        list_ids = []
        for i in range(3):  # Create 3 lists
            list_name = test_data_manager.create_test_list_name(f"batch_test_{i}")

            rate_limit_helper.wait_if_needed("create_list", 1.0)

            list_id = api_client.suscriptores.create_list(
                sender_email=list_config["sender_email"],
                name=list_name,
                company=list_config["company"],
                country=list_config["country"],
                city=list_config["city"],
                address=list_config["address"],
                phone=list_config["phone"]
            )

            list_ids.append(list_id)
            test_data_manager.register_created_list(list_id, list_name)

            # Add a subscriber to each list
            test_email = test_data_manager.create_test_email(f"batch{i}@example.com")

            rate_limit_helper.wait_if_needed("add_subscriber", 0.5)

            api_client.suscriptores.add_subscriber(
                list_id=list_id,
                merge_fields={"email": test_email, "nombre": f"Batch User {i}"},
                double_optin=0,
                update_subscriber=1
            )

            test_data_manager.register_created_subscriber(list_id, test_email)

        # Verify all were created
        assert len(test_data_manager.created_lists) == 3
        assert len(test_data_manager.created_subscribers) == 3

        # Batch cleanup
        start_time = time.time()
        test_data_manager.cleanup_test_data(api_client)
        cleanup_time = time.time() - start_time

        # Verify all were cleaned up
        rate_limit_helper.wait_if_needed("get_lists", 0.5)
        lists = api_client.suscriptores.get_lists()
        remaining_lists = [l for l in lists if l.id in list_ids]
        assert len(remaining_lists) == 0

        # Cleanup should be reasonably fast
        assert cleanup_time < 30  # Should complete within 30 seconds


@pytest.mark.integration
class TestRateLimitHelper:
    """Test rate limiting helper functionality"""

    def test_rate_limit_helper_timing(self, rate_limit_helper):
        """Test rate limit helper enforces delays"""

        endpoint = "test_endpoint"
        min_interval = 0.5  # 500ms

        # First call should not wait
        start_time = time.time()
        rate_limit_helper.wait_if_needed(endpoint, min_interval)
        first_call_time = time.time() - start_time

        # Should be very fast (no waiting)
        assert first_call_time < 0.1

        # Second call immediately after should wait
        start_time = time.time()
        rate_limit_helper.wait_if_needed(endpoint, min_interval)
        second_call_time = time.time() - start_time

        # Should wait approximately min_interval
        assert second_call_time >= min_interval * 0.9  # Allow 10% tolerance

    def test_rate_limit_helper_different_endpoints(self, rate_limit_helper):
        """Test rate limiting works independently for different endpoints"""

        endpoint1 = "endpoint_1"
        endpoint2 = "endpoint_2"
        min_interval = 0.3

        # Call endpoint1
        rate_limit_helper.wait_if_needed(endpoint1, min_interval)

        # Call endpoint2 immediately should not wait (different endpoint)
        start_time = time.time()
        rate_limit_helper.wait_if_needed(endpoint2, min_interval)
        call_time = time.time() - start_time

        # Should be fast (no waiting for different endpoint)
        assert call_time < 0.1

        # Call endpoint1 again should wait
        start_time = time.time()
        rate_limit_helper.wait_if_needed(endpoint1, min_interval)
        call_time = time.time() - start_time

        # Should wait
        assert call_time >= min_interval * 0.9

    def test_rate_limit_helper_after_delay(self, rate_limit_helper):
        """Test rate limiting doesn't wait if enough time has passed"""

        endpoint = "test_endpoint"
        min_interval = 0.2

        # First call
        rate_limit_helper.wait_if_needed(endpoint, min_interval)

        # Wait longer than min_interval
        time.sleep(min_interval * 1.5)

        # Second call should not wait additional time
        start_time = time.time()
        rate_limit_helper.wait_if_needed(endpoint, min_interval)
        call_time = time.time() - start_time

        # Should be fast (enough time already passed)
        assert call_time < 0.1


@pytest.mark.integration
class TestTestConfiguration:
    """Test configuration and setup for integration tests"""

    def test_test_config_loading(self, test_config):
        """Test that test configuration loads properly"""
        assert test_config is not None
        assert isinstance(test_config, dict)

        # Should have required configuration
        assert "url_base" in test_config or "api" in test_config

    def test_api_client_initialization(self, api_client):
        """Test API client initializes properly"""
        assert api_client is not None
        assert hasattr(api_client, 'suscriptores')
        assert hasattr(api_client, 'campanias')

    def test_logger_functionality(self, test_logger):
        """Test logger works in test environment"""
        assert test_logger is not None

        # Test logging doesn't crash
        test_logger.info("Test info message")
        test_logger.warning("Test warning message")
        test_logger.error("Test error message")

    def test_sample_data_fixtures(self, sample_subscriber_data, sample_excel_data, list_config):
        """Test sample data fixtures are properly configured"""

        # Subscriber data
        assert "email" in sample_subscriber_data
        assert "@" in sample_subscriber_data["email"]

        # Excel data
        assert sample_excel_data.endswith(".xlsx")
        import os
        assert os.path.exists(sample_excel_data)

        # List config
        assert "sender_email" in list_config
        assert "company" in list_config
        assert "@" in list_config["sender_email"]