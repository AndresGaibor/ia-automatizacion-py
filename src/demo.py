# Wrapper delgado - código real en src/core/commands/demo.py
from .core.commands.demo import *

# Re-exportar función principal
from .core.commands.demo import main

__all__ = ['main']
