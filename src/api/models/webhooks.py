from pydantic import BaseModel, HttpUrl, Field, validator
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum

class WebhookEventType(str, Enum):
    """Tipos de eventos de webhook"""
    # Eventos de lista
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    # Eventos de email
    DELIVERED = "delivered"
    HARD_BOUNCE = "hard_bounce"
    SOFT_BOUNCE = "soft_bounce"
    COMPLAIN = "complain"
    OPEN = "open"
    CLICK = "click"
    # Eventos de SMS
    SMS_DELIVERED = "sms_delivered"
    SMS_FAILED = "sms_failed"

class WebhookStatus(str, Enum):
    """Estados del webhook"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    SUSPENDED = "suspended"

class Webhook(BaseModel):
    """Modelo base para webhooks"""
    
    # Identificación
    id: Optional[int] = Field(None, description="ID único del webhook")
    callback_url: HttpUrl = Field(..., description="URL del webhook")
    
    # Configuración de eventos
    delivered: bool = Field(False, description="Activar evento entregado")
    hard_bounce: bool = Field(False, description="Activar rebote duro")
    soft_bounce: bool = Field(False, description="Activar rebote suave")
    complain: bool = Field(False, description="Activar quejas")
    opens: bool = Field(False, description="Activar aperturas")
    click: bool = Field(False, description="Activar clics")
    
    # Estado
    active: bool = Field(True, description="Webhook activo")
    status: Optional[WebhookStatus] = Field(WebhookStatus.ACTIVE, description="Estado del webhook")
    
    # Información adicional
    created_date: Optional[datetime] = Field(None, description="Fecha de creación")
    updated_date: Optional[datetime] = Field(None, description="Fecha de actualización")
    
    # Estadísticas
    total_calls: Optional[int] = Field(0, description="Total de llamadas realizadas")
    successful_calls: Optional[int] = Field(0, description="Llamadas exitosas")
    failed_calls: Optional[int] = Field(0, description="Llamadas fallidas")
    last_call: Optional[datetime] = Field(None, description="Última llamada")
    last_success: Optional[datetime] = Field(None, description="Último éxito")
    last_error: Optional[datetime] = Field(None, description="Último error")
    
    # Configuración avanzada
    timeout: Optional[int] = Field(30, description="Timeout en segundos", ge=1, le=300)
    retry_attempts: Optional[int] = Field(3, description="Intentos de reintento", ge=0, le=10)
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        json_schema_extra = {
            "example": {
                "callback_url": "https://miapp.com/webhook",
                "delivered": True,
                "opens": True,
                "click": True,
                "active": True
            }
        }

class SMTPWebhook(Webhook):
    """Webhook específico para SMTP"""
    
    # Eventos específicos de SMTP (hereda los básicos)
    pass

class ListWebhook(Webhook):
    """Webhook específico para listas"""
    
    # Identificación de la lista
    list_id: int = Field(..., description="ID de la lista asociada")
    
    # Eventos específicos de listas
    subscribes: bool = Field(False, description="Activar suscripciones")
    unsubscribes: bool = Field(False, description="Activar bajas")

class WebhookEvent(BaseModel):
    """Modelo para eventos de webhook"""
    
    # Identificación del evento
    event_id: Optional[str] = Field(None, description="ID único del evento")
    event_type: WebhookEventType = Field(..., description="Tipo de evento")
    
    # Información temporal
    timestamp: datetime = Field(..., description="Fecha y hora del evento")
    
    # Datos del destinatario
    email: str = Field(..., description="Email del destinatario")
    subscriber_id: Optional[int] = Field(None, description="ID del suscriptor")
    
    # Información de la campaña/lista
    campaign_id: Optional[int] = Field(None, description="ID de la campaña")
    list_id: Optional[int] = Field(None, description="ID de la lista")
    email_key: Optional[str] = Field(None, description="Clave del email (SMTP)")
    
    # Información adicional según el evento
    ip_address: Optional[str] = Field(None, description="Dirección IP")
    user_agent: Optional[str] = Field(None, description="User agent")
    country: Optional[str] = Field(None, description="País")
    city: Optional[str] = Field(None, description="Ciudad")
    
    # Para eventos de clic
    url: Optional[str] = Field(None, description="URL clicada")
    
    # Para eventos de rebote o queja
    reason: Optional[str] = Field(None, description="Razón del rebote o queja")
    error_code: Optional[str] = Field(None, description="Código de error")
    
    # Datos adicionales
    custom_data: Optional[Dict[str, Any]] = Field(None, description="Datos personalizados")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class WebhookCreate(BaseModel):
    """Modelo para crear un webhook"""
    callback_url: HttpUrl = Field(..., description="URL del webhook")
    
    # Configuración de eventos
    delivered: Optional[bool] = Field(False, description="Activar evento entregado")
    hard_bounce: Optional[bool] = Field(False, description="Activar rebote duro")
    soft_bounce: Optional[bool] = Field(False, description="Activar rebote suave")
    complain: Optional[bool] = Field(False, description="Activar quejas")
    opens: Optional[bool] = Field(False, description="Activar aperturas")
    click: Optional[bool] = Field(False, description="Activar clics")
    
    # Para webhooks de lista
    subscribes: Optional[bool] = Field(False, description="Activar suscripciones")
    unsubscribes: Optional[bool] = Field(False, description="Activar bajas")
    
    # Estado
    active: Optional[bool] = Field(True, description="Webhook activo")
    
    # Configuración avanzada
    timeout: Optional[int] = Field(30, description="Timeout en segundos", ge=1, le=300)
    retry_attempts: Optional[int] = Field(3, description="Intentos de reintento", ge=0, le=10)

class WebhookUpdate(BaseModel):
    """Modelo para actualizar un webhook"""
    callback_url: Optional[HttpUrl] = Field(None, description="Nueva URL del webhook")
    
    # Configuración de eventos
    delivered: Optional[bool] = Field(None, description="Activar evento entregado")
    hard_bounce: Optional[bool] = Field(None, description="Activar rebote duro")
    soft_bounce: Optional[bool] = Field(None, description="Activar rebote suave")
    complain: Optional[bool] = Field(None, description="Activar quejas")
    opens: Optional[bool] = Field(None, description="Activar aperturas")
    click: Optional[bool] = Field(None, description="Activar clics")
    subscribes: Optional[bool] = Field(None, description="Activar suscripciones")
    unsubscribes: Optional[bool] = Field(None, description="Activar bajas")
    
    # Estado
    active: Optional[bool] = Field(None, description="Webhook activo")
    
    # Configuración avanzada
    timeout: Optional[int] = Field(None, description="Timeout en segundos", ge=1, le=300)
    retry_attempts: Optional[int] = Field(None, description="Intentos de reintento", ge=0, le=10)

class WebhookTest(BaseModel):
    """Modelo para probar un webhook"""
    callback_url: HttpUrl = Field(..., description="URL del webhook a probar")
    event_type: WebhookEventType = Field(..., description="Tipo de evento de prueba")
    test_data: Optional[Dict[str, Any]] = Field(None, description="Datos de prueba personalizados")

class WebhookLog(BaseModel):
    """Modelo para logs de webhook"""
    
    # Identificación
    id: Optional[int] = Field(None, description="ID único del log")
    webhook_id: int = Field(..., description="ID del webhook")
    
    # Información del evento
    event_type: WebhookEventType = Field(..., description="Tipo de evento")
    attempt_number: int = Field(..., description="Número de intento")
    
    # Información de la llamada
    call_date: datetime = Field(..., description="Fecha y hora de la llamada")
    response_code: Optional[int] = Field(None, description="Código de respuesta HTTP")
    response_time: Optional[float] = Field(None, description="Tiempo de respuesta en ms")
    
    # Datos enviados y recibidos
    request_payload: Optional[Dict[str, Any]] = Field(None, description="Datos enviados")
    response_body: Optional[str] = Field(None, description="Respuesta recibida")
    
    # Estado
    success: bool = Field(..., description="Llamada exitosa")
    error_message: Optional[str] = Field(None, description="Mensaje de error")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class WebhookStats(BaseModel):
    """Estadísticas de webhooks"""
    
    # Periodo
    date_from: datetime = Field(..., description="Fecha inicio del periodo")
    date_to: datetime = Field(..., description="Fecha fin del periodo")
    
    # Estadísticas generales
    total_webhooks: int = Field(0, description="Total de webhooks configurados")
    active_webhooks: int = Field(0, description="Webhooks activos")
    
    # Estadísticas de llamadas
    total_calls: int = Field(0, description="Total de llamadas")
    successful_calls: int = Field(0, description="Llamadas exitosas")
    failed_calls: int = Field(0, description="Llamadas fallidas")
    
    # Porcentajes
    success_rate: Optional[float] = Field(None, description="Tasa de éxito (%)")
    
    # Por tipo de evento
    calls_by_event: Optional[Dict[str, int]] = Field(None, description="Llamadas por tipo de evento")
    
    # Estadísticas de rendimiento
    average_response_time: Optional[float] = Field(None, description="Tiempo promedio de respuesta (ms)")
    fastest_response: Optional[float] = Field(None, description="Respuesta más rápida (ms)")
    slowest_response: Optional[float] = Field(None, description="Respuesta más lenta (ms)")

class WebhookSecurity(BaseModel):
    """Configuración de seguridad para webhooks"""
    webhook_id: int = Field(..., description="ID del webhook")
    
    # Autenticación
    secret_key: Optional[str] = Field(None, description="Clave secreta para firma")
    use_signature: bool = Field(False, description="Usar firma de seguridad")
    
    # Headers personalizados
    custom_headers: Optional[Dict[str, str]] = Field(None, description="Headers personalizados")
    
    # Restricciones de IP
    allowed_ips: Optional[List[str]] = Field(None, description="IPs permitidas")
    
    # SSL
    verify_ssl: bool = Field(True, description="Verificar certificado SSL")
    
    class Config:
        json_schema_extra = {
            "example": {
                "webhook_id": 123,
                "use_signature": True,
                "custom_headers": {
                    "Authorization": "Bearer token123",
                    "X-Custom-Header": "value"
                },
                "verify_ssl": True
            }
        }