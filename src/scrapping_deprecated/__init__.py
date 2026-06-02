"""
Módulo de scraping para Acumbamail
Proporciona funcionalidad híbrida combinando API y scraping
"""
from .endpoints import SubscriberDetailsService
from .models import (
    HardBounceSubscriber,
    NoOpenSubscriber,
    SoftBounceSubscriber,
    ScrapingResult,
    ScrapingSession
)

__all__ = [
    "SubscriberDetailsService",
    "HardBounceSubscriber",
    "NoOpenSubscriber",
    "SoftBounceSubscriber",
    "ScrapingResult",
    "ScrapingSession"
]