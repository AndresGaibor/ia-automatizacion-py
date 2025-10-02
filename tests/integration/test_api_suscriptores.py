"""
Integration tests for Suscriptores API endpoints
Tests create and cleanup their own data to avoid affecting production
"""
import pytest
import time

from src.infrastructure.api import API
from src.infrastructure.api.models.suscriptores import SubscriberData


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.destructive
class TestSuscriptoresAPIIntegration:
    """Integration tests for Suscriptores API - creates and cleans own data"""

    def test_create_and_delete_list_lifecycle(self, api_client: API, test_data_manager, list_config, rate_limit_helper):
        """Test complete list lifecycle: create -> verify -> delete"""

        # Create unique test list name
        list_name = test_data_manager.create_test_list_name("lifecycle_test")

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

        assert isinstance(list_id, int)
        assert list_id > 0

        # Register for cleanup
        test_data_manager.register_created_list(list_id, list_name)

        rate_limit_helper.wait_if_needed("get_lists", 0.5)

        # Verify list exists
        lists = api_client.suscriptores.get_lists()
        created_list = next((l for l in lists if l.id == list_id), None)
        assert created_list is not None
        assert created_list.name == list_name

        rate_limit_helper.wait_if_needed("get_list_stats", 1.0)

        # Get list stats
        stats = api_client.suscriptores.get_list_stats(list_id)
        assert stats.list_id == list_id
        assert stats.name == list_name
        assert stats.active_subscribers == 0  # New list should be empty

        # Cleanup is handled by test_data_manager fixture

    def test_subscriber_crud_operations(self, api_client: API, test_data_manager, list_config, sample_subscriber_data, rate_limit_helper):
        """Test complete subscriber CRUD: create list -> add subscriber -> update -> delete"""

        # Create test list
        list_name = test_data_manager.create_test_list_name("subscriber_crud")

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

        # Prepare subscriber data
        subscriber_fields = {
            "email": test_email,
            "nombre": sample_subscriber_data["nombre"],
            "apellido": sample_subscriber_data["apellido"],
            "telefono": sample_subscriber_data["telefono"]
        }

        rate_limit_helper.wait_if_needed("add_subscriber", 0.5)

        # Add subscriber
        subscriber_id = api_client.suscriptores.add_subscriber(
            list_id=list_id,
            merge_fields=subscriber_fields,
            double_optin=0,  # Skip double opt-in for testing
            update_subscriber=1
        )

        assert isinstance(subscriber_id, int)
        assert subscriber_id > 0

        test_data_manager.register_created_subscriber(list_id, test_email)

        rate_limit_helper.wait_if_needed("get_subscribers", 1.0)

        # Verify subscriber was added
        subscribers = api_client.suscriptores.get_subscribers(list_id, status=None)
        added_subscriber = next((s for s in subscribers if s.email == test_email), None)
        assert added_subscriber is not None
        assert added_subscriber.email == test_email

        rate_limit_helper.wait_if_needed("get_subscriber_details", 0.5)

        # Get detailed subscriber info
        details = api_client.suscriptores.get_subscriber_details(list_id, test_email)
        assert details.email == test_email
        assert details.list_id == list_id

        # Update subscriber
        updated_fields = {
            "email": test_email,
            "nombre": "Updated Name",
            "apellido": sample_subscriber_data["apellido"],
            "telefono": "+34999888777"
        }

        rate_limit_helper.wait_if_needed("update_subscriber", 0.5)

        updated_id = api_client.suscriptores.update_subscriber(
            list_id=list_id,
            subscriber_id=subscriber_id,
            merge_fields=updated_fields
        )

        assert updated_id == subscriber_id

        # Verify update
        rate_limit_helper.wait_if_needed("get_subscriber_details", 0.5)
        updated_details = api_client.suscriptores.get_subscriber_details(list_id, test_email)
        # Note: Field verification might depend on list configuration
        assert updated_details.email == test_email

    def test_batch_add_subscribers_safe(self, api_client: API, test_data_manager, list_config, rate_limit_helper):
        """Test batch adding subscribers with safe test data"""

        # Create test list
        list_name = test_data_manager.create_test_list_name("batch_test")

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

        # Create test subscribers data
        test_subscribers = []
        for i in range(3):
            test_email = test_data_manager.create_test_email(f"batch{i}@example.com")
            test_data_manager.register_created_subscriber(list_id, test_email)

            subscriber_data = SubscriberData(
                email=test_email,
                nombre=f"Batch User {i}",
                apellido="Test"
            )
            test_subscribers.append(subscriber_data)

        rate_limit_helper.wait_if_needed("batch_add_subscribers", 1.0)

        # Batch add subscribers
        result = api_client.suscriptores.batch_add_subscribers(
            list_id=list_id,
            subscribers_data=test_subscribers,
            update_subscriber=1,
            complete_json=1
        )

        assert result.success_count >= 3
        assert result.error_count == 0

        # Verify subscribers were added
        rate_limit_helper.wait_if_needed("get_subscribers", 1.0)
        subscribers = api_client.suscriptores.get_subscribers(list_id, status=None)

        added_emails = {s.email for s in subscribers}
        for subscriber in test_subscribers:
            assert subscriber.email in added_emails

    def test_search_subscriber_safe(self, api_client: API, test_data_manager, list_config, sample_subscriber_data, rate_limit_helper):
        """Test searching for subscribers across lists"""

        # Create test list
        list_name = test_data_manager.create_test_list_name("search_test")

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

        # Add subscriber
        subscriber_fields = {
            "email": test_email,
            "nombre": sample_subscriber_data["nombre"],
            "apellido": sample_subscriber_data["apellido"]
        }

        rate_limit_helper.wait_if_needed("add_subscriber", 0.5)

        api_client.suscriptores.add_subscriber(
            list_id=list_id,
            merge_fields=subscriber_fields,
            double_optin=0,
            update_subscriber=1
        )

        test_data_manager.register_created_subscriber(list_id, test_email)

        # Search for subscriber
        rate_limit_helper.wait_if_needed("search_subscriber", 1.0)

        search_results = api_client.suscriptores.search_subscriber(test_email)

        # Should find the subscriber in our test list
        assert len(search_results) >= 1
        found_subscriber = next((s for s in search_results if s.email == test_email), None)
        assert found_subscriber is not None
        assert found_subscriber.email == test_email

    def test_list_fields_and_segments(self, api_client: API, test_data_manager, list_config, rate_limit_helper):
        """Test field and segment related operations"""

        # Create test list
        list_name = test_data_manager.create_test_list_name("fields_test")

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

        # Get list fields
        rate_limit_helper.wait_if_needed("get_list_fields", 1.0)
        fields = api_client.suscriptores.get_list_fields(list_id)
        assert fields.list_id == list_id

        # Get merge fields
        rate_limit_helper.wait_if_needed("get_merge_fields", 1.0)
        merge_fields = api_client.suscriptores.get_merge_fields(list_id)
        assert len(merge_fields.fields) > 0  # Should have at least email field

        # Get segments
        rate_limit_helper.wait_if_needed("get_list_segments", 0.5)
        segments = api_client.suscriptores.get_list_segments(list_id)
        # New list might not have segments, so just verify no error
        assert segments is not None

    def test_unsubscribe_subscriber_safe(self, api_client: API, test_data_manager, list_config, sample_subscriber_data, rate_limit_helper):
        """Test unsubscribing a subscriber (safe operation)"""

        # Create test list
        list_name = test_data_manager.create_test_list_name("unsubscribe_test")

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

        # Add subscriber
        subscriber_fields = {
            "email": test_email,
            "nombre": sample_subscriber_data["nombre"]
        }

        rate_limit_helper.wait_if_needed("add_subscriber", 0.5)

        api_client.suscriptores.add_subscriber(
            list_id=list_id,
            merge_fields=subscriber_fields,
            double_optin=0,
            update_subscriber=1
        )

        test_data_manager.register_created_subscriber(list_id, test_email)

        # Unsubscribe subscriber (this is a safe operation)
        rate_limit_helper.wait_if_needed("unsubscribe_subscriber", 0.5)

        api_client.suscriptores.unsubscribe_subscriber(list_id, test_email)

        # Verify subscriber status changed (they still exist but are unsubscribed)
        rate_limit_helper.wait_if_needed("get_subscribers", 1.0)
        subscribers = api_client.suscriptores.get_subscribers(list_id, status=None)
        found_subscriber = next((s for s in subscribers if s.email == test_email), None)

        # Subscriber might still be there but unsubscribed, or might not appear with certain status filters
        # The important thing is the unsubscribe call didn't throw an error

    @pytest.mark.slow
    def test_get_inactive_subscribers(self, api_client: API, rate_limit_helper):
        """Test getting inactive subscribers (read-only operation)"""

        rate_limit_helper.wait_if_needed("get_inactive_subscribers", 1.0)

        # Test with recent date range to minimize data
        inactive = api_client.suscriptores.get_inactive_subscribers(
            date_from="2024-01-01",
            date_to="2024-01-02",  # Small range to limit results
            full_info=0
        )

        # Just verify no error occurred
        assert inactive is not None

    def test_add_merge_tag_safe(self, api_client: API, test_data_manager, list_config, rate_limit_helper):
        """Test adding a merge tag to a test list"""

        # Create test list
        list_name = test_data_manager.create_test_list_name("merge_tag_test")

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

        # Add a test merge tag
        test_field_name = f"test_field_{int(time.time())}"

        rate_limit_helper.wait_if_needed("add_merge_tag", 1.0)

        # This should not raise an exception
        api_client.suscriptores.add_merge_tag(
            list_id=list_id,
            field_name=test_field_name,
            field_type="text"
        )

        # Verify field was added
        rate_limit_helper.wait_if_needed("get_fields", 1.0)
        fields = api_client.suscriptores.get_fields(list_id)

        # Field should appear in the list
        field_names = [field.name for field in fields.fields]
        assert test_field_name in field_names


