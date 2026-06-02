"""
SubscribersListPage — página de suscriptores de una lista de correo.

Navega a /app/list/{id}/subscriber/list/ y encapsula:
- navegación a la lista
- paginación
- extracción de filas de suscriptores
"""

from playwright.sync_api import Page
from src.infrastructure.scraping.pages.base_page import BasePage
from src.shared.logging.logger import get_logger

logger = get_logger()


class SubscribersListPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page, url="")
        self._list_url_template = "https://acumbamail.com/app/list/{list_id}/subscriber/list/"

    def navigate_to_list(self, list_id: int) -> bool:
        url = self._list_url_template.format(list_id=list_id)
        try:
            self._page.goto(url, wait_until="networkidle", timeout=60000)
            self._page.wait_for_load_state("networkidle", timeout=15000)
            self._page.wait_for_timeout(2000)
            return True
        except Exception as e:
            logger.error(f"Error navigating to subscriber list {list_id}: {e}")
            return False

    def wait_for_table(self) -> bool:
        try:
            self._page.wait_for_load_state("networkidle", timeout=15000)
            self._page.wait_for_timeout(2000)
            table_present = self._page.locator("ul li").count() > 0
            return table_present
        except Exception as e:
            logger.error(f"Error waiting for subscriber table: {e}")
            return False

    def get_total_pages(self) -> int:
        from src.shared.utils.legacy_utils import obtener_total_paginas
        return obtener_total_paginas(self._page)

    def navigate_to_next_page(self, current_page: int) -> bool:
        from src.shared.utils.legacy_utils import navegar_siguiente_pagina
        return navegar_siguiente_pagina(self._page, current_page)

    def extract_subscribers_js(self, nombre_lista: str, list_id: int) -> list[dict]:
        """
        Extrae suscriptores usando JavaScript para parsear el HTML de la tabla.
        Retorna lista de diccionarios con datos del suscriptor.
        """
        logger.start_timer("extraer_suscriptores_tabla_lista")
        suscriptores = []

        try:
            self._page.wait_for_load_state("networkidle", timeout=15000)
            self._page.wait_for_timeout(2000)

            resultado = self._page.evaluate("""
                () => {
                    const listas = document.querySelectorAll('ul');
                    let listaTabla = null;
                    for (let ul of listas) {
                        const items = ul.querySelectorAll('li');
                        if (items.length > 5) {
                            const enlaces = ul.querySelectorAll('a[href*="subscriber/detail"]');
                            if (enlaces.length > 0) {
                                listaTabla = ul;
                                break;
                            }
                        }
                    }

                    if (!listaTabla) return { error: "No se encontró la tabla de suscriptores" };

                    const filas = listaTabla.querySelectorAll('li');
                    const encabezados = [];

                    if (filas.length > 0) {
                        const filaHeader = filas[0];
                        const elementos = filaHeader.querySelectorAll('span, div');
                        for (let elem of elementos) {
                            const text = elem.textContent.trim();
                            if (text && text.length > 2 && text.length < 50 &&
                                !text.includes('checkbox') && !text.includes('button') &&
                                !text.match(/^\\d+$/) && !encabezados.includes(text)) {
                                encabezados.push(text);
                            }
                        }
                    }

                    const datosFilas = [];
                    const emailsYaProcesados = new Set();

                    for (let i = 1; i < filas.length; i++) {
                        const fila = filas[i];
                        const linkEmail = fila.querySelector('a[href*="subscriber/detail"]');
                        let emailEncontrado = null;
                        if (linkEmail) {
                            emailEncontrado = linkEmail.textContent.trim();
                        }

                        if (!emailEncontrado || emailsYaProcesados.has(emailEncontrado)) {
                            continue;
                        }

                        emailsYaProcesados.add(emailEncontrado);
                        const celdas = [];

                        const spans = fila.querySelectorAll('span');
                        for (let span of spans) {
                            const text = span.textContent.trim();
                            if (text && text.length > 0 &&
                                !text.includes('checkbox') && !text.includes('button') &&
                                !text.includes('Ver') && !text.includes('Editar') &&
                                !text.includes('Eliminar') && !text.includes('✓') &&
                                !text.includes('×') && !text.match(/^\\d+$/) && text.length < 100) {
                                celdas.push(text);
                            }
                        }

                        if (celdas.length < 5) {
                            const divs = fila.querySelectorAll('div');
                            for (let div of divs) {
                                const text = div.textContent.trim();
                                if (text && text.length > 0 &&
                                    !text.includes('checkbox') && !text.includes('button') &&
                                    !text.includes('Ver') && !text.includes('Editar') &&
                                    !text.includes('Eliminar') && !text.includes('✓') &&
                                    !text.includes('×') && !text.match(/^\\d+$/) &&
                                    !celdas.includes(text) && text.length < 100) {
                                    celdas.push(text);
                                }
                            }
                        }

                        datosFilas.push({ email: emailEncontrado, textos: celdas });
                    }

                    return {
                        totalFilas: filas.length,
                        encabezados: encabezados,
                        datosFilas: datosFilas,
                        debug: { primeraFilaDatos: datosFilas.length > 0 ? datosFilas[0] : null }
                    };
                }
            """)

            if resultado.get("error"):
                print(f"❌ {resultado['error']}")
                return []

            encabezados = resultado["encabezados"]
            datos_filas = resultado["datosFilas"]
            total_filas = resultado["totalFilas"]

            print(f"📊 Total de filas encontradas: {total_filas}")
            print(f"📋 {len(encabezados)} encabezados detectados:")

            mapeo = {
                'correo electrónico': 'correo_electronico',
                'correo electronico': 'correo_electronico',
                'estado': 'estado',
                'fecha de alta': 'fecha_de_alta',
                'n organo': 'n_organo',
                'n órgano': 'n_organo',
                'observaciones': 'observaciones',
                'creacion': 'creacion',
                'creación': 'creacion',
                'activo (si/no)': 'activo_si_no',
                'activo si/no': 'activo_si_no',
                'perfil usuario': 'perfil_usuario',
                'funcion usuario': 'funcion_usuario',
                'función usuario': 'funcion_usuario',
                'id': 'id',
                'primer apellido': 'primer_apellido',
                'segundo apellido': 'segundo_apellido',
                'login': 'login',
                'rol usuario': 'rol_usuario',
                'fecha revision': 'fecha_revision',
                'fecha revisión': 'fecha_revision',
                'sede': 'sede',
                'organo': 'organo',
                'órgano': 'organo',
                'nombre': 'nombre',
                'calidad': 'calidad',
                'detalles': 'detalles'
            }

            def normalizar(nombre: str) -> str:
                nombre_lower = nombre.lower().strip()
                if nombre_lower in mapeo:
                    return mapeo[nombre_lower]
                resultado = nombre_lower
                for old, new in [(' ', '_'), ('.', '_'), ('(', ''), (')', ''),
                                 ('/', '_'), ('ó', 'o'), ('í', 'i'),
                                 ('á', 'a'), ('é', 'e'), ('ú', 'u'), ('ñ', 'n')]:
                    resultado = resultado.replace(old, new)
                return resultado

            for i, header in enumerate(encabezados):
                print(f"   {i}: '{header}' -> '{normalizar(header)}'")

            for fila_idx, datos_fila in enumerate(datos_filas):
                try:
                    suscriptor = {"lista": nombre_lista}
                    if datos_fila["email"] and "@" in datos_fila["email"]:
                        suscriptor["email"] = datos_fila["email"]

                    textos = datos_fila["textos"]
                    texto_idx = 0

                    for i, header in enumerate(encabezados):
                        nombre_columna = normalizar(header)
                        if nombre_columna == "correo_electronico":
                            continue
                        if texto_idx < len(textos):
                            valor = textos[texto_idx]
                            if valor and valor != "" and valor != "0" and valor != suscriptor.get("email", ""):
                                suscriptor[nombre_columna] = valor
                            texto_idx += 1

                    if suscriptor.get("email") and "@" in suscriptor["email"]:
                        suscriptores.append(suscriptor)
                        if len(suscriptores) <= 3:
                            print(f"✅ Suscriptor {len(suscriptores)}: {suscriptor}")

                    if (fila_idx + 1) % 50 == 0:
                        print(f"   📊 Procesadas {fila_idx + 1}/{len(datos_filas)} filas, {len(suscriptores)} suscriptores extraídos")

                except Exception as e:
                    print(f"❌ Error procesando fila {fila_idx}: {e}")
                    continue

            print(f"📊 Total suscriptores extraídos: {len(suscriptores)} de {len(datos_filas)} filas de datos")
            logger.end_timer("extraer_suscriptores_tabla_lista", f"Extraídos {len(suscriptores)} suscriptores")
            return suscriptores

        except Exception as e:
            print(f"❌ Error en extracción: {e}")
            logger.error(f"Error en extracción: {e}")
            logger.end_timer("extraer_suscriptores_tabla_lista", "Error")
            return []

    def scrape_all_pages(self, list_id: int, nombre_lista: str) -> list[dict]:
        """
        Realiza scraping completo de todos los suscriptores de una lista con paginación.
        """
        logger.info(f"Iniciando scraping de lista {list_id}: {nombre_lista}")

        if not self.navigate_to_list(list_id):
            logger.error(f"No se pudo navegar a lista {list_id}")
            return []

        if not self.wait_for_table():
            logger.error(f"No se encontró tabla de suscriptores para lista {list_id}")
            return []

        total_paginas = self.get_total_pages()
        logger.info(f"📄 Total de páginas a procesar: {total_paginas}")

        todos_suscriptores = []

        for numero_pagina in range(1, total_paginas + 1):
            logger.info(f"📃 Procesando página {numero_pagina}/{total_paginas}")

            try:
                suscriptores_pagina = self.extract_subscribers_js(nombre_lista, list_id)
                logger.info(f"✅ Página {numero_pagina}: {len(suscriptores_pagina)} suscriptores extraídos")
                todos_suscriptores.extend(suscriptores_pagina)

                if numero_pagina < total_paginas:
                    if not self.navigate_to_next_page(numero_pagina):
                        logger.error(f"No se pudo navegar a página {numero_pagina + 1}")
                        break

            except Exception as e:
                logger.error(f"Error procesando página {numero_pagina}: {e}")
                continue

        logger.info(f"✅ Scraping completado - Total: {len(todos_suscriptores)} suscriptores de lista {list_id}")
        return todos_suscriptores