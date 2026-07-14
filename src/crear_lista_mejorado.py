# Wrapper delgado - código real en src/core/commands/crear_lista_mejorado.py
from .core.commands.crear_lista_mejorado import *

# Re-exportar funciones públicas
from .core.commands.crear_lista_mejorado import extraer_id_desde_nombre_archivo, crear_lista_automatica, main_automatico, main_lote

__all__ = ['extraer_id_desde_nombre_archivo', 'crear_lista_automatica', 'main_automatico', 'main_lote']
