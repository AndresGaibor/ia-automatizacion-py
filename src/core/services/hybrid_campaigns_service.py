"""
API Híbrida de Campañas: Combina API oficial + scraping inteligentemente

Esta clase proporciona una interfaz unificada que:
- Usa la API oficial cuando los endpoints existen (rápido y eficiente)
- Usa scraping cuando los datos no están disponibles en API (no-openers, hard bounces)
- Combina ambos métodos para análisis completos
"""
from typing import List, Union, Dict, Any
from playwright.sync_api import Page

from ..api.endpoints.campanias import CampaignsAPI
from ..api.client import APIClient
from ..api.models.campanias import (
    CampaignSummary, CampaignComplete, CampaignOpener, 
    CampaignClicker, CampaignLink, CampaignSoftBounce
)
from ..scraping.endpoints.campanias import CampaignsScraper
from ..scraping.models.campanias import (
    ScrapedNonOpener, ScrapedHardBounce
)
from ..logger import logger


class HybridCampaignsAPI:
    """
    🎯 API unificada que combina endpoints API + scraping inteligentemente
    
    Estrategia:
    - API: Para datos que existen (openers, clicks, stats básicas)
    - Scraping: Para datos que NO existen (no-openers, hard bounces detallados)
    - Híbrido: Combina ambos para análisis completos
    """
    
    def __init__(self, api_client: APIClient, page: Page):
        """
        Inicializar API híbrida
        
        Args:
            api_client: Cliente para la API oficial de Acumbamail
            page: Página de Playwright para scraping
        """
        self.api = CampaignsAPI(api_client)
        self.scraper = CampaignsScraper(page)
        logger.info("🎯 HybridCampaignsAPI inicializada")
    
    # ===================================================================
    # MÉTODOS API (RÁPIDOS - usar cuando estén disponibles)
    # ===================================================================
    
    def get_all_campaigns(self, complete_info: bool = False) -> Union[List[CampaignSummary], List[CampaignComplete]]:
        """
        ⚡ Obtener todas las campañas (API)
        
        Args:
            complete_info: Si obtener información completa
            
        Returns:
            Lista de campañas
        """
        logger.info("⚡ Usando API para obtener campañas")
        return self.api.get_all(complete_info)
    
    def get_openers(self, campaign_id: int) -> List[CampaignOpener]:
        """⚡ Obtener suscriptores que SÍ abrieron (API)"""
        logger.info(f"⚡ Usando API para obtener openers de campaña {campaign_id}")
        return self.api.get_openers(campaign_id)
    
    def get_clicks(self, campaign_id: int) -> List[CampaignClicker]:
        """⚡ Obtener suscriptores que hicieron clic (API)"""
        logger.info(f"⚡ Usando API para obtener clicks de campaña {campaign_id}")
        return self.api.get_clicks(campaign_id)
    
    def get_links(self, campaign_id: int) -> List[CampaignLink]:
        """⚡ Obtener enlaces y sus estadísticas (API)"""
        logger.info(f"⚡ Usando API para obtener links de campaña {campaign_id}")
        return self.api.get_links(campaign_id)
    
    def get_soft_bounces(self, campaign_id: int) -> List[CampaignSoftBounce]:
        """⚡ Obtener soft bounces (API)"""
        logger.info(f"⚡ Usando API para obtener soft bounces de campaña {campaign_id}")
        return self.api.get_soft_bounces(campaign_id)
    
    # ===================================================================
    # MÉTODOS SCRAPING (ÚNICOS - no existen en API)
    # ===================================================================
    
    def get_non_openers(self, campaign_id: int) -> List[ScrapedNonOpener]:
        """
        🔍 Obtener suscriptores que NO abrieron (SCRAPING ÚNICO)
        
        Este dato NO está disponible en la API de Acumbamail.
        Solo se puede obtener por scraping.
        
        Args:
            campaign_id: ID de la campaña
            
        Returns:
            Lista de suscriptores que no abrieron
        """
        logger.info(f"🔍 Usando SCRAPING para obtener no-openers de campaña {campaign_id}")
        return self.scraper.get_non_openers(campaign_id)
    
    def get_hard_bounces_detailed(self, campaign_id: int) -> List[ScrapedHardBounce]:
        """
        🔍 Obtener hard bounces con detalles (SCRAPING ÚNICO)
        
        Aunque la API puede tener algunos bounces, el scraping puede
        proporcionar detalles adicionales como razones específicas.
        
        Args:
            campaign_id: ID de la campaña
            
        Returns:
            Lista de hard bounces con información detallada
        """
        logger.info(f"🔍 Usando SCRAPING para obtener hard bounces detallados de campaña {campaign_id}")
        return self.scraper.get_hard_bounces(campaign_id)
    
    # ===================================================================
    # MÉTODOS HÍBRIDOS (COMBINAN API + SCRAPING)
    # ===================================================================
    
    def get_complete_subscriber_analysis(self, campaign_id: int) -> Dict[str, Any]:
        """
        🎯 Análisis completo de suscriptores (HÍBRIDO)
        
        Combina datos de API + scraping para obtener el panorama completo:
        - API: Openers, clickers, soft bounces (rápido)
        - Scraping: No-openers, hard bounces detallados (único)
        
        Args:
            campaign_id: ID de la campaña
            
        Returns:
            Diccionario con análisis completo
        """
        logger.info(f"🎯 Iniciando análisis completo de suscriptores para campaña {campaign_id}")
        
        try:
            # === DATOS DE API (RÁPIDOS) ===
            logger.info("⚡ Obteniendo datos de API...")
            api_openers = self.get_openers(campaign_id)
            api_clicks = self.get_clicks(campaign_id)
            api_soft_bounces = self.get_soft_bounces(campaign_id)
            
            # === DATOS DE SCRAPING (ÚNICOS) ===
            logger.info("🔍 Obteniendo datos de scraping...")
            scraped_non_openers = self.get_non_openers(campaign_id)
            scraped_hard_bounces = self.get_hard_bounces_detailed(campaign_id)
            
            # === ANÁLISIS COMBINADO ===
            total_openers = len(api_openers)
            total_non_openers = len(scraped_non_openers)
            total_clickers = len(api_clicks)
            total_soft_bounces = len(api_soft_bounces)
            total_hard_bounces = len(scraped_hard_bounces)
            
            # Calcular totales y tasas
            total_delivered = total_openers + total_non_openers
            open_rate = (total_openers / total_delivered * 100) if total_delivered > 0 else 0
            click_rate = (total_clickers / total_delivered * 100) if total_delivered > 0 else 0
            
            analysis = {
                "campaign_id": campaign_id,
                
                # Datos API
                "api_data": {
                    "openers": api_openers,
                    "clickers": api_clicks,
                    "soft_bounces": api_soft_bounces
                },
                
                # Datos scraping  
                "scraped_data": {
                    "non_openers": scraped_non_openers,
                    "hard_bounces": scraped_hard_bounces
                },
                
                # Resumen y métricas
                "summary": {
                    "total_openers": total_openers,
                    "total_non_openers": total_non_openers,
                    "total_clickers": total_clickers,
                    "total_soft_bounces": total_soft_bounces,
                    "total_hard_bounces": total_hard_bounces,
                    "total_delivered": total_delivered,
                    "open_rate": round(open_rate, 2),
                    "click_rate": round(click_rate, 2)
                },
                
                # Análisis por dominios (solo no-openers y hard bounces)
                "domain_analysis": {
                    "problematic_domains": self._analyze_problematic_domains(
                        scraped_non_openers, scraped_hard_bounces
                    )
                }
            }
            
            logger.info(f"✅ Análisis completo finalizado: {analysis['summary']}")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error en análisis completo: {e}")
            raise
    
    def get_campaign_comparison(self, campaign_ids: List[int]) -> Dict[str, Any]:
        """
        📊 Comparar múltiples campañas (HÍBRIDO)
        
        Obtiene métricas clave de múltiples campañas para comparación.
        Usa API para datos rápidos y scraping selectivo.
        
        Args:
            campaign_ids: Lista de IDs de campañas a comparar
            
        Returns:
            Diccionario con comparación de campañas
        """
        logger.info(f"📊 Iniciando comparación de {len(campaign_ids)} campañas")
        
        comparison = {
            "campaigns": {},
            "summary": {
                "total_campaigns": len(campaign_ids),
                "best_open_rate": 0,
                "worst_open_rate": 100,
                "best_campaign_id": None,
                "worst_campaign_id": None
            }
        }
        
        for campaign_id in campaign_ids:
            try:
                logger.info(f"📊 Analizando campaña {campaign_id}")
                
                # Obtener métricas básicas rápidamente
                openers = self.get_openers(campaign_id)
                
                # Solo hacer scraping de no-openers si queremos análisis detallado
                # Para comparación rápida, podríamos saltárnoslo
                non_openers = self.get_non_openers(campaign_id)
                
                total_delivered = len(openers) + len(non_openers)
                open_rate = (len(openers) / total_delivered * 100) if total_delivered > 0 else 0
                
                comparison["campaigns"][campaign_id] = {
                    "openers": len(openers),
                    "non_openers": len(non_openers),
                    "total_delivered": total_delivered,
                    "open_rate": round(open_rate, 2)
                }
                
                # Actualizar mejores/peores
                if open_rate > comparison["summary"]["best_open_rate"]:
                    comparison["summary"]["best_open_rate"] = open_rate
                    comparison["summary"]["best_campaign_id"] = campaign_id
                
                if open_rate < comparison["summary"]["worst_open_rate"]:
                    comparison["summary"]["worst_open_rate"] = open_rate
                    comparison["summary"]["worst_campaign_id"] = campaign_id
                
            except Exception as e:
                logger.error(f"❌ Error analizando campaña {campaign_id}: {e}")
                comparison["campaigns"][campaign_id] = {"error": str(e)}
        
        logger.info(f"✅ Comparación completada: {comparison['summary']}")
        return comparison
    
    def export_non_openers_to_file(self, campaign_id: int, filename: str = None) -> str:
        """
        💾 Exportar no-openers a archivo CSV (HÍBRIDO)
        
        Usa scraping para obtener no-openers y los exporta a CSV.
        Útil para crear listas de re-engagement.
        
        Args:
            campaign_id: ID de la campaña
            filename: Nombre del archivo (opcional)
            
        Returns:
            Ruta del archivo creado
        """
        import csv
        from pathlib import Path
        from datetime import datetime
        
        # Obtener no-openers por scraping
        non_openers = self.get_non_openers(campaign_id)
        
        # Generar nombre de archivo si no se proporciona
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"non_openers_campaign_{campaign_id}_{timestamp}.csv"
        
        # Crear archivo CSV
        filepath = Path("data") / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=[
                'email', 'campaign_id', 'date_sent', 'list_name', 'subscriber_name', 'domain'
            ])
            
            writer.writeheader()
            for non_opener in non_openers:
                writer.writerow({
                    'email': non_opener.email,
                    'campaign_id': non_opener.campaign_id,
                    'date_sent': non_opener.date_sent,
                    'list_name': non_opener.list_name,
                    'subscriber_name': non_opener.subscriber_name,
                    'domain': non_opener.domain
                })
        
        logger.info(f"💾 No-openers exportados a: {filepath}")
        return str(filepath)
    
    # ===================================================================
    # MÉTODOS AUXILIARES
    # ===================================================================
    
    def _analyze_problematic_domains(self, non_openers: List[ScrapedNonOpener], 
                                   hard_bounces: List[ScrapedHardBounce]) -> Dict[str, Any]:
        """
        Analizar dominios problemáticos combinando no-openers y hard bounces
        
        Args:
            non_openers: Lista de no-openers
            hard_bounces: Lista de hard bounces
            
        Returns:
            Análisis de dominios problemáticos
        """
        from collections import Counter
        
        # Contar dominios en no-openers
        non_opener_domains = Counter(no.domain for no in non_openers if no.domain)
        
        # Contar dominios en hard bounces
        hard_bounce_domains = Counter(hb.domain for hb in hard_bounces if hb.domain)
        
        # Combinar para encontrar dominios más problemáticos
        all_problematic = non_opener_domains + hard_bounce_domains
        
        return {
            "top_non_opener_domains": dict(non_opener_domains.most_common(10)),
            "top_hard_bounce_domains": dict(hard_bounce_domains.most_common(10)),
            "most_problematic_overall": dict(all_problematic.most_common(10))
        }


