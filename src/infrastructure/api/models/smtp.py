from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class EmailStatus(int, Enum):
    """Estados posibles de un email transaccional"""
    PENDING = 0
    SENT = 1
    DELIVERED = 2
    OPENED = 3
    CLICKED = 4
    BOUNCED = 5
    COMPLAINED = 6
    UNSUBSCRIBED = 7
    FAILED = 8

class SMTPEmail(BaseModel):
    """Modelo para email transaccional individual"""
    
    # Identificación
    email_key: Optional[str] = Field(None, description="Clave única del email")
    
    # Remitente y destinatarios
    from_email: EmailStr = Field(..., description="Email del remitente")
    from_name: Optional[str] = Field(None, description="Nombre del remitente", max_length=100)
    to_email: EmailStr = Field(..., description="Email del destinatario")
    to_name: Optional[str] = Field(None, description="Nombre del destinatario", max_length=100)
    
    # Destinatarios adicionales
    cc_email: Optional[EmailStr] = Field(None, description="Email con copia")
    bcc_email: Optional[EmailStr] = Field(None, description="Email con copia oculta")
    
    # Contenido
    subject: str = Field(..., description="Asunto del email", max_length=255)
    body: str = Field(..., description="Cuerpo del email (HTML o texto)")
    
    # Plantilla
    template_id: Optional[str] = Field(None, description="ID de la plantilla")
    merge_tags: Optional[Dict[str, Any]] = Field(None, description="Variables de personalización")
    
    # Programación
    program_date: Optional[datetime] = Field(None, description="Fecha de envío programado")
    
    # Categorización
    category: Optional[str] = Field(None, description="Categoría del email", max_length=50)
    
    # Estado y seguimiento
    status: Optional[EmailStatus] = Field(None, description="Estado del email")
    sent_date: Optional[datetime] = Field(None, description="Fecha de envío")
    delivered_date: Optional[datetime] = Field(None, description="Fecha de entrega")
    opened_date: Optional[datetime] = Field(None, description="Fecha de apertura")
    clicked_date: Optional[datetime] = Field(None, description="Fecha de clic")
    
    # Adjuntos
    attachments: Optional[List[Dict[str, str]]] = Field(None, description="Lista de adjuntos")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        json_schema_extra = {
            "example": {
                "from_email": "noreply@miempresa.com",
                "from_name": "Mi Empresa",
                "to_email": "cliente@ejemplo.com",
                "to_name": "Juan Pérez",
                "subject": "Confirmación de pedido #12345",
                "body": "<html><body><h1>Gracias por tu pedido</h1></body></html>",
                "category": "transaccional"
            }
        }

class SMTPEmailBatch(BaseModel):
    """Modelo para envío masivo de emails transaccionales"""
    messages: List[SMTPEmail] = Field(..., description="Lista de emails a enviar")
    
    @validator('messages')
    def validate_messages_count(cls, v):
        if len(v) > 100:  # Límite razonable para emails transaccionales
            raise ValueError("Máximo 100 emails por lote")
        return v

class SMTPEmailCreate(BaseModel):
    """Modelo para crear un email transaccional"""
    from_email: EmailStr = Field(..., description="Email del remitente")
    from_name: Optional[str] = Field(None, description="Nombre del remitente", max_length=100)
    to_email: EmailStr = Field(..., description="Email del destinatario")
    to_name: Optional[str] = Field(None, description="Nombre del destinatario", max_length=100)
    cc_email: Optional[EmailStr] = Field(None, description="Email con copia")
    bcc_email: Optional[EmailStr] = Field(None, description="Email con copia oculta")
    subject: str = Field(..., description="Asunto del email", max_length=255)
    body: str = Field(..., description="Cuerpo del email")
    template_id: Optional[str] = Field(None, description="ID de la plantilla")
    merge_tags: Optional[Dict[str, Any]] = Field(None, description="Variables de personalización")
    program_date: Optional[datetime] = Field(None, description="Fecha de envío programado")
    category: Optional[str] = Field(None, description="Categoría del email", max_length=50)
    attachments: Optional[List[Dict[str, str]]] = Field(None, description="Lista de adjuntos")

