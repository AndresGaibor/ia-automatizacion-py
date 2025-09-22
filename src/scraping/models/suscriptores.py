from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class SubscriberScrapingData(BaseModel):
    """Modelo para datos de suscriptor extraídos por scraping"""
    proyecto: str = Field("", description="Nombre del proyecto/campaña")
    lista: str = Field("", description="Nombre de la lista")
    correo: str = Field("", description="Email del suscriptor")
    fecha_apertura: Optional[str] = Field(None, description="Fecha de apertura")
    fecha_clic: Optional[str] = Field(None, description="Fecha del primer clic")
    pais: str = Field("", description="País de apertura")
    aperturas: str = Field("", description="Número de aperturas")
    lista2: str = Field("", description="Lista duplicada")
    estado: str = Field("Activo", description="Estado del suscriptor")
    calidad: str = Field("", description="Calidad del suscriptor")

    class Config:
        json_schema_extra = {
            "example": {
                "proyecto": "Campaña de Bienvenida",
                "lista": "Lista Principal",
                "correo": "usuario@example.com",
                "fecha_apertura": "2024-01-15 10:30:00",
                "fecha_clic": "2024-01-15 10:35:00",
                "pais": "España",
                "aperturas": "3",
                "lista2": "Lista Principal",
                "estado": "Activo",
                "calidad": "Buena"
            }
        }

class SubscriberTableData(BaseModel):
    """Modelo para datos extraídos de tabla de suscriptores en la interfaz web"""
    correo: str = Field("", description="Email del suscriptor")
    lista: str = Field("", description="Nombre de la lista")
    estado: str = Field("", description="Estado del suscriptor")
    calidad: str = Field("", description="Calidad del suscriptor")

    class Config:
        json_schema_extra = {
            "example": {
                "correo": "usuario@example.com",
                "lista": "Lista Principal",
                "estado": "Activo",
                "calidad": "Buena"
            }
        }

class SubscriberFilterResult(BaseModel):
    """Resultado de aplicar un filtro específico de suscriptores"""
    filter_type: str = Field(..., description="Tipo de filtro aplicado")
    subscribers: List[SubscriberScrapingData] = Field(default_factory=list, description="Suscriptores extraídos")
    total_pages: int = Field(0, description="Total de páginas procesadas")
    total_subscribers: int = Field(0, description="Total de suscriptores extraídos")

    @property
    def success_rate(self) -> float:
        """Calcular tasa de éxito de extracción"""
        if self.total_pages > 0:
            return (len(self.subscribers) / (self.total_pages * 25)) * 100  # Asumiendo 25 por página
        return 0.0

    class Config:
        json_schema_extra = {
            "example": {
                "filter_type": "Hard bounces",
                "subscribers": [],
                "total_pages": 5,
                "total_subscribers": 120
            }
        }

class CampaignSubscriberReport(BaseModel):
    """Informe completo de suscriptores de una campaña"""
    campaign_id: int = Field(..., description="ID de la campaña")
    campaign_name: str = Field("", description="Nombre de la campaña")
    fecha_envio: str = Field("", description="Fecha de envío de la campaña")

    # Datos por tipo
    abiertos: List[SubscriberScrapingData] = Field(default_factory=list, description="Suscriptores que abrieron")
    no_abiertos: List[SubscriberScrapingData] = Field(default_factory=list, description="Suscriptores que no abrieron")
    clics: List[SubscriberScrapingData] = Field(default_factory=list, description="Suscriptores que hicieron clic")
    hard_bounces: List[SubscriberScrapingData] = Field(default_factory=list, description="Hard bounces")
    soft_bounces: List[SubscriberScrapingData] = Field(default_factory=list, description="Soft bounces")

    # Metadatos de procesamiento
    extracted_at: datetime = Field(default_factory=datetime.now, description="Fecha de extracción")
    processing_time_seconds: Optional[float] = Field(None, description="Tiempo total de procesamiento")

    @property
    def total_subscribers(self) -> int:
        """Total de suscriptores únicos extraídos"""
        all_emails = set()
        for subscriber_list in [self.abiertos, self.no_abiertos, self.clics, self.hard_bounces, self.soft_bounces]:
            for subscriber in subscriber_list:
                all_emails.add(subscriber.correo)
        return len(all_emails)

    @property
    def summary_counts(self) -> Dict[str, int]:
        """Resumen de conteos por tipo"""
        return {
            "abiertos": len(self.abiertos),
            "no_abiertos": len(self.no_abiertos),
            "clics": len(self.clics),
            "hard_bounces": len(self.hard_bounces),
            "soft_bounces": len(self.soft_bounces),
            "total_unicos": self.total_subscribers
        }

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        json_schema_extra = {
            "example": {
                "campaign_id": 123456,
                "campaign_name": "Campaña de Bienvenida",
                "fecha_envio": "2024-01-15",
                "abiertos": [],
                "no_abiertos": [],
                "clics": [],
                "hard_bounces": [],
                "soft_bounces": [],
                "processing_time_seconds": 45.2
            }
        }

