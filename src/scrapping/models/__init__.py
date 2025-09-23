"""
Modelos para datos de scraping
"""
from .subscriber import (
    SubscriberDetailBase,
    HardBounceSubscriber,
    SoftBounceSubscriber,
    NoOpenSubscriber,
    ScrapingResult,
    ScrapingPaginationInfo,
    FilterInfo,
    ScrapingError,
    ScrapingErrorRecord,
    ScrapingSession,
    SubscriberQuality,
    SubscriberStatus
)

__all__ = [
    "SubscriberDetailBase",
    "HardBounceSubscriber",
    "SoftBounceSubscriber",
    "NoOpenSubscriber",
    "ScrapingResult",
    "ScrapingPaginationInfo",
    "FilterInfo",
    "ScrapingError",
    "ScrapingErrorRecord",
    "ScrapingSession",
    "SubscriberQuality",
    "SubscriberStatus"
]