"""
Modelos para datos de suscriptores obtenidos por scraping
Extienden los modelos de API con información específica de scraping
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from ...api.models.suscriptores import ActualSubscriber
from ...api.models.campanias import CampaignBasicInfo


class SubscriberQuality(str, Enum):
    """Calidades de suscriptor observadas en scraping"""
    EXCELLENT = "Excelente"
    GOOD = "Buena"
    REGULAR = "Regular"
    POOR = "Pobre"
    UNKNOWN = ""


class SubscriberStatus(str, Enum):
    """Estados de suscriptor observados en scraping"""
    ACTIVE = "Activo"
    INACTIVE = "Inactivo"
    BOUNCED = "Rebotado"
    UNSUBSCRIBED = "Dado de baja"
    UNKNOWN = ""


class SubscriberDetailBase(BaseModel):
    """Modelo base para detalles de suscriptor extraído por scraping"""
    email: str = Field(..., description="Email del suscriptor")
    lista: str = Field("", description="Nombre de la lista")
    estado: SubscriberStatus = Field(SubscriberStatus.UNKNOWN, description="Estado del suscriptor")
    calidad: SubscriberQuality = Field(SubscriberQuality.UNKNOWN, description="Calidad del suscriptor")
    proyecto: str = Field("", description="Nombre del proyecto/campaña")

    # Metadatos de scraping
    extracted_at: datetime = Field(default_factory=datetime.now, description="Fecha de extracción")
    page_number: Optional[int] = Field(None, description="Número de página donde fue encontrado")

    class Config:
        use_enum_values = True


class HardBounceSubscriber(SubscriberDetailBase):
    """Suscriptor con hard bounce obtenido por scraping"""
    bounce_reason: Optional[str] = Field(None, description="Razón del rebote si está disponible")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@dominio-inexistente.com",
                "lista": "Lista Principal",
                "estado": "Rebotado",
                "calidad": "Pobre",
                "proyecto": "Campaña Newsletter",
                "bounce_reason": "Dominio no existe"
            }
        }


class SoftBounceSubscriber(SubscriberDetailBase):
    """Suscriptor con soft bounce obtenido por scraping"""
    bounce_attempts: Optional[int] = Field(None, description="Número de intentos de entrega")
    last_bounce_date: Optional[str] = Field(None, description="Fecha del último rebote")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@gmail.com",
                "lista": "Lista Promocional",
                "estado": "Activo",
                "calidad": "Regular",
                "proyecto": "Campaña Promocional",
                "bounce_attempts": 2,
                "last_bounce_date": "2025-09-20"
            }
        }


class NoOpenSubscriber(SubscriberDetailBase):
    """Suscriptor que no abrió el email obtenido por scraping"""
    days_since_sent: Optional[int] = Field(None, description="Días desde que se envió la campaña")
    previous_opens: Optional[int] = Field(0, description="Aperturas en campañas anteriores")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@ejemplo.com",
                "lista": "Lista Clientes",
                "estado": "Activo",
                "calidad": "Buena",
                "proyecto": "Newsletter Semanal",
                "days_since_sent": 7,
                "previous_opens": 3
            }
        }


class ScrapingPaginationInfo(BaseModel):
    """Información de paginación para scraping"""
    current_page: int = Field(1, description="Página actual")
    total_pages: int = Field(1, description="Total de páginas")
    has_next: bool = Field(False, description="Tiene página siguiente")
    items_per_page: Optional[int] = Field(None, description="Items por página")
    total_items: Optional[int] = Field(None, description="Total de items")

    @property
    def is_last_page(self) -> bool:
        return self.current_page >= self.total_pages

    @property
    def progress_percentage(self) -> float:
        if self.total_pages > 0:
            return (self.current_page / self.total_pages) * 100
        return 0.0


class FilterInfo(BaseModel):
    """Información sobre el filtro aplicado durante el scraping"""
    filter_name: str = Field(..., description="Nombre del filtro (ej: 'Hard bounces', 'No abiertos')")
    filter_value: Optional[str] = Field(None, description="Valor del filtro si aplica")
    total_results: Optional[int] = Field(None, description="Total de resultados para este filtro")

    class Config:
        json_schema_extra = {
            "example": {
                "filter_name": "Hard bounces",
                "filter_value": None,
                "total_results": 45
            }
        }


class ScrapingResult(BaseModel):
    """Resultado completo de scraping para una campaña"""
    campaign_id: int = Field(..., description="ID de la campaña")
    campaign_name: str = Field("", description="Nombre de la campaña")

    # Datos extraídos
    hard_bounces: List[HardBounceSubscriber] = Field(default_factory=list)
    soft_bounces: List[SoftBounceSubscriber] = Field(default_factory=list)
    no_opens: List[NoOpenSubscriber] = Field(default_factory=list)

    # Metadatos del scraping
    extraction_datetime: datetime = Field(default_factory=datetime.now)
    total_processed: int = Field(0, description="Total de registros procesados")
    filters_applied: List[FilterInfo] = Field(default_factory=list)
    pagination_info: Optional[ScrapingPaginationInfo] = Field(None)

    # Estadísticas calculadas
    @property
    def total_hard_bounces(self) -> int:
        return len(self.hard_bounces)

    @property
    def total_soft_bounces(self) -> int:
        return len(self.soft_bounces)

    @property
    def total_no_opens(self) -> int:
        return len(self.no_opens)

    @property
    def extraction_summary(self) -> Dict[str, int]:
        return {
            "hard_bounces": self.total_hard_bounces,
            "soft_bounces": self.total_soft_bounces,
            "no_opens": self.total_no_opens,
            "total_processed": self.total_processed
        }

    class Config:
        json_schema_extra = {
            "example": {
                "campaign_id": 123456,
                "campaign_name": "Newsletter Marzo 2025",
                "hard_bounces": [],
                "soft_bounces": [],
                "no_opens": [],
                "total_processed": 150,
                "filters_applied": [
                    {"filter_name": "Hard bounces", "total_results": 12},
                    {"filter_name": "No abiertos", "total_results": 85}
                ]
            }
        }


class ScrapingError(Exception):
    """Error de excepción durante el scraping"""
    def __init__(self, error_type: str, error_message: str, context: Dict[str, Any] = None):
        self.error_type = error_type
        self.error_message = error_message
        self.occurred_at = datetime.now()
        self.context = context or {}
        super().__init__(error_message)


class ScrapingErrorRecord(BaseModel):
    """Registro de error durante el scraping para almacenar en resultados"""
    error_type: str = Field(..., description="Tipo de error")
    error_message: str = Field(..., description="Mensaje de error")
    occurred_at: datetime = Field(default_factory=datetime.now)
    context: Dict[str, Any] = Field(default_factory=dict, description="Contexto adicional del error")

    class Config:
        json_schema_extra = {
            "example": {
                "error_type": "NavigationError",
                "error_message": "No se pudo navegar a la página de detalles",
                "context": {
                    "campaign_id": 123456,
                    "current_page": 3,
                    "filter": "Hard bounces"
                }
            }
        }


class ScrapingSession(BaseModel):
    """Sesión completa de scraping con múltiples campañas"""
    session_id: str = Field(..., description="ID único de la sesión")
    started_at: datetime = Field(default_factory=datetime.now)
    finished_at: Optional[datetime] = Field(None)

    # Resultados por campaña
    campaign_results: List[ScrapingResult] = Field(default_factory=list)
    errors: List[ScrapingErrorRecord] = Field(default_factory=list)

    # Estadísticas generales
    total_campaigns_processed: int = Field(0)
    total_subscribers_extracted: int = Field(0)
    success_rate: float = Field(0.0)

    @property
    def duration_minutes(self) -> Optional[float]:
        if self.finished_at and self.started_at:
            delta = self.finished_at - self.started_at
            return delta.total_seconds() / 60
        return None

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def add_campaign_result(self, result: ScrapingResult):
        """Agregar resultado de campaña y actualizar estadísticas"""
        self.campaign_results.append(result)
        self.total_campaigns_processed = len(self.campaign_results)
        self.total_subscribers_extracted = sum(
            r.total_processed for r in self.campaign_results
        )

        # Calcular tasa de éxito (campañas sin errores críticos)
        successful_campaigns = len([r for r in self.campaign_results if r.total_processed > 0])
        if self.total_campaigns_processed > 0:
            self.success_rate = (successful_campaigns / self.total_campaigns_processed) * 100

    def finish_session(self):
        """Marcar sesión como terminada"""
        self.finished_at = datetime.now()

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "scraping_20250922_143022",
                "total_campaigns_processed": 5,
                "total_subscribers_extracted": 1250,
                "success_rate": 100.0
            }
        }