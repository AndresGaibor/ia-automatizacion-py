from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum


# === MODELOS DE PARÁMETROS ===

class SubscriberData(BaseModel):
    """Datos de un suscriptor para agregar en lote"""
    email: str = Field(..., description="Email del suscriptor (requerido)")
    nombre: Optional[str] = Field(None, description="Nombre del suscriptor")
    apellidos: Optional[str] = Field(None, description="Apellidos del suscriptor")

    # Campos adicionales como Dict para flexibilidad
    class Config:
        extra = "allow"  # Permite campos adicionales

class BatchAddSubscribersRequest(BaseModel):
    """Parámetros para batchAddSubscribers"""
    list_id: int = Field(..., description="ID de la lista")
    subscribers_data: List[SubscriberData] = Field(..., description="Lista de suscriptores a agregar")
    update_subscriber: int = Field(0, description="Actualizar si existe (1=sí, 0=no)")
    complete_json: int = Field(0, description="Respuesta completa (1=sí, 0=no)")

class DeleteSubscriberRequest(BaseModel):
    """Parámetros para deleteSubscriber"""
    list_id: int = Field(..., description="ID de la lista")
    email: str = Field(..., description="Email del suscriptor a eliminar")

class GetInactiveSubscribersRequest(BaseModel):
    """Parámetros para getInactiveSubscribers"""
    date_from: str = Field(..., description="Fecha desde (formato YYYY-MM-DD)")
    date_to: str = Field(..., description="Fecha hasta (formato YYYY-MM-DD)")
    full_info: int = Field(0, description="Información completa (1=sí, 0=no)")

class GetFieldsRequest(BaseModel):
    """Parámetros para getFields"""
    list_id: int = Field(..., description="ID de la lista")

class GetMergeFieldsRequest(BaseModel):
    """Parámetros para getMergeFields"""
    list_id: int = Field(..., description="ID de la lista")

class UnsubscribeSubscriberRequest(BaseModel):
    """Parámetros para unsubscribeSubscriber"""
    list_id: int = Field(..., description="ID de la lista")
    email: str = Field(..., description="Email del suscriptor")

class BatchDeleteSubscribersRequest(BaseModel):
    """Parámetros para batchDeleteSubscribers"""
    list_id: int = Field(..., description="ID de la lista")
    email_list: Dict[str, str] = Field(..., description="Diccionario con lista de emails a eliminar")

class DeleteListRequest(BaseModel):
    """Parámetros para deleteList"""
    list_id: int = Field(..., description="ID de la lista a eliminar")


# === MODELOS DE RESPUESTA DE ENDPOINTS ===

class ListSummary(BaseModel):
    """Resumen de lista de suscriptores desde getLists"""
    id: int = Field(..., description="ID único de la lista")
    name: str = Field(..., description="Nombre de la lista")

    @classmethod
    def from_api_dict(cls, list_id: str, list_data: Any) -> "ListSummary":
        """Crear ListSummary desde el formato de API {id: datos}"""
        if isinstance(list_data, str):
            # Formato simple: {id: nombre}
            return cls(id=int(list_id), name=list_data)
        elif isinstance(list_data, dict):
            # Formato complejo: {id: {name: ..., description: ...}}
            name = list_data.get('name', str(list_data))
            return cls(id=int(list_id), name=name)
        else:
            # Fallback: usar el valor como string
            return cls(id=int(list_id), name=str(list_data))

    @classmethod
    def from_api_response(cls, api_response: Dict[str, Any]) -> List["ListSummary"]:
        """Convertir respuesta completa de API a lista de ListSummary"""
        return [cls.from_api_dict(list_id, list_data) for list_id, list_data in api_response.items()]

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1166850,
                "name": "Lista Principal"
            }
        }


