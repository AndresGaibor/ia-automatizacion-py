"""Orquestación del mapeo de segmentos."""
import os
import pandas as pd
from typing import Dict, List, Any

from ..utils import load_config, notify
from ..logger import get_logger
from ..excel_helper import ExcelHelper
from ..infrastructure.api import API
from .id_manager import (
    ARCHIVO_SEGMENTOS, CARPETA_LISTAS,
    obtener_o_buscar_id_lista, asegurar_nombre_archivo_con_id,
    actualizar_id_en_segmentos
)
from .file_manager import (
    inicializar_archivo_segmentos, mostrar_estado_listas_segmentos,
    procesar_excel_segmentos
)
from .segment_processor import (
    verificar_columnas_compatibles, aplicar_condiciones_segmento,
    actualizar_columna_segmentos, detectar_cambios_segmentos
)
from .api_operations import (
    obtener_id_lista_por_nombre, verificar_y_crear_campos_segmentacion,
    obtener_usuarios_existentes_con_segmentos, eliminar_usuarios_de_lista,
    subir_usuarios_actualizados, crear_segmentos_con_scraping_batch
)

logger = get_logger()


def procesar_lista_individual(nombre_lista: str, segmentos_data: List[List[Any]], headers: List[str]) -> bool:
    logger.info(f"🔍 Iniciando procesamiento de lista: {nombre_lista}")

    try:
        if not nombre_lista or not nombre_lista.strip():
            logger.error("Nombre de lista vacío o inválido")
            notify("Error", "Nombre de lista vacío o inválido", "error")
            return False

        if not segmentos_data:
            logger.warning(f"No hay datos de segmentos para la lista: {nombre_lista}")
            notify("Advertencia", f"No hay datos de segmentos para la lista: {nombre_lista}", "warning")
            return False

        try:
            config = load_config()
            if not config:
                logger.error("No se pudo cargar la configuración")
                notify("Error", "No se pudo cargar la configuración", "error")
                return False
            api_client = API()
        except Exception as e:
            logger.error(f"Error configurando cliente API: {e}")
            notify("Error API", f"Error configurando cliente API: {e}", "error")
            return False

        list_id = None
        try:
            list_id = obtener_o_buscar_id_lista(nombre_lista)
        except Exception as e:
            logger.warning(f"Error buscando ID local para {nombre_lista}: {e}")

        if list_id:
            print(f"ID {list_id} encontrado para lista '{nombre_lista}'")
            try:
                listas_remotas = api_client.suscriptores.get_lists()
                lista_existe = any(lista.id == list_id for lista in listas_remotas)
                if not lista_existe:
                    logger.warning(f"Lista con ID {list_id} no existe en el servidor, será recreada")
                    print(f"Lista ID {list_id} no existe en servidor, creando nueva")
                    list_id = None
                else:
                    logger.info(f"Lista ID {list_id} confirmada en servidor")
            except Exception as e:
                logger.warning(f"Error verificando lista en servidor: {e}")

        if not list_id:
            try:
                list_id = obtener_id_lista_por_nombre(nombre_lista, api_client)
            except Exception as e:
                logger.warning(f"Error buscando lista por nombre en servidor: {e}")
                notify("Advertencia", f"Error buscando lista por nombre: {e}", "warning")

            if list_id:
                print(f"Lista '{nombre_lista}' encontrada en servidor (ID: {list_id})")
                try:
                    actualizar_id_en_segmentos(nombre_lista, list_id)
                except Exception as e:
                    logger.warning(f"Error actualizando ID en segmentos: {e}")
            else:
                logger.info(f"Lista '{nombre_lista}' no existe en carpeta /listas ni en servidor. Saltando...")
                print(f"⚠️ Lista '{nombre_lista}' no existe en /listas. Saltando segmento.")
                notify("Lista No Encontrada", f"Lista '{nombre_lista}' no existe en /listas. Segmento saltado.", "warning")
                return False

        if not list_id:
            logger.error(f"No se pudo obtener ID válido para lista: {nombre_lista}")
            notify("Error", f"No se pudo obtener ID válido para lista: {nombre_lista}", "error")
            return False

        print(f"Lista encontrada: {nombre_lista} (ID: {list_id})")

        try:
            if not verificar_y_crear_campos_segmentacion(list_id, headers, api_client):
                logger.error(f"No se pudieron crear los campos necesarios para lista {nombre_lista}")
                notify("Error", f"No se pudieron crear campos para lista {nombre_lista}", "error")
                return False
        except Exception as e:
            logger.error(f"Error verificando campos para lista {nombre_lista}: {e}")
            notify("Error", f"Error verificando campos: {e}", "error")
            return False

        try:
            usuarios_existentes = obtener_usuarios_existentes_con_segmentos(list_id, api_client)
        except Exception as e:
            logger.warning(f"Error obteniendo usuarios existentes: {e}")
            usuarios_existentes = {}

        try:
            todos_usuarios_acumba = api_client.suscriptores.get_subscribers(list_id, all_fields=1, complete_json=1)
            emails_en_acumba = {usuario.email for usuario in todos_usuarios_acumba}
            logger.info(f"Encontrados {len(emails_en_acumba)} usuarios en Acumbamail")
        except Exception as e:
            if "No subscribers" in str(e) or "not found" in str(e).lower():
                logger.info(f"Lista {list_id} está vacía (recién creada)")
                emails_en_acumba = set()
            else:
                logger.warning(f"Error obteniendo usuarios de Acumbamail: {e}")
                emails_en_acumba = set()

        try:
            ruta_archivo = asegurar_nombre_archivo_con_id(nombre_lista, list_id)
            if not ruta_archivo:
                logger.error(f"No se pudo determinar ruta de archivo para lista {nombre_lista}")
                notify("Error", f"No se pudo determinar ruta de archivo para lista {nombre_lista}", "error")
                return False
        except Exception as e:
            logger.error(f"Error determinando ruta de archivo: {e}")
            notify("Error", f"Error determinando ruta de archivo: {e}", "error")
            return False

        if not os.path.exists(ruta_archivo):
            logger.warning(f"Archivo local no existe: {ruta_archivo}")
            try:
                columnas_base = ['email'] + headers[1:]
                df_vacio = pd.DataFrame(columns=columnas_base)
                if not ExcelHelper.escribir_excel(df_vacio, ruta_archivo):
                    logger.error(f"No se pudo crear archivo para lista {nombre_lista}")
                    notify("Error", f"No se pudo crear archivo para lista {nombre_lista}", "error")
                    return False
                logger.info(f"Creado archivo nuevo para lista: {nombre_lista}")
                notify("Archivo Creado", f"Creado archivo nuevo para lista: {nombre_lista}", "info")
                return True
            except Exception as e:
                logger.error(f"Error creando archivo para lista {nombre_lista}: {e}")
                notify("Error", f"Error creando archivo: {e}", "error")
                return False

        try:
            df = ExcelHelper.leer_excel(ruta_archivo)
            if df is None:
                logger.error(f"No se pudo leer archivo: {ruta_archivo}")
                notify("Error", f"No se pudo leer archivo: {ruta_archivo}", "error")
                return False
        except Exception as e:
            logger.error(f"Error leyendo archivo {ruta_archivo}: {e}")
            notify("Error", f"Error leyendo archivo: {e}", "error")
            return False

        if df.empty:
            logger.warning(f"Lista {nombre_lista} está vacía")
            notify("Advertencia", f"Lista {nombre_lista} está vacía", "warning")
            return True

        try:
            es_compatible, columnas_disponibles = verificar_columnas_compatibles(df, headers)
        except Exception as e:
            logger.error(f"Error verificando compatibilidad de columnas: {e}")
            notify("Error", f"Error verificando compatibilidad: {e}", "error")
            return False

        if not es_compatible:
            if 'email' in df.columns:
                logger.info(f"Lista {nombre_lista} no tiene columnas para segmentación, procesando solo usuarios")
                notify("Sin Segmentación", f"Lista {nombre_lista} no tiene campos de segmentación, procesando solo usuarios", "warning")

                try:
                    emails_locales = set(df['email'].dropna())
                    usuarios_nuevos = emails_locales - emails_en_acumba
                    if usuarios_nuevos:
                        print(f"Subiendo {len(usuarios_nuevos)} usuarios nuevos a Acumbamail...")
                        df_nuevos = df[df['email'].isin(usuarios_nuevos)]
                        try:
                            usuarios_subidos = subir_usuarios_actualizados(df_nuevos, list_id, api_client)
                            print(f"{usuarios_subidos} usuarios nuevos subidos")
                            notify("Usuarios Subidos", f"{usuarios_subidos} usuarios nuevos subidos a {nombre_lista}", "info")
                        except Exception as e:
                            logger.error(f"Error subiendo usuarios nuevos: {e}")
                            notify("Error Subida", f"Error subiendo usuarios: {e}", "error")
                    else:
                        notify("Sin Usuarios Nuevos", f"No hay usuarios nuevos para subir a {nombre_lista}", "info")
                except Exception as e:
                    logger.error(f"Error procesando usuarios sin segmentación: {e}")
                    notify("Error", f"Error procesando usuarios: {e}", "error")
                    return False

                logger.info(f"Lista {nombre_lista} procesada sin segmentación")
                return True
            else:
                columnas_faltantes = ['email'] + [h for h in headers[1:] if h not in df.columns]
                error_msg = (f"Lista {nombre_lista} no es compatible. Faltan columnas: "
                             f"{', '.join(columnas_faltantes)}. Columnas disponibles: {', '.join(df.columns.tolist())}")
                logger.warning(error_msg)
                notify("Lista Incompatible", error_msg, "error")
                return False

        logger.info(f"Lista {nombre_lista}: {len(df)} filas, columnas disponibles: {columnas_disponibles}")

        try:
            emails_locales = set(df['email'].dropna())
            usuarios_nuevos = emails_locales - emails_en_acumba
            if usuarios_nuevos:
                print(f"Subiendo {len(usuarios_nuevos)} usuarios nuevos a Acumbamail...")
                notify("Subiendo Usuarios", f"Subiendo {len(usuarios_nuevos)} usuarios nuevos", "info")
                df_nuevos = df[df['email'].isin(usuarios_nuevos)]
                try:
                    usuarios_subidos = subir_usuarios_actualizados(df_nuevos, list_id, api_client)
                    print(f"{usuarios_subidos} usuarios nuevos subidos")
                    notify("Usuarios Subidos", f"{usuarios_subidos} usuarios nuevos subidos", "info")
                except Exception as e:
                    logger.error(f"Error subiendo usuarios nuevos: {e}")
                    notify("Error Subida", f"Error subiendo usuarios nuevos: {e}", "error")
        except Exception as e:
            logger.error(f"Error identificando usuarios nuevos: {e}")
            notify("Error", f"Error identificando usuarios nuevos: {e}", "warning")

        try:
            df_original = df.copy()
        except Exception as e:
            logger.error(f"Error copiando DataFrame: {e}")
            notify("Error", f"Error copiando datos: {e}", "error")
            return False

        total_modificaciones = 0
        usuarios_a_eliminar = set()
        segmentos_creados = set()

        notify("Procesando Segmentos", f"Iniciando procesamiento de {len(segmentos_data)} segmentos", "info")

        for i, segmento_condiciones in enumerate(segmentos_data, 1):
            nombre_segmento = segmento_condiciones[0]
            logger.info(f"Aplicando segmento {i}/{len(segmentos_data)}: {nombre_segmento}")

            try:
                mask = aplicar_condiciones_segmento(df, segmento_condiciones, headers)
            except Exception as e:
                logger.error(f"Error aplicando condiciones del segmento {nombre_segmento}: {e}")
                notify("Error Segmento", f"Error en segmento {nombre_segmento}: {e}", "warning")
                continue

            if mask.any():
                try:
                    df, filas_modificadas = actualizar_columna_segmentos(df, mask, nombre_segmento)
                    total_modificaciones += len(filas_modificadas)

                    for idx in filas_modificadas:
                        try:
                            email = df.loc[idx, 'email']
                            usuarios_a_eliminar.add(email)
                        except Exception as e:
                            logger.warning(f"Error procesando usuario en índice {idx}: {e}")

                    print(f"  Segmento '{nombre_segmento}': {len(filas_modificadas)} usuarios asignados")
                    segmentos_creados.add(nombre_segmento)
                except Exception as e:
                    logger.error(f"Error actualizando segmento {nombre_segmento}: {e}")
                    notify("Error Actualización", f"Error actualizando segmento {nombre_segmento}: {e}", "warning")
                    continue
            else:
                print(f"  Segmento '{nombre_segmento}': 0 usuarios cumplen las condiciones")

        try:
            df_cambios = detectar_cambios_segmentos(df_original, df)
        except Exception as e:
            logger.error(f"Error detectando cambios: {e}")
            notify("Error", f"Error detectando cambios: {e}", "warning")
            df_cambios = None

        if usuarios_a_eliminar:
            print(f"Actualizando {len(usuarios_a_eliminar)} usuarios en Acumbamail...")
            notify("Actualizando Usuarios", f"Actualizando {len(usuarios_a_eliminar)} usuarios en Acumbamail", "info")

            try:
                emails_a_eliminar = list(usuarios_a_eliminar)
                if eliminar_usuarios_de_lista(emails_a_eliminar, list_id, api_client):
                    print(f"  Eliminados {len(emails_a_eliminar)} usuarios para actualización")
                    try:
                        df_usuarios_actualizados = df[df['email'].isin(emails_a_eliminar)]
                        usuarios_subidos = subir_usuarios_actualizados(df_usuarios_actualizados, list_id, api_client)
                        print(f"  Re-subidos {usuarios_subidos} usuarios con segmentos actualizados")
                        notify("Usuarios Actualizados", f"Re-subidos {usuarios_subidos} usuarios", "info")
                    except Exception as e:
                        logger.error(f"Error re-subiendo usuarios: {e}")
                        notify("Error Re-subida", f"Error re-subiendo usuarios: {e}", "error")
                else:
                    logger.warning("No se pudieron eliminar usuarios para actualización")
                    notify("Advertencia", "No se pudieron eliminar usuarios para actualización", "warning")
            except Exception as e:
                logger.error(f"Error en proceso de actualización de usuarios: {e}")
                notify("Error Actualización", f"Error actualizando usuarios: {e}", "error")

        if total_modificaciones > 0:
            try:
                if ExcelHelper.escribir_excel(df, ruta_archivo, 'Datos', reemplazar=True):
                    logger.info(f"Guardado archivo principal: {nombre_lista} ({total_modificaciones} modificaciones)")
                    notify("Archivo Guardado", f"Guardado archivo con {total_modificaciones} modificaciones", "info")
                else:
                    logger.error(f"Error guardando archivo principal: {nombre_lista}")
                    notify("Error Guardado", f"Error guardando archivo: {nombre_lista}", "error")
            except Exception as e:
                logger.error(f"Error escribiendo archivo {ruta_archivo}: {e}")
                notify("Error Archivo", f"Error escribiendo archivo: {e}", "error")
                return False

        if df_cambios is not None and not df_cambios.empty:
            try:
                if ExcelHelper.escribir_excel(df_cambios, ruta_archivo, 'Cambios', reemplazar=False):
                    logger.info(f"Guardada hoja de cambios: {nombre_lista} ({len(df_cambios)} cambios)")
                    notify("Cambios Guardados", f"Guardados {len(df_cambios)} cambios detectados", "info")
                else:
                    logger.warning(f"Error guardando hoja de cambios: {nombre_lista}")
                    notify("Error Cambios", f"Error guardando hoja de cambios: {nombre_lista}", "warning")
            except Exception as e:
                logger.error(f"Error escribiendo hoja de cambios: {e}")
                notify("Error", f"Error escribiendo hoja de cambios: {e}", "warning")

        num_cambios = len(df_cambios) if df_cambios is not None else 0
        print(f"Lista '{nombre_lista}' procesada: {total_modificaciones} modificaciones, {num_cambios} cambios detectados")
        notify("Lista Procesada", f"Lista '{nombre_lista}' procesada: {total_modificaciones} modificaciones", "info")

        if segmentos_creados:
            segmentos_unicos = sorted(list(segmentos_creados))
            print(f"Procesando {len(segmentos_unicos)} segmento(s) únicos: {segmentos_unicos}")
            notify("Creando Segmentos", f"Procesando {len(segmentos_unicos)} segmentos únicos", "info")

            try:
                exito_segmentos = crear_segmentos_con_scraping_batch(list_id, segmentos_unicos, api_client)
                if exito_segmentos:
                    print("  Procesamiento de segmentos completado exitosamente")
                    notify("Segmentos Creados", "Procesamiento de segmentos completado exitosamente", "info")
                else:
                    print("  Algunos segmentos pudieron no haberse procesado correctamente")
                    logger.warning(f"Error procesando algunos segmentos para lista '{nombre_lista}'")
                    notify("Advertencia Segmentos", "Algunos segmentos pudieron no procesarse correctamente", "warning")
            except Exception as e:
                logger.error(f"Error creando segmentos: {e}")
                notify("Error Segmentos", f"Error creando segmentos: {e}", "error")
        else:
            print("  No hay segmentos nuevos para crear")
            notify("Sin Segmentos", "No hay segmentos nuevos para crear", "info")

        logger.info(f"Lista {nombre_lista} procesada exitosamente")
        return True

    except Exception as e:
        logger.error(f"Error procesando lista {nombre_lista}: {e}")
        notify("Error Procesamiento", f"Error procesando lista '{nombre_lista}': {e}", "error")
        return False


