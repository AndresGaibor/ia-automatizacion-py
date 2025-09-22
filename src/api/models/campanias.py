from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum

class CampaignStatus(str, Enum):
    """Estados posibles de una campaña"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    PAUSED = "paused"
    CANCELLED = "cancelled"

class CampaignSummary(BaseModel):
    """Modelo simplificado para la respuesta de getCampaigns"""
    id: int = Field(..., description="ID único de la campaña")
    name: str = Field(..., description="Nombre de la campaña")
    
    @classmethod
    def from_api_dict(cls, api_item: Dict[str, str]) -> "CampaignSummary":
        """Crear CampaignSummary desde el formato de API {id: nombre}"""
        campaign_id, campaign_name = next(iter(api_item.items()))
        return cls(id=int(campaign_id), name=campaign_name)
    
    @classmethod
    def from_api_response(cls, api_response: List[Dict[str, str]]) -> List["CampaignSummary"]:
        """Convertir respuesta completa de API a lista de CampaignSummary"""
        return [cls.from_api_dict(item) for item in api_response if isinstance(item, dict)]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class CampaignBasicInfo(BaseModel):
    """Información básica de campaña desde getCampaignBasicInformation"""
    status: str = Field(..., description="Estado actual de la campaña")
    date_sent: Optional[str] = Field(None, description="Fecha de envío ('None' si no enviada)")
    name: str = Field(..., description="Nombre de la campaña")
    date: str = Field(..., description="Fecha de creación")
    total_sent: int = Field(0, description="Total de emails enviados")
    email_from: str = Field("", description="Email del remitente")
    lists: List[Any] = Field(default_factory=list, description="Listas asociadas")
    subject: str = Field("", description="Asunto del email")
    
    @classmethod
    def from_api_response(cls, api_response: Dict[str, Any]) -> "CampaignBasicInfo":
        """Crear CampaignBasicInfo desde respuesta de API"""
        return cls(**api_response)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        json_schema_extra = {
            "example": {
                "status": "Editing",
                "date_sent": "None",
                "name": "Prueba Encuestas-228275",
                "date": "2025-06-02 11:18:24",
                "total_sent": 0,
                "email_from": "",
                "lists": [],
                "subject": ""
            }
        }

class CampaignDetailedInfo(BaseModel):
    """Información detallada de campaña desde getCampaignTotalInformation"""
    total_delivered: int = Field(0, description="Emails entregados exitosamente")
    soft_bounces: int = Field(0, description="Rebotes temporales")
    campaign_url: str = Field("", description="URL de visualización de la campaña")
    unsubscribes: int = Field(0, description="Bajas/desuscripciones")
    complaints: int = Field(0, description="Quejas/spam reports")
    unique_clicks: int = Field(0, description="Clics únicos (por usuario)")
    unopened: int = Field(0, description="Emails no abiertos")
    emails_to_send: int = Field(0, description="Emails pendientes de envío")
    opened: int = Field(0, description="Emails abiertos")
    hard_bounces: int = Field(0, description="Rebotes permanentes")
    total_clicks: int = Field(0, description="Total de clics")
    
    @classmethod
    def from_api_response(cls, api_response: Dict[str, Any]) -> "CampaignDetailedInfo":
        """Crear CampaignDetailedInfo desde respuesta de API"""
        return cls(**api_response)
    
    # Propiedades calculadas
    @property
    def open_rate(self) -> float:
        """Calcular tasa de apertura como porcentaje"""
        if self.total_delivered > 0:
            return (self.opened / self.total_delivered) * 100
        return 0.0
    
    @property
    def click_rate(self) -> float:
        """Calcular tasa de clics como porcentaje"""
        if self.total_delivered > 0:
            return (self.unique_clicks / self.total_delivered) * 100
        return 0.0
    
    @property
    def bounce_rate(self) -> float:
        """Calcular tasa de rebote como porcentaje"""
        total_bounces = self.hard_bounces + self.soft_bounces
        if self.emails_to_send > 0:
            return (total_bounces / self.emails_to_send) * 100
        return 0.0
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        json_schema_extra = {
            "example": {
                "total_delivered": 100,
                "soft_bounces": 2,
                "campaign_url": "https://clickacm.com/show/example",
                "unsubscribes": 1,
                "complaints": 0,
                "unique_clicks": 15,
                "unopened": 30,
                "emails_to_send": 100,
                "opened": 70,
                "hard_bounces": 0,
                "total_clicks": 25
            }
        }

class CampaignComplete(BaseModel):
    """Información completa de campaña desde getCampaigns con complete_json=1"""
    id: int = Field(..., description="ID único de la campaña")
    name: str = Field(..., description="Nombre de la campaña")
    subject: str = Field("", description="Asunto del email")
    date: str = Field(..., description="Fecha de creación")
    from_name: str = Field("", description="Nombre del remitente")
    from_email: str = Field("", description="Email del remitente")
    total_delivered: int = Field(0, description="Total de emails entregados")
    opened: int = Field(0, description="Emails abiertos")
    unopened: int = Field(0, description="Emails no abiertos")
    
    @classmethod
    def from_api_response(cls, api_response: List[Dict[str, Any]]) -> List["CampaignComplete"]:
        """Convertir respuesta de API con complete_json=1 a lista de CampaignComplete"""
        return [cls(**item) for item in api_response if isinstance(item, dict)]
    
    # Propiedades calculadas
    @property
    def open_rate(self) -> float:
        """Calcular tasa de apertura como porcentaje"""
        if self.total_delivered > 0:
            return (self.opened / self.total_delivered) * 100
        return 0.0
    
    @property
    def creation_date(self) -> str:
        """Extraer solo la fecha de creación"""
        return self.date.split(" ")[0] if " " in self.date else self.date
    
    @property
    def creation_time(self) -> str:
        """Extraer solo la hora de creación"""
        return self.date.split(" ")[1] if " " in self.date else ""
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 3250041,
                "name": "Prueba Encuestas-228275",
                "subject": "Test Subject",
                "date": "2025-06-02 11:18:24",
                "from_name": "Remitente",
                "from_email": "test@example.com",
                "total_delivered": 100,
                "opened": 75,
                "unopened": 25
            }
        }

class Campaign(BaseModel):
    """Modelo de campaña con validación automática basado en la API de Acumbamail"""
    
    # Identificación
    id: Optional[int] = Field(None, description="ID único de la campaña")
    name: str = Field(..., description="Nombre de la campaña", max_length=255)
    
    # Información del remitente
    from_name: str = Field(..., description="Nombre del remitente", max_length=100)
    from_email: EmailStr = Field(..., description="Email del remitente")
    
    # Contenido
    subject: str = Field(..., description="Asunto del email", max_length=255)
    content: Optional[str] = Field(None, description="Contenido HTML del email")
    template_id: Optional[int] = Field(None, description="ID de la plantilla a usar")
    
    # Destinatarios
    lists: Dict[str, str] = Field(..., description="Listas destinatarias {id: nombre}")
    
    # Programación
    date_send: Optional[datetime] = Field(None, description="Fecha de envío programado")
    
    # Configuración
    tracking_urls: Optional[bool] = Field(True, description="Activar seguimiento de URLs")
    https: Optional[bool] = Field(True, description="Usar HTTPS en los enlaces")
    complete_json: Optional[bool] = Field(False, description="Respuesta completa en JSON")
    
    # Estado y estadísticas (solo lectura)
    status: Optional[CampaignStatus] = Field(None, description="Estado actual de la campaña")
    created_date: Optional[datetime] = Field(None, description="Fecha de creación")
    sent_date: Optional[datetime] = Field(None, description="Fecha de envío real")
    
    # Estadísticas básicas
    total_recipients: Optional[int] = Field(None, description="Total de destinatarios")
    total_sent: Optional[int] = Field(None, description="Total enviados")
    total_opens: Optional[int] = Field(None, description="Total de aperturas")
    total_clicks: Optional[int] = Field(None, description="Total de clics")
    total_bounces: Optional[int] = Field(None, description="Total de rebotes")
    total_unsubscribes: Optional[int] = Field(None, description="Total de bajas")
    
    # Configuración avanzada
    category: Optional[str] = Field(None, description="Categoría de la campaña")
    merge_tags: Optional[Dict[str, Any]] = Field(None, description="Variables de personalización")
    
    class Config:
        """Configuración del modelo"""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        json_schema_extra = {
            "example": {
                "name": "Campaña de Bienvenida",
                "from_name": "Mi Empresa",
                "from_email": "info@miempresa.com",
                "subject": "¡Bienvenido a nuestra comunidad!",
                "content": "<html><body><h1>Bienvenido</h1><p>Gracias por suscribirte.</p></body></html>",
                "lists": {"12345": "Lista Principal"},
                "tracking_urls": True,
                "https": True
            }
        }

class CampaignCreate(BaseModel):
    """Modelo para crear una nueva campaña"""
    name: str = Field(..., description="Nombre de la campaña", max_length=255)
    from_name: str = Field(..., description="Nombre del remitente", max_length=100)
    from_email: EmailStr = Field(..., description="Email del remitente")
    subject: str = Field(..., description="Asunto del email", max_length=255)
    content: Optional[str] = Field(None, description="Contenido HTML del email")
    template_id: Optional[int] = Field(None, description="ID de la plantilla a usar")
    lists: Dict[str, str] = Field(..., description="Listas destinatarias {id: nombre}")
    date_send: Optional[datetime] = Field(None, description="Fecha de envío programado")
    tracking_urls: Optional[bool] = Field(True, description="Activar seguimiento de URLs")
    https: Optional[bool] = Field(True, description="Usar HTTPS en los enlaces")
    complete_json: Optional[bool] = Field(False, description="Respuesta completa en JSON")
    category: Optional[str] = Field(None, description="Categoría de la campaña")
    merge_tags: Optional[Dict[str, Any]] = Field(None, description="Variables de personalización")

class CampaignStats(BaseModel):
    """Modelo para estadísticas detalladas de campaña"""
    campaign_id: int = Field(..., description="ID de la campaña")
    
    # Estadísticas básicas
    total_recipients: int = Field(0, description="Total de destinatarios")
    total_sent: int = Field(0, description="Total enviados")
    total_opens: int = Field(0, description="Total de aperturas")
    unique_opens: int = Field(0, description="Aperturas únicas")
    total_clicks: int = Field(0, description="Total de clics")
    unique_clicks: int = Field(0, description="Clics únicos")
    total_bounces: int = Field(0, description="Total de rebotes")
    soft_bounces: int = Field(0, description="Rebotes suaves")
    hard_bounces: int = Field(0, description="Rebotes duros")
    total_unsubscribes: int = Field(0, description="Total de bajas")
    total_complaints: int = Field(0, description="Total de quejas")
    
    # Porcentajes calculados
    open_rate: Optional[float] = Field(None, description="Tasa de apertura (%)")
    click_rate: Optional[float] = Field(None, description="Tasa de clics (%)")
    bounce_rate: Optional[float] = Field(None, description="Tasa de rebote (%)")
    unsubscribe_rate: Optional[float] = Field(None, description="Tasa de baja (%)")
    
    # Información temporal
    first_open: Optional[datetime] = Field(None, description="Primera apertura")
    last_open: Optional[datetime] = Field(None, description="Última apertura")
    first_click: Optional[datetime] = Field(None, description="Primer clic")
    last_click: Optional[datetime] = Field(None, description="Último clic")

class CampaignOpener(BaseModel):
    """Modelo para suscriptores que abrieron la campaña"""
    email: str = Field(..., description="Email del suscriptor")
    open_datetime: str = Field(..., description="Fecha y hora de apertura")
    
    @classmethod
    def from_api_response(cls, api_response: List[Dict[str, Any]]) -> List["CampaignOpener"]:
        """Convertir respuesta de API a lista de CampaignOpener"""
        return [cls(**item) for item in api_response if isinstance(item, dict)]
    
    # Propiedades calculadas
    @property
    def open_date(self) -> str:
        """Extraer solo la fecha de apertura"""
        return self.open_datetime.split(" ")[0] if " " in self.open_datetime else self.open_datetime
    
    @property
    def open_time(self) -> str:
        """Extraer solo la hora de apertura"""
        return self.open_datetime.split(" ")[1] if " " in self.open_datetime else ""
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@example.com",
                "open_datetime": "2025-09-11 09:40:57"
            }
        }

class CampaignClicker(BaseModel):
    """Modelo para suscriptores que hicieron clic"""
    email: str = Field(..., description="Email del suscriptor")
    click_datetime: str = Field(..., description="Fecha y hora del clic")
    
    @classmethod
    def from_api_response(cls, api_response: List[Dict[str, Any]]) -> List["CampaignClicker"]:
        """Convertir respuesta de API a lista de CampaignClicker"""
        return [cls(**item) for item in api_response if isinstance(item, dict)]
    
    # Propiedades calculadas
    @property
    def click_date(self) -> str:
        """Extraer solo la fecha del clic"""
        return self.click_datetime.split(" ")[0] if " " in self.click_datetime else self.click_datetime
    
    @property
    def click_time(self) -> str:
        """Extraer solo la hora del clic"""
        return self.click_datetime.split(" ")[1] if " " in self.click_datetime else ""
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@example.com",
                "click_datetime": "2025-09-10 15:01:14"
            }
        }

class CampaignLink(BaseModel):
    """Modelo para enlaces de la campaña y sus estadísticas"""
    url: str = Field(..., description="URL del enlace")
    total_clics: int = Field(0, description="Total de clics en el enlace")
    unique_clics: int = Field(0, description="Clics únicos en el enlace")
    subscribers: str = Field("", description="Lista de suscriptores que hicieron clic (separados por coma)")
    
    @classmethod
    def from_api_response(cls, api_response: List[Dict[str, Any]]) -> List["CampaignLink"]:
        """Convertir respuesta de API a lista de CampaignLink"""
        return [cls(**item) for item in api_response if isinstance(item, dict)]
    
    # Propiedades calculadas
    @property
    def subscriber_list(self) -> List[str]:
        """Convertir string de suscriptores a lista limpia"""
        if not self.subscribers:
            return []
        # Limpiar la cadena: quitar espacios extras y comas al inicio/final
        clean_subscribers = self.subscribers.strip(", ")
        if not clean_subscribers:
            return []
        return [email.strip() for email in clean_subscribers.split(",") if email.strip()]
    
    @property
    def subscriber_count(self) -> int:
        """Número de suscriptores únicos que hicieron clic"""
        return len(self.subscriber_list)
    
    @property
    def click_rate_per_subscriber(self) -> float:
        """Tasa de clics por suscriptor (total_clics / unique_clics)"""
        if self.unique_clics > 0:
            return self.total_clics / self.unique_clics
        return 0.0
    
    @property
    def short_url(self) -> str:
        """Versión corta de la URL para display"""
        if len(self.url) > 50:
            return self.url[:47] + "..."
        return self.url
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com/document.pdf",
                "total_clics": 2,
                "unique_clics": 2,
                "subscribers": ", user1@example.com, user2@example.com"
            }
        }


class CampaignSoftBounce(BaseModel):
    """Modelo para soft bounces de una campaña"""
    email: str = Field(..., description="Email del suscriptor con soft bounce")
    
    @classmethod
    def from_api_response(cls, api_response: List[Dict[str, Any]]) -> List["CampaignSoftBounce"]:
        """Convertir respuesta de API a lista de CampaignSoftBounce"""
        return [cls(**item) for item in api_response if isinstance(item, dict)]
    
    @property
    def domain(self) -> str:
        """Extraer el dominio del email (ej: gmail.com)"""
        return self.email.split("@")[1] if "@" in self.email else ""
    
    @property
    def username(self) -> str:
        """Extraer el nombre de usuario del email (ej: usuario)"""
        return self.email.split("@")[0] if "@" in self.email else self.email
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@ejemplo.com"
            }
        }


class CampaignStatsByDate(BaseModel):
    """Modelo para estadísticas diarias de una campaña"""
    unopened: int = Field(0, description="Emails no abiertos")
    opened: int = Field(0, description="Emails abiertos")
    hard_bounces: int = Field(0, description="Rebotes duros")
    complaints: int = Field(0, description="Quejas/spam")
    total_sent: int = Field(0, description="Total de emails enviados")
    total_clicks: int = Field(0, description="Total de clics")
    soft_bounces: int = Field(0, description="Rebotes suaves")
    unique_clicks: int = Field(0, description="Clics únicos")
    
    @classmethod
    def from_api_response(cls, api_response: Dict[str, Any]) -> "CampaignStatsByDate":
        """Convertir respuesta de API a CampaignStatsByDate"""
        return cls(**api_response)
    
    # Propiedades calculadas
    @property
    def total_received(self) -> int:
        """Total de emails que llegaron a destino (sin bounces)"""
        return self.total_sent - self.hard_bounces - self.soft_bounces
    
    @property
    def open_rate(self) -> float:
        """Tasa de apertura (abiertos / recibidos)"""
        if self.total_received > 0:
            return (self.opened / self.total_received) * 100
        return 0.0
    
    @property
    def click_rate(self) -> float:
        """Tasa de clics (clics únicos / recibidos)"""
        if self.total_received > 0:
            return (self.unique_clicks / self.total_received) * 100
        return 0.0
    
    @property
    def bounce_rate(self) -> float:
        """Tasa total de rebotes (hard + soft / enviados)"""
        if self.total_sent > 0:
            return ((self.hard_bounces + self.soft_bounces) / self.total_sent) * 100
        return 0.0
    
    @property
    def complaint_rate(self) -> float:
        """Tasa de quejas (complaints / enviados)"""
        if self.total_sent > 0:
            return (self.complaints / self.total_sent) * 100
        return 0.0
    
    class Config:
        json_schema_extra = {
            "example": {
                "unopened": 126625,
                "opened": 6196,
                "hard_bounces": 5,
                "complaints": 0,
                "total_sent": 11751,
                "total_clicks": 370,
                "soft_bounces": 143,
                "unique_clicks": 370
            }
        }