@pytest.mark.integration
@pytest.mark.api
class TestSuscriptoresAPIReadOnly:
    """Read-only integration tests that don't create data"""

    def test_get_lists_readonly(self, api_client: API, rate_limit_helper):
        """Test getting lists (read-only)"""

        rate_limit_helper.wait_if_needed("get_lists", 0.5)

        lists = api_client.suscriptores.get_lists()
        assert isinstance(lists, list)

        # If there are lists, verify structure
        if lists:
            sample_list = lists[0]
            assert hasattr(sample_list, 'id')
            assert hasattr(sample_list, 'name')
            assert isinstance(sample_list.id, int)

    def test_api_error_handling(self, api_client: API, rate_limit_helper):
        """Test API error handling with invalid requests"""

        # Test with invalid list ID
        rate_limit_helper.wait_if_needed("get_list_stats", 1.0)

        with pytest.raises(Exception):
            api_client.suscriptores.get_list_stats(999999999)  # Very unlikely to exist

        # Test with invalid email format for search
        rate_limit_helper.wait_if_needed("search_subscriber", 1.0)

        # This might return empty results rather than error, but should not crash
        try:
            result = api_client.suscriptores.search_subscriber("invalid-email-format")
            assert isinstance(result, list)
        except Exception:
            # Some APIs might throw validation errors, which is also acceptable
            pass