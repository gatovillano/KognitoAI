#!/usr/bin/env python3
"""
Script para migrar automáticamente datos de PGVector a Neo4j
Escanea la base de conocimientos existente y crea grafos de conocimiento.
"""

import asyncio
import sys
import os
from typing import Dict, List, Any
from datetime import datetime
import json

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_session
from tools.cognee_knowledge_graph_tool import CogneeKnowledgeGraphTool
from sqlalchemy import text
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PGVectorToNeo4jMigrator:
    """Migrador automático de PGVector a Neo4j."""
    
    def __init__(self):
        self.cognee_tool = CogneeKnowledgeGraphTool()
        self.processed_count = 0
        self.error_count = 0
        self.accounts_processed = set()
    
    async def migrate_all_knowledge(self, limit_per_account: int = 50):
        """Migra todo el conocimiento de PGVector a Neo4j."""
        
        logger.info("🚀 Iniciando migración de PGVector a Neo4j...")
        
        # 1. Migrar documentos
        await self._migrate_documents(limit_per_account)
        
        # 2. Migrar memorias de usuario
        await self._migrate_user_memories(limit_per_account)
        
        # 3. Migrar conversaciones
        await self._migrate_conversations(limit_per_account)
        
        # 4. Crear conexiones entre diferentes tipos de contenido
        await self._create_cross_content_connections()
        
        # 5. Generar reporte final
        await self._generate_migration_report()
        
        logger.info(f"✅ Migración completada: {self.processed_count} elementos procesados")
    
    async def _migrate_documents(self, limit_per_account: int):
        """Migra documentos de PGVector a Neo4j."""
        
        logger.info("📄 Migrando documentos...")
        
        async with get_session() as session:
            query = text("""
                SELECT 
                    account_id,
                    content,
                    metadata,
                    ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY id) as row_num
                FROM langchain_pg_embedding 
                WHERE content_type = 'user_documents'
                AND LENGTH(content) > 100
                ORDER BY account_id, id
            """)
            
            result = await session.execute(query)
            documents_by_account = {}
            
            for row in result:
                if row.row_num > limit_per_account:
                    continue
                
                account_id = row.account_id
                if account_id not in documents_by_account:
                    documents_by_account[account_id] = []
                
                # Extraer metadatos
                metadata = row.metadata if row.metadata else {}
                
                document = {
                    "id": f"doc_{len(documents_by_account[account_id])}",
                    "title": metadata.get('file_name', f"Documento {len(documents_by_account[account_id]) + 1}"),
                    "content": row.content,
                    "metadata": {
                        **metadata,
                        "source": "pgvector_migration",
                        "content_type": "document",
                        "migrated_at": datetime.now().isoformat()
                    }
                }
                
                documents_by_account[account_id].append(document)
        
        # Procesar por cuenta
        for account_id, documents in documents_by_account.items():
            await self._process_documents_for_account(account_id, documents, "migrated_documents")
            self.accounts_processed.add(account_id)
    
    async def _migrate_user_memories(self, limit_per_account: int):
        """Migra memorias de usuario de PGVector a Neo4j."""
        
        logger.info("🧠 Migrando memorias de usuario...")
        
        async with get_session() as session:
            query = text("""
                SELECT 
                    account_id,
                    content,
                    metadata,
                    ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY id) as row_num
                FROM langchain_pg_embedding 
                WHERE content_type = 'user_memory'
                AND LENGTH(content) > 50
                ORDER BY account_id, id
            """)
            
            result = await session.execute(query)
            memories_by_account = {}
            
            for row in result:
                if row.row_num > limit_per_account:
                    continue
                
                account_id = row.account_id
                if account_id not in memories_by_account:
                    memories_by_account[account_id] = []
                
                metadata = row.metadata if row.metadata else {}
                
                memory = {
                    "id": f"memory_{len(memories_by_account[account_id])}",
                    "title": f"Memoria: {metadata.get('category', 'General')}",
                    "content": row.content,
                    "metadata": {
                        **metadata,
                        "source": "pgvector_migration",
                        "content_type": "memory",
                        "migrated_at": datetime.now().isoformat()
                    }
                }
                
                memories_by_account[account_id].append(memory)
        
        # Procesar memorias por cuenta
        for account_id, memories in memories_by_account.items():
            await self._process_documents_for_account(account_id, memories, "migrated_memories")
            self.accounts_processed.add(account_id)
    
    async def _migrate_conversations(self, limit_per_account: int):
        """Migra conversaciones de PGVector a Neo4j."""
        
        logger.info("💬 Migrando conversaciones...")
        
        async with get_session() as session:
            query = text("""
                SELECT 
                    account_id,
                    content,
                    metadata,
                    ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY id) as row_num
                FROM langchain_pg_embedding 
                WHERE content_type IN ('chat_summary', 'conversation')
                AND LENGTH(content) > 100
                ORDER BY account_id, id
            """)
            
            result = await session.execute(query)
            conversations_by_account = {}
            
            for row in result:
                if row.row_num > limit_per_account:
                    continue
                
                account_id = row.account_id
                if account_id not in conversations_by_account:
                    conversations_by_account[account_id] = []
                
                metadata = row.metadata if row.metadata else {}
                
                conversation = {
                    "id": f"conv_{len(conversations_by_account[account_id])}",
                    "title": f"Conversación {len(conversations_by_account[account_id]) + 1}",
                    "content": row.content,
                    "metadata": {
                        **metadata,
                        "source": "pgvector_migration",
                        "content_type": "conversation",
                        "migrated_at": datetime.now().isoformat()
                    }
                }
                
                conversations_by_account[account_id].append(conversation)
        
        # Procesar conversaciones por cuenta
        for account_id, conversations in conversations_by_account.items():
            await self._process_documents_for_account(account_id, conversations, "migrated_conversations")
            self.accounts_processed.add(account_id)
    
    async def _process_documents_for_account(self, account_id: str, documents: List[Dict], dataset_name: str):
        """Procesa documentos para una cuenta específica."""
        
        if not documents:
            return
        
        logger.info(f"🔄 Procesando {len(documents)} elementos para {account_id} en dataset {dataset_name}")
        
        try:
            result = await self.cognee_tool._arun(
                action="process_documents",
                account_id=account_id,
                documents=documents,
                dataset_name=dataset_name
            )
            
            self.processed_count += len(documents)
            logger.info(f"✅ Procesados {len(documents)} elementos para {account_id}")
            
        except Exception as e:
            self.error_count += len(documents)
            logger.error(f"❌ Error procesando documentos para {account_id}: {e}")
    
    async def _create_cross_content_connections(self):
        """Crea conexiones entre diferentes tipos de contenido."""
        
        logger.info("🔗 Creando conexiones entre tipos de contenido...")
        
        for account_id in self.accounts_processed:
            try:
                # Buscar conexiones entre documentos y memorias
                search_result = await self.cognee_tool._arun(
                    action="get_insights",
                    account_id=account_id,
                    query="conexiones entre documentos y memorias",
                    dataset_name="migrated_documents"
                )
                
                logger.info(f"🔍 Conexiones encontradas para {account_id}")
                
            except Exception as e:
                logger.warning(f"⚠️ No se pudieron crear conexiones para {account_id}: {e}")
    
    async def _generate_migration_report(self):
        """Genera reporte final de la migración."""
        
        report = {
            "migration_completed_at": datetime.now().isoformat(),
            "total_processed": self.processed_count,
            "total_errors": self.error_count,
            "accounts_processed": len(self.accounts_processed),
            "accounts_list": list(self.accounts_processed),
            "success_rate": (self.processed_count / (self.processed_count + self.error_count)) * 100 if (self.processed_count + self.error_count) > 0 else 0
        }
        
        # Guardar reporte
        with open("migration_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        logger.info("📊 Reporte de migración:")
        logger.info(f"   • Elementos procesados: {self.processed_count}")
        logger.info(f"   • Errores: {self.error_count}")
        logger.info(f"   • Cuentas procesadas: {len(self.accounts_processed)}")
        logger.info(f"   • Tasa de éxito: {report['success_rate']:.1f}%")
        logger.info(f"   • Reporte guardado en: migration_report.json")

async def main():
    """Función principal del script."""
    
    print("🔄 Migrador Automático: PGVector → Neo4j")
    print("=" * 50)
    
    # Configuración
    limit_per_account = int(input("Límite de elementos por cuenta (default 50): ") or "50")
    
    confirm = input(f"¿Proceder con la migración? (máximo {limit_per_account} elementos por cuenta) [y/N]: ")
    if confirm.lower() != 'y':
        print("❌ Migración cancelada")
        return
    
    # Ejecutar migración
    migrator = PGVectorToNeo4jMigrator()
    
    try:
        await migrator.migrate_all_knowledge(limit_per_account)
        
        print("\n" + "=" * 50)
        print("✅ Migración completada exitosamente!")
        print("\n💡 Próximos pasos:")
        print("1. Accede a Neo4j Browser: http://localhost:7474")
        print("2. Ejecuta: MATCH (n) RETURN n LIMIT 25")
        print("3. Explora los grafos creados por cuenta")
        print("4. Revisa el archivo migration_report.json")
        
    except Exception as e:
        logger.error(f"❌ Error durante la migración: {e}")
        print(f"\n❌ Error: {e}")
        print("\n🔧 Verifica:")
        print("1. Que Neo4j esté corriendo")
        print("2. Que las credenciales sean correctas")
        print("3. Que haya datos en PGVector")

if __name__ == "__main__":
    asyncio.run(main())
