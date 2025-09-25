"""
Unit tests for ConfigManager
"""
import pytest
import tempfile
import os
import yaml
from unittest.mock import patch, mock_open

from src.core.config.config_manager import ConfigManager
from src.core.errors.exceptions import ConfigurationError


@pytest.mark.unit
class TestConfigManager:
    """Unit tests for configuration management"""

    def test_load_valid_config(self, mock_config, temp_config_file):
        """Test loading valid configuration"""
        config_manager = ConfigManager(config_path=temp_config_file)
        loaded_config = config_manager.get_config()

        assert loaded_config['url'] == mock_config['url']
        assert loaded_config['user'] == mock_config['user']
        assert loaded_config['api']['api_key'] == mock_config['api']['api_key']

    def test_load_missing_config_file(self):
        """Test loading missing configuration file"""
        with pytest.raises(ConfigurationError, match="Configuration file not found"):
            ConfigManager(config_path="nonexistent.yaml")

    def test_load_invalid_yaml(self):
        """Test loading invalid YAML syntax"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            invalid_config_path = f.name

        try:
            with pytest.raises(ConfigurationError, match="Error parsing configuration file"):
                ConfigManager(config_path=invalid_config_path)
        finally:
            os.unlink(invalid_config_path)

    def test_validate_required_fields(self, mock_config, temp_config_file):
        """Test validation of required configuration fields"""
        # Remove required field
        incomplete_config = mock_config.copy()
        del incomplete_config['url']

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(incomplete_config, f)
            incomplete_config_path = f.name

        try:
            with pytest.raises(ConfigurationError, match="Missing required configuration"):
                ConfigManager(config_path=incomplete_config_path)
        finally:
            os.unlink(incomplete_config_path)

    def test_api_config_validation(self, mock_config):
        """Test API configuration validation"""
        config_manager = ConfigManager._validate_api_config

        # Valid API config
        valid_api_config = mock_config['api']
        assert config_manager(valid_api_config) == valid_api_config

        # Missing API key
        invalid_api_config = {'base_url': 'https://api.example.com'}
        with pytest.raises(ConfigurationError, match="API key is required"):
            config_manager(invalid_api_config)

    def test_logging_config_defaults(self, mock_config, temp_config_file):
        """Test logging configuration with defaults"""
        # Remove logging config to test defaults
        config_without_logging = mock_config.copy()
        del config_without_logging['logging']

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_without_logging, f)
            config_path = f.name

        try:
            config_manager = ConfigManager(config_path=config_path)
            config = config_manager.get_config()

            # Should have default logging config
            assert 'logging' in config
            assert config['logging']['enabled'] == True
            assert config['logging']['level'] == 'normal'
        finally:
            os.unlink(config_path)

    def test_config_update(self, mock_config, temp_config_file):
        """Test configuration updating"""
        config_manager = ConfigManager(config_path=temp_config_file)

        # Update config
        new_values = {'debug': True, 'headless': False}
        config_manager.update_config(new_values)

        updated_config = config_manager.get_config()
        assert updated_config['debug'] == True
        assert updated_config['headless'] == False

    def test_get_nested_value(self, mock_config, temp_config_file):
        """Test getting nested configuration values"""
        config_manager = ConfigManager(config_path=temp_config_file)

        # Test nested access
        api_key = config_manager.get_nested('api.api_key')
        assert api_key == mock_config['api']['api_key']

        logging_level = config_manager.get_nested('logging.level')
        assert logging_level == mock_config['logging']['level']

        # Test non-existent nested key
        with pytest.raises(KeyError):
            config_manager.get_nested('non.existent.key')

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="url: test")
    def test_config_file_permissions(self, mock_file, mock_exists):
        """Test configuration file permissions handling"""
        mock_exists.return_value = True
        mock_file.side_effect = PermissionError("Permission denied")

        with pytest.raises(ConfigurationError, match="Permission denied"):
            ConfigManager(config_path="config.yaml")

    def test_config_caching(self, temp_config_file):
        """Test that configuration is cached properly"""
        config_manager = ConfigManager(config_path=temp_config_file)

        # First access
        config1 = config_manager.get_config()

        # Second access should return cached version
        with patch.object(config_manager, '_load_config') as mock_load:
            config2 = config_manager.get_config()
            mock_load.assert_not_called()  # Should not reload from file
            assert config1 is config2  # Should be same object

    def test_config_reload(self, temp_config_file, mock_config):
        """Test configuration reloading"""
        config_manager = ConfigManager(config_path=temp_config_file)

        # Get initial config
        initial_config = config_manager.get_config()

        # Modify the file
        modified_config = mock_config.copy()
        modified_config['debug'] = True

        with open(temp_config_file, 'w') as f:
            yaml.dump(modified_config, f)

        # Force reload
        config_manager.reload()
        reloaded_config = config_manager.get_config()

        assert reloaded_config['debug'] == True
        assert initial_config is not reloaded_config  # Different objects