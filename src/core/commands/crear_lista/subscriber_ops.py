"""Operaciones de suscriptores: campos personalizados, API, verificación."""

from typing import Optional, Dict, Any

import pandas as pd

from ....infrastructure.api import API
from ....infrastructure.api.models.suscriptores import SubscriberData, FieldType
from ....shared.logging.logger import get_logger


def crear_campos_personalizados(list_id: int, df_suscriptores: pd.DataFrame, api: API, page=None) -> bool:
    """
    Crea campos personalizados inteligentemente basándose en los campos disponibles en Acumba.
    Usa scraping para verificar qué campos ya existen y evita crear duplicados.

    Args:
        list_id: ID de la lista
        df_suscriptores: DataFrame con los datos de suscriptores
        api: Instancia de API
        page: Página de Playwright para scraping (opcional)

    Returns:
        bool: True si se crearon exitosamente
    """
    logger = get_logger()

    try:
        campos_excel = [col for col in df_suscriptores.columns if col != 'email']

        if not campos_excel:
            logger.info("No hay campos personalizados para procesar")
            return True

        print(f"🔍 Analizando {len(campos_excel)} campos del Excel...")

        campos_acumba = []
        if page:
            try:
                from ....infrastructure.scraping.utils.field_scraper import obtener_campos_disponibles_acumba, filtrar_campos_necesarios

                print("📊 Obteniendo campos disponibles en Acumbamail...")
                info_campos = obtener_campos_disponibles_acumba(page, list_id)
                campos_acumba = info_campos.get("fields", [])

                print(f"📋 Campos detectados en Acumba: {len(campos_acumba)}")
                for campo in campos_acumba[:5]:
                    print(f"   • {campo}")
                if len(campos_acumba) > 5:
                    print(f"   • ... y {len(campos_acumba) - 5} más")

                filtrado = filtrar_campos_necesarios(campos_excel, campos_acumba)
                campos_crear = filtrado["crear"]
                campos_mapear = filtrado["mapear"]
                campos_ignorar = filtrado["ignorar"]

                print(f"🆕 Campos nuevos a crear: {len(campos_crear)}")
                print(f"🔗 Campos existentes a mapear: {len(campos_mapear)}")
                print(f"🚫 Campos a ignorar: {len(campos_ignorar)}")

                if campos_ignorar:
                    print("📋 Campos ignorados:")
                    for campo in campos_ignorar:
                        print(f"   • {campo}")

            except Exception as e:
                logger.warning(f"Error en scraping de campos, usando modo fallback: {e}")
                campos_crear = campos_excel
        else:
            logger.info("No hay página disponible para scraping, usando modo legacy")
            campos_crear = campos_excel

        if not campos_crear:
            print("✅ No se necesitan crear campos nuevos")
            return True

        print(f"🔧 Creando {len(campos_crear)} campos personalizados necesarios...")

        campos_creados = 0
        campos_fallidos = 0

        for campo in campos_crear:
            try:
                campo_normalizado = campo.replace(' ', '_').replace('-', '_')

                api.suscriptores.add_merge_tag(
                    list_id=list_id,
                    field_name=campo_normalizado,
                    field_type=FieldType.TEXT
                )

                campos_creados += 1
                print(f"   ✅ {campo} -> {campo_normalizado}")
                logger.info(f"Campo '{campo_normalizado}' creado exitosamente")

            except Exception as e:
                campos_fallidos += 1
                print(f"   ❌ {campo}: {e}")
                logger.warning(f"Error creando campo '{campo}': {e}")

        print(f"📊 Resultado: {campos_creados} exitosos, {campos_fallidos} fallidos")
        return campos_creados > 0

    except Exception as e:
        logger.error(f"Error general creando campos personalizados: {e}")
        print(f"❌ Error creando campos personalizados: {e}")
        return False


def crear_lista_via_api(nombre_lista: str, config_lista: Dict[str, str], api: API) -> Optional[int]:
    """
    Crea una lista usando la API de suscriptores
    """
    logger = get_logger()

    try:
        list_id = api.suscriptores.create_list(
            sender_email=config_lista.get('sender_email', 'admin@example.com'),
            name=nombre_lista,
            company=config_lista.get('company', 'Mi Empresa'),
            country=config_lista.get('country', 'España'),
            city=config_lista.get('city', 'Madrid'),
            address=config_lista.get('address', 'Calle Principal 123'),
            phone=config_lista.get('phone', '+34 900 000 000')
        )

        logger.info(f"Lista creada exitosamente: {nombre_lista} (ID: {list_id})")
        return list_id

    except Exception as e:
        logger.error(f"Error creando lista {nombre_lista}: {e}")
        print(f"Error creando lista {nombre_lista}: {e}")
        return None


