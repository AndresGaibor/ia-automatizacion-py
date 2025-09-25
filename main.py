#!/usr/bin/env python3
"""
Script principal para gestionar suscriptores en lista específica
Lista ID: 1168867 (Prueba_SEGMENTOS)
"""

import sys
sys.path.insert(0, '.')

from src.api import API
from src.api.models.suscriptores import ListSummary
from datetime import datetime
from typing import List, Optional

def pause_for_user(message: str = ""):
	"""Pausa la ejecución hasta que el usuario presione Enter"""
	if message:
		print(f"\n⏸️  {message}")
	else:
		print("\n⏸️  Presiona Enter para continuar...")
	input()

def main():
	print("🎯 GESTIÓN DE SUSCRIPTORES - Lista 1168867 (Prueba_SEGMENTOS)")
	print("=" * 60)
	
	# Configurar API integrada
	with API() as api:

		campanias = api.campaigns.get_all()
		for campania in campanias:
			print(campania)
		print("✅ API integrada inicializada correctamente\n")
		
		# ID de la lista objetivo
		target_list_id = 1168867
		target_email = "usuario_10002@example.com"  # Email del attachment
		nuevo_segmento = "Segmento4"
		
		print(f"📋 Lista objetivo: {target_list_id}")
		print(f"👤 Usuario objetivo: {target_email}")
		print(f"🎯 Nuevo segmento: {nuevo_segmento}\n")
		
		pause_for_user("¿Listo para comenzar? Los siguientes pasos serán:")
		print("   1️⃣ Verificar que la lista existe")
		print("   2️⃣ Buscar el usuario en la lista")
		print("   3️⃣ Eliminar el usuario si existe")
		print("   4️⃣ Agregar el usuario con el nuevo segmento")
		print("   5️⃣ Verificar el resultado final")
		pause_for_user()
		
		# 1. VERIFICAR QUE LA LISTA EXISTE
		print("1️⃣ Verificando lista objetivo...")
		try:
			listas: List[ListSummary] = api.suscriptores.get_lists()
			lista_encontrada: Optional[ListSummary] = None
			
			print(f"   📊 Total de listas encontradas: {len(listas)}")
			
			# Buscar la lista objetivo
			for lista in listas:
				if lista.id == target_list_id:
					lista_encontrada = lista
					print(f"   ✅ Lista encontrada: {lista.name} (ID: {lista.id})")
					break
			
			if not lista_encontrada:
				print(f"❌ Error: Lista {target_list_id} no encontrada")
				print("   📋 Listas disponibles:")
				for lista in listas[:5]:  # Mostrar solo las primeras 5
					print(f"      - ID: {lista.id} | Nombre: {lista.name}")
				return
			
		except Exception as e:
			print(f"   ❌ Error verificando lista: {e}")
			return
		
		pause_for_user("Lista verificada exitosamente. Continuar con búsqueda de usuario?")
		
		# 2. BUSCAR EL USUARIO EN LA LISTA
		print(f"\n2️⃣ Buscando usuario {target_email}...")
		try:
			# Obtener suscriptores de la lista
			subscribers = api.suscriptores.get_subscribers(
				list_id=target_list_id,
				status=1,  # Activos
				block_index=0,  # Primera página
				all_fields=1  # Obtener todos los campos
			)
			
			user_found = False
			user_data = None
			
			if isinstance(subscribers, dict):
				for email, data in subscribers.items():
					if email == target_email:
						user_found = True
						user_data = data
						print(f"   ✅ Usuario encontrado: {email}")
						print(f"   📊 Status: {data.get('status', 'N/A')}")
						print(f"   🆔 ID: {data.get('id', 'N/A')}")
						break
			
			if not user_found:
				print(f"   ⚠️  Usuario {target_email} no encontrado en la lista")
				print("   💡 Agregando usuario directamente con el nuevo segmento...")
				
				# Agregar usuario directamente si no existe
				result = api.suscriptores.add_subscriber(
					list_id=target_list_id,
					merge_fields={
						'email': target_email,
						'segmento': nuevo_segmento
					}
				)
				print(f"   ✅ Usuario agregado con ID: {result}")
				
				print("\n🎉 PROCESO COMPLETADO")
				print("📝 Resumen:")
				print(f"   • Lista: {target_list_id} (Prueba_SEGMENTOS)")
				print(f"   • Usuario: {target_email}")
				print(f"   • Nuevo segmento: {nuevo_segmento}")
				print("   • Acción: Usuario agregado (no existía previamente)")
				print(f"   • Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
				
				pause_for_user("Usuario agregado exitosamente. Presiona Enter para finalizar.")
				return
				
		except Exception as e:
			# Si no hay suscriptores en la lista o el usuario no existe
			error_str = str(e)
			if "400" in error_str and "No subscribers for selected parameters" in error_str:
				print("   ℹ️  Lista vacía o el usuario no existe en la lista (esto es normal)")
				print("   � La API devuelve error 400 cuando no encuentra suscriptores con los parámetros dados")
			else:
				print(f"   ⚠️  Error inesperado buscando usuario: {e}")
			
			print("   💡 Procediendo a agregar/actualizar usuario directamente...")
			
			try:
				# Agregar usuario con actualización habilitada
				result = api.suscriptores.add_subscriber(
					list_id=target_list_id,
					merge_fields={
						'email': target_email,
						'segmento': nuevo_segmento
					},
					update_subscriber=1  # Actualizar si ya existe
				)
				print(f"   ✅ Usuario agregado/actualizado con ID: {result}")
				
				print("\n🎉 PROCESO COMPLETADO")
				print("📝 Resumen:")
				print(f"   • Lista: {target_list_id} (Prueba_SEGMENTOS)")
				print(f"   • Usuario: {target_email}")
				print(f"   • Nuevo segmento: {nuevo_segmento}")
				print("   • Acción: Usuario agregado/actualizado con nuevo segmento")
				print(f"   • Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
				
				pause_for_user("Usuario procesado exitosamente. Presiona Enter para finalizar.")
				return
				
			except Exception as add_error:
				print(f"   ❌ Error agregando/actualizando usuario: {add_error}")
				return
		
		pause_for_user("Usuario encontrado en la lista. Continuar con eliminación?")
		
		# 3. ELIMINAR EL USUARIO EXISTENTE
		print("\n3️⃣ Eliminando usuario existente...")
		try:
			# Usar el método individual de eliminación
			api.suscriptores.delete_subscriber(list_id=target_list_id, email=target_email)
			print(f"   ✅ Usuario {target_email} eliminado exitosamente")
			
		except Exception as e:
			print(f"   ❌ Error eliminando usuario: {e}")
			print("   ⚠️  Continuando con la adición...")
		
		pause_for_user("Eliminación completada. Continuar con adición del usuario con nuevo segmento?")
		
		# 4. AGREGAR EL USUARIO CON EL NUEVO SEGMENTO
		print(f"\n4️⃣ Agregando usuario con segmento '{nuevo_segmento}'...")
		try:
			result = api.suscriptores.add_subscriber(
				list_id=target_list_id,
				merge_fields={
					'email': target_email,
					'segmento': nuevo_segmento
				},
				update_subscriber=1  # Actualizar si existe
			)
			
			print(f"   ✅ Usuario agregado exitosamente con ID: {result}")
			
		except Exception as e:
			print(f"   ❌ Error agregando usuario: {e}")
			return
		
		pause_for_user("Usuario agregado exitosamente. Continuar con verificación final?")
		
		# 5. VERIFICAR EL RESULTADO
		print("\n5️⃣ Verificando resultado final...")
		try:
			# Verificar que el usuario está en la lista con el nuevo segmento
			subscribers_final = api.suscriptores.get_subscribers(
				list_id=target_list_id,
				status=1,
				block_index=0,
				all_fields=1
			)
			
			if isinstance(subscribers_final, dict) and target_email in subscribers_final:
				user_final = subscribers_final[target_email]
				print("   ✅ Verificación exitosa:")
				print(f"      📧 Email: {target_email}")
				print(f"      📊 Status: {user_final.get('status', 'N/A')}")
				print(f"      🆔 ID: {user_final.get('id', 'N/A')}")
				
				# Intentar obtener el segmento si está disponible
				try:
					subscriber_details = api.suscriptores.get_subscriber_details(
						list_id=target_list_id,
						subscriber=target_email
					)
					print("      🎯 Detalles obtenidos del suscriptor")
					print(f"      🎯 Segmento: Se asignó '{nuevo_segmento}' (verificar en interfaz)")
				except:
					print(f"      🎯 Segmento: Se asignó '{nuevo_segmento}' (verificar en interfaz)")
			else:
				print("   ⚠️  No se pudo verificar el usuario en la lista")
				
		except Exception as e:
			print(f"   ⚠️  Error en verificación final: {e}")
		
		print("\n🎉 PROCESO COMPLETADO")
		print("📝 Resumen:")
		print(f"   • Lista: {target_list_id} (Prueba_SEGMENTOS)")
		print(f"   • Usuario: {target_email}")
		print(f"   • Nuevo segmento: {nuevo_segmento}")
		print("   • Acción: Usuario eliminado y re-agregado con nuevo segmento")
		print(f"   • Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
		
		pause_for_user("¡Proceso completado exitosamente! Presiona Enter para finalizar.")

if __name__ == "__main__":
	main()