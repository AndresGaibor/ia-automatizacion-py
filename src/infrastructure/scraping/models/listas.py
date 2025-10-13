from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ListScrapingData(BaseModel):
    """Modelo para datos de lista extraídos por scraping"""
    buscar: str = Field("", description="Término de búsqueda")
    nombre_lista: str = Field("", description="Nombre de la lista")
    suscriptores: str = Field("", description="Número de suscriptores")
    creacion: str = Field("", description="Fecha de creación")

    class Config:
        json_schema_extra = {
            "example": {
                "buscar": "",
                "nombre_lista": "Lista Principal",
                "suscriptores": "1250",
                "creacion": "Creada el 15/01/2024"
            }
        }

class ListTableExtraction(BaseModel):
    """Resultado de extracción de tabla de listas"""
    lists_found: List[ListScrapingData] = Field(default_factory=list, description="Listas encontradas")
    search_term_found: bool = Field(False, description="Si se encontró el término de búsqueda")
    page_processed: int = Field(1, description="Página procesada")
    extraction_successful: bool = Field(True, description="Extracción exitosa")

    @property
    def total_lists(self) -> int:
        """Total de listas extraídas"""
        return len(self.lists_found)

    class Config:
        json_schema_extra = {
            "example": {
                "lists_found": [],
                "search_term_found": False,
                "page_processed": 1,
                "extraction_successful": True
            }
        }

class ListSearchTerms(BaseModel):
    """Términos de búsqueda para listas"""
    nombre_lista: str = Field("", description="Nombre de lista a buscar")
    creacion: str = Field("", description="Fecha de creación a buscar")

    @property
    def has_search_terms(self) -> bool:
        """Indica si hay términos de búsqueda válidos"""
        return bool(self.nombre_lista.strip() or self.creacion.strip())

    @property
    def search_all(self) -> bool:
        """Indica si debe buscar todas las listas"""
        return not self.has_search_terms

    class Config:
        json_schema_extra = {
            "example": {
                "nombre_lista": "Lista Promocional",
                "creacion": "15/01/2024"
            }
        }

class ListNavigationInfo(BaseModel):
    """Información de navegación para el scraping de listas"""
    current_page: int = Field(1, description="Página actual")
    total_pages: int = Field(1, description="Total de páginas")
    navigation_successful: bool = Field(True, description="Navegación exitosa")
    lists_section_loaded: bool = Field(False, description="Sección de listas cargada")

    @property
    def progress_percentage(self) -> float:
        """Porcentaje de progreso"""
        if self.total_pages > 0:
            return (self.current_page / self.total_pages) * 100
        return 0.0

    @property
    def has_more_pages(self) -> bool:
        """Indica si hay más páginas"""
        return self.current_page < self.total_pages

    class Config:
        json_schema_extra = {
            "example": {
                "current_page": 2,
                "total_pages": 5,
                "navigation_successful": True,
                "lists_section_loaded": True
            }
        }

class ListScrapingSession(BaseModel):
    """Sesión de scraping para listas"""
    session_id: str = Field(..., description="ID único de la sesión")
    started_at: datetime = Field(default_factory=datetime.now, description="Inicio de la sesión")
    ended_at: Optional[datetime] = Field(None, description="Fin de la sesión")
    search_terms: ListSearchTerms = Field(..., description="Términos de búsqueda usados")
    total_lists_found: int = Field(0, description="Total de listas encontradas")
    pages_processed: int = Field(0, description="Páginas procesadas")
    errors_encountered: List[str] = Field(default_factory=list, description="Errores encontrados")
    status: str = Field("active", description="Estado de la sesión")

    @property
    def duration_seconds(self) -> Optional[float]:
        """Duración de la sesión en segundos"""
        if self.ended_at and self.started_at:
            return (self.ended_at - self.started_at).total_seconds()
        return None

    @property
    def average_lists_per_page(self) -> float:
        """Promedio de listas por página"""
        if self.pages_processed > 0:
            return self.total_lists_found / self.pages_processed
        return 0.0

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
                "session_id": "list_scraping_20240115_103000",
                "search_terms": {
                    "nombre_lista": "Lista Promocional",
                    "creacion": "15/01/2024"
                },
                "total_lists_found": 45,
                "pages_processed": 3,
                "errors_encountered": [],
                "status": "active"
            }
        }

