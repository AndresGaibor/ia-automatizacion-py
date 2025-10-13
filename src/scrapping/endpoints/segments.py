"""
Servicio de scraping para la gestión de segmentos en Acumbamail.
Extraído desde mapeo_segmentos.py y adaptado al patrón de endpoints en src/scrapping/endpoints.
"""
import logging
from typing import List, Optional
import time

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

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

    # (Sin helpers de lifecycle complicados; se usa context manager cuando no hay Page externa)

    # ============== API pública ==============
    def create_segment(self, list_id: int, segment_name: str, api_client) -> bool:
        """
        Crea un segmento individual.
        Primero verifica por API si ya existe. Si no, lo crea vía UI.
        """
        logging.info(f"🔍 Iniciando creación de segmento '{segment_name}' en lista {list_id}")

        # Paso 1: Verificar existencia por API
        logging.info("📌 Paso 1: Verificando si segmento ya existe por API")
        try:
            logging.debug(f"🔍 Consultando segmentos existentes para lista {list_id}")
            segmentos_existentes = api_client.suscriptores.get_list_segments(list_id)
            existing_names: List[str] = []

            if segmentos_existentes:
                logging.debug(f"📋 Se encontraron segmentos existentes, procesando...")
                # soportar distintos formatos (objeto con .segments o lista directa/tuplas)
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
                return True

            logging.debug(f"📋 Segmento '{segment_name}' no existe - Procediendo a crearlo")

        except Exception as e:
            logging.warning(f"⚠️ No se pudo verificar segmentos existentes por API: {e}")
            logging.warning("🔄 Continuando con creación vía UI de todas formas")

        # Paso 2: Navegar a página de segmentos
        logging.info("📌 Paso 2: Navegando a página de segmentos")
        try:
            if self.page is not None:
                page = self.page
                segments_url = f"https://acumbamail.com/app/list/{list_id}/segments/"
                logging.debug(f"🌐 Navegando a: {segments_url}")

                page.goto(segments_url, wait_until="domcontentloaded", timeout=60000)
                logging.debug("✅ Navegación iniciada (domcontentloaded)")

                page.wait_for_load_state("networkidle", timeout=30000)
                logging.debug("✅ Página cargada completamente (networkidle)")

            else:
                logging.error("❌ ERROR PASO 2 - No hay página disponible")
                return False

        except PWTimeoutError as e:
            logging.error(f"❌ ERROR PASO 2 - Timeout navegando a página de segmentos: {e}")
            logging.error(f"⏱️ URL intentada: https://acumbamail.com/app/list/{list_id}/segments/")
            return False
        except Exception as e:
            logging.error(f"❌ ERROR PASO 2 - Error navegando a página de segmentos: {e}")
            return False

        # Paso 3: Localizar botón "Nuevo segmento"
        logging.info("📌 Paso 3: Localizando botón 'Nuevo segmento'")
        nuevo_segmento_button = None

        # Estrategia 1: Botón en estado vacío
        try:
            logging.debug("🔍 Buscando botón en estado vacío (#empty-state-add-segment-button)")
            empty_state_button = page.locator("#empty-state-add-segment-button").get_by_text("Nuevo segmento")
            if empty_state_button.is_visible(timeout=5000):
                nuevo_segmento_button = empty_state_button
                logging.debug("✅ Botón encontrado en estado vacío")
        except PWTimeoutError:
            logging.debug("⏱️ Botón en estado vacío no encontrado (timeout)")
        except Exception as e:
            logging.debug(f"⚠️ Error buscando botón en estado vacío: {e}")

        # Estrategia 2: Botón normal
        if not nuevo_segmento_button:
            try:
                logging.debug("🔍 Buscando botón normal (#new-segment-button)")
                normal_button = page.locator("#new-segment-button").get_by_text("Nuevo segmento")
                if normal_button.is_visible(timeout=5000):
                    nuevo_segmento_button = normal_button
                    logging.debug("✅ Botón normal encontrado")
            except PWTimeoutError:
                logging.debug("⏱️ Botón normal no encontrado (timeout)")
            except Exception as e:
                logging.debug(f"⚠️ Error buscando botón normal: {e}")

        # Estrategia 3: Por rol
        if not nuevo_segmento_button:
            try:
                logging.debug("🔍 Buscando botón por rol (button, name='Nuevo segmento')")
                by_role_button = page.get_by_role("button", name="Nuevo segmento")
                if by_role_button.is_visible(timeout=5000):
                    nuevo_segmento_button = by_role_button
                    logging.debug("✅ Botón encontrado por rol")
            except PWTimeoutError:
                logging.debug("⏱️ Botón por rol no encontrado (timeout)")
            except Exception as e:
                logging.debug(f"⚠️ Error buscando botón por rol: {e}")

        # Verificación final
        if not nuevo_segmento_button:
            logging.error("❌ ERROR PASO 3 - No se pudo encontrar el botón 'Nuevo segmento' con ninguna estrategia")
            logging.debug("🔍 Estrategias intentadas: estado vacío, normal, por rol")
            return False

        # Paso 4: Hacer clic en "Nuevo segmento"
        logging.info("📌 Paso 4: Haciendo clic en 'Nuevo segmento'")
        try:
            logging.debug("🖱️ Haciendo clic en botón 'Nuevo segmento'")
            nuevo_segmento_button.click(timeout=10000)
            logging.debug("✅ Clic realizado exitosamente")
        except PWTimeoutError as e:
            logging.error(f"❌ ERROR PASO 4 - Timeout haciendo clic en 'Nuevo segmento': {e}")
            return False
        except Exception as e:
            logging.error(f"❌ ERROR PASO 4 - Error haciendo clic en 'Nuevo segmento': {e}")
            return False

        # Paso 5: Esperar y llenar formulario
        logging.info("📌 Paso 5: Llenando formulario de segmento")
        try:
            # Esperar a que aparezca el formulario
            logging.debug("⏳ Esperando selector #field-value-1")
            page.wait_for_selector("#field-value-1", timeout=10000)
            logging.debug("✅ Formulario visible")

            # Llenar nombre del segmento
            try:
                logging.debug("📝 Intentando llenar nombre con rol 'textbox, name=Nombre del segmento'")
                nombre_input = page.get_by_role("textbox", name="Nombre del segmento")
                nombre_input.fill(segment_name)
                logging.debug(f"✅ Nombre '{segment_name}' llenado con rol")
            except Exception:
                try:
                    logging.debug("📝 Fallback: usando selector #field-value-1")
                    nombre_input = page.locator("#field-value-1")
                    nombre_input.fill(segment_name)
                    logging.debug(f"✅ Nombre '{segment_name}' llenado con selector")
                except Exception as e:
                    logging.error(f"❌ ERROR llenando nombre del segmento: {e}")
                    return False

            # Paso 6: Configurar condiciones del segmento
            logging.info("📌 Paso 6: Configurando condiciones del segmento")
            try:
                logging.debug("📋 Configurando campo 'Segmentos'")
                campo_select = page.locator("#field-name-1")
                campo_select.select_option(label="Segmentos")
                logging.debug("✅ Campo 'Segmentos' seleccionado")

                logging.debug("📋 Configurando condición 'contiene'")
                condicion_select = page.locator("#field-type-1")
                condicion_select.select_option(label="contiene")
                logging.debug("✅ Condición 'contiene' seleccionada")

                logging.debug(f"📋 Configurando valor '{segment_name}'")
                valor_input = page.locator("#field-value-1")
                valor_input.fill(segment_name)
                logging.debug(f"✅ Valor '{segment_name}' configurado")

            except Exception as e:
                logging.warning(f"⚠️ Selectores específicos fallaron: {e}")
                logging.debug("🔄 Intentando estrategia genérica fallback")
                try:
                    logging.debug("📋 Fallback: haciendo clic en 'Segmentos'")
                    page.get_by_text("Segmentos").click(timeout=5000)

                    logging.debug("📋 Fallback: haciendo clic en 'contiene'")
                    page.get_by_text("contiene").click(timeout=5000)

                    logging.debug(f"📋 Fallback: llenando último input con '{segment_name}'")
                    page.locator("input[type='text']").last.fill(segment_name)
                    logging.debug("✅ Estrategia fallback completada")
                except Exception as e2:
                    logging.error(f"❌ ERROR configurando condiciones - Fallback también falló: {e2}")
                    return False

        except PWTimeoutError as e:
            logging.error(f"❌ ERROR PASO 5/6 - Timeout en formulario: {e}")
            return False
        except Exception as e:
            logging.error(f"❌ ERROR PASO 5/6 - Error en formulario: {e}")
            return False

        # Paso 7: Guardar el segmento
        logging.info("📌 Paso 7: Guardando el segmento")
        try:
            save_button = None

            # Estrategia 1: #segment-button-text
            try:
                logging.debug("🔍 Buscando botón #segment-button-text")
                save_button = page.locator("#segment-button-text")
                if save_button.is_visible(timeout=3000):
                    logging.debug("✅ Botón #segment-button-text encontrado")
            except Exception:
                pass

            # Estrategia 2: botón "Guardar"
            if not save_button or not save_button.is_visible():
                try:
                    logging.debug("🔍 Buscando botón 'Guardar' por rol")
                    save_button = page.get_by_role("button", name="Guardar")
                    if save_button.is_visible(timeout=3000):
                        logging.debug("✅ Botón 'Guardar' encontrado")
                except Exception:
                    pass

            # Estrategia 3: botón "Crear"
            if not save_button or not save_button.is_visible():
                try:
                    logging.debug("🔍 Buscando botón 'Crear' por rol")
                    save_button = page.get_by_role("button", name="Crear")
                    if save_button.is_visible(timeout=3000):
                        logging.debug("✅ Botón 'Crear' encontrado")
                except Exception:
                    pass

            # Estrategia 4: submit button
            if not save_button or not save_button.is_visible():
                try:
                    logging.debug("🔍 Buscando botón type='submit'")
                    save_button = page.locator("button[type='submit']").first
                    if save_button.is_visible(timeout=3000):
                        logging.debug("✅ Botón submit encontrado")
                except Exception:
                    pass

            if not save_button or not save_button.is_visible():
                logging.error("❌ ERROR PASO 7 - No se encontró botón de guardar con ninguna estrategia")
                return False

            # Hacer clic en guardar
            logging.debug("💾 Haciendo clic en guardar segmento")
            save_button.click(timeout=10000)
            logging.debug("✅ Clic en guardar realizado")

            # Esperar confirmación
            logging.debug("⏳ Esperando confirmación de guardado")
            page.wait_for_load_state("networkidle", timeout=15000)
            page.wait_for_timeout(5000)

            logging.success(f"✅ Segmento '{segment_name}' creado exitosamente en lista {list_id}")
            return True

        except PWTimeoutError as e:
            logging.error(f"❌ ERROR PASO 7 - Timeout guardando segmento: {e}")
            return False
        except Exception as e:
            logging.error(f"❌ ERROR PASO 7 - Error guardando segmento: {e}")
            return False
        # Si no hay página disponible, crear navegador temporal
        logging.info("📌 Creando navegador temporal para creación de segmento")
        try:
            with sync_playwright() as playwright:
                logging.debug("🌐 Iniciando navegador temporal")
                browser = playwright.chromium.launch(headless=False)
                context = crear_contexto_navegador(browser)
                page = context.new_page()
                logging.debug("✅ Navegador temporal creado")

                # Ejecutar los mismos pasos de creación pero con la página temporal
                # Pasos 2-7 del flujo normal (reutilizamos la lógica)
                segments_url = f"https://acumbamail.com/app/list/{list_id}/segments/"
                logging.debug(f"🌐 Navegando a: {segments_url}")

                page.goto(segments_url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_load_state("networkidle", timeout=30000)

                # TODO: Extraer lógica de creación a un método privado para reutilizar
                # Por ahora, replicamos la lógica esencial de forma simplificada

                # Localizar y hacer clic en "Nuevo segmento"
                nuevo_segmento_button = None
                for strategy_name, locator_func in [
                    ("estado vacío", lambda: page.locator("#empty-state-add-segment-button").get_by_text("Nuevo segmento")),
                    ("normal", lambda: page.locator("#new-segment-button").get_by_text("Nuevo segmento")),
                    ("por rol", lambda: page.get_by_role("button", name="Nuevo segmento"))
                ]:
                    try:
                        button = locator_func()
                        if button.is_visible(timeout=5000):
                            nuevo_segmento_button = button
                            logging.debug(f"✅ Botón encontrado con estrategia: {strategy_name}")
                            break
                    except PlaywrightTimeoutError:
                        continue

                if not nuevo_segmento_button:
                    logging.error("❌ ERROR - No se encontró botón 'Nuevo segmento' en navegador temporal")
                    return False

                nuevo_segmento_button.click()
                logging.debug("✅ Clic en 'Nuevo segmento' realizado")

                # Llenar formulario y guardar (versión simplificada)
                page.wait_for_selector("#field-value-1", timeout=10000)

                # Nombre del segmento
                nombre_input = page.locator("#field-value-1")
                nombre_input.fill(segment_name)

                # Configuración del segmento
                campo_select = page.locator("#field-name-1")
                campo_select.select_option(label="Segmentos")

                condicion_select = page.locator("#field-type-1")
                condicion_select.select_option(label="contiene")

                valor_input = page.locator("#field-value-1")
                valor_input.fill(segment_name)

                # Guardar
                save_button = page.locator("button[type='submit']").first
                save_button.click()

                # Esperar confirmación
                page.wait_for_load_state("networkidle", timeout=15000)
                page.wait_for_timeout(5000)

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

        # Paso 1: Validar entrada
        logging.info("📌 Paso 1: Validando entrada de segmentos")
        if not segment_names:
            logging.info("✅ No hay segmentos para crear - Lista vacía")
            print("  ℹ️  No hay segmentos para crear")
            return True

        logging.debug(f"📋 Segmentos a procesar: {segment_names}")
        logging.info(f"✅ Entrada validada - {len(segment_names)} segmentos para procesar")

        # Paso 2: Verificar existencia por API
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

        # Paso 3: Analizar y clasificar segmentos
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

        # Paso 4: Creación iterativa de segmentos
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

                # Llamar al método create_segment individual
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

                # Pausa entre segmentos (excepto el último)
                if idx < len(to_create) - 1:
                    logging.debug("⏱️ Pausa de 2 segundos entre segmentos")
                    time.sleep(2)

            except Exception as e:
                error_count += 1
                logging.error(f"❌ ERROR INESPERADO creando segmento '{name}': {e}")
                print(f"      ❌ Error inesperado creando segmento '{name}': {e}")
                success = False

                # Continuar con el siguiente segmento incluso si hay error
                continue

        # Paso 5: Resumen final
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