class ListStats(BaseModel):
    """Estadísticas de lista desde getListStats"""
    unsubscribed_subscribers: int = Field(0, description="Suscriptores dados de baja")
    create_date: str = Field("", description="Fecha de creación")
    name: str = Field("", description="Nombre de la lista")
    spam_subscribers: int = Field(0, description="Suscriptores marcados como spam")
    total_subscribers: int = Field(0, description="Total de suscriptores")
    hard_bounced_subscribers: int = Field(0, description="Suscriptores con rebote duro")

    @classmethod
    def from_api_response(cls, api_response: Dict[str, Any]) -> "ListStats":
        """Crear ListStats desde respuesta de API"""
        return cls(**api_response)

    # Propiedades calculadas
    @property
    def active_subscribers(self) -> int:
        """Calcular suscriptores activos"""
        return self.total_subscribers - self.unsubscribed_subscribers - self.hard_bounced_subscribers - self.spam_subscribers

    @property
    def churn_rate(self) -> float:
        """Calcular tasa de abandono como porcentaje"""
        if self.total_subscribers > 0:
            churned = self.unsubscribed_subscribers + self.hard_bounced_subscribers + self.spam_subscribers
            return (churned / self.total_subscribers) * 100
        return 0.0

    class Config:
        json_schema_extra = {
            "example": {
                "unsubscribed_subscribers": 5,
                "create_date": "2025-01-15 10:30:00",
                "name": "Lista Principal",
                "spam_subscribers": 2,
                "total_subscribers": 1000,
                "hard_bounced_subscribers": 3
            }
        }


class ListFields(BaseModel):
    """Campos de lista desde getListFields"""
    fields: Any = Field(default_factory=dict, description="Campos disponibles en la lista")

    @classmethod
    def from_api_response(cls, api_response: Any) -> "ListFields":
        """Crear ListFields desde respuesta de API"""
        if isinstance(api_response, dict):
            return cls(**api_response)
        elif isinstance(api_response, list):
            # Si la respuesta es una lista de campos, guardarla directamente
            return cls(fields=api_response)
        else:
            # Fallback
            return cls(fields=api_response)

    # Propiedades calculadas
    @property
    def field_count(self) -> int:
        """Número total de campos"""
        if isinstance(self.fields, dict):
            return len(self.fields)
        elif isinstance(self.fields, list):
            return len(self.fields)
        return 0

    @property
    def field_names(self) -> List[str]:
        """Lista de nombres de campos"""
        if isinstance(self.fields, dict):
            return list(self.fields.keys())
        elif isinstance(self.fields, list):
            return [field.get('name', '') for field in self.fields if isinstance(field, dict)]
        return []

    class Config:
        json_schema_extra = {
            "example": {
                "fields": {
                    "email": {"type": "email", "required": True},
                    "name": {"type": "text", "required": False},
                    "company": {"type": "text", "required": False}
                }
            }
        }


class SubscriberDetails(BaseModel):
    """Detalles de suscriptor desde getSubscriberDetails"""
    email: str = Field("", description="Email del suscriptor")
    status: str = Field("", description="Estado del suscriptor")
    subscription_date: str = Field("", description="Fecha de suscripción")

    @classmethod
    def from_api_response(cls, api_response: Dict[str, Any]) -> "SubscriberDetails":
        """Crear SubscriberDetails desde respuesta de API"""
        # La API retorna {email: {datos}}, necesitamos extraer los datos
        if len(api_response) == 1:
            email = list(api_response.keys())[0]
            data = api_response[email]
            if isinstance(data, dict):
                # Usar create_date como subscription_date si no existe subscription_date
                subscription_date = data.get('subscription_date', data.get('create_date', ''))
                return cls(
                    email=data.get('email', email),
                    status=data.get('status', ''),
                    subscription_date=subscription_date
                )
        
        # Fallback para formato directo
        return cls(**api_response)

    # Propiedades calculadas
    @property
    def domain(self) -> str:
        """Extraer el dominio del email"""
        return self.email.split("@")[1] if "@" in self.email else ""

    @property
    def subscription_date_formatted(self) -> str:
        """Extraer solo la fecha de suscripción"""
        return self.subscription_date.split(" ")[0] if " " in self.subscription_date else self.subscription_date

    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@example.com",
                "status": "active",
                "subscription_date": "2025-01-15 10:30:00"
            }
        }


# === MODELOS DE RESPUESTA CORREGIDOS ===