# ===================================================================
# EJEMPLO DE USO
# ===================================================================
"""
🚀 EJEMPLO DE USO:

from src.infrastructure.api.client import APIClient
from src.hybrid.campanias import HybridCampaignsAPI
from ..core.authentication.authentication_service import AuthenticationService, FileSessionStorage
from ..core.config.config_manager import ConfigManager

def demo_hybrid_api():
    # Inicializar componentes
    api_client = APIClient()
    page = login_acumbamail()  # Tu función existente
    
    # Crear API híbrida
    hybrid = HybridCampaignsAPI(api_client, page)
    
    # Usar métodos API (rápidos)
    campaigns = hybrid.get_all_campaigns()
    print(f"Total campañas: {len(campaigns)}")
    
    if campaigns:
        campaign_id = campaigns[0].id
        
        # Usar métodos scraping (únicos)
        non_openers = hybrid.get_non_openers(campaign_id)
        print(f"No abrieron: {len(non_openers)}")
        
        # Usar análisis híbrido (combinado)
        analysis = hybrid.get_complete_subscriber_analysis(campaign_id)
        print(f"Análisis completo: {analysis['summary']}")
        
        # Exportar datos únicos
        csv_file = hybrid.export_non_openers_to_file(campaign_id)
        print(f"Exportado a: {csv_file}")

if __name__ == "__main__":
    demo_hybrid_api()
"""