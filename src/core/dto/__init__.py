# -*- coding: utf-8 -*-
"""Pure data transfer objects for scraping output.

NO Playwright, NO openpyxl, NO infrastructure imports.
These are the boundary between scraping extraction and export layers.
"""

from .campaign_summary import CampaignSummary
from .scraping_result import ScrapingResult

__all__ = [
    "CampaignSummary",
    "ScrapingResult",
]