class ActualSubscriber(BaseModel):
    """Modelo real de suscriptor según respuestas de API observadas"""
    email: str = Field(..., description="Email del suscriptor")
    id: int = Field(..., description="ID único del suscriptor")
    status: str = Field(..., description="Estado del suscriptor (ej: 'active')")
    create_date: str = Field(..., description="Fecha de creación (formato: 2025/09/21 19:39:26)")
    Segmentos: Optional[str] = Field(None, description="Segmentos separados por ';' (ej: 'Segmento1;Segmento2')")
    list_id: Optional[int] = Field(None, description="ID de la lista (solo en search_subscriber)")
    
    class Config:
        extra = "allow"  # Permitir campos adicionales que puedan venir de la API
        json_schema_extra = {
            "example": {
                "email": "usuario@example.com",
                "id": 5269148194,
                "status": "active",
                "create_date": "2025/09/21 19:39:26",
                "Segmentos": "Segmento1;Segmento2",
                "list_id": 1168867
            }
        }

class SubscriberSearchResult(BaseModel):
    """Resultado de búsqueda de suscriptor desde searchSubscriber - CORREGIDO"""
    # La API retorna directamente una lista, no un objeto con results
    pass

    @classmethod
    def from_api_response(cls, api_response: Any) -> List[ActualSubscriber]:
        """Crear lista de suscriptores desde respuesta de API - CORREGIDO"""
        if isinstance(api_response, list):
            # La API retorna directamente una lista de suscriptores
            return [ActualSubscriber(**item) for item in api_response]
        elif isinstance(api_response, dict):
            # Si es un dict, probablemente hay un solo resultado
            return [ActualSubscriber(**api_response)]
        else:
            return []

class SubscriberList(BaseModel):
    """Lista de suscriptores desde getSubscribers - CORREGIDO"""
    # La API retorna directamente una lista, no un objeto con subscribers
    pass

    @classmethod
    def from_api_response(cls, api_response: Any) -> List[ActualSubscriber]:
        """Crear lista de suscriptores desde respuesta de API - CORREGIDO"""
        if isinstance(api_response, list):
            # La API retorna directamente una lista de suscriptores
            return [ActualSubscriber(**item) for item in api_response]
        elif isinstance(api_response, dict):
            # Mantener compatibilidad si algún día retorna objeto
            if 'subscribers' in api_response:
                return [ActualSubscriber(**item) for item in api_response['subscribers']]
            else:
                return []
        else:
            return []


class ListSubsStats(BaseModel):
    """Estadísticas de suscriptores por campaña desde getListSubsStats"""
    subscriber_stats: List[Dict[str, Any]] = Field(default_factory=list, description="Estadísticas por suscriptor")
    block_index: int = Field(0, description="Índice de bloque actual")

    @classmethod
    def from_api_response(cls, api_response: Any) -> "ListSubsStats":
        """Crear ListSubsStats desde respuesta de API"""
        if isinstance(api_response, dict):
            return cls(**api_response)
        elif isinstance(api_response, list):
            return cls(subscriber_stats=api_response, block_index=0)
        else:
            return cls(subscriber_stats=[], block_index=0)

    @property
    def stats_count(self) -> int:
        """Número de estadísticas en este bloque"""
        return len(self.subscriber_stats)

    class Config:
        json_schema_extra = {
            "example": {
                "subscriber_stats": [
                    {"email": "user@example.com", "opens": 5, "clicks": 2},
                    {"email": "user2@example.com", "opens": 3, "clicks": 1}
                ],
                "block_index": 0
            }
        }


class FormsList(BaseModel):
    """Lista de formularios desde getForms"""
    forms: List[Dict[str, Any]] = Field(default_factory=list, description="Formularios de la lista")

    @classmethod
    def from_api_response(cls, api_response: Any) -> "FormsList":
        """Crear FormsList desde respuesta de API"""
        if isinstance(api_response, dict):
            # Si viene como {"forms": [...]}
            if "forms" in api_response:
                return cls(forms=api_response["forms"])
            else:
                # Si el dict completo son los formularios
                return cls(forms=[api_response])
        elif isinstance(api_response, list):
            return cls(forms=api_response)
        else:
            return cls(forms=[])

    @property
    def form_count(self) -> int:
        """Número de formularios disponibles"""
        return len(self.forms)

    class Config:
        json_schema_extra = {
            "example": {
                "forms": [
                    {"id": 123, "name": "Formulario de suscripción", "active": True},
                    {"id": 124, "name": "Formulario de contacto", "active": False}
                ]
            }
        }


