"""Operaciones con la API de Acumbamail para segmentos."""
import pandas as pd
from typing import Dict, List, Optional

from ..logger import get_logger
from ..infrastructure.api import API
from ..infrastructure.api.models.suscriptores import SubscriberData
from ..scrapping.endpoints import SegmentsScrapingService

logger = get_logger()


def obtener_id_lista_por_nombre(nombre_lista: str, api_client: API) -> Optional[int]:
    try:
        listas = api_client.suscriptores.get_lists()
        for lista in listas:
            if lista.name == nombre_lista:
                return lista.id
        logger.warning(f"Lista '{nombre_lista}' no encontrada en Acumbamail")
        return None
    except Exception as e:
        logger.error(f"Error buscando lista '{nombre_lista}': {e}")
        return None


def verificar_y_crear_campos_segmentacion(list_id: int, headers: List[str], api_client: API) -> bool:
    try:
        campos_existentes = api_client.suscriptores.get_merge_fields(list_id)

        nombres_campos = []
        if hasattr(campos_existentes, 'merge_fields'):
            mf = getattr(campos_existentes, 'merge_fields')
            if isinstance(mf, dict):
                nombres_campos = list(mf.keys())
            elif isinstance(mf, list):
                for campo in mf:
                    if isinstance(campo, dict):
                        name_val = campo.get('name')
                        if name_val:
                            nombres_campos.append(str(name_val))
                    elif hasattr(campo, 'name'):
                        try:
                            nombres_campos.append(str(getattr(campo, 'name')))
                        except Exception:
                            continue
        else:
            if isinstance(campos_existentes, dict):
                nombres_campos = list(campos_existentes.keys())
            elif isinstance(campos_existentes, list):
                for campo in campos_existentes:
                    if isinstance(campo, dict):
                        name_val = campo.get('name')
                        if name_val:
                            nombres_campos.append(str(name_val))
                    elif hasattr(campo, 'name'):
                        try:
                            nombres_campos.append(str(getattr(campo, 'name')))
                        except Exception:
                            continue

        logger.info(f"Campos existentes en lista {list_id}: {nombres_campos}")

        campos_a_crear = []
        if "Segmentos" not in nombres_campos:
            campos_a_crear.append(("Segmentos", "text"))

        for header in headers[1:]:
            if header not in nombres_campos:
                campos_a_crear.append((header, "text"))

        for nombre_campo, tipo_campo in campos_a_crear:
            try:
                logger.info(f"Creando campo '{nombre_campo}' tipo '{tipo_campo}' en lista {list_id}")
                api_client.suscriptores.add_merge_tag(list_id, nombre_campo, tipo_campo)
                print(f"  ✅ Campo '{nombre_campo}' creado exitosamente")
            except Exception as e:
                logger.error(f"Error creando campo '{nombre_campo}': {e}")
                print(f"  ❌ Error creando campo '{nombre_campo}': {e}")

        if campos_a_crear:
            logger.info(f"Creados {len(campos_a_crear)} campos en lista {list_id}")
        else:
            logger.info(f"Todos los campos necesarios ya existen en lista {list_id}")

        return True

    except Exception as e:
        logger.error(f"Error verificando/creando campos en lista {list_id}: {e}")
        return False


def obtener_usuarios_existentes_con_segmentos(list_id: int, api_client: API) -> Dict[str, str]:
    try:
        usuarios_con_segmentos = {}
        block_index = 0

        while True:
            try:
                suscriptores = api_client.suscriptores.get_subscribers(
                    list_id=list_id, block_index=block_index,
                    all_fields=1, complete_json=1
                )
            except Exception as e:
                if "No subscribers" in str(e):
                    logger.info(f"Lista {list_id} está vacía")
                    break
                raise e

            if not suscriptores:
                break

            for suscriptor in suscriptores:
                email = suscriptor.email
                try:
                    segmentos = getattr(suscriptor, 'Segmentos', None) or ''
                    if not segmentos:
                        segmentos = getattr(suscriptor, 'segmentos', None) or ''
                except AttributeError:
                    segmentos = ''

                if segmentos and segmentos.strip():
                    usuarios_con_segmentos[email] = segmentos

            if len(suscriptores) < 1000:
                break
            block_index += 1

        logger.info(f"Encontrados {len(usuarios_con_segmentos)} usuarios con segmentos existentes")
        return usuarios_con_segmentos

    except Exception as e:
        if "No subscribers" in str(e):
            logger.info(f"Lista {list_id} está vacía (sin suscriptores)")
            return {}
        logger.error(f"Error obteniendo usuarios con segmentos: {e}")
        return {}


def eliminar_usuarios_de_lista(emails: List[str], list_id: int, api_client: API) -> bool:
    try:
        if not emails:
            return True

        logger.info(f"Eliminando {len(emails)} usuarios de lista {list_id}")

        for email in emails:
            try:
                api_client.suscriptores.delete_subscriber(list_id, email)
            except Exception as e:
                logger.warning(f"Error eliminando usuario {email}: {e}")

        logger.info(f"Proceso de eliminación completado para {len(emails)} usuarios")
        return True
    except Exception as e:
        logger.error(f"Error eliminando usuarios: {e}")
        return False


def subir_usuarios_actualizados(df: pd.DataFrame, list_id: int, api_client: API) -> int:
    try:
        usuarios_subidos = 0
        subscribers_batch = []
        batch_size = 100

        for _, row in df.iterrows():
            try:
                merge_fields = {"email": str(row["email"]).strip()}

                if "Segmentos" in df.columns and pd.notna(row["Segmentos"]) and str(row["Segmentos"]).strip():
                    merge_fields["Segmentos"] = str(row["Segmentos"]).strip()

                for col in df.columns:
                    if col not in ["email", "Segmentos"] and pd.notna(row[col]) and str(row[col]).strip():
                        merge_fields[col] = str(row[col]).strip()

                if not merge_fields.get("email"):
                    logger.warning(f"Fila sin email válido: {row.to_dict()}")
                    continue

                subscriber_data = SubscriberData(
                    email=merge_fields["email"],
                    **{k: v for k, v in merge_fields.items() if k != "email"}
                )
                subscribers_batch.append(subscriber_data)

                if len(subscribers_batch) >= batch_size:
                    result = api_client.suscriptores.batch_add_subscribers(
                        list_id=list_id, subscribers_data=subscribers_batch,
                        update_subscriber=1, complete_json=1
                    )
                    usuarios_subidos += result.success_count
                    logger.info(f"Lote procesado: {result.success_count} exitosos, {result.error_count} errores")
                    subscribers_batch.clear()

            except Exception as e:
                logger.warning(f"Error preparando usuario {row.get('email', 'unknown')}: {e}")
                continue

        if subscribers_batch:
            result = api_client.suscriptores.batch_add_subscribers(
                list_id=list_id, subscribers_data=subscribers_batch,
                update_subscriber=1, complete_json=1
            )
            usuarios_subidos += result.success_count
            logger.info(f"Último lote procesado: {result.success_count} exitosos, {result.error_count} errores")

        logger.info(f"Subidos {usuarios_subidos} usuarios a lista {list_id}")
        return usuarios_subidos

    except Exception as e:
        logger.error(f"Error subiendo usuarios: {e}")
        return 0


def crear_segmentos_con_scraping_batch(list_id: int, segmentos_nombres: List[str], api_client: API) -> bool:
    service = SegmentsScrapingService()
    return service.create_segments_batch(list_id, segmentos_nombres, api_client)
