"""
Herramienta de Revisión de Conversaciones por Rango de Días.

Permite al agente (y al heartbeat autónomo) analizar los hilos de conversación
de un usuario en un rango de días previos, generando un resumen estructurado
de temas, decisiones, compromisos y patrones detectados.

Modos de operación:
- global:    revisa todas las conversaciones (todos los workspaces + sin workspace).
- workspace: filtra solo las conversaciones del workspace especificado.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Type

from langchain_community.chat_message_histories import PostgresChatMessageHistory
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from sqlalchemy import select

from core.config import settings
from core.database import ChatThread, SessionLocal
from core.llm_manager import get_fast_llm, get_llm_for_user
from utils.db_session import DBSession

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schema de entrada
# ---------------------------------------------------------------------------

class ConversationReviewInput(BaseModel):
    days_back: int = Field(
        default=7,
        ge=1,
        le=365,
        description=(
            "Número de días hacia atrás a revisar (1-365). "
            "Por ejemplo, 7 revisa la última semana."
        ),
    )
    mode: str = Field(
        default="global",
        description=(
            "Modo de búsqueda: "
            "'global' para revisar todas las conversaciones incluyendo todos los workspaces; "
            "'workspace' para filtrar solo al workspace_id activo."
        ),
    )
    workspace_id: Optional[str] = Field(
        default=None,
        description=(
            "ID del workspace a filtrar cuando mode='workspace'. "
            "Si se omite y mode='workspace', se usará el workspace_id del contexto."
        ),
    )
    max_threads: int = Field(
        default=15,
        ge=1,
        le=50,
        description="Máximo de hilos a analizar (1-50). Por defecto 15.",
    )
    max_messages_per_thread: int = Field(
        default=30,
        ge=5,
        le=200,
        description="Máximo de mensajes a incluir por hilo. Por defecto 30.",
    )
    focus: Optional[str] = Field(
        default=None,
        description=(
            "Tema, proyecto o palabra clave sobre el cual focalizar la revisión. "
            "Si se proporciona, el análisis enfatizará menciones relacionadas."
        ),
    )


# ---------------------------------------------------------------------------
# Herramienta principal
# ---------------------------------------------------------------------------

class ConversationReviewTool(BaseTool):
    """
    Revisa las conversaciones del usuario en un rango de días previos.

    Útil para:
    - Hacer un repaso semanal/mensual de lo conversado.
    - Detectar temas recurrentes, decisiones tomadas y compromisos pendientes.
    - Obtener contexto histórico de un workspace específico.
    - Alimentar el heartbeat autónomo con contenido real de las conversaciones.
    """

    name: str = "conversation_review"
    description: str = (
        "Revisa y resume las conversaciones del usuario en un rango de días previos. "
        "Soporta revisión global (todas las conversaciones y workspaces) o filtrada por workspace. "
        "Devuelve temas clave, decisiones, compromisos detectados y patrones recurrentes. "
        "Ideal para reportes semanales, retrospectivas o para el heartbeat autónomo."
    )
    args_schema: Type[BaseModel] = ConversationReviewInput
    return_direct: bool = False

    # Inyectados por el SkillManager
    account_id: str = Field(..., description="ID de la cuenta del usuario.")
    workspace_id: Optional[str] = Field(
        default=None,
        description="ID del workspace activo (usado como fallback cuando mode='workspace').",
    )

    # ------------------------------------------------------------------
    # Punto de entrada asíncrono
    # ------------------------------------------------------------------

    async def _arun(
        self,
        days_back: int = 7,
        mode: str = "global",
        workspace_id: Optional[str] = None,
        max_threads: int = 15,
        max_messages_per_thread: int = 30,
        focus: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        logger.info(
            f"ConversationReviewTool: account={self.account_id} mode={mode} "
            f"days_back={days_back} workspace_id={workspace_id or self.workspace_id}"
        )

        # Resolver workspace_id efectivo
        effective_workspace_id: Optional[str] = None
        if mode == "workspace":
            effective_workspace_id = workspace_id or self.workspace_id

        # 1. Obtener hilos dentro del rango
        threads = await self._fetch_threads(
            days_back=days_back,
            workspace_id=effective_workspace_id,
            max_threads=max_threads,
        )

        if not threads:
            period_desc = f"los últimos {days_back} día(s)"
            scope_desc = (
                f"el workspace {effective_workspace_id}"
                if effective_workspace_id
                else "todas las conversaciones"
            )
            return (
                f"No se encontraron conversaciones en {period_desc} para {scope_desc}."
            )

        # 2. Cargar mensajes de cada hilo
        threads_content = await self._load_thread_messages(
            threads=threads,
            max_messages_per_thread=max_messages_per_thread,
        )

        if not threads_content:
            return "Se encontraron hilos pero no se pudieron recuperar mensajes."

        # 3. Generar resumen con LLM
        return await self._generate_review(
            threads_content=threads_content,
            days_back=days_back,
            mode=mode,
            focus=focus,
        )

    def _run(self, *args: Any, **kwargs: Any) -> str:
        import asyncio
        return asyncio.run(self._arun(*args, **kwargs))

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    async def _fetch_threads(
        self,
        days_back: int,
        workspace_id: Optional[str],
        max_threads: int,
    ) -> List[ChatThread]:
        """Recupera los hilos de la BD dentro del rango de fecha."""
        account_uuid = uuid.UUID(self.account_id)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

        async with DBSession(SessionLocal) as db:
            stmt = (
                select(ChatThread)
                .where(
                    ChatThread.account_id == account_uuid,
                    ChatThread.created_at >= cutoff,
                )
                .order_by(ChatThread.created_at.desc())
                .limit(max_threads)
            )

            if workspace_id:
                try:
                    ws_uuid = uuid.UUID(workspace_id)
                    stmt = stmt.where(ChatThread.workspace_id == ws_uuid)
                except ValueError:
                    logger.warning(
                        f"ConversationReviewTool: workspace_id inválido '{workspace_id}', ignorando filtro."
                    )

            result = await db.execute(stmt)
            threads = result.scalars().all()

        logger.info(f"ConversationReviewTool: {len(threads)} hilo(s) encontrado(s).")
        return list(threads)

    async def _load_thread_messages(
        self,
        threads: List[ChatThread],
        max_messages_per_thread: int,
    ) -> List[Dict[str, Any]]:
        """Carga mensajes de cada hilo usando PostgresChatMessageHistory."""
        if not settings.database_url:
            logger.error("ConversationReviewTool: DATABASE_URL no configurado.")
            return []

        # PostgresChatMessageHistory requiere URL síncrona (psycopg2)
        db_sync_url = settings.database_url.replace("+psycopg", "").replace("+asyncpg", "")

        threads_content: List[Dict[str, Any]] = []

        for thread in threads:
            try:
                history = PostgresChatMessageHistory(
                    connection_string=db_sync_url,
                    session_id=str(thread.id),
                    table_name="langchain_chat_history",
                )
                messages = await history.aget_messages()
                if not messages:
                    continue

                # Limitar y formatear
                trimmed = messages[-max_messages_per_thread:]
                conversation_lines: List[str] = []
                for msg in trimmed:
                    role = "Usuario" if msg.type == "human" else "KAI"
                    content = msg.content
                    if isinstance(content, list):
                        # Mensaje multimodal: extraer solo el texto
                        text_parts = [
                            p.get("text", "") for p in content
                            if isinstance(p, dict) and p.get("type") == "text"
                        ]
                        content = " ".join(text_parts)
                    if content:
                        conversation_lines.append(f"{role}: {str(content)[:800]}")

                if conversation_lines:
                    threads_content.append({
                        "thread_id": str(thread.id),
                        "title": thread.title or "Sin título",
                        "platform": thread.platform or "web",
                        "created_at": thread.created_at.isoformat() if thread.created_at else None,
                        "workspace_id": str(thread.workspace_id) if thread.workspace_id else None,
                        "messages": conversation_lines,
                        "message_count": len(conversation_lines),
                    })

            except Exception as e:
                logger.warning(
                    f"ConversationReviewTool: error cargando hilo {thread.id}: {e}"
                )
                continue

        logger.info(
            f"ConversationReviewTool: {len(threads_content)} hilo(s) con contenido cargados."
        )
        return threads_content

    async def _generate_review(
        self,
        threads_content: List[Dict[str, Any]],
        days_back: int,
        mode: str,
        focus: Optional[str],
    ) -> str:
        """Usa el LLM para generar un análisis estructurado de las conversaciones."""
        llm = await get_llm_for_user(self.account_id, purpose="fast")
        if not llm:
            llm = await get_fast_llm()
        if not llm:
            return self._format_without_llm(threads_content, days_back, mode)

        # Construir el bloque de conversaciones para el prompt
        conversation_blocks: List[str] = []
        for tc in threads_content:
            header = (
                f"--- Hilo: {tc['title']} "
                f"| {tc['platform']} "
                f"| {tc['created_at'] or 'fecha desconocida'} "
                f"| {tc['message_count']} mensajes ---"
            )
            body = "\n".join(tc["messages"][:20])  # hasta 20 líneas por hilo en el prompt
            conversation_blocks.append(f"{header}\n{body}")

        all_conversations = "\n\n".join(conversation_blocks)
        scope_label = (
            f"workspace {threads_content[0].get('workspace_id', 'desconocido')}"
            if mode == "workspace"
            else "todas las conversaciones (global)"
        )
        focus_instruction = (
            f"\nPrioriza menciones relacionadas con: **{focus}**."
            if focus
            else ""
        )

        prompt = f"""Eres KAI, un asistente de inteligencia aumentada. 