class ListScrapingResult(BaseModel):
    """Resultado completo de scraping de listas"""
    lists_data: List[ListScrapingData] = Field(default_factory=list, description="Datos de listas extraídas")
    session_info: ListScrapingSession = Field(..., description="Información de la sesión")
    search_completed: bool = Field(False, description="Búsqueda completada")
    target_found: bool = Field(False, description="Objetivo de búsqueda encontrado")

    @property
    def total_lists(self) -> int:
        """Total de listas extraídas"""
        return len(self.lists_data)

    @property
    def summary(self) -> Dict[str, Any]:
        """Resumen del resultado"""
        return {
            "total_lists": self.total_lists,
            "pages_processed": self.session_info.pages_processed,
            "duration_seconds": self.session_info.duration_seconds,
            "search_completed": self.search_completed,
            "target_found": self.target_found,
            "errors_count": len(self.session_info.errors_encountered)
        }

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        json_schema_extra = {
            "example": {
                "lists_data": [],
                "session_info": {
                    "session_id": "list_scraping_20240115_103000",
                    "search_terms": {
                        "nombre_lista": "",
                        "creacion": ""
                    },
                    "total_lists_found": 45,
                    "pages_processed": 3,
                    "status": "completed"
                },
                "search_completed": True,
                "target_found": False
            }
        }

class ListExtractionConfig(BaseModel):
    """Configuración para extracción de listas"""
    max_pages: Optional[int] = Field(None, description="Máximo de páginas a procesar")
    timeout_seconds: int = Field(30, description="Timeout para operaciones")
    retry_attempts: int = Field(3, description="Intentos de reintento")

    # Configuración de búsqueda
    stop_on_target_found: bool = Field(True, description="Parar cuando se encuentre el objetivo")
    extract_all_if_no_target: bool = Field(True, description="Extraer todo si no hay objetivo")

    # Configuración de navegación
    wait_for_load: bool = Field(True, description="Esperar a que cargue la página")
    wait_time_ms: int = Field(2000, description="Tiempo de espera en milisegundos")

    class Config:
        json_schema_extra = {
            "example": {
                "max_pages": 50,
                "timeout_seconds": 30,
                "retry_attempts": 3,
                "stop_on_target_found": True,
                "extract_all_if_no_target": True,
                "wait_for_load": True,
                "wait_time_ms": 2000
            }
        }

class ListElementInfo(BaseModel):
    """Información de elementos de lista en la interfaz web"""
    element_index: int = Field(..., description="Índice del elemento")
    nombre_texto: str = Field("", description="Texto del nombre")
    suscriptores_texto: str = Field("", description="Texto de suscriptores")
    fecha_creacion_texto: str = Field("", description="Texto de fecha de creación")
    extraction_successful: bool = Field(True, description="Extracción exitosa")

    def to_list_data(self) -> ListScrapingData:
        """Convertir a ListScrapingData"""
        return ListScrapingData(
            buscar="",
            nombre_lista=self.nombre_texto,
            suscriptores=self.suscriptores_texto.replace(' suscriptores', ''),
            creacion=self.fecha_creacion_texto.replace('Creada el ', '')
        )

    class Config:
        json_schema_extra = {
            "example": {
                "element_index": 1,
                "nombre_texto": "Lista Principal",
                "suscriptores_texto": "1250 suscriptores",
                "fecha_creacion_texto": "Creada el 15/01/2024",
                "extraction_successful": True
            }
        }


# ==============================================================================
# Modelos para SUBIDA/CREACIÓN de listas
# ==============================================================================

class ListUploadColumn(BaseModel):
    """Información de una columna del archivo a subir"""
    index: int = Field(..., description="Índice de la columna")
    name: str = Field(..., description="Nombre de la columna")
    field_type: str = Field("Texto", description="Tipo de campo detectado")
    sample_value: str = Field("", description="Valor de ejemplo")

    class Config:
        json_schema_extra = {
            "example": {
                "index": 2,
                "name": "Nombre",
                "field_type": "Texto",
                "sample_value": "Juan Pérez"
            }
        }


