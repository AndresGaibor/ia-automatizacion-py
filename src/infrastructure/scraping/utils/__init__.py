"""
Utilidades para scraping
"""

from .selectors import CampaignSelectors, CommonSelectors, ReportPageSelectors, SessionSelectors
from .navigation import NavigationHelper

__all__ = ["CampaignSelectors", "CommonSelectors", "ReportPageSelectors", "SessionSelectors", "NavigationHelper"]
