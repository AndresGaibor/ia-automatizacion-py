#!/usr/bin/env python3
"""
Script de prueba para verificar las validaciones y notificaciones
"""

import os
import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.utils import load_config, notify

def test_validaciones():
    """Prueba todas las validaciones implementadas"""
    
    print("🔍 Probando sistema de validaciones...")
    
    # Importar funciones de validación desde app.py
    import importlib.util
    spec = importlib.util.spec_from_file_location("app_validations", "app.py")
    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)
    
    # Prueba 1: Validar configuración
    print("\n1. Validando configuración...")
    valid, message = app_module.validar_configuracion()
    print(f"   Resultado: {message}")
    
    # Prueba 2: Validar archivo de búsqueda
    print("\n2. Validando archivo de búsqueda...")
    valid, message, count = app_module.validar_archivo_busqueda()
    print(f"   Resultado: {message}")
    
    # Prueba 3: Validar archivo de búsqueda de listas
    print("\n3. Validando archivo de búsqueda de listas...")
    valid, message, count = app_module.validar_archivo_busqueda_listas()
    print(f"   Resultado: {message}")
    
    # Prueba 4: Validar archivo de segmentos
    print("\n4. Validando archivo de segmentos...")
    valid, message, count = app_module.validar_archivo_segmentos()
    print(f"   Resultado: {message}")
    
    # Prueba 5: Sistema de notificaciones
    print("\n5. Probando sistema de notificaciones...")
    notify("Prueba", "✅ Sistema de notificaciones funcionando", "info")
    notify("Advertencia de Prueba", "⚠️ Esta es una advertencia de prueba", "warning")
    
    print("\n✅ Pruebas de validación completadas")

if __name__ == "__main__":
    test_validaciones()