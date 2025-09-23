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

	Prioridad de carga:
	1) Variables de entorno (API_BASE_URL, API_KEY)
	2) config.yaml -> sección `api: { base_url, api_key }`
	3) Valores por defecto seguros
	"""

	def __init__(self):
		# Defaults que coinciden con la estructura del config.yaml
		defaults = {
			"api": {
				"base_url": "https://acumbamail.com/api/1/",
				"api_key": None,
			}
		}

		cfg = load_config(defaults)
		api_cfg = cfg.get("api", {}) if isinstance(cfg, dict) else {}

		# Cargar primero desde config.yaml
		base_url_cfg = api_cfg.get("base_url") or defaults["api"]["base_url"]
		api_key_cfg = api_cfg.get("api_key")

		# Overrides por entorno si existen (mantener compatibilidad)
		self.api_base_url: str = os.getenv("API_BASE_URL", base_url_cfg)
		self.api_key: Optional[str] = os.getenv("API_KEY", api_key_cfg)

	def validate(self) -> None:
		if not self.api_base_url:
			raise ValueError("api_base_url no configurado. Define api.base_url en config.yaml o API_BASE_URL en entorno.")


settings = Settings()