# Documentación API Acumbamail

## Información General

### Endpoint Base
- **URL Base:** `https://acumbamail.com/api/1/(nombreFuncion)/`
- **Formato:** REST API
- **Métodos:** POST (recomendado) y GET

### Autenticación
- **Requerimiento:** Todas las llamadas requieren `auth_token`
- **Seguridad:** El token es exclusivo de cada cuenta y no debe compartirse
- **Inclusión:** Debe incluirse en todas las peticiones

### Formatos de Respuesta
- **JSON** (por defecto)
- **XML**
- **Parámetro:** `response_type` con valores 'json' o 'xml'

### Códigos de Estado HTTP
- **200:** Consulta exitosa
- **201:** Datos modificados correctamente
- **400:** Petición incorrecta (argumentos incorrectos)
- **401:** No autorizado (autenticación incorrecta)
- **429:** Rate limiting (demasiadas peticiones)
- **500:** Error del servidor

### Parámetros Especiales
- **Diccionarios en GET:** `dict[key]=value&dict[key1]=value1`
- **POST:** Parámetros en el body como form-data

---

## 1. CAMPAÑAS DE EMAIL

### Creación y Envío

#### createCampaign
```
POST /api/1/createCampaign/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `name` (string): Nombre de la campaña
- `from_name` (string): Nombre del remitente
- `from_email` (string): Email del remitente
- `subject` (string): Asunto del email
- `content` (string): Contenido HTML del email
- `lists` (dict): Listas destinatarias
- `date_send` (date): Fecha de envío programado
- `tracking_urls` (integer): Activar seguimiento de URLs
- `complete_json` (integer): Respuesta completa en JSON
- `https` (integer): Usar HTTPS

**Retorna:** integer (ID de campaña)
**Límite:** 10 peticiones/minuto

#### sendTemplateCampaign
```
POST /api/1/sendTemplateCampaign/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `name` (string): Nombre de la campaña
- `from_name` (string): Nombre del remitente
- `from_email` (string): Email del remitente
- `subject` (string): Asunto
- `template_id` (integer): ID de la plantilla
- `lists` (dict): Listas destinatarias
- `date_send` (date): Fecha de envío
- `https` (integer): Usar HTTPS

**Retorna:** integer (ID de campaña)
**Límite:** 10 peticiones/minuto

#### createTemplate
```
POST /api/1/createTemplate/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `template_name` (string): Nombre de la plantilla
- `html_content` (string): Contenido HTML
- `id` (number): ID de plantilla (opcional)
- `custom_category` (string): Categoría personalizada
- `subject` (string): Asunto predeterminado
- `bee_json` (dict): Configuración BEE editor

**Retorna:** string (ID de plantilla)
**Límite:** 10 peticiones/minuto

#### duplicateTemplate
```
POST /api/1/duplicateTemplate/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `template_name` (string): Nombre nueva plantilla
- `origin_template_id` (string): ID plantilla origen

**Retorna:** integer (ID nueva plantilla)
**Límite:** 10 peticiones/minuto

### Obtención de Información

#### getCampaigns
```
GET /api/1/getCampaigns/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `complete_json` (integer): Información completa

**Retorna:** dict (lista de campañas)
**Límite:** 10 peticiones/minuto

#### getCampaignBasicInformation
```
GET /api/1/getCampaignBasicInformation/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `campaign_id` (integer): ID de la campaña

**Retorna:** dict (información básica)
**Límite:** 10 peticiones/minuto

#### getCampaignTotalInformation
```
GET /api/1/getCampaignTotalInformation/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `campaign_id` (integer): ID de la campaña

**Retorna:** dict (información completa)
**Límite:** 10 peticiones/minuto

### Estadísticas de Interacción

#### getCampaignOpeners
```
GET /api/1/getCampaignOpeners/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `campaign_id` (integer): ID de la campaña

**Retorna:** dict (suscriptores que abrieron y fechas)
**Límite:** 10 peticiones/minuto

#### getCampaignClicks
```
GET /api/1/getCampaignClicks/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `campaign_id` (integer): ID de la campaña

**Retorna:** dict (suscriptores que hicieron clic y fechas)
**Límite:** 10 peticiones/minuto

#### getCampaignLinks
```
GET /api/1/getCampaignLinks/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `campaign_id` (integer): ID de la campaña

**Retorna:** dict (enlaces y clics por cada uno)
**Límite:** 10 peticiones/minuto

