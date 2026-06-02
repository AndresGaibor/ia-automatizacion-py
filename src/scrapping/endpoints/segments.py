"""
Servicio de scraping para la gestión de segmentos en Acumbamail.
Extraído desde mapeo_segmentos.py y adaptado al patrón de endpoints en src/scrapping/endpoints.
"""
import logging
from typing import List, Optional
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

from src.infrastructure.scraping.pages.segments_page import SegmentPage
from src.shared.logging.logger import get_logger
from src.shared.utils.legacy_utils import load_config, crear_contexto_navegador


class SegmentsScrapingService:
    """
    Servicio para crear segmentos mediante scraping en la UI de Acumbamail.

    Puede operar con una Page ya autenticada (recomendada) o, si no se provee,
    creará un navegador temporal usando el storage state configurado.
    """

    def __init__(self, page: Optional[Page] = None):
        self.page = page
        self.logger = get_logger()
        self.config = load_config()

    def create_segment(self, list_id: int, segment_name: str, api_client) -> bool:
        """
        Crea un segmento individual.
        Primero verifica por API si ya existe. Si no, lo crea vía UI.
        """
        logging.info(f"🔍 Iniciando creación de segmento '{segment_name}' en lista {list_id}")

        if not self._verify_segment_not_exists(list_id, segment_name, api_client):
            return True

        if self.page is not None:
            return self._create_segment_with_page(list_id, segment_name)
        else:
            return self._create_segment_with_browser(list_id, segment_name)

    def _verify_segment_not_exists(self, list_id: int, segment_name: str, api_client) -> bool:
        logging.info("📌 Paso 1: Verificando si segmento ya existe por API")
        try:
            logging.debug(f"🔍 Consultando segmentos existentes para lista {list_id}")
            segmentos_existentes = api_client.suscriptores.get_list_segments(list_id)
            existing_names: List[str] = []

            if segmentos_existentes:
                logging.debug(f"📋 Se encontraron segmentos existentes, procesando...")
                items = getattr(segmentos_existentes, 'segments', segmentos_existentes)
                for seg in items or []:
                    if isinstance(seg, tuple):
                        existing_names.append(str(seg[0]))
                    elif hasattr(seg, 'name'):
                        existing_names.append(str(getattr(seg, 'name')))
                    elif isinstance(seg, dict) and 'name' in seg:
                        existing_names.append(str(seg['name']))
                    else:
                        existing_names.append(str(seg))

                logging.debug(f"📋 Nombres de segmentos existentes: {existing_names}")

            if segment_name in existing_names:
                logging.info(f"✅ Segmento '{segment_name}' ya existe - No es necesario crearlo")
                return False

            logging.debug(f"📋 Segmento '{segment_name}' no existe - Procediendo a crearlo")

        except Exception as e:
            logging.warning(f"⚠️ No se pudo verificar segmentos existentes por API: {e}")
            logging.warning("🔄 Continuando con creación vía UI de todas formas")

        return True

    def _create_segment_with_page(self, list_id: int, segment_name: str) -> bool:
        logging.info("📌 Paso 2: Navegando a página de segmentos")
        try:
            segment_page = SegmentPage(self.page)

            if not segment_page.navigate_to(list_id):
                logging.error("❌ ERROR PASO 2 - No se pudo navegar")
                return False

            logging.debug("✅ Navegación iniciada (networkidle)")

            segment_page.wait_page_ready()

            logging.info("📌 Paso 3: Localizando botón 'Nuevo segmento'")
            if not segment_page.click_nuevo_segmento():
                logging.error("❌ ERROR PASO 3 - No se pudo encontrar el botón 'Nuevo segmento'")
                return False

            logging.info("📌 Paso 4: Llenando formulario de segmento")
            if not segment_page.wait_for_form():
                logging.error("❌ ERROR - No se pudo esperar el formulario")
                return False

            if not segment_page.fill_segment_name(segment_name):
                logging.error("❌ ERROR llenando nombre del segmento")
                return False

            logging.info("📌 Paso 5: Configurando condiciones del segmento")
            if not segment_page.configure_segment_conditions(segment_name):
                logging.warning("⚠️ Configuración de condiciones tuvo problemas")
                if not self._fallback_configure_conditions(segment_page, segment_name):
                    return False

            logging.info("📌 Paso 6: Guardando el segmento")
            if not segment_page.click_guardar():
                logging.error("❌ ERROR PASO 6 - No se encontró botón de guardar")
                return False

            if not segment_page.wait_for_saved():
                logging.error("❌ ERROR - Problemas esperando confirmación")
                return False

            logging.success(f"✅ Segmento '{segment_name}' creado exitosamente en lista {list_id}")
            return True

        except PlaywrightTimeoutError as e:
            logging.error(f"❌ ERROR - Timeout: {e}")
            return False
        except Exception as e:
            logging.error(f"❌ ERROR - Error: {e}")
            return False

    def _fallback_configure_conditions(self, segment_page: SegmentPage, segment_name: str) -> bool:
        try:
            logging.debug("🔄 Intentando estrategia genérica fallback")
            if not segment_page.click_segmentos_field():
                return False
            if not segment_page.click_contiene_condition():
                return False
            if not segment_page.fill_segment_value_input(segment_name):
                return False
            logging.debug("✅ Estrategia fallback completada")
            return True
        except Exception as e2:
            logging.error(f"❌ ERROR fallback: {e2}")
            return False

    def _create_segment_with_browser(self, list_id: int, segment_name: str) -> bool:
        logging.info("📌 Creando navegador temporal para creación de segmento")
        try:
            with sync_playwright() as playwright:
                logging.debug("🌐 Iniciando navegador temporal")
                browser = playwright.chromium.launch(headless=False)
                context = crear_contexto_navegador(browser)
                page = context.new_page()
                logging.debug("✅ Navegador temporal creado")

                segment_page = SegmentPage(page)

                if not segment_page.navigate_to(list_id):
                    logging.error("❌ ERROR - No se pudo navegar a segmentos en navegador temporal")
                    return False

                if not segment_page.click_nuevo_segmento():
                    logging.error("❌ ERROR - No se encontró botón 'Nuevo segmento' en navegador temporal")
                    return False

                if not segment_page.wait_for_form():
                    logging.error("❌ ERROR - No se pudo esperar el formulario")
                    return False

                if not segment_page.fill_segment_name(segment_name):
                    logging.error("❌ ERROR llenando nombre del segmento")
                    return False

                if not segment_page.configure_segment_conditions(segment_name):
                    logging.error("❌ ERROR configurando condiciones")
                    return False

                if not segment_page.click_guardar():
                    logging.error("❌ ERROR - No se encontró botón de guardar")
                    return False

                if not segment_page.wait_for_saved():
                    logging.error("❌ ERROR - Problemas esperando confirmación")
                    return False

                logging.success(f"✅ Segmento '{segment_name}' creado exitosamente con navegador temporal")
                return True

        except PlaywrightTimeoutError as e:
            logging.error(f"❌ ERROR - Timeout en navegador temporal: {e}")
            return False
        except Exception as e:
            logging.error(f"❌ ERROR - Error con navegador temporal: {e}")
            return False

    def create_segments_batch(self, list_id: int, segment_names: List[str], api_client) -> bool:
        """
        Crea múltiples segmentos con verificación previa de existencia.
        """
        logging.info(f"🔍 Iniciando creación batch de segmentos - Lista: {list_id}, Total: {len(segment_names)}")

        logging.info("📌 Paso 1: Validando entrada de segmentos")
        if not segment_names:
            logging.info("✅ No hay segmentos para crear - Lista vacía")
            print("  ℹ️  No hay segmentos para crear")
            return True

        logging.debug(f"📋 Segmentos a procesar: {segment_names}")
        logging.info(f"✅ Entrada validada - {len(segment_names)} segmentos para procesar")

        logging.info("📌 Paso 2: Verificando segmentos existentes por API")
        try:
            logging.debug(f"🔍 Consultando segmentos existentes para lista {list_id}")
            segmentos_existentes = api_client.suscriptores.get_list_segments(list_id)
            existing_names: List[str] = []

            if segmentos_existentes:
                logging.debug("📋 Procesando segmentos existentes encontrados...")
                items = getattr(segmentos_existentes, 'segments', segmentos_existentes)
                for seg in items or []:
                    if isinstance(seg, tuple):
                        existing_names.append(str(seg[0]))
                    elif hasattr(seg, 'name'):
                        existing_names.append(str(getattr(seg, 'name')))
                    elif isinstance(seg, dict) and 'name' in seg:
                        existing_names.append(str(seg['name']))
                    else:
                        existing_names.append(str(seg))

                logging.debug(f"📋 Segmentos existentes procesados: {existing_names}")
            else:
                logging.debug("📋 No se encontraron segmentos existentes")

            logging.info(f"✅ Verificación API completada - {len(existing_names)} segmentos existentes")

        except Exception as e:
            logging.warning(f"⚠️ Error verificando segmentos existentes por API: {e}")
            logging.warning("🔄 Continuando con creación de todos los segmentos")
            existing_names = []

        logging.info("📌 Paso 3: Clasificando segmentos por estado")
        to_create = [n for n in segment_names if n not in existing_names]
        already = [n for n in segment_names if n in existing_names]

        logging.debug(f"📊 Clasificación resultante:")
        logging.debug(f"   • Ya existen: {already}")
        logging.debug(f"   • Por crear: {to_create}")

        if already:
            print(f"  ✅ {len(already)} segmento(s) ya existe(n): {already}")
            logging.info(f"✅ {len(already)} segmentos ya existen: {already}")

        if not to_create:
            print("  ✅ Todos los segmentos ya existen")
            logging.success("✅ Todos los segmentos solicitados ya existen")
            return True

        print(f"  🚀 Creando {len(to_create)} segmento(s) nuevo(s): {to_create}")
        logging.info(f"🚀 Iniciando creación de {len(to_create)} segmentos nuevos: {to_create}")

        logging.info("📌 Paso 4: Creación iterativa de segmentos")
        success = True
        created_count = 0
        error_count = 0

        for idx, name in enumerate(to_create):
            segment_number = idx + 1
            total_segments = len(to_create)

            try:
                logging.info(f"📝 Creando segmento {segment_number}/{total_segments}: '{name}'")
                print(f"      📝 Creando segmento {segment_number}/{total_segments}: '{name}'")

                creation_success = self.create_segment(list_id, name, api_client)

                if creation_success:
                    created_count += 1
                    print(f"      ✅ Segmento '{name}' creado exitosamente")
                    logging.success(f"✅ Segmento '{name}' creado exitosamente ({created_count}/{total_segments})")
                else:
                    error_count += 1
                    print(f"      ❌ Error creando segmento '{name}'")
                    logging.error(f"❌ Error creando segmento '{name}' ({error_count} errores)")
                    success = False

                if idx < len(to_create) - 1:
                    logging.debug("⏱️ Pausa de 2 segundos entre segmentos")
                    if self.page is not None:
                        self.page.wait_for_timeout(2000)

            except Exception as e:
                error_count += 1
                logging.error(f"❌ ERROR INESPERADO creando segmento '{name}': {e}")
                print(f"      ❌ Error inesperado creando segmento '{name}': {e}")
                success = False
                continue

        logging.info("📌 Paso 5: Generando resumen final")
        total = len(segment_names)

        print("  📊 Resumen de segmentos:")
        print(f"      • Total solicitados: {total}")
        print(f"      • Ya existían: {len(already)}")
        print(f"      • Creados nuevos: {created_count}")
        print(f"      • Errores: {len(to_create) - created_count}")

        logging.info("📊 Resumen final de operación batch:")
        logging.info(f"   • Total solicitados: {total}")
        logging.info(f"   • Ya existían: {len(already)}")
        logging.info(f"   • Creados nuevos: {created_count}")
        logging.info(f"   • Errores: {error_count}")
        logging.info(f"   • Éxito general: {'✅' if success else '❌'}")

        if success:
            logging.success(f"✅ Operación batch completada exitosamente - {created_count}/{len(to_create)} segmentos creados")
        else:
            logging.warning(f"⚠️ Operación batch completada con errores - {created_count}/{len(to_create)} segmentos creados, {error_count} errores")

        return success