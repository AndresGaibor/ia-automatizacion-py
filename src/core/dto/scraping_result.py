from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .campaign_summary import CampaignSummary


@dataclass
class ScrapingResult:
    """Container for scraping output.

    Replaces ``list[list[str]]`` with typed data and metadata.
    """

    campaigns: list[CampaignSummary] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    scraped_at: Optional[str] = None
    total_pages: int = 0

    def __post_init__(self):
        if self.scraped_at is None:
            self.scraped_at = datetime.now().isoformat()

    @property
    def total_campaigns(self) -> int:
        return len(self.campaigns)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def add_campaign(self, campaign: CampaignSummary) -> None:
        self.campaigns.append(campaign)

    def to_excel_rows(self) -> list[list[str]]:
        """Convert all campaigns to Excel row lists."""
        return [c.to_excel_row() for c in self.campaigns]