class SegmentsList(BaseModel):
    """Lista de segmentos desde getListSegments"""
    segments: List[Dict[str, Any]] = Field(default_factory=list, description="Segmentos de la lista")

    @classmethod
    def from_api_response(cls, api_response: Any) -> "SegmentsList":
        """Crear SegmentsList desde respuesta de API"""
        if isinstance(api_response, list):
            return cls(segments=api_response)
        elif isinstance(api_response, dict):
            if "segments" in api_response:
                return cls(segments=api_response["segments"])
            else:
                return cls(segments=[api_response])
        else:
            return cls(segments=[])

    @property
    def segment_count(self) -> int:
        """Número de segmentos disponibles"""
        return len(self.segments)

    @property
    def segment_names(self) -> List[str]:
        """Lista de nombres de segmentos"""
        return [segment.get('name', '') for segment in self.segments if isinstance(segment, dict)]

    class Config:
        json_schema_extra = {
            "example": {
                "segments": [
                    {"id": 1, "name": "Segmento1", "subscriber_count": 100},
                    {"id": 2, "name": "Segmento2", "subscriber_count": 50}
                ]
            }
        }


class BatchAddResult(BaseModel):
    """Resultado de agregar suscriptores en lote desde batchAddSubscribers"""
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Resultados del proceso por suscriptor")
    success_count: int = Field(0, description="Número de suscriptores agregados exitosamente")
    error_count: int = Field(0, description="Número de errores")

    @classmethod
    def from_api_response(cls, api_response: Any) -> "BatchAddResult":
        """Crear BatchAddResult desde respuesta de API"""
        if isinstance(api_response, list):
            success_count = 0
            error_count = 0
            
            for result in api_response:
                if isinstance(result, dict):
                    # Formato con complete_json=1: {'email': '...', 'id': 123}
                    if 'id' in result:
                        success_count += 1
                    # Formato sin complete_json: {'email@domain.com': 123}
                    elif len(result) == 1 and '@' in list(result.keys())[0] and isinstance(list(result.values())[0], int):
                        success_count += 1
                    else:
                        error_count += 1
                else:
                    error_count += 1
            
            return cls(results=api_response, success_count=success_count, error_count=error_count)
        elif isinstance(api_response, dict):
            # Un solo resultado
            if 'id' in api_response:
                success = 1
            elif len(api_response) == 1 and '@' in list(api_response.keys())[0] and isinstance(list(api_response.values())[0], int):
                success = 1
            else:
                success = 0
            error = 1 - success
            return cls(results=[api_response], success_count=success, error_count=error)
        else:
            return cls(results=[], success_count=0, error_count=0)

    @property
    def total_processed(self) -> int:
        """Total de suscriptores procesados"""
        return len(self.results)

    @property
    def success_rate(self) -> float:
        """Porcentaje de éxito"""
        if self.total_processed > 0:
            return (self.success_count / self.total_processed) * 100
        return 0.0

class BatchDeleteResult(BaseModel):
    """Resultado de eliminar suscriptores en lote desde batchDeleteSubscribers"""
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Resultados del proceso por suscriptor")
    success_count: int = Field(0, description="Número de suscriptores eliminados exitosamente")
    error_count: int = Field(0, description="Número de errores")

    @classmethod
    def from_api_response(cls, api_response: Any) -> "BatchDeleteResult":
        """Crear BatchDeleteResult desde respuesta de API"""
        if isinstance(api_response, list):
            success_count = sum(1 for result in api_response if isinstance(result, dict) and result.get('success', False))
            error_count = len(api_response) - success_count
            return cls(results=api_response, success_count=success_count, error_count=error_count)
        elif isinstance(api_response, dict):
            return cls(results=[api_response], success_count=1, error_count=0)
        else:
            return cls(results=[], success_count=0, error_count=0)

    @property
    def total_processed(self) -> int:
        """Total de suscriptores procesados"""
        return len(self.results)

    @property
    def errors(self) -> List[str]:
        """Lista de errores encontrados"""
        errors = []
        for result in self.results:
            if isinstance(result, dict) and not result.get('success', False):
                errors.append(result.get('message', 'Error desconocido'))
        return errors

    @property
    def success_rate(self) -> float:
        """Porcentaje de éxito"""
        if self.total_processed > 0:
            return (self.success_count / self.total_processed) * 100
        return 0.0

    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {"email": "user1@example.com", "success": True, "id": 123},
                    {"email": "user2@example.com", "success": False, "error": "Invalid email"}
                ],
                "success_count": 1,
                "error_count": 1
            }
        }


