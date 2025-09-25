from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum

class TemplateCategory(str, Enum):
    """Categorías de plantillas"""
    NEWSLETTER = "newsletter"
    PROMOTIONAL = "promotional"
    TRANSACTIONAL = "transactional"
    WELCOME = "welcome"
    ABANDONED_CART = "abandoned_cart"
    CONFIRMATION = "confirmation"
    CUSTOM = "custom"

class TemplateType(str, Enum):
    """Tipos de plantillas"""
    HTML = "html"
    BEE = "bee"
    DRAG_DROP = "drag_drop"
    TEXT = "text"

class Plantilla(BaseModel):
    """Modelo de plantilla de email"""
    
    # Identificación
    id: Optional[int] = Field(None, description="ID único de la plantilla")
    template_name: str = Field(..., description="Nombre de la plantilla", max_length=100)
    
    # Contenido
    html_content: str = Field(..., description="Contenido HTML de la plantilla")
    text_content: Optional[str] = Field(None, description="Contenido de texto plano")
    subject: Optional[str] = Field(None, description="Asunto predeterminado", max_length=255)
    
    # Categorización
    category: Optional[TemplateCategory] = Field(None, description="Categoría de la plantilla")
    custom_category: Optional[str] = Field(None, description="Categoría personalizada", max_length=50)
    
    # Tipo y configuración
    template_type: Optional[TemplateType] = Field(TemplateType.HTML, description="Tipo de plantilla")
    bee_json: Optional[Dict[str, Any]] = Field(None, description="Configuración BEE editor")
    
    # Variables y personalización
    merge_tags: Optional[List[str]] = Field(None, description="Variables disponibles")
    dynamic_content: Optional[Dict[str, Any]] = Field(None, description="Contenido dinámico")
    
    # Fechas
    created_date: Optional[datetime] = Field(None, description="Fecha de creación")
    updated_date: Optional[datetime] = Field(None, description="Fecha de actualización")
    last_used: Optional[datetime] = Field(None, description="Última vez utilizada")
    
    # Estadísticas de uso
    usage_count: Optional[int] = Field(0, description="Número de veces utilizada")
    
    # Configuración de diseño
    design_settings: Optional[Dict[str, Any]] = Field(None, description="Configuraciones de diseño")
    
    # Información adicional
    description: Optional[str] = Field(None, description="Descripción de la plantilla", max_length=500)
    tags: Optional[List[str]] = Field(None, description="Etiquetas para organización")
    
    # Estado
    is_active: Optional[bool] = Field(True, description="Plantilla activa")
    is_public: Optional[bool] = Field(False, description="Plantilla pública")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        json_schema_extra = {
            "example": {
                "template_name": "Newsletter Mensual",
                "html_content": "<html><body><h1>{{titulo}}</h1><p>{{contenido}}</p></body></html>",
                "subject": "Newsletter {{mes}} - {{empresa}}",
                "category": "newsletter",
                "merge_tags": ["titulo", "contenido", "mes", "empresa"],
                "description": "Plantilla para newsletter mensual con contenido personalizable"
            }
        }

class PlantillaCreate(BaseModel):
    """Modelo para crear una nueva plantilla"""
    template_name: str = Field(..., description="Nombre de la plantilla", max_length=100)
    html_content: str = Field(..., description="Contenido HTML")
    text_content: Optional[str] = Field(None, description="Contenido de texto plano")
    subject: Optional[str] = Field(None, description="Asunto predeterminado", max_length=255)
    category: Optional[TemplateCategory] = Field(None, description="Categoría de la plantilla")
    custom_category: Optional[str] = Field(None, description="Categoría personalizada", max_length=50)
    template_type: Optional[TemplateType] = Field(TemplateType.HTML, description="Tipo de plantilla")
    bee_json: Optional[Dict[str, Any]] = Field(None, description="Configuración BEE editor")
    description: Optional[str] = Field(None, description="Descripción", max_length=500)
    tags: Optional[List[str]] = Field(None, description="Etiquetas")
    is_public: Optional[bool] = Field(False, description="Plantilla pública")

class PlantillaDuplicate(BaseModel):
    """Modelo para duplicar una plantilla"""
    template_name: str = Field(..., description="Nombre de la nueva plantilla", max_length=100)
    origin_template_id: int = Field(..., description="ID de la plantilla origen")
    
    # Modificaciones opcionales
    new_category: Optional[TemplateCategory] = Field(None, description="Nueva categoría")
    new_description: Optional[str] = Field(None, description="Nueva descripción", max_length=500)
    new_tags: Optional[List[str]] = Field(None, description="Nuevas etiquetas")

