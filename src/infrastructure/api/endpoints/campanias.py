from typing import List, Union, overload, Literal, Optional
from ..client import APIClient
from ..models.campanias import (
    CampaignLink,
    CampaignSummary,
    CampaignBasicInfo,
    CampaignDetailedInfo,
    CampaignComplete,
    CampaignOpener,
    CampaignClicker,
    CampaignSoftBounce,
    CampaignStatsByDate,
)
from ..decorators import medium_rate_limit
from ..validators import DateValidator

try:
    from ...shared.logging import get_logger
except ImportError:
    try:
        from src.shared.logging import get_logger
    except ImportError:
        try:
            from src.logger import get_logger
        except ImportError:
            # Fallback minimal logger
            import logging

            def get_logger():
                return logging.getLogger(__name__)


logger = get_logger()


class CampaignsAPI:
    """Endpoints relacionado con las campañas"""

    def __init__(self, client: APIClient):
        self.client = client

    # Tipado especializado por parámetro
    @overload
    def get_all(self, complete_info: Literal[True]) -> List[CampaignComplete]: ...

    @overload
    def get_all(self, complete_info: Literal[False] = False) -> List[CampaignSummary]: ...

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
        logger.info("🌐 Iniciando obtención de campañas", complete_info=complete_info)

        if complete_info:
            # Usar complete_json=1 para obtener información detallada de todas las campañas
            logger.info(" Detaylı Obteniendo información completa de campañas")
            params = {"complete_json": "1"}
            response = self.client.get("getCampaigns/", params=params)

            # La respuesta con complete_json=1 devuelve datos detallados
            if isinstance(response, list):
                logger.info("📊 Procesando respuesta con información detallada", total_registros=len(response))
                result = CampaignComplete.from_api_response(response)
                logger.success("✅ Campañas con información completa obtenidas exitosamente", total=len(result))
                return result
            logger.warning("⚠️ No se recibieron datos al solicitar información completa")
            return []
        else:
            # Comportamiento original: solo resumen básico
            logger.info("📋 Obteniendo resumen básico de campañas")
            params = {}
            response = self.client.get("getCampaigns/", params=params)

            # Convertir respuesta usando el método del modelo
            if isinstance(response, list):
                logger.info("📊 Procesando respuesta con resumen básico", total_registros=len(response))
                result = CampaignSummary.from_api_response(response)
                logger.success("✅ Campañas con resumen básico obtenidas exitosamente", total=len(result))
                return result
            logger.warning("⚠️ No se recibieron datos al solicitar resumen básico")
            return []

    @medium_rate_limit
    def get_basic_info(self, campaign_id: int) -> CampaignBasicInfo:
        logger.info("📋 Obteniendo información básica de campaña", campaign_id=campaign_id)
        params = {"campaign_id": campaign_id}
        response = self.client.get("getCampaignBasicInformation/", params=params)
        result = CampaignBasicInfo.from_api_response(response, campaign_id=campaign_id)
        logger.success("✅ Información básica obtenida exitosamente", campaign_id=campaign_id)
        return result

    @medium_rate_limit
    def get_total_info(self, campaign_id: int, campaign_name: Optional[str] = None) -> CampaignDetailedInfo:
        logger.info("📊 Obtener información completa de campaña", campaign_id=campaign_id)
        params = {"campaign_id": campaign_id}
        response = self.client.get("getCampaignTotalInformation/", params=params)

        if campaign_name is None:
            basic_info = self.get_basic_info(campaign_id)
            campaign_name = basic_info.name

        result = CampaignDetailedInfo.from_api_response(response, campaign_id=campaign_id, campaign_name=campaign_name)
        logger.success("✅ Información completa obtenida exitosamente", campaign_id=campaign_id)
        return result

    @medium_rate_limit
    def get_openers(self, campaign_id: int) -> List[CampaignOpener]:
        """Obtener lista de suscriptores que abrieron la campaña"""
        logger.info("👀 Obteniendo lista de abridores", campaign_id=campaign_id)
        params = {"campaign_id": campaign_id}
        response = self.client.get("getCampaignOpeners/", params=params)
        if isinstance(response, list):
            result = CampaignOpener.from_api_response(response)
            logger.success("✅ Abridores obtenidos exitosamente", campaign_id=campaign_id, total=len(result))
            return result
        logger.warning("⚠️ No se recibieron datos de abridores", campaign_id=campaign_id)
        return []

    @medium_rate_limit
    def get_clicks(self, campaign_id: int) -> List[CampaignClicker]:
        """Obtener lista de suscriptores que hicieron clic en la campaña"""
        logger.info("🖱️ Obteniendo lista de clics", campaign_id=campaign_id)
        params = {"campaign_id": campaign_id}
        response = self.client.get("getCampaignClicks/", params=params)
        if isinstance(response, list):
            result = CampaignClicker.from_api_response(response)
            logger.success("✅ Clics obtenidos exitosamente", campaign_id=campaign_id, total=len(result))
            return result
        logger.warning("⚠️ No se recibieron datos de clics", campaign_id=campaign_id)
        return []

    @medium_rate_limit
    def get_links(self, campaign_id: int) -> List[CampaignLink]:
        """Obtener lista de enlaces en la campaña y sus estadísticas"""
        logger.info("🔗 Obteniendo lista de enlaces", campaign_id=campaign_id)
        params = {"campaign_id": campaign_id}
        response = self.client.get("getCampaignLinks/", params=params)
        if isinstance(response, list):
            result = CampaignLink.from_api_response(response)
            logger.success("✅ Enlaces obtenidos exitosamente", campaign_id=campaign_id, total=len(result))
            return result
        logger.warning("⚠️ No se recibieron datos de enlaces", campaign_id=campaign_id)
        return []

    @medium_rate_limit
    def get_soft_bounces(self, campaign_id: int) -> List[CampaignSoftBounce]:
        """Obtener lista de soft bounces para una campaña específica"""
        logger.info("📧 Obteniendo lista de soft bounces", campaign_id=campaign_id)
        params = {"campaign_id": campaign_id}
        response = self.client.get("getCampaignSoftBounces/", params=params)
        if isinstance(response, list):
            result = CampaignSoftBounce.from_api_response(response)
            logger.success("✅ Soft bounces obtenidos exitosamente", campaign_id=campaign_id, total=len(result))
            return result
        logger.warning("⚠️ No se recibieron datos de soft bounces", campaign_id=campaign_id)
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
                ValueError: Si las fechas no tienen el formato correcto o el list_id es inválido
        """
        logger.info("📊 Obteniendo estadísticas por fecha", list_id=list_id, start_date=start_date, end_date=end_date)
        DateValidator.validate_date_range(start_date, end_date)

        params = {"list_id": list_id, "date_from": start_date, "date_to": end_date}
        response = self.client.get("getStatsByDate/", params=params)

        if isinstance(response, dict):
            result = CampaignStatsByDate.from_api_response(response)
            logger.success(
                "✅ Estadísticas obtenidas exitosamente", list_id=list_id, start_date=start_date, end_date=end_date
            )
            return result

        result = CampaignStatsByDate(
            unopened=0,
            opened=0,
            hard_bounces=0,
            complaints=0,
            total_sent=0,
            total_clicks=0,
            soft_bounces=0,
            unique_clicks=0,
        )
        logger.warning("⚠️ No se recibieron estadísticas, retornando valores por defecto", list_id=list_id)
        return result
