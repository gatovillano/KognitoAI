#!/usr/bin/env python3
"""
Script para analizar los datos existentes en PGVector antes de la migración.
Proporciona estadísticas y recomendaciones para la migración.
"""

import asyncio
import sys
import os
from datetime import datetime
import json

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_session
from sqlalchemy import text
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PGVectorAnalyzer:
    """Analizador de datos existentes en PGVector."""
    
    def __init__(self):
        self.analysis_results = {}
    
    async def analyze_all_data(self):
        """Analiza todos los datos en PGVector."""
        
        logger.info("🔍 Analizando datos existentes en PGVector...")
        
        # 1. Estadísticas generales
        await self._analyze_general_stats()
        
        # 2. Análisis por tipo de contenido
        await self._analyze_by_content_type()
        
        # 3. Análisis por cuenta
        await self._analyze_by_account()
        
        # 4. Análisis de calidad de datos
        await self._analyze_data_quality()
        
        # 5. Recomendaciones para migración
        await self._generate_migration_recommendations()
        
        # 6. Guardar reporte
        await self._save_analysis_report()
    
    async def _analyze_general_stats(self):
        """Analiza estadísticas generales."""
        
        async with get_session() as session:
            # Conteo total
            query = text("SELECT COUNT(*) as total FROM langchain_pg_embedding")
            result = await session.execute(query)
            total_records = result.scalar()
            
            # Conteo por tabla/colección
            query = text("""
                SELECT collection_name, COUNT(*) as count
                FROM langchain_pg_embedding
                GROUP BY collection_name
                ORDER BY count DESC
            """)
            result = await session.execute(query)
            collections = {row.collection_name: row.count for row in result}
            
            self.analysis_results['general'] = {
                'total_records': total_records,
                'collections': collections,
                'analyzed_at': datetime.now().isoformat()
            }
            
            logger.info(f"📊 Total de registros: {total_records}")
            for collection, count in collections.items():
                logger.info(f"   • {collection}: {count} registros")
    
    async def _analyze_by_content_type(self):
        """Analiza datos por tipo de contenido."""
        
        async with get_session() as session:
            query = text("""
                SELECT 
                    content_type,
                    COUNT(*) as count,
                    AVG(LENGTH(content)) as avg_length,
                    MIN(LENGTH(content)) as min_length,
                    MAX(LENGTH(content)) as max_length
                FROM langchain_pg_embedding
                WHERE content_type IS NOT NULL
                GROUP BY content_type
                ORDER BY count DESC
            """)
            
            result = await session.execute(query)
            content_types = {}
            
            for row in result:
                content_types[row.content_type] = {
                    'count': row.count,
                    'avg_length': int(row.avg_length) if row.avg_length else 0,
                    'min_length': row.min_length,
                    'max_length': row.max_length
                }
            
            self.analysis_results['content_types'] = content_types
            
            logger.info("📝 Análisis por tipo de contenido:")
            for content_type, stats in content_types.items():
                logger.info(f"   • {content_type}: {stats['count']} registros (promedio: {stats['avg_length']} chars)")
    
    async def _analyze_by_account(self):
        """Analiza datos por cuenta de usuario."""
        
        async with get_session() as session:
            query = text("""
                SELECT 
                    account_id,
                    COUNT(*) as total_records,
                    COUNT(DISTINCT content_type) as content_types,
                    SUM(LENGTH(content)) as total_content_length
                FROM langchain_pg_embedding
                WHERE account_id IS NOT NULL
                GROUP BY account_id
                ORDER BY total_records DESC
                LIMIT 20
            """)
            
            result = await session.execute(query)
            accounts = {}
            
            for row in result:
                accounts[row.account_id] = {
                    'total_records': row.total_records,
                    'content_types': row.content_types,
                    'total_content_length': row.total_content_length
                }
            
            self.analysis_results['accounts'] = accounts
            
            logger.info("👥 Top 20 cuentas por volumen de datos:")
            for account_id, stats in list(accounts.items())[:10]:
                logger.info(f"   • {account_id}: {stats['total_records']} registros, {stats['content_types']} tipos")
    
    async def _analyze_data_quality(self):
        """Analiza la calidad de los datos."""
        
        async with get_session() as session:
            # Registros con contenido vacío o muy corto
            query = text("""
                SELECT COUNT(*) as empty_content
                FROM langchain_pg_embedding
                WHERE content IS NULL OR LENGTH(content) < 10
            """)
            result = await session.execute(query)
            empty_content = result.scalar()
            
            # Registros sin metadatos
            query = text("""
                SELECT COUNT(*) as no_metadata
                FROM langchain_pg_embedding
                WHERE metadata IS NULL OR metadata = '{}'
            """)
            result = await session.execute(query)
            no_metadata = result.scalar()
            
            # Registros sin account_id
            query = text("""
                SELECT COUNT(*) as no_account
                FROM langchain_pg_embedding
                WHERE account_id IS NULL
            """)
            result = await session.execute(query)
            no_account = result.scalar()
            
            # Duplicados potenciales (mismo contenido)
            query = text("""
                SELECT COUNT(*) as potential_duplicates
                FROM (
                    SELECT content, COUNT(*) as cnt
                    FROM langchain_pg_embedding
                    WHERE LENGTH(content) > 50
                    GROUP BY content
                    HAVING COUNT(*) > 1
                ) duplicates
            """)
            result = await session.execute(query)
            duplicates = result.scalar()
            
            quality_stats = {
                'empty_content': empty_content,
                'no_metadata': no_metadata,
                'no_account': no_account,
                'potential_duplicates': duplicates,
                'total_records': self.analysis_results['general']['total_records']
            }
            
            # Calcular porcentajes
            total = quality_stats['total_records']
            quality_stats['quality_score'] = (
                (total - empty_content - no_metadata - no_account) / total * 100
            ) if total > 0 else 0
            
            self.analysis_results['data_quality'] = quality_stats
            
            logger.info("🔍 Análisis de calidad de datos:")
            logger.info(f"   • Contenido vacío: {empty_content} ({empty_content/total*100:.1f}%)")
            logger.info(f"   • Sin metadatos: {no_metadata} ({no_metadata/total*100:.1f}%)")
            logger.info(f"   • Sin account_id: {no_account} ({no_account/total*100:.1f}%)")
            logger.info(f"   • Duplicados potenciales: {duplicates}")
            logger.info(f"   • Puntuación de calidad: {quality_stats['quality_score']:.1f}%")
    
    async def _generate_migration_recommendations(self):
        """Genera recomendaciones para la migración."""
        
        recommendations = []
        
        # Basado en volumen de datos
        total_records = self.analysis_results['general']['total_records']
        if total_records > 10000:
            recommendations.append({
                'type': 'performance',
                'message': f'Alto volumen de datos ({total_records} registros). Considera migrar en lotes.',
                'action': 'Usar límites por cuenta (ej: 100 elementos por cuenta)'
            })
        
        # Basado en calidad de datos
        quality_score = self.analysis_results['data_quality']['quality_score']
        if quality_score < 80:
            recommendations.append({
                'type': 'quality',
                'message': f'Calidad de datos baja ({quality_score:.1f}%). Considera limpieza previa.',
                'action': 'Filtrar registros con contenido < 50 caracteres'
            })
        
        # Basado en tipos de contenido
        content_types = self.analysis_results['content_types']
        if 'user_documents' in content_types and content_types['user_documents']['count'] > 1000:
            recommendations.append({
                'type': 'strategy',
                'message': 'Gran cantidad de documentos. Priorizar documentos más recientes.',
                'action': 'Migrar primero documentos con metadatos de fecha'
            })
        
        # Basado en distribución por cuenta
        accounts = self.analysis_results['accounts']
        if len(accounts) > 50:
            recommendations.append({
                'type': 'scalability',
                'message': f'Muchas cuentas ({len(accounts)}). Migrar por lotes de cuentas.',
                'action': 'Procesar 10-20 cuentas por ejecución'
            })
        
        self.analysis_results['recommendations'] = recommendations
        
        logger.info("💡 Recomendaciones para la migración:")
        for i, rec in enumerate(recommendations, 1):
            logger.info(f"   {i}. [{rec['type'].upper()}] {rec['message']}")
            logger.info(f"      → {rec['action']}")
    
    async def _save_analysis_report(self):
        """Guarda el reporte de análisis."""
        
        filename = f"pgvector_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.analysis_results, f, indent=2)
        
        logger.info(f"📄 Reporte guardado en: {filename}")

async def main():
    """Función principal del análisis."""
    
    print("🔍 Analizador de Datos PGVector")
    print("=" * 40)
    
    analyzer = PGVectorAnalyzer()
    
    try:
        await analyzer.analyze_all_data()
        
        print("\n" + "=" * 40)
        print("✅ Análisis completado!")
        print("\n📊 Resumen:")
        
        general = analyzer.analysis_results['general']
        quality = analyzer.analysis_results['data_quality']
        
        print(f"   • Total de registros: {general['total_records']}")
        print(f"   • Calidad de datos: {quality['quality_score']:.1f}%")
        print(f"   • Cuentas analizadas: {len(analyzer.analysis_results['accounts'])}")
        
        print("\n💡 Recomendaciones:")
        for rec in analyzer.analysis_results['recommendations']:
            print(f"   • {rec['message']}")
        
        print(f"\n📄 Reporte detallado guardado")
        
    except Exception as e:
        logger.error(f"❌ Error durante el análisis: {e}")
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