class SMTPTemplate(BaseModel):
    """Modelo para plantilla SMTP"""
    id: Optional[str] = Field(None, description="ID único de la plantilla")
    name: str = Field(..., description="Nombre de la plantilla", max_length=100)
    subject: str = Field(..., description="Asunto de la plantilla", max_length=255)
    html_content: str = Field(..., description="Contenido HTML de la plantilla")
    text_content: Optional[str] = Field(None, description="Contenido de texto plano")
    
    # Variables disponibles
    merge_tags: Optional[List[str]] = Field(None, description="Variables disponibles en la plantilla")
    
    # Fechas
    created_date: Optional[datetime] = Field(None, description="Fecha de creación")
    updated_date: Optional[datetime] = Field(None, description="Fecha de actualización")
    
    # Categorización
    category: Optional[str] = Field(None, description="Categoría de la plantilla", max_length=50)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class SMTPCredits(BaseModel):
    """Información de créditos SMTP"""
    available_credits: int = Field(..., description="Créditos SMTP disponibles")
    used_credits: int = Field(0, description="Créditos utilizados")
    total_credits: int = Field(..., description="Total de créditos")
    
    # Información adicional
    credit_cost: Optional[float] = Field(None, description="Costo por crédito")
    expiration_date: Optional[datetime] = Field(None, description="Fecha de expiración")
    monthly_limit: Optional[int] = Field(None, description="Límite mensual")
    monthly_used: Optional[int] = Field(None, description="Utilizados este mes")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class SMTPStats(BaseModel):
    """Estadísticas SMTP"""
    
    # Periodo
    date_from: datetime = Field(..., description="Fecha inicio del periodo")
    date_to: datetime = Field(..., description="Fecha fin del periodo")
    
    # Contadores básicos
    total_sent: int = Field(0, description="Total enviados")
    total_delivered: int = Field(0, description="Total entregados")
    total_opened: int = Field(0, description="Total abiertos")
    total_clicked: int = Field(0, description="Total con clic")
    total_bounced: int = Field(0, description="Total rebotados")
    total_complained: int = Field(0, description="Total con quejas")
    total_unsubscribed: int = Field(0, description="Total dados de baja")
    total_failed: int = Field(0, description="Total fallidos")
    
    # Porcentajes
    delivery_rate: Optional[float] = Field(None, description="Tasa de entrega (%)")
    open_rate: Optional[float] = Field(None, description="Tasa de apertura (%)")
    click_rate: Optional[float] = Field(None, description="Tasa de clic (%)")
    bounce_rate: Optional[float] = Field(None, description="Tasa de rebote (%)")
    complaint_rate: Optional[float] = Field(None, description="Tasa de quejas (%)")
    
    # Por categoría
    stats_by_category: Optional[Dict[str, Dict[str, int]]] = Field(None, description="Estadísticas por categoría")

class SMTPWebhook(BaseModel):
    """Configuración de webhook SMTP"""
    callback_url: str = Field(..., description="URL del webhook")
    
    # Eventos activados
    delivered: bool = Field(False, description="Activar evento entregado")
    hard_bounce: bool = Field(False, description="Activar rebote duro")
    soft_bounce: bool = Field(False, description="Activar rebote suave")
    complain: bool = Field(False, description="Activar quejas")
    opens: bool = Field(False, description="Activar aperturas")
    click: bool = Field(False, description="Activar clics")
    
    # Estado
    active: bool = Field(True, description="Webhook activo")
    
    # Información adicional
    created_date: Optional[datetime] = Field(None, description="Fecha de creación")
    last_call: Optional[datetime] = Field(None, description="Última llamada")
    total_calls: Optional[int] = Field(0, description="Total de llamadas")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class SMTPWebhookEvent(BaseModel):
    """Evento de webhook SMTP"""
    event_type: str = Field(..., description="Tipo de evento")
    email_key: str = Field(..., description="Clave del email")
    email: EmailStr = Field(..., description="Email del destinatario")
    timestamp: datetime = Field(..., description="Fecha y hora del evento")
    
    # Información adicional según el evento
    ip_address: Optional[str] = Field(None, description="Dirección IP")
    user_agent: Optional[str] = Field(None, description="User agent")
    url: Optional[str] = Field(None, description="URL clicada (para eventos de clic)")
    reason: Optional[str] = Field(None, description="Razón del rebote o queja")
    
    # Información geográfica
    country: Optional[str] = Field(None, description="País")
    city: Optional[str] = Field(None, description="Ciudad")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }