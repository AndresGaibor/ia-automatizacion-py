# Wrapper delgado - código real en src/core/config/config_validator.py
from src.core.config.config_validator import *

# Re-exportar función pública
from src.core.config.config_validator import check_config_or_show_dialog

__all__ = ['check_config_or_show_dialog']
