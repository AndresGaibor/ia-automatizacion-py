#!/usr/bin/env python3
"""
Script para debuggear la página de listas y encontrar los selectores correctos
"""

from playwright.sync_api import sync_playwright
from src.utils import configurar_navegador, crear_contexto_navegador, load_config, storage_state_path
from src.autentificacion import login
import os

def debug_lists_page():
    """Debug la página de listas para encontrar selectores correctos"""
    config = load_config()
    url = config.get("url", "")
    url_base = config.get("url_base", "")

    with sync_playwright() as p:
        browser = configurar_navegador(p, extraccion_oculta=False)
        context = crear_contexto_navegador(browser)
        page = context.new_page()

        try:
            # Navegar y hacer login si es necesario
            page.goto(url_base)
            page.wait_for_load_state("domcontentloaded")

            # Verificar si hay sesión guardada
            if os.path.exists(storage_state_path()):
                print("🔑 Usando sesión guardada...")
                # La función ya maneja la sesión automáticamente
            else:
                print("🔐 Haciendo login...")
                page.goto(url)
                login(page)
                context.storage_state(path=storage_state_path())

            # Navegar a la página de listas
            print("📋 Navegando a la página de listas...")
            page.goto("https://acumbamail.com/app/lists/")
            page.wait_for_load_state("networkidle", timeout=30000)

            # Tomar screenshot para debugging
            page.screenshot(path="debug_lists_page.png", full_page=True)
            print("📸 Screenshot guardado como debug_lists_page.png")

            # Explorar la estructura de la página
            print("\n🔍 Explorando estructura de la página...")

            # Buscar posibles contenedores de listas
            selectors_to_try = [
                "table",
                "tbody tr",
                ".table",
                "[class*='list']",
                "[class*='List']",
                "[id*='list']",
                "[id*='List']",
                ".row",
                "[data-*]",
                "li",
                ".item",
                ".card"
            ]

            for selector in selectors_to_try:
                try:
                    elements = page.locator(selector)
                    count = elements.count()
                    if count > 0:
                        print(f"✅ Selector '{selector}': {count} elementos encontrados")

                        # Mostrar algunos ejemplos del contenido
                        for i in range(min(3, count)):
                            try:
                                text = elements.nth(i).inner_text()[:100]
                                classes = elements.nth(i).get_attribute("class") or ""
                                print(f"   Elemento {i}: clase='{classes}' texto='{text}...'")
                            except:
                                pass
                    else:
                        print(f"❌ Selector '{selector}': 0 elementos")
                except Exception as e:
                    print(f"⚠️ Error con selector '{selector}': {e}")

            # Buscar selectores de paginación
            print("\n🔍 Buscando selectores de paginación...")
            pagination_selectors = [
                "select",
                "[name*='page']",
                "[class*='page']",
                "[class*='per']",
                "[class*='items']"
            ]

            for selector in pagination_selectors:
                try:
                    elements = page.locator(selector)
                    count = elements.count()
                    if count > 0:
                        print(f"✅ Paginación '{selector}': {count} elementos")
                        for i in range(min(2, count)):
                            try:
                                attrs = elements.nth(i).evaluate("el => Object.fromEntries([...el.attributes].map(a => [a.name, a.value]))")
                                print(f"   Elemento {i}: {attrs}")
                            except:
                                pass
                except Exception as e:
                    print(f"⚠️ Error con selector paginación '{selector}': {e}")

            # Buscar el HTML completo de la página
            print("\n📄 Guardando HTML completo para análisis...")
            html_content = page.content()
            with open("debug_lists_page.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            print("💾 HTML guardado como debug_lists_page.html")

            input("\n⏸️ Presiona Enter para cerrar el browser...")

        except Exception as e:
            print(f"❌ Error durante el debugging: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    debug_lists_page()