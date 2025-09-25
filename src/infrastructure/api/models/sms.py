from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum

class SMSStatus(str, Enum):
    """Estados posibles de un SMS"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"

class SMSCampaign(BaseModel):
    """Modelo de campaña SMS"""
    
    # Identificación
    id: Optional[int] = Field(None, description="ID único de la campaña SMS")
    name: str = Field(..., description="Nombre de la campaña", max_length=100)
    
    # Contenido
    message: str = Field(..., description="Contenido del mensaje SMS", max_length=160)
    sender_id: Optional[str] = Field(None, description="ID del remitente", max_length=11)
    
    # Programación
    send_date: Optional[datetime] = Field(None, description="Fecha de envío programado")
    
    # Estado
    status: Optional[SMSStatus] = Field(None, description="Estado de la campaña")
    created_date: Optional[datetime] = Field(None, description="Fecha de creación")
    sent_date: Optional[datetime] = Field(None, description="Fecha de envío real")
    
    # Estadísticas
    total_recipients: Optional[int] = Field(0, description="Total de destinatarios")
    total_sent: Optional[int] = Field(0, description="Total enviados")
    total_delivered: Optional[int] = Field(0, description="Total entregados")
    total_failed: Optional[int] = Field(0, description="Total fallidos")
    
    # Costos
    cost_per_sms: Optional[float] = Field(None, description="Costo por SMS")
    total_cost: Optional[float] = Field(None, description="Costo total")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        json_schema_extra = {
            "example": {
                "name": "Campaña Promocional",
                "message": "¡Oferta especial! 20% descuento en toda la tienda. Válido hasta el 31/12.",
                "sender_id": "MiEmpresa"
            }
        }

class SMSMessage(BaseModel):
    """Modelo para mensaje SMS individual"""
    
    # Destinatario
    phone: str = Field(..., description="Número de teléfono", max_length=20)
    
    # Contenido
    message: str = Field(..., description="Contenido del mensaje", max_length=160)
    sender_id: Optional[str] = Field(None, description="ID del remitente", max_length=11)
    
    # Programación
    send_date: Optional[datetime] = Field(None, description="Fecha de envío programado")
    
    # Personalización
    merge_tags: Optional[Dict[str, str]] = Field(None, description="Variables de personalización")
    
    # Identificación
    external_id: Optional[str] = Field(None, description="ID externo para tracking", max_length=50)
    
    @validator('phone')
    def validate_phone(cls, v):
        # Validación básica de formato de teléfono
        import re
        if not re.match(r'^\+?[1-9]\d{1,14}$', v.replace(' ', '').replace('-', '')):
            raise ValueError('Formato de teléfono inválido')
        return v
    
    @validator('message')
    def validate_message_length(cls, v):
        if len(v) > 160:
            raise ValueError('El mensaje no puede exceder 160 caracteres')
        return v

class SMSBatch(BaseModel):
    """Modelo para envío masivo de SMS"""
    messages: List[SMSMessage] = Field(..., description="Lista de mensajes SMS")
    
    # Configuración común
    default_sender_id: Optional[str] = Field(None, description="Sender ID por defecto", max_length=11)
    send_date: Optional[datetime] = Field(None, description="Fecha de envío programado")
    
    @validator('messages')
    def validate_messages_count(cls, v):
        if len(v) > 1000:  # Límite razonable para batch
            raise ValueError("Máximo 1000 mensajes por lote")
        return v

class SMSSubscriberReport(BaseModel):
    """Reporte de suscriptor SMS"""
    phone: str = Field(..., description="Número de teléfono")
    status: SMSStatus = Field(..., description="Estado del SMS")
    sent_date: Optional[datetime] = Field(None, description="Fecha de envío")
    delivered_date: Optional[datetime] = Field(None, description="Fecha de entrega")
    error_message: Optional[str] = Field(None, description="Mensaje de error si aplica")
    cost: Optional[float] = Field(None, description="Costo del SMS")
    
    # Información adicional
    country_code: Optional[str] = Field(None, description="Código del país")
    carrier: Optional[str] = Field(None, description="Operador móvil")

class SMSQuickReport(BaseModel):
    """Reporte rápido de SMS"""
    phone: str = Field(..., description="Número de teléfono")
    message: str = Field(..., description="Contenido del mensaje")
    sent_date: datetime = Field(..., description="Fecha de envío")
    status: SMSStatus = Field(..., description="Estado del SMS")
    cost: Optional[float] = Field(None, description="Costo del SMS")

class SMSCredits(BaseModel):
    """Información de créditos SMS"""
    available_credits: int = Field(..., description="Créditos disponibles")
    used_credits: int = Field(0, description="Créditos utilizados")
    total_credits: int = Field(..., description="Total de créditos")
    
    # Información adicional
    credit_cost: Optional[float] = Field(None, description="Costo por crédito")
    expiration_date: Optional[datetime] = Field(None, description="Fecha de expiración")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class SMSSimpleReport(BaseModel):
    """Reporte simple de SMS"""
    sms_id: int = Field(..., description="ID del SMS")
    phone: str = Field(..., description="Número de teléfono")
    message: str = Field(..., description="Contenido del mensaje")
    status: SMSStatus = Field(..., description="Estado del SMS")
    sent_date: Optional[datetime] = Field(None, description="Fecha de envío")
    delivered_date: Optional[datetime] = Field(None, description="Fecha de entrega")
    cost: Optional[float] = Field(None, description="Costo del SMS")
    error_code: Optional[str] = Field(None, description="Código de error")
    error_message: Optional[str] = Field(None, description="Mensaje de error")

class SMSCreate(BaseModel):
    """Modelo para crear campaña SMS"""
    name: str = Field(..., description="Nombre de la campaña", max_length=100)
    message: str = Field(..., description="Contenido del mensaje", max_length=160)
    recipients: List[str] = Field(..., description="Lista de números de teléfono")
    sender_id: Optional[str] = Field(None, description="ID del remitente", max_length=11)
    send_date: Optional[datetime] = Field(None, description="Fecha de envío programado")
    
    @validator('recipients')
    def validate_recipients(cls, v):
        if len(v) == 0:
            raise ValueError("Debe especificar al menos un destinatario")
        if len(v) > 1000:
            raise ValueError("Máximo 1000 destinatarios por campaña")
        return v