Analiza las siguientes conversaciones de los últimos {days_back} día(s) ({scope_label}).{focus_instruction}

Genera un informe estructurado en español con las siguientes secciones:

## 📋 Resumen Ejecutivo
(2-3 oraciones resumiendo lo más relevante del período)

## 🗣️ Temas Principales
(Lista de 3-7 temas recurrentes o más discutidos, con breve descripción)

## ✅ Decisiones y Compromisos
(Decisiones tomadas, tareas asignadas o compromisos mencionados)

## ⚠️ Pendientes y Seguimientos
(Puntos sin resolver, preguntas sin respuesta, temas que requieren acción)

## 🔁 Patrones Detectados
(Comportamientos repetitivos, preguntas frecuentes, áreas de interés constante)

## 💡 Observaciones Adicionales
(Insights no obvios, conexiones entre temas, oportunidades detectadas)

---
CONVERSACIONES A ANALIZAR ({len(threads_content)} hilos):

{all_conversations[:12000]}
"""

        try:
            # Desactivar streaming para análisis en batch
            if hasattr(llm, "model_copy"):
                llm_copy = llm.model_copy()
            elif hasattr(llm, "copy"):
                llm_copy = llm.copy()
            else:
                llm_copy = llm

            if hasattr(llm_copy, "streaming"):
                llm_copy.streaming = False

            response = await llm_copy.ainvoke(prompt)
            result_text = response.content if hasattr(response, "content") else str(response)
            return (
                f"## 🗓️ Revisión de Conversaciones — Últimos {days_back} día(s)\n"
                f"**Alcance:** {scope_label} | **Hilos analizados:** {len(threads_content)}\n\n"
                + result_text.strip()
            )
        except Exception as e:
            logger.error(f"ConversationReviewTool: error en LLM: {e}", exc_info=True)
            return self._format_without_llm(threads_content, days_back, mode)

    def _format_without_llm(
        self,
        threads_content: List[Dict[str, Any]],
        days_back: int,
        mode: str,
    ) -> str:
        """Fallback: lista simple de hilos sin análisis LLM."""
        lines = [
            f"## 🗓️ Conversaciones — Últimos {days_back} día(s) ({mode})",
            f"Se encontraron **{len(threads_content)}** hilo(s):\n",
        ]
        for tc in threads_content:
            lines.append(
                f"- **{tc['title']}** ({tc['platform']}, {tc['message_count']} mensajes, {tc['created_at'] or 'sin fecha'})"
            )
        return "\n".join(lines)