def verificar_y_mostrar_campos(list_id: int, df_suscriptores: pd.DataFrame, api: API) -> bool:
    """
    Verifica los campos de la lista después de agregar suscriptores
    """
    logger = get_logger()

    try:
        print(f"🔍 Verificando campos de la lista {list_id}...")

        campos_respuesta = api.suscriptores.get_merge_fields(list_id)

        if hasattr(campos_respuesta, 'merge_fields') and campos_respuesta.merge_fields:
            campos_existentes = list(campos_respuesta.merge_fields.keys())
            print(f"📋 Campos existentes en la lista: {campos_existentes}")

            campos_esperados = [col.replace(' ', '_').replace('-', '_') for col in df_suscriptores.columns if col != 'email']
            campos_faltantes = [c for c in campos_esperados if c not in campos_existentes]

            if campos_faltantes:
                print(f"⚠️  Campos faltantes en la lista: {campos_faltantes}")
                print("💡 Esto puede indicar que los campos no se enviaron correctamente")
            else:
                print(f"✅ Todos los campos esperados están presentes: {campos_esperados}")

        else:
            print(f"⚠️  No se encontraron merge fields en la lista {list_id}")

        return True

    except Exception as e:
        logger.warning(f"Error verificando campos de lista {list_id}: {e}")
        print(f"⚠️  No se pudieron verificar los campos de la lista: {e}")
        return False


def agregar_suscriptores_via_api(list_id: int, df_suscriptores: pd.DataFrame, api: API) -> int:
    """
    Agrega suscriptores a una lista usando la API con procesamiento en lotes
    Primero define los campos personalizados, luego agrega los suscriptores
    """
    logger = get_logger()
    suscriptores_agregados = 0

    if df_suscriptores.empty:
        logger.warning("DataFrame de suscriptores está vacío")
        return 0

    email_column = None
    possible_email_columns = ['email', 'Email', 'EMAIL', 'Correo Electrónico', 'Correo', 'correo', 'e-mail', 'E-mail']

    for col_name in possible_email_columns:
        if col_name in df_suscriptores.columns:
            email_column = col_name
            break

    if not email_column:
        logger.error(f"Columna de email no encontrada. Columnas disponibles: {list(df_suscriptores.columns)}")
        logger.error(f"Columnas esperadas de email: {possible_email_columns}")
        return 0

    print(f"📧 Usando columna de email: '{email_column}'")

    try:
        print("👥 Agregando suscriptores con campos personalizados...")

        df_trabajo = df_suscriptores.copy()
        if email_column != 'email':
            df_trabajo = df_trabajo.rename(columns={email_column: 'email'})
            print(f"📧 Renombrando '{email_column}' -> 'email' para API")

        subscribers_batch = []
        batch_size = 100

        for _, fila in df_suscriptores.iterrows():
            merge_fields = {}

            for columna, valor in fila.items():
                if pd.notna(valor) and str(valor).strip():
                    campo_normalizado = columna.replace(' ', '_').replace('-', '_')
                    merge_fields[campo_normalizado] = str(valor).strip()

            if 'email' not in merge_fields or not merge_fields['email']:
                logger.warning(f"Fila sin email válido: {fila.to_dict()}")
                continue

            try:
                if len(subscribers_batch) == 0:
                    print("📤 Datos del primer suscriptor:")
                    for k, v in merge_fields.items():
                        print(f"   {k}: '{v}'")

                subscriber_data = SubscriberData(
                    email=merge_fields['email'],
                    **{k: v for k, v in merge_fields.items() if k != 'email'}
                )

                if len(subscribers_batch) == 0:
                    subscriber_dict = subscriber_data.model_dump()
                    print("📦 SubscriberData creado:")
                    for k, v in subscriber_dict.items():
                        if v is not None:
                            print(f"   {k}: '{v}'")

                subscribers_batch.append(subscriber_data)

                if len(subscribers_batch) >= batch_size:
                    result = api.suscriptores.batch_add_subscribers(
                        list_id=list_id,
                        subscribers_data=subscribers_batch,
                        update_subscriber=1,
                        complete_json=1
                    )
                    suscriptores_agregados += result.success_count
                    logger.info(f"Lote procesado: {result.success_count} exitosos, {result.error_count} errores")
                    subscribers_batch.clear()

            except Exception as e:
                logger.warning(f"Error preparando suscriptor {merge_fields.get('email', 'sin email')}: {e}")
                continue

        if subscribers_batch:
            result = api.suscriptores.batch_add_subscribers(
                list_id=list_id,
                subscribers_data=subscribers_batch,
                update_subscriber=1,
                complete_json=1
            )
            suscriptores_agregados += result.success_count
            logger.info(f"Último lote procesado: {result.success_count} exitosos, {result.error_count} errores")

        logger.info(f"Agregados {suscriptores_agregados} suscriptores a lista {list_id}")

        if suscriptores_agregados > 0:
            print("🔍 Verificando campos de la lista...")
            verificar_y_mostrar_campos(list_id, df_suscriptores, api)

    except Exception as e:
        logger.error(f"Error en proceso de agregar suscriptores: {e}")

    return suscriptores_agregados
