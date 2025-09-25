# Modelos base
from .base import (
    APIResponse,
    PaginatedResponse,
    ErrorResponse,
    HTTPMethod,
    AuthToken,
    RateLimitInfo,
    APICredentials,
    BatchOperation,
    ValidationError,
    FileUpload,
    DateRange
)

# Modelos de campañas
from .campanias import (
    CampaignStatus,
    CampaignSummary,
    CampaignBasicInfo,
    CampaignDetailedInfo,
    CampaignComplete,
    Campaign,
    CampaignCreate,
    CampaignStats,
    CampaignOpener,
    CampaignClicker,
    CampaignLink,
    CampaignSoftBounce,
    CampaignStatsByDate,
)

# Modelos de suscriptores y listas
from .suscriptores import (
    SubscriberStatus,
    FieldType,
    Suscriptor,
    SuscriptorCreate,
    SuscriptorBatch,
    Lista,
    ListaCreate,
    ListaStats,
    CampoPersonalizado,
    Segmento,
    SuscriptorInactivo
)

# Modelos de SMS
from .sms import (
    SMSStatus,
    SMSCampaign,
    SMSMessage,
    SMSBatch,
    SMSSubscriberReport,
    SMSQuickReport,
    SMSCredits,
    SMSSimpleReport,
    SMSCreate
)

# Modelos de SMTP
from .smtp import (
    EmailStatus,
    SMTPEmail,
    SMTPEmailBatch,
    SMTPEmailCreate,
    SMTPTemplate,
    SMTPCredits,
    SMTPStats,
    SMTPWebhook,
    SMTPWebhookEvent
)

# Modelos de plantillas
from .plantillas import (
    TemplateCategory,
    TemplateType,
    Plantilla,
    PlantillaCreate,
    PlantillaDuplicate,
    PlantillaUpdate,
    PlantillaPreview,
    PlantillaStats,
    PlantillaFolder,
    PlantillaVersion
)

# Modelos de webhooks
from .webhooks import (
    WebhookEventType,
    WebhookStatus,
    Webhook,
    SMTPWebhook,
    ListWebhook,
    WebhookEvent,
    WebhookCreate,
    WebhookUpdate,
    WebhookTest,
    WebhookLog,
    WebhookStats,
    WebhookSecurity
)

__all__ = [
    # Base
    "APIResponse",
    "PaginatedResponse", 
    "ErrorResponse",
    "HTTPMethod",
    "AuthToken",
    "RateLimitInfo",
    "APICredentials",
    "BatchOperation",
    "ValidationError",
    "FileUpload",
    "DateRange",
    
    # Campañas
    "CampaignStatus",
    "CampaignSummary",
    "CampaignBasicInfo",
    "CampaignDetailedInfo",
    "CampaignComplete",
    "Campaign",
    "CampaignCreate",
    "CampaignStats",
    "CampaignOpener",
    "CampaignClicker",
    "CampaignLink",
    
    # Suscriptores
    "SubscriberStatus",
    "FieldType",
    "Suscriptor",
    "SuscriptorCreate",
    "SuscriptorBatch",
    "Lista",
    "ListaCreate",
    "ListaStats",
    "CampoPersonalizado",
    "Segmento",
    "SuscriptorInactivo",
    
    # SMS
    "SMSStatus",
    "SMSCampaign",
    "SMSMessage",
    "SMSBatch",
    "SMSSubscriberReport",
    "SMSQuickReport",
    "SMSCredits",
    "SMSSimpleReport",
    "SMSCreate",
    
    # SMTP
    "EmailStatus",
    "SMTPEmail",
    "SMTPEmailBatch",
    "SMTPEmailCreate",
    "SMTPTemplate",
    "SMTPCredits",
    "SMTPStats",
    "SMTPWebhook",
    "SMTPWebhookEvent",
    
    # Plantillas
    "TemplateCategory",
    "TemplateType",
    "Plantilla",
    "PlantillaCreate",
    "PlantillaDuplicate",
    "PlantillaUpdate",
    "PlantillaPreview",
    "PlantillaStats",
    "PlantillaFolder",
    "PlantillaVersion",
    
    # Webhooks
    "WebhookEventType",
    "WebhookStatus", 
    "Webhook",
    "SMTPWebhook",
    "ListWebhook",
    "WebhookEvent",
    "WebhookCreate",
    "WebhookUpdate",
    "WebhookTest",
    "WebhookLog",
    "WebhookStats",
    "WebhookSecurity",
]