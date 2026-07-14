# Wrapper delgado - código real en src/core/commands/descargar_listas.py
from .core.commands.descargar_listas import *

# Re-exportar funciones públicas
from .core.commands.descargar_listas import procesar_listas_marcadas, listar_archivos_descargados

__all__ = ['procesar_listas_marcadas', 'listar_archivos_descargados']