class InactiveSubscribersList(BaseModel):
    """Lista de suscriptores inactivos desde getInactiveSubscribers"""
    inactive_subscribers: List[Dict[str, Any]] = Field(default_factory=list, description="Suscriptores inactivos")
    date_range: Dict[str, str] = Field(default_factory=dict, description="Rango de fechas consultado")

    @classmethod
    def from_api_response(cls, api_response: Any, date_from: str = "", date_to: str = "") -> "InactiveSubscribersList":
        """Crear InactiveSubscribersList desde respuesta de API"""
        if isinstance(api_response, list):
            return cls(
                inactive_subscribers=api_response,
                date_range={"from": date_from, "to": date_to}
            )
        elif isinstance(api_response, dict):
            if "inactive_subscribers" in api_response:
                return cls(
                    inactive_subscribers=api_response["inactive_subscribers"],
                    date_range={"from": date_from, "to": date_to}
                )
            else:
                return cls(
                    inactive_subscribers=[api_response],
                    date_range={"from": date_from, "to": date_to}
                )
        else:
            return cls(inactive_subscribers=[], date_range={"from": date_from, "to": date_to})

    @property
    def inactive_count(self) -> int:
        """Número de suscriptores inactivos"""
        return len(self.inactive_subscribers)

    @property
    def inactive_emails(self) -> List[str]:
        """Lista de emails inactivos"""
        return [sub.get('email', '') for sub in self.inactive_subscribers if isinstance(sub, dict)]

    class Config:
        json_schema_extra = {
            "example": {
                "inactive_subscribers": [
                    {"email": "inactive1@example.com", "last_activity": "2025-01-01", "days_inactive": 30},
                    {"email": "inactive2@example.com", "last_activity": "2025-01-02", "days_inactive": 29}
                ],
                "date_range": {"from": "2025-01-01", "to": "2025-01-31"}
            }
        }


class FieldsList(BaseModel):
    """Lista de campos desde getFields"""
    fields: Dict[str, Any] = Field(default_factory=dict, description="Campos y sus tipos")

    @classmethod
    def from_api_response(cls, api_response: Any) -> "FieldsList":
        """Crear FieldsList desde respuesta de API"""
        if isinstance(api_response, dict):
            return cls(fields=api_response)
        elif isinstance(api_response, list):
            # Convertir lista a dict usando email como clave o índice
            fields_dict = {str(i): field for i, field in enumerate(api_response)}
            return cls(fields=fields_dict)
        else:
            return cls(fields={})

    @property
    def field_count(self) -> int:
        """Número de campos disponibles"""
        return len(self.fields)

    @property
    def field_types(self) -> List[str]:
        """Lista de tipos de campos"""
        types = set()
        for field_data in self.fields.values():
            if isinstance(field_data, dict) and 'type' in field_data:
                types.add(field_data['type'])
        return list(types)

    class Config:
        json_schema_extra = {
            "example": {
                "fields": {
                    "email": {"type": "email", "required": True},
                    "name": {"type": "text", "required": False},
                    "age": {"type": "number", "required": False}
                }
            }
        }


