"""
Herramientas de debugging y análisis del sistema de cache
"""
import argparse
import json
import sqlite3
import time
import os
from datetime import datetime
from typing import Dict, Any, List
from src.cache.universal_cache import UniversalAPICache
from src.cache.cleanup_manager import CacheCleanupManager


class CacheAnalyzer:
    def __init__(self, cache: UniversalAPICache):
        self.cache = cache
        self.cleanup_manager = CacheCleanupManager(cache)

    def generate_cache_report(self) -> Dict[str, Any]:
        """Genera reporte completo del estado del cache"""
        print("🔍 Generando reporte de cache...")
        
        if not os.path.exists(self.cache.db_path):
            return {"error": "Database not found", "db_path": self.cache.db_path}

        with sqlite3.connect(self.cache.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Estadísticas por endpoint
            endpoint_stats = conn.execute("""
                SELECT 
                    endpoint_name,
                    COUNT(*) as total_entries,
                    AVG(hit_count) as avg_hits,
                    SUM(CASE WHEN expires_at > datetime('now') THEN 1 ELSE 0 END) as valid_entries,
                    SUM(CASE WHEN expires_at <= datetime('now') THEN 1 ELSE 0 END) as expired_entries,
                    MIN(created_at) as oldest_entry,
                    MAX(created_at) as newest_entry,
                    SUM(LENGTH(response_data)) as total_size_bytes
                FROM api_cache 
                GROUP BY endpoint_name
                ORDER BY total_entries DESC
            """).fetchall()

            # Hit rates recientes
            hit_rates = conn.execute("""
                SELECT 
                    endpoint_name,
                    date,
                    total_requests,
                    cache_hits,
                    cache_misses,
                    CASE WHEN total_requests > 0 
                         THEN (cache_hits * 100.0 / total_requests) 
                         ELSE 0 END as hit_rate
                FROM cache_stats 
                WHERE date >= date('now', '-7 days')
                ORDER BY date DESC, hit_rate DESC
            """).fetchall()

            # Estadísticas globales
            global_stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_cache_entries,
                    SUM(hit_count) as total_hits,
                    SUM(LENGTH(response_data)) as total_size_bytes,
                    COUNT(DISTINCT endpoint_name) as unique_endpoints
                FROM api_cache
            """).fetchone()

        # Calcular tamaño del archivo de base de datos
        db_size_mb = os.path.getsize(self.cache.db_path) / 1024 / 1024 if os.path.exists(self.cache.db_path) else 0

        return {
            "timestamp": datetime.now().isoformat(),
            "database_info": {
                "file_path": self.cache.db_path,
                "size_mb": round(db_size_mb, 2),
                "total_entries": global_stats["total_cache_entries"] if global_stats else 0,
                "total_hits": global_stats["total_hits"] if global_stats else 0,
                "unique_endpoints": global_stats["unique_endpoints"] if global_stats else 0
            },
            "endpoint_stats": [dict(row) for row in endpoint_stats],
            "recent_hit_rates": [dict(row) for row in hit_rates],
            "performance_metrics": self._calculate_performance_metrics(endpoint_stats)
        }

    def _calculate_performance_metrics(self, endpoint_stats: List) -> Dict[str, Any]:
        """Calcula métricas de performance del cache"""
        if not endpoint_stats:
            return {}

        total_entries = sum(row["total_entries"] for row in endpoint_stats)
        total_hits = sum(row["avg_hits"] * row["total_entries"] for row in endpoint_stats)
        
        return {
            "average_hit_count": round(total_hits / total_entries if total_entries > 0 else 0, 2),
            "most_used_endpoint": max(endpoint_stats, key=lambda x: x["avg_hits"])["endpoint_name"] if endpoint_stats else None,
            "cache_efficiency": "High" if total_hits / total_entries > 5 else "Medium" if total_hits / total_entries > 2 else "Low"
        }

    def benchmark_cache_performance(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Compara performance cache vs API directa"""
        print(f"🏃‍♂️ Benchmark para {endpoint} con parámetros: {kwargs}")
        
        # Tiempo con cache (simulado)
        start = time.time()
        cached_result = self.cache.get_cached_response(endpoint, **kwargs)
        cache_time = time.time() - start

        # Calcular tiempo simulado de API (basado en promedios conocidos)
        api_time_estimates = {
            "get_basic_info": 0.8,
            "get_total_info": 1.2,
            "get_clicks": 1.5,
            "get_openers": 1.5,
            "get_subscribers": 2.0,
            "get_lists": 0.6,
            "search_subscriber": 1.0
        }
        
        estimated_api_time = api_time_estimates.get(endpoint, 1.0)
        
        return {
            "endpoint": endpoint,
            "parameters": kwargs,
            "cache_time_ms": round(cache_time * 1000, 2),
            "estimated_api_time_ms": round(estimated_api_time * 1000, 2),
            "speedup_factor": round(estimated_api_time / cache_time if cache_time > 0 else float('inf'), 1),
            "cache_hit": cached_result is not None,
            "timestamp": datetime.now().isoformat()
        }

    def print_detailed_report(self, report: Dict[str, Any]):
        """Imprime reporte detallado en consola"""
        print("\n" + "="*60)
        print("📊 REPORTE DETALLADO DEL SISTEMA DE CACHE")
        print("="*60)
        
        # Info de base de datos
        db_info = report["database_info"]
        print("\n🗄️  INFORMACIÓN DE BASE DE DATOS:")
        print(f"   📁 Archivo: {db_info['file_path']}")
        print(f"   💾 Tamaño: {db_info['size_mb']} MB")
        print(f"   📋 Total entradas: {db_info['total_entries']}")
        print(f"   🎯 Total hits: {db_info['total_hits']}")
        print(f"   🔗 Endpoints únicos: {db_info['unique_endpoints']}")
        
        # Estadísticas por endpoint
        print("\n📈 ESTADÍSTICAS POR ENDPOINT:")
        endpoint_stats = report["endpoint_stats"]
        if endpoint_stats:
            for stat in endpoint_stats:
                print(f"   🎯 {stat['endpoint_name']}:")
                print(f"      📊 Entradas: {stat['total_entries']} (válidas: {stat['valid_entries']}, expiradas: {stat['expired_entries']})")
                print(f"      🔥 Hits promedio: {stat['avg_hits']:.1f}")
                print(f"      💾 Tamaño: {stat['total_size_bytes']/1024:.1f} KB")
                print(f"      📅 Rango: {stat['oldest_entry']} → {stat['newest_entry']}")
        else:
            print("   ⚠️  No hay estadísticas disponibles")
        
        # Hit rates recientes
        print("\n🎯 HIT RATES RECIENTES (últimos 7 días):")
        hit_rates = report["recent_hit_rates"]
        if hit_rates:
            for rate in hit_rates[:10]:  # Mostrar solo los primeros 10
                print(f"   📅 {rate['date']} - {rate['endpoint_name']}: {rate['hit_rate']:.1f}% "
                      f"({rate['cache_hits']}/{rate['total_requests']})")
        else:
            print("   ⚠️  No hay datos de hit rates disponibles")
        
        # Métricas de performance
        performance = report.get("performance_metrics", {})
        if performance:
            print("\n⚡ MÉTRICAS DE PERFORMANCE:")
            print(f"   🎯 Hit count promedio: {performance.get('average_hit_count', 0)}")
            print(f"   🏆 Endpoint más usado: {performance.get('most_used_endpoint', 'N/A')}")
            print(f"   🚀 Eficiencia del cache: {performance.get('cache_efficiency', 'N/A')}")

    def cleanup_and_optimize(self) -> Dict[str, int]:
        """Ejecuta limpieza y optimización del cache"""
        print("🧹 Iniciando limpieza y optimización...")
        
        results = {
            "expired_removed": self.cleanup_manager.cleanup_expired_entries(),
            "limit_cleanup": self.cleanup_manager.cleanup_by_limits(),
            "optimized_db": 0
        }
        
        # Optimizar base de datos SQLite
        with sqlite3.connect(self.cache.db_path) as conn:
            conn.execute("VACUUM")
            conn.execute("ANALYZE")
            results["optimized_db"] = 1
        
        print("✅ Limpieza completada:")
        print(f"   🗑️  Entradas expiradas eliminadas: {results['expired_removed']}")
        print(f"   📊 Entradas por límites eliminadas: {results['limit_cleanup']}")
        print(f"   ⚡ Base de datos optimizada: {'Sí' if results['optimized_db'] else 'No'}")
        
        return results


def main():
    parser = argparse.ArgumentParser(description="Herramientas de debugging para el sistema de cache")
    parser.add_argument("--stats", action="store_true", help="Mostrar estadísticas del cache")
    parser.add_argument("--cleanup", action="store_true", help="Limpiar cache expirado")
    parser.add_argument("--benchmark", help="Hacer benchmark de un endpoint específico")
    parser.add_argument("--export", help="Exportar reporte a archivo JSON")
    
    args = parser.parse_args()
    
    # Inicializar cache y analyzer
    cache = UniversalAPICache()
    analyzer = CacheAnalyzer(cache)
    
    if args.stats:
        report = analyzer.generate_cache_report()
        analyzer.print_detailed_report(report)
        
        if args.export:
            with open(args.export, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"\n📁 Reporte exportado a: {args.export}")
    
    if args.cleanup:
        analyzer.cleanup_and_optimize()
    
    if args.benchmark:
        endpoint = args.benchmark
        # Ejemplo de benchmark con parámetros comunes
        test_params = {
            "get_basic_info": {"campaign_id": 123},
            "get_subscribers": {"list_id": 456},
            "search_subscriber": {"email": "test@example.com"}
        }
        
        params = test_params.get(endpoint, {})
        benchmark = analyzer.benchmark_cache_performance(endpoint, **params)
        
        print("\n🏃‍♂️ BENCHMARK RESULTS:")
        print(f"   Endpoint: {benchmark['endpoint']}")
        print(f"   Cache time: {benchmark['cache_time_ms']} ms")
        print(f"   Estimated API time: {benchmark['estimated_api_time_ms']} ms")
        print(f"   Speedup factor: {benchmark['speedup_factor']}x")
        print(f"   Cache hit: {'✅' if benchmark['cache_hit'] else '❌'}")


if __name__ == "__main__":
    main()