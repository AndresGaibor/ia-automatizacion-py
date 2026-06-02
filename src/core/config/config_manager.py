"""Gestión centralizada de configuración con validación mejorada."""

from typing import Dict, Any, Optional
import yaml
from pathlib import Path


class ErrorConfiguracion(Exception):
    """Lanzada cuando la configuración es inválida o falta."""
    pass


class GestorConfiguracion:
    """Gestión centralizada de configuración con validación mejorada."""

    _instancia = None
    _config = None

    def __new__(cls):
        if cls._instancia is None:
            cls._instancia = super().__new__(cls)
        return cls._instancia

    @classmethod
    def cargar(cls, ruta_config: Path, valores_por_defecto: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Carga configuración con valores por defecto inteligentes."""
        if not ruta_config.exists():
            return cls._crear_config_por_defecto(ruta_config, valores_por_defecto or {})

        try:
            with open(ruta_config, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
        except Exception as e:
            raise ErrorConfiguracion(f"Error cargando configuración desde {ruta_config}: {e}")

        cls._validar_config(config)
        cls._config = config
        return config

    @classmethod
    def obtener_config(cls) -> Dict[str, Any]:
        """Obtiene la configuración actualmente cargada."""
        if cls._config is None:
            try:
                from ...shared.utils.legacy_utils import load_config
                cls._config = load_config()
            except ImportError:
                raise ErrorConfiguracion("Configuración no cargada. Llamar cargar() primero.")
        return cls._config

    @classmethod
    def _crear_config_por_defecto(cls, ruta_config: Path, valores_por_defecto: Dict[str, Any]) -> Dict[str, Any]:
        """Crea archivo de configuración por defecto."""
        ruta_config.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(ruta_config, 'w', encoding='utf-8') as f:
                yaml.safe_dump(valores_por_defecto, f, default_flow_style=False)
        except Exception as e:
            raise ErrorConfiguracion(f"Error creando configuración por defecto: {e}")
        return valores_por_defecto

    @classmethod
    def _validar_config(cls, config: Dict[str, Any]):
        """Implementa validación exhaustiva de configuración."""
        claves_requeridas = ['url', 'url_base', 'user', 'password']

        for clave in claves_requeridas:
            if not cls._obtener_clave_anidada(config, clave):
                raise ErrorConfiguracion(f"Falta clave de configuración requerida: {clave}")

        url = config.get('url', '')
        url_base = config.get('url_base', '')
        if not (url.startswith('http://') or url.startswith('https://')):
            raise ErrorConfiguracion(f"Formato URL inválido: {url}")
        if not (url_base.startswith('http://') or url_base.startswith('https://')):
            raise ErrorConfiguracion(f"Formato URL base inválido: {url_base}")

    @staticmethod
    def _obtener_clave_anidada(config: Dict[str, Any], clave: str) -> Any:
        """Recupera claves de diccionarios anidados de forma segura."""
        partes = clave.split('.')
        valor = config
        for k in partes:
            if not isinstance(valor, dict) or k not in valor:
                return None
            valor = valor[k]
        return valor

    @classmethod
    def obtener(cls, clave: str, valor_por_defecto: Any = None) -> Any:
        """Obtiene un valor de configuración por clave (soporta claves anidadas con puntos)."""
        if cls._config is None:
            raise ErrorConfiguracion("Configuración no cargada. Llamar cargar() primero.")

        valor = cls._obtener_clave_anidada(cls._config, clave)
        return valor if valor is not None else valor_por_defecto

    @classmethod
    def actualizar(cls, clave: str, valor: Any):
        """Actualiza un valor de configuración."""
        if cls._config is None:
            raise ErrorConfiguracion("Configuración no cargada. Llamar cargar() primero.")

        partes = clave.split('.')
        config = cls._config

        for k in partes[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[partes[-1]] = valor

    @classmethod
    def guardar(cls, ruta_config: Path):
        """Guarda la configuración actual en archivo."""
        if cls._config is None:
            raise ErrorConfiguracion("No hay configuración para guardar.")

        try:
            with open(ruta_config, 'w', encoding='utf-8') as f:
                yaml.safe_dump(cls._config, f, default_flow_style=False)
        except Exception as e:
            raise ErrorConfiguracion(f"Error guardando configuración: {e}")
ConfigManager = GestorConfiguracion
