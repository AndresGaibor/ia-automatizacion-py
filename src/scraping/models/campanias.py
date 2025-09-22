"""
Modelos para datos de campañas obtenidos por scraping

Estos modelos representan datos que NO están disponibles en la API de Acumbamail
y solo se pueden obtener mediante scraping.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ScrapedNonOpener(BaseModel):
    """
    Suscriptor que NO abrió la campaña
    
    Este dato no está disponible en la API de Acumbamail,
    solo se puede obtener por scraping.
    """
    email: str = Field(..., description="Email del suscriptor")
    campaign_id: int = Field(..., description="ID de la campaña")
    date_sent: Optional[str] = Field(None, description="Fecha de envío")
    list_name: Optional[str] = Field(None, description="Nombre de la lista")
    subscriber_name: Optional[str] = Field(None, description="Nombre del suscriptor")
    reason: Optional[str] = Field(None, description="Razón por la que no abrió (si está disponible)")
    
    @property
    def domain(self) -> str:
        """Extraer dominio del email"""
        return self.email.split("@")[1] if "@" in self.email else ""
    
    @property
    def username(self) -> str:
        """Extraer usuario del email"""
        return self.email.split("@")[0] if "@" in self.email else self.email
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@ejemplo.com",
                "campaign_id": 12345,
                "date_sent": "2024-01-15",
                "list_name": "Lista Principal",
                "subscriber_name": "Juan Pérez",
                "reason": None
            }
        }


class ScrapedHardBounce(BaseModel):
    """
    Hard bounce con información detallada
    
    Aunque la API tiene soft bounces, los hard bounces con detalles
    pueden requerir scraping para obtener información completa.
    """
    email: str = Field(..., description="Email con hard bounce")
    campaign_id: int = Field(..., description="ID de la campaña")
    bounce_date: Optional[str] = Field(None, description="Fecha del bounce")
    bounce_reason: Optional[str] = Field(None, description="Razón específica del bounce")
    bounce_code: Optional[str] = Field(None, description="Código de error del bounce")
    list_name: Optional[str] = Field(None, description="Lista de origen")
    subscriber_name: Optional[str] = Field(None, description="Nombre del suscriptor")
    
    @property
    def domain(self) -> str:
        """Extraer dominio del email"""
        return self.email.split("@")[1] if "@" in self.email else ""
    
    @property
    def is_permanent(self) -> bool:
        """Determinar si es un bounce permanente basado en la razón"""
        if not self.bounce_reason:
            return True  # Asumir permanente si no hay razón
        
        permanent_indicators = [
            "mailbox does not exist",
            "user unknown",
            "recipient rejected",
            "domain not found"
        ]
        
        reason_lower = self.bounce_reason.lower()
        return any(indicator in reason_lower for indicator in permanent_indicators)
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "invalido@noexiste.com",
                "campaign_id": 12345,
                "bounce_date": "2024-01-15",
                "bounce_reason": "Mailbox does not exist",
                "bounce_code": "550",
                "list_name": "Lista Principal",
                "subscriber_name": "Email Inválido"
            }
        }


class ScrapedGeographicStats(BaseModel):
    """Estadísticas geográficas de una campaña"""
    country: str = Field(..., description="País")
    opens: int = Field(0, description="Aperturas desde este país")
    clicks: int = Field(0, description="Clics desde este país")
    percentage: float = Field(0.0, description="Porcentaje del total")
    
    class Config:
        json_schema_extra = {
            "example": {
                "country": "España",
                "opens": 150,
                "clicks": 25,
                "percentage": 45.5
            }
        }


class ScrapedDeviceStats(BaseModel):
    """Estadísticas por dispositivo de una campaña"""
    device_type: str = Field(..., description="Tipo de dispositivo (móvil, escritorio, tablet)")
    device_name: Optional[str] = Field(None, description="Nombre específico del dispositivo")
    email_client: Optional[str] = Field(None, description="Cliente de email usado")
    opens: int = Field(0, description="Aperturas desde este dispositivo")
    clicks: int = Field(0, description="Clics desde este dispositivo")
    percentage: float = Field(0.0, description="Porcentaje del total")
    
    class Config:
        json_schema_extra = {
            "example": {
                "device_type": "móvil",
                "device_name": "iPhone",
                "email_client": "Gmail App",
                "opens": 80,
                "clicks": 12,
                "percentage": 24.2
            }
        }


class ScrapedCampaignStats(BaseModel):
    """
    Estadísticas extendidas de campaña solo disponibles por scraping
    
    Incluye datos que no están en la API y requieren navegación web.
    """
    campaign_id: int = Field(..., description="ID de la campaña")
    
    # Estadísticas básicas (verificación con API)
    total_sent: int = Field(0, description="Total de emails enviados")
    total_opened: int = Field(0, description="Total de emails abiertos")
    total_not_opened: int = Field(0, description="Total de emails NO abiertos")
    total_clicks: int = Field(0, description="Total de clics")
    total_hard_bounces: int = Field(0, description="Total de hard bounces")
    total_soft_bounces: int = Field(0, description="Total de soft bounces")
    
    # Datos solo disponibles por scraping
    geographic_stats: List[ScrapedGeographicStats] = Field(default_factory=list, description="Estadísticas por país")
    device_stats: List[ScrapedDeviceStats] = Field(default_factory=list, description="Estadísticas por dispositivo")
    hourly_stats: Optional[Dict[str, int]] = Field(None, description="Estadísticas por hora del día")
    daily_stats: Optional[Dict[str, int]] = Field(None, description="Estadísticas por día de la semana")
    
    # Metadatos del scraping
    scraped_at: Optional[str] = Field(None, description="Timestamp del scraping")
    scraping_duration: Optional[float] = Field(None, description="Duración del scraping en segundos")
    
    @property
    def non_open_rate(self) -> float:
        """Tasa de no apertura"""
        if self.total_sent == 0:
            return 0.0
        return (self.total_not_opened / self.total_sent) * 100
    
    @property
    def hard_bounce_rate(self) -> float:
        """Tasa de hard bounces"""
        if self.total_sent == 0:
            return 0.0
        return (self.total_hard_bounces / self.total_sent) * 100
    
    @property
    def top_countries(self) -> List[ScrapedGeographicStats]:
        """Top 5 países por aperturas"""
        return sorted(self.geographic_stats, key=lambda x: x.opens, reverse=True)[:5]
    
    @property
    def top_devices(self) -> List[ScrapedDeviceStats]:
        """Top 5 dispositivos por aperturas"""
        return sorted(self.device_stats, key=lambda x: x.opens, reverse=True)[:5]
    
    class Config:
        json_schema_extra = {
            "example": {
                "campaign_id": 12345,
                "total_sent": 10000,
                "total_opened": 2500,
                "total_not_opened": 7500,
                "total_clicks": 400,
                "total_hard_bounces": 50,
                "total_soft_bounces": 150,
                "geographic_stats": [
                    {
                        "country": "España",
                        "opens": 1200,
                        "clicks": 180,
                        "percentage": 48.0
                    }
                ],
                "device_stats": [
                    {
                        "device_type": "móvil",
                        "opens": 1500,
                        "clicks": 240,
                        "percentage": 60.0
                    }
                ],
                "scraped_at": "2024-01-15T10:30:00Z",
                "scraping_duration": 45.2
            }
        }


class ScrapedCampaignData(BaseModel):
    """
    Contenedor para todos los datos scrapeados de una campaña
    
    Agrupa todos los tipos de datos que se pueden obtener por scraping.
    """
    campaign_id: int = Field(..., description="ID de la campaña")
    
    # Listas de suscriptores
    non_openers: List[ScrapedNonOpener] = Field(default_factory=list, description="Suscriptores que no abrieron")
    hard_bounces: List[ScrapedHardBounce] = Field(default_factory=list, description="Hard bounces con detalles")
    
    # Estadísticas extendidas
    extended_stats: Optional[ScrapedCampaignStats] = Field(None, description="Estadísticas extendidas")
    
    # Metadatos
    scraped_at: str = Field(..., description="Timestamp del scraping")
    scraping_methods: List[str] = Field(default_factory=list, description="Métodos de scraping utilizados")
    
    @property
    def total_scraped_emails(self) -> int:
        """Total de emails únicos scrapeados"""
        all_emails = set()
        all_emails.update(item.email for item in self.non_openers)
        all_emails.update(item.email for item in self.hard_bounces)
        return len(all_emails)
    
    @property
    def summary(self) -> Dict[str, Any]:
        """Resumen de los datos scrapeados"""
        return {
            "campaign_id": self.campaign_id,
            "non_openers_count": len(self.non_openers),
            "hard_bounces_count": len(self.hard_bounces),
            "total_unique_emails": self.total_scraped_emails,
            "has_extended_stats": self.extended_stats is not None,
            "scraped_at": self.scraped_at,
            "methods_used": self.scraping_methods
        }
    
    class Config:
        json_schema_extra = {
            "example": {
                "campaign_id": 12345,
                "non_openers": [],
                "hard_bounces": [],
                "extended_stats": None,
                "scraped_at": "2024-01-15T10:30:00Z",
                "scraping_methods": ["get_non_openers", "get_hard_bounces"]
            }
        }