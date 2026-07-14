# Wrapper delgado - código real en src/presentation/gui/config_window.py
from src.presentation.gui.config_window import *

# Re-exportar clase pública
from src.presentation.gui.config_window import ConfigWindow, show_config_window

__all__ = ['ConfigWindow', 'show_config_window']