class ListUploadConfig(BaseModel):
    """Configuración para subida de lista"""
    nombre_lista: str = Field(..., description="Nombre de la lista a crear")
    archivo_path: str = Field(..., description="Ruta del archivo Excel/CSV")
    hoja_nombre: str = Field(..., description="Nombre de la hoja a usar")
    columnas: List[ListUploadColumn] = Field(default_factory=list, description="Columnas a mapear")

    # Configuraciones opcionales
    timeout_seconds: int = Field(60, description="Timeout para operaciones")
    wait_time_ms: int = Field(2000, description="Tiempo de espera entre acciones")

    class Config:
        json_schema_extra = {
            "example": {
                "nombre_lista": "Lista Promocional 2024",
                "archivo_path": "/ruta/archivo.xlsx",
                "hoja_nombre": "Datos",
                "columnas": [],
                "timeout_seconds": 60,
                "wait_time_ms": 2000
            }
        }


class ListUploadProgress(BaseModel):
    """Progreso de subida de lista"""
    stage: str = Field("iniciando", description="Etapa actual: iniciando, navegando, creando_lista, subiendo_archivo, mapeando_campos, finalizando")
    current_column: int = Field(0, description="Columna actual siendo mapeada")
    total_columns: int = Field(0, description="Total de columnas a mapear")
    mensaje: str = Field("", description="Mensaje de progreso")
    porcentaje: float = Field(0.0, description="Porcentaje de progreso (0-100)")

    @property
    def is_complete(self) -> bool:
        """Indica si el proceso está completo"""
        return self.stage == "finalizando" and self.porcentaje >= 100.0

    class Config:
        json_schema_extra = {
            "example": {
                "stage": "mapeando_campos",
                "current_column": 3,
                "total_columns": 5,
                "mensaje": "Mapeando columna 'Teléfono'",
                "porcentaje": 60.0
            }
        }


class ListUploadSession(BaseModel):
    """Sesión de subida de lista"""
    session_id: str = Field(..., description="ID único de la sesión")
    started_at: datetime = Field(default_factory=datetime.now, description="Inicio de la sesión")
    ended_at: Optional[datetime] = Field(None, description="Fin de la sesión")
    config: ListUploadConfig = Field(..., description="Configuración de subida")
    progress: ListUploadProgress = Field(default_factory=ListUploadProgress, description="Progreso actual")
    errors_encountered: List[str] = Field(default_factory=list, description="Errores encontrados")
    status: str = Field("active", description="Estado: active, completed, failed")

    @property
    def duration_seconds(self) -> Optional[float]:
        """Duración de la sesión en segundos"""
        if self.ended_at and self.started_at:
            return (self.ended_at - self.started_at).total_seconds()
        return None

    def add_error(self, error_message: str) -> None:
        """Agregar un error a la sesión"""
        self.errors_encountered.append(f"{datetime.now().isoformat()}: {error_message}")
        self.status = "failed"

    def complete_session(self, success: bool = True) -> None:
        """Marcar la sesión como completada"""
        self.ended_at = datetime.now()
        self.status = "completed" if success else "failed"
        if success:
            self.progress.stage = "finalizando"
            self.progress.porcentaje = 100.0
            self.progress.mensaje = "Subida completada exitosamente"

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        json_schema_extra = {
            "example": {
                "session_id": "list_upload_20240115_103000",
                "config": {
                    "nombre_lista": "Lista Test",
                    "archivo_path": "/ruta/archivo.xlsx",
                    "hoja_nombre": "Datos",
                    "columnas": []
                },
                "status": "active"
            }
        }


class ListUploadResult(BaseModel):
    """Resultado de subida de lista"""
    session_info: ListUploadSession = Field(..., description="Información de la sesión")
    success: bool = Field(False, description="Subida exitosa")
    list_created: bool = Field(False, description="Lista creada")
    fields_mapped: int = Field(0, description="Campos mapeados exitosamente")
    subscribers_uploaded: bool = Field(False, description="Suscriptores subidos")
    error_message: Optional[str] = Field(None, description="Mensaje de error si falló")

    @property
    def summary(self) -> Dict[str, Any]:
        """Resumen del resultado"""
        return {
            "success": self.success,
            "list_created": self.list_created,
            "fields_mapped": self.fields_mapped,
            "subscribers_uploaded": self.subscribers_uploaded,
            "duration_seconds": self.session_info.duration_seconds,
            "errors_count": len(self.session_info.errors_encountered),
            "error_message": self.error_message
        }

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        json_schema_extra = {
            "example": {
                "session_info": {
                    "session_id": "list_upload_20240115_103000",
                    "status": "completed"
                },
                "success": True,
                "list_created": True,
                "fields_mapped": 5,
                "subscribers_uploaded": True,
                "error_message": None
            }
        }