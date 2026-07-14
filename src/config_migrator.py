# Wrapper delgado - código real en src/core/config/config_migrator.py
from src.core.config.config_migrator import *

# Re-exportar clases y funciones públicas
from src.core.config.config_migrator import ConfigMigrator, ensure_config_valid

__all__ = ['ConfigMigrator', 'ensure_config_valid']
