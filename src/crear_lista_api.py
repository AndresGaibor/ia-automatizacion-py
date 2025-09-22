"""
Módulo para crear listas de suscriptores usando la API de Acumbamail.
Reemplaza la implementación anterior que usaba Playwright.
"""
from .utils import data_path, notify, load_config
from .api import API
from .api.models.suscriptores import SubscriberData
from .logger import get_logger
from .excel_helper import ExcelHelper
import pandas as pd
import os
import tkinter as tk
from tkinter import messagebox, ttk
import threading
from typing import List, Optional, Union, Dict, Any

# archivo_busqueda será asignado dinámicamente

def seleccionar_archivo_tk(directorio: str, master=None) -> Optional[str]:
    """
    Selector de archivos Excel con interfaz Tkinter
    """
    import glob

    archivos_excel = glob.glob(os.path.join(directorio, "*.xlsx"))
    # Excluir Plantilla.xlsx del listado
    archivos_excel = [f for f in archivos_excel if not f.endswith('Plantilla.xlsx')]

    if not archivos_excel:
        if master:
            messagebox.showerror("Error", "No se encontraron archivos Excel en el directorio.")
        return None

    if len(archivos_excel) == 1:
        return archivos_excel[0]

    # Crear ventana de selección
    if not master:
        root = tk.Tk()
        root.withdraw()
        master = root

    dialog = tk.Toplevel(master)
    dialog.title("Seleccionar Archivo")
    dialog.geometry("500x300")
    dialog.transient(master)
    dialog.grab_set()

    # Centrar ventana
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
    y = (dialog.winfo_screenheight() // 2) - (300 // 2)
    dialog.geometry(f"500x300+{x}+{y}")

    result = None

    # Frame principal
    main_frame = ttk.Frame(dialog, padding="10")
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Título
    title_label = ttk.Label(main_frame, text="Selecciona el archivo Excel:")
    title_label.pack(anchor=tk.W, pady=(0, 10))

    # Frame para listbox y scrollbar
    list_frame = ttk.Frame(main_frame)
    list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

    # Listbox con scrollbar
    scrollbar = ttk.Scrollbar(list_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE, yscrollcommand=scrollbar.set)
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=listbox.yview)

    # Agregar archivos a la lista (solo nombres, no rutas completas)
    nombres_archivos = [os.path.basename(archivo) for archivo in archivos_excel]
    for nombre in nombres_archivos:
        listbox.insert(tk.END, nombre)

    # Seleccionar primer archivo por defecto
    listbox.selection_set(0)

    # Frame para botones
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill=tk.X)

    # Botones
    def on_ok():
        nonlocal result
        selected_index = listbox.curselection()
        if selected_index:
            result = archivos_excel[selected_index[0]]
        dialog.destroy()

    def on_cancel():
        dialog.destroy()

    ttk.Button(button_frame, text="Cancelar", command=on_cancel).pack(side=tk.RIGHT)
    ttk.Button(button_frame, text="Aceptar", command=on_ok).pack(side=tk.RIGHT, padx=(0, 5))

    # Bind Enter y Escape
    dialog.bind('<Return>', lambda e: on_ok())
    dialog.bind('<Escape>', lambda e: on_cancel())

    # Esperar a que se cierre el diálogo
    dialog.wait_window()

    return result