class MergeFieldsList(BaseModel):
    """Lista de merge fields desde getMergeFields"""
    merge_fields: Dict[str, Any] = Field(default_factory=dict, description="Merge fields disponibles")

    @classmethod
    def from_api_response(cls, api_response: Any) -> "MergeFieldsList":
        """Crear MergeFieldsList desde respuesta de API"""
        if isinstance(api_response, dict):
            return cls(merge_fields=api_response)
        elif isinstance(api_response, list):
            # Convertir lista a dict usando nombre como clave
            merge_dict = {}
            for field in api_response:
                if isinstance(field, dict) and 'name' in field:
                    merge_dict[field['name']] = field
                else:
                    merge_dict[str(len(merge_dict))] = field
            return cls(merge_fields=merge_dict)
        else:
            return cls(merge_fields={})

    @property
    def merge_field_count(self) -> int:
        """Número de merge fields disponibles"""
        return len(self.merge_fields)

    @property
    def merge_field_names(self) -> List[str]:
        """Lista de nombres de merge fields"""
        return list(self.merge_fields.keys())

    class Config:
        json_schema_extra = {
            "example": {
                "merge_fields": {
                    "EMAIL": {"tag": "EMAIL", "name": "Email Address", "type": "email"},
                    "FNAME": {"tag": "FNAME", "name": "First Name", "type": "text"},
                    "LNAME": {"tag": "LNAME", "name": "Last Name", "type": "text"}
                }
            }
        }

# === MODELOS PARA PARÁMETROS DE ENTRADA ===

class CreateListRequest(BaseModel):
    """Parámetros para crear una nueva lista"""
    sender_email: EmailStr = Field(..., description="Email del remitente")
    name: str = Field(..., description="Nombre de la lista", max_length=100)
    company: str = Field(..., description="Nombre de la empresa", max_length=100)
    country: str = Field(..., description="País", max_length=50)
    city: str = Field(..., description="Ciudad", max_length=50)
    address: str = Field(..., description="Dirección", max_length=200)
    phone: str = Field(..., description="Teléfono", max_length=20)

    class Config:
        json_schema_extra = {
            "example": {
                "sender_email": "info@empresa.com",
                "name": "Lista Principal",
                "company": "Mi Empresa S.L.",
                "country": "España",
                "city": "Madrid",
                "address": "Calle Principal 123",
                "phone": "+34912345678"
            }
        }


class AddSubscriberRequest(BaseModel):
    """Parámetros para agregar un suscriptor"""
    list_id: int = Field(..., description="ID de la lista")
    merge_fields: Dict[str, Any] = Field(..., description="Campos del suscriptor (debe incluir 'email')")
    double_optin: bool = Field(True, description="Activar doble opt-in")
    update_subscriber: bool = Field(False, description="Actualizar si existe")
    complete_json: bool = Field(False, description="Respuesta completa")

    @validator('merge_fields')
    def validate_email_in_merge_fields(cls, v):
        if "email" not in v:
            raise ValueError("merge_fields debe contener el campo 'email'")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "list_id": 123456,
                "merge_fields": {
                    "email": "usuario@example.com",
                    "name": "Juan Pérez",
                    "segmentos": "VIP"
                },
                "double_optin": False,
                "update_subscriber": True,
                "complete_json": True
            }
        }


class AddMergeTagRequest(BaseModel):
    """Parámetros para agregar un campo personalizado"""
    list_id: int = Field(..., description="ID de la lista")
    field_name: str = Field(..., description="Nombre del campo", max_length=50)
    field_type: str = Field(..., description="Tipo del campo (text, number, date, etc.)")

    class Config:
        json_schema_extra = {
            "example": {
                "list_id": 123456,
                "field_name": "empresa",
                "field_type": "text"
            }
        }


# === MODELOS EXISTENTES ===

class SubscriberStatus(int, Enum):
    """Estados posibles de un suscriptor"""
    ACTIVE = 1
    UNSUBSCRIBED = 2
    BOUNCED = 3
    PENDING = 4

class FieldType(str, Enum):
    """Tipos de campos personalizados"""
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"

