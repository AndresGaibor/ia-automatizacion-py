"""Configuration validation utilities for the GUI."""
import os
import pandas as pd
from typing import Tuple

from ...shared.utils import load_config, data_path
from ...shared.logging import get_logger
from ...core.errors import ValidationError, DataProcessingError

logger = get_logger()


class ConfigValidator:
    """Validates application configuration and data files."""

    @staticmethod
    def validate_configuration() -> Tuple[bool, str]:
        """Validates that the configuration is complete."""
        logger.info("🔍 Validating configuration")

        try:
            config = load_config()
        except Exception as e:
            logger.error(f"❌ Failed to load configuration: {e}")
            return False, f"Error loading configuration: {e}"

        # Validate basic credentials
        user = config.get("user")
        if not user or user == "usuario@correo.com":
            logger.warning("❌ Invalid configuration: User not configured", user=user)
            return False, "Error: User not configured. Edit config.yaml with your Acumbamail credentials."

        password = config.get("password")
        if not password or password == "clave":
            logger.warning("❌ Invalid configuration: Password not configured", user=user)
            return False, "Error: Password not configured. Edit config.yaml with your Acumbamail password."

        # Validate API key if needed
        api_config = config.get("api", {})
        if not api_config.get("api_key"):
            logger.warning("⚠️ API Key not configured", user=user)
            return False, "Warning: API Key not configured. Some functions may not work. Configure api.api_key in config.yaml."

        logger.success("✅ Configuration valid", user=user)
        return True, "Configuration valid"

    @staticmethod
    def validate_configuration_legacy() -> Tuple[bool, str]:
        """Legacy validation function for backwards compatibility with app.py."""
        logger.info("🔍 Validando configuración")
        config = load_config()

        # Validar credenciales básicas
        if not config.get("user") or config.get("user") == "usuario@correo.com":
            logger.warning("❌ Configuración inválida: Usuario no configurado", user=config.get("user"))
            return False, "Error: Usuario no configurado. Edite config.yaml con sus credenciales de Acumbamail."

        if not config.get("password") or config.get("password") == "clave":
            logger.warning("❌ Configuración inválida: Contraseña no configurada", user=config.get("user"))
            return False, "Error: Contraseña no configurada. Edite config.yaml con su contraseña de Acumbamail."

        # Validar API key si se necesita
        api_config = config.get("api", {})
        if not api_config.get("api_key"):
            logger.warning("⚠️ API Key no configurada", user=config.get("user"))
            return False, "Advertencia: API Key no configurada. Algunas funciones pueden no funcionar. Configure api.api_key en config.yaml."

        logger.success("✅ Configuración válida", user=config.get("user"))
        return True, "Configuración válida"

    @staticmethod
    def validate_search_file() -> Tuple[bool, str, int]:
        """Validates the search file and counts marked items."""
        archivo = data_path("Busqueda.xlsx")
        logger.info("🔍 Validating search file", archivo=archivo)

        if not os.path.exists(archivo):
            logger.error("❌ Search file not found", archivo=archivo)
            return False, "Error: Busqueda.xlsx file does not exist", 0

        try:
            logger.info("📊 Reading search file", archivo=archivo)
            df = pd.read_excel(archivo)

            if 'Buscar' not in df.columns:
                logger.error("❌ 'Buscar' column not found in file", archivo=archivo)
                return False, "Error: Busqueda.xlsx file does not have 'Buscar' column", 0

            marked_count = df[df['Buscar'].isin(['x', 'X'])].shape[0]
            if marked_count == 0:
                logger.warning("⚠️ No marked items in file", archivo=archivo)
                return False, "Warning: No items marked with 'x' in Busqueda.xlsx file", 0

            logger.success(
                f"✅ Search file valid: {marked_count} marked items",
                archivo=archivo,
                marked_items=marked_count
            )
            return True, f"{marked_count} items marked for processing", marked_count

        except Exception as e:
            logger.error(f"❌ Error reading search file: {e}", archivo=archivo, error=str(e))
            raise DataProcessingError(
                f"Error reading Busqueda.xlsx: {e}",
                file_path=archivo
            ) from e

    @staticmethod
    def validate_lists_search_file() -> Tuple[bool, str, int]:
        """Validates the lists search file and counts marked items."""
        archivo = data_path("Busqueda_Listas.xlsx")
        logger.info("🔍 Validating lists search file", archivo=archivo)

        if not os.path.exists(archivo):
            logger.error("❌ Lists search file not found", archivo=archivo)
            return False, "Error: Busqueda_Listas.xlsx file does not exist", 0

        try:
            logger.info("📊 Reading lists search file", archivo=archivo)
            df = pd.read_excel(archivo)

            if 'Buscar' not in df.columns:
                logger.error("❌ 'Buscar' column not found in lists file", archivo=archivo)
                return False, "Error: Busqueda_Listas.xlsx file does not have 'Buscar' column", 0

            marked_count = df[df['Buscar'].isin(['x', 'X'])].shape[0]
            if marked_count == 0:
                logger.warning("⚠️ No lists marked in file", archivo=archivo)
                return False, "Warning: No lists marked with 'x' in Busqueda_Listas.xlsx file", 0

            logger.success(
                f"✅ Lists search file valid: {marked_count} lists marked",
                archivo=archivo,
                marked_lists=marked_count
            )
            return True, f"{marked_count} lists marked for processing", marked_count

        except Exception as e:
            logger.error(f"❌ Error reading lists search file: {e}", archivo=archivo, error=str(e))
            raise DataProcessingError(
                f"Error reading Busqueda_Listas.xlsx: {e}",
                file_path=archivo
            ) from e

    @staticmethod
    def validate_segments_file() -> Tuple[bool, str, int]:
        """Validates the segments file."""
        archivo = data_path("Segmentos.xlsx")
        logger.info("🔍 Validating segments file", archivo=archivo)

        if not os.path.exists(archivo):
            logger.error("❌ Segments file not found", archivo=archivo)
            return False, "Error: Segmentos.xlsx file does not exist", 0

        try:
            logger.info("📊 Reading segments file", archivo=archivo)
            df = pd.read_excel(archivo)
            required_columns = ['NOMBRE LISTA', 'NOMBRE SEGMENTO']
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                logger.error(
                    "❌ Required columns missing in segments file",
                    archivo=archivo,
                    missing_columns=missing_columns
                )
                return False, f"Error: Missing columns in Segmentos.xlsx: {', '.join(missing_columns)}", 0

            row_count = len(df)
            if row_count == 0:
                logger.warning("⚠️ Segments file is empty", archivo=archivo)
                return False, "Warning: Segmentos.xlsx file is empty", 0

            logger.success(
                f"✅ Segments file valid: {row_count} segments defined",
                archivo=archivo,
                segment_count=row_count
            )
            return True, f"{row_count} segments defined for processing", row_count

        except Exception as e:
            logger.error(f"❌ Error reading segments file: {e}", archivo=archivo, error=str(e))
            raise DataProcessingError(
                f"Error reading Segmentos.xlsx: {e}",
                file_path=archivo
            ) from e