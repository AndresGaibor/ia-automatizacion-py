"""
Endpoints de scraping para campañas, suscriptores y listas
"""

from .campanias import ScraperCampanias
from .suscriptores import ScraperSuscriptores
from .listas import ScraperListas

__all__ = [
    'ScraperCampanias',
    'ScraperSuscriptores',
    'ScraperListas'
]