class Suscriptor(BaseModel):
    """Modelo de suscriptor con validación automática"""
    
    # Identificación
    id: Optional[int] = Field(None, description="ID único del suscriptor")
    email: EmailStr = Field(..., description="Email del suscriptor")
    
    # Información básica
    name: Optional[str] = Field(None, description="Nombre del suscriptor", max_length=100)
    first_name: Optional[str] = Field(None, description="Nombre", max_length=50)
    last_name: Optional[str] = Field(None, description="Apellido", max_length=50)
    phone: Optional[str] = Field(None, description="Teléfono", max_length=20)
    
    # Estado y fechas
    status: Optional[SubscriberStatus] = Field(SubscriberStatus.ACTIVE, description="Estado del suscriptor")
    subscription_date: Optional[datetime] = Field(None, description="Fecha de suscripción")
    unsubscription_date: Optional[datetime] = Field(None, description="Fecha de baja")
    last_activity: Optional[datetime] = Field(None, description="Última actividad")
    
    # Información adicional
    ip_address: Optional[str] = Field(None, description="IP de suscripción")
    country: Optional[str] = Field(None, description="País", max_length=50)
    city: Optional[str] = Field(None, description="Ciudad", max_length=50)
    source: Optional[str] = Field(None, description="Fuente de suscripción", max_length=100)
    
    # Campos personalizados
    merge_fields: Optional[Dict[str, Any]] = Field(None, description="Campos personalizados")
    
    # Estadísticas
    total_opens: Optional[int] = Field(0, description="Total de aperturas")
    total_clicks: Optional[int] = Field(0, description="Total de clics")
    last_open: Optional[datetime] = Field(None, description="Última apertura")
    last_click: Optional[datetime] = Field(None, description="Último clic")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        json_schema_extra = {
            "example": {
                "email": "usuario@ejemplo.com",
                "name": "Juan Pérez",
                "first_name": "Juan",
                "last_name": "Pérez",
                "phone": "+34600000000",
                "country": "España",
                "city": "Madrid",
                "merge_fields": {
                    "empresa": "Mi Empresa S.L.",
                    "cargo": "Gerente"
                }
            }
        }

class SuscriptorCreate(BaseModel):
    """Modelo para crear un nuevo suscriptor"""
    email: EmailStr = Field(..., description="Email del suscriptor")
    name: Optional[str] = Field(None, description="Nombre completo", max_length=100)
    first_name: Optional[str] = Field(None, description="Nombre", max_length=50)
    last_name: Optional[str] = Field(None, description="Apellido", max_length=50)
    phone: Optional[str] = Field(None, description="Teléfono", max_length=20)
    country: Optional[str] = Field(None, description="País", max_length=50)
    city: Optional[str] = Field(None, description="Ciudad", max_length=50)
    source: Optional[str] = Field(None, description="Fuente de suscripción", max_length=100)
    merge_fields: Optional[Dict[str, Any]] = Field(None, description="Campos personalizados")
    double_optin: Optional[bool] = Field(True, description="Activar doble opt-in")
    update_subscriber: Optional[bool] = Field(False, description="Actualizar si existe")

class SuscriptorBatch(BaseModel):
    """Modelo para carga masiva de suscriptores"""
    subscribers_data: List[Dict[str, Any]] = Field(..., description="Lista de datos de suscriptores")
    update_subscriber: Optional[bool] = Field(False, description="Actualizar existentes")
    complete_json: Optional[bool] = Field(False, description="Respuesta completa")
    
    @validator('subscribers_data')
    def validate_subscribers_data(cls, v):
        if len(v) > 1000:  # Límite razonable para batch
            raise ValueError("Máximo 1000 suscriptores por lote")
        
        for subscriber in v:
            if 'email' not in subscriber:
                raise ValueError("Cada suscriptor debe tener un email")
        return v

class Lista(BaseModel):
    """Modelo de lista de suscriptores"""
    
    # Identificación
    id: Optional[int] = Field(None, description="ID único de la lista")
    name: str = Field(..., description="Nombre de la lista", max_length=100)
    
    # Información del remitente
    sender_email: EmailStr = Field(..., description="Email del remitente de la lista")
    company: str = Field(..., description="Nombre de la empresa", max_length=100)
    
    # Información de contacto
    country: str = Field(..., description="País", max_length=50)
    city: str = Field(..., description="Ciudad", max_length=50)
    address: str = Field(..., description="Dirección", max_length=200)
    phone: str = Field(..., description="Teléfono", max_length=20)
    
    # Fechas
    created_date: Optional[datetime] = Field(None, description="Fecha de creación")
    updated_date: Optional[datetime] = Field(None, description="Fecha de actualización")
    
    # Estadísticas
    total_subscribers: Optional[int] = Field(0, description="Total de suscriptores")
    active_subscribers: Optional[int] = Field(0, description="Suscriptores activos")
    unsubscribed_subscribers: Optional[int] = Field(0, description="Suscriptores dados de baja")
    bounced_subscribers: Optional[int] = Field(0, description="Suscriptores con rebote")
    
    # Configuración
    double_optin: Optional[bool] = Field(True, description="Doble opt-in activado")
    welcome_email: Optional[bool] = Field(False, description="Email de bienvenida")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        json_schema_extra = {
            "example": {
                "name": "Lista Principal",
                "sender_email": "info@miempresa.com",
                "company": "Mi Empresa S.L.",
                "country": "España",
                "city": "Madrid",
                "address": "Calle Principal 123",
                "phone": "+34912345678"
            }
        }

