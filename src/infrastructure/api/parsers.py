"""Utilidades para convertir respuestas de API a modelos"""

from typing import List, Dict, TypeVar
from .models.campanias import CampaignSummary

T = TypeVar('T')

def parse_campaign_list(api_response: List[Dict[str, str]]) -> List[CampaignSummary]:
    """
    Convierte respuesta de getCampaigns a lista de CampaignSummary
    
    Args:
        api_response: Lista de dicts con formato {id: nombre}
        
    Returns:
        Lista de objetos CampaignSummary
    """
    return [
        CampaignSummary(
            id=int(campaign_id), 
            name=campaign_name
        )
        for item in api_response 
        if isinstance(item, dict)
        for campaign_id, campaign_name in item.items()
    ]

def parse_id_name_dict(item: Dict[str, str]) -> tuple[int, str]:
    """
    Extrae ID y nombre de un dict con formato {id: nombre}
    
    Args:
        item: Dict con un solo par clave-valor
        
    Returns:
        Tupla (id, nombre)
    """
    campaign_id, campaign_name = next(iter(item.items()))
    return int(campaign_id), campaign_name