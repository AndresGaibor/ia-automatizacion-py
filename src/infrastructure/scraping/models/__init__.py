"""
Modelos específicos para datos obtenidos por scraping
"""

from .campanias import (
    ScrapedNonOpener,
    ScrapedHardBounce,
    ScrapedCampaignStats,
    ScrapedGeographicStats,
    ScrapedDeviceStats
)

from .suscriptores import (
    SubscriberScrapingData,
    SubscriberTableData,
    SubscriberFilterResult,
    CampaignSubscriberReport,
    PageNavigationInfo,
    ScrapingSession,
    SubscriberExtractionConfig
)

from .listas import (
    ListScrapingData,
    ListTableExtraction,
    ListSearchTerms,
    ListNavigationInfo,
    ListScrapingSession,
    ListScrapingResult,
    ListExtractionConfig,
    ListElementInfo
)

__all__ = [
    # Campañas
    'ScrapedNonOpener',
    'ScrapedHardBounce',
    'ScrapedCampaignStats',
    'ScrapedGeographicStats',
    'ScrapedDeviceStats',

    # Suscriptores
    'SubscriberScrapingData',
    'SubscriberTableData',
    'SubscriberFilterResult',
    'CampaignSubscriberReport',
    'PageNavigationInfo',
    'ScrapingSession',
    'SubscriberExtractionConfig',

    # Listas
    'ListScrapingData',
    'ListTableExtraction',
    'ListSearchTerms',
    'ListNavigationInfo',
    'ListScrapingSession',
    'ListScrapingResult',
    'ListExtractionConfig',
    'ListElementInfo'
]