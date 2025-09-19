"""
Funciones utilitarias compartidas para automatización.
"""

import os
import sys

def _early_project_root() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Forzar ruta de navegadores de Playwright antes de importar la librería
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", os.path.join(_early_project_root(), "ms-playwright"))
os.makedirs(os.environ["PLAYWRIGHT_BROWSERS_PATH"], exist_ok=True)

from playwright.sync_api import Page, TimeoutError as PWTimeoutError
from playwright._impl._errors import Error as PWError
import pandas as pd
import json
import yaml
import time
import re
from functools import wraps

REAL_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_6) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# Variables globales para timeouts adaptativos
_current_navigation_timeout = 2000   # Empezar con 2s (ultra agresivo)
_current_processing_timeout = 1000   # Empezar con 1s (ultra agresivo)
_max_navigation_timeout = 300000     # Máximo 5 minutos
_max_processing_timeout = 60000      # Máximo 1 minuto
_timeout_increment = 3000            # Aumentar de 3 en 3 segundos

def get_current_navigation_timeout():
    """Obtiene el timeout actual de navegación"""
    return _current_navigation_timeout

def get_current_processing_timeout():
    """Obtiene el timeout actual de procesamiento"""
    return _current_processing_timeout

def increase_navigation_timeout():
    """Aumenta el timeout de navegación si no ha llegado al máximo"""
    global _current_navigation_timeout
    if _current_navigation_timeout < _max_navigation_timeout:
        _current_navigation_timeout = min(_current_navigation_timeout + _timeout_increment, _max_navigation_timeout)
        # Solo importar logger cuando se necesite para evitar importaciones circulares
        try:
            from .logger import get_logger
            logger = get_logger()
            logger.logger.info(f"🔧 Timeout de navegación aumentado a {_current_navigation_timeout//1000}s")
        except:
            print(f"🔧 Timeout de navegación aumentado a {_current_navigation_timeout//1000}s")
    return _current_navigation_timeout

def increase_processing_timeout():
    """Aumenta el timeout de procesamiento si no ha llegado al máximo"""
    global _current_processing_timeout
    if _current_processing_timeout < _max_processing_timeout:
        _current_processing_timeout = min(_current_processing_timeout + _timeout_increment, _max_processing_timeout)
        try:
            from .logger import get_logger
            logger = get_logger()
            logger.logger.info(f"🔧 Timeout de procesamiento aumentado a {_current_processing_timeout//1000}s")
        except:
            print(f"🔧 Timeout de procesamiento aumentado a {_current_processing_timeout//1000}s")
    return _current_processing_timeout

def reset_adaptive_timeouts():
    """Resetea los timeouts adaptativos cuando todo va bien"""
    global _current_navigation_timeout, _current_processing_timeout
    _current_navigation_timeout = 2000  # Volver a 2s
    _current_processing_timeout = 1000  # Volver a 1s
    try:
        from .logger import get_logger
        logger = get_logger()
        logger.logger.info("✅ Timeouts adaptativos reseteados a valores iniciales")
    except:
        print("✅ Timeouts adaptativos reseteados a valores iniciales")

