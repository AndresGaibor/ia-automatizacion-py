import httpx
from typing import Optional, Dict, Any
import logging

# Usar el logger estructurado del proyecto
try:
	from ...shared.logging.logger import get_logger
	logger = get_logger()
except ImportError:
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
		logger.info("🔧 APIClient inicializado", base_url=base_url, has_token=bool(auth_token))
	
	@property
	def client(self) -> httpx.Client:
		"""Cliente singleton para reutilizar conexiones"""
		if self._client is None:
			logger.debug("🔌 Creando cliente HTTP singleton")
			# Configurar timeouts para evitar cuelgues
			timeout = httpx.Timeout(
				connect=10.0,  # 10s para conectar
				read=30.0,     # 30s para leer respuesta
				write=10.0,    # 10s para escribir
				pool=60.0      # 60s total para el pool
			)
			logger.debug("⏱️ Configurando timeouts HTTP",
			           connect=10.0, read=30.0, write=10.0, pool=60.0)

			self._client = httpx.Client(
				base_url=self.base_url,
				timeout=timeout,
				# Límites de conexión para evitar problemas de pool
				limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
				verify=False  # Deshabilitar verificación SSL para entornos corporativos con proxies
			)
			logger.success("✅ Cliente HTTP creado exitosamente",
			             max_keepalive=5, max_connections=10)
		return self._client
	
	def _make_request(
		self,
		method: str,
		endpoint: str,
		**kwargs
	) -> httpx.Response:
		"""Metodo interno para hacer peticiones HTTP"""
		logger.debug(f"🌐 Preparando request {method}", endpoint=endpoint)

		# Validar configuración de API
		if not self.base_url or not self.auth_token:
			logger.error("❌ Configuración de API incompleta",
			           has_base_url=bool(self.base_url),
			           has_auth_token=bool(self.auth_token))
			raise Exception("Configuración de API incompleta. Verifique 'api.base_url' y 'api.api_key' en config.yaml")

		# Construir la URL completa manteniendo la estructura de la API
		url = f"{self.base_url}{endpoint.lstrip('/')}"
		logger.debug(f"🔗 URL construida: {url}")

		# Para métodos POST, añadir auth_token a los datos del formulario
		if method.upper() == "POST":
			if 'data' not in kwargs:
				kwargs['data'] = {}
			if self.auth_token:
				kwargs['data']['auth_token'] = self.auth_token
			logger.debug("📤 Request POST preparado", data_keys=list(kwargs.get('data', {}).keys()))
		else:
			# Para GET, agregar auth_token a los parámetros si está disponible
			if 'params' not in kwargs:
				kwargs['params'] = {}
			if kwargs['params'] is None:
				kwargs['params'] = {}
			if self.auth_token:
				kwargs['params']['auth_token'] = self.auth_token

			# Filtrar auth_token de los logs por seguridad
			safe_params = {k: v for k, v in kwargs.get('params', {}).items() if k != 'auth_token'}
			logger.debug("📥 Request GET preparado", params=safe_params)

		try:
			logger.debug(f"⏳ Ejecutando request {method} a {endpoint}...")
			response = self.client.request(method, url, **kwargs)
			logger.debug(f"📊 Response recibido", status_code=response.status_code)

			response.raise_for_status()
			logger.success(f"✅ Request exitoso: {method} {endpoint}", status=response.status_code)
			return response

		except httpx.TimeoutException as e:
			logger.error(f"⏱️ Request timeout", endpoint=endpoint, error=str(e))
			raise Exception(f"Request timed out: {str(e)}")
		except httpx.ConnectError as e:
			logger.error(f"🔌 Connection error", endpoint=endpoint, error=str(e))
			raise Exception(f"Connection failed: {str(e)}")
		except httpx.HTTPStatusError as e:
			logger.error(f"❌ HTTP error",
			           endpoint=endpoint,
			           status_code=e.response.status_code,
			           response_text=e.response.text[:200])  # Primeros 200 chars
			raise
		except Exception as e:
			logger.error(f"❌ Request error inesperado", endpoint=endpoint, error=str(e))
			raise

	def get(
		self,
		endpoint: str,
		params: Optional[Dict] = None,
	) -> Dict[str, Any]:
		"""GET request"""
		logger.debug("📥 Ejecutando GET request", endpoint=endpoint)
		if params is None:
			params = {}

		response = self._make_request("GET", endpoint, params=params)

		try:
			json_data = response.json()
			logger.debug("✅ Respuesta JSON parseada exitosamente",
			           data_type=type(json_data).__name__)
			return json_data
		except ValueError as e:
			logger.error("❌ Error parseando JSON response", error=str(e))
			raise
	
	def post(
		self,
		endpoint: str,
		data: Optional[Dict] = None
	) -> Any:
		"""POST request with form data"""
		logger.debug("📤 Ejecutando POST request", endpoint=endpoint)

		# Enviar como form data en lugar de JSON para la API de Acumbamail
		response = self._make_request("POST", endpoint, data=data)

		# Intentar parsear como JSON, pero también manejar respuestas de texto plano
		try:
			json_data = response.json()
			logger.debug("✅ Respuesta JSON parseada exitosamente",
			           data_type=type(json_data).__name__)
			return json_data
		except ValueError:
			# Algunas respuestas de la API pueden ser enteros o strings simples
			logger.debug("⚠️ Respuesta no es JSON, retornando texto plano")
			return response.text
	
	def close(self):
		"""Cerrar el cliente HTTP"""
		if self._client:
			logger.debug("🔌 Cerrando cliente HTTP")
			self._client.close()
			self._client = None
			logger.success("✅ Cliente HTTP cerrado exitosamente")
	
	def __enter__(self):
		return self
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		self.close()