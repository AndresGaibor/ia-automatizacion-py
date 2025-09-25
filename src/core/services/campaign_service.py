"""Service for handling campaign operations and data extraction."""
from typing import List, Dict, Any, Tuple
from datetime import datetime
import re

try:
    from ...shared.utils import data_path, cargar_campanias_a_buscar
    from ...shared.logging import get_logger
    from ..errors import DataProcessingError, ValidationError
except ImportError:
    from src.shared.utils import data_path, cargar_campanias_a_buscar
    from src.shared.logging import get_logger
    from src.core.errors import DataProcessingError, ValidationError

logger = get_logger()


class CampaignService:
    """Service for handling campaign-related operations."""

    def __init__(self):
        self.search_file = data_path("Busqueda.xlsx")
        self.reports_prefix = data_path("informes")

    def load_campaigns_to_search(self) -> List[Tuple[int, str]]:
        """Load campaigns marked for search from Excel file."""
        try:
            campaigns = cargar_campanias_a_buscar(self.search_file)
            logger.info(f"Loaded {len(campaigns)} campaigns for processing")
            return campaigns
        except Exception as e:
            raise DataProcessingError(
                f"Failed to load campaigns from search file: {e}",
                file_path=str(self.search_file)
            ) from e

    def generate_report_filename(self, campaign_name: str = "", send_date: str = "") -> str:
        """Generate report filename based on campaign info."""
        now = datetime.now()
        extraction_date = now.strftime("%Y%m%d%H%M")

        if campaign_name and send_date:
            # Clean campaign name of problematic characters for filenames
            clean_name = re.sub(r'[<>:"/\\|?*]', '_', campaign_name)
            filename = f"{clean_name}-{send_date}_{extraction_date}.xlsx"
            # Ensure filename is in data/suscriptores directory
            return data_path(f"suscriptores/{filename}")
        else:
            # Fallback to previous format if parameters not provided
            filename = f"{self.reports_prefix}_{extraction_date}.xlsx"
            return data_path(filename.replace(f"{self.reports_prefix}_", ""))

    def validate_campaign_data(self, campaign_data: Dict[str, Any]) -> bool:
        """Validate campaign data structure."""
        required_fields = ['id', 'name', 'send_date']

        for field in required_fields:
            if field not in campaign_data or campaign_data[field] is None:
                raise ValidationError(
                    f"Missing required field '{field}' in campaign data",
                    field_name=field
                )

        return True

    def format_campaign_info(self, campaign_id: int, campaign_name: str) -> Dict[str, Any]:
        """Format campaign information for processing."""
        return {
            'id': campaign_id,
            'name': campaign_name.strip() if campaign_name else f"Campaign_{campaign_id}",
            'processed_at': datetime.now().isoformat()
        }

    def generate_lists_string(self, all_lists: List[str], list_ids: List[str]) -> str:
        """Generate formatted lists string from list data."""
        lists_array = []
        for list_id in list_ids:
            found_list = next((lst for lst in all_lists if lst['id'] == list_id), None)
            if found_list:
                lists_array.append(found_list['name'])

        return "; ".join(lists_array) if lists_array else "Sin listas asociadas"

    def process_campaign_metrics(self, raw_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Process and validate campaign metrics."""
        try:
            processed_metrics = {
                'emails_sent': int(raw_metrics.get('emails_sent', 0)),
                'opened': int(raw_metrics.get('opened', 0)),
                'clicked': int(raw_metrics.get('clicked', 0)),
                'hard_bounces': int(raw_metrics.get('hard_bounces', 0)),
                'soft_bounces': int(raw_metrics.get('soft_bounces', 0)),
                'unsubscribed': int(raw_metrics.get('unsubscribed', 0))
            }

            # Calculate rates
            emails_sent = processed_metrics['emails_sent']
            if emails_sent > 0:
                processed_metrics['open_rate'] = round((processed_metrics['opened'] / emails_sent) * 100, 2)
                processed_metrics['click_rate'] = round((processed_metrics['clicked'] / emails_sent) * 100, 2)
                processed_metrics['bounce_rate'] = round(
                    ((processed_metrics['hard_bounces'] + processed_metrics['soft_bounces']) / emails_sent) * 100, 2
                )
            else:
                processed_metrics['open_rate'] = 0.0
                processed_metrics['click_rate'] = 0.0
                processed_metrics['bounce_rate'] = 0.0

            return processed_metrics

        except (ValueError, TypeError) as e:
            raise DataProcessingError(
                f"Failed to process campaign metrics: {e}",
                context={"raw_metrics": raw_metrics}
            ) from e

    def categorize_subscriber_data(self, subscribers: List[Dict[str, Any]]) -> Dict[str, List[List[str]]]:
        """Categorize subscriber data by interaction type."""
        categories = {
            'opened': [],
            'not_opened': [],
            'clicked': [],
            'hard_bounces': [],
            'soft_bounces': []
        }

        for subscriber in subscribers:
            base_data = [
                subscriber.get('project', ''),
                subscriber.get('list_name', ''),
                subscriber.get('email', ''),
                subscriber.get('list_name', ''),  # Duplicate for compatibility
                subscriber.get('status', ''),
                subscriber.get('quality', '')
            ]

            # Categorize based on interaction
            if subscriber.get('opened'):
                opened_data = base_data.copy()
                opened_data.insert(3, subscriber.get('open_date', ''))
                opened_data.insert(4, subscriber.get('open_country', ''))
                opened_data.insert(5, str(subscriber.get('open_count', 1)))
                categories['opened'].append(opened_data)

            if subscriber.get('clicked'):
                clicked_data = base_data.copy()
                clicked_data.insert(3, subscriber.get('first_click_date', ''))
                clicked_data.insert(4, subscriber.get('click_country', ''))
                categories['clicked'].append(clicked_data)

            if subscriber.get('hard_bounce'):
                categories['hard_bounces'].append(base_data)

            if subscriber.get('soft_bounce'):
                categories['soft_bounces'].append(base_data)

            if not any([
                subscriber.get('opened'),
                subscriber.get('clicked'),
                subscriber.get('hard_bounce'),
                subscriber.get('soft_bounce')
            ]):
                categories['not_opened'].append(base_data)

        logger.info(f"Categorized subscribers: {len(categories['opened'])} opened, "
                   f"{len(categories['not_opened'])} not opened, {len(categories['clicked'])} clicked")

        return categories

    def validate_subscriber_export_data(self, export_data: Dict[str, Any]) -> bool:
        """Validate subscriber export data structure."""
        required_keys = ['general', 'detailed']

        for key in required_keys:
            if key not in export_data:
                raise ValidationError(
                    f"Missing required key '{key}' in export data",
                    field_name=key
                )

        # Validate detailed data structure
        detailed = export_data['detailed']
        expected_categories = ['opened', 'not_opened', 'clicked', 'hard_bounces', 'soft_bounces']

        for category in expected_categories:
            if category not in detailed:
                raise ValidationError(
                    f"Missing category '{category}' in detailed data",
                    field_name=category
                )

        return True

    def prepare_export_data(
        self,
        general_data: List[List[str]],
        categorized_subscribers: Dict[str, List[List[str]]]
    ) -> Dict[str, Any]:
        """Prepare data for Excel export."""
        export_data = {
            'general': general_data,
            'detailed': {
                'opened': categorized_subscribers.get('opened', []),
                'not_opened': categorized_subscribers.get('not_opened', []),
                'clicked': categorized_subscribers.get('clicked', []),
                'hard_bounces': categorized_subscribers.get('hard_bounces', []),
                'soft_bounces': categorized_subscribers.get('soft_bounces', [])
            }
        }

        self.validate_subscriber_export_data(export_data)
        return export_data