#!/usr/bin/env python3
"""
Script de prueba para verificar la optimización de verificación de segmentos existentes.
"""

import sys
import os
from pathlib import Path

# Agregar el directorio src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.mapeo_segmentos import crear_segmentos_con_scraping_batch
from src.api import API
from src.logger import get_logger

logger = get_logger()

def test_verificacion_segmentos():
    """
    Prueba la función de verificación de segmentos para asegurar que no crea duplicados.
    """
    print("🧪 Probando verificación de segmentos existentes...")
    
    try:
        # Crear cliente API usando la configuración integrada
        api_client = API()
        
        # Usar una lista de prueba (reemplazar con un ID real de tu cuenta)
        test_list_id = 1168867  # Lista de Prueba_SEGMENTOS del main.py
        
        # Segmentos de prueba (algunos que podrían existir, otros que no)
        segmentos_prueba = [
            "TEST_Optimizacion_1",
            "TEST_Optimizacion_2", 
            "TEST_Optimizacion_3"
        ]
        
        print(f"📋 Probando con lista {test_list_id} y segmentos: {segmentos_prueba}")
        
        # Primera ejecución: debería verificar y crear los segmentos
        print("\n=== Primera ejecución ===")
        resultado1 = crear_segmentos_con_scraping_batch(test_list_id, segmentos_prueba, api_client)
        print(f"Resultado primera ejecución: {resultado1}")
        
        # Segunda ejecución: debería detectar que ya existen y no crear duplicados
        print("\n=== Segunda ejecución (verificando duplicados) ===")
        resultado2 = crear_segmentos_con_scraping_batch(test_list_id, segmentos_prueba, api_client)
        print(f"Resultado segunda ejecución: {resultado2}")
        
        print("\n✅ Prueba completada. Los segmentos existentes deberían haberse detectado en la segunda ejecución.")
        
        # Cerrar la conexión API
        api_client.close()
        
    except Exception as e:
        print(f"❌ Error en la prueba: {e}")
        logger.error(f"Error en la prueba de verificación de segmentos: {e}")

if __name__ == "__main__":
    # Mostrar advertencia sobre la prueba
    print("⚠️  ADVERTENCIA: Esta prueba puede crear segmentos reales en tu cuenta de Acumbamail.")
    print("   Asegúrate de usar una lista de prueba y segmentos con prefijo TEST_")
    print("   Presiona Ctrl+C para cancelar o Enter para continuar...")
    
    try:
        input()
        test_verificacion_segmentos()
    except KeyboardInterrupt:
        print("\n❌ Prueba cancelada por el usuario.")