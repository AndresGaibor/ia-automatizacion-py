"""
Utilidad para obtener los campos disponibles en una lista de Acumbamail mediante scraping
Utiliza la misma técnica que descargar_suscriptores.py para detectar campos dinámicamente
"""
from typing import List, Dict
from playwright.sync_api import Page
from ..pages.fields_page import PaginaCampos as FieldsPage
from ....shared.logging.logger import get_logger


def obtener_campos_disponibles_acumba(page: Page, list_id: int) -> Dict[str, List[str]]:
    """
    Obtiene los campos disponibles en una lista de Acumbamail mediante scraping
    MEJORADO para detectar mejor los campos y evitar duplicados

    Returns:
        Dict con:
        - 'fields': Lista de nombres de campos disponibles
        - 'required': Lista de campos requeridos (como 'email')
        - 'optional': Lista de campos opcionales
    """
    logger = get_logger()
    logger.info(f"Obteniendo campos disponibles para lista {list_id}")

    try:
        fields_page = FieldsPage(page)

        if not fields_page.navigate_to(list_id):
            logger.info("No se pudo navegar a página de campos, intentando desde lista de suscriptores...")
            if not fields_page.navigate_to_subscribers_fallback(list_id):
                raise Exception("No se pudo navegar a página de campos ni a suscriptores")

        campos_desde_pagina_campos = fields_page.extract_fields_from_page()
        logger.info(f"Campos detectados desde página de campos: {campos_desde_pagina_campos}")

        if not campos_desde_pagina_campos or len(campos_desde_pagina_campos) == 0:
            logger.info("No se encontraron campos en la página de campos, intentando desde lista de suscriptores...")
            if not fields_page.navigate_to_subscribers_fallback(list_id):
                raise Exception("No se pudo navegar a suscriptores como fallback")
            campos = fields_page.extract_fields_from_subscribers()
        else:
            campos = campos_desde_pagina_campos

        campos_limpios = []
        campos_vistos = set()

        for campo in campos:
            campo_limpio = campo.strip()
            campo_norm = normalizar_nombre_campo(campo_limpio)

            if campo_norm not in campos_vistos and campo_limpio:
                campos_limpios.append(campo_limpio)
                campos_vistos.add(campo_norm)
            else:
                logger.info(f"Campo duplicado omitido: {campo_limpio} (normalizado: {campo_norm})")

        logger.info(f"Campos detectados (sin duplicados): {campos_limpios}")

        campos_requeridos = []
        campos_opcionales = []

        for campo in campos_limpios:
            campo_lower = campo.lower()
            if any(keyword in campo_lower for keyword in ["correo", "email", "e-mail"]):
                campos_requeridos.append(campo)
            else:
                campos_opcionales.append(campo)

        if not any("email" in c.lower() or "correo" in c.lower() for c in campos_requeridos):
            campos_requeridos.append("email")

        return {
            "fields": campos_limpios,
            "required": campos_requeridos,
            "optional": campos_opcionales
        }

    except Exception as e:
        logger.error(f"Error obteniendo campos disponibles: {e}")
        return {
            "fields": ["Correo electrónico", "Estado", "Fecha de alta"],
            "required": ["email"],
            "optional": ["Estado", "Fecha de alta"]
        }


def normalizar_nombre_campo(nombre: str) -> str:
    """
    Normaliza nombre de campo para comparación con mejor detección de duplicados
    """
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
        'perfilusuario': 'perfil_usuario',
        'rol usuario': 'rol_usuario',
        'rolusuario': 'rol_usuario',
        'rol_usuario': 'rol_usuario',
        'primer apellido': 'primer_apellido',
        'segundo apellido': 'segundo_apellido',
        'nombre': 'nombre',
        'sede': 'sede',
        'organo': 'organo',
        'órgano': 'organo',
        'n organo': 'n_organo',
        'norgano': 'n_organo',
    }

    nombre_lower = nombre.lower().strip()

    if nombre_lower in mapeo:
        return mapeo[nombre_lower]

    resultado = nombre_lower
    resultado = resultado.replace(' ', '_')
    resultado = resultado.replace('.', '_')
    resultado = resultado.replace('(', '')
    resultado = resultado.replace(')', '')
    resultado = resultado.replace('/', '_')
    resultado = resultado.replace('-', '_')
    resultado = resultado.replace('ó', 'o')
    resultado = resultado.replace('í', 'i')
    resultado = resultado.replace('á', 'a')
    resultado = resultado.replace('é', 'e')
    resultado = resultado.replace('ú', 'u')
    resultado = resultado.replace('ñ', 'n')

    while '__' in resultado:
        resultado = resultado.replace('__', '_')

    resultado = resultado.strip('_')

    return resultado


def filtrar_campos_necesarios(campos_excel: List[str], campos_acumba: List[str]) -> Dict[str, List[str]]:
    """
    Filtra qué campos del Excel son necesarios basándose en los disponibles en Acumba
    CON DETECCIÓN MEJORADA DE DUPLICADOS

    Returns:
        Dict con:
        - 'crear': Campos que necesitan crearse
        - 'mapear': Campos que ya existen y se pueden mapear
        - 'ignorar': Campos que no son necesarios
    """
    logger = get_logger()

    campos_acumba_norm = [normalizar_nombre_campo(c) for c in campos_acumba]

    mapeo_acumba = {}
    for campo_acumba in campos_acumba:
        norm = normalizar_nombre_campo(campo_acumba)
        if norm not in mapeo_acumba:
            mapeo_acumba[norm] = []
        mapeo_acumba[norm].append(campo_acumba)

    campos_crear = []
    campos_mapear = []
    campos_ignorar = []

    campos_ya_procesados = set()

    for campo_original in campos_excel:
        campo_norm = normalizar_nombre_campo(campo_original)

        if campo_norm in campos_ya_procesados:
            logger.info(f"Campo duplicado detectado y omitido: {campo_original} (normalizado: {campo_norm})")
            campos_ignorar.append(campo_original)
            continue

        if campo_norm == 'email':
            campos_mapear.append(campo_original)
        elif campo_norm in campos_acumba_norm:
            campos_mapear.append(campo_original)
            campos_equivalentes = mapeo_acumba.get(campo_norm, [])
            logger.info(f"Mapeando '{campo_original}' -> {campos_equivalentes}")
        else:
            if vale_la_pena_crear_campo(campo_original):
                campos_crear.append(campo_original)
            else:
                campos_ignorar.append(campo_original)

        campos_ya_procesados.add(campo_norm)

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

    ignorar_patrones = [
        'unnamed',
        'index',
        'temp',
        'aux',
        'helper',
        'fecha_proceso',
        'timestamp',
        'version',
    ]

    for patron in ignorar_patrones:
        if patron in nombre_lower:
            return False

    if nombre_campo.startswith('_'):
        return False

    if len(nombre_lower) < 2:
        return False

    if len(nombre_lower) > 50:
        return False

    return True