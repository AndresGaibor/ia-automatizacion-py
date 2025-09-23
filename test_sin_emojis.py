#!/usr/bin/env python3
"""
Script para probar las validaciones y notificaciones sin emojis
"""

import sys
sys.path.insert(0, '.')

from app import (
    validar_configuracion, 
    validar_archivo_busqueda, 
    validar_archivo_busqueda_listas, 
    validar_archivo_segmentos
)
from src.utils import notify

def test_validaciones_sin_emojis():
    """Prueba el sistema de validaciones con mensajes profesionales"""
    
    print("Probando sistema de validaciones sin emojis...")
    print("=" * 50)
    
    print("\n1. Validando configuración...")
    valid, message = validar_configuracion()
    print(f"   Resultado: {message}")
    
    print("\n2. Validando archivo de búsqueda...")
    valid, message, count = validar_archivo_busqueda()
    print(f"   Resultado: {message}")
    
    print("\n3. Validando archivo de búsqueda de listas...")
    valid, message, count = validar_archivo_busqueda_listas()
    print(f"   Resultado: {message}")
    
    print("\n4. Validando archivo de segmentos...")
    valid, message, count = validar_archivo_segmentos()
    print(f"   Resultado: {message}")
    
    print("\n5. Probando sistema de notificaciones...")
    notify("Información", "Esta es una notificación informativa", "info")
    notify("Advertencia", "Esta es una notificación de advertencia", "warning")
    notify("Error", "Esta es una notificación de error", "error")
    
    print("\nPruebas de validación completadas")

if __name__ == "__main__":
    test_validaciones_sin_emojis()