#### getCampaignSoftBounces
```
GET /api/1/getCampaignSoftBounces/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `campaign_id` (integer): ID de la campaña

**Retorna:** dict (soft bounces)
**Límite:** 10 peticiones/minuto

### Análisis Avanzado

#### getCampaignInformationByISP
```
GET /api/1/getCampaignInformationByISP/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `campaign_id` (integer): ID de la campaña

**Retorna:** dict (información por ISP)
**Límite:** 10 peticiones/minuto

#### getCampaignOpenersByCountries
```
GET /api/1/getCampaignOpenersByCountries/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `campaign_id` (integer): ID de la campaña

**Retorna:** dict (aperturas por país)
**Límite:** 10 peticiones/minuto

#### getCampaignOpenersByBrowser
```
GET /api/1/getCampaignOpenersByBrowser/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `campaign_id` (integer): ID de la campaña

**Retorna:** dict (aperturas por navegador)
**Límite:** 10 peticiones/minuto

#### getCampaignOpenersByOs
```
GET /api/1/getCampaignOpenersByOs/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `campaign_id` (integer): ID de la campaña

**Retorna:** dict (aperturas por sistema operativo)
**Límite:** 10 peticiones/minuto

#### getStatsByDate
```
GET /api/1/getStatsByDate/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `list_id` (integer): ID de la lista
- `date_from` (date): Fecha inicio
- `date_to` (date): Fecha fin

**Retorna:** dict (estadísticas agrupadas)
**Límite:** 10 peticiones/minuto

#### getTemplates
```
GET /api/1/getTemplates/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación

**Retorna:** dict (plantillas disponibles)
**Límite:** 1 petición/segundo

---

## 2. SMS

### sendSMS
```
POST /api/1/sendSMS/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `messages` (JSON): Mensajes a enviar

**Retorna:** JSON (resultado del envío)

### getCreditsSMS
```
GET /api/1/getCreditsSMS/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación

**Retorna:** string (créditos disponibles)
**Límite:** 10 peticiones/minuto

### getSMSCampaigns
```
GET /api/1/getSMSCampaigns/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `start_date` (date): Fecha inicio (opcional)
- `end_date` (date): Fecha fin (opcional)

**Retorna:** json (lista de campañas SMS)
**Límite:** 10 peticiones/minuto

### getSMSSubscriberReport
```
GET /api/1/getSMSSubscriberReport/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `sms_campaign_id` (integer): ID de campaña SMS

**Retorna:** list (detalle de receptores)
**Límite:** 10 peticiones/minuto

### getSMSQuickSubscriberReport
```
GET /api/1/getSMSQuickSubscriberReport/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `start_date` (date): Fecha inicio
- `end_date` (date): Fecha fin

**Retorna:** list (receptores de envíos rápidos)
**Límite:** 10 peticiones/minuto

### getSMSSimpleReport
```
GET /api/1/getSMSSimpleReport/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `sms_id` (integer): ID del SMS

**Retorna:** json (información del SMS)

---

## 3. SMTP (Email Transaccional)

### send
```
POST /api/1/send/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `messages` (dict): Mensajes a enviar

**Retorna:** list (resultados del envío)

### sendOne
```
POST /api/1/sendOne/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `from_email` (string): Email remitente
- `to_email` (string): Email destinatario
- `cc_email` (string, opcional): Con copia
- `bcc_email` (string, opcional): Con copia oculta
- `body` (string): Cuerpo del email
- `template_id` (string, opcional): ID de plantilla
- `merge_tags` (dict, opcional): Variables de personalización
- `subject` (string): Asunto
- `category` (string, opcional): Categoría
- `program_date` (date, opcional): Fecha programada

**Retorna:** string (ID del email)

### getEmailStatus
```
GET /api/1/getEmailStatus/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `email_key` (string): Clave del email

**Retorna:** integer (estado del email)

### getCreditsSMTP
```
GET /api/1/getCreditsSMTP/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación

**Retorna:** integer (créditos SMTP disponibles)
**Límite:** 10 peticiones/minuto

---

## 4. SUSCRIPTORES

### Gestión de Listas

#### createList
```
POST /api/1/createList/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `sender_email` (string): Email del remitente
- `name` (string): Nombre de la lista
- `company` (string): Empresa
- `country` (string): País
- `city` (string): Ciudad
- `address` (string): Dirección
- `phone` (string): Teléfono

**Retorna:** integer (ID de la lista)

#### getLists
```
GET /api/1/getLists/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación

**Retorna:** dict (listas disponibles)
**Límite:** 5 peticiones/segundo

#### deleteList
```
POST /api/1/deleteList/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `list_id` (integer): ID de la lista

