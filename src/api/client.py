import httpx
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class APIClient:
	"""Cliente base para interactuar con una API RESTful."""

	def __init__(
		self,
		base_url: str,
		auth_token: Optional[str] = None
	):
		# No eliminamos la barra final para preservar el path de la API
		self.base_url = base_url
		self.auth_token = auth_token
		self._client = None
	
	@property
	def client(self) -> httpx.Client:
		"""Cliente singleton para reutilizar conexiones"""
		if self._client is None:
			# Configurar timeouts para evitar cuelgues
			timeout = httpx.Timeout(
				connect=10.0,  # 10s para conectar
				read=30.0,     # 30s para leer respuesta
				write=10.0,    # 10s para escribir
				pool=60.0      # 60s total para el pool
			)
			self._client = httpx.Client(
				base_url=self.base_url,
				timeout=timeout,
				# Límites de conexión para evitar problemas de pool
				limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
			)
		return self._client
	
	def _make_request(
		self,
		method: str,
		endpoint: str,
		**kwargs
	) -> httpx.Response:
		"""Metodo interno para hacer peticiones HTTP"""
		# Construir la URL completa manteniendo la estructura de la API
		url = f"{self.base_url}{endpoint.lstrip('/')}"

		# Para métodos POST, añadir auth_token a los datos del formulario
		if method.upper() == "POST":
			if 'data' not in kwargs:
				kwargs['data'] = {}
			if self.auth_token:
				kwargs['data']['auth_token'] = self.auth_token
		else:
			# Para GET, agregar auth_token a los parámetros si está disponible
			if 'params' not in kwargs:
				kwargs['params'] = {}
			if kwargs['params'] is None:
				kwargs['params'] = {}
			if self.auth_token:
				kwargs['params']['auth_token'] = self.auth_token

		# Debug: imprimir la URL completa
		logger.info(f"Making {method} request to: {url}")
		logger.info(f"With params: {kwargs.get('params', {})}")
		if method.upper() == "POST":
			logger.info(f"With data: {kwargs.get('data', {})}")

		try:
			response = self.client.request(method, url, **kwargs)
			response.raise_for_status()
			return response
		except httpx.TimeoutException as e:
			logger.error(f"Request timeout occurred: {str(e)}")
			raise Exception(f"Request timed out: {str(e)}")
		except httpx.ConnectError as e:
			logger.error(f"Connection error occurred: {str(e)}")
			raise Exception(f"Connection failed: {str(e)}")
		except httpx.HTTPStatusError as e:
			logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
			raise
		except Exception as e:
			logger.error(f"Request error occurred: {str(e)}")
			raise

	def get(
		self,
		endpoint: str,
		params: Optional[Dict] = None,
	) -> Dict[str, Any]:
		"""GET request"""
		if params is None:
			params = {}
		response = self._make_request("GET", endpoint, params=params)
		return response.json()
	
	def post(
		self,
		endpoint: str,
		data: Optional[Dict] = None
	) -> Any:
		"""POST request with form data"""
		# Enviar como form data en lugar de JSON para la API de Acumbamail
		response = self._make_request("POST", endpoint, data=data)

		# Intentar parsear como JSON, pero también manejar respuestas de texto plano
		try:
			return response.json()
		except ValueError:
			# Algunas respuestas de la API pueden ser enteros o strings simples
			return response.text
	
	def close(self):
		"""Cerrar el cliente HTTP"""
		if self._client:
			self._client.close()
			self._client = None
	
	def __enter__(self):
		return self
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		self.close()