class PageNavigationInfo(BaseModel):
    """Información de navegación entre páginas durante el scraping"""
    current_page: int = Field(1, description="Página actual")
    total_pages: int = Field(1, description="Total de páginas")
    items_per_page: int = Field(25, description="Elementos por página")
    has_next: bool = Field(False, description="Hay página siguiente")
    navigation_successful: bool = Field(True, description="Navegación exitosa")

    @property
    def progress_percentage(self) -> float:
        """Porcentaje de progreso"""
        if self.total_pages > 0:
            return (self.current_page / self.total_pages) * 100
        return 0.0

    class Config:
        json_schema_extra = {
            "example": {
                "current_page": 3,
                "total_pages": 10,
                "items_per_page": 25,
                "has_next": True,
                "navigation_successful": True
            }
        }

class ScrapingSession(BaseModel):
    """Sesión de scraping para tracking y logging"""
    session_id: str = Field(..., description="ID único de la sesión")
    started_at: datetime = Field(default_factory=datetime.now, description="Inicio de la sesión")
    ended_at: Optional[datetime] = Field(None, description="Fin de la sesión")
    campaign_ids: List[int] = Field(default_factory=list, description="IDs de campañas procesadas")
    total_subscribers_extracted: int = Field(0, description="Total de suscriptores extraídos")
    errors_encountered: List[str] = Field(default_factory=list, description="Errores encontrados")
    status: str = Field("active", description="Estado de la sesión")

    @property
    def duration_seconds(self) -> Optional[float]:
        """Duración de la sesión en segundos"""
        if self.ended_at and self.started_at:
            return (self.ended_at - self.started_at).total_seconds()
        return None

    @property
    def campaigns_processed(self) -> int:
        """Número de campañas procesadas"""
        return len(self.campaign_ids)

    def add_error(self, error_message: str) -> None:
        """Agregar un error a la sesión"""
        self.errors_encountered.append(f"{datetime.now().isoformat()}: {error_message}")

    def complete_session(self) -> None:
        """Marcar la sesión como completada"""
        self.ended_at = datetime.now()
        self.status = "completed"

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        json_schema_extra = {
            "example": {
                "session_id": "scraping_20240115_103000",
                "campaign_ids": [123, 124, 125],
                "total_subscribers_extracted": 1500,
                "errors_encountered": [],
                "status": "active"
            }
        }

class SubscriberExtractionConfig(BaseModel):
    """Configuración para extracción de suscriptores"""
    extract_abiertos: bool = Field(True, description="Extraer suscriptores que abrieron")
    extract_no_abiertos: bool = Field(True, description="Extraer suscriptores que no abrieron")
    extract_clics: bool = Field(True, description="Extraer suscriptores que hicieron clic")
    extract_hard_bounces: bool = Field(True, description="Extraer hard bounces")
    extract_soft_bounces: bool = Field(True, description="Extraer soft bounces")

    max_pages_per_filter: Optional[int] = Field(None, description="Máximo de páginas por filtro")
    timeout_seconds: int = Field(30, description="Timeout para operaciones")
    retry_attempts: int = Field(3, description="Intentos de reintento")

    # Optimizaciones
    use_optimized_extraction: bool = Field(True, description="Usar extracción optimizada")
    batch_process: bool = Field(True, description="Procesar en lotes")

    class Config:
        json_schema_extra = {
            "example": {
                "extract_abiertos": True,
                "extract_no_abiertos": True,
                "extract_clics": True,
                "extract_hard_bounces": True,
                "extract_soft_bounces": False,
                "max_pages_per_filter": 50,
                "timeout_seconds": 30,
                "retry_attempts": 3,
                "use_optimized_extraction": True,
                "batch_process": True
            }
        }