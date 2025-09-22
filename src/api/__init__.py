from .client import APIClient
from .endpoints.campanias import CampaignsAPI
from .endpoints.suscriptores import SuscriptoresAPI
from src.config.settings import settings

class API:
	"""Clase principal para agrupar todos los endpoints"""
	
	def __init__(self):
		base_url = settings.api_base_url
		api_key = settings.api_key
		
		self.client = APIClient(
			base_url=base_url,
			auth_token=api_key
		)

		# Inicializar endpoints
		self.campaigns = CampaignsAPI(self.client)
		self.suscriptores = SuscriptoresAPI(self.client)
	
	def close(self):
		"""Cerrar el cliente HTTP"""
		self.client.close()

	def __enter__(self):
		return self
	
	def __exit__(self, *args):
		self.close()