"""
Selectores CSS para scraping de Acumbamail

IMPORTANTE: Estos selectores necesitan ser actualizados según la estructura HTML real del sitio.
Los valores aquí son PLACEHOLDER que debes reemplazar con los selectores reales.
"""
from dataclasses import dataclass


@dataclass
class CampaignSelectors:
    """
    Selectores CSS para páginas de campañas
    
    TODO: Actualizar todos estos selectores con los valores reales del sitio
    """
    
    # === NAVEGACIÓN Y PESTAÑAS ===
    statistics_tab: str = "[data-tab='statistics']"  # TODO: Verificar selector real
    subscribers_tab: str = "[data-tab='subscribers']"  # TODO: Verificar selector real
    reports_tab: str = "[data-tab='reports']"  # TODO: Verificar selector real
    
    # === ESTADÍSTICAS BÁSICAS ===
    total_sent: str = ".stat-total-sent .number"  # TODO: Verificar selector real
    total_opened: str = ".stat-opened .number"  # TODO: Verificar selector real
    total_not_opened: str = ".stat-not-opened .number"  # TODO: Verificar selector real
    total_clicks: str = ".stat-clicks .number"  # TODO: Verificar selector real
    total_hard_bounces: str = ".stat-hard-bounces .number"  # TODO: Verificar selector real
    total_soft_bounces: str = ".stat-soft-bounces .number"  # TODO: Verificar selector real
    
    # === LISTAS DE SUSCRIPTORES ===
    # Suscriptores que SÍ abrieron
    opener_emails: str = ".openers-list .email"  # TODO: Verificar selector real
    opener_rows: str = ".openers-list tr"  # TODO: Verificar selector real
    
    # Suscriptores que NO abrieron (principal objetivo del scraping)
    non_opener_emails: str = ".non-openers-list .email"  # TODO: Encontrar selector real
    non_opener_rows: str = ".non-openers-list tr"  # TODO: Encontrar selector real
    
    # Hard bounces (otro objetivo del scraping)
    hard_bounce_emails: str = ".hard-bounces-list .email"  # TODO: Encontrar selector real
    hard_bounce_rows: str = ".hard-bounces-list tr"  # TODO: Encontrar selector real
    hard_bounce_reason: str = ".bounce-reason"  # TODO: Encontrar selector real
    
    # Soft bounces (ya disponible en API, pero útil para verificar)
    soft_bounce_emails: str = ".soft-bounces-list .email"  # TODO: Verificar selector real
    
    # === INFORMACIÓN ADICIONAL ===
    email_date: str = ".email-date"  # TODO: Encontrar selector real
    subscriber_info: str = ".subscriber-info"  # TODO: Encontrar selector real
    
    # === PAGINACIÓN ===
    next_page_button: str = ".pagination .next:not(.disabled)"  # TODO: Verificar selector real
    prev_page_button: str = ".pagination .prev:not(.disabled)"  # TODO: Verificar selector real
    page_info: str = ".pagination .page-info"  # TODO: Verificar selector real
    page_numbers: str = ".pagination .page-number"  # TODO: Verificar selector real
    
    # === FILTROS Y CONTROLES ===
    date_filter_start: str = "input[name='start_date']"  # TODO: Verificar selector real
    date_filter_end: str = "input[name='end_date']"  # TODO: Verificar selector real
    apply_filter_button: str = "button.apply-filter"  # TODO: Verificar selector real
    reset_filter_button: str = "button.reset-filter"  # TODO: Verificar selector real
    
    # === ESTADÍSTICAS AVANZADAS (solo por scraping) ===
    geographic_stats: str = ".geographic-stats"  # TODO: Encontrar selector real
    device_stats: str = ".device-stats"  # TODO: Encontrar selector real
    time_stats: str = ".time-stats"  # TODO: Encontrar selector real
    
    # === EXPORTS Y DESCARGAS ===
    export_button: str = ".export-button"  # TODO: Verificar selector real
    download_link: str = ".download-link"  # TODO: Verificar selector real

    # === SEGUIMIENTO DE URLs ===
    # Página: /report/campaign/{id}/url/
    url_tracking_list: str = "ul, .url-list"  # Lista que contiene las URLs
    url_tracking_items: str = "li"  # Items individuales de URL
    url_details_link: str = "a[href*='/click/details/']"  # Enlace de detalles


