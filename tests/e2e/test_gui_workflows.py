"""
End-to-End tests for GUI workflows
"""
import pytest
import os
import time
import tkinter as tk
from typing import Dict, Any
from unittest.mock import patch, Mock, MagicMock

from src.presentation.gui.legacy_main_window import LegacyMainWindow
from src.infrastructure.excel.excel_manager import ExcelManager


@pytest.mark.e2e
@pytest.mark.gui
@pytest.mark.slow_e2e
class TestGUIWorkflows:
    """End-to-end tests for GUI application workflows"""

    def test_gui_application_startup(
        self,
        e2e_config,
        performance_monitor,
        e2e_logger
    ):
        """Test GUI application startup and initialization"""

        e2e_logger.info("🚀 Starting GUI startup E2E test")
        performance_monitor.start_timing("gui_startup")

        try:
            # Mock tkinter to avoid actual GUI creation in tests
            with patch('tkinter.Tk') as mock_tk, \
                 patch('tkinter.ttk.Frame') as mock_frame:

                mock_root = Mock()
                mock_tk.return_value = mock_root

                # Initialize GUI application
                performance_monitor.start_timing("gui_initialization")
                app = LegacyMainWindow()
                performance_monitor.end_timing("gui_initialization")

                # Verify initialization
                assert app is not None
                performance_monitor.add_checkpoint("gui_initialized", "Main window created")

                # Test window configuration
                performance_monitor.start_timing("window_configuration")

                # Mock window setup methods
                with patch.object(app, '_setup_window') as mock_setup, \
                     patch.object(app, '_create_widgets') as mock_widgets:

                    app._setup_window()
                    app._create_widgets()

                    mock_setup.assert_called_once()
                    mock_widgets.assert_called_once()

                performance_monitor.end_timing("window_configuration")
                performance_monitor.end_timing("gui_startup")

                # Performance validation
                performance_report = performance_monitor.get_report()
                startup_time = performance_report['timings']['gui_startup']['duration']
                assert startup_time < 5.0, f"GUI startup took too long: {startup_time:.2f}s"

                e2e_logger.info(f"✅ GUI startup completed in {startup_time:.2f}s")

        except Exception as e:
            e2e_logger.error(f"❌ GUI startup test failed: {e}")
            raise

    def test_campaign_listing_gui_workflow(
        self,
        e2e_config,
        campaign_search_terms,
        test_data_manager,
        performance_monitor,
        workflow_validator,
        e2e_logger
    ):
        """Test campaign listing workflow through GUI"""

        e2e_logger.info("🚀 Starting campaign listing GUI E2E test")
        performance_monitor.start_timing("campaign_gui_workflow")

        # Create test search file
        search_file_path = test_data_manager.create_test_excel_file(campaign_search_terms)

        try:
            # Mock GUI components
            with patch('tkinter.Tk') as mock_tk, \
                 patch('tkinter.filedialog.askopenfilename') as mock_file_dialog, \
                 patch('tkinter.messagebox.showinfo') as mock_message:

                mock_root = Mock()
                mock_tk.return_value = mock_root

                # Setup file dialog to return our test file
                mock_file_dialog.return_value = search_file_path

                # Initialize GUI application
                app = LegacyMainWindow()

                # Mock the campaign processing
                with patch.object(app, 'process_campaigns') as mock_process:
                    mock_result = {
                        'success': True,
                        'campaigns_processed': len(campaign_search_terms),
                        'output_file': f"data/gui_test_campaigns_{test_data_manager.test_prefix}.xlsx",
                        'processing_time': 30.5
                    }
                    mock_process.return_value = mock_result

                    # Simulate user clicking "List Campaigns" button
                    performance_monitor.start_timing("campaign_processing")
                    result = app.process_campaigns()
                    performance_monitor.end_timing("campaign_processing")

                    # Verify processing
                    assert result['success'] == True
                    assert result['campaigns_processed'] > 0
                    performance_monitor.add_checkpoint("campaigns_processed", f"Processed: {result['campaigns_processed']}")

                # Create mock output file for validation
                excel_manager = ExcelManager()
                output_file = result['output_file']

                # Generate mock campaign data
                campaign_data = []
                for term in campaign_search_terms:
                    campaign_data.append({
                        'Campaign Name': term['Nombre'],
                        'Type': term['Tipo'],
                        'Send Date': term['Fecha envío'],
                        'Emails Sent': 1000,
                        'Opens': 200,
                        'Clicks': 50,
                        'Open Rate': '20.0%',
                        'Click Rate': '5.0%'
                    })

                excel_manager.write_excel(campaign_data, output_file)

                # Validate output
                performance_monitor.start_timing("result_validation")
                expected_columns = ['Campaign Name', 'Type', 'Send Date', 'Emails Sent', 'Opens', 'Clicks']
                validation_success = workflow_validator.validate_excel_output(output_file, expected_columns)

                assert validation_success == True, "Campaign GUI output validation failed"
                performance_monitor.end_timing("result_validation")

                performance_monitor.end_timing("campaign_gui_workflow")

                # Performance validation
                performance_report = performance_monitor.get_report()
                total_time = performance_report['timings']['campaign_gui_workflow']['duration']
                assert total_time < 60.0, f"Campaign GUI workflow took too long: {total_time:.2f}s"

                e2e_logger.info(f"✅ Campaign listing GUI workflow completed in {total_time:.2f}s")

        finally:
            # Cleanup
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_subscriber_management_gui_workflow(
        self,
        e2e_config,
        sample_subscriber_list,
        list_configuration,
        test_data_manager,
        performance_monitor,
        workflow_validator,
        e2e_logger
    ):
        """Test subscriber management workflow through GUI"""

        e2e_logger.info("🚀 Starting subscriber management GUI E2E test")
        performance_monitor.start_timing("subscriber_gui_workflow")

        # Create test subscriber file
        subscriber_file_path = test_data_manager.create_test_excel_file(sample_subscriber_list)

        try:
            # Mock GUI components
            with patch('tkinter.Tk') as mock_tk, \
                 patch('tkinter.filedialog.askopenfilename') as mock_file_dialog, \
                 patch('tkinter.simpledialog.askstring') as mock_input_dialog:

                mock_root = Mock()
                mock_tk.return_value = mock_root

                # Setup dialogs
                mock_file_dialog.return_value = subscriber_file_path
                mock_input_dialog.return_value = test_data_manager.create_test_name("subscriber_list")

                # Initialize GUI application
                app = LegacyMainWindow()

                # Mock subscriber operations
                with patch.object(app, 'create_subscriber_list') as mock_create, \
                     patch.object(app, 'download_subscribers') as mock_download:

                    # Mock list creation
                    mock_create_result = {
                        'success': True,
                        'list_name': test_data_manager.create_test_name("subscriber_list"),
                        'subscribers_added': len(sample_subscriber_list),
                        'processing_time': 25.3
                    }
                    mock_create.return_value = mock_create_result

                    # Mock subscriber download
                    output_file = f"data/gui_test_subscribers_{test_data_manager.test_prefix}.xlsx"
                    mock_download_result = {
                        'success': True,
                        'output_file': output_file,
                        'subscribers_downloaded': len(sample_subscriber_list),
                        'processing_time': 15.7
                    }
                    mock_download.return_value = mock_download_result

                    # Simulate user workflow
                    performance_monitor.start_timing("list_creation")
                    create_result = app.create_subscriber_list()
                    performance_monitor.end_timing("list_creation")

                    performance_monitor.start_timing("subscriber_download")
                    download_result = app.download_subscribers()
                    performance_monitor.end_timing("subscriber_download")

                    # Verify operations
                    assert create_result['success'] == True
                    assert download_result['success'] == True
                    assert create_result['subscribers_added'] == len(sample_subscriber_list)

                    performance_monitor.add_checkpoint("list_created", f"Added: {create_result['subscribers_added']}")
                    performance_monitor.add_checkpoint("subscribers_downloaded", f"Downloaded: {download_result['subscribers_downloaded']}")

                # Create mock output file for validation
                excel_manager = ExcelManager()
                excel_manager.write_excel(sample_subscriber_list, output_file)

                # Validate output
                performance_monitor.start_timing("result_validation")
                expected_columns = ['email', 'nombre', 'apellido', 'telefono']
                validation_success = workflow_validator.validate_excel_output(output_file, expected_columns)

                assert validation_success == True, "Subscriber GUI output validation failed"
                performance_monitor.end_timing("result_validation")

                performance_monitor.end_timing("subscriber_gui_workflow")

                # Performance validation
                performance_report = performance_monitor.get_report()
                total_time = performance_report['timings']['subscriber_gui_workflow']['duration']
                assert total_time < 90.0, f"Subscriber GUI workflow took too long: {total_time:.2f}s"

                e2e_logger.info(f"✅ Subscriber management GUI workflow completed in {total_time:.2f}s")

        finally:
            # Cleanup
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_gui_error_handling_workflow(
        self,
        e2e_config,
        test_data_manager,
        performance_monitor,
        e2e_logger
    ):
        """Test GUI error handling and user feedback"""

        e2e_logger.info("🚀 Starting GUI error handling E2E test")
        performance_monitor.start_timing("gui_error_handling")

        try:
            # Mock GUI components
            with patch('tkinter.Tk') as mock_tk, \
                 patch('tkinter.messagebox.showerror') as mock_error_dialog, \
                 patch('tkinter.messagebox.showwarning') as mock_warning_dialog:

                mock_root = Mock()
                mock_tk.return_value = mock_root

                # Initialize GUI application
                app = LegacyMainWindow()

                # Test 1: Invalid file handling
                performance_monitor.start_timing("invalid_file_handling")

                with patch.object(app, 'process_campaigns') as mock_process:
                    # Simulate file processing error
                    mock_process.side_effect = FileNotFoundError("Test file not found")

                    try:
                        app.process_campaigns()
                    except FileNotFoundError:
                        # Verify error dialog was shown
                        mock_error_dialog.assert_called()
                        performance_monitor.add_checkpoint("file_error_handled", "Error dialog shown")

                performance_monitor.end_timing("invalid_file_handling")

                # Test 2: Network error handling
                performance_monitor.start_timing("network_error_handling")

                with patch.object(app, 'download_subscribers') as mock_download:
                    # Simulate network error
                    mock_download.side_effect = ConnectionError("Network connection failed")

                    try:
                        app.download_subscribers()
                    except ConnectionError:
                        # Verify error dialog was shown
                        mock_error_dialog.assert_called()
                        performance_monitor.add_checkpoint("network_error_handled", "Network error handled")

                performance_monitor.end_timing("network_error_handling")

                # Test 3: Validation error handling
                performance_monitor.start_timing("validation_error_handling")

                with patch.object(app, 'create_subscriber_list') as mock_create:
                    # Simulate validation error
                    mock_create.return_value = {
                        'success': False,
                        'error': 'Invalid email format in row 5',
                        'validation_errors': ['Email validation failed']
                    }

                    result = app.create_subscriber_list()

                    # Verify warning dialog was shown for validation errors
                    if not result['success']:
                        mock_warning_dialog.assert_called()
                        performance_monitor.add_checkpoint("validation_error_handled", "Validation error shown")

                performance_monitor.end_timing("validation_error_handling")

                performance_monitor.end_timing("gui_error_handling")

                # Verify error handling performance
                performance_report = performance_monitor.get_report()
                error_handling_time = performance_report['timings']['gui_error_handling']['duration']
                assert error_handling_time < 10.0, f"Error handling took too long: {error_handling_time:.2f}s"

                # Verify all error types were handled
                checkpoints = [cp['name'] for cp in performance_report['checkpoints']]
                assert 'file_error_handled' in checkpoints
                assert 'network_error_handled' in checkpoints
                assert 'validation_error_handled' in checkpoints

                e2e_logger.info(f"✅ GUI error handling completed in {error_handling_time:.2f}s")

        except Exception as e:
            e2e_logger.error(f"❌ GUI error handling test failed: {e}")
            raise

    def test_gui_progress_tracking_workflow(
        self,
        e2e_config,
        test_data_manager,
        performance_monitor,
        e2e_logger
    ):
        """Test GUI progress tracking and user feedback"""

        e2e_logger.info("🚀 Starting GUI progress tracking E2E test")
        performance_monitor.start_timing("gui_progress_tracking")

        try:
            # Mock GUI components including progress dialog
            with patch('tkinter.Tk') as mock_tk, \
                 patch('src.presentation.gui.progress_dialog.ProgressDialog') as mock_progress_dialog:

                mock_root = Mock()
                mock_tk.return_value = mock_root

                # Setup progress dialog mock
                mock_dialog_instance = Mock()
                mock_progress_dialog.return_value = mock_dialog_instance

                # Initialize GUI application
                app = LegacyMainWindow()

                # Test progress tracking during campaign processing
                performance_monitor.start_timing("progress_tracking_campaigns")

                with patch.object(app, 'process_campaigns') as mock_process:
                    def simulate_progress():
                        # Simulate progress updates
                        mock_dialog_instance.update_progress.assert_called()
                        return {
                            'success': True,
                            'campaigns_processed': 5,
                            'progress_updates': 10
                        }

                    mock_process.side_effect = simulate_progress

                    result = app.process_campaigns()

                    # Verify progress tracking
                    assert result['success'] == True
                    performance_monitor.add_checkpoint("campaign_progress_tracked", "Progress dialog used")

                performance_monitor.end_timing("progress_tracking_campaigns")

                # Test progress tracking during subscriber operations
                performance_monitor.start_timing("progress_tracking_subscribers")

                with patch.object(app, 'download_subscribers') as mock_download:
                    def simulate_subscriber_progress():
                        # Simulate subscriber progress updates
                        for i in range(0, 101, 20):  # 0%, 20%, 40%, 60%, 80%, 100%
                            mock_dialog_instance.update_progress.called_with(i)
                        return {
                            'success': True,
                            'subscribers_downloaded': 150,
                            'progress_updates': 6
                        }

                    mock_download.side_effect = simulate_subscriber_progress

                    result = app.download_subscribers()

                    # Verify subscriber progress tracking
                    assert result['success'] == True
                    performance_monitor.add_checkpoint("subscriber_progress_tracked", "Subscriber progress tracked")

                performance_monitor.end_timing("progress_tracking_subscribers")

                performance_monitor.end_timing("gui_progress_tracking")

                # Performance validation
                performance_report = performance_monitor.get_report()
                progress_time = performance_report['timings']['gui_progress_tracking']['duration']
                assert progress_time < 15.0, f"Progress tracking took too long: {progress_time:.2f}s"

                # Verify progress checkpoints
                checkpoints = [cp['name'] for cp in performance_report['checkpoints']]
                assert 'campaign_progress_tracked' in checkpoints
                assert 'subscriber_progress_tracked' in checkpoints

                e2e_logger.info(f"✅ GUI progress tracking completed in {progress_time:.2f}s")

        except Exception as e:
            e2e_logger.error(f"❌ GUI progress tracking test failed: {e}")
            raise

    def test_gui_configuration_workflow(
        self,
        e2e_config,
        performance_monitor,
        e2e_logger
    ):
        """Test GUI configuration management workflow"""

        e2e_logger.info("🚀 Starting GUI configuration E2E test")
        performance_monitor.start_timing("gui_configuration")

        try:
            # Mock GUI components including config dialog
            with patch('tkinter.Tk') as mock_tk, \
                 patch('src.presentation.gui.config_window.ConfigWindow') as mock_config_window:

                mock_root = Mock()
                mock_tk.return_value = mock_root

                # Setup config window mock
                mock_config_instance = Mock()
                mock_config_window.return_value = mock_config_instance

                # Initialize GUI application
                app = LegacyMainWindow()

                # Test configuration loading
                performance_monitor.start_timing("config_loading")

                with patch.object(app, 'load_configuration') as mock_load_config:
                    mock_load_config.return_value = {
                        'success': True,
                        'config': e2e_config,
                        'validation_passed': True
                    }

                    config_result = app.load_configuration()

                    assert config_result['success'] == True
                    assert config_result['validation_passed'] == True
                    performance_monitor.add_checkpoint("config_loaded", "Configuration loaded successfully")

                performance_monitor.end_timing("config_loading")

                # Test configuration validation
                performance_monitor.start_timing("config_validation")

                with patch.object(app, 'validate_configuration') as mock_validate:
                    mock_validate.return_value = {
                        'valid': True,
                        'errors': [],
                        'warnings': []
                    }

                    validation_result = app.validate_configuration()

                    assert validation_result['valid'] == True
                    assert len(validation_result['errors']) == 0
                    performance_monitor.add_checkpoint("config_validated", "Configuration validation passed")

                performance_monitor.end_timing("config_validation")

                # Test configuration updates
                performance_monitor.start_timing("config_updates")

                with patch.object(app, 'update_configuration') as mock_update:
                    new_config = e2e_config.copy()
                    new_config['headless'] = not new_config['headless']

                    mock_update.return_value = {
                        'success': True,
                        'updated_config': new_config,
                        'changes_applied': True
                    }

                    update_result = app.update_configuration(new_config)

                    assert update_result['success'] == True
                    assert update_result['changes_applied'] == True
                    performance_monitor.add_checkpoint("config_updated", "Configuration updated successfully")

                performance_monitor.end_timing("config_updates")

                performance_monitor.end_timing("gui_configuration")

                # Performance validation
                performance_report = performance_monitor.get_report()
                config_time = performance_report['timings']['gui_configuration']['duration']
                assert config_time < 20.0, f"Configuration workflow took too long: {config_time:.2f}s"

                # Verify configuration checkpoints
                checkpoints = [cp['name'] for cp in performance_report['checkpoints']]
                assert 'config_loaded' in checkpoints
                assert 'config_validated' in checkpoints
                assert 'config_updated' in checkpoints

                e2e_logger.info(f"✅ GUI configuration workflow completed in {config_time:.2f}s")

        except Exception as e:
            e2e_logger.error(f"❌ GUI configuration test failed: {e}")
            raise