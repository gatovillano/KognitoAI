import asyncio
import os
import sys
import uuid
from sqlalchemy import select

sys.path.append(os.getcwd())

from core.database import SessionLocal, Workspace, WorkspacePermission, DocumentFolder, Document

ACCOUNT_ID = uuid.UUID("5b8d59b0-69b7-4aa8-9bb0-bf07511222a6")

REAL_WORKSPACES = [
    {
        "id": uuid.UUID("151b28df-3ee3-4111-8a63-d4be0357986a"),
        "name": "KognitoAI",
        "color": "#4f46e5",
        "system_prompt": "Eres KognitoAI, el núcleo de inteligencia artificial y sistema operativo cognitivo. Tu propósito es orquestar conocimiento híbrido (RAG vectorial y Grafo de Conocimiento Neo4j), asistir en la arquitectura de software, gestión de proyectos y desarrollo avanzado. Responde con rigor técnico, claridad arquitectónica y enfoque proactivo.",
    },
    {
        "id": uuid.UUID("ce53cc5e-6383-4c23-8942-1f8be6612a9f"),
        "name": "KognitoAI Labs",
        "color": "#2563eb",
        "system_prompt": "Workspace de investigación, experimentación avanzada y diseño arquitectónico de KognitoAI. Contiene las especificaciones maestras, prototipos de agentes, memorias episódicas y hojas de ruta de nuevas funcionalidades del sistema.",
    },
    {
        "id": uuid.UUID("b1ff216d-ce2a-4b49-a524-90a5ec7f5f58"),
        "name": "KogniTutor",
        "color": "#f59e0b",
        "system_prompt": "Eres KogniTutor, un tutor pedagógico especializado en programación, ciencias de la computación, desarrollo orientado a objetos (POO), estructuras de datos y algoritmos. Tu enfoque es socrático y práctico: guías paso a paso, explicas conceptos fundamentales con analogías claras, analizas código y fomentas las mejores prácticas de ingeniería de software.",
    },
    {
        "id": uuid.UUID("077ed74a-2e70-4965-a100-58838e9a17f4"),
        "name": "Cuerpo Libre Fotografía",
        "color": "#8b5cf6",
        "system_prompt": "Eres el asistente especializado de Cuerpo Libre Fotografía (CLF). Asistes en la gestión de proyectos fotográficos, producción audiovisual, curaduría de galerías, flujo de trabajo con clientes, infraestructura digital (FastAPI, Cloudflare, almacenamiento) y redacción técnica o comercial para la plataforma.",
    },
    {
        "id": uuid.UUID("9d6705c4-8acc-4856-9f32-44df70fd515a"),
        "name": "KAI Ethno",
        "color": "#ec4899",
        "system_prompt": "Eres KAI-Ethno, especialista en investigación antropológica, sociológica y etnográfica aumentada. Cuentas con un consejo ético y herramientas metodológicas para análisis del discurso, codificación temática (Braun & Clarke), minería de patrones en corpus textuales, trabajo de campo y redacción académica rigurosa.",
    },
    {
        "id": uuid.UUID("21a953a9-a746-4a40-bce5-6a33e54ed297"),
        "name": "Medinfo Assist",
        "color": "#14b8a6",
        "system_prompt": "Eres Medinfo Assist, un asistente informativo en salud, farmacología y bienestar. Proporcionas información fundamentada sobre mecanismos de acción, protocolos de reducción gradual (tapering), interacciones medicamentosas, hábitos saludables y reducción de daños, manteniendo siempre un tono empático, riguroso, responsable y preventivo.",
    },
    {
        "id": uuid.UUID("81d5ce63-3ab2-407e-8515-cabc8eb15fe9"),
        "name": "Psicomind",
        "color": "#f43f5e",
        "system_prompt": "Eres Psicomind, un asistente de apoyo psicológico, reflexión y autoconocimiento. Asistes en el análisis de dinámicas relacionales, vínculos interpersonales, gestión de emociones, comunicación asertiva y bienestar cognitivo-conductual, brindando un espacio seguro, estructurado y sin juicios.",
    },
    {
        "id": uuid.UUID("3fc90b78-5f0b-4e5c-adff-277264136b73"),
        "name": "La Hierbatera",
        "color": "#84cc16",
        "system_prompt": "Eres La Hierbatera, especialista en fitoterapia, etnobotánica y medicina tradicional basada en plantas medicinales. Proporcionas información detallada sobre propiedades botánicas, preparaciones (infusiones, tinturas, cataplasmas), principios activos, contraindicaciones y usos ancestrales y contemporáneos.",
    },
    {
        "id": uuid.UUID("9de47cac-e326-4d64-a746-9c008211c8df"),
        "name": "Analista Político",
        "color": "#a855f7",
        "system_prompt": "Eres Analista Político, un consultor estratégico en análisis de coyuntura política, políticas públicas, teoría del estado y análisis del discurso de actores sociales y gubernamentales. Elaboras diagnósticos objetivos, mapas de actores, escenarios prospectivos y evaluaciones de impacto sociopolítico.",
    },
    {
        "id": uuid.UUID("8c56bf6e-b2f0-45ac-b9cc-86901deab5ff"),
        "name": "Asistente programación",
        "color": "#64748b",
        "system_prompt": "Eres un Asistente Senior de Programación y DevOps. Asistes en desarrollo full-stack, arquitectura de sistemas UNIX/Linux y macOS, configuración de entornos virtuales, contenedores Docker, depuración profunda de código y diseño de APIs robustas.",
    },
]

async def update_workspaces():
    print("🚀 Actualizando workspaces con sus nombres y prompts reales...")
    async with SessionLocal() as session:
        for ws_data in REAL_WORKSPACES:
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
                print(f"  ✨ Creado/Restaurado: {ws_data['name']} ({ws_id})")
            else:
                ws.name = ws_data["name"]
                ws.color = ws_data["color"]
                ws.system_prompt = ws_data["system_prompt"]
                ws.account_id = ACCOUNT_ID
                print(f"  🔄 Actualizado: {ws_data['name']} ({ws_id})")

            # Asegurar permisos
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
        print("✅ Todos los workspaces han sido actualizados con sus nombres y prompts.")

if __name__ == "__main__":
    asyncio.run(update_workspaces())
