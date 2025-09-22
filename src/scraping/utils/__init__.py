"""
Utilidades para scraping
"""

from .selectors import CampaignSelectors, CommonSelectors
from .navigation import NavigationHelper

__all__ = [
    'CampaignSelectors',
    'CommonSelectors', 
    'NavigationHelper'
]