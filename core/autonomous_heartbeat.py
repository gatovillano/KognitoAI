import difflib
import json
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from core.config import settings
from core.database import (
    Account,
    AgendaEvent,
    AnalysisTask,
    ChatThread,
    Document,
    Nota,
    ProactiveInsight,
    SessionLocal,
    Task,
    Workspace,
)
from core.llm_manager import get_fallback_llm, get_llm_for_user
from core.memory_manager import get_relevant_memories, get_user_profile
from core.prompt_manager import PromptManager
from core.websocket_manager import send_personal_message
from utils.db_session import DBSession

logger = logging.getLogger(__name__)

AUTONOMOUS_HEARTBEAT_QUERY = (
    "riesgos oportunidades dependencias seguimientos pendientes bloqueos plazos "
    "decisiones prioridades coordinación"
)


def _extract_balanced_json(text: str, start_idx: int) -> Optional[str]:
    if start_idx >= len(text) or text[start_idx] != '{':
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i in range(start_idx, len(text)):
        char = text[i]

        if escape_next:
            escape_next = False
            continue

        if char == '\\':
            escape_next = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if not in_string:
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return text[start_idx:i + 1]

    return None


def _strip_json_code_fences(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()


def _extract_json_dict(raw_text: str) -> Optional[Dict[str, Any]]:
    cleaned = _strip_json_code_fences(raw_text)
    try:
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        first_curly = cleaned.find('{')
        if first_curly == -1:
            return None
        json_str = _extract_balanced_json(cleaned, first_curly)
        if not json_str:
            return None
        try:
            data = json.loads(json_str)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None


def _normalize_insight_key(text: str) -> str:
    normalized = re.sub(r'\s+', ' ', text or '').strip().lower()
    normalized = re.sub(r'[^\w\s]', '', normalized)
    return normalized


def _clone_llm_without_streaming(llm: Any) -> Any:
    llm_copy = llm

    if hasattr(llm, "model_copy"):
        try:
            llm_copy = llm.model_copy(deep=True)
        except TypeError:
            llm_copy = llm.model_copy()
    elif hasattr(llm, "copy"):
        try:
            llm_copy = llm.copy(deep=True)
        except TypeError:
            llm_copy = llm.copy()

    if hasattr(llm_copy, "streaming"):
        llm_copy.streaming = False

    extra_body = getattr(llm_copy, "extra_body", None)
    if isinstance(extra_body, dict):
        extra_body.setdefault("include_reasoning", False)

    return llm_copy


def _llm_signature(llm: Any) -> str:
    return "|".join(
        [
            type(llm).__name__,
            str(getattr(llm, "model_name", "") or getattr(llm, "model", "") or ""),
            str(getattr(llm, "provider", "") or getattr(llm, "custom_llm_provider", "") or ""),
            str(getattr(llm, "api_base", "") or getattr(llm, "base_url", "") or ""),
        ]
    )


def _is_retryable_heartbeat_llm_error(exc: Exception) -> bool:
    error_text = str(exc).lower()
    retry_markers = [
        "midstreamfallbackerror",
        "openrouterexception",
        "provider returned error",
        "error_type': 'unmapped'",
        '"error_type": "unmapped"',
        "serviceunavailableerror",
        "maximum context length",
        "context_length_exceeded",
        "expecting value",
        "internalservererror",
        "openaiexception",
    ]
    return any(marker in error_text for marker in retry_markers)


async def _invoke_autonomous_heartbeat_llm(
    prompt: str,
    primary_llm: Any,
    secondary_llm: Optional[Any] = None,
) -> Any:
    attempted_signatures = set()
    last_exc: Optional[Exception] = None

    for label, candidate in (("primary", primary_llm), ("secondary", secondary_llm)):
        if not candidate:
            continue

        signature = _llm_signature(candidate)
        if signature in attempted_signatures:
            continue
        attempted_signatures.add(signature)

        try:
            return await _clone_llm_without_streaming(candidate).ainvoke(prompt)
        except Exception as exc:
            last_exc = exc
            retryable = _is_retryable_heartbeat_llm_error(exc)
            logger.warning(
                "Heartbeat autónomo: fallo al invocar LLM %s | retryable=%s | error=%s",
                label,
                retryable,
                exc,
            )
            if not retryable:
                raise

    if last_exc and _is_retryable_heartbeat_llm_error(last_exc):
        provider_fallback_llm = get_fallback_llm()
        if provider_fallback_llm:
            fallback_signature = _llm_signature(provider_fallback_llm)
            if fallback_signature not in attempted_signatures:
                try:
                    logger.warning(
                        "Heartbeat autónomo: reintentando con proveedor fallback tras error OpenRouter/LiteLLM"
                    )
                    return await _clone_llm_without_streaming(provider_fallback_llm).ainvoke(prompt)
                except Exception as fallback_exc:
                    last_exc = fallback_exc
                    logger.error(
                        "Heartbeat autónomo: fallback de proveedor también falló | error=%s",
                        fallback_exc,
                    )

    if last_exc:
        raise last_exc

    raise ValueError("No hay LLM disponible para ejecutar el heartbeat autónomo")


async def _build_kai_heartbeat_personality_preamble(
    account_id: str,
    workspace_id: Optional[str],
    context_payload: Dict[str, Any],
) -> str:
    """
    Reutiliza la base de personalidad de KAI (mismo constructor central de agent.py)
    para que el heartbeat conserve tono/identidad sin heredar un prompt gigante.
    """
    try:
        user_profile = await get_user_profile(account_id)
    except Exception as exc:
        logger.warning("Heartbeat: no se pudo cargar user_profile para prompt base KAI: %s", exc)
        user_profile = None

    memory_items = context_payload.get("memory_snippets") or []
    memory_lines: List[str] = []
    for item in memory_items[:5]:
        if not isinstance(item, dict):
            continue
        snippet = (item.get("snippet") or "").strip()
        title = (item.get("title") or "").strip()
        if snippet:
            label = f"{title}: " if title else ""
            memory_lines.append(f"- {label}{snippet[:280]}")
    relevant_memories_text = "\\n".join(memory_lines) if memory_lines else "Sin memorias relevantes recientes."

    custom_prompt = None
    if user_profile is not None:
        # Compatibilidad con distintos formatos de user_profile.
        custom_prompt = getattr(user_profile, "system_prompt", None)
        if custom_prompt is None and isinstance(user_profile, dict):
            custom_prompt = user_profile.get("system_prompt")

    try:
        prompt_manager = PromptManager(settings={"default_system_prompt": settings.default_system_prompt})
        return prompt_manager.build_system_prompt(
            user_profile=user_profile,
            relevant_memories=relevant_memories_text,
            summary_string="",
            custom_prompt_from_profile=str(custom_prompt) if custom_prompt else None,
            workspace_prompt=None,
            tools=[],
            account_id=account_id,
            telegram_id=None,
            user_message="Heartbeat autónomo cualitativo",
            has_explicit_rag_context=False,
            explicit_document_names=None,
            context={"type": "heartbeat", "id": workspace_id} if workspace_id else None,
            compact_mode=True,
        )
    except Exception as exc:
        logger.warning("Heartbeat: no se pudo construir prompt base KAI desde PromptManager: %s", exc)
        return ""


async def _collect_autonomous_heartbeat_context(
    account_id: str,
    workspace_id: Optional[str] = None,
    lookback_days: Optional[int] = None,
) -> Dict[str, Any]:
    account_uuid = uuid.UUID(account_id)
    lookback_days = lookback_days or settings.autonomous_heartbeat_lookback_days
    now = datetime.now(timezone.utc)
    lookback_start = now - timedelta(days=lookback_days)

    async with DBSession(SessionLocal) as db:
        account = await db.get(Account, account_uuid)
        
        # Obtener mapa de workspaces para nombrar el origen de cada item
        workspaces_stmt = select(Workspace).where(Workspace.account_id == account_uuid)
        all_workspaces = (await db.execute(workspaces_stmt)).scalars().all()
        workspace_map = {str(w.id): w.name for w in all_workspaces}
        
        workspace_name = workspace_map.get(str(workspace_id)) if workspace_id else None

        notes_stmt = select(Nota).where(Nota.account_id == account_uuid)
        analyses_stmt = select(AnalysisTask).where(
            AnalysisTask.account_id == account_uuid,
            AnalysisTask.status == "completed",
        )
        events_stmt = select(AgendaEvent).where(
            AgendaEvent.account_id == account_uuid,
            AgendaEvent.is_active == True,
            AgendaEvent.event_datetime_utc >= now,
        )
        threads_stmt = select(ChatThread).where(ChatThread.account_id == account_uuid)
        tasks_stmt = select(Task).where(
            Task.account_id == account_uuid,
            Task.is_completed == False,
        )
        
        if workspace_id:
            ws_uuid = uuid.UUID(workspace_id)
            notes_stmt = notes_stmt.where(Nota.workspace_id == ws_uuid)
            events_stmt = events_stmt.where(AgendaEvent.workspace_id == ws_uuid)
            threads_stmt = threads_stmt.where(ChatThread.workspace_id == ws_uuid)
            tasks_stmt = tasks_stmt.where(Task.workspace_id == ws_uuid)
            # AnalysisTask puede o no tener workspace_id, así que no lo filtramos o lo hacemos seguro:
            if hasattr(AnalysisTask, "workspace_id"):
                analyses_stmt = analyses_stmt.where(AnalysisTask.workspace_id == ws_uuid)

        notes_stmt = notes_stmt.order_by(Nota.updated_at.desc()).limit(6)
        analyses_stmt = analyses_stmt.order_by(AnalysisTask.created_at.desc()).limit(6)
        events_stmt = events_stmt.order_by(AgendaEvent.event_datetime_utc.asc()).limit(20)
        threads_stmt = threads_stmt.order_by(ChatThread.created_at.desc()).limit(6)
        tasks_stmt = tasks_stmt.order_by(Task.due_date.asc().nulls_last(), Task.created_at.desc()).limit(15)
        
        prior_insights_stmt = select(ProactiveInsight).where(
            ProactiveInsight.account_id == account_uuid,
            ProactiveInsight.created_at >= lookback_start,
        )
        if workspace_id:
            prior_insights_stmt = prior_insights_stmt.where(ProactiveInsight.workspace_id == uuid.UUID(workspace_id))
            
        prior_insights_stmt = prior_insights_stmt.order_by(ProactiveInsight.created_at.desc()).limit(10)

        notes = (await db.execute(notes_stmt)).scalars().all()
        analyses = (await db.execute(analyses_stmt)).scalars().all()
        events = (await db.execute(events_stmt)).scalars().all()
        threads = (await db.execute(threads_stmt)).scalars().all()
        tasks = (await db.execute(tasks_stmt)).scalars().all()
        
        # Manejar gracefully si las columnas nuevas no existen aún en la BD
        try:
            prior_insights = (await db.execute(prior_insights_stmt)).scalars().all()
        except Exception as e:
            logger.warning(f"No se pudieron recuperar insights previos (columnas pueden no existir): {e}")
            prior_insights = []

        # Documentos existentes y creados/subidos en los últimos 3 días
        existing_docs = []
        recent_docs = []
        try:
            docs_stmt = select(Document).where(Document.account_id == account_uuid)
            if workspace_id:
                docs_stmt = docs_stmt.where(Document.workspace_id == uuid.UUID(workspace_id))
            docs_stmt = docs_stmt.order_by(Document.created_at.desc())
            all_docs = (await db.execute(docs_stmt)).scalars().all()
            
            three_days_ago = now - timedelta(days=3)
            for doc in all_docs:
                doc_data = {
                    "id": str(doc.id),
                    "filename": doc.filename,
                    "extension": doc.extension,
                    "workspace_name": workspace_map.get(str(doc.workspace_id), "Global") if getattr(doc, "workspace_id", None) else "Global",
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
                }
                existing_docs.append(doc_data)
                doc_created = doc.created_at
                if doc_created:
                    if doc_created.tzinfo is None:
                        doc_created = doc_created.replace(tzinfo=timezone.utc)
                    if doc_created >= three_days_ago:
                        recent_docs.append(doc_data)
        except Exception as doc_err:
            logger.warning(f"No se pudieron recuperar los documentos en el heartbeat: {doc_err}")

    memory_snippets: List[Dict[str, Any]] = []
    try:
        memory_output = await get_relevant_memories(
            account_id=account_id,
            query=AUTONOMOUS_HEARTBEAT_QUERY,
            workspace_id=workspace_id,
            content_types=["thread_summary", "user_memory_proactive_llm", "general_memory", "user_notes", "user_documents"],
            k=8,
            similarity_threshold=0.55,
        )
        if memory_output and getattr(memory_output, "sources", None):
            for source in memory_output.sources[:8]:
                source_dict = source.dict() if hasattr(source, "dict") else source.model_dump()
                memory_snippets.append({
                    "title": source_dict.get("title"),
                    "type": source_dict.get("type"),
                    "snippet": source_dict.get("snippet"),
                    "metadata": source_dict.get("metadata", {}),
                })
    except Exception as exc:
        logger.warning(f"No se pudieron recuperar memorias para heartbeat autónomo: {exc}")

    # --- Revisión de conversaciones recientes (contenido real de los hilos) ---
    conversation_review: Optional[str] = None
    try:
        from skills.analysis_and_insights_skill.scripts.conversation_review_tool import ConversationReviewTool
        review_tool = ConversationReviewTool(
            account_id=account_id,
            workspace_id=workspace_id,
        )
        mode = "workspace" if workspace_id else "global"
        conversation_review = await review_tool._arun(
            days_back=lookback_days,
            mode=mode,
            workspace_id=workspace_id,
            max_threads=10,
            max_messages_per_thread=20,
        )
        logger.info(f"Heartbeat: revisión de conversaciones completada ({len(conversation_review or '')} chars).")
    except Exception as exc:
        logger.warning(f"Heartbeat: no se pudo completar la revisión de conversaciones: {exc}")

    return {
        "account": {
            "id": account_id,
            "name": account.name if account else None,
            "timezone": account.timezone if account else "UTC",
            "language": account.language if account else "es",
        },
        "workspace": {
            "id": workspace_id,
            "name": workspace_name,
        },
        "notes": [
            {
                "id": note.id,
                "title": note.title,
                "category": note.category,
                "workspace_name": workspace_map.get(str(note.workspace_id), "Global") if getattr(note, "workspace_id", None) else "Global",
                "updated_at": note.updated_at.isoformat() if note.updated_at else None,
                "content_preview": (note.content or "")[:500],
            }
            for note in notes
        ],
        "analysis_tasks": [
            {
                "id": str(task.id),
                "file_name": task.file_name,
                "analysis_type": task.analysis_type,
                "workspace_name": workspace_map.get(str(task.workspace_id), "Global") if getattr(task, "workspace_id", None) else "Global",
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "result_excerpt": json.dumps(task.result_payload, ensure_ascii=False)[:800] if task.result_payload else None,
            }
            for task in analyses
        ],
        "upcoming_events": [
            {
                "id": event.id,
                "summary": event.summary,
                "description": event.description,
                "status": event.status,
                "workspace_name": workspace_map.get(str(event.workspace_id), "Global") if getattr(event, "workspace_id", None) else "Global",
                "event_datetime_utc": event.event_datetime_utc.isoformat() if event.event_datetime_utc else None,
                "duration_minutes": event.duration_minutes,
            }
            for event in events
        ],
        "pending_tasks": [
            {
                "id": str(task.id),
                "description": task.description,
                "status": task.status,
                "workspace_name": workspace_map.get(str(task.workspace_id), "Global") if getattr(task, "workspace_id", None) else "Global",
                "start_date": task.start_date.isoformat() if task.start_date else None,
                "end_date": task.end_date.isoformat() if task.end_date else None,
                "due_date": task.due_date.isoformat() if task.due_date else None,
            }
            for task in tasks
        ],
        "recent_threads": [
            {
                "id": str(thread.id),
                "title": thread.title,
                "platform": thread.platform,
                "workspace_name": workspace_map.get(str(thread.workspace_id), "Global") if getattr(thread, "workspace_id", None) else "Global",
                "created_at": thread.created_at.isoformat() if thread.created_at else None,
            }
            for thread in threads
        ],
        "recent_insights": [
            {
                "type": insight.type,
                "insight_message": insight.insight_message,
                "action_suggestion": insight.action_suggestion,
                "workspace_name": workspace_map.get(str(insight.workspace_id), "Global") if getattr(insight, "workspace_id", None) else "Global",
                "created_at": insight.created_at.isoformat() if insight.created_at else None,
            }
            for insight in prior_insights
        ],
        "recent_documents": recent_docs,
        "existing_documents": existing_docs,
        "memory_snippets": memory_snippets,
        "conversation_review": conversation_review,
        "window": {
            "lookback_days": lookback_days,
            "generated_at": now.isoformat(),
        },
    }


async def _save_autonomous_heartbeat_insights(
    account_id: str,
    insights: List[Dict[str, Any]],
    workspace_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    account_uuid = uuid.UUID(account_id)
    created_payloads: List[Dict[str, Any]] = []

    async with DBSession(SessionLocal) as db:
        recent_stmt = (
            select(ProactiveInsight)
            .where(
                ProactiveInsight.account_id == account_uuid,
                ProactiveInsight.workspace_id == (uuid.UUID(workspace_id) if workspace_id else None)
            )
            .order_by(ProactiveInsight.created_at.desc())
            .limit(30)
        )
        recent_insights = (await db.execute(recent_stmt)).scalars().all()
        known_keys = {_normalize_insight_key(item.insight_message) for item in recent_insights}

        for insight in insights:
            insight_message = (insight.get("insight_message") or insight.get("summary") or "").strip()
            if not insight_message:
                continue

            normalized_key = _normalize_insight_key(insight_message)
            
            # Contar repeticiones basadas en recent_insights
            similar_count = 1  # Incluye el actual que vamos a guardar
            matched_original_insight = None
            
            for item in recent_insights:
                item_normalized = _normalize_insight_key(item.insight_message)
                if item_normalized == normalized_key:
                    similar_count += 1
                    if not matched_original_insight:
                        matched_original_insight = item
                elif (item.title and insight.get("title") and 
                      difflib.SequenceMatcher(None, item.title.strip().lower(), insight.get("title").strip().lower()).ratio() > 0.82):
                    similar_count += 1
                    if not matched_original_insight:
                        matched_original_insight = item
                elif difflib.SequenceMatcher(None, item_normalized, normalized_key).ratio() > 0.85:
                    similar_count += 1
                    if not matched_original_insight:
                        matched_original_insight = item

            confidence_raw = insight.get("confidence_score", 0.65)
            try:
                confidence_score = max(0.0, min(1.0, float(confidence_raw)))
            except (TypeError, ValueError):
                confidence_score = 0.65

            related_items = insight.get("related_items")
            if not isinstance(related_items, list):
                related_items = []

            # Si es repetido, guardamos metadatos de la repetición
            if similar_count > 1:
                logger.info(f"Insight repetido detectado (frecuencia actual: {similar_count}): '{insight.get('title')}'")
                related_items.append({
                    "kind": "repetition_tracker",
                    "is_repeated": True,
                    "repetition_count": similar_count,
                    "parent_insight_id": str(matched_original_insight.id) if (matched_original_insight and getattr(matched_original_insight, 'id', None)) else None
                })
            # Procesar acciones sugeridas (suggested_actions) para almacenarlas como sugerencias en los metadatos
            suggested_actions = insight.get("suggested_actions")
            if isinstance(suggested_actions, list):
                for sa in suggested_actions:
                    if isinstance(sa, dict):
                        related_items.append({
                            "kind": sa.get("kind") or "suggested_action",
                            "title": sa.get("title"),
                            "description": sa.get("description"),
                            "start_date": sa.get("start_date"),
                            "end_date": sa.get("end_date"),
                            "duration_minutes": sa.get("duration_minutes"),
                            "workspace_name": sa.get("workspace_name", "Global"),
                        })

            # Forzar type='insight' para máxima compatibilidad frontend/backend
            record = ProactiveInsight(
                account_id=account_uuid,
                workspace_id=uuid.UUID(workspace_id) if workspace_id else None,
                type="insight",
                title=(insight.get("title") or "").strip() or None,
                insight_message=insight_message,
                confidence_score=confidence_score,
                action_suggestion=(insight.get("action_suggestion") or "").strip() or None,
                innovation_potential=(insight.get("innovation_potential") or "").strip() or None,
                related_items=related_items,
            )
            db.add(record)
            known_keys.add(normalized_key)

            created_payloads.append({
                "type": record.type,
                "title": record.title,
                "insight_message": record.insight_message,
                "confidence_score": record.confidence_score,
                "action_suggestion": record.action_suggestion,
                "innovation_potential": record.innovation_potential,
                "related_items": record.related_items,
            })

        if created_payloads:
            await db.commit()

    return created_payloads


async def _run_heartbeat_tool_phase(
    account_id: str,
    workspace_id: Optional[str],
    allowed_tools: Optional[List[str]],
    context_payload: Dict[str, Any],
    heartbeat_instructions: str,
    llm: Any,
    main_llm: Any,
    max_iterations: int = 3,
) -> List[Dict[str, Any]]:
    """
    Fase de ejecución de herramientas del heartbeat.
    El LLM decide qué herramientas llamar basándose en el contexto,
    las ejecuta (máx max_iterations rondas) y devuelve los resultados acumulados.
    Si allowed_tools es None, el LLM puede elegir de todas las herramientas disponibles.
    """
    from core.tools import get_all_langchain_tools

    try:
        all_tools = await get_all_langchain_tools(
            account_id=account_id,
            workspace_id=workspace_id,
            query=heartbeat_instructions,
        )
    except Exception as e:
        logger.warning(f"Heartbeat: no se pudieron cargar herramientas: {e}")
        return []

    # Si allowed_tools es None, el LLM puede elegir de todas las herramientas disponibles
    tool_map = {t.name: t for t in all_tools}
    if allowed_tools is not None:
        selected_tools = [tool_map[name] for name in allowed_tools if name in tool_map]
        if not selected_tools:
            logger.warning(f"Heartbeat: ninguna de las herramientas configuradas existe: {allowed_tools}")
            return []
    else:
        selected_tools = list(all_tools)

    if not selected_tools:
        logger.warning("Heartbeat: no hay herramientas disponibles para el usuario")
        return []

    # Construir descripción de herramientas para el planning prompt
    tools_description_lines = []
    for t in selected_tools:
        desc = (t.description or '').strip()[:200]
        args_desc = ""
        try:
            if t.args:
                args_list = []
                for arg_name, arg_info in t.args.items():
                    arg_type = arg_info.get("type", "any")
                    arg_desc_text = arg_info.get("description", "")
                    args_list.append(f"    * `{arg_name}` ({arg_type}): {arg_desc_text}")
                if args_list:
                    args_desc = "\n  Parámetros:\n" + "\n".join(args_list)
        except Exception:
            pass
        tools_description_lines.append(f"- **{t.name}**: {desc}{args_desc}")
    tools_description = "\n".join(tools_description_lines)

    tool_selection_note = (
        "Tienes acceso a TODAS las herramientas disponibles del sistema. Elige las que mejor sirvan a las instrucciones."
        if allowed_tools is None
        else "Tienes acceso a un conjunto preseleccionado de herramientas. Elige las que mejor sirvan a las instrucciones."
    )

    recent_docs_list = context_payload.get('recent_documents', [])
    existing_docs_list = context_payload.get('existing_documents', [])
    
    recent_docs_str = "\n".join([f"  - {d['filename']} (Creado/Subido: {d['created_at']})" for d in recent_docs_list]) if recent_docs_list else "  - Ningún documento creado/subido recientemente."
    existing_docs_str = "\n".join([f"  - {d['filename']} (workspace: {d['workspace_name']})" for d in existing_docs_list]) if existing_docs_list else "  - Ningún documento existente."

    planning_prompt = f"""Eres KAI ejecutando tu heartbeat autónomo. {tool_selection_note}

**HERRAMIENTAS DISPONIBLES ({len(selected_tools)}):**
{tools_description}

**CONTEXTO ACTUAL DEL USUARIO:**
- Notas recientes: {len(context_payload.get('notes', []))} notas
- Tareas pendientes: {len(context_payload.get('pending_tasks', []))} tareas
- Análisis completados: {len(context_payload.get('analysis_tasks', []))} análisis
- Eventos próximos: {len(context_payload.get('upcoming_events', []))} eventos
- Conversaciones recientes: {len(context_payload.get('recent_threads', []))} hilos
- Documentos creados/subidos en los últimos 3 días:
{recent_docs_str}
- Lista de documentos existentes:
{existing_docs_str}

**INSTRUCCIONES DEL HEARTBEAT:**
{heartbeat_instructions}

**TU TAREA:**
Analiza las instrucciones y decide qué herramientas ejecutar. Puedes hacer DOS tipos de llamadas:
1. **Consulta/búsqueda**: para obtener información y enriquecer el análisis
2. **Acción**: para publicar, crear o enviar algo (ej: postear una reflexión, crear una nota)

### REGLA CRÍTICA OBLIGATORIA PARA LEER DOCUMENTOS (`get_document_content_tool`):
Si consideras que alguno de los documentos creados o existentes recientemente es relevante para tu análisis, para relacionar conceptos o para las instrucciones del heartbeat, DEBES leer su contenido completo llamando a `get_document_content_tool` pasándole el `file_name` correspondiente.

### REGLA CRÍTICA OBLIGATORIA PARA GUARDAR NOTAS (`add_note`):
Si decides crear o guardar una nota utilizando la herramienta `add_note`, debes establecer OBLIGATORIAMENTE el parámetro `send_as_agent_message` en `true`. Esto garantiza que el contenido se guarde como un mensaje enviado al usuario en su Bandeja de entrada. Nunca dejes este parámetro en `false` o ausente.

Si las instrucciones piden una acción (como "postea una reflexión en Moltbook"), DEBES incluirla como tool_call generando el contenido apropiado en los args basándote en el contexto disponible.

Responde SOLO con JSON:
{{
  "tool_calls": [
    {{
      "tool": "nombre_exacto_de_la_herramienta",
      "args": {{"argumento": "valor_o_contenido_generado"}},
      "reason": "Por qué ejecutar esta herramienta / qué acción realiza",
      "type": "query"
    }}
  ]
}}

Si no hay herramientas relevantes para las instrucciones, responde: {{"tool_calls": []}}
Máximo {max_iterations} tool calls. Para acciones con contenido generado, crea contenido genuinamente útil basado en el contexto."""

    tool_results: List[Dict[str, Any]] = []
    executed_count = 0

    try:
        plan_response = await _clone_llm_without_streaming(llm).ainvoke(planning_prompt)
        plan_text = plan_response.content if hasattr(plan_response, "content") else str(plan_response)
        plan = _extract_json_dict(plan_text) or {"tool_calls": []}
        tool_calls = plan.get("tool_calls", [])
        if not isinstance(tool_calls, list):
            tool_calls = []
    except Exception as e:
        logger.warning(f"Heartbeat: error en fase de planning de herramientas: {e}")
        return []

    for tc in tool_calls[:max_iterations]:
        if not isinstance(tc, dict):
            continue
        tool_name = tc.get("tool")
        tool_args = tc.get("args", {})
        reason = tc.get("reason", "")

        if not tool_name or tool_name not in tool_map:
            continue

        tool = tool_map[tool_name]
        try:
            call_type = tc.get("type", "query")
            logger.info(f"Heartbeat tool-call [{call_type}]: {tool_name} | args={str(tool_args)[:200]} | reason={reason}")
            if isinstance(tool_args, dict):
                result = await tool.arun(tool_input=tool_args)
            else:
                result = await tool.arun(tool_input=str(tool_args))

            tool_results.append({
                "tool": tool_name,
                "reason": reason,
                "result": str(result)[:3000],  # Limitar tamaño para no desbordar el contexto
            })
            executed_count += 1
        except Exception as e:
            logger.warning(f"Heartbeat: error ejecutando herramienta {tool_name}: {e}")
            tool_results.append({
                "tool": tool_name,
                "reason": reason,
                "result": f"[Error al ejecutar: {str(e)[:200]}]",
            })

    logger.info(f"Heartbeat tool phase: {executed_count}/{len(tool_calls)} herramientas ejecutadas")
    return tool_results


async def _check_and_escalate_expired_tasks(account_id: str, db: Any) -> None:
    """
    Busca todas las tareas no completadas creadas por el Tablero de Resolución
    que hayan expirado (más de 48 horas / end_date pasado) y las escala
    a decisión explícita actualizando su estado a 'Escalada'.
    """
    now = datetime.now(timezone.utc)
    stmt = select(Task).where(
        Task.account_id == uuid.UUID(account_id),
        Task.is_completed == False,
        Task.end_date < now,
        Task.status != "Escalada",
        Task.status != "Cancelada",
        Task.status != "Postergada",
        Task.description.like("[Tablero de Resolución]%")
    )
    result = await db.execute(stmt)
    expired_tasks = result.scalars().all()

    escalations_count = 0
    for task in expired_tasks:
        task.status = "Escalada"
        task.updated_at = now
        escalations_count += 1
        logger.info(f"Heartbeat: tarea ID {task.id} marcada como Escalada (venció su plazo de 48h).")

    if escalations_count > 0:
        await db.commit()
        logger.info(f"Heartbeat autónomo: escaladas {escalations_count} tareas expiradas.")


async def _log_to_heartbeat_thread(thread_id: uuid.UUID, content: str):
    """Persiste un mensaje AI en el hilo de heartbeat usando inserción SQL directa async."""
    try:
        import json as _json
        from sqlalchemy import text as _text
        from core.database import SessionLocal
        from utils.db_session import DBSession

        now_utc = datetime.now(timezone.utc).isoformat()
        # El formato que langchain_chat_history espera: {"type": "ai", "data": {...}}
        message_payload = _json.dumps({
            "type": "ai",
            "data": {
                "content": content,
                "additional_kwargs": {"created_at": now_utc},
                "type": "ai",
                "name": None,
                "id": None,
                "example": False,
            }
        })

        async with DBSession(SessionLocal) as session:
            from sqlalchemy.dialects.postgresql import JSONB
            from sqlalchemy import type_coerce
            await session.execute(
                _text(
                    "INSERT INTO langchain_chat_history (session_id, message) "
                    "VALUES (:session_id, cast(:message as jsonb))"
                ),
                {
                    "session_id": str(thread_id),
                    "message": message_payload,
                },
            )
            await session.commit()
    except Exception as e:
        logger.warning(f"Error logging to heartbeat thread {thread_id}: {e}")


async def run_autonomous_agent_heartbeat(
    account_id: str,
    workspace_id: Optional[str] = None,
    heartbeat_instructions: Optional[str] = None,
    max_insights: Optional[int] = None,
    lookback_days: Optional[int] = None,
    notify: bool = True,
    allowed_tools: Optional[List[str]] = None,
) -> str:
    if not settings.get_proactive_insights_enabled or not settings.autonomous_heartbeat_enabled:
        return "Heartbeat autónomo deshabilitado por configuración"

    # --- Crear un hilo nuevo para este heartbeat al inicio para poder registrar logs en él ---
    thread_id = uuid.uuid4()
    thread_created = False
    try:
        async with DBSession(SessionLocal) as db:
            thread = ChatThread(
                id=thread_id,
                account_id=uuid.UUID(account_id),
                workspace_id=uuid.UUID(workspace_id) if workspace_id else None,
                title=(f"Heartbeat autónomo - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S')}"),
                platform="system",
                hidden_from_sidebar=True,
            )
            db.add(thread)
            await db.commit()
            thread_created = True
    except Exception as exc:
        logger.warning(f"Heartbeat: no se pudo crear hilo oculto para el heartbeat: {exc}")

    if thread_created:
        await _log_to_heartbeat_thread(thread_id, "⚙️ **Iniciando ciclo autónomo de heartbeat.**\nSe buscarán tareas expiradas, se ejecutarán herramientas y se analizará el contexto del usuario para buscar nuevos insights.")

    # --- Ejecutar escalación de tareas expiradas del Tablero de Resolución ---
    escalations_logged = "No se detectaron tareas expiradas."
    try:
        async with DBSession(SessionLocal) as db:
            now = datetime.now(timezone.utc)
            stmt = select(Task).where(
                Task.account_id == uuid.UUID(account_id),
                Task.is_completed == False,
                Task.end_date < now,
                Task.status != "Escalada",
                Task.status != "Cancelada",
                Task.status != "Postergada",
                Task.description.like("[Tablero de Resolución]%")
            )
            result = await db.execute(stmt)
            expired_tasks = result.scalars().all()

            escalations_count = 0
            for task in expired_tasks:
                task.status = "Escalada"
                task.updated_at = now
                escalations_count += 1
                logger.info(f"Heartbeat: tarea ID {task.id} marcada como Escalada (venció su plazo de 48h).")

            if escalations_count > 0:
                await db.commit()
                escalations_logged = f"Se detectaron y escalaron **{escalations_count}** tareas que superaron el plazo de 48 horas."
                logger.info(f"Heartbeat autónomo: escaladas {escalations_count} tareas expiradas.")
    except Exception as esc_err:
        logger.warning(f"Error al verificar escalación de tareas: {esc_err}")
        escalations_logged = f"Error al verificar escalación de tareas: {esc_err}"

    if thread_created:
        await _log_to_heartbeat_thread(thread_id, f"📋 **[Fase 1: Tareas del Tablero de Resolución]**\n{escalations_logged}")

    max_insights = max_insights or settings.autonomous_heartbeat_max_insights
    heartbeat_instructions = heartbeat_instructions or settings.autonomous_heartbeat_instructions
    fast_llm = await get_llm_for_user(account_id, purpose="fast")
    main_llm = await get_llm_for_user(account_id, purpose="main")
    llm = fast_llm or main_llm
    if not llm:
        raise ValueError(f"No hay LLM disponible para heartbeat autónomo de la cuenta {account_id}")

    context_payload = await _collect_autonomous_heartbeat_context(
        account_id=account_id,
        workspace_id=workspace_id,
        lookback_days=lookback_days,
    )
    kai_personality_preamble = await _build_kai_heartbeat_personality_preamble(
        account_id=account_id,
        workspace_id=workspace_id,
        context_payload=context_payload,
    )

    # --- PHASE 1: Tool Execution ---
    tool_results: List[Dict[str, Any]] = []
    if allowed_tools != []:
        if thread_created:
            await _log_to_heartbeat_thread(thread_id, "🔧 **[Fase 2: Ejecución de Herramientas]**\nIniciando planificación y ejecución de herramientas...")
        tool_results = await _run_heartbeat_tool_phase(
            account_id=account_id,
            workspace_id=workspace_id,
            allowed_tools=allowed_tools,  # None = todas las herramientas
            context_payload=context_payload,
            heartbeat_instructions=heartbeat_instructions,
            llm=llm,
            main_llm=main_llm,
        )
        if thread_created:
            if tool_results:
                tools_summary = "\n".join([
                    f"- **{tr['tool']}** (Motivo: *{tr['reason']}*):\n  ```\n  {tr['result'][:500]}...\n  ```"
                    for tr in tool_results
                ])
                await _log_to_heartbeat_thread(thread_id, f"🔧 **[Fase 2: Ejecución de Herramientas]**\nSe ejecutaron **{len(tool_results)}** herramienta(s):\n{tools_summary}")
            else:
                await _log_to_heartbeat_thread(thread_id, "🔧 **[Fase 2: Ejecución de Herramientas]**\nNo se requirió la ejecución de ninguna herramienta.")

    if thread_created:
        await _log_to_heartbeat_thread(thread_id, "🧠 **[Fase 3: Análisis Cualitativo de Contexto]**\nIniciando el análisis cognitivo para detectar brechas de conocimiento y patrones...")

    prompt = f"""{f'''PERSONALIDAD BASE KAI (compartida con agent.py):
    {kai_personality_preamble}

    ---
    ''' if kai_personality_preamble else ''}🧠 **KAI AUTONOMOUS HEARTBEAT - COGNITIVE PROCESSOR SYSTEM PROMPT** 🧠

Eres KAI, el exocerebro digital de Inteligencia Aumentada del usuario. Te encuentras en tu ciclo de **Heartbeat Autónomo**, un proceso de pensamiento reflexivo en segundo plano donde tu rol principal es actuar como un procesador cognitivo profundo, conectando cabos susueltos, identificando brechas de conocimiento y encontrando oportunidades estratégicas o de innovación para el usuario.

### 1. OBJETIVOS COGNITIVOS DEL HEARTBEAT
Tu análisis no debe ser una simple lista de tareas o resúmenes directos de lo que ha pasado. Debes generar **insights cuantitativos y cualitativos de alto valor**. Busca:
- **Conexiones Inter-contextuales:** Relaciones no obvias entre notas recientes, tareas de análisis, eventos y conversaciones.
- **Detección de Brechas de Conocimiento:** Identificar temas o ideas de los que el usuario habla o investiga pero de los que no tiene notas guardadas o estructuradas.
- **Oportunidades de Innovación:** Detectar ideas emergentes en las conversaciones o notas que puedan transformarse en experimentos prácticos, herramientas o mejoras de flujo.
- **Tensiones y Bloqueos:** Detectar riesgos reales (bloqueos operativos, plazos vencidos, falta de seguimiento en acuerdos) priorizando siempre el impacto humano y estratégico sobre los simples fallos técnicos.

### 2. PROTOCOLO DE AISLAMIENTO DE CONTEXTOS (WORKSPACES)
- El contexto actual es: **workspace_id={workspace_id or 'global'}**.
- **Si workspace_id NO es global (es un UUID específico):** Toda la información suministrada pertenece estrictamente a este espacio de trabajo. No asumas ni inventes conexiones con otros espacios de trabajo. Tus insights deben enfocarse únicamente en el valor dentro de este workspace.
- **Si el contexto es global (workspace_id = global):** Los elementos del contexto pueden provenir de diferentes workspaces. Debes ser extremadamente cuidadoso: relaciona elementos solo si pertenecen al mismo contexto, o si cruzan workspaces, adviértelo de forma explícita ("Este elemento de Workspace A se relaciona con este de Workspace B").

### 3. METODOLOGÍA DE ANÁLISIS DE INFORMACIÓN (INPUTS)
Analiza minuciosamente los siguientes bloques en el payload de contexto:
1. **Notas Recientes (`notes`):** Representan el conocimiento estructurado y reflexiones del usuario.
2. **Tareas de Análisis (`analysis_tasks`):** Muestran datos procesados y reportes detallados que el usuario ha solicitado (fíjate en los resúmenes y resultados).
3. **Eventos de Agenda (`upcoming_events`):** Representan el tiempo del usuario, hitos clave y compromisos.
4. **Tareas Pendientes (`pending_tasks`):** Tareas activas/pendientes actuales del usuario, con sus respectivas fechas de inicio, finalización o vencimiento si están definidas.
5. **Conversaciones Recientes (`recent_threads` y `conversation_review`):** La voz viva del usuario. Aquí radican sus preocupaciones, intenciones inmediatas, frustraciones y focos actuales.
6. **Documentos Recientes (`recent_documents`):** Documentos subidos o creados en los últimos 3 días.
7. **Documentos Existentes (`existing_documents`):** Lista completa de documentos guardados por el usuario.
8. **Resultados de Herramientas (`tool_results`):** Resultados de búsquedas o acciones que ejecutaste en la fase previa de este heartbeat (como la lectura del contenido de algún documento relevante). Úsalos como datos duros para enriquecer tus insights.

### 4. INSTRUCCIONES PERSONALIZADAS DE ESTA CUENTA
Aplica con máxima prioridad estas directrices definidas por el usuario:
{heartbeat_instructions}

### 5. JERARQUÍA DE VALOR (PRIORIZACIÓN DE INSIGHTS)
Al redactar tus insights, prioriza en este orden:
1. **Oportunidades e Innovación:** Ideas que añaden valor estratégico o sugieren experimentos útiles (`opportunity`, `innovation`).
2. **Síntesis y Patrones:** Agrupación de temas repetidos o tensiones a lo largo de los días (`synthesis`).
3. **Seguimientos de Alto Impacto:** Hilos o compromisos de reuniones que quedaron en el aire (`follow_up`, `deadline`).
4. **Alertas y Riesgos Estratégicos:** Bloqueos críticos o plazos de entrega en peligro (`alert`).

### 6. GUARDARRAÍLES Y EVITACIÓN DE RUIDO
- **Cero obviedades:** No generes insights como "Tienes una reunión mañana" o "Escribiste una nota sobre X". Cada insight debe aportar una lectura cualitativa ("por qué importa esto ahora" o "qué patrón revela").
- **Evita duplicados:** Compara tus hallazgos con los `recent_insights` provistos. Si un insight ya fue reportado recientemente con el mismo enfoque, no lo repitas a menos que haya evolucionado significativamente o se haya convertido en un problema crítico.
- **Cantidad máxima:** Genera un máximo de {max_insights} insights (solo los de mayor calidad y relevancia).
- **Cita y Vínculo Preciso (`related_items`):** Cada elemento relacionado debe mapear a objetos reales en el contexto. Especifica su tipo (`kind`) y su identificador o título exacto (`reference`), explicando brevemente la razón de su vínculo.
- **Prohibición de Creación Directa y Sugerencia de Acciones (OBLIGATORIO):** NO crees directamente objetos en la base de datos de tareas ni eventos en la agenda. Tu objetivo es mantener la agenda del usuario limpia y libre de ruido. Si a partir de tu análisis detectas compromisos, tareas pendientes o reuniones a programar, DEBES proponerlas únicamente como sugerencias dentro del campo `suggested_actions` en cada insight (o en `action_suggestion`).
- **Salida:** Si no hay hallazgos con suficiente solidez, devuelve una lista vacía `{{"insights": []}}`. No inventes datos ni asumas hechos.
- **Idioma y Tono:** Redacta exclusivamente en **español**, con un tono profesional, ejecutivo, claro y accionable.

### 7. FORMATO DE SALIDA (ESQUEMA JSON ESTRICTO)
Tu respuesta debe ser un objeto JSON válido y estructurado exactamente así. No envíes bloques de código Markdown alrededor del JSON, responde únicamente con el texto del JSON. Asegúrate de escapar correctamente las comillas dobles y los caracteres especiales.

{{
  "insights": [
    {{
      "type": "opportunity|innovation|synthesis|follow_up|deadline|alert|insight",
      "title": "Título descriptivo, corto y potente (máx 10 palabras)",
      "insight_message": "Explicación profunda de 1 a 2 párrafos. Explica qué pasa, por qué es relevante estratégicamente y qué patrón cognitivo revela.",
      "confidence_score": 0.85,
      "action_suggestion": "Propuesta de acción concreta, realista y accionable para resolver o aprovechar este insight.",
      "innovation_potential": "Descripción de cómo este insight abre una puerta a la innovación, un nuevo experimento o una mejora del flujo de trabajo.",
      "related_items": [
        {{
          "kind": "note|analysis|event|memory|thread|document",
          "reference": "ID_DE_REFERENCIA_O_TITULO_EXACTO",
          "reason": "Vínculo explicativo muy breve de por qué se asocia este elemento."
        }}
      ],
      "suggested_actions": [
        {{
          "kind": "suggested_task|suggested_event",
          "title": "Título sugerido para la tarea o evento",
          "description": "Detalles adicionales",
          "start_date": "YYYY-MM-DDTHH:MM:SSZ",
          "end_date": "YYYY-MM-DDTHH:MM:SSZ",
          "duration_minutes": 60,
          "workspace_name": "Nombre exacto del workspace o 'Global'"
        }}
      ]
    }}
  ]
}}

### 8. DATOS DE CONTEXTO ACTUAL
{json.dumps(context_payload, ensure_ascii=False, indent=2)}

{f'''
### 9. REVISIÓN DE CONVERSACIONES RECIENTES (Últimos {context_payload.get("window", {}).get("lookback_days", "N/A")} días)
{context_payload.get("conversation_review", "")}
''' if context_payload.get("conversation_review") else ''}

{f'''
### 10. RESULTADOS DE HERRAMIENTAS EJECUTADAS EN LA FASE 2
{json.dumps(tool_results, ensure_ascii=False, indent=2)}
''' if tool_results else ''}
"""

    response = await _invoke_autonomous_heartbeat_llm(
        prompt=prompt,
        primary_llm=llm,
        secondary_llm=main_llm if llm is not main_llm else None,
    )
    response_text = response.content if hasattr(response, "content") else str(response)
    parsed = _extract_json_dict(str(response_text)) or {"insights": []}
    
    # --- PROCESAMIENTO DE INSIGHTS ---
    raw_insights = parsed.get("insights") if isinstance(parsed, dict) else []
    if not isinstance(raw_insights, list):
        raw_insights = []

    normalized_insights: List[Dict[str, Any]] = []
    for raw_insight in raw_insights[:max_insights]:
        if not isinstance(raw_insight, dict):
            continue
        insight_message = (raw_insight.get("insight_message") or raw_insight.get("summary") or "").strip()
        if not insight_message:
            continue

        related_items = raw_insight.get("related_items")
        if not isinstance(related_items, list):
            related_items = []

        suggested_actions = raw_insight.get("suggested_actions")
        if not isinstance(suggested_actions, list):
            suggested_actions = []

        normalized_insights.append({
            "type": raw_insight.get("type") or "insight",
            "title": raw_insight.get("title"),
            "insight_message": insight_message,
            "confidence_score": raw_insight.get("confidence_score", 0.65),
            "action_suggestion": raw_insight.get("action_suggestion") or "",
            "innovation_potential": raw_insight.get("innovation_potential") or "",
            "related_items": related_items,
            "suggested_actions": suggested_actions,
        })

    created_insights = await _save_autonomous_heartbeat_insights(account_id, normalized_insights, workspace_id)

    if created_insights:
        titles = [i.get('title') or i.get('insight_message', '')[:60] for i in created_insights]
        logger.info(
            f"Heartbeat autónomo: {len(created_insights)} insight(s) guardados: "
            + " | ".join(titles)
        )

    if created_insights and notify:
        try:
            await send_personal_message(account_id, {
                "type": "proactive_insight_created",
                "source": "autonomous_heartbeat",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "insights": created_insights,
            })
        except Exception as ws_err:
            logger.warning(f"Error al enviar notificación de insights proactivos vía WebSocket: {ws_err}")

    if thread_created:
        if created_insights:
            insights_summary = "\n".join([
                f"- **{i.get('title') or 'Sin título'}** ({i.get('type')}):\n  {i.get('insight_message')}\n  *Sugerencia:* {i.get('action_suggestion')}"
                for i in created_insights
            ])
            await _log_to_heartbeat_thread(
                thread_id,
                f"🧠 **[Fase 3: Análisis Cualitativo de Contexto]**\nAnálisis completado. Se generaron y guardaron **{len(created_insights)}** insight(s) nuevos:\n\n{insights_summary}"
            )
        else:
            await _log_to_heartbeat_thread(
                thread_id,
                "🧠 **[Fase 3: Análisis Cualitativo de Contexto]**\nAnálisis completado. No se detectaron patrones ni oportunidades lo suficientemente sólidos para reportar o todos eran duplicados de insights recientes."
            )

    return (
        f"Heartbeat autónomo completado para {account_id}: "
        f"{len(created_insights)} insight(s) nuevos guardados"
    )