class ListaCreate(BaseModel):
    """Modelo para crear una nueva lista"""
    name: str = Field(..., description="Nombre de la lista", max_length=100)
    sender_email: EmailStr = Field(..., description="Email del remitente")
    company: str = Field(..., description="Nombre de la empresa", max_length=100)
    country: str = Field(..., description="País", max_length=50)
    city: str = Field(..., description="Ciudad", max_length=50)
    address: str = Field(..., description="Dirección", max_length=200)
    phone: str = Field(..., description="Teléfono", max_length=20)

class ListaStats(BaseModel):
    """Estadísticas detalladas de una lista"""
    list_id: int = Field(..., description="ID de la lista")
    
    # Contadores básicos
    total_subscribers: int = Field(0, description="Total de suscriptores")
    active_subscribers: int = Field(0, description="Suscriptores activos")
    unsubscribed_subscribers: int = Field(0, description="Dados de baja")
    bounced_subscribers: int = Field(0, description="Con rebote")
    pending_subscribers: int = Field(0, description="Pendientes de confirmar")
    
    # Estadísticas temporales
    subscriptions_today: int = Field(0, description="Suscripciones hoy")
    subscriptions_this_week: int = Field(0, description="Suscripciones esta semana")
    subscriptions_this_month: int = Field(0, description="Suscripciones este mes")
    
    unsubscriptions_today: int = Field(0, description="Bajas hoy")
    unsubscriptions_this_week: int = Field(0, description="Bajas esta semana")
    unsubscriptions_this_month: int = Field(0, description="Bajas este mes")
    
    # Fechas importantes
    last_subscription: Optional[datetime] = Field(None, description="Última suscripción")
    last_unsubscription: Optional[datetime] = Field(None, description="Última baja")

class CampoPersonalizado(BaseModel):
    """Modelo para campos personalizados (merge tags)"""
    field_name: str = Field(..., description="Nombre del campo", max_length=50)
    field_type: FieldType = Field(..., description="Tipo del campo")
    field_label: Optional[str] = Field(None, description="Etiqueta del campo", max_length=100)
    required: Optional[bool] = Field(False, description="Campo obligatorio")
    default_value: Optional[str] = Field(None, description="Valor por defecto")
    
    # Para campos de selección
    options: Optional[List[str]] = Field(None, description="Opciones disponibles")
    
    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "field_name": "empresa",
                "field_type": "text",
                "field_label": "Nombre de la Empresa",
                "required": False,
                "default_value": ""
            }
        }

class Segmento(BaseModel):
    """Modelo para segmentos de listas"""
    id: Optional[int] = Field(None, description="ID único del segmento")
    name: str = Field(..., description="Nombre del segmento", max_length=100)
    list_id: int = Field(..., description="ID de la lista padre")
    
    # Criterios de segmentación
    conditions: Dict[str, Any] = Field(..., description="Condiciones del segmento")
    
    # Estadísticas
    subscriber_count: Optional[int] = Field(0, description="Número de suscriptores")
    
    # Fechas
    created_date: Optional[datetime] = Field(None, description="Fecha de creación")
    updated_date: Optional[datetime] = Field(None, description="Fecha de actualización")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class SuscriptorInactivo(BaseModel):
    """Modelo para suscriptores inactivos"""
    email: EmailStr = Field(..., description="Email del suscriptor")
    list_id: int = Field(..., description="ID de la lista")
    last_activity: Optional[datetime] = Field(None, description="Última actividad")
    days_inactive: int = Field(..., description="Días sin actividad")
    total_campaigns_received: int = Field(0, description="Campañas recibidas")
    total_opens: int = Field(0, description="Total de aperturas")
    total_clicks: int = Field(0, description="Total de clics")