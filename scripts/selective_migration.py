#!/usr/bin/env python3
"""
Script para migración selectiva de PGVector a Neo4j.
Permite elegir cuentas específicas, tipos de contenido, y filtros.
"""

import asyncio
import sys
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_session
from tools.cognee_knowledge_graph_tool import CogneeKnowledgeGraphTool
from sqlalchemy import text
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SelectiveMigrator:
    """Migrador selectivo con filtros avanzados."""
    
    def __init__(self):
        self.cognee_tool = CogneeKnowledgeGraphTool()
    
    async def migrate_by_criteria(
        self,
        account_ids: Optional[List[str]] = None,
        content_types: Optional[List[str]] = None,
        min_content_length: int = 50,
        max_records_per_account: int = 100,
        days_back: Optional[int] = None
    ):
        """Migra datos según criterios específicos."""
        
        logger.info("🎯 Iniciando migración selectiva...")
        logger.info(f"   • Cuentas: {account_ids or 'Todas'}")
        logger.info(f"   • Tipos de contenido: {content_types or 'Todos'}")
        logger.info(f"   • Longitud mínima: {min_content_length}")
        logger.info(f"   • Máximo por cuenta: {max_records_per_account}")
        logger.info(f"   • Días hacia atrás: {days_back or 'Sin límite'}")
        
        # Construir query dinámicamente
        conditions = ["LENGTH(content) >= :min_length"]
        params = {"min_length": min_content_length}
        
        if account_ids:
            conditions.append("account_id = ANY(:account_ids)")
            params["account_ids"] = account_ids
        
        if content_types:
            conditions.append("content_type = ANY(:content_types)")
            params["content_types"] = content_types
        
        if days_back:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            conditions.append("created_at >= :cutoff_date")
            params["cutoff_date"] = cutoff_date
        
        where_clause = " AND ".join(conditions)
        
        query = text(f"""
            SELECT 
                account_id,
                content,
                metadata,
                content_type,
                ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY id DESC) as row_num
            FROM langchain_pg_embedding 
            WHERE {where_clause}
            ORDER BY account_id, id DESC
        """)
        
        async with get_session() as session:
            result = await session.execute(query, params)
            
            documents_by_account = {}
            processed_count = 0
            
            for row in result:
                if row.row_num > max_records_per_account:
                    continue
                
                account_id = row.account_id
                if account_id not in documents_by_account:
                    documents_by_account[account_id] = []
                
                metadata = row.metadata if row.metadata else {}
                
                document = {
                    "id": f"{row.content_type}_{len(documents_by_account[account_id])}",
                    "title": self._generate_title(row.content, metadata, row.content_type),
                    "content": row.content,
                    "metadata": {
                        **metadata,
                        "source": "selective_migration",
                        "content_type": row.content_type,
                        "migrated_at": datetime.now().isoformat()
                    }
                }
                
                documents_by_account[account_id].append(document)
                processed_count += 1
            
            logger.info(f"📊 Encontrados {processed_count} registros para migrar")
            
            # Procesar por cuenta
            for account_id, documents in documents_by_account.items():
                await self._process_account_documents(account_id, documents)
            
            logger.info(f"✅ Migración selectiva completada: {processed_count} registros")
    
    def _generate_title(self, content: str, metadata: Dict, content_type: str) -> str:
        """Genera un título apropiado para el documento."""
        
        # Intentar obtener título de metadatos
        if 'file_name' in metadata:
            return metadata['file_name']
        
        if 'title' in metadata:
            return metadata['title']
        
        # Generar título basado en contenido
        first_line = content.split('\n')[0].strip()
        if len(first_line) > 5 and len(first_line) < 100:
            return first_line
        
        # Título por defecto basado en tipo
        type_titles = {
            'user_documents': 'Documento',
            'user_memory': 'Memoria',
            'chat_summary': 'Conversación',
            'conversation': 'Chat'
        }
        
        return type_titles.get(content_type, 'Contenido')
    
    async def _process_account_documents(self, account_id: str, documents: List[Dict]):
        """Procesa documentos para una cuenta."""
        
        if not documents:
            return
        
        logger.info(f"🔄 Procesando {len(documents)} documentos para {account_id}")
        
        try:
            # Agrupar por tipo de contenido
            by_type = {}
            for doc in documents:
                content_type = doc['metadata']['content_type']
                if content_type not in by_type:
                    by_type[content_type] = []
                by_type[content_type].append(doc)
            
            # Procesar cada tipo por separado
            for content_type, docs in by_type.items():
                dataset_name = f"selective_{content_type}"
                
                result = await self.cognee_tool._arun(
                    action="process_documents",
                    account_id=account_id,
                    documents=docs,
                    dataset_name=dataset_name
                )
                
                logger.info(f"✅ Procesados {len(docs)} documentos de tipo {content_type}")
        
        except Exception as e:
            logger.error(f"❌ Error procesando documentos para {account_id}: {e}")
    
    async def list_available_accounts(self) -> List[str]:
        """Lista las cuentas disponibles para migración."""
        
        async with get_session() as session:
            query = text("""
                SELECT 
                    account_id,
                    COUNT(*) as record_count,
                    COUNT(DISTINCT content_type) as content_types
                FROM langchain_pg_embedding
                WHERE account_id IS NOT NULL
                GROUP BY account_id
                ORDER BY record_count DESC
                LIMIT 50
            """)
            
            result = await session.execute(query)
            accounts = []
            
            print("\n📋 Cuentas disponibles:")
            for i, row in enumerate(result, 1):
                accounts.append(row.account_id)
                print(f"   {i:2d}. {row.account_id} ({row.record_count} registros, {row.content_types} tipos)")
            
            return accounts
    
    async def list_content_types(self) -> List[str]:
        """Lista los tipos de contenido disponibles."""
        
        async with get_session() as session:
            query = text("""
                SELECT 
                    content_type,
                    COUNT(*) as count
                FROM langchain_pg_embedding
                WHERE content_type IS NOT NULL
                GROUP BY content_type
                ORDER BY count DESC
            """)
            
            result = await session.execute(query)
            content_types = []
            
            print("\n📝 Tipos de contenido disponibles:")
            for i, row in enumerate(result, 1):
                content_types.append(row.content_type)
                print(f"   {i}. {row.content_type} ({row.count} registros)")
            
            return content_types

