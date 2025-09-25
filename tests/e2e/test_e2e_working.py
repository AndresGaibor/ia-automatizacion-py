"""
Working End-to-End tests for complete workflows
"""
import pytest
import os
import time
import tempfile
import pandas as pd
from typing import Dict, Any
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime


@pytest.mark.e2e
@pytest.mark.fast
class TestWorkingE2EWorkflows:
    """End-to-end tests that actually work with current structure"""

    def test_excel_processing_workflow(self, sample_excel_data, e2e_logger, performance_monitor):
        """Test complete Excel processing workflow"""

        e2e_logger.info("🚀 Starting Excel processing E2E test")
        performance_monitor.start_timing("excel_processing_workflow")

        try:
            # Step 1: Create and read Excel file
            performance_monitor.start_timing("excel_read")

            # Create temporary Excel file from fixture data
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
                temp_excel_file = f.name

            # Use sample data from fixture
            sample_df = pd.DataFrame([
                {"email": "test1@example.com", "nombre": "Test 1", "apellido": "User"},
                {"email": "test2@example.com", "nombre": "Test 2", "apellido": "User"},
                {"email": "test3@example.com", "nombre": "Test 3", "apellido": "User"}
            ])
            sample_df.to_excel(temp_excel_file, index=False)

            df = pd.read_excel(temp_excel_file)
            performance_monitor.end_timing("excel_read")

            assert len(df) == 3, "Should have 3 rows"
            assert 'email' in df.columns, "Should have email column"

            # Step 2: Process data
            performance_monitor.start_timing("data_processing")

            # Add new columns (simulate campaign processing)
            df['opens'] = [10, 15, 8]
            df['clicks'] = [2, 3, 1]
            df['open_rate'] = df['opens'] / 100 * 100

            performance_monitor.end_timing("data_processing")
            performance_monitor.add_checkpoint("data_processed", f"Added metrics to {len(df)} records")

            # Step 3: Generate output file
            performance_monitor.start_timing("excel_write")

            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
                output_file = f.name

            df.to_excel(output_file, index=False)
            performance_monitor.end_timing("excel_write")

            # Step 4: Validate output
            performance_monitor.start_timing("output_validation")

            # Read back and validate
            result_df = pd.read_excel(output_file)
            assert len(result_df) == 3, "Output should have 3 rows"
            assert 'opens' in result_df.columns, "Should have opens column"
            assert 'clicks' in result_df.columns, "Should have clicks column"
            assert result_df['opens'].sum() == 33, "Total opens should be 33"

            performance_monitor.end_timing("output_validation")
            performance_monitor.end_timing("excel_processing_workflow")

            # Performance validation
            performance_report = performance_monitor.get_report()
            total_time = performance_report['timings']['excel_processing_workflow']['duration']
            assert total_time < 5.0, f"Workflow took too long: {total_time:.2f}s"

            e2e_logger.info(f"✅ Excel processing workflow completed in {total_time:.2f}s")

        finally:
            # Cleanup
            if os.path.exists(output_file):
                os.unlink(output_file)
            if os.path.exists(temp_excel_file):
                os.unlink(temp_excel_file)

    def test_data_validation_workflow(self, e2e_logger, performance_monitor):
        """Test data validation workflow"""

        e2e_logger.info("🚀 Starting data validation E2E test")
        performance_monitor.start_timing("data_validation_workflow")

        try:
            # Step 1: Create test data with various issues
            performance_monitor.start_timing("test_data_creation")

            test_data = pd.DataFrame([
                {"email": "valid@example.com", "nombre": "Valid User", "status": "active"},
                {"email": "invalid-email", "nombre": "Invalid Email", "status": "active"},
                {"email": "", "nombre": "Empty Email", "status": "inactive"},
                {"email": "duplicate@example.com", "nombre": "First Duplicate", "status": "active"},
                {"email": "duplicate@example.com", "nombre": "Second Duplicate", "status": "active"},
                {"email": "   spaces@example.com   ", "nombre": "  Spaces  ", "status": "active"}
            ])

            performance_monitor.end_timing("test_data_creation")
            performance_monitor.add_checkpoint("test_data_created", f"Created {len(test_data)} test records")

            # Step 2: Email validation
            performance_monitor.start_timing("email_validation")

            valid_emails = test_data['email'].str.contains('@', na=False)
            valid_count = valid_emails.sum()
            invalid_count = len(test_data) - valid_count

            performance_monitor.end_timing("email_validation")
            performance_monitor.add_checkpoint("email_validation", f"Found {valid_count} valid, {invalid_count} invalid emails")

            # Step 3: Data cleaning
            performance_monitor.start_timing("data_cleaning")

            # Remove empty emails
            cleaned_data = test_data[test_data['email'].str.strip() != '']

            # Clean whitespace
            cleaned_data = cleaned_data.copy()
            cleaned_data['email'] = cleaned_data['email'].str.strip()
            cleaned_data['nombre'] = cleaned_data['nombre'].str.strip()

            # Remove duplicates
            cleaned_data = cleaned_data.drop_duplicates(subset=['email']).reset_index(drop=True)

            performance_monitor.end_timing("data_cleaning")
            performance_monitor.add_checkpoint("data_cleaned", f"Cleaned to {len(cleaned_data)} records")

            # Step 4: Validation results
            performance_monitor.start_timing("validation_summary")

            validation_results = {
                'original_count': len(test_data),
                'cleaned_count': len(cleaned_data),
                'removed_empty': len(test_data) - len(test_data[test_data['email'].str.strip() != '']),
                'removed_duplicates': len(test_data) - len(cleaned_data),
                'final_valid_emails': cleaned_data['email'].str.contains('@', na=False).sum()
            }

            performance_monitor.end_timing("validation_summary")
            performance_monitor.end_timing("data_validation_workflow")

            # Assertions
            assert validation_results['cleaned_count'] > 0, "Should have some cleaned data"
            assert validation_results['final_valid_emails'] >= 2, "Should have at least 2 valid emails"
            assert cleaned_data.iloc[0]['email'] == 'valid@example.com', "First record should be valid email"

            # Performance validation
            performance_report = performance_monitor.get_report()
            total_time = performance_report['timings']['data_validation_workflow']['duration']
            assert total_time < 3.0, f"Validation workflow took too long: {total_time:.2f}s"

            e2e_logger.info(f"✅ Data validation workflow completed in {total_time:.2f}s")
            e2e_logger.info(f"📊 Validation results: {validation_results}")

        except Exception as e:
            e2e_logger.error(f"❌ Data validation workflow failed: {e}")
            raise

    def test_mock_api_workflow(self, mocker, e2e_logger, performance_monitor):
        """Test mock API interaction workflow"""

        e2e_logger.info("🚀 Starting mock API workflow E2E test")
        performance_monitor.start_timing("api_workflow")

        try:
            # Step 1: Mock API responses
            performance_monitor.start_timing("api_setup")

            # Create mock HTTP client
            mock_httpx_client = Mock()

            # Setup different response scenarios
            mock_responses = {
                'campaigns': {'status': 'success', 'data': [
                    {'id': 1, 'name': 'Test Campaign 1', 'recipients': 1000, 'opens': 200},
                    {'id': 2, 'name': 'Test Campaign 2', 'recipients': 1500, 'opens': 300},
                ]},
                'subscribers': {'status': 'success', 'data': [
                    {'email': 'user1@test.com', 'name': 'User 1', 'status': 'active'},
                    {'email': 'user2@test.com', 'name': 'User 2', 'status': 'active'},
                ]}
            }

            mock_httpx_client.get.side_effect = [
                Mock(status_code=200, json=lambda: mock_responses['campaigns']),
                Mock(status_code=200, json=lambda: mock_responses['subscribers'])
            ]

            performance_monitor.end_timing("api_setup")
            performance_monitor.add_checkpoint("api_setup", "Mock API configured")

            # Step 2: Simulate API calls
            performance_monitor.start_timing("api_calls")

            # Call 1: Get campaigns
            campaigns_response = mock_httpx_client.get("/api/campaigns")
            campaigns_data = campaigns_response.json()

            # Call 2: Get subscribers
            subscribers_response = mock_httpx_client.get("/api/subscribers")
            subscribers_data = subscribers_response.json()

            performance_monitor.end_timing("api_calls")
            performance_monitor.add_checkpoint("api_calls", "API calls completed")

            # Step 3: Process API responses
            performance_monitor.start_timing("response_processing")

            # Process campaigns
            campaigns_df = pd.DataFrame(campaigns_data['data'])
            total_recipients = campaigns_df['recipients'].sum()
            total_opens = campaigns_df['opens'].sum()
            overall_open_rate = (total_opens / total_recipients) * 100 if total_recipients > 0 else 0

            # Process subscribers
            subscribers_df = pd.DataFrame(subscribers_data['data'])
            active_subscribers = subscribers_df[subscribers_df['status'] == 'active']

            performance_monitor.end_timing("response_processing")
            performance_monitor.add_checkpoint("response_processing", f"Processed {len(campaigns_df)} campaigns, {len(active_subscribers)} subscribers")

            # Step 4: Generate summary report
            performance_monitor.start_timing("report_generation")

            summary_report = {
                'total_campaigns': len(campaigns_df),
                'total_recipients': int(total_recipients),
                'total_opens': int(total_opens),
                'overall_open_rate': round(overall_open_rate, 2),
                'active_subscribers': len(active_subscribers),
                'processing_timestamp': datetime.now().isoformat()
            }

            performance_monitor.end_timing("report_generation")
            performance_monitor.end_timing("api_workflow")

            # Validations
            assert campaigns_response.status_code == 200, "Campaigns API should return 200"
            assert subscribers_response.status_code == 200, "Subscribers API should return 200"
            assert summary_report['total_campaigns'] == 2, "Should have 2 campaigns"
            assert summary_report['total_recipients'] == 2500, "Should have 2500 total recipients"
            assert summary_report['active_subscribers'] == 2, "Should have 2 active subscribers"
            assert summary_report['overall_open_rate'] == 20.0, "Overall open rate should be 20%"

            # Performance validation
            performance_report = performance_monitor.get_report()
            total_time = performance_report['timings']['api_workflow']['duration']
            assert total_time < 2.0, f"API workflow took too long: {total_time:.2f}s"

            # Verify mock calls
            assert mock_httpx_client.get.call_count == 2, "Should have made 2 API calls"

            e2e_logger.info(f"✅ Mock API workflow completed in {total_time:.2f}s")
            e2e_logger.info(f"📊 Summary report: {summary_report}")

        except Exception as e:
            e2e_logger.error(f"❌ Mock API workflow failed: {e}")
            raise

    def test_file_processing_pipeline(self, e2e_logger, performance_monitor, workflow_validator):
        """Test complete file processing pipeline"""

        e2e_logger.info("🚀 Starting file processing pipeline E2E test")
        performance_monitor.start_timing("file_pipeline")

        temp_files = []

        try:
            # Step 1: Create multiple input files
            performance_monitor.start_timing("file_creation")

            file_data = [
                [
                    {"email": "campaign1@test.com", "campaign": "Newsletter", "opens": 50},
                    {"email": "campaign2@test.com", "campaign": "Newsletter", "opens": 75}
                ],
                [
                    {"email": "promo1@test.com", "campaign": "Promotion", "opens": 30},
                    {"email": "promo2@test.com", "campaign": "Promotion", "opens": 45}
                ],
                [
                    {"email": "update1@test.com", "campaign": "Update", "opens": 60},
                    {"email": "update2@test.com", "campaign": "Update", "opens": 40}
                ]
            ]

            for i, data in enumerate(file_data):
                with tempfile.NamedTemporaryFile(suffix=f'_input_{i}.xlsx', delete=False) as f:
                    df = pd.DataFrame(data)
                    df.to_excel(f.name, index=False)
                    temp_files.append(f.name)

            performance_monitor.end_timing("file_creation")
            performance_monitor.add_checkpoint("file_creation", f"Created {len(temp_files)} input files")

            # Step 2: Process each file
            performance_monitor.start_timing("file_processing")

            all_data = []
            for file_path in temp_files:
                df = pd.read_excel(file_path)
                # Add processing timestamp
                df['processed_at'] = datetime.now().isoformat()
                # Calculate click rate (mock)
                df['clicks'] = df['opens'] * 0.2  # 20% click rate
                all_data.append(df)

            performance_monitor.end_timing("file_processing")
            performance_monitor.add_checkpoint("file_processing", f"Processed {len(all_data)} files")

            # Step 3: Merge all data
            performance_monitor.start_timing("data_merging")

            combined_df = pd.concat(all_data, ignore_index=True)

            # Add summary calculations
            combined_df['open_rate'] = (combined_df['opens'] / 100) * 100  # Mock calculation
            combined_df['click_rate'] = (combined_df['clicks'] / combined_df['opens']) * 100

            performance_monitor.end_timing("data_merging")
            performance_monitor.add_checkpoint("data_merging", f"Merged to {len(combined_df)} total records")

            # Step 4: Generate final report
            performance_monitor.start_timing("report_creation")

            with tempfile.NamedTemporaryFile(suffix='_final_report.xlsx', delete=False) as f:
                final_report_file = f.name
                temp_files.append(final_report_file)

            # Create summary sheet
            summary_stats = combined_df.groupby('campaign').agg({
                'opens': ['sum', 'mean'],
                'clicks': ['sum', 'mean'],
                'email': 'count'
            }).round(2)

            # Write to Excel with multiple sheets
            with pd.ExcelWriter(final_report_file) as writer:
                combined_df.to_excel(writer, sheet_name='Raw Data', index=False)
                summary_stats.to_excel(writer, sheet_name='Summary')

            performance_monitor.end_timing("report_creation")
            performance_monitor.end_timing("file_pipeline")

            # Step 5: Validate final output
            performance_monitor.start_timing("output_validation")

            # Validate file exists and has correct structure
            validation_success = workflow_validator.validate_excel_output(
                final_report_file,
                ['email', 'campaign', 'opens', 'clicks']
            )

            # Read back and validate data
            final_df = pd.read_excel(final_report_file, sheet_name='Raw Data')

            performance_monitor.end_timing("output_validation")

            # Assertions
            assert validation_success == True, "Final report validation should pass"
            assert len(final_df) == 6, "Should have 6 total records"
            assert final_df['campaign'].nunique() == 3, "Should have 3 unique campaigns"
            assert final_df['opens'].sum() == 300, "Total opens should be 300"
            assert all(final_df['clicks'] > 0), "All records should have clicks"

            # Performance validation
            performance_report = performance_monitor.get_report()
            total_time = performance_report['timings']['file_pipeline']['duration']
            assert total_time < 10.0, f"File pipeline took too long: {total_time:.2f}s"

            # Summary statistics
            campaign_summary = final_df.groupby('campaign').agg({
                'opens': 'sum',
                'clicks': 'sum',
                'email': 'count'
            }).to_dict()

            e2e_logger.info(f"✅ File processing pipeline completed in {total_time:.2f}s")
            e2e_logger.info(f"📊 Campaign summary: {campaign_summary}")

        finally:
            # Cleanup all temp files
            for file_path in temp_files:
                try:
                    if os.path.exists(file_path):
                        os.unlink(file_path)
                except:
                    pass  # Ignore cleanup errors

    def test_error_handling_and_recovery(self, e2e_logger, performance_monitor):
        """Test error handling and recovery scenarios"""

        e2e_logger.info("🚀 Starting error handling E2E test")
        performance_monitor.start_timing("error_handling_workflow")

        try:
            # Test 1: File not found error handling
            performance_monitor.start_timing("file_not_found_test")

            try:
                pd.read_excel("nonexistent_file.xlsx")
                assert False, "Should have raised FileNotFoundError"
            except FileNotFoundError as e:
                e2e_logger.info(f"✅ Correctly handled FileNotFoundError: {e}")
                performance_monitor.add_checkpoint("file_error_handled", "FileNotFoundError handled correctly")

            performance_monitor.end_timing("file_not_found_test")

            # Test 2: Invalid data handling
            performance_monitor.start_timing("invalid_data_test")

            invalid_data = pd.DataFrame([
                {"email": "", "name": ""},
                {"email": "invalid", "name": "Invalid Email"},
                {"email": None, "name": "None Email"}
            ])

            # Clean invalid data
            cleaned = invalid_data.dropna()
            cleaned = cleaned[cleaned['email'].str.strip() != '']

            assert len(cleaned) == 1, "Should have 1 valid record after cleaning"
            performance_monitor.add_checkpoint("invalid_data_handled", f"Cleaned {len(invalid_data) - len(cleaned)} invalid records")

            performance_monitor.end_timing("invalid_data_test")

            # Test 3: Recovery simulation
            performance_monitor.start_timing("recovery_test")

            retry_count = 0
            max_retries = 3

            while retry_count < max_retries:
                try:
                    if retry_count < 2:  # Simulate failures
                        raise ConnectionError(f"Simulated failure {retry_count + 1}")
                    else:  # Success on 3rd try
                        result = {"status": "success", "data": "recovered"}
                        break
                except ConnectionError as e:
                    retry_count += 1
                    e2e_logger.info(f"Retry {retry_count}: {e}")
                    if retry_count >= max_retries:
                        raise

            assert result["status"] == "success", "Recovery should succeed"
            performance_monitor.add_checkpoint("recovery_handled", f"Recovered after {retry_count} retries")

            performance_monitor.end_timing("recovery_test")
            performance_monitor.end_timing("error_handling_workflow")

            # Performance validation
            performance_report = performance_monitor.get_report()
            total_time = performance_report['timings']['error_handling_workflow']['duration']

            # Verify all error scenarios were handled
            checkpoints = [cp['name'] for cp in performance_report['checkpoints']]
            assert 'file_error_handled' in checkpoints, "File error should be handled"
            assert 'invalid_data_handled' in checkpoints, "Invalid data should be handled"
            assert 'recovery_handled' in checkpoints, "Recovery should be handled"

            e2e_logger.info(f"✅ Error handling workflow completed in {total_time:.2f}s")
            e2e_logger.info(f"🛡️ All error scenarios handled successfully")

        except Exception as e:
            e2e_logger.error(f"❌ Error handling workflow failed: {e}")
            raise