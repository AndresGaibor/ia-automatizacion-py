"""Operaciones remotas: verificación de listas, obtención y comparación de suscriptores."""

from typing import Dict, Any, Set

import pandas as pd

from ....infrastructure.api import API
from ....shared.logging.logger import get_logger


def verificar_lista_existe_remota(list_id: int, api: API) -> bool:
    """
    Verifica si una lista existe en el servidor remoto

    Args:
        list_id: ID de la lista a verificar
        api: Instancia de API

    Returns:
        True si la lista existe, False en caso contrario
    """
    logger = get_logger()

    try:
        listas = api.suscriptores.get_lists()

        for lista in listas:
            if lista.id == list_id:
                logger.info(f"Lista {list_id} '{lista.name}' existe en el servidor")
                return True

        logger.info(f"Lista {list_id} no existe en el servidor")
        return False

    except Exception as e:
        logger.warning(f"Error verificando lista {list_id}: {e}")
        return False


def obtener_suscriptores_remotos(list_id: int, api: API) -> Set[str]:
    """
    Obtiene los emails de suscriptores de una lista remota

    Args:
        list_id: ID de la lista
        api: Instancia de API

    Returns:
        Set con los emails de los suscriptores remotos
    """
    logger = get_logger()

    try:
        subscribers = api.suscriptores.get_subscribers(list_id)

        emails_remotos = set()
        if subscribers:
            for subscriber in subscribers:
                if subscriber.email:
                    emails_remotos.add(subscriber.email.lower())

        logger.info(f"Lista {list_id}: {len(emails_remotos)} suscriptores remotos encontrados")
        return emails_remotos

    except Exception as e:
        logger.error(f"Error obteniendo suscriptores de lista {list_id}: {e}")
        return set()


def comparar_suscriptores_local_vs_remoto(df_local: pd.DataFrame, emails_remotos: Set[str]) -> Dict[str, Any]:
    """
    Compara suscriptores locales vs remotos para encontrar nuevos

    Args:
        df_local: DataFrame con suscriptores locales
        emails_remotos: Set con emails remotos

    Returns:
        Dict con información de la comparación
    """
    logger = get_logger()

    email_column = None
    possible_email_columns = ['email', 'Email', 'EMAIL', 'Correo Electrónico', 'Correo', 'correo', 'e-mail', 'E-mail']

    for col_name in possible_email_columns:
        if col_name in df_local.columns:
            email_column = col_name
            break

    if not email_column:
        print(f"⚠️ No se encontró columna de email. Columnas disponibles: {list(df_local.columns)}")
        return {
            'total_locales': 0,
            'total_remotos': len(emails_remotos),
            'emails_nuevos': set(),
            'cantidad_nuevos': 0,
            'df_nuevos': pd.DataFrame(),
            'tiene_nuevos': False,
            'error': f'No se encontró columna de email en: {list(df_local.columns)}'
        }

    print(f"📧 Usando columna de email: '{email_column}'")

    emails_locales = set(df_local[email_column].dropna().astype(str).str.lower())
    emails_nuevos = emails_locales - emails_remotos

    df_nuevos = pd.DataFrame()
    if emails_nuevos:
        mask = df_local[email_column].astype(str).str.lower().isin(emails_nuevos)
        df_nuevos = df_local[mask].copy()

        if email_column != 'email':
            df_nuevos = df_nuevos.rename(columns={email_column: 'email'})

    resultado = {
        'total_locales': len(emails_locales),
        'total_remotos': len(emails_remotos),
        'emails_nuevos': emails_nuevos,
        'cantidad_nuevos': len(emails_nuevos),
        'df_nuevos': df_nuevos,
        'tiene_nuevos': len(emails_nuevos) > 0,
        'email_column_used': email_column
    }

    logger.info(f"Comparación: {resultado['total_locales']} locales, "
               f"{resultado['total_remotos']} remotos, "
               f"{resultado['cantidad_nuevos']} nuevos")

    return resultado