async def interactive_migration():
    """Migración interactiva con selección de criterios."""
    
    migrator = SelectiveMigrator()
    
    print("🎯 Migración Selectiva PGVector → Neo4j")
    print("=" * 50)
    
    # 1. Mostrar cuentas disponibles
    available_accounts = await migrator.list_available_accounts()
    
    # 2. Seleccionar cuentas
    account_selection = input("\nSeleccionar cuentas (números separados por comas, o 'all' para todas): ")
    
    if account_selection.lower() == 'all':
        selected_accounts = None
    else:
        try:
            indices = [int(x.strip()) - 1 for x in account_selection.split(',')]
            selected_accounts = [available_accounts[i] for i in indices if 0 <= i < len(available_accounts)]
        except:
            print("❌ Selección inválida, usando todas las cuentas")
            selected_accounts = None
    
    # 3. Mostrar tipos de contenido
    available_types = await migrator.list_content_types()
    
    # 4. Seleccionar tipos de contenido
    type_selection = input("\nSeleccionar tipos de contenido (números separados por comas, o 'all' para todos): ")
    
    if type_selection.lower() == 'all':
        selected_types = None
    else:
        try:
            indices = [int(x.strip()) - 1 for x in type_selection.split(',')]
            selected_types = [available_types[i] for i in indices if 0 <= i < len(available_types)]
        except:
            print("❌ Selección inválida, usando todos los tipos")
            selected_types = None
    
    # 5. Configurar filtros adicionales
    min_length = int(input("\nLongitud mínima de contenido (default 50): ") or "50")
    max_per_account = int(input("Máximo de registros por cuenta (default 100): ") or "100")
    days_back = input("Días hacia atrás (default sin límite): ")
    days_back = int(days_back) if days_back.strip() else None
    
    # 6. Confirmar y ejecutar
    print(f"\n📋 Configuración de migración:")
    print(f"   • Cuentas: {len(selected_accounts) if selected_accounts else 'Todas'}")
    print(f"   • Tipos: {len(selected_types) if selected_types else 'Todos'}")
    print(f"   • Longitud mínima: {min_length}")
    print(f"   • Máximo por cuenta: {max_per_account}")
    print(f"   • Días hacia atrás: {days_back or 'Sin límite'}")
    
    confirm = input("\n¿Proceder con la migración? [y/N]: ")
    if confirm.lower() != 'y':
        print("❌ Migración cancelada")
        return
    
    # Ejecutar migración
    await migrator.migrate_by_criteria(
        account_ids=selected_accounts,
        content_types=selected_types,
        min_content_length=min_length,
        max_records_per_account=max_per_account,
        days_back=days_back
    )
    
    print("\n✅ Migración selectiva completada!")
    print("🌐 Revisa los resultados en Neo4j Browser: http://localhost:7474")

if __name__ == "__main__":
    asyncio.run(interactive_migration())
