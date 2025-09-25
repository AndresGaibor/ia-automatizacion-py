from .client import APIClient
from .endpoints.campanias import CampaignsAPI
from .endpoints.suscriptores import SuscriptoresAPI

try:
    from src.config.settings import settings
except ImportError:
    # Create a mock settings object for testing
    class MockSettings:
        def __init__(self):
            self.api_base_url = 'https://acumbamail.com/api/1/'
            self.api_key = None
    settings = MockSettings()

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