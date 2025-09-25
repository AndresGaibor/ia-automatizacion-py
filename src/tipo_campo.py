import unicodedata
from typing import Optional
from urllib.parse import urlparse  # <-- añadido

try:
    from .logger import get_logger
    logger = get_logger()
except ImportError:
    # Fallback si no se puede importar logger
    import logging
    logger = logging.getLogger(__name__)

# Mapa oficial value -> etiqueta (según tu <select>)
VALUE_TO_LABEL = {
    "1": "Texto",
    "2": "Checkbox",
    "10": "Lista",
    "3": "Número entero",
    "4": "Número decimal",
    "5": "Fecha",
    "7": "Texto largo",
    "8": "Ip",
    "9": "Url",
}

# Normaliza strings (minúsculas, sin acentos, sin espacios ni guiones)
def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.lower().replace(" ", "").replace("-", "").replace("_", "")

# Sinónimos/variantes de nombre -> etiqueta canónica
NAME_TO_LABEL = {
    _norm("Texto"): "Texto",
    _norm("Checkbox"): "Checkbox",
    _norm("Lista"): "Lista",
    _norm("Número entero"): "Número entero",
    _norm("Entero"): "Número entero",
    _norm("Número decimal"): "Número decimal",
    _norm("Decimal"): "Número decimal",
    _norm("Fecha"): "Fecha",
    _norm("Texto largo"): "Texto largo",
    _norm("Long text"): "Texto largo",
    _norm("Ip"): "Ip",
    _norm("IP"): "Ip",
    _norm("Url"): "Url",
    _norm("URL"): "Url",
}

def field_type_label(value_or_name: str, *, default: str = "Texto") -> str:
    """
    Devuelve la etiqueta visible del tipo de campo (p. ej., 'Texto', 'Url').
    Acepta el 'value' del <option> (p. ej., '1', '9', '10') o el nombre del tipo
    en texto (con/sin acentos, mayúsculas o sinónimos). Si no se reconoce, devuelve 'Texto'.
    """
    if value_or_name is None:
        logger.debug("Tipo de campo: valor es None, usando default", default=default)
        return default

    s = str(value_or_name).strip()
    logger.debug("Identificando tipo de campo", valor_original=value_or_name, valor_procesado=s, default=default)

    # 1) Si coincide con un value conocido (como string)
    if s in VALUE_TO_LABEL:
        result = VALUE_TO_LABEL[s]
        logger.debug("Tipo de campo identificado por VALUE_TO_LABEL", valor=s, tipo=result)
        return result

    # 2) Si parece numérico (por si pasan 1 en vez de "1")
    if s.isdigit() and s in VALUE_TO_LABEL:
        result = VALUE_TO_LABEL[s]
        logger.debug("Tipo de campo identificado por valor numérico", valor=s, tipo=result)
        return result

    # 3) Intentar por nombre normalizado
    n = _norm(s)
    if n in NAME_TO_LABEL:
        result = NAME_TO_LABEL[n]
        logger.debug("Tipo de campo identificado por nombre normalizado", nombre_original=s, nombre_normalizado=n, tipo=result)
        return result

    # 4) Heurísticas básicas por valor de ejemplo
    if _looks_like_url(s):
        logger.debug("Tipo de campo identificado como URL por heurística", valor=s)
        return "Url"
    if _looks_like_int(s):
        logger.debug("Tipo de campo identificado como entero por heurística", valor=s)
        return "Número entero"
    if _looks_like_float(s):
        logger.debug("Tipo de campo identificado como decimal por heurística", valor=s)
        return "Número decimal"

    # 5) Fallback
    logger.debug("Tipo de campo no reconocido, usando default", valor=value_or_name, default=default)
    return default

# Heurísticas simples
def _looks_like_url(s: str) -> bool:
    try:
        p = urlparse(s)
        result = (p.scheme in ("http", "https") and bool(p.netloc)) or (s.lower().startswith("www.") and "." in s)
        logger.debug("Heurística URL", valor=s, es_url=result)
        return result
    except Exception:
        logger.debug("Heurística URL fallida", valor=s)
        return False

def _looks_like_int(s: str) -> bool:
    try:
        result = s.isdigit()
        logger.debug("Heurística entero", valor=s, es_entero=result)
        return result
    except Exception:
        logger.debug("Heurística entero fallida", valor=s)
        return False

def _looks_like_float(s: str) -> bool:
    try:
        s2 = s.replace(",", ".")
        result = float(s2) and not _looks_like_int(s)  # evitar clasificar enteros como decimales
        logger.debug("Heurística decimal", valor=s, valor_convertido=s2, es_decimal=result)
        return result
    except ValueError:
        logger.debug("Heurística decimal fallida", valor=s)
        return False

