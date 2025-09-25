"""Centralized configuration management with enhanced validation and loading."""
from typing import Dict, Any, Optional
import yaml
from pathlib import Path


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


class ConfigManager:
    """Centralized configuration management with enhanced validation and loading."""

    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def load(cls, config_path: Path, defaults: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Load configuration with intelligent defaults and validation."""
        if not config_path.exists():
            return cls._create_default_config(config_path, defaults or {})

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration from {config_path}: {e}")

        cls._validate_config(config)
        cls._config = config
        return config

    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Get the current loaded configuration."""
        if cls._config is None:
            # Try to load from legacy utils
            try:
                from ...shared.utils.legacy_utils import load_config
                cls._config = load_config()
            except ImportError:
                raise ConfigurationError("Configuration not loaded. Call load() first.")
        return cls._config

    @classmethod
    def _create_default_config(cls, config_path: Path, defaults: Dict[str, Any]) -> Dict[str, Any]:
        """Create a default configuration file."""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(defaults, f, default_flow_style=False)
        except Exception as e:
            raise ConfigurationError(f"Failed to create default configuration: {e}")
        return defaults

    @classmethod
    def _validate_config(cls, config: Dict[str, Any]):
        """Implement comprehensive configuration validation."""
        required_keys = [
            'url',
            'url_base',
            'user',
            'password'
        ]

        for key in required_keys:
            if not cls._get_nested_key(config, key):
                raise ConfigurationError(f"Missing required configuration key: {key}")

        # Validate URLs
        url = config.get('url', '')
        url_base = config.get('url_base', '')
        if not (url.startswith('http://') or url.startswith('https://')):
            raise ConfigurationError(f"Invalid URL format: {url}")
        if not (url_base.startswith('http://') or url_base.startswith('https://')):
            raise ConfigurationError(f"Invalid base URL format: {url_base}")

    @staticmethod
    def _get_nested_key(config: Dict[str, Any], key: str) -> Any:
        """Retrieve nested dictionary keys safely."""
        keys = key.split('.')
        value = config
        for k in keys:
            if not isinstance(value, dict) or k not in value:
                return None
            value = value[k]
        return value

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get a configuration value by key (supports nested keys with dots)."""
        if cls._config is None:
            raise ConfigurationError("Configuration not loaded. Call load() first.")

        value = cls._get_nested_key(cls._config, key)
        return value if value is not None else default

    @classmethod
    def update(cls, key: str, value: Any):
        """Update a configuration value."""
        if cls._config is None:
            raise ConfigurationError("Configuration not loaded. Call load() first.")

        keys = key.split('.')
        config = cls._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    @classmethod
    def save(cls, config_path: Path):
        """Save current configuration to file."""
        if cls._config is None:
            raise ConfigurationError("No configuration to save.")

        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(cls._config, f, default_flow_style=False)
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")