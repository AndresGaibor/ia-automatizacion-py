"""
Unit tests for logging system
"""
import pytest
from unittest.mock import patch, mock_open
from datetime import datetime

from src.shared.logging import get_logger
from src.shared.logging.legacy_logger import PerformanceLogger


@pytest.mark.unit
class TestLoggingSystem:
    """Unit tests for logging functionality"""

    def test_logger_initialization(self, mock_config):
        """Test logger initialization with different configs"""
        with patch('src.shared.logging.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            logger = get_logger()
            assert logger is not None

    def test_logger_singleton_behavior(self):
        """Test that get_logger returns the same instance"""
        logger1 = get_logger()
        logger2 = get_logger()

        assert logger1 is logger2

    def test_performance_logger_timer(self):
        """Test performance logger timer functionality"""
        logger = PerformanceLogger()

        # Start timer
        logger.start_timer("test_operation")
        assert "test_operation" in logger.active_timers

        # End timer
        logger.end_timer("test_operation", "Test completed")
        assert "test_operation" not in logger.active_timers
        assert len(logger.completed_operations) > 0

    def test_performance_logger_context_manager(self):
        """Test performance logger as context manager"""
        logger = PerformanceLogger()

        with logger.timer("context_operation"):
            pass  # Simulate some work

        # Should have recorded the operation
        completed_ops = [op for op in logger.completed_operations if op['operation'] == 'context_operation']
        assert len(completed_ops) == 1

    def test_performance_logger_report_generation(self):
        """Test performance report generation"""
        logger = PerformanceLogger()

        # Add some test operations
        logger.start_timer("fast_op")
        logger.end_timer("fast_op", "Fast operation", duration=0.1)

        logger.start_timer("slow_op")
        logger.end_timer("slow_op", "Slow operation", duration=2.0)

        # Generate report
        report = logger.get_performance_report()

        assert "Total operations" in report
        assert "Fastest" in report
        assert "Slowest" in report

    @patch('builtins.print')
    def test_performance_logger_print_report(self, mock_print):
        """Test performance report printing"""
        logger = PerformanceLogger()

        logger.start_timer("test_op")
        logger.end_timer("test_op", "Test operation")

        logger.print_performance_report()

        # Should have printed something
        assert mock_print.called

    def test_logging_levels(self, mock_logger):
        """Test different logging levels"""
        mock_logger.info("Info message")
        mock_logger.warning("Warning message")
        mock_logger.error("Error message")
        mock_logger.debug("Debug message")

        mock_logger.info.assert_called_with("Info message")
        mock_logger.warning.assert_called_with("Warning message")
        mock_logger.error.assert_called_with("Error message")
        mock_logger.debug.assert_called_with("Debug message")

    def test_structured_logging_format(self):
        """Test structured logging format"""
        logger = PerformanceLogger(structured_format=True)

        # Mock the file writing
        with patch('builtins.open', mock_open()) as mock_file:
            logger._write_structured_log({
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'operation': 'test_op',
                'duration': 1.5,
                'message': 'Test message'
            })

            mock_file.assert_called()

    def test_log_file_creation(self, mock_config):
        """Test log file creation and writing"""
        with patch('src.shared.logging.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            # Mock file operations
            with patch('builtins.open', mock_open()) as mock_file, \
                 patch('os.makedirs') as mock_makedirs:

                logger = PerformanceLogger()
                logger._ensure_log_directory()

                # Should create data directory if it doesn't exist
                mock_makedirs.assert_called()

    def test_emoji_logging_style(self):
        """Test emoji logging style"""
        logger = PerformanceLogger(emoji_style=True)

        # Test different operation types
        test_cases = [
            ("login", "🔐"),
            ("navigation", "🧭"),
            ("extraction", "📊"),
            ("file_operation", "📁"),
            ("api_call", "🌐"),
            ("default", "⏱️")
        ]

        for operation, expected_emoji in test_cases:
            emoji = logger._get_operation_emoji(operation)
            if operation == "default":
                # For unknown operations, should return default emoji
                emoji = logger._get_operation_emoji("unknown_operation")
            assert expected_emoji in emoji

    def test_performance_metrics_calculation(self):
        """Test performance metrics calculation"""
        logger = PerformanceLogger()

        # Add test data
        test_operations = [
            {'operation': 'op1', 'duration': 1.0},
            {'operation': 'op2', 'duration': 2.0},
            {'operation': 'op3', 'duration': 0.5}
        ]

        logger.completed_operations.extend(test_operations)

        metrics = logger._calculate_metrics()

        assert metrics['total_operations'] == 3
        assert metrics['total_duration'] == 3.5
        assert metrics['average_duration'] == pytest.approx(1.167, rel=1e-2)
        assert metrics['fastest']['duration'] == 0.5
        assert metrics['slowest']['duration'] == 2.0

    def test_heartbeat_logging(self, mock_logger):
        """Test heartbeat logging functionality"""
        with patch('src.shared.logging.get_logger') as mock_get_logger:
            mock_get_logger.return_value = mock_logger

            logger = PerformanceLogger()
            logger.log_heartbeat("Test process running")

            # Should have logged a heartbeat
            mock_logger.info.assert_called()

    def test_checkpoint_logging(self, mock_logger):
        """Test checkpoint logging functionality"""
        with patch('src.shared.logging.get_logger') as mock_get_logger:
            mock_get_logger.return_value = mock_logger

            logger = PerformanceLogger()
            logger.log_checkpoint("Reached important step")

            # Should have logged a checkpoint
            mock_logger.info.assert_called()

    def test_error_logging_with_context(self, mock_logger):
        """Test error logging with context information"""
        with patch('src.shared.logging.get_logger') as mock_get_logger:
            mock_get_logger.return_value = mock_logger

            logger = PerformanceLogger()

            try:
                raise ValueError("Test error")
            except Exception as e:
                logger.log_error("Operation failed", e, {"context": "test"})

            mock_logger.error.assert_called()

    def test_progress_logging(self, mock_logger):
        """Test progress logging functionality"""
        with patch('src.shared.logging.get_logger') as mock_get_logger:
            mock_get_logger.return_value = mock_logger

            logger = PerformanceLogger()
            logger.log_progress("Processing", 50, 100)

            mock_logger.info.assert_called()

    def test_batch_operation_logging(self):
        """Test batch operation logging"""
        logger = PerformanceLogger()

        operations = ["op1", "op2", "op3"]

        with logger.batch_timer("batch_operation", operations):
            for op in operations:
                with logger.timer(f"sub_{op}"):
                    pass  # Simulate work

        # Should have logged batch and sub-operations
        batch_ops = [op for op in logger.completed_operations if 'batch' in op['operation']]
        sub_ops = [op for op in logger.completed_operations if 'sub_' in op['operation']]

        assert len(batch_ops) >= 1
        assert len(sub_ops) == 3

    def test_log_filtering_by_level(self, mock_config):
        """Test log filtering by level"""
        config_with_debug = mock_config.copy()
        config_with_debug['logging']['level'] = 'debug'

        with patch('src.shared.logging.load_config') as mock_load_config:
            mock_load_config.return_value = config_with_debug

            logger = PerformanceLogger()

            # Debug level should allow all messages
            assert logger._should_log('debug')
            assert logger._should_log('info')
            assert logger._should_log('warning')
            assert logger._should_log('error')

        config_with_error = mock_config.copy()
        config_with_error['logging']['level'] = 'error'

        with patch('src.shared.logging.load_config') as mock_load_config:
            mock_load_config.return_value = config_with_error

            logger = PerformanceLogger()

            # Error level should only allow error messages
            assert not logger._should_log('debug')
            assert not logger._should_log('info')
            assert not logger._should_log('warning')
            assert logger._should_log('error')