**Retorna:** void
**Límite:** 10 peticiones/minuto

#### getListStats
```
GET /api/1/getListStats/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `list_id` (integer): ID de la lista

**Retorna:** dict (estadísticas de la lista)
**Límite:** 10 peticiones/minuto

#### getListSubsStats
```
GET /api/1/getListSubsStats/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `list_id` (integer): ID de la lista
- `block_index` (integer): Índice de paginación

**Retorna:** dict (estadísticas por suscriptor)
**Límite:** 10 peticiones/minuto

### Gestión de Suscriptores

#### addSubscriber
```
POST /api/1/addSubscriber/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `list_id` (integer): ID de la lista
- `merge_fields` (dict): Campos del suscriptor
- `double_optin` (integer): Activar doble opt-in
- `update_subscriber` (integer): Actualizar si existe
- `complete_json` (integer): Respuesta completa

**Retorna:** integer (ID del suscriptor)

#### batchAddSubscribers
```
POST /api/1/batchAddSubscribers/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `list_id` (integer): ID de la lista
- `update_subscriber` (integer): Actualizar existentes
- `subscribers_data` (list): Datos de suscriptores
- `complete_json` (integer): Respuesta completa

**Retorna:** list (resultados del proceso)
**Límite:** 5 peticiones/segundo

#### deleteSubscriber
```
POST /api/1/deleteSubscriber/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `list_id` (integer): ID de la lista
- `email` (string): Email del suscriptor

**Retorna:** void

#### batchDeleteSubscribers
```
POST /api/1/batchDeleteSubscribers/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `list_id` (integer): ID de la lista
- `email_list` (dict): Lista de emails

**Retorna:** list (resultados del proceso)
**Límite:** 10 peticiones/minuto

#### deleteAllSubscribers
```
POST /api/1/deleteAllSubscribers/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `list_id` (integer): ID de la lista

**Retorna:** void (proceso asíncrono)
**Límite:** 10 peticiones/minuto
**Nota:** Se ejecuta en segundo plano. Verificar finalización con getListStats

#### unsubscribeSubscriber
```
POST /api/1/unsubscribeSubscriber/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `list_id` (integer): ID de la lista
- `email` (string): Email del suscriptor

**Retorna:** void

### Búsqueda y Consulta

#### getSubscribers
```
GET /api/1/getSubscribers/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `list_id` (integer): ID de la lista
- `status` (integer): Estado del suscriptor
- `block_index` (integer): Índice de paginación
- `all_fields` (integer): Todos los campos
- `complete_json` (integer): Respuesta completa

**Retorna:** dict (lista de suscriptores)
**Límite:** 10 peticiones/minuto

#### getSubscriberDetails
```
GET /api/1/getSubscriberDetails/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `list_id` (integer): ID de la lista
- `subscriber` (string): Email del suscriptor

**Retorna:** dict (detalles del suscriptor)
**Límite:** 5 peticiones/segundo

#### searchSubscriber
```
GET /api/1/searchSubscriber/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `subscriber` (string): Email a buscar

**Retorna:** dict (datos en todas las listas)
**Límite:** 10 peticiones/minuto

#### getInactiveSubscribers
```
GET /api/1/getInactiveSubscribers/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `date_from` (date): Fecha desde
- `date_to` (date): Fecha hasta
- `full_info` (integer): Información completa

**Retorna:** list (suscriptores inactivos)
**Límite:** 10 peticiones/minuto

### Campos Personalizados

#### addMergeTag
```
POST /api/1/addMergeTag/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `list_id` (integer): ID de la lista
- `field_name` (string): Nombre del campo
- `field_type` (string): Tipo del campo

**Retorna:** void
**Límite:** 10 peticiones/minuto

#### getFields
```
GET /api/1/getFields/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `list_id` (integer): ID de la lista

**Retorna:** dict (campos y tipos)
**Límite:** 10 peticiones/minuto

#### getMergeFields
```
GET /api/1/getMergeFields/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `list_id` (integer): ID de la lista

**Retorna:** dict (merge fields)
**Límite:** 10 peticiones/minuto

#### getListFields
```
GET /api/1/getListFields/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `list_id` (integer): ID de la lista

**Retorna:** dict (información completa de campos)

### Otros

#### getForms
```
GET /api/1/getForms/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `list_id` (integer): ID de la lista

**Retorna:** dict (formularios asociados)
**Límite:** 5 peticiones/segundo

#### getListSegments
```
GET /api/1/getListSegments/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `list_id` (integer): ID de la lista

