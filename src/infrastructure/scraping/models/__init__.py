"""
Modelos específicos para datos obtenidos por scraping
"""

from .campanias import (
    ScrapedNoAbridor,
    ScrapedReboteDuro,
    ScrapedEstadisticasCampania,
    ScrapedEstadisticasGeograficas,
    ScrapedEstadisticasDispositivo
)

from .suscriptores import (
    DatosScrapingSuscriptor,
    DatosTablaSuscriptor,
    ResultadoFiltroSuscriptor,
    InformeSubscriptorCampania,
    PageNavigationInfo,
    ScrapingSession,
    SubscriberExtractionConfig
)

from .listas import (
    DatosScrapingLista,
    ExtraccionTablaLista,
    TerminosBusquedaLista,
    InfoNavegacionLista,
    ListScrapingSession,
    ListScrapingResult,
    ListExtractionConfig,
    ListElementInfo
)

__all__ = [
    # Campañas
    'ScrapedNoAbridor',
    'ScrapedReboteDuro',
    'ScrapedEstadisticasCampania',
    'ScrapedEstadisticasGeograficas',
    'ScrapedEstadisticasDispositivo',

    # Suscriptores
    'DatosScrapingSuscriptor',
    'DatosTablaSuscriptor',
    'ResultadoFiltroSuscriptor',
    'InformeSubscriptorCampania',
    'PageNavigationInfo',
    'ScrapingSession',
    'SubscriberExtractionConfig',

    # Listas
    'DatosScrapingLista',
    'ExtraccionTablaLista',
    'TerminosBusquedaLista',
    'InfoNavegacionLista',
    'ListScrapingSession',
    'ListScrapingResult',
    'ListExtractionConfig',
    'ListElementInfo'
]