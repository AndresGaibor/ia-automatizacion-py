import unicodedata
from typing import Optional
from urllib.parse import urlparse  # <-- añadido

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
        return default

    s = str(value_or_name).strip()

    # 1) Si coincide con un value conocido (como string)
    if s in VALUE_TO_LABEL:
        return VALUE_TO_LABEL[s]

    # 2) Si parece numérico (por si pasan 1 en vez de "1")
    if s.isdigit() and s in VALUE_TO_LABEL:
        return VALUE_TO_LABEL[s]

    # 3) Intentar por nombre normalizado
    n = _norm(s)
    if n in NAME_TO_LABEL:
        return NAME_TO_LABEL[n]

    # 4) Heurísticas básicas por valor de ejemplo
    if _looks_like_url(s):
        return "Url"
    if _looks_like_int(s):
        return "Número entero"
    if _looks_like_float(s):
        return "Número decimal"

    # 5) Fallback
    return default

# Heurísticas simples
def _looks_like_url(s: str) -> bool:
    p = urlparse(s)
    return (p.scheme in ("http", "https") and bool(p.netloc)) or (s.lower().startswith("www.") and "." in s)

def _looks_like_int(s: str) -> bool:
    return s.isdigit()

def _looks_like_float(s: str) -> bool:
    s2 = s.replace(",", ".")
    try:
        float(s2)
        return not _looks_like_int(s)  # evitar clasificar enteros como decimales
    except ValueError:
        return False

