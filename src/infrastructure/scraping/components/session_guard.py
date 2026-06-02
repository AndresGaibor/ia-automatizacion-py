from playwright.sync_api import Page
from src.shared.logging.logger import get_logger

logger = get_logger()


class ComponenteGuardiaSesion:
    AUTHENTICATED_ELEMENT_SELECTORS = [
        {"selector": "navigation", "description": "Navegación principal"},
        {"selector": "nav", "description": "Barra de navegación"},
        {"selector": "[data-testid='user-menu']", "description": "Menú de usuario"},
        {"selector": "a[href*='logout']", "description": "Enlace de logout"},
        {"selector": "a[href*='profile']", "description": "Enlace de perfil"},
        {"selector": "button[aria-label*='usuario']", "description": "Botón de usuario"},
        {"selector": "a[href*='/report/']", "description": "Enlace a reportes"},
        {"selector": "a[href*='/campaigns/']", "description": "Enlace a campañas"},
        {"selector": "a[href*='/subscribers/']", "description": "Enlace a suscriptores"},
        {"selector": "h1:has-text('Panel')", "description": "Título de panel"},
        {"selector": "h1:has-text('Dashboard')", "description": "Título de dashboard"},
        {"selector": ".dashboard", "description": "Contenedor de dashboard"},
    ]

    LOGIN_ELEMENT_SELECTORS = [
        "input[type='email']",
        "input[type='password']",
        "button[name='login']",
        "button:has-text('Entrar')",
        "button:has-text('Login')",
        "a:has-text('¿Olvidaste tu contraseña?')",
    ]

    def __init__(self, page: Page):
        self._page = page

    def is_on_login_page(self) -> bool:
        for selector in self.LOGIN_ELEMENT_SELECTORS:
            try:
                if self._page.locator(selector).count() > 0:
                    return True
            except Exception:
                pass
        return False

    def is_authenticated(self) -> bool:
        resultado = self.verify_login()
        return resultado["success"]

    def verify_login(self) -> dict:
        logger.info("Verificando éxito del login")
        resultado = {
            "success": False,
            "method": None,
            "details": "",
            "url": self._page.url,
            "authenticated_elements": [],
        }

        try:
            current_url = self._page.url.lower()
            url_indicates_auth = (
                "/login/" not in current_url
                and "/login" not in current_url
                and ("acumbamail.com" in current_url or current_url.endswith("/"))
            )

            if url_indicates_auth:
                resultado["method"] = "url_check"
                resultado["details"] = f"URL {self._page.url} no es página de login"

            elementos_encontrados = []
            for elemento in self.AUTHENTICATED_ELEMENT_SELECTORS:
                try:
                    locator = self._page.locator(elemento["selector"])
                    if locator.count() > 0:
                        elementos_encontrados.append(elemento["description"])
                except Exception:
                    pass

            resultado["authenticated_elements"] = elementos_encontrados

            login_elements_found = []
            for login_element in self.LOGIN_ELEMENT_SELECTORS:
                try:
                    if self._page.locator(login_element).count() > 0:
                        login_elements_found.append(login_element)
                except Exception:
                    pass

            if len(elementos_encontrados) >= 2:
                resultado["success"] = True
                if not resultado["method"]:
                    resultado["method"] = "content_verification"
                resultado["details"] = f"Se encontraron {len(elementos_encontrados)} elementos de autenticación"
            elif url_indicates_auth and len(elementos_encontrados) >= 1:
                resultado["success"] = True
                resultado["details"] = f"URL válida y {len(elementos_encontrados)} elemento de autenticación"
            elif len(login_elements_found) == 0 and url_indicates_auth:
                resultado["success"] = True
                if not resultado["method"]:
                    resultado["method"] = "url_only"
                resultado["details"] = "URL válida y sin elementos de login detectados"
            else:
                resultado["details"] = (
                    f"No se pudo verificar autenticación: {len(elementos_encontrados)} elementos encontrados, {len(login_elements_found)} elementos de login"
                )

        except Exception as e:
            resultado["details"] = f"Error durante verificación: {str(e)}"

        return resultado
