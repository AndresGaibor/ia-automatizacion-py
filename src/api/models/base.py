from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import datetime
from enum import Enum

class APIResponse(BaseModel):
    """Modelo base para respuestas de la API"""
    success: bool = Field(..., description="Indica si la operación fue exitosa")
    data: Optional[Any] = Field(None, description="Datos de respuesta")
    message: Optional[str] = Field(None, description="Mensaje informativo")
    error_code: Optional[str] = Field(None, description="Código de error si aplica")
    timestamp: Optional[datetime] = Field(None, description="Fecha y hora de la respuesta")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class PaginatedResponse(BaseModel):
    """Modelo para respuestas paginadas"""
    data: list = Field(..., description="Lista de elementos")
    total: int = Field(..., description="Total de elementos")
    page: int = Field(..., description="Página actual")
    per_page: int = Field(..., description="Elementos por página")
    total_pages: int = Field(..., description="Total de páginas")
    has_next: bool = Field(..., description="Hay página siguiente")
    has_prev: bool = Field(..., description="Hay página anterior")

class ErrorResponse(BaseModel):
    """Modelo para respuestas de error"""
    error: bool = Field(True, description="Indica que es un error")
    error_code: str = Field(..., description="Código del error")
    error_message: str = Field(..., description="Mensaje del error")
    details: Optional[Dict[str, Any]] = Field(None, description="Detalles adicionales del error")
    timestamp: datetime = Field(..., description="Fecha y hora del error")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class HTTPMethod(str, Enum):
    """Métodos HTTP permitidos"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"

class AuthToken(BaseModel):
    """Modelo para token de autenticación"""
    auth_token: str = Field(..., description="Token de autenticación de Acumbamail")
    
    class Config:
        json_schema_extra = {
            "example": {
                "auth_token": "tu_token_aqui"
            }
        }

class RateLimitInfo(BaseModel):
    """Información de límites de velocidad"""
    endpoint: str = Field(..., description="Endpoint de la API")
    limit: int = Field(..., description="Límite de peticiones")
    period: str = Field(..., description="Periodo del límite (por minuto, por segundo)")
    remaining: Optional[int] = Field(None, description="Peticiones restantes")
    reset_time: Optional[datetime] = Field(None, description="Momento de reseteo del límite")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class APICredentials(BaseModel):
    """Credenciales para la API"""
    auth_token: str = Field(..., description="Token de autenticación")
    base_url: str = Field("https://acumbamail.com/api/1/", description="URL base de la API")
    timeout: int = Field(30, description="Timeout en segundos", ge=1, le=300)
    max_retries: int = Field(3, description="Máximo número de reintentos", ge=0, le=10)
    
    class Config:
        json_schema_extra = {
            "example": {
                "auth_token": "tu_token_aqui",
                "base_url": "https://acumbamail.com/api/1/",
                "timeout": 30,
                "max_retries": 3
            }
        }

class BatchOperation(BaseModel):
    """Modelo base para operaciones en lote"""
    operation_type: str = Field(..., description="Tipo de operación")
    total_items: int = Field(..., description="Total de elementos a procesar")
    processed_items: int = Field(0, description="Elementos procesados")
    successful_items: int = Field(0, description="Elementos procesados exitosamente")
    failed_items: int = Field(0, description="Elementos que fallaron")
    
    # Información temporal
    started_at: Optional[datetime] = Field(None, description="Momento de inicio")
    finished_at: Optional[datetime] = Field(None, description="Momento de finalización")
    
    # Detalles de errores
    errors: Optional[list] = Field(None, description="Lista de errores ocurridos")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class ValidationError(BaseModel):
    """Modelo para errores de validación"""
    field: str = Field(..., description="Campo que falló la validación")
    message: str = Field(..., description="Mensaje de error")
    invalid_value: Optional[Any] = Field(None, description="Valor inválido")
    
class FileUpload(BaseModel):
    """Modelo para carga de archivos"""
    filename: str = Field(..., description="Nombre del archivo")
    content_type: str = Field(..., description="Tipo de contenido")
    size: int = Field(..., description="Tamaño en bytes")
    data: bytes = Field(..., description="Datos del archivo")
    
    class Config:
        arbitrary_types_allowed = True

class DateRange(BaseModel):
    """Modelo para rangos de fecha"""
    date_from: datetime = Field(..., description="Fecha de inicio")
    date_to: datetime = Field(..., description="Fecha de fin")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        json_schema_extra = {
            "example": {
                "date_from": "2024-01-01T00:00:00",
                "date_to": "2024-12-31T23:59:59"
            }
        }