def mapear_segmentos_completo() -> Dict[str, Any]:
    logger.info("🔍 Iniciando mapeo completo de segmentos")
    notify("Iniciando", "Iniciando mapeo de segmentos", "info")

    try:
        if not inicializar_archivo_segmentos():
            error_msg = "No se pudo inicializar archivo de segmentos"
            notify("Error", error_msg, "error")
            return {"error": error_msg}

        try:
            mostrar_estado_listas_segmentos()
        except Exception as e:
            logger.warning(f"Error mostrando estado de listas: {e}")
            notify("Advertencia", f"No se pudo mostrar el estado de listas: {e}", "warning")

        if not os.path.exists(ARCHIVO_SEGMENTOS):
            error_msg = f"Archivo de segmentos no encontrado: {ARCHIVO_SEGMENTOS}"
            logger.error(error_msg)
            notify("Error", error_msg, "error")
            return {"error": error_msg}

        try:
            headers, grouped_data = procesar_excel_segmentos(ARCHIVO_SEGMENTOS)
        except Exception as e:
            error_msg = f"Error procesando archivo de segmentos: {e}"
            logger.error(error_msg)
            notify("Error", error_msg, "error")
            return {"error": error_msg}

        if not grouped_data:
            error_msg = "No se encontraron datos de segmentos para procesar"
            logger.warning(error_msg)
            notify("Advertencia", error_msg, "warning")
            return {"error": error_msg}

        notify("Listas Encontradas", f"Se encontraron {len(grouped_data)} lista(s) con segmentos", "info")

        print(f"Encontradas {len(grouped_data)} lista(s) con segmentos:")
        for lista_info in grouped_data:
            nombre_lista = lista_info[0]
            segmentos = lista_info[1]
            try:
                list_id = obtener_o_buscar_id_lista(nombre_lista)
                if list_id:
                    print(f"  • {nombre_lista} (ID: {list_id}): {len(segmentos)} segmento(s)")
                else:
                    print(f"  • {nombre_lista} (sin ID): {len(segmentos)} segmento(s)")
            except Exception as e:
                logger.warning(f"Error obteniendo ID para lista {nombre_lista}: {e}")
                print(f"  • {nombre_lista} (ID desconocido): {len(segmentos)} segmento(s)")

        estadisticas = {
            "listas_procesadas": [],
            "listas_fallidas": [],
            "total_listas": len(grouped_data),
            "headers": headers,
            "errores_detallados": []
        }

        for i, lista_info in enumerate(grouped_data, 1):
            nombre_lista = lista_info[0]
            segmentos_data = lista_info[1]

            print(f"\nProcesando lista {i}/{len(grouped_data)}: {nombre_lista}")
            notify("Progreso", f"Procesando lista {i}/{len(grouped_data)}: {nombre_lista}", "info")

            try:
                if procesar_lista_individual(nombre_lista, segmentos_data, headers):
                    estadisticas["listas_procesadas"].append(nombre_lista)
                    logger.info(f"Lista procesada exitosamente: {nombre_lista}")
                else:
                    estadisticas["listas_fallidas"].append(nombre_lista)
                    estadisticas["errores_detallados"].append(f"{nombre_lista}: Error en procesamiento")
                    logger.warning(f"Lista falló en procesamiento: {nombre_lista}")
            except Exception as e:
                estadisticas["listas_fallidas"].append(nombre_lista)
                error_detalle = f"{nombre_lista}: {str(e)}"
                estadisticas["errores_detallados"].append(error_detalle)
                logger.error(f"Error procesando lista {nombre_lista}: {e}")
                notify("Error Lista", f"Error procesando {nombre_lista}: {e}", "warning")

        print("\nResumen del mapeo:")
        print(f"   Listas procesadas: {len(estadisticas['listas_procesadas'])}")
        for lista in estadisticas["listas_procesadas"]:
            print(f"      • {lista}")
        print(f"   Listas fallidas: {len(estadisticas['listas_fallidas'])}")
        for lista in estadisticas["listas_fallidas"]:
            print(f"      • {lista}")

        if estadisticas["listas_procesadas"]:
            notify("Mapeo Completado",
                f"Mapeo finalizado: {len(estadisticas['listas_procesadas'])} listas exitosas, {len(estadisticas['listas_fallidas'])} fallidas",
                "info")
        else:
            notify("Mapeo Sin Éxito", "No se procesaron listas correctamente", "warning")

        logger.info(f"Mapeo completado: {len(estadisticas['listas_procesadas'])} exitosas, {len(estadisticas['listas_fallidas'])} fallidas")
        return estadisticas

    except Exception as e:
        error_msg = f"Error crítico en mapeo de segmentos: {e}"
        logger.error(error_msg)
        notify("Error Crítico", error_msg, "error")
        return {"error": error_msg}


def main():
    """Función principal para ejecutar el mapeo desde línea de comandos"""
    try:
        resultado = mapear_segmentos_completo()

        if "error" in resultado:
            print(f"❌ {resultado['error']}")
            return False

        if resultado["listas_procesadas"]:
            print("🎉 Mapeo de segmentos completado exitosamente")
            return True
        else:
            print("⚠️ No se procesaron listas correctamente")
            return False

    except Exception as e:
        logger.error(f"Error en mapeo de segmentos: {e}")
        print(f"❌ Error durante el mapeo: {e}")
        return False


if __name__ == "__main__":
    main()
