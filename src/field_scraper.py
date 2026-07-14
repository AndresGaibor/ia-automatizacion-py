# Wrapper delgado - código real en src/infrastructure/scraping/utils/field_scraper.py
from .infrastructure.scraping.utils.field_scraper import *

# Re-exportar funciones públicas
from .infrastructure.scraping.utils.field_scraper import (
    obtener_campos_disponibles_acumba,
    filtrar_campos_necesarios
)

__all__ = ['obtener_campos_disponibles_acumba', 'filtrar_campos_necesarios']