**Retorna:** list (segmentos de la lista)

---

## 5. WEBHOOKS

### SMTP Webhooks

#### getSMTPWebhook
```
GET /api/1/getSMTPWebhook/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación

**Retorna:** dict (configuración del webhook)
**Límite:** 10 peticiones/minuto

#### configSMTPWebhook
```
POST /api/1/configSMTPWebhook/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `callback_url` (string): URL del webhook
- `delivered` (integer): Activar evento entregado
- `hard_bounce` (integer): Activar rebote duro
- `soft_bounce` (integer): Activar rebote suave
- `complain` (integer): Activar quejas
- `opens` (integer): Activar aperturas
- `click` (integer): Activar clics
- `active` (integer): Activar webhook

**Retorna:** integer (estado de configuración)
**Límite:** 10 peticiones/minuto

### Lista Webhooks

#### getListWebhook
```
GET /api/1/getListWebhook/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `list_id` (integer): ID de la lista

**Retorna:** dict (configuración del webhook)
**Límite:** 10 peticiones/minuto

#### configListWebhook
```
POST /api/1/configListWebhook/
```
**Parámetros:**
- `auth_token` (string): Token de autenticación
- `list_id` (integer): ID de la lista
- `callback_url` (string): URL del webhook
- `subscribes` (integer): Activar suscripciones
- `unsubscribes` (integer): Activar bajas
- `hard_bounce` (integer): Activar rebote duro
- `soft_bounce` (integer): Activar rebote suave
- `complain` (integer): Activar quejas
- `opens` (integer): Activar aperturas
- `click` (integer): Activar clics
- `active` (integer): Activar webhook

**Retorna:** integer (estado de configuración)
**Límite:** 10 peticiones/minuto

---

## Ejemplos de Uso

### Ejemplo: Crear y enviar una campaña
```python
import requests

# Configuración
API_BASE = "https://acumbamail.com/api/1/"
AUTH_TOKEN = "tu_auth_token_aqui"

# Crear campaña
params = {
    "auth_token": AUTH_TOKEN,
    "name": "Campaña de Navidad",
    "from_name": "Mi Empresa",
    "from_email": "info@miempresa.com",
    "subject": "Ofertas especiales de Navidad",
    "content": "<html><body><h1>Feliz Navidad</h1></body></html>",
    "lists": {"12345": "Lista Principal"},
    "tracking_urls": 1,
    "https": 1
}

response = requests.post(f"{API_BASE}createCampaign/", data=params)
campaign_id = response.json()
```

### Ejemplo: Añadir suscriptor con double opt-in
```python
params = {
    "auth_token": AUTH_TOKEN,
    "list_id": 12345,
    "merge_fields": {
        "email": "nuevo@ejemplo.com",
        "name": "Juan Pérez",
        "phone": "+34600000000"
    },
    "double_optin": 1,
    "update_subscriber": 0
}

response = requests.post(f"{API_BASE}addSubscriber/", data=params)
subscriber_id = response.json()
```

### Ejemplo: Configurar webhook
```python
params = {
    "auth_token": AUTH_TOKEN,
    "list_id": 12345,
    "callback_url": "https://miapp.com/webhook",
    "subscribes": 1,
    "unsubscribes": 1,
    "opens": 1,
    "click": 1,
    "active": 1
}

response = requests.post(f"{API_BASE}configListWebhook/", data=params)
```

---

## Consideraciones Importantes

1. **Rate Limiting**: Cada endpoint tiene límites específicos de peticiones. Respeta estos límites para evitar el código 429.

2. **Paginación**: Para grandes conjuntos de datos, usa `block_index` para paginar resultados.

3. **Procesos Asíncronos**: Algunas operaciones (como `deleteAllSubscribers`) se ejecutan en segundo plano.

4. **Double Opt-in**: Recomendado para cumplir con regulaciones como GDPR.

5. **Campos Personalizados**: Usa merge tags para personalizar contenido dinámicamente.

6. **Webhooks**: Útiles para mantener sincronizados sistemas externos con eventos de Acumbamail.

7. **Formatos de Fecha**: Usar formato ISO 8601 (YYYY-MM-DD HH:MM:SS).

8. **Gestión de Errores**: Implementar manejo adecuado de códigos de error HTTP.

9. **Seguridad**: Nunca exponer el auth_token en código cliente o repositorios públicos.

10. **Testing**: Usar listas de prueba antes de envíos masivos en producción.