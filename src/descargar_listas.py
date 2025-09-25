"""
Módulo para descargar listas de suscriptores marcadas en Busqueda_Listas.xlsx

Este módulo lee el archivo Busqueda_Listas.xlsx, identifica las listas marcadas con 'x'
en la columna 'Buscar', descarga los suscriptores usando la API de AcumbaMail,
y guarda cada lista como un archivo Excel separado en /data/listas/

Uso:
    # Como módulo:
    from src.descargar_listas import procesar_listas_marcadas
    resultados = procesar_listas_marcadas()
    
    # Ejecutar directamente:
    python src/descargar_listas.py
"""

import pandas as pd
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import re

# Agregar el directorio raíz al path cuando se ejecuta directamente
if __name__ == "__main__":
    current_dir = Path(__file__).parent
    root_dir = current_dir.parent
    sys.path.insert(0, str(root_dir))

# Imports que funcionan tanto ejecutando directamente como módulo
try:
    # Cuando se ejecuta como módulo del paquete
    from .logger import get_logger
    from .utils import load_config, data_path, notify
    from .api.client import APIClient
    from .api.endpoints.suscriptores import SuscriptoresAPI
    from .excel_utils import crear_o_cargar_libro_excel, obtener_o_crear_hoja, agregar_datos
except ImportError:
    # Cuando se ejecuta directamente
    from src.logger import get_logger
    from src.utils import load_config
    from src.api.client import APIClient
    from src.api.endpoints.suscriptores import SuscriptoresAPI
    from src.excel_utils import crear_o_cargar_libro_excel, obtener_o_crear_hoja, agregar_datos

logger = get_logger()