@dataclass
class CommonSelectors:
    """
    Selectores comunes del sitio Acumbamail
    
    TODO: Actualizar con los selectores reales del sitio
    """
    
    # === ESTADOS DE CARGA ===
    loading_spinner: str = ".loading, .spinner, .loader"  # TODO: Verificar selectores reales
    loading_overlay: str = ".loading-overlay"  # TODO: Verificar selector real
    
    # === MENSAJES DEL SISTEMA ===
    error_message: str = ".alert-error, .error-message, .alert-danger"  # TODO: Verificar selectores reales
    success_message: str = ".alert-success, .success-message"  # TODO: Verificar selectores reales
    warning_message: str = ".alert-warning, .warning-message"  # TODO: Verificar selectores reales
    info_message: str = ".alert-info, .info-message"  # TODO: Verificar selectores reales
    
    # === AUTENTICACIÓN (si es necesario re-login) ===
    login_form: str = "form.login-form"  # TODO: Verificar selector real
    login_email: str = "input[name='email'], input[type='email']"  # TODO: Verificar selector real
    login_password: str = "input[name='password'], input[type='password']"  # TODO: Verificar selector real
    login_submit: str = "button[type='submit'], .login-button"  # TODO: Verificar selector real
    logout_link: str = ".logout, .sign-out"  # TODO: Verificar selector real
    
    # === NAVEGACIÓN PRINCIPAL ===
    main_menu: str = ".main-menu, .navbar"  # TODO: Verificar selector real
    campaigns_menu: str = ".campaigns-menu, [href*='campaign']"  # TODO: Verificar selector real
    lists_menu: str = ".lists-menu, [href*='list']"  # TODO: Verificar selector real
    
    # === MODALES Y POPUPS ===
    modal: str = ".modal, .popup"  # TODO: Verificar selector real
    modal_close: str = ".modal-close, .close-button"  # TODO: Verificar selector real
    modal_confirm: str = ".modal-confirm, .confirm-button"  # TODO: Verificar selector real
    modal_cancel: str = ".modal-cancel, .cancel-button"  # TODO: Verificar selector real
    
    # === TABLAS GENÉRICAS ===
    table: str = "table, .data-table"  # TODO: Verificar selector real
    table_row: str = "tr, .table-row"  # TODO: Verificar selector real
    table_cell: str = "td, .table-cell"  # TODO: Verificar selector real
    table_header: str = "th, .table-header"  # TODO: Verificar selector real
    
    # === FORMULARIOS ===
    form_input: str = "input, .form-input"  # TODO: Verificar selector real
    form_select: str = "select, .form-select"  # TODO: Verificar selector real
    form_button: str = "button, .form-button"  # TODO: Verificar selector real
    form_submit: str = "[type='submit'], .submit-button"  # TODO: Verificar selector real


# === INSTRUCCIONES PARA ACTUALIZAR SELECTORES ===
"""
CÓMO ENCONTRAR LOS SELECTORES REALES:

1. Abrir las herramientas de desarrollador en el navegador (F12)
2. Navegar a la página de una campaña en Acumbamail
3. Inspeccionar los elementos que necesitas
4. Anotar los selectores CSS correctos
5. Actualizar esta clase con los valores reales

ELEMENTOS PRIORITARIOS A ENCONTRAR:
- Lista de emails que NO abrieron la campaña
- Lista de hard bounces
- Botones de paginación
- Estadísticas numéricas

TIPS:
- Busca por clases CSS (.class-name)
- Busca por atributos data-* ([data-attribute="value"])
- Usa selectores específicos pero no demasiado frágiles
- Prueba los selectores en la consola: document.querySelector("selector")
"""