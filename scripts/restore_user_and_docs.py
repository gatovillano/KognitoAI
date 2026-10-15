import asyncio
import os
import sys
import uuid
from pathlib import Path
from sqlalchemy import select

# Setup path
sys.path.append(os.getcwd())

from core.database import SessionLocal, Account, Document, DocumentFolder, UserDocumentTopic

TARGET_ACCOUNT_ID = uuid.UUID("5b8d59b0-69b7-4aa8-9bb0-bf07511222a6")
STORAGE_DOCS_ROOT = Path("storage/onlyoffice/documents") / str(TARGET_ACCOUNT_ID)

async def restore_docs():
    print(f"🔄 Iniciando sincronización de documentos para {TARGET_ACCOUNT_ID}...")
    
    async with SessionLocal() as session:
        if not STORAGE_DOCS_ROOT.exists():
            print(f"⚠️ No se encontró la ruta de documentos: {STORAGE_DOCS_ROOT}")
            return
            
        print(f"📂 Escaneando archivos en {STORAGE_DOCS_ROOT}...")
        
        folder_map = {} # name -> folder_id
        
        # Encontrar carpetas de primer nivel
        for entry in STORAGE_DOCS_ROOT.iterdir():
            if entry.is_dir() and not entry.name.startswith("."):
                folder_name = entry.name
                # Buscar o crear carpeta
                res_f = await session.execute(
                    select(DocumentFolder).where(
                        DocumentFolder.account_id == TARGET_ACCOUNT_ID,
                        DocumentFolder.name == folder_name
                    )
                )
                folder = res_f.scalars().first()
                if not folder:
                    folder = DocumentFolder(
                        id=uuid.uuid4(),
                        account_id=TARGET_ACCOUNT_ID,
                        name=folder_name,
                        parent_id=None
                    )
                    session.add(folder)
                    await session.flush()
                    print(f"  📁 Carpeta registrada: {folder_name}")
                folder_map[folder_name] = folder.id
                
        await session.commit()
        
        # Registrar documentos en la raíz
        total_docs = 0
        for file_path in STORAGE_DOCS_ROOT.iterdir():
            if file_path.is_file() and not file_path.name.startswith("."):
                filename = file_path.name
                ext = file_path.suffix.lstrip(".").lower()
                rel_path = str(Path(str(TARGET_ACCOUNT_ID)) / filename)
                
                # Verificar si ya existe
                res_d = await session.execute(
                    select(Document).where(
                        Document.account_id == TARGET_ACCOUNT_ID,
                        Document.filename == filename,
                        Document.folder_id == None
                    )
                )
                if not res_d.scalars().first():
                    doc = Document(
                        id=uuid.uuid4(),
                        account_id=TARGET_ACCOUNT_ID,
                        folder_id=None,
                        filename=filename,
                        extension=ext,
                        file_path=rel_path
                    )
                    session.add(doc)
                    total_docs += 1

        # Registrar documentos dentro de las carpetas
        for folder_name, folder_id in folder_map.items():
            folder_dir = STORAGE_DOCS_ROOT / folder_name
            for file_path in folder_dir.iterdir():
                if file_path.is_file() and not file_path.name.startswith("."):
                    filename = file_path.name
                    ext = file_path.suffix.lstrip(".").lower()
                    rel_path = str(Path(str(TARGET_ACCOUNT_ID)) / folder_name / filename)
                    
                    res_d = await session.execute(
                        select(Document).where(
                            Document.account_id == TARGET_ACCOUNT_ID,
                            Document.filename == filename,
                            Document.folder_id == folder_id
                        )
                    )
                    if not res_d.scalars().first():
                        doc = Document(
                            id=uuid.uuid4(),
                            account_id=TARGET_ACCOUNT_ID,
                            folder_id=folder_id,
                            filename=filename,
                            extension=ext,
                            file_path=rel_path
                        )
                        session.add(doc)
                        total_docs += 1
                        
        await session.commit()
        print(f"✅ {total_docs} documentos registrados en PostgreSQL!")

        # 3. Registrar colecciones de temas en user_document_topics
        topics_from_neo4j = [
            "Estrategia Comunalismo",
            "Simulacion2",
            "Plantas",
            "Yoga",
            "Perfil_Cognitivo",
            "IA-Salud-mental",
            "general"
        ]
        created_topics = 0
        for t_name in topics_from_neo4j:
            res_t = await session.execute(
                select(UserDocumentTopic).where(
                    UserDocumentTopic.account_id == TARGET_ACCOUNT_ID,
                    UserDocumentTopic.name == t_name
                )
            )
            if not res_t.scalars().first():
                topic_obj = UserDocumentTopic(
                    id=uuid.uuid4(),
                    account_id=TARGET_ACCOUNT_ID,
                    name=t_name,
                    description=f"Colección {t_name} restaurada",
                    parent_id=None
                )
                session.add(topic_obj)
                created_topics += 1
                
        await session.commit()
        print(f"✅ {created_topics} temas/colecciones registrados en PostgreSQL!")

if __name__ == "__main__":
    asyncio.run(restore_docs())
