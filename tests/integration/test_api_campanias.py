"""
Integration tests for Campanias API endpoints
These are primarily read-only tests since campaign creation requires more complex setup
"""
import pytest
from datetime import datetime, timedelta
from typing import List

from src.api import API
from src.api.models.campanias import CampaignSummary, CampaignComplete, CampaignBasicInfo


@pytest.mark.integration
@pytest.mark.api
class TestCampaignsAPIIntegration:
    """Integration tests for Campaigns API - mostly read-only operations"""

    def test_get_all_campaigns_summary(self, api_client: API, rate_limit_helper):
        """Test getting all campaigns with basic summary"""

        rate_limit_helper.wait_if_needed("get_campaigns", 1.0)

        campaigns = api_client.campanias.get_all(complete_info=False)
        assert isinstance(campaigns, list)

        # If there are campaigns, verify structure
        if campaigns:
            sample_campaign = campaigns[0]
            assert isinstance(sample_campaign, CampaignSummary)
            assert hasattr(sample_campaign, 'id')
            assert hasattr(sample_campaign, 'name')
            assert isinstance(sample_campaign.id, int)

    @pytest.mark.slow
    def test_get_all_campaigns_complete(self, api_client: API, rate_limit_helper):
        """Test getting all campaigns with complete information (slower)"""

        rate_limit_helper.wait_if_needed("get_campaigns_complete", 2.0)

        campaigns = api_client.campanias.get_all(complete_info=True)
        assert isinstance(campaigns, list)

        # If there are campaigns, verify complete structure
        if campaigns:
            sample_campaign = campaigns[0]
            assert isinstance(sample_campaign, CampaignComplete)
            assert hasattr(sample_campaign, 'id')
            assert hasattr(sample_campaign, 'name')
            assert hasattr(sample_campaign, 'total_sent')
            assert isinstance(sample_campaign.id, int)

    def test_get_campaign_basic_info(self, api_client: API, rate_limit_helper):
        """Test getting basic information for specific campaigns"""

        rate_limit_helper.wait_if_needed("get_campaigns", 1.0)

        # First get available campaigns
        campaigns = api_client.campanias.get_all(complete_info=False)

        if not campaigns:
            pytest.skip("No campaigns available for testing")

        # Test with first few campaigns
        test_campaigns = campaigns[:3]  # Limit to first 3 to avoid rate limits

        for campaign in test_campaigns:
            rate_limit_helper.wait_if_needed("get_campaign_basic_info", 1.0)

            basic_info = api_client.campanias.get_basic_info(campaign.id)
            assert isinstance(basic_info, CampaignBasicInfo)
            assert basic_info.id == campaign.id
            assert basic_info.name is not None

    def test_get_campaign_detailed_info(self, api_client: API, rate_limit_helper):
        """Test getting detailed information for specific campaigns"""

        rate_limit_helper.wait_if_needed("get_campaigns", 1.0)

        # Get available campaigns
        campaigns = api_client.campanias.get_all(complete_info=False)

        if not campaigns:
            pytest.skip("No campaigns available for testing")

        # Test with first campaign only to avoid rate limits
        test_campaign = campaigns[0]

        rate_limit_helper.wait_if_needed("get_campaign_total_info", 1.0)

        detailed_info = api_client.campanias.get_total_info(test_campaign.id)
        assert detailed_info.id == test_campaign.id
        assert hasattr(detailed_info, 'total_sent')
        assert hasattr(detailed_info, 'total_opened')

    def test_get_campaign_openers(self, api_client: API, rate_limit_helper):
        """Test getting campaign openers"""

        rate_limit_helper.wait_if_needed("get_campaigns", 1.0)

        # Get available campaigns
        campaigns = api_client.campanias.get_all(complete_info=False)

        if not campaigns:
            pytest.skip("No campaigns available for testing")

        # Test with first campaign
        test_campaign = campaigns[0]

        rate_limit_helper.wait_if_needed("get_campaign_openers", 1.0)

        openers = api_client.campanias.get_openers(test_campaign.id)
        assert isinstance(openers, list)

        # If there are openers, verify structure
        if openers:
            sample_opener = openers[0]
            assert hasattr(sample_opener, 'email')
            assert hasattr(sample_opener, 'open_date')

    def test_get_campaign_clicks(self, api_client: API, rate_limit_helper):
        """Test getting campaign clicks"""

        rate_limit_helper.wait_if_needed("get_campaigns", 1.0)

        # Get available campaigns
        campaigns = api_client.campanias.get_all(complete_info=False)

        if not campaigns:
            pytest.skip("No campaigns available for testing")

        # Test with first campaign
        test_campaign = campaigns[0]

        rate_limit_helper.wait_if_needed("get_campaign_clicks", 1.0)

        clickers = api_client.campanias.get_clicks(test_campaign.id)
        assert isinstance(clickers, list)

        # If there are clickers, verify structure
        if clickers:
            sample_clicker = clickers[0]
            assert hasattr(sample_clicker, 'email')
            assert hasattr(sample_clicker, 'click_date')

    def test_get_campaign_links(self, api_client: API, rate_limit_helper):
        """Test getting campaign links"""

        rate_limit_helper.wait_if_needed("get_campaigns", 1.0)

        # Get available campaigns
        campaigns = api_client.campanias.get_all(complete_info=False)

        if not campaigns:
            pytest.skip("No campaigns available for testing")

        # Test with first campaign
        test_campaign = campaigns[0]

        rate_limit_helper.wait_if_needed("get_campaign_links", 1.0)

        links = api_client.campanias.get_links(test_campaign.id)
        assert isinstance(links, list)

        # If there are links, verify structure
        if links:
            sample_link = links[0]
            assert hasattr(sample_link, 'url')
            assert hasattr(sample_link, 'clicks')

    def test_get_campaign_soft_bounces(self, api_client: API, rate_limit_helper):
        """Test getting campaign soft bounces"""

        rate_limit_helper.wait_if_needed("get_campaigns", 1.0)

        # Get available campaigns
        campaigns = api_client.campanias.get_all(complete_info=False)

        if not campaigns:
            pytest.skip("No campaigns available for testing")

        # Test with first campaign
        test_campaign = campaigns[0]

        rate_limit_helper.wait_if_needed("get_campaign_soft_bounces", 1.0)

        soft_bounces = api_client.campanias.get_soft_bounces(test_campaign.id)
        assert isinstance(soft_bounces, list)

        # If there are soft bounces, verify structure
        if soft_bounces:
            sample_bounce = soft_bounces[0]
            assert hasattr(sample_bounce, 'email')
            assert hasattr(sample_bounce, 'bounce_date')

    def test_get_campaign_stats_by_date(self, api_client: API, test_data_manager, list_config, rate_limit_helper):
        """Test getting campaign statistics by date range"""

        # We need a list ID for this endpoint
        # Create a temporary test list
        list_name = test_data_manager.create_test_list_name("stats_test")

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

        # Test with recent date range
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        rate_limit_helper.wait_if_needed("get_campaign_stats_by_date", 1.0)

        stats = api_client.campanias.get_stats_by_date(
            list_id=list_id,
            start_date=start_date,
            end_date=end_date
        )

        # Verify structure
        assert hasattr(stats, 'total_sent')
        assert hasattr(stats, 'opened')
        assert hasattr(stats, 'unopened')
        assert hasattr(stats, 'total_clicks')
        assert isinstance(stats.total_sent, int)
        assert isinstance(stats.opened, int)

    def test_date_validation_in_stats(self, api_client: API, test_data_manager, list_config, rate_limit_helper):
        """Test date validation in campaign stats"""

        # Create a temporary test list
        list_name = test_data_manager.create_test_list_name("date_validation_test")

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

        # Test with invalid date format
        with pytest.raises(ValueError):
            api_client.campanias.get_stats_by_date(
                list_id=list_id,
                start_date="invalid-date",
                end_date="2024-01-01"
            )

        # Test with end date before start date
        with pytest.raises(ValueError):
            api_client.campanias.get_stats_by_date(
                list_id=list_id,
                start_date="2024-12-31",
                end_date="2024-01-01"
            )

    def test_campaign_api_error_handling(self, api_client: API, rate_limit_helper):
        """Test error handling with invalid campaign IDs"""

        # Test with invalid campaign ID
        rate_limit_helper.wait_if_needed("get_campaign_basic_info", 1.0)

        with pytest.raises(Exception):
            api_client.campanias.get_basic_info(999999999)  # Very unlikely to exist

        rate_limit_helper.wait_if_needed("get_campaign_total_info", 1.0)

        with pytest.raises(Exception):
            api_client.campanias.get_total_info(999999999)

    @pytest.mark.slow
    def test_bulk_campaign_operations(self, api_client: API, rate_limit_helper):
        """Test bulk operations on multiple campaigns (slow test)"""

        rate_limit_helper.wait_if_needed("get_campaigns", 1.0)

        # Get all campaigns
        campaigns = api_client.campanias.get_all(complete_info=False)

        if len(campaigns) < 2:
            pytest.skip("Need at least 2 campaigns for bulk testing")

        # Test getting basic info for multiple campaigns
        test_campaigns = campaigns[:5]  # Limit to 5 to avoid excessive rate limiting

        basic_infos = []
        for campaign in test_campaigns:
            rate_limit_helper.wait_if_needed("get_campaign_basic_info", 1.0)

            basic_info = api_client.campanias.get_basic_info(campaign.id)
            basic_infos.append(basic_info)

        assert len(basic_infos) == len(test_campaigns)

        # Verify all basic infos have required fields
        for basic_info in basic_infos:
            assert hasattr(basic_info, 'id')
            assert hasattr(basic_info, 'name')
            assert isinstance(basic_info.id, int)

    def test_campaign_data_consistency(self, api_client: API, rate_limit_helper):
        """Test data consistency between different campaign endpoints"""

        rate_limit_helper.wait_if_needed("get_campaigns", 1.0)

        # Get campaigns
        campaigns = api_client.campanias.get_all(complete_info=False)

        if not campaigns:
            pytest.skip("No campaigns available for consistency testing")

        test_campaign = campaigns[0]

        # Get basic info
        rate_limit_helper.wait_if_needed("get_campaign_basic_info", 1.0)
        basic_info = api_client.campanias.get_basic_info(test_campaign.id)

        # Get detailed info
        rate_limit_helper.wait_if_needed("get_campaign_total_info", 1.0)
        detailed_info = api_client.campanias.get_total_info(test_campaign.id)

        # Verify consistency
        assert basic_info.id == detailed_info.id
        assert basic_info.name == detailed_info.name

        # Both should have the same campaign ID
        assert basic_info.id == test_campaign.id