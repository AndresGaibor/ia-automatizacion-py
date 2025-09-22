from typing import List, Optional, Union, Dict, Any, overload, Literal
from ..client import APIClient
from ..models.campanias import Campaign, CampaignLink, CampaignSummary, CampaignBasicInfo, CampaignDetailedInfo, CampaignComplete, CampaignOpener, CampaignClicker, CampaignSoftBounce, CampaignStatsByDate
from ..decorators import disabled_endpoint, medium_rate_limit, low_rate_limit
from ..validators import DateValidator, CampaignValidator

class CampaignsAPI:
	"""Endpoints relacionado con las campañas"""

	def __init__(self, client: APIClient):
		self.client = client

	# Tipado especializado por parámetro
	@overload
	def get_all(self, complete_info: Literal[True]) -> List[CampaignComplete]:
		...

	@overload
	def get_all(self, complete_info: Literal[False] = False) -> List[CampaignSummary]:
		...

	@medium_rate_limit
	def get_all(self, complete_info: bool = False) -> Union[List[CampaignSummary], List[CampaignComplete]]:
		"""
		Obtener todas las campañas
		
		Args:
			complete_info: Si True, obtiene información completa (lento pero evita rate limiting)
						  Si False, obtiene solo resumen básico (rápido)
		
		Returns:
			List[CampaignSummary] si complete_info=False
			List[CampaignComplete] si complete_info=True
		"""
		if complete_info:
			# Usar complete_json=1 para obtener información detallada de todas las campañas
			params = {"complete_json": "1"}
			response = self.client.get("getCampaigns/", params=params)
			
			# La respuesta con complete_json=1 devuelve datos detallados
			if isinstance(response, list):
				return CampaignComplete.from_api_response(response)
			return []
		else:
			# Comportamiento original: solo resumen básico
			params = {}
			response = self.client.get("getCampaigns/", params=params)
			
			# Convertir respuesta usando el método del modelo
			if isinstance(response, list):
				return CampaignSummary.from_api_response(response)
			return []
	
	@medium_rate_limit
	def get_basic_info(self, campaign_id: int) -> CampaignBasicInfo:
		"""Obtener información básica de una campaña específica"""
		params = {"campaign_id": campaign_id}
		response = self.client.get("getCampaignBasicInformation/", params=params)
		return CampaignBasicInfo.from_api_response(response)
	
	@medium_rate_limit
	def get_total_info(self, campaign_id: int) -> CampaignDetailedInfo:
		"""Obtener información completa de una campaña específica"""
		params = {"campaign_id": campaign_id}
		response = self.client.get("getCampaignTotalInformation/", params=params)
		return CampaignDetailedInfo.from_api_response(response)
	
	@medium_rate_limit
	def get_openers(self, campaign_id: int) -> List[CampaignOpener]:
		"""Obtener lista de suscriptores que abrieron la campaña"""
		params = {"campaign_id": campaign_id}
		response = self.client.get("getCampaignOpeners/", params=params)
		if isinstance(response, list):
			return CampaignOpener.from_api_response(response)
		return []

	@medium_rate_limit
	def get_clicks(self, campaign_id: int) -> List[CampaignClicker]:
		"""Obtener lista de suscriptores que hicieron clic en la campaña"""
		params = {"campaign_id": campaign_id}
		response = self.client.get("getCampaignClicks/", params=params)
		if isinstance(response, list):
			return CampaignClicker.from_api_response(response)
		return []

	@medium_rate_limit
	def get_links(self, campaign_id: int) -> List[CampaignLink]:
		"""Obtener lista de enlaces en la campaña y sus estadísticas"""
		params = {"campaign_id": campaign_id}
		response = self.client.get("getCampaignLinks/", params=params)
		if isinstance(response, list):
			return CampaignLink.from_api_response(response)
		return []

	@medium_rate_limit
	def get_soft_bounces(self, campaign_id: int) -> List[CampaignSoftBounce]:
		"""Obtener lista de soft bounces para una campaña específica"""
		params = {"campaign_id": campaign_id}
		response = self.client.get("getCampaignSoftBounces/", params=params)
		if isinstance(response, list):
			return CampaignSoftBounce.from_api_response(response)
		return []

	@medium_rate_limit
	def get_stats_by_date(self, list_id: int, start_date: str, end_date: str) -> CampaignStatsByDate:
		"""
		Obtener estadísticas de las campañas enviadas en una lista en un rango de fechas
		
		Args:
			list_id: ID de la lista
			start_date: Fecha de inicio (YYYY-MM-DD)
			end_date: Fecha de fin (YYYY-MM-DD)
		
		Returns:
			CampaignStatsByDate con estadísticas del período
			
		Raises:
			ValueError: Si las fechas no tienen el formato correcto o el campaign_id es inválido
		"""
		# Validar parámetros usando validadores externos
		DateValidator.validate_date_range(start_date, end_date)
		
		params = {
			"campaign_id": list_id,
			"start_date": start_date,
			"end_date": end_date
		}
		response = self.client.get("getCampaignStatsByDate/", params=params)
		
		if isinstance(response, dict):
			return CampaignStatsByDate.from_api_response(response)
		
		# Si no hay datos, retornar estadísticas en cero
		return CampaignStatsByDate(
			unopened=0,
			opened=0,
			hard_bounces=0,
			complaints=0,
			total_sent=0,
			total_clicks=0,
			soft_bounces=0,
			unique_clicks=0
		)