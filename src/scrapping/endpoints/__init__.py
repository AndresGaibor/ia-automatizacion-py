"""
Endpoints de scraping para extracción de datos de Acumbamail
"""
from .subscriber_details import SubscriberDetailsService
from .segments import SegmentsScrapingService

__all__ = [
    "SubscriberDetailsService",
    "SegmentsScrapingService"
]