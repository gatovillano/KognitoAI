import asyncio
import os
import sys
import uuid
from sqlalchemy import select

sys.path.append(os.getcwd())

from core.database import SessionLocal, Workspace, WorkspacePermission, DocumentFolder, Document

ACCOUNT_ID = uuid.UUID("5b8d59b0-69b7-4aa8-9bb0-bf07511222a6")

WORKSPACES = [
    {
        "id": uuid.UUID("151b28df-3ee3-4111-8a63-d4be0357986a"),
        "name": "KognitoAI / Inteligencia Artificial",
        "color": "#4f46e5",
        "system_prompt": "Workspace para desarrollo y análisis de KognitoAI e Inteligencia Artificial.",
    },
    {
        "id": uuid.UUID("ce53cc5e-6383-4c23-8942-1f8be6612a9f"),
        "name": "KognitoAI Labs",
        "color": "#2563eb",
        "system_prompt": "Workspace principal de KognitoAI Labs y arquitectura del sistema.",
    },
    {
        "id": uuid.UUID("4bfbbe51-843d-4f34-b291-84918a82e3d3"),
        "name": "Documentos Técnicos",
        "color": "#0284c7",
        "system_prompt": "Workspace de documentación técnica y especificaciones.",
    },
    {
        "id": uuid.UUID("7fa1fff9-8a86-4ff9-81e0-cb6709301632"),
        "name": "Contexto Global",
        "color": "#10b981",
        "system_prompt": "Workspace de contexto global y conocimientos generales.",
    },
    {
        "id": uuid.UUID("b1ff216d-ce2a-4b49-a524-90a5ec7f5f58"),
        "name": "Programación / POO",
        "color": "#f59e0b",
        "system_prompt": "Workspace de desarrollo orientado a objetos, algoritmos y código.",
    },
    {
        "id": uuid.UUID("077ed74a-2e70-4965-a100-58838e9a17f4"),
        "name": "Infraestructura & Cloud",
        "color": "#8b5cf6",
        "system_prompt": "Workspace de despliegue, servidores, Docker, Cloudflare y FastAPI.",
    },
    {
        "id": uuid.UUID("9d6705c4-8acc-4856-9f32-44df70fd515a"),
        "name": "Antropología & Salud",
        "color": "#ec4899",
        "system_prompt": "Workspace de antropología médica, salud mental y cuidados colectivos.",
    },
    {
        "id": uuid.UUID("21a953a9-a746-4a40-bce5-6a33e54ed297"),
        "name": "Salud & Bienestar",
        "color": "#14b8a6",
        "system_prompt": "Workspace de seguimiento de salud, bienestar y hábitos.",
    },
    {
        "id": uuid.UUID("8c56bf6e-b2f0-45ac-b9cc-86901deab5ff"),
        "name": "Sistemas & macOS",
        "color": "#64748b",
        "system_prompt": "Workspace para entornos virtuales, macOS y configuración de sistemas.",
    },
    {
        "id": uuid.UUID("81d5ce63-3ab2-407e-8515-cabc8eb15fe9"),
        "name": "Vínculos & Relaciones",
        "color": "#f43f5e",
        "system_prompt": "Workspace sobre dinámicas relacionales, vínculos y comunicación.",
    },
    {
        "id": uuid.UUID("3fc90b78-5f0b-4e5c-adff-277264136b73"),
        "name": "La Hierbatera / Plantas",
        "color": "#84cc16",
        "system_prompt": "Workspace de fitoterapia, plantas medicinales y medicina natural.",
    },
    {
        "id": uuid.UUID("9de47cac-e326-4d64-a746-9c008211c8df"),
        "name": "Investigación Profunda",
        "color": "#a855f7",
        "system_prompt": "Workspace para análisis exhaustivos e investigación académica.",
    },
]

async def restore_workspaces():
    print(f"🚀 Restaurando workspaces para cuenta {ACCOUNT_ID}...")
    async with SessionLocal() as session:
        created_count = 0
        for ws_data in WORKSPACES:
            ws_id = ws_data["id"]
            res = await session.execute(select(Workspace).where(Workspace.id == ws_id))
            ws = res.scalars().first()
            if not ws:
                ws = Workspace(
                    id=ws_id,
                    account_id=ACCOUNT_ID,
                    name=ws_data["name"],
                    color=ws_data["color"],
                    system_prompt=ws_data["system_prompt"]
                )
                session.add(ws)
                created_count += 1
                print(f"  🏢 Workspace creado: {ws_data['name']} ({ws_id})")
            else:
                ws.name = ws_data["name"]
                ws.color = ws_data["color"]
                ws.system_prompt = ws_data["system_prompt"]
                ws.account_id = ACCOUNT_ID
                print(f"  🏢 Workspace actualizado: {ws_data['name']}")

            # Asegurar permisos de owner
            perm_res = await session.execute(
                select(WorkspacePermission).where(
                    WorkspacePermission.workspace_id == ws_id,
                    WorkspacePermission.account_id == ACCOUNT_ID
                )
            )
            perm = perm_res.scalars().first()
            if not perm:
                perm = WorkspacePermission(
                    id=uuid.uuid4(),
                    workspace_id=ws_id,
                    account_id=ACCOUNT_ID,
                    role="owner"
                )
                session.add(perm)
                print(f"    🔑 Permiso 'owner' otorgado")

        await session.commit()
        print(f"✅ {created_count} workspaces creados/restaurados exitosamente!")

        # Opcional: Vincular carpetas clave a sus workspaces correspondientes
        folder_ws_links = {
            "Documentos Técnicos CLF": uuid.UUID("4bfbbe51-843d-4f34-b291-84918a82e3d3"),
            "U1 POO": uuid.UUID("b1ff216d-ce2a-4b49-a524-90a5ec7f5f58"),
        }
        for f_name, target_ws_id in folder_ws_links.items():
            f_res = await session.execute(
                select(DocumentFolder).where(
                    DocumentFolder.account_id == ACCOUNT_ID,
                    DocumentFolder.name == f_name
                )
            )
            f_obj = f_res.scalars().first()
            if f_obj:
                f_obj.workspace_id = target_ws_id
                # Actualizar también los documentos dentro de esa carpeta
                docs_res = await session.execute(
                    select(Document).where(Document.folder_id == f_obj.id)
                )
                for d in docs_res.scalars().all():
                    d.workspace_id = target_ws_id
                print(f"  🔗 Carpeta '{f_name}' y sus documentos vinculados al workspace {target_ws_id}")

        await session.commit()
        print("✅ Vinculaciones de carpetas a workspaces completadas!")

if __name__ == "__main__":
    asyncio.run(restore_workspaces())
