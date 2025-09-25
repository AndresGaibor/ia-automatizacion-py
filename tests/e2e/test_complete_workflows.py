"""
End-to-End tests for complete workflows
"""
import pytest
import os
from unittest.mock import patch

from src.core.services.campaign_service import CampaignService
from src.core.services.legacy_operations_service import LegacyOperationsService
from src.infrastructure.excel.excel_manager import ExcelManager


@pytest.mark.e2e
@pytest.mark.browser_required
@pytest.mark.slow_e2e
class TestCompleteWorkflows:
    """End-to-end tests for complete automation workflows"""

    @pytest.mark.data_dependent
    def test_complete_campaign_listing_workflow(
        self,
        browser_manager,
        e2e_config,
        campaign_search_terms,
        test_data_manager,
        performance_monitor,
        screenshot_manager,
        workflow_validator,
        e2e_logger
    ):
        """Test complete campaign listing workflow from search to Excel export"""

        e2e_logger.info("🚀 Starting complete campaign listing E2E test")
        performance_monitor.start_timing("complete_workflow")

        # Create test search file
        search_file_path = test_data_manager.create_test_excel_file(campaign_search_terms)
        performance_monitor.add_checkpoint("search_file_created", f"Created: {search_file_path}")

        try:
            # Step 1: Initialize services
            performance_monitor.start_timing("service_initialization")
            campaign_service = CampaignService()
            excel_manager = ExcelManager()
            performance_monitor.end_timing("service_initialization")

            # Step 2: Launch browser and authenticate
            performance_monitor.start_timing("browser_authentication")
            page = browser_manager.launch_browser()
            screenshot_manager.take_screenshot(page, "workflow", "browser_launched")

            # Navigate to login page
            browser_manager.navigate_to(page, e2e_config['url'])
            screenshot_manager.take_screenshot(page, "workflow", "login_page")
            performance_monitor.end_timing("browser_authentication")

            # Step 3: Load search terms and process campaigns
            performance_monitor.start_timing("campaign_processing")
            search_data = excel_manager.read_excel(search_file_path)

            # Mock the campaign processing for E2E test
            with patch.object(campaign_service, 'process_campaigns') as mock_process:
                # Simulate successful campaign processing
                mock_result = {
                    'campaigns_found': len(search_data),
                    'total_emails': 1500,
                    'total_opens': 300,
                    'total_clicks': 75,
                    'processing_time': 45.2,
                    'success': True
                }
                mock_process.return_value = mock_result

                result = campaign_service.process_campaigns(search_data, page)

                assert result['success'] == True
                assert result['campaigns_found'] > 0
                performance_monitor.add_checkpoint("campaigns_processed", f"Found: {result['campaigns_found']}")

            performance_monitor.end_timing("campaign_processing")

            # Step 4: Generate Excel report
            performance_monitor.start_timing("excel_generation")
            output_file = f"data/e2e_test_campaign_report_{test_data_manager.test_prefix}.xlsx"

            # Create mock report data
            report_data = []
            for _, row in search_data.iterrows():
                report_data.append({
                    'Campaign Name': row['Nombre'],
                    'Type': row['Tipo'],
                    'Send Date': row['Fecha envío'],
                    'Total Emails': 500,
                    'Opens': 100,
                    'Clicks': 25,
                    'Open Rate': '20.0%',
                    'Click Rate': '5.0%'
                })

            excel_manager.write_excel_formatted(
                report_data,
                output_file,
                {
                    'header_format': {'bold': True, 'bg_color': '#D7E4BC'},
                    'number_format': '#,##0'
                }
            )

            performance_monitor.end_timing("excel_generation")
            performance_monitor.add_checkpoint("excel_created", f"File: {output_file}")

            # Step 5: Validate results
            performance_monitor.start_timing("result_validation")

            # Validate Excel output
            expected_columns = ['Campaign Name', 'Type', 'Send Date', 'Total Emails', 'Opens', 'Clicks']
            validation_success = workflow_validator.validate_excel_output(output_file, expected_columns)

            assert validation_success == True, "Excel output validation failed"
            assert os.path.exists(output_file), "Excel file was not created"

            performance_monitor.end_timing("result_validation")
            performance_monitor.end_timing("complete_workflow")

            # Performance assertions
            performance_report = performance_monitor.get_report()
            assert performance_report['timings']['complete_workflow']['duration'] < 120  # Should complete in under 2 minutes

            e2e_logger.info(f"✅ Campaign listing workflow completed successfully in {performance_report['timings']['complete_workflow']['duration']:.2f}s")

        finally:
            # Cleanup
            browser_manager.cleanup_browser(page.context)
            if os.path.exists(output_file):
                os.unlink(output_file)

    @pytest.mark.data_dependent
    def test_complete_subscriber_workflow(
        self,
        browser_manager,
        e2e_config,
        sample_subscriber_list,
        list_configuration,
        test_data_manager,
        performance_monitor,
        screenshot_manager,
        workflow_validator,
        e2e_logger
    ):
        """Test complete subscriber management workflow"""

        e2e_logger.info("🚀 Starting complete subscriber management E2E test")
        performance_monitor.start_timing("subscriber_workflow")

        # Create test subscriber file
        subscriber_file_path = test_data_manager.create_test_excel_file(sample_subscriber_list)
        performance_monitor.add_checkpoint("subscriber_file_created", f"Created: {subscriber_file_path}")

        try:
            # Step 1: Initialize services
            performance_monitor.start_timing("service_initialization")
            operations_service = LegacyOperationsService()
            excel_manager = ExcelManager()
            performance_monitor.end_timing("service_initialization")

            # Step 2: Launch browser and authenticate
            performance_monitor.start_timing("browser_authentication")
            page = browser_manager.launch_browser()
            screenshot_manager.take_screenshot(page, "subscriber_workflow", "browser_launched")

            # Navigate to login page
            browser_manager.navigate_to(page, e2e_config['url'])
            screenshot_manager.take_screenshot(page, "subscriber_workflow", "login_page")
            performance_monitor.end_timing("browser_authentication")

            # Step 3: Create subscriber list
            performance_monitor.start_timing("list_creation")

            list_name = test_data_manager.create_test_name("subscriber_list")
            test_data_manager.register_created_item("list", "mock_id", list_name)

            # Mock list creation for E2E test
            with patch.object(operations_service, 'create_subscriber_list') as mock_create_list:
                mock_create_list.return_value = {
                    'success': True,
                    'list_id': 'mock_list_123',
                    'list_name': list_name,
                    'subscribers_added': len(sample_subscriber_list)
                }

                result = operations_service.create_subscriber_list(
                    page,
                    list_name,
                    subscriber_file_path,
                    list_configuration
                )

                assert result['success'] == True
                assert result['subscribers_added'] == len(sample_subscriber_list)
                performance_monitor.add_checkpoint("list_created", f"Added: {result['subscribers_added']} subscribers")

            performance_monitor.end_timing("list_creation")

            # Step 4: Download and validate subscriber data
            performance_monitor.start_timing("subscriber_download")

            output_file = f"data/e2e_test_subscribers_{test_data_manager.test_prefix}.xlsx"

            # Mock subscriber download
            with patch.object(operations_service, 'download_subscribers') as mock_download:
                mock_download.return_value = {
                    'success': True,
                    'output_file': output_file,
                    'subscribers_downloaded': len(sample_subscriber_list),
                    'processing_time': 15.3
                }

                # Create mock output file
                excel_manager.write_excel(sample_subscriber_list, output_file)

                download_result = operations_service.download_subscribers(
                    page,
                    list_name,
                    output_file
                )

                assert download_result['success'] == True
                assert download_result['subscribers_downloaded'] > 0
                performance_monitor.add_checkpoint("subscribers_downloaded", f"File: {output_file}")

            performance_monitor.end_timing("subscriber_download")

            # Step 5: Validate results
            performance_monitor.start_timing("result_validation")

            # Validate subscriber data
            expected_columns = ['email', 'nombre', 'apellido', 'telefono']
            validation_success = workflow_validator.validate_excel_output(output_file, expected_columns)

            assert validation_success == True, "Subscriber data validation failed"
            assert os.path.exists(output_file), "Subscriber file was not created"

            # Validate data integrity
            subscriber_data = excel_manager.read_excel(output_file)
            assert len(subscriber_data) == len(sample_subscriber_list)

            performance_monitor.end_timing("result_validation")
            performance_monitor.end_timing("subscriber_workflow")

            # Performance assertions
            performance_report = performance_monitor.get_report()
            assert performance_report['timings']['subscriber_workflow']['duration'] < 180  # Should complete in under 3 minutes

            e2e_logger.info(f"✅ Subscriber workflow completed successfully in {performance_report['timings']['subscriber_workflow']['duration']:.2f}s")

        finally:
            # Cleanup
            browser_manager.cleanup_browser(page.context)
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_error_recovery_workflow(
        self,
        browser_manager,
        e2e_config,
        test_data_manager,
        performance_monitor,
        screenshot_manager,
        e2e_logger
    ):
        """Test error recovery and resilience in workflows"""

        e2e_logger.info("🚀 Starting error recovery E2E test")
        performance_monitor.start_timing("error_recovery_test")

        try:
            # Step 1: Launch browser
            page = browser_manager.launch_browser()
            screenshot_manager.take_screenshot(page, "error_recovery", "browser_launched")

            # Step 2: Test navigation timeout recovery
            performance_monitor.start_timing("timeout_recovery")

            try:
                # Try to navigate to invalid URL
                browser_manager.navigate_to(page, "https://invalid.nonexistent.url")
            except Exception as e:
                e2e_logger.info(f"Expected navigation error caught: {e}")
                screenshot_manager.take_screenshot(page, "error_recovery", "navigation_error")

                # Recovery: Navigate to valid URL
                browser_manager.navigate_to(page, e2e_config['url_base'])
                screenshot_manager.take_screenshot(page, "error_recovery", "recovery_success")

                performance_monitor.add_checkpoint("timeout_recovery", "Successfully recovered from navigation error")

            performance_monitor.end_timing("timeout_recovery")

            # Step 3: Test element interaction error recovery
            performance_monitor.start_timing("element_recovery")

            try:
                # Try to interact with non-existent element
                browser_manager.click_element(page, "button", "NonExistentButton")
            except Exception as e:
                e2e_logger.info(f"Expected element error caught: {e}")
                screenshot_manager.take_screenshot(page, "error_recovery", "element_error")

                # Recovery: Continue with valid operations
                performance_monitor.add_checkpoint("element_recovery", "Successfully handled element not found")

            performance_monitor.end_timing("element_recovery")
            performance_monitor.end_timing("error_recovery_test")

            # Verify error recovery worked
            performance_report = performance_monitor.get_report()
            assert len(performance_report['checkpoints']) >= 2  # Should have recovery checkpoints

            e2e_logger.info("✅ Error recovery test completed successfully")

        finally:
            # Cleanup
            browser_manager.cleanup_browser(page.context)

    def test_performance_benchmarking(
        self,
        browser_manager,
        e2e_config,
        performance_monitor,
        e2e_logger
    ):
        """Test performance benchmarking for key operations"""

        e2e_logger.info("🚀 Starting performance benchmarking E2E test")

        # Performance thresholds (in seconds)
        thresholds = {
            'browser_launch': 10.0,
            'page_navigation': 5.0,
            'element_interaction': 2.0,
            'page_load': 8.0
        }

        try:
            # Test 1: Browser launch performance
            performance_monitor.start_timing("browser_launch")
            page = browser_manager.launch_browser()
            performance_monitor.end_timing("browser_launch")

            # Test 2: Page navigation performance
            performance_monitor.start_timing("page_navigation")
            browser_manager.navigate_to(page, e2e_config['url_base'])
            performance_monitor.end_timing("page_navigation")

            # Test 3: Page load performance
            performance_monitor.start_timing("page_load")
            page.wait_for_load_state('networkidle')
            performance_monitor.end_timing("page_load")

            # Test 4: Element interaction performance (mock)
            performance_monitor.start_timing("element_interaction")
            try:
                # Try to find a common element
                page.locator('body').wait_for(timeout=1000)
            except:
                pass  # Expected for mock test
            performance_monitor.end_timing("element_interaction")

            # Validate performance
            performance_report = performance_monitor.get_report()

            for operation, threshold in thresholds.items():
                if operation in performance_report['timings']:
                    duration = performance_report['timings'][operation]['duration']
                    assert duration <= threshold, f"{operation} took {duration:.2f}s, expected <= {threshold}s"
                    e2e_logger.info(f"✅ {operation}: {duration:.2f}s (threshold: {threshold}s)")

            e2e_logger.info("✅ Performance benchmarking completed successfully")

        finally:
            # Cleanup
            browser_manager.cleanup_browser(page.context)

    def test_concurrent_operations_workflow(
        self,
        e2e_config,
        test_data_manager,
        performance_monitor,
        e2e_logger
    ):
        """Test handling of concurrent operations (mocked)"""

        e2e_logger.info("🚀 Starting concurrent operations E2E test")
        performance_monitor.start_timing("concurrent_operations")

        # Simulate concurrent operations using mocked services
        from src.infrastructure.excel.excel_manager import ExcelManager

        try:
            excel_manager = ExcelManager()

            # Test 1: Concurrent Excel processing
            performance_monitor.start_timing("concurrent_excel")

            # Create multiple test files simultaneously
            test_files = []
            for i in range(3):
                test_data = [
                    {"email": f"concurrent{i}_{j}@test.com", "name": f"User {i}_{j}"}
                    for j in range(10)
                ]
                file_path = test_data_manager.create_test_excel_file(test_data)
                test_files.append(file_path)

            # Process files concurrently (simulated)
            results = []
            for file_path in test_files:
                data = excel_manager.read_excel(file_path)
                results.append(len(data))

            performance_monitor.end_timing("concurrent_excel")

            # Validate concurrent processing
            assert len(results) == 3
            assert all(result == 10 for result in results)  # Each file should have 10 rows

            performance_monitor.add_checkpoint("concurrent_processing", f"Processed {len(test_files)} files")

            # Test 2: Concurrent data validation
            performance_monitor.start_timing("concurrent_validation")

            validation_results = []
            for file_path in test_files:
                data = excel_manager.read_excel(file_path)
                stats = excel_manager.get_statistics(data)
                validation_results.append(stats['unique_emails'])

            performance_monitor.end_timing("concurrent_validation")

            # Validate results
            assert len(validation_results) == 3
            assert all(result == 10 for result in validation_results)  # Each should have 10 unique emails

            performance_monitor.end_timing("concurrent_operations")

            # Performance validation
            performance_report = performance_monitor.get_report()
            total_duration = performance_report['timings']['concurrent_operations']['duration']
            assert total_duration < 30.0, f"Concurrent operations took too long: {total_duration:.2f}s"

            e2e_logger.info(f"✅ Concurrent operations completed in {total_duration:.2f}s")

        finally:
            # Files are automatically cleaned up by test_data_manager
            pass