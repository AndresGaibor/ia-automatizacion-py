"""
Validador de configuración con manejo automático de errores y migración
"""
from tkinter import messagebox
from .config.settings import settings
from .config_window import show_config_window
from .config_migrator import ensure_config_valid

def check_config_or_show_dialog(parent=None) -> bool:
    """
    Verifica la configuración y muestra diálogo de configuración si es necesaria.
    Incluye validación y migración automática del archivo config.yaml.

    Args:
        parent: Ventana padre para el diálogo

    Returns:
        bool: True si la configuración está completa, False si se canceló
    """
    # 1. Primero validar y migrar el archivo config.yaml si es necesario
    try:
        migration_success, migration_msg, warnings = ensure_config_valid()

        # Mostrar advertencias de migración si las hay
        if warnings and any("⚠️" in warning or "Backup creado" in warning or "actualizada automáticamente" in warning for warning in warnings):
            warning_text = "\n".join(warnings)
            messagebox.showwarning(
                "Configuración Actualizada",
                f"Su archivo config.yaml ha sido actualizado:\n\n{warning_text}",
                parent=parent
            )

        if not migration_success:
            messagebox.showerror(
                "Error de Configuración",
                f"No se pudo validar/migrar config.yaml:\n{migration_msg}",
                parent=parent
            )
            return False

    except Exception as e:
        messagebox.showerror(
            "Error de Configuración",
            f"Error procesando config.yaml: {e}",
            parent=parent
        )
        return False

    # 2. Recargar configuración después de la migración
    try:
        settings.__init__()  # Reinicializar settings para cargar cambios
        settings.validate()
        return True

    except ValueError as e:
        # Mostrar alerta y abrir ventana de configuración
        error_msg = str(e)

        # Personalizar mensaje según el error
        if "Credenciales no configuradas" in error_msg:
            title = "⚠️ Credenciales Requeridas"
            message = "Para usar esta función necesita configurar sus credenciales de Acumbamail.\n\n¿Desea configurarlas ahora?"
        elif "API key no configurada" in error_msg:
            title = "⚠️ API Key Requerida"
            message = "Para usar esta función necesita configurar su API Key de Acumbamail.\n\n¿Desea configurarla ahora?"
        else:
            title = "⚠️ Configuración Incompleta"
            message = f"Configuración incompleta: {error_msg}\n\n¿Desea configurar ahora?"

        # Mostrar diálogo de confirmación
        result = messagebox.askyesno(title, message, icon="warning")

        if result:
            # Mostrar ventana de configuración
            show_config_window(parent)
            # Verificar nuevamente después de mostrar la ventana
            try:
                settings.__init__()  # Recargar configuración
                settings.validate()
                return True
            except ValueError:
                # Usuario canceló o no completó la configuración
                return False
        else:
            return False

def validate_config_silently() -> bool:
    """
    Valida la configuración sin mostrar diálogos.
    Incluye migración automática silenciosa.

    Returns:
        bool: True si la configuración está completa
    """
    try:
        # Migrar silenciosamente si es necesario
        ensure_config_valid()

        # Recargar y validar configuración
        settings.__init__()
        settings.validate()
        return True
    except:
        return False

def get_config_status() -> tuple[bool, str]:
    """
    Obtiene el estado de la configuración.

    Returns:
        tuple: (is_valid, status_message)
    """
    try:
        settings.validate()
        return True, "✅ Configuración completa"
    except ValueError as e:
        return False, f"❌ {str(e)}"

def show_config_status(parent=None):
    """Muestra el estado actual de la configuración"""
    is_valid, message = get_config_status()

    if is_valid:
        messagebox.showinfo("Estado de Configuración", message, parent=parent)
    else:
        result = messagebox.askyesno(
            "Estado de Configuración",
            f"{message}\n\n¿Desea configurar ahora?",
            icon="warning",
            parent=parent
        )
        if result:
            show_config_window(parent)