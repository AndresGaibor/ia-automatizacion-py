"""
Endpoints de scraping para campañas, suscriptores y listas
"""

from .campanias import CampaignsScraper
from .suscriptores import SubscribersScraper
from .listas import ListsScraper

__all__ = [
    'CampaignsScraper',
    'SubscribersScraper',
    'ListsScraper'
]