import os
from typing import Optional, Any, Dict

try:
	# Cargar utilidades para leer config.yaml
	from ..utils import load_config
except Exception:
	# Fallback relativo cuando el import anterior no está disponible aún
	import yaml
	import sys
	def load_config(defaults: Dict[str, Any] | None = None) -> Dict[str, Any]:
		project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
		path = os.path.join(project_root, "config.yaml")
		if os.path.exists(path):
			with open(path, "r") as f:
				return yaml.safe_load(f) or {}
		return defaults or {}


class Settings:
	"""Configuración centralizada de la aplicación

	URLs hardcodeadas para evitar errores de configuración del usuario.
	Solo requiere configurar credenciales (usuario, password, api_key).
	"""

	def __init__(self):
		# URLs hardcodeadas - el usuario no necesita configurarlas
		self.url_base: str = "https://acumbamail.com"
		self.url: str = "https://acumbamail.com/app/newsletter/"
		self.api_base_url: str = "https://acumbamail.com/api/1/"

		# Cargar configuración del usuario solo para credenciales
		cfg = load_config({})

		# Credenciales del usuario (requeridas)
		self.user: Optional[str] = cfg.get("user")
		self.password: Optional[str] = cfg.get("password")
		self.api_key: Optional[str] = cfg.get("api", {}).get("api_key") if cfg.get("api") else None

		# Configuraciones opcionales con defaults
		self.headless: bool = cfg.get("headless", False)
		self.debug: bool = cfg.get("debug", False)

	def validate(self) -> None:
		"""Valida que las credenciales estén configuradas"""
		if not self.user or not self.password:
			raise ValueError("Credenciales no configuradas. Configure 'user' y 'password' en config.yaml")
		if not self.api_key:
			raise ValueError("API key no configurada. Configure 'api.api_key' en config.yaml")

	def is_configured(self) -> bool:
		"""Verifica si la configuración está completa"""
		return bool(self.user and self.password and self.api_key)


settings = Settings()