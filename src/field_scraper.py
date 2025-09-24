"""
Utilidad para obtener los campos disponibles en una lista de Acumbamail mediante scraping
Utiliza la misma técnica que descargar_suscriptores.py para detectar campos dinámicamente
"""
from typing import List, Dict, Set, Optional
from playwright.sync_api import Page
from .logger import get_logger

def obtener_campos_disponibles_acumba(page: Page, list_id: int) -> Dict[str, List[str]]:
    """
    Obtiene los campos disponibles en una lista de Acumbamail mediante scraping

    Returns:
        Dict con:
        - 'fields': Lista de nombres de campos disponibles
        - 'required': Lista de campos requeridos (como 'email')
        - 'optional': Lista de campos opcionales
    """
    logger = get_logger()
    logger.info(f"Obteniendo campos disponibles para lista {list_id}")

    try:
        # Navegar a la lista de suscriptores
        url = f"https://acumbamail.com/app/list/{list_id}/subscriber/list/"
        page.goto(url, timeout=30000)
        page.wait_for_load_state("networkidle", timeout=30000)

        # Usar el mismo JavaScript que descargar_suscriptores para detectar campos
        resultado = page.evaluate("""
            () => {
                // Buscar todas las listas UL
                const listas = document.querySelectorAll('ul');

                // Buscar la lista que contenga enlaces de suscriptores
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

                // Extraer encabezados de la primera fila
                const encabezados = [];
                if (filas.length > 0) {
                    const filaHeader = filas[0];

                    // Buscar spans que contengan texto de encabezados
                    const elementos = filaHeader.querySelectorAll('span, div');
                    for (let elem of elementos) {
                        const text = elem.textContent.trim();
                        // Filtrar solo los textos que parecen encabezados de columna
                        if (text && text.length > 2 && text.length < 50 &&
                            !text.includes('checkbox') && !text.includes('button') &&
                            !text.match(/^\\d+$/) && !encabezados.includes(text)) {
                            encabezados.push(text);
                        }
                    }
                }

                return {
                    encabezados: encabezados,
                    totalFilas: filas.length
                };
            }
        """)

        if resultado.get("error"):
            logger.error(f"Error obteniendo campos: {resultado['error']}")
            return {"fields": [], "required": ["email"], "optional": []}

        campos = resultado.get("encabezados", [])
        logger.info(f"Campos detectados: {campos}")

        # Clasificar campos
        campos_requeridos = []
        campos_opcionales = []

        for campo in campos:
            campo_lower = campo.lower()
            if any(keyword in campo_lower for keyword in ["correo", "email", "e-mail"]):
                campos_requeridos.append(campo)
            else:
                campos_opcionales.append(campo)

        # Asegurar que 'email' esté en requeridos
        if not any("email" in c.lower() or "correo" in c.lower() for c in campos_requeridos):
            campos_requeridos.append("email")

        return {
            "fields": campos,
            "required": campos_requeridos,
            "optional": campos_opcionales
        }

    except Exception as e:
        logger.error(f"Error obteniendo campos disponibles: {e}")
        # Fallback con campos básicos comunes
        return {
            "fields": ["Correo electrónico", "Estado", "Fecha de alta"],
            "required": ["email"],
            "optional": ["Estado", "Fecha de alta"]
        }

def normalizar_nombre_campo(nombre: str) -> str:
    """
    Normaliza nombre de campo para comparación
    """
    # Mapeo de nombres comunes
    mapeo = {
        'correo electrónico': 'email',
        'correo electronico': 'email',
        'e-mail': 'email',
        'email': 'email',
        'estado': 'estado',
        'fecha de alta': 'fecha_de_alta',
        'fecha alta': 'fecha_de_alta',
        'segmentos': 'segmentos',
        'perfil usuario': 'perfil_usuario',
        'rol usuario': 'rol_usuario',
        'primer apellido': 'primer_apellido',
        'segundo apellido': 'segundo_apellido',
        'nombre': 'nombre',
        'sede': 'sede',
        'organo': 'organo',
        'órgano': 'organo',
    }

    nombre_lower = nombre.lower().strip()

    # Buscar en mapeo exacto primero
    if nombre_lower in mapeo:
        return mapeo[nombre_lower]

    # Normalización automática
    resultado = nombre_lower
    resultado = resultado.replace(' ', '_')
    resultado = resultado.replace('.', '_')
    resultado = resultado.replace('(', '')
    resultado = resultado.replace(')', '')
    resultado = resultado.replace('/', '_')
    resultado = resultado.replace('ó', 'o')
    resultado = resultado.replace('í', 'i')
    resultado = resultado.replace('á', 'a')
    resultado = resultado.replace('é', 'e')
    resultado = resultado.replace('ú', 'u')
    resultado = resultado.replace('ñ', 'n')

    return resultado

def filtrar_campos_necesarios(campos_excel: List[str], campos_acumba: List[str]) -> Dict[str, List[str]]:
    """
    Filtra qué campos del Excel son necesarios basándose en los disponibles en Acumba

    Returns:
        Dict con:
        - 'crear': Campos que necesitan crearse
        - 'mapear': Campos que ya existen y se pueden mapear
        - 'ignorar': Campos que no son necesarios
    """
    logger = get_logger()

    # Normalizar campos para comparación
    campos_excel_norm = {normalizar_nombre_campo(c): c for c in campos_excel}
    campos_acumba_norm = [normalizar_nombre_campo(c) for c in campos_acumba]

    campos_crear = []
    campos_mapear = []
    campos_ignorar = []

    for campo_norm, campo_original in campos_excel_norm.items():
        if campo_norm == 'email':
            # Email siempre se mapea, nunca se crea
            campos_mapear.append(campo_original)
        elif campo_norm in campos_acumba_norm:
            # Campo ya existe en Acumba, se puede mapear
            campos_mapear.append(campo_original)
        else:
            # Verificar si es un campo que vale la pena crear
            if vale_la_pena_crear_campo(campo_original):
                campos_crear.append(campo_original)
            else:
                campos_ignorar.append(campo_original)

    logger.info(f"Campos a crear: {campos_crear}")
    logger.info(f"Campos a mapear: {campos_mapear}")
    logger.info(f"Campos a ignorar: {campos_ignorar}")

    return {
        "crear": campos_crear,
        "mapear": campos_mapear,
        "ignorar": campos_ignorar
    }

def vale_la_pena_crear_campo(nombre_campo: str) -> bool:
    """
    Determina si un campo vale la pena crearlo en Acumba
    """
    nombre_lower = nombre_campo.lower().strip()

    # Campos que NO vale la pena crear (son metadatos o temporales)
    ignorar_patrones = [
        'unnamed',  # Columnas sin nombre de pandas
        'index',    # Índices
        'temp',     # Temporales
        'aux',      # Auxiliares
        'helper',   # Ayudantes
        'fecha_proceso',  # Metadatos de procesamiento
        'timestamp',      # Timestamps de procesamiento
        'version',        # Control de versiones
    ]

    # Verificar patrones de ignore
    for patron in ignorar_patrones:
        if patron in nombre_lower:
            return False

    # Campos que empiecen con guión bajo (privados/internos)
    if nombre_campo.startswith('_'):
        return False

    # Campos muy cortos probablemente no son útiles
    if len(nombre_lower) < 2:
        return False

    # Campos muy largos probablemente son errores
    if len(nombre_lower) > 50:
        return False

    # Si llegamos aquí, el campo es válido para crear
    return True