def seleccionar_hoja_tk(archivo: str, master=None, multiple: bool = True) -> Optional[List[str]]:
    """
    Selector de hojas con interfaz Tkinter para selección múltiple
    """
    if not os.path.exists(archivo):
        if master:
            messagebox.showerror("Error", f"Archivo no encontrado: {archivo}")
        return None
    
    hojas = ExcelHelper.obtener_hojas(archivo)
    if not hojas:
        if master:
            messagebox.showerror("Error", "El archivo no contiene hojas.")
        return None
    
    if len(hojas) == 1:
        return hojas
    
    # Crear ventana de selección
    if not master:
        root = tk.Tk()
        root.withdraw()
        master = root
    
    dialog = tk.Toplevel(master)
    dialog.title("Seleccionar Hojas")
    dialog.geometry("400x300")
    dialog.transient(master)
    dialog.grab_set()
    
    # Centrar ventana
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
    y = (dialog.winfo_screenheight() // 2) - (300 // 2)
    dialog.geometry(f"400x300+{x}+{y}")
    
    result = []
    
    # Frame principal
    main_frame = ttk.Frame(dialog, padding="10")
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Título
    title_label = ttk.Label(main_frame, text="Selecciona las hojas del archivo Excel:")
    title_label.pack(anchor=tk.W, pady=(0, 10))
    
    # Frame para listbox y scrollbar
    list_frame = ttk.Frame(main_frame)
    list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
    
    # Listbox con scrollbar
    scrollbar = ttk.Scrollbar(list_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE if multiple else tk.SINGLE, 
                        yscrollcommand=scrollbar.set)
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=listbox.yview)
    
    # Agregar hojas a la lista
    for hoja in hojas:
        listbox.insert(tk.END, hoja)
    
    # Seleccionar primera hoja por defecto
    listbox.selection_set(0)
    
    # Frame para botones
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill=tk.X)
    
    # Botones
    def on_ok():
        selected_indices = listbox.curselection()
        if selected_indices:
            result.extend([hojas[i] for i in selected_indices])
        dialog.destroy()
    
    def on_cancel():
        dialog.destroy()
    
    def on_select_all():
        listbox.selection_set(0, tk.END)
    
    def on_select_none():
        listbox.selection_clear(0, tk.END)
    
    if multiple:
        ttk.Button(button_frame, text="Seleccionar Todo", command=on_select_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Limpiar", command=on_select_none).pack(side=tk.LEFT, padx=(0, 5))
    
    ttk.Button(button_frame, text="Cancelar", command=on_cancel).pack(side=tk.RIGHT)
    ttk.Button(button_frame, text="Aceptar", command=on_ok).pack(side=tk.RIGHT, padx=(0, 5))
    
    # Bind Enter y Escape
    dialog.bind('<Return>', lambda e: on_ok())
    dialog.bind('<Escape>', lambda e: on_cancel())
    
    # Esperar a que se cierre el diálogo
    dialog.wait_window()
    
    return result if result else None

def crear_lista_via_api(nombre_lista: str, config_lista: Dict[str, str], api: API) -> Optional[int]:
    """
    Crea una lista usando la API de suscriptores
    
    Args:
        nombre_lista: Nombre de la lista a crear
        config_lista: Configuración de la lista (sender_email, company, etc.)
        api: Instancia de API reutilizable
        
    Returns:
        ID de la lista creada o None si hay error
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

def agregar_suscriptores_via_api(list_id: int, df_suscriptores: pd.DataFrame, api: API) -> int:
    """
    Agrega suscriptores a una lista usando la API con procesamiento en lotes
    
    Args:
        list_id: ID de la lista
        df_suscriptores: DataFrame con los datos de suscriptores
        api: Instancia de API reutilizable
        
    Returns:
        Número de suscriptores agregados exitosamente
    """
    logger = get_logger()
    suscriptores_agregados = 0
    
    if df_suscriptores.empty:
        logger.warning("DataFrame de suscriptores está vacío")
        return 0
    
    # Verificar que tenga columna email
    tiene_email, faltantes = ExcelHelper.verificar_columnas(df_suscriptores, ['email'])
    if not tiene_email:
        logger.error(f"Columna 'email' requerida no encontrada. Columnas disponibles: {list(df_suscriptores.columns)}")
        return 0
    
    try:
        # Preparar datos para procesamiento en lotes
        subscribers_batch = []
        batch_size = 100  # Procesar en lotes de 100
        
        for _, fila in df_suscriptores.iterrows():
            # Preparar campos del suscriptor
            merge_fields = {}
            
            for columna, valor in fila.items():
                if pd.notna(valor) and str(valor).strip():  # Solo valores no vacíos
                    merge_fields[columna] = str(valor).strip()
            
            # Verificar que tenga email
            if 'email' not in merge_fields or not merge_fields['email']:
                logger.warning(f"Fila sin email válido: {fila.to_dict()}")
                continue
            
            # Crear SubscriberData tipado
            try:
                subscriber_data = SubscriberData(
                    email=merge_fields['email'],
                    **{k: v for k, v in merge_fields.items() if k != 'email'}
                )
                subscribers_batch.append(subscriber_data)
                
                # Procesar lote cuando alcance el tamaño
                if len(subscribers_batch) >= batch_size:
                    result = api.suscriptores.batch_add_subscribers(
                        list_id=list_id,
                        subscribers_data=subscribers_batch,
                        update_subscriber=1,  # Actualizar si existe
                        complete_json=1
                    )
                    suscriptores_agregados += result.success_count
                    logger.info(f"Lote procesado: {result.success_count} exitosos, {result.error_count} errores")
                    subscribers_batch.clear()
                    
            except Exception as e:
                logger.warning(f"Error preparando suscriptor {merge_fields.get('email', 'sin email')}: {e}")
                continue
        
        # Procesar último lote si queda alguno
        if subscribers_batch:
            result = api.suscriptores.batch_add_subscribers(
                list_id=list_id,
                subscribers_data=subscribers_batch,
                update_subscriber=1,  # Actualizar si existe
                complete_json=1
            )
            suscriptores_agregados += result.success_count
            logger.info(f"Último lote procesado: {result.success_count} exitosos, {result.error_count} errores")
        
        logger.info(f"Agregados {suscriptores_agregados} suscriptores a lista {list_id}")
        
    except Exception as e:
        logger.error(f"Error en proceso de agregar suscriptores: {e}")
    
    return suscriptores_agregados

def procesar_hoja_excel(archivo: str, nombre_hoja: str, config_lista: Dict[str, str], api: API) -> Optional[Dict[str, Any]]:
    """
    Procesa una hoja de Excel: crea lista y agrega suscriptores
    
    Args:
        archivo: Ruta del archivo Excel
        nombre_hoja: Nombre de la hoja a procesar
        config_lista: Configuración de la lista
        api: Instancia de API reutilizable
        
    Returns:
        Dict con resultado del procesamiento o None si error
    """
    logger = get_logger()
    
    try:
        # Leer hoja de Excel
        df = ExcelHelper.leer_excel(archivo, nombre_hoja)
        
        if df.empty:
            logger.warning(f"Hoja '{nombre_hoja}' está vacía")
            return None
        
        print(f"📄 Procesando hoja '{nombre_hoja}' con {len(df)} filas")
        
        # Crear lista
        list_id = crear_lista_via_api(nombre_hoja, config_lista, api)
        if not list_id:
            return None
        
        # Agregar suscriptores
        suscriptores_agregados = agregar_suscriptores_via_api(list_id, df, api)
        
        resultado = {
            'nombre_lista': nombre_hoja,
            'list_id': list_id,
            'total_filas': len(df),
            'suscriptores_agregados': suscriptores_agregados,
            'exitoso': suscriptores_agregados > 0
        }
        
        print(f"✅ Lista '{nombre_hoja}' creada - ID: {list_id}, Suscriptores: {suscriptores_agregados}/{len(df)}")
        return resultado
        
    except Exception as e:
        logger.error(f"Error procesando hoja {nombre_hoja}: {e}")
        print(f"❌ Error procesando hoja {nombre_hoja}: {e}")
        return None

def cargar_configuracion_lista() -> Dict[str, str]:
    """
    Carga la configuración de la lista desde config.yaml o valores por defecto
    
    Returns:
        Dict con configuración de la lista
    """
    config = load_config()
    lista_config = config.get('lista', {}) if config else {}
    
    return {
        'sender_email': lista_config.get('sender_email', 'admin@example.com'),
        'company': lista_config.get('company', 'Mi Empresa'),
        'country': lista_config.get('country', 'España'),
        'city': lista_config.get('city', 'Madrid'),
        'address': lista_config.get('address', 'Calle Principal 123'),
        'phone': lista_config.get('phone', '+34 900 000 000')
    }

def main(archivo: Optional[str] = None, nombre_hoja: Optional[Union[str, List[str]]] = None, multiple: bool = True):
    """
    Función principal para crear listas de suscriptores usando API
    
    Args:
        nombre_hoja: Nombre de hoja(s) específica(s) o None para seleccionar
        multiple: Permitir selección múltiple
    """
    logger = get_logger()

    # Usar archivo proporcionado o fallback a Lista_envio.xlsx
    archivo_busqueda = archivo if archivo else data_path("Lista_envio.xlsx")

    # Verificar archivo de entrada
    if not os.path.exists(archivo_busqueda):
        print(f"❌ Archivo no encontrado: {archivo_busqueda}")
        return
    
    # Cargar configuración desde config.yaml
    config_lista = cargar_configuracion_lista()
    
    # Crear instancia única de API
    try:
        api = API()
    except Exception as e:
        logger.error(f"Error inicializando API: {e}")
        print(f"❌ Error inicializando API: {e}")
        return
    
    try:
        # Seleccionar hojas
        if nombre_hoja is None:
            # Selección interactiva (debe ser llamado desde hilo principal)
            if threading.current_thread() is threading.main_thread():
                hojas_seleccionadas = seleccionar_hoja_tk(archivo_busqueda, multiple=multiple)
            else:
                # Fallback: usar todas las hojas
                hojas_seleccionadas = ExcelHelper.obtener_hojas(archivo_busqueda)
                print(f"⚠️  Modo automático: procesando todas las hojas ({len(hojas_seleccionadas)})")
        elif isinstance(nombre_hoja, str):
            hojas_seleccionadas = [nombre_hoja]
        else:
            hojas_seleccionadas = nombre_hoja
        
        if not hojas_seleccionadas:
            print("❌ No se seleccionaron hojas para procesar")
            return
        
        print(f"📋 Se procesarán {len(hojas_seleccionadas)} hoja(s):")
        for i, hoja in enumerate(hojas_seleccionadas, 1):
            print(f"  {i}. {hoja}")
        
        # Procesar cada hoja
        resultados = []
        exitosos = 0
        fallidos = 0
        
        for idx, hoja in enumerate(hojas_seleccionadas, 1):
            print(f"\n🔄 Procesando {idx}/{len(hojas_seleccionadas)}: {hoja}")
            
            resultado = procesar_hoja_excel(archivo_busqueda, hoja, config_lista, api)
            
            if resultado:
                resultados.append(resultado)
                if resultado['exitoso']:
                    exitosos += 1
                else:
                    fallidos += 1
            else:
                fallidos += 1
        
        # Resumen final
        print(f"\n📊 Resumen del proceso:")
        print(f"   ✅ Exitosos: {exitosos}")
        print(f"   ❌ Fallidos: {fallidos}")
        print(f"   📊 Total: {len(hojas_seleccionadas)}")
        
        if resultados:
            print(f"\n📋 Listas creadas:")
            for r in resultados:
                if r['exitoso']:
                    print(f"   • {r['nombre_lista']} (ID: {r['list_id']}) - {r['suscriptores_agregados']} suscriptores")
        
        # Notificación
        if exitosos > 0:
            # notify("Listas creadas", f"Se crearon {exitosos} listas exitosamente")
            print(f"🎉 Se crearon {exitosos} listas exitosamente")
        else:
            # notify("Error", "No se pudieron crear listas")
            print("❌ No se pudieron crear listas")
        
        logger.info(f"Proceso completado: {exitosos} exitosos, {fallidos} fallidos")
        
    finally:
        # Cerrar API al finalizar
        api.close()

if __name__ == "__main__":
    main()