def retry(max_attempts=3, delay=1.0, exceptions=(Exception,)):
    """
    Decorador para reintentar funciones automáticamente cuando fallan.
    
    Args:
        max_attempts: Número máximo de intentos
        delay: Tiempo de espera base entre intentos (con backoff exponencial)
        exceptions: Tupla de excepciones que disparan el retry
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from .logger import get_logger
            logger = get_logger()
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        logger.log_error(f"retry_{func.__name__}", e, f"Falló después de {max_attempts} intentos")
                        raise
                    
                    wait_time = delay * (2 ** attempt)
                    logger.log_warning(f"retry_{func.__name__}", f"Intento {attempt + 1}/{max_attempts} falló: {e}. Reintentando en {wait_time}s")
                    time.sleep(wait_time)
            
            return None
        return wrapper
    return decorator

def cargar_terminos_busqueda(archivo_busqueda: str) -> list[list[str]]:
    """
    Carga los términos de búsqueda desde el archivo Excel
    """
    from .logger import get_logger
    logger = get_logger()
    
    logger.start_timer("cargar_terminos_busqueda")
    logger.log_file_operation("Leyendo", archivo_busqueda)
    
    try:
        terminos = []
        df = pd.read_excel(archivo_busqueda, engine="openpyxl")
        
        for index, row in df.iterrows():
            buscar = row['Buscar']
            if(buscar == 'x' or buscar == 'X'):
                terminos.append([row['Nombre'], row['Listas']])
        
        logger.end_timer("cargar_terminos_busqueda", f"Cargados {len(terminos)} términos")
        logger.log_success("cargar_terminos_busqueda", f"Términos encontrados: {len(terminos)}")
        return terminos
        
    except Exception as e:
        logger.log_error("cargar_terminos_busqueda", e, f"archivo: {archivo_busqueda}")
        logger.end_timer("cargar_terminos_busqueda")
        raise

def project_root() -> str:
    """Directorio base de la app:
    - Si está congelada (PyInstaller), carpeta del ejecutable.
    - En desarrollo, raíz del proyecto (carpeta que contiene app.py).
    """
    if getattr(sys, "frozen", False):  # PyInstaller --onefile
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def config_path() -> str:
    return os.path.join(project_root(), "config.yaml")

def data_path(name: str) -> str:
    d = os.path.join(project_root(), "data")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, name)

def load_config(defaults: dict | None = None) -> dict:
    """Carga config.yaml desde el directorio base. Si no existe, lo crea con defaults (si se proveen)."""
    path = config_path()
    if os.path.exists(path):
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    if defaults is None:
        defaults = {}
    with open(path, "w") as f:
        yaml.safe_dump(defaults, f, sort_keys=False)
    return defaults

def get_timeouts():
	"""
	Obtiene los timeouts configurados en el archivo de configuración
	Convierte de segundos a milisegundos para Playwright
	"""
	config = load_config()
	timeouts_config = config.get('timeouts', {})
	
	# Valores por defecto en segundos
	defaults = {
		'navigation': 120,       # 2 minutos
		'page_load': 60,         # 1 minuto
		'element_wait': 30,      # 30 segundos  
		'elements': 45,          # 45 segundos
		'context': 300,          # 5 minutos
		'long_operations': 240,  # 4 minutos
		'file_upload': 180,      # 3 minutos
		'tables': 60,            # 1 minuto
		'pagination': 90         # 1.5 minutos
	}
	
	# Combinar configuración con defaults y convertir a milisegundos
	timeouts = {}
	for key, default_value in defaults.items():
		seconds = timeouts_config.get(key, default_value)
		timeouts[key] = seconds * 1000  # Convertir a milisegundos
	
	return timeouts

def save_config(cfg: dict):
    with open(config_path(), "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)

## NOTA: se elimina la antigua función load_config basada en project_root,
## ya que ahora toda configuración vive en app_data_dir (compatible con PyInstaller).

def crear_contexto_navegador(browser, extraccion_oculta: bool = False):
    """
    Crea y configura el contexto del navegador
    """
    storage_state = storage_state_path()
    if not os.path.exists(storage_state):
        # asegurar carpeta data y archivo
        os.makedirs(os.path.dirname(storage_state), exist_ok=True)
        with open(storage_state, "w") as f:
            json.dump({}, f)

    context = browser.new_context(
        viewport={"width": 1400, "height": 900},
        user_agent=REAL_UA,
        locale="es-ES",
        timezone_id="Europe/Madrid",
        ignore_https_errors=True,
        storage_state=storage_state,
    )
    
    # Configurar timeouts desde la configuración
    timeouts = get_timeouts()
    context.set_default_timeout(timeouts['context'])
    context.set_default_navigation_timeout(timeouts['navigation'])
    
    return context

def storage_state_path() -> str:
    """Ruta al archivo de estado de sesión persistente."""
    return data_path("datos_sesion.json")

def ensure_playwright_browsers_path() -> str:
    """
    Garantiza la ruta (ya establecida arriba) y la devuelve.
    """
    path = os.environ["PLAYWRIGHT_BROWSERS_PATH"]
    os.makedirs(path, exist_ok=True)
    return path

def configurar_navegador(p, extraccion_oculta: bool = False):
    """
    Configura y lanza el navegador
    """
    from .logger import get_logger
    logger = get_logger()
    
    logger.start_timer("configurar_navegador")
    logger.log_browser_action("Configurando navegador", extra_info=f"headless={extraccion_oculta}")
    
    ensure_playwright_browsers_path()
    try:
        browser = p.chromium.launch(
            headless=extraccion_oculta,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        logger.end_timer("configurar_navegador")
        logger.log_success("configurar_navegador", "Navegador lanzado exitosamente")
        return browser
    except PWError as e:
        msg = str(e)
        if "Executable doesn't exist" in msg or "playwright install" in msg:
            logger.log_warning("configurar_navegador", "Playwright no encontrado, descargando...")
            try:
                notify("Playwright", "Descargando Chromium (solo la primera vez)...")
            except Exception:
                pass
            # Ejecutar el CLI sin cerrar el proceso
            from playwright.__main__ import main as playwright_main
            old_argv = sys.argv[:]
            try:
                for args in (["playwright", "install", "chromium"],
                             ["playwright", "install", "--force", "chromium"]):
                    try:
                        sys.argv = args
                        ensure_playwright_browsers_path()
                        playwright_main()
                        break  # instalación OK
                    except SystemExit as se:
                        # Evitar que cierre la app; solo propagar si es error real
                        if se.code not in (0, None):
                            raise
                    except Exception:
                        # Intentará con --force en el siguiente ciclo
                        continue
            finally:
                sys.argv = old_argv

            # Reintento de lanzamiento tras instalar
            browser = p.chromium.launch(
                headless=extraccion_oculta,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )
            logger.end_timer("configurar_navegador")
            logger.log_success("configurar_navegador", "Navegador lanzado después de instalación")
            return browser
        logger.log_error("configurar_navegador", e)
        logger.end_timer("configurar_navegador")
        raise

@retry(max_attempts=3, delay=1.0, exceptions=(PWTimeoutError, Exception))
def navegar_a_reportes(page: Page):
    """Navega a la sección de reportes con retry automático"""
    from .logger import get_logger
    logger = get_logger()
    
    logger.log_browser_action("Navegando a reportes")
    click_element(page.locator("a[href*='/reports']"))
    page.wait_for_load_state('networkidle')

@retry(max_attempts=3, delay=2.0, exceptions=(PWTimeoutError, Exception))
def safe_goto(page: Page, url: str, wait_until: str = "domcontentloaded") -> None:
    """Navegar a una URL con retry automático"""
    from .logger import get_logger
    logger = get_logger()
    
    logger.log_page_navigation(url)
    
    timeouts = get_timeouts()
    timeout = timeouts['page_load'] if wait_until == "domcontentloaded" else timeouts['navigation']
    
    start_time = time.time()
    page.goto(url, wait_until=wait_until, timeout=timeout)  # type: ignore
    wait_time = time.time() - start_time
    
    logger.log_page_navigation(url, wait_time)

def safe_wait_for_element(locator, timeout_type: str = "elements") -> None:
    """Esperar por un elemento usando timeouts adaptativos."""
    if timeout_type == "elements":
        timeout_actual = get_current_processing_timeout()
    else:
        timeouts = get_timeouts()
        timeout_actual = timeouts.get(timeout_type, get_current_processing_timeout())
    
    try:
        locator.wait_for(timeout=timeout_actual)
    except Exception:
        # Si falla, aumentar timeout para futuras operaciones
        increase_processing_timeout()
        raise

@retry(max_attempts=3, delay=0.5, exceptions=(PWTimeoutError, Exception))
def click_element(locator):
    """Click en elemento con preparación automática y timeouts adaptativos"""
    timeout_actual = get_current_processing_timeout()
    
    try:
        locator.wait_for(state="visible", timeout=timeout_actual)
        locator.wait_for(state="attached", timeout=min(timeout_actual//2, 3000))
        
        try:
            locator.scroll_into_view_if_needed(timeout=min(timeout_actual//4, 2000))
        except Exception:
            pass
        
        locator.click(timeout=min(timeout_actual//2, 5000))
    except Exception:
        # Si falla, aumentar timeout para futuras operaciones
        increase_processing_timeout()
        raise

@retry(max_attempts=3, delay=0.5, exceptions=(PWTimeoutError, Exception))
def fill_field(locator, text, clear_first=True):
    """Llenar campo de texto con verificación y timeouts adaptativos"""
    timeout_actual = get_current_processing_timeout()
    
    try:
        locator.wait_for(state="visible", timeout=timeout_actual)
        locator.wait_for(state="attached", timeout=min(timeout_actual//2, 5000))
        
        try:
            locator.scroll_into_view_if_needed(timeout=min(timeout_actual//4, 2000))
        except Exception:
            pass
        
        # Verificar que es un campo de entrada
        try:
            # Intentar hacer focus para asegurar que es editable
            locator.focus(timeout=min(timeout_actual//4, 2000))
        except Exception:
            pass
        
        if clear_first:
            locator.clear(timeout=min(timeout_actual//4, 3000))
            time.sleep(0.1)
        
        locator.fill(text, timeout=min(timeout_actual//2, 5000))
        
        # Verificar que se llenó correctamente
        try:
            if locator.input_value(timeout=min(timeout_actual//4, 2000)) != text:
                raise Exception(f"Campo no se llenó correctamente. Esperado: '{text}'")
        except Exception:
            pass  # No todos los elementos soportan input_value
    except Exception:
        # Si falla, aumentar timeout para futuras operaciones
        increase_processing_timeout()
        raise


def obtener_total_paginas(page: Page) -> int:
    """
    Obtiene el número total de páginas de reportes
    """
    from .logger import get_logger
    logger = get_logger()

    timeouts = get_timeouts()

    # 1) Intentar aumentar items por página si existe el select o un combobox custom
    try:
        hecho = False
        # Intentar obtener el conteo inicial de items para verificar refresco
        lista_reportes = None
        try:
            lista_reportes = page.locator('#newsletter-reports')
            count_before = lista_reportes.locator('> li').count()
        except Exception:
            count_before = None
        select_candidates = page.locator('select')
        logger.logger.info(f"🔍 Controles de paginación: {select_candidates.count()} <select> encontrados")
        if select_candidates.count() > 0:
            # Usar el primer select que tenga múltiples opciones
            objetivo = select_candidates.first

            # Retry simple: seleccionar la última opción disponible
            for select_attempt in range(2):
                try:
                    # Esperar que el select esté listo
                    objetivo.wait_for(state="visible", timeout=5000)
                    objetivo.wait_for(state="attached", timeout=2000)

                    # Obtener todas las opciones y seleccionar la última
                    opciones = objetivo.locator('option')
                    count = opciones.count()

                    if count > 1:  # Solo si hay múltiples opciones
                        # Seleccionar la última opción (index = count - 1)
                        objetivo.select_option(index=count - 1)

                        # Obtener el texto/valor de la opción seleccionada para el log
                        try:
                            last_option_text = opciones.nth(count - 1).inner_text() or "última opción"
                            last_option_value = opciones.nth(count - 1).get_attribute('value') or last_option_text
                        except Exception:
                            last_option_text = f"opción #{count}"
                            last_option_value = last_option_text

                        logger.logger.info(f"🔧 Items por página (select): seleccionada última opción '{last_option_text}' (intento {select_attempt + 1})")
                        page.wait_for_timeout(500)

                        # Verificar que la selección se aplicó correctamente (simplificado)
                        try:
                            selected_index = objetivo.evaluate("el => el.selectedIndex")
                            if selected_index == count - 1:
                                logger.logger.info(f"✅ Confirmado: última opción seleccionada correctamente")
                            else:
                                logger.log_warning("verify_selection", f"Índice seleccionado ({selected_index}) no coincide con el último ({count - 1})")
                        except Exception as verify_e:
                            logger.log_warning("verify_selection", f"No se pudo verificar la selección: {verify_e}")

                        hecho = True
                        break
                    else:
                        logger.log_warning("select_items_per_page", f"Select solo tiene {count} opción(es), omitiendo")
                        break

                except Exception as e:
                    logger.log_warning("select_items_per_page", f"Intento {select_attempt + 1}/2 falló: {e}")
                    if select_attempt == 0:
                        time.sleep(1)

        if not hecho:
            # Fallback para combobox personalizado (no-native select)
            # Intentar primero dentro o cerca de la región de reportes
            logger.logger.info("🔍 Buscando comboboxes personalizados...")
            regiones = []
            try:
                if lista_reportes and lista_reportes.count() > 0:
                    regiones.append(lista_reportes)
                    parent1 = lista_reportes.locator('xpath=..')
                    regiones.append(parent1)
                    parent2 = parent1.locator('xpath=..')
                    regiones.append(parent2)
                    parent3 = parent2.locator('xpath=..')
                    regiones.append(parent3)
            except Exception:
                pass

            comboboxes = None
            for reg in regiones:
                try:
                    c = reg.get_by_role('combobox')
                    if c.count() > 0:
                        comboboxes = c
                        break
                except Exception:
                    continue
            if comboboxes is None:
                comboboxes = page.get_by_role('combobox')
            logger.logger.info(f"🔍 Comboboxes encontrados: {comboboxes.count() if comboboxes else 0}")
            if comboboxes and comboboxes.count() > 0:
                # Probar comboboxes con retry
                for cb_idx in range(min(comboboxes.count(), 3)):
                    for cb_attempt in range(2):
                        try:
                            cb = comboboxes.nth(cb_idx)
                            
                            # Usar click_element para el combobox
                            click_element(cb)
                            
                            # Buscar opciones típicas en un listbox/menú con retry
                            opciones = page.get_by_role('option')
                            if opciones.count() == 0:
                                page.wait_for_timeout(300)
                                opciones = page.locator('[role="listbox"] [role="option"]')
                            if opciones.count() == 0:
                                # Cerrar y probar otro combobox
                                page.keyboard.press('Escape')
                                if cb_attempt == 0:
                                    time.sleep(0.5)
                                    continue
                                else:
                                    break
                            
                            # Simplificado: seleccionar la última opción directamente
                            count_opciones = opciones.count()
                            if count_opciones > 1:
                                # Seleccionar la última opción (index = count - 1)
                                last_idx = count_opciones - 1
                                try:
                                    last_option_text = opciones.nth(last_idx).inner_text() or f"opción #{last_idx + 1}"
                                except Exception:
                                    last_option_text = f"última opción"

                                click_element(opciones.nth(last_idx))
                                logger.logger.info(f"🔧 Items por página (combobox): seleccionada última opción '{last_option_text}' (intento {cb_attempt + 1})")
                                page.wait_for_timeout(500)
                                hecho = True
                                break
                            else:
                                logger.log_warning("combobox_options", f"Solo {count_opciones} opción(es) disponible(s), omitiendo")
                                page.keyboard.press('Escape')
                                if cb_attempt == 0:
                                    time.sleep(0.5)
                                break
                                    
                        except Exception as e:
                            logger.log_warning("combobox_selection", f"Intento {cb_attempt + 1}/2 en combobox {cb_idx} falló: {e}")
                            try:
                                page.keyboard.press('Escape')
                            except Exception:
                                pass
                            if cb_attempt == 0:
                                time.sleep(1)
                    
                    if hecho:
                        break

        if not hecho:
            logger.logger.info("ℹ️ No se encontraron controles de 'items por página' en esta interfaz. Probablemente no haya paginación o use otro sistema.")
        
        # Tras cambiar, esperar a que el listado se refresque si teníamos un conteo previo
        if hecho and count_before is not None:
            try:
                # Espera más robusta para permitir recarga de tabla
                timeout_actual = get_current_processing_timeout()
                page.wait_for_load_state("domcontentloaded", timeout=min(timeout_actual, 8000))  # Máximo 8s
                page.wait_for_timeout(800)  # Aumentado a 800ms para dar tiempo a la recarga

                # Intentar detectar cambio en el conteo de elementos
                for _ in range(15):  # Aumentado a 15 iteraciones
                    page.wait_for_timeout(300)  # Aumentado a 300ms por iteración
                    count_after = page.locator('#newsletter-reports').locator('> li').count()
                    if count_after != count_before and count_after > 0:
                        logger.logger.info(f"🔄 Listado actualizado: {count_before} → {count_after} elementos")
                        # Espera adicional para que la tabla se estabilice completamente
                        page.wait_for_timeout(500)
                        break
                else:
                    # Si no se detectó cambio, esperar tiempo fijo adicional
                    logger.log_warning("items_per_page", f"No se detectó cambio en el conteo ({count_before} elementos). Aplicando espera adicional.")
                    page.wait_for_timeout(1500)  # Espera fija de 1.5s si no hay cambio detectable
            except Exception as ex:
                logger.log_warning("refrescar_listado", f"Error esperando refresco: {ex}")
                # Aumentar timeout si falla
                increase_processing_timeout()

    except Exception as e:
        logger.log_warning("obtener_total_paginas", f"No se pudo ajustar 'items por página': {e}")

    # Espera robusta para estabilidad después de configurar paginación
    try:
        timeout_actual = get_current_processing_timeout()
        page.wait_for_timeout(800)  # Aumentado a 800ms para permitir actualización completa
        page.wait_for_load_state("domcontentloaded", timeout=min(timeout_actual, 5000))  # Máximo 5s

        # Espera adicional específica para que la configuración de paginación tome efecto
        page.wait_for_timeout(500)  # 500ms adicionales para estabilización
    except Exception:
        # Si falla, aumentar timeout para futuras operaciones
        increase_processing_timeout()

    # 2) Obtener la navegación y determinar el último número con timeout adaptativo
    max_reintentos_navegacion = 3
    
    for intento_nav in range(max_reintentos_navegacion):
        # Usar timeout adaptativo actual
        timeout_actual = get_current_processing_timeout()
        
        try:
            logger.logger.info(f"🔍 Buscando navegación (intento {intento_nav + 1}/{max_reintentos_navegacion}, timeout: {timeout_actual//1000}s)")
            
            # Buscar barra de paginación que contenga enlaces numéricos, usando un ancla conocida (1)
            navegacion = page.locator('ul').filter(
                has=page.locator('li').locator('a', has_text="1")
            ).last

            # Si no hay esa barra, intentar un fallback: cualquier ul con varios li que tengan anchors numéricos
            if navegacion.count() == 0:
                posibles = page.locator('ul')
                mejor = None
                mejor_count = 0
                total = posibles.count()
                for i in range(min(total, 5)):
                    ul = posibles.nth(i)
                    li_count = ul.locator('li').count()
                    if li_count > mejor_count:
                        mejor = ul
                        mejor_count = li_count
                if mejor is not None:
                    navegacion = mejor

            # Espera con timeout adaptativo para elementos de paginación
            try:
                navegacion.locator('li').first.wait_for(timeout=timeout_actual)
            except Exception:
                pass

            # Verificar que tenemos navegación válida
            if navegacion.count() == 0:
                logger.logger.info(f"❌ Sin navegación en intento {intento_nav + 1}")
                if intento_nav < max_reintentos_navegacion - 1:
                    # Aumentar timeout para próximo intento
                    increase_processing_timeout()
                    page.wait_for_timeout(300)  # Espera mínima
                    continue
                else:
                    logger.logger.info("📄 Sin navegación después de múltiples intentos, asumiendo 1 página")
                    return 1

            ultimo_elemento = navegacion.locator('li').last
            texto = ultimo_elemento.inner_text().strip()

            # A veces el último li es 'Siguiente' o '>' – intentar encontrar el máximo número
            if not texto.isdigit():
                # Escanear todos los li y tomar el mayor número
                lis = navegacion.locator('li')
                count = lis.count()
                max_num = 1
                for i in range(count):
                    try:
                        t = lis.nth(i).inner_text().strip()
                        if t.isdigit():
                            max_num = max(max_num, int(t))
                    except Exception:
                        continue
                logger.logger.info(f"📄 Páginas detectadas: {max_num}")
                # Éxito en primer intento - resetear timeouts
                if intento_nav == 0:
                    reset_adaptive_timeouts()
                return max_num

            numero_paginas = int(texto) if texto.isdigit() else 1
            logger.logger.info(f"📄 Páginas detectadas: {numero_paginas}")
            # Éxito en primer intento - resetear timeouts
            if intento_nav == 0:
                reset_adaptive_timeouts()
            return numero_paginas
            
        except Exception as e:
            logger.log_warning("buscar_navegacion", f"Error en intento {intento_nav + 1} (timeout {timeout_actual//1000}s) buscando navegación: {e}")
            
            # Aumentar timeout para próximo intento
            increase_processing_timeout()
            
            if intento_nav < max_reintentos_navegacion - 1:
                page.wait_for_timeout(300)  # Espera mínima
                continue
            else:
                logger.log_warning("obtener_total_paginas", f"No se pudo obtener el total de páginas después de {max_reintentos_navegacion} intentos: {e}")
                # Intentar capturar screenshot para diagnóstico sin fallar el flujo
                try:
                    path = data_path(f"pagination_error_{int(time.time())}.png")
                    page.screenshot(path=path)
                    logger.log_file_operation("Screenshot paginación", path)
                except Exception:
                    pass
                return 1
    
    return 1

def navegar_siguiente_pagina(page: Page, pagina_actual: int) -> bool:
	"""
	Navega a la siguiente página con timeout adaptativo que se mantiene y aumenta
	"""
	from .logger import get_logger
	logger = get_logger()
	
	siguiente_pagina = pagina_actual + 1
	max_reintentos = 3
	
	logger.start_timer(f"navegar_pagina_{siguiente_pagina}")
	logger.log_browser_action("Navegando a siguiente página", f"página {siguiente_pagina}")
	
	for intento in range(max_reintentos):
		# Usar el timeout actual (que se mantiene entre llamadas)
		timeout_actual = get_current_navigation_timeout()
		
		try:
			logger.logger.info(f"🔄 Navegando a página {siguiente_pagina} (timeout: {timeout_actual//1000}s)")
			
			# Sin espera previa - directamente buscar navegación
			navegacion = page.locator('ul').filter(
				has=page.locator('li').locator('a', has_text=f"{siguiente_pagina}")
			).last
			
			enlace = navegacion.locator('a', has_text=f"{siguiente_pagina}").first
			
			if enlace.count() > 0:
				# Click inmediato con timeout adaptativo
				enlace.wait_for(timeout=timeout_actual)
				enlace.click()
				
				# SOLO domcontentloaded - NUNCA networkidle
				page.wait_for_load_state("domcontentloaded", timeout=timeout_actual)
				time.sleep(0.1)  # Solo 100ms mínimo
				
				# Verificación rápida de contenido
				try:
					page.locator('#newsletter-reports li').first.wait_for(timeout=min(timeout_actual, 3000))
				except:
					pass
				
				logger.end_timer(f"navegar_pagina_{siguiente_pagina}")
				logger.log_success("navegar_siguiente_pagina", f"Página {siguiente_pagina} alcanzada en intento {intento + 1}")
				
				# Si todo va bien en el primer intento, resetear timeouts para mantenerse rápido
				if intento == 0:
					reset_adaptive_timeouts()
				
				return True
			else:
				raise Exception(f"No se encontró enlace para página {siguiente_pagina}")
				
		except Exception as e:
			logger.log_warning("navegar_siguiente_pagina", f"Error en intento {intento + 1} (timeout {timeout_actual//1000}s): {e}")
			
			# CLAVE: Aumentar el timeout para el siguiente intento (se mantiene para futuras navegaciones)
			increase_navigation_timeout()
			
			if intento < max_reintentos - 1:
				logger.logger.info(f"🔄 Reintentando con timeout aumentado...")
				time.sleep(1)  # 1 segundo entre reintentos
			else:
				logger.log_error("navegar_siguiente_pagina", e, f"Falló después de {max_reintentos} intentos")
				logger.end_timer(f"navegar_pagina_{siguiente_pagina}")
				return False
	
	return False

# Funciones específicas para listas de suscriptores

def obtener_total_paginas_listas(page: Page) -> int:
	"""
	Obtiene el número total de páginas en la sección de listas
	"""
	from .logger import get_logger
	logger = get_logger()

	try:
		# Buscar la paginación específica de listas
		paginacion = page.locator('.am-pagination')

		if paginacion.count() == 0:
			logger.logger.info("No se encontró paginación, asumiendo 1 página")
			return 1

		# Buscar todos los enlaces de página dentro de la paginación
		enlaces_pagina = paginacion.locator('li a')
		total_paginas = 1

		for i in range(enlaces_pagina.count()):
			try:
				texto = enlaces_pagina.nth(i).inner_text().strip()
				if texto.isdigit():
					numero_pagina = int(texto)
					total_paginas = max(total_paginas, numero_pagina)
			except:
				continue

		logger.logger.info(f"📄 Total de páginas de listas encontradas: {total_paginas}")
		return total_paginas

	except Exception as e:
		logger.log_warning("obtener_total_paginas_listas", f"Error obteniendo total de páginas: {e}")
		return 1

def navegar_siguiente_pagina_listas(page: Page, pagina_actual: int) -> bool:
	"""
	Navega a la siguiente página en la sección de listas
	"""
	from .logger import get_logger
	logger = get_logger()

	siguiente_pagina = pagina_actual + 1

	try:
		logger.logger.info(f"🔄 Navegando a página {siguiente_pagina} de listas")

		# Buscar el enlace específico de la siguiente página
		paginacion = page.locator('.am-pagination')
		enlace_siguiente = paginacion.locator(f'li a:has-text("{siguiente_pagina}")')

		if enlace_siguiente.count() == 0:
			logger.log_warning("navegar_siguiente_pagina_listas", f"No se encontró enlace para página {siguiente_pagina}")
			return False

		# Hacer clic en el enlace
		enlace_siguiente.first.wait_for(timeout=10000)
		enlace_siguiente.first.click()

		# Esperar a que cargue la nueva página
		page.wait_for_load_state("domcontentloaded", timeout=15000)
		page.wait_for_timeout(2000)  # Esperar un poco más para que carguen los elementos

		# Verificar que estamos en la página correcta
		pagina_activa = paginacion.locator('li.active a')
		if pagina_activa.count() > 0:
			texto_activo = pagina_activa.first.inner_text().strip()
			if texto_activo == str(siguiente_pagina):
				logger.logger.info(f"✅ Navegación exitosa a página {siguiente_pagina}")
				return True

		logger.log_warning("navegar_siguiente_pagina_listas", f"No se pudo verificar navegación a página {siguiente_pagina}")
		return False

	except Exception as e:
		logger.log_error("navegar_siguiente_pagina_listas", f"Error navegando a página {siguiente_pagina}: {e}")
		return False

def cambiar_items_por_pagina_listas(page: Page, items: int = 50) -> bool:
	"""
	Cambia el número de elementos por página en la sección de listas
	"""
	from .logger import get_logger
	logger = get_logger()

	try:
		logger.logger.info(f"📊 Intentando cambiar a {items} elementos por página")

		# Buscar el select dentro de .am-items-per-page
		items_per_page_container = page.locator('.am-items-per-page')

		if items_per_page_container.count() == 0:
			logger.log_warning("cambiar_items_por_pagina_listas", "No se encontró contenedor de items per page")
			return False

		select_element = items_per_page_container.locator('select').first

		if select_element.count() == 0:
			logger.log_warning("cambiar_items_por_pagina_listas", "No se encontró select de items per page")
			return False

		# Verificar si la opción existe
		opcion = select_element.locator(f'option:has-text("{items}")')

		if opcion.count() == 0:
			logger.log_warning("cambiar_items_por_pagina_listas", f"No se encontró opción para {items} elementos")
			# Mostrar opciones disponibles
			opciones = select_element.locator('option')
			opciones_disponibles = []
			for i in range(opciones.count()):
				texto = opciones.nth(i).inner_text().strip()
				opciones_disponibles.append(texto)
			logger.logger.info(f"Opciones disponibles: {opciones_disponibles}")

			# Usar la opción más alta disponible
			if opciones_disponibles:
				items_max = max([int(x) for x in opciones_disponibles if x.isdigit()])
				logger.logger.info(f"Usando {items_max} elementos por página en su lugar")
				opcion = select_element.locator(f'option:has-text("{items_max}")')

		# Seleccionar la opción
		if opcion.count() > 0:
			select_element.wait_for(timeout=10000)
			select_element.select_option(label=opcion.first.inner_text().strip())

			# Esperar a que la página se recargue
			page.wait_for_load_state("domcontentloaded", timeout=15000)
			page.wait_for_timeout(2000)

			logger.logger.info(f"✅ Cambiado a {items} elementos por página")
			return True

		return False

	except Exception as e:
		logger.log_error("cambiar_items_por_pagina_listas", f"Error cambiando items por página: {e}")
		return False


def notify(title: str, message: str, level: str = "info") -> bool:
    """
    Muestra una notificación segura:
    - Si hay una UI Tk activa (o se puede crear en el hilo principal), usa messagebox.
    - Si no, imprime en consola.

    Retorna True si se mostró con Tk, False si se hizo fallback a print.
    """
    try:
        import tkinter as tk  # type: ignore
        from tkinter import messagebox  # type: ignore
        import threading

        root = getattr(tk, "_default_root", None)
        created = False

        if root is None:
            # Solo crear una raíz si estamos en el hilo principal para evitar errores.
            if threading.current_thread() is not threading.main_thread():
                raise RuntimeError("No hay Tk root y no estamos en el hilo principal")
            root = tk.Tk()
            root.withdraw()
            created = True

        if level == "error":
            messagebox.showerror(title, message)
        elif level == "warning":
            messagebox.showwarning(title, message)
        else:
            messagebox.showinfo(title, message)

        if created:
            # Cerrar la raíz temporal para no dejar ventanas ocultas vivas.
            try:
                root.destroy()
            except Exception:
                pass
        return True
    except Exception:
        # Entornos headless o sin Tk: fallback a consola
        print(f"{title}: {message}")
        return False