class PlantillaUpdate(BaseModel):
    """Modelo para actualizar una plantilla"""
    template_name: Optional[str] = Field(None, description="Nuevo nombre", max_length=100)
    html_content: Optional[str] = Field(None, description="Nuevo contenido HTML")
    text_content: Optional[str] = Field(None, description="Nuevo contenido de texto")
    subject: Optional[str] = Field(None, description="Nuevo asunto", max_length=255)
    category: Optional[TemplateCategory] = Field(None, description="Nueva categoría")
    custom_category: Optional[str] = Field(None, description="Nueva categoría personalizada")
    bee_json: Optional[Dict[str, Any]] = Field(None, description="Nueva configuración BEE")
    description: Optional[str] = Field(None, description="Nueva descripción", max_length=500)
    tags: Optional[List[str]] = Field(None, description="Nuevas etiquetas")
    is_active: Optional[bool] = Field(None, description="Estado activo")
    is_public: Optional[bool] = Field(None, description="Plantilla pública")

class PlantillaPreview(BaseModel):
    """Modelo para vista previa de plantilla"""
    template_id: int = Field(..., description="ID de la plantilla")
    merge_tags: Optional[Dict[str, str]] = Field(None, description="Valores para las variables")
    preview_email: Optional[str] = Field(None, description="Email para envío de prueba")
    
    # Configuración de vista previa
    device_type: Optional[str] = Field("desktop", description="Tipo de dispositivo (desktop, mobile, tablet)")
    email_client: Optional[str] = Field("generic", description="Cliente de email")

class PlantillaStats(BaseModel):
    """Estadísticas de uso de plantilla"""
    template_id: int = Field(..., description="ID de la plantilla")
    
    # Uso básico
    total_campaigns: int = Field(0, description="Total de campañas que la han usado")
    total_emails_sent: int = Field(0, description="Total de emails enviados")
    
    # Fechas importantes
    first_used: Optional[datetime] = Field(None, description="Primera vez utilizada")
    last_used: Optional[datetime] = Field(None, description="Última vez utilizada")
    
    # Estadísticas de rendimiento
    average_open_rate: Optional[float] = Field(None, description="Tasa promedio de apertura")
    average_click_rate: Optional[float] = Field(None, description="Tasa promedio de clics")
    
    # Uso por periodo
    usage_this_month: int = Field(0, description="Uso este mes")
    usage_last_month: int = Field(0, description="Uso el mes pasado")
    
    # Campañas exitosas
    successful_campaigns: int = Field(0, description="Campañas exitosas")
    failed_campaigns: int = Field(0, description="Campañas fallidas")

class PlantillaFolder(BaseModel):
    """Modelo para carpetas de plantillas"""
    id: Optional[int] = Field(None, description="ID de la carpeta")
    name: str = Field(..., description="Nombre de la carpeta", max_length=100)
    description: Optional[str] = Field(None, description="Descripción", max_length=500)
    parent_id: Optional[int] = Field(None, description="ID de la carpeta padre")
    
    # Contenido
    template_count: Optional[int] = Field(0, description="Número de plantillas")
    subfolder_count: Optional[int] = Field(0, description="Número de subcarpetas")
    
    # Fechas
    created_date: Optional[datetime] = Field(None, description="Fecha de creación")
    updated_date: Optional[datetime] = Field(None, description="Fecha de actualización")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class PlantillaVersion(BaseModel):
    """Modelo para versiones de plantilla"""
    id: Optional[int] = Field(None, description="ID de la versión")
    template_id: int = Field(..., description="ID de la plantilla padre")
    version_number: int = Field(..., description="Número de versión")
    
    # Contenido de la versión
    html_content: str = Field(..., description="Contenido HTML de esta versión")
    subject: Optional[str] = Field(None, description="Asunto de esta versión")
    
    # Información de la versión
    created_date: datetime = Field(..., description="Fecha de creación de la versión")
    created_by: Optional[str] = Field(None, description="Usuario que creó la versión")
    comment: Optional[str] = Field(None, description="Comentario de la versión", max_length=500)
    
    # Estado
    is_current: bool = Field(False, description="Es la versión actual")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }