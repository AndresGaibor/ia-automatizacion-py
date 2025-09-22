# Modelos de la API de Acumbamail

Este documento describe todos los modelos Pydantic creados para interactuar con la API de Acumbamail.

## Estructura de Modelos

### 📁 Base (`base.py`)
Modelos fundamentales para la API:

- **`APIResponse`**: Respuesta estándar de la API
- **`PaginatedResponse`**: Respuestas paginadas
- **`ErrorResponse`**: Manejo de errores
- **`AuthToken`**: Token de autenticación
- **`APICredentials`**: Credenciales completas de la API
- **`BatchOperation`**: Operaciones en lote
- **`DateRange`**: Rangos de fechas
- **`ValidationError`**: Errores de validación

### 📧 Campañas (`campanias.py`)
Modelos para gestión de campañas de email:

- **`Campaign`**: Campaña completa con estadísticas
- **`CampaignCreate`**: Crear nueva campaña
- **`CampaignStats`**: Estadísticas detalladas
- **`CampaignOpener`**: Suscriptores que abrieron
- **`CampaignClicker`**: Suscriptores que hicieron clic
- **`CampaignLink`**: Enlaces y sus estadísticas
- **`CampaignStatus`**: Estados de campaña (enum)

### 👥 Suscriptores y Listas (`suscriptores.py`)
Modelos para gestión de listas y suscriptores:

#### Suscriptores
- **`Suscriptor`**: Suscriptor completo con estadísticas
- **`SuscriptorCreate`**: Crear nuevo suscriptor
- **`SuscriptorBatch`**: Carga masiva de suscriptores
- **`SuscriptorInactivo`**: Suscriptores inactivos

#### Listas
- **`Lista`**: Lista completa con estadísticas
- **`ListaCreate`**: Crear nueva lista
- **`ListaStats`**: Estadísticas de lista

#### Campos y Segmentos
- **`CampoPersonalizado`**: Campos personalizados (merge tags)
- **`Segmento`**: Segmentos de listas
- **`FieldType`**: Tipos de campos (enum)
- **`SubscriberStatus`**: Estados de suscriptor (enum)

### 📱 SMS (`sms.py`)
Modelos para campañas y mensajes SMS:

- **`SMSCampaign`**: Campaña SMS completa
- **`SMSMessage`**: Mensaje SMS individual
- **`SMSBatch`**: Envío masivo de SMS
- **`SMSCreate`**: Crear campaña SMS
- **`SMSCredits`**: Información de créditos
- **`SMSSubscriberReport`**: Reporte por suscriptor
- **`SMSQuickReport`**: Reporte rápido
- **`SMSSimpleReport`**: Reporte simple
- **`SMSStatus`**: Estados de SMS (enum)

### 📬 SMTP - Email Transaccional (`smtp.py`)
Modelos para emails transaccionales:

- **`SMTPEmail`**: Email transaccional completo
- **`SMTPEmailCreate`**: Crear email transaccional
- **`SMTPEmailBatch`**: Envío masivo transaccional
- **`SMTPTemplate`**: Plantillas SMTP
- **`SMTPCredits`**: Créditos SMTP
- **`SMTPStats`**: Estadísticas SMTP
- **`SMTPWebhook`**: Configuración de webhook
- **`SMTPWebhookEvent`**: Eventos de webhook
- **`EmailStatus`**: Estados de email (enum)

### 🎨 Plantillas (`plantillas.py`)
Modelos para plantillas de email:

- **`Plantilla`**: Plantilla completa
- **`PlantillaCreate`**: Crear nueva plantilla
- **`PlantillaDuplicate`**: Duplicar plantilla
- **`PlantillaUpdate`**: Actualizar plantilla
- **`PlantillaPreview`**: Vista previa
- **`PlantillaStats`**: Estadísticas de uso
- **`PlantillaFolder`**: Carpetas de organización
- **`PlantillaVersion`**: Versiones de plantilla
- **`TemplateCategory`**: Categorías (enum)
- **`TemplateType`**: Tipos de plantilla (enum)

### 🔗 Webhooks (`webhooks.py`)
Modelos para configuración de webhooks:

- **`Webhook`**: Webhook base
- **`SMTPWebhook`**: Webhook específico para SMTP
- **`ListWebhook`**: Webhook específico para listas
- **`WebhookEvent`**: Eventos de webhook
- **`WebhookCreate`**: Crear webhook
- **`WebhookUpdate`**: Actualizar webhook
- **`WebhookTest`**: Probar webhook
- **`WebhookLog`**: Logs de webhook
- **`WebhookStats`**: Estadísticas de webhooks
- **`WebhookSecurity`**: Configuración de seguridad
- **`WebhookEventType`**: Tipos de eventos (enum)
- **`WebhookStatus`**: Estados de webhook (enum)

## Características de los Modelos

### ✅ Validación Automática
- **Tipos estrictos**: EmailStr, datetime, HttpUrl
- **Validaciones personalizadas**: Teléfonos, longitudes de mensaje SMS
- **Enums tipados**: Estados, categorías, tipos

### ✅ Documentación Integrada
- **Descripciones completas** en cada campo
- **Ejemplos de uso** en json_schema_extra
- **Docstrings explicativos** en cada modelo

### ✅ Configuración Avanzada
- **Encoders JSON** para datetime
- **Nombres de campos** consistentes con la API
- **Valores por defecto** apropiados

### ✅ Compatibilidad Total
- **Pydantic V2**: Última versión con mejores performances
- **API de Acumbamail**: Todos los endpoints cubiertos
- **Type hints**: Soporte completo para IDEs

## Uso Básico

```python
from src.api.models import Campaign, CampaignCreate, Lista, Suscriptor

# Crear una nueva campaña
nueva_campania = CampaignCreate(
    name="Mi Campaña",
    from_name="Mi Empresa",
    from_email="info@miempresa.com",
    subject="Asunto del email",
    content="<html><body>Contenido</body></html>",
    lists={"123": "Lista Principal"}
)

# Crear un suscriptor
nuevo_suscriptor = SuscriptorCreate(
    email="usuario@ejemplo.com",
    name="Juan Pérez",
    merge_fields={"empresa": "Mi Empresa"}
)
```

## Enums Disponibles

### Estados y Tipos
- `CampaignStatus`: Estados de campaña
- `SubscriberStatus`: Estados de suscriptor
- `SMSStatus`: Estados de SMS
- `EmailStatus`: Estados de email transaccional
- `WebhookStatus`: Estados de webhook

### Categorías y Tipos
- `TemplateCategory`: Categorías de plantillas
- `TemplateType`: Tipos de plantillas
- `FieldType`: Tipos de campos personalizados
- `WebhookEventType`: Tipos de eventos de webhook

## Integración con la API

Estos modelos están diseñados para:

1. **Serialización/Deserialización** automática con la API
2. **Validación** de datos antes del envío
3. **Type safety** en el desarrollo
4. **Documentación** automática de la API
5. **Testing** con datos consistentes

## Próximos Pasos

Con estos modelos ya puedes:

1. **Crear un cliente API** type-safe
2. **Implementar validaciones** robustas
3. **Generar documentación** automática
4. **Crear tests** consistentes
5. **Integrar con tu UI** de manera segura