class DescargadorListas:
    """Clase para manejar la descarga de listas de suscriptores"""
    
    def __init__(self, archivo_busqueda: str = "data/Busqueda_Listas.xlsx"):
        """
        Inicializa el descargador de listas.
        
        Args:
            archivo_busqueda: Ruta al archivo Excel con las listas a procesar
        """
        self.archivo_busqueda = Path(archivo_busqueda)
        self.directorio_salida = Path("data/listas")
        self.config = load_config()
        
        # Validar configuración de API
        api_config = self.config.get("api", {})
        if not api_config.get("api_key"):
            notify("Error de API", "Error: API Key no configurada. Configure api.api_key en config.yaml", "error")
            raise ValueError("API Key no configurada")
        
        if not api_config.get("base_url"):
            notify("Error de API", "Error: URL base de API no configurada en config.yaml", "error")
            raise ValueError("URL base de API no configurada")
        
        # Configurar cliente API
        try:
            self.api_client = APIClient(
                base_url=self.config["api"]["base_url"],
                auth_token=self.config["api"]["api_key"]
            )
            self.suscriptores_api = SuscriptoresAPI(self.api_client)
        except Exception as e:
            notify("Error de API", f"Error configurando cliente API: {e}", "error")
            raise
        
        # Crear directorio de salida si no existe
        self.directorio_salida.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Descargador inicializado. Archivo: {self.archivo_busqueda}")
        logger.info(f"Directorio de salida: {self.directorio_salida}")
        notify("API", "Cliente API configurado correctamente", "info")

    def leer_listas_marcadas(self) -> List[Dict[str, Any]]:
        """
        Lee el archivo Excel y retorna las listas marcadas con 'x'.
        
        Returns:
            Lista de diccionarios con información de listas marcadas
            
        Raises:
            FileNotFoundError: Si el archivo no existe
            ValueError: Si el archivo no tiene la estructura esperada
        """
        if not self.archivo_busqueda.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {self.archivo_busqueda}")
        
        logger.info(f"Leyendo archivo: {self.archivo_busqueda}")
        
        try:
            df = pd.read_excel(self.archivo_busqueda)
        except Exception as e:
            raise ValueError(f"Error al leer Excel: {e}")
        
        # Verificar columnas requeridas
        columnas_requeridas = ['Buscar', 'ID_LISTA', 'NOMBRE LISTA', 'SUSCRIPTORES', 'CREACION']
        columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
        if columnas_faltantes:
            raise ValueError(f"Columnas faltantes en Excel: {columnas_faltantes}")
        
        # Filtrar listas marcadas con 'x' (ignorar mayúsculas/minúsculas)
        listas_marcadas = df[df['Buscar'].astype(str).str.lower() == 'x']
        
        logger.info(f"Total de listas en archivo: {len(df)}")
        logger.info(f"Listas marcadas para descarga: {len(listas_marcadas)}")
        
        if listas_marcadas.empty:
            logger.warning("No se encontraron listas marcadas con 'x' en la columna 'Buscar'")
            return []
        
        # Convertir a lista de diccionarios
        listas = []
        for _, row in listas_marcadas.iterrows():
            lista_info = {
                'id_lista': int(row['ID_LISTA']),
                'nombre': str(row['NOMBRE LISTA']),
                'suscriptores_total': int(row['SUSCRIPTORES']),
                'fecha_creacion': str(row['CREACION'])
            }
            listas.append(lista_info)
            logger.info(f"Lista marcada: ID {lista_info['id_lista']} - {lista_info['nombre']} ({lista_info['suscriptores_total']} suscriptores)")
        
        return listas

    def limpiar_nombre_archivo(self, nombre: str) -> str:
        """
        Limpia un nombre para usarlo como nombre de archivo.
        
        Args:
            nombre: Nombre original
            
        Returns:
            Nombre limpio y seguro para archivo
        """
        # Caracteres no permitidos en nombres de archivo
        caracteres_invalidos = r'[<>:"/\\|?*]'
        nombre_limpio = re.sub(caracteres_invalidos, '_', nombre)
        
        # Remover espacios extras y puntos al final
        nombre_limpio = nombre_limpio.strip(' .')
        
        # Limitar longitud
        if len(nombre_limpio) > 100:
            nombre_limpio = nombre_limpio[:100]
        
        return nombre_limpio

    def obtener_campos_lista(self, id_lista: int) -> List[str]:
        """
        Obtiene los campos disponibles en una lista.
        
        Args:
            id_lista: ID de la lista
            
        Returns:
            Lista de nombres de campos
        """
        try:
            logger.info(f"Obteniendo campos de lista {id_lista}")
            campos_respuesta = self.suscriptores_api.get_fields(id_lista)
            
            # Extraer nombres de campos
            campos = []
            if hasattr(campos_respuesta, 'fields') and campos_respuesta.fields:
                # Si fields es un dict, usar las claves como nombres de campos
                if isinstance(campos_respuesta.fields, dict):
                    campos = list(campos_respuesta.fields.keys())
                else:
                    campos = ['email']  # Fallback básico
            else:
                campos = ['email']  # Fallback básico
            
            # Asegurar que email esté incluido
            if 'email' not in campos:
                campos.insert(0, 'email')
            
            logger.info(f"Campos encontrados en lista {id_lista}: {campos}")
            return campos
            
        except Exception as e:
            logger.error(f"Error obteniendo campos de lista {id_lista}: {e}")
            # Fallback con campos básicos comunes
            return ['email', 'nombre', 'apellidos', 'Segmentos']

    def descargar_suscriptores_lista(self, id_lista: int) -> List[Dict[str, Any]]:
        """
        Descarga todos los suscriptores de una lista con todos sus campos.
        
        Args:
            id_lista: ID de la lista
            
        Returns:
            Lista de diccionarios con datos completos de suscriptores
        """
        logger.info(f"Descargando suscriptores de lista {id_lista}")
        
        todos_suscriptores = []
        block_index = 0
        
        try:
            while True:
                logger.debug(f"Descargando bloque {block_index} de lista {id_lista}")
                
                # Usar getSubscribers con all_fields=1 y complete_json=1 para obtener todos los datos
                suscriptores = self.suscriptores_api.get_subscribers(
                    list_id=id_lista,
                    status=None,  # Todos los estados
                    block_index=block_index,
                    all_fields=1,  # IMPORTANTE: Obtener todos los campos
                    complete_json=1  # IMPORTANTE: Respuesta completa
                )
                
                if not suscriptores:
                    logger.info(f"No más suscriptores en bloque {block_index}")
                    break
                
                # Convertir a diccionarios si es necesario
                suscriptores_dict = []
                for suscriptor in suscriptores:
                    if hasattr(suscriptor, 'model_dump'):
                        # Son objetos Pydantic
                        suscriptor_dict = suscriptor.model_dump()
                    elif hasattr(suscriptor, '__dict__'):
                        # Objeto con atributos
                        suscriptor_dict = suscriptor.__dict__
                    elif isinstance(suscriptor, dict):
                        # Ya es diccionario
                        suscriptor_dict = suscriptor
                    else:
                        # Fallback: convertir a string y luego parsear si es posible
                        logger.warning(f"Formato de suscriptor no reconocido: {type(suscriptor)}")
                        suscriptor_dict = {'email': str(suscriptor)}
                    
                    suscriptores_dict.append(suscriptor_dict)
                
                todos_suscriptores.extend(suscriptores_dict)
                logger.info(f"Descargados {len(suscriptores)} suscriptores en bloque {block_index} (total: {len(todos_suscriptores)})")
                
                # Si recibimos menos de lo esperado, probablemente es el último bloque
                if len(suscriptores) < 100:  # Asumiendo tamaño de página típico
                    break
                
                block_index += 1
                
        except Exception as e:
            logger.error(f"Error descargando suscriptores de lista {id_lista}: {e}")
            if todos_suscriptores:
                logger.warning(f"Se descargaron parcialmente {len(todos_suscriptores)} suscriptores")
            else:
                raise
        
        logger.info(f"Descarga completada: {len(todos_suscriptores)} suscriptores de lista {id_lista}")
        return todos_suscriptores

    def guardar_lista_excel(self, lista_info: Dict[str, Any], suscriptores: List[Dict[str, Any]], campos: List[str]) -> str:
        """
        Guarda los suscriptores de una lista en un archivo Excel.
        
        Args:
            lista_info: Información de la lista
            suscriptores: Lista de suscriptores
            campos: Campos a incluir en el Excel
            
        Returns:
            Ruta del archivo creado
        """
        # Crear nombre de archivo - Solo el nombre de la lista limpio
        nombre_limpio = self.limpiar_nombre_archivo(lista_info['nombre'])
        nombre_archivo = f"{nombre_limpio}.xlsx"
        ruta_archivo = self.directorio_salida / nombre_archivo
        
        logger.info(f"Guardando lista {lista_info['id_lista']} en: {ruta_archivo}")
        
        # Crear libro Excel
        libro = crear_o_cargar_libro_excel(str(ruta_archivo))
        
        # Eliminar la hoja por defecto si existe
        if "Sheet" in libro.sheetnames:
            del libro["Sheet"]
        
        # Crear hoja con el nombre de la lista que contenga los suscriptores
        hoja_principal = obtener_o_crear_hoja(libro, lista_info['nombre'], campos)
        
        # Preparar datos de suscriptores
        datos_suscriptores = []
        for suscriptor in suscriptores:
            fila = []
            for campo in campos:
                valor = suscriptor.get(campo, "")
                # Manejar valores especiales
                if isinstance(valor, (list, dict)):
                    valor = str(valor)
                elif valor is None:
                    valor = ""
                fila.append(valor)
            datos_suscriptores.append(fila)
        
        # Agregar datos
        registros_agregados = agregar_datos(hoja_principal, datos_suscriptores)
        
        # Guardar archivo
        libro.save(str(ruta_archivo))
        
        logger.info(f"Archivo guardado exitosamente: {ruta_archivo}")
        logger.info(f"Registros guardados: {registros_agregados}")
        
        return str(ruta_archivo)

    def procesar_lista_individual(self, lista_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa una lista individual: descarga suscriptores y guarda Excel.
        
        Args:
            lista_info: Información de la lista
            
        Returns:
            Resultado del procesamiento
        """
        resultado = {
            'id_lista': lista_info['id_lista'],
            'nombre': lista_info['nombre'],
            'exitoso': False,
            'archivo_creado': None,
            'suscriptores_descargados': 0,
            'campos_encontrados': [],
            'error': None
        }
        
        try:
            logger.info(f"Procesando lista {lista_info['id_lista']}: {lista_info['nombre']}")
            
            # Descargar suscriptores primero
            suscriptores = self.descargar_suscriptores_lista(lista_info['id_lista'])
            
            if not suscriptores:
                logger.warning(f"No se encontraron suscriptores en lista {lista_info['id_lista']}")
                resultado['error'] = "No se encontraron suscriptores"
                return resultado
            
            # Obtener campos dinámicamente de los datos reales de suscriptores
            campos_reales = self.extraer_campos_de_suscriptores(suscriptores)
            resultado['campos_encontrados'] = campos_reales
            
            logger.info(f"Campos encontrados en datos reales: {campos_reales}")
            
            # Guardar en Excel
            archivo_creado = self.guardar_lista_excel(lista_info, suscriptores, campos_reales)
            
            # Actualizar resultado
            resultado['exitoso'] = True
            resultado['archivo_creado'] = archivo_creado
            resultado['suscriptores_descargados'] = len(suscriptores)
            
            logger.info(f"Lista {lista_info['id_lista']} procesada exitosamente")
            
        except Exception as e:
            logger.error(f"Error procesando lista {lista_info['id_lista']}: {e}")
            resultado['error'] = str(e)
        
        return resultado

    def extraer_campos_de_suscriptores(self, suscriptores: List[Dict[str, Any]]) -> List[str]:
        """
        Extrae todos los campos únicos presentes en los suscriptores.
        
        Args:
            suscriptores: Lista de suscriptores
            
        Returns:
            Lista ordenada de nombres de campos
        """
        if not suscriptores:
            return ['email']
        
        # Recopilar todos los campos únicos de todos los suscriptores
        campos_unicos = set()
        for suscriptor in suscriptores:
            if isinstance(suscriptor, dict):
                campos_unicos.update(suscriptor.keys())
        
        # Convertir a lista y ordenar, con email primero
        campos_lista = list(campos_unicos)
        
        # Asegurar que email esté primero
        if 'email' in campos_lista:
            campos_lista.remove('email')
            campos_lista.insert(0, 'email')
        
        # Ordenar el resto alfabéticamente (excepto email que ya está primero)
        campos_lista[1:] = sorted(campos_lista[1:])
        
        logger.info(f"Campos extraídos de suscriptores: {campos_lista}")
        return campos_lista

    def procesar_todas_las_listas(self) -> Dict[str, Any]:
        """
        Procesa todas las listas marcadas en el archivo Excel.
        
        Returns:
            Resumen de resultados del procesamiento
        """
        logger.info("Iniciando procesamiento de listas marcadas")
        
        resultados = {
            'total_listas': 0,
            'exitosas': 0,
            'fallidas': 0,
            'archivos_creados': [],
            'errores': [],
            'detalle': []
        }
        
        try:
            # Leer listas marcadas
            listas_marcadas = self.leer_listas_marcadas()
            resultados['total_listas'] = len(listas_marcadas)
            
            if not listas_marcadas:
                logger.info("No hay listas marcadas para procesar")
                return resultados
            
            # Procesar cada lista
            for lista_info in listas_marcadas:
                resultado = self.procesar_lista_individual(lista_info)
                resultados['detalle'].append(resultado)
                
                if resultado['exitoso']:
                    resultados['exitosas'] += 1
                    resultados['archivos_creados'].append(resultado['archivo_creado'])
                    logger.info(f"✅ Lista {resultado['id_lista']} procesada: {resultado['archivo_creado']}")
                else:
                    resultados['fallidas'] += 1
                    resultados['errores'].append(f"Lista {resultado['id_lista']}: {resultado['error']}")
                    logger.error(f"❌ Lista {resultado['id_lista']} falló: {resultado['error']}")
            
            # Resumen final
            logger.info(f"Procesamiento completado: {resultados['exitosas']}/{resultados['total_listas']} exitosas")
            
        except Exception as e:
            logger.error(f"Error en procesamiento general: {e}")
            resultados['errores'].append(f"Error general: {e}")
        
        return resultados


def procesar_listas_marcadas(archivo_busqueda: Optional[str] = None) -> Dict[str, Any]:
    """
    Función principal para procesar listas marcadas.
    
    Args:
        archivo_busqueda: Ruta al archivo Excel (opcional, usa default si no se especifica)
        
    Returns:
        Resumen de resultados del procesamiento
    """
    if archivo_busqueda is None:
        archivo_busqueda = "data/Busqueda_Listas.xlsx"
    
    descargador = DescargadorListas(archivo_busqueda)
    return descargador.procesar_todas_las_listas()


def listar_archivos_descargados() -> List[str]:
    """
    Lista todos los archivos descargados en el directorio de listas.
    
    Returns:
        Lista de rutas de archivos descargados
    """
    directorio_listas = Path("data/listas")
    if not directorio_listas.exists():
        return []
    
    archivos = []
    for archivo in directorio_listas.glob("*.xlsx"):
        archivos.append(str(archivo))
    
    return sorted(archivos)


if __name__ == "__main__":
    print("📋 === DESCARGADOR DE LISTAS DE ACUMBAMAIL ===")
    print("Busca listas marcadas con 'x' en data/Busqueda_Listas.xlsx")
    print("Descarga suscriptores y guarda archivos Excel en data/listas/")
    print()
    
    try:
        # Verificar que existe el archivo de búsqueda
        archivo_busqueda = "data/Busqueda_Listas.xlsx"
        if not os.path.exists(archivo_busqueda):
            print(f"❌ Error: No se encontró el archivo {archivo_busqueda}")
            print("   Asegúrate de que el archivo existe y tiene listas marcadas con 'x'")
            sys.exit(1)
        
        print(f"🔍 Leyendo archivo: {archivo_busqueda}")
        
        # Procesar listas marcadas
        print("🚀 Iniciando descarga de listas marcadas...")
        resultados = procesar_listas_marcadas()
        
        print("\n📊 === RESUMEN DE RESULTADOS ===")
        print(f"Total listas procesadas: {resultados['total_listas']}")
        print(f"Exitosas: {resultados['exitosas']}")
        print(f"Fallidas: {resultados['fallidas']}")
        
        if resultados['archivos_creados']:
            print(f"\n✅ ARCHIVOS CREADOS ({len(resultados['archivos_creados'])}):")
            for archivo in resultados['archivos_creados']:
                print(f"   📄 {archivo}")
        
        if resultados['errores']:
            print(f"\n❌ ERRORES ENCONTRADOS ({len(resultados['errores'])}):")
            for error in resultados['errores']:
                print(f"   ⚠️ {error}")
        
        # Mostrar archivos disponibles
        archivos_existentes = listar_archivos_descargados()
        if archivos_existentes:
            print(f"\n📂 ARCHIVOS DISPONIBLES EN data/listas/ ({len(archivos_existentes)} total):")
            for archivo in archivos_existentes[-10:]:  # Mostrar últimos 10
                archivo_relativo = os.path.relpath(archivo)
                print(f"   📄 {archivo_relativo}")
        
        if resultados['total_listas'] == 0:
            print("\n💡 INSTRUCCIONES:")
            print("   1. Abre data/Busqueda_Listas.xlsx")
            print("   2. Marca con 'x' las listas que quieres descargar en la columna 'Buscar'")
            print("   3. Ejecuta este script nuevamente")
        else:
            print("\n🎉 Proceso completado exitosamente!")
        
    except Exception as e:
        print(f"\n❌ Error durante la ejecución: {e}")
        logger.error(f"Error en main: {e}", exc_info=True)
        sys.exit(1)