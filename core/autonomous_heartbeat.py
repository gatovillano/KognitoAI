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
    Nota,
    ProactiveInsight,
    SessionLocal,
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
        'error_type": "unmapped"',
        "serviceunavailableerror",
        "maximum context length",
        "context_length_exceeded",
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
    relevant_memories_text = "\n".join(memory_lines) if memory_lines else "Sin memorias relevantes recientes."

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
        workspace_name = None
        if workspace_id:
            workspace = await db.get(Workspace, uuid.UUID(workspace_id))
            workspace_name = workspace.name if workspace else None

        notes_stmt = (
            select(Nota)
            .where(
                Nota.account_id == account_uuid,
                Nota.workspace_id == (uuid.UUID(workspace_id) if workspace_id else None)
            )
            .order_by(Nota.updated_at.desc())
            .limit(6)
        )
        analyses_stmt = (
            select(AnalysisTask)
            .where(
                AnalysisTask.account_id == account_uuid,
                AnalysisTask.status == "completed",
            )
            .order_by(AnalysisTask.created_at.desc())
            .limit(6)
        )
        events_stmt = (
            select(AgendaEvent)
            .where(
                AgendaEvent.account_id == account_uuid,
                AgendaEvent.workspace_id == (uuid.UUID(workspace_id) if workspace_id else None),
                AgendaEvent.is_active == True,
                AgendaEvent.event_datetime_utc >= now,
            )
            .order_by(AgendaEvent.event_datetime_utc.asc())
            .limit(6)
        )
        threads_stmt = (
            select(ChatThread)
            .where(
                ChatThread.account_id == account_uuid,
                ChatThread.workspace_id == (uuid.UUID(workspace_id) if workspace_id else None)
            )
            .order_by(ChatThread.created_at.desc())
            .limit(6)
        )
        prior_insights_stmt = (
            select(ProactiveInsight)
            .where(
                ProactiveInsight.account_id == account_uuid,
                ProactiveInsight.workspace_id == (uuid.UUID(workspace_id) if workspace_id else None),
                ProactiveInsight.created_at >= lookback_start,
            )
            .order_by(ProactiveInsight.created_at.desc())
            .limit(10)
        )

        notes = (await db.execute(notes_stmt)).scalars().all()
        analyses = (await db.execute(analyses_stmt)).scalars().all()
        events = (await db.execute(events_stmt)).scalars().all()
        threads = (await db.execute(threads_stmt)).scalars().all()
        
        # Manejar gracefully si las columnas nuevas no existen aún en la BD
        try:
            prior_insights = (await db.execute(prior_insights_stmt)).scalars().all()
        except Exception as e:
            logger.warning(f"No se pudieron recuperar insights previos (columnas pueden no existir): {e}")
            prior_insights = []

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
                "event_datetime_utc": event.event_datetime_utc.isoformat() if event.event_datetime_utc else None,
                "duration_minutes": event.duration_minutes,
            }
            for event in events
        ],
        "recent_threads": [
            {
                "id": str(thread.id),
                "title": thread.title,
                "platform": thread.platform,
                "created_at": thread.created_at.isoformat() if thread.created_at else None,
            }
            for thread in threads
        ],
        "recent_insights": [
            {
                "type": insight.type,
                "insight_message": insight.insight_message,
                "action_suggestion": insight.action_suggestion,
                "created_at": insight.created_at.isoformat() if insight.created_at else None,
            }
            for insight in prior_insights
        ],
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
            if normalized_key in known_keys:
                continue

            confidence_raw = insight.get("confidence_score", 0.65)
            try:
                confidence_score = max(0.0, min(1.0, float(confidence_raw)))
            except (TypeError, ValueError):
                confidence_score = 0.65

            related_items = insight.get("related_items")
            if not isinstance(related_items, list):
                related_items = []

            record = ProactiveInsight(
                account_id=account_uuid,
                workspace_id=uuid.UUID(workspace_id) if workspace_id else None,
                type=str(insight.get("type") or "insight")[:50],
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
    tools_description = "\n".join([
        f"- **{t.name}**: {(t.description or '').strip()[:200]}"
        for t in selected_tools
    ])

    tool_selection_note = (
        "Tienes acceso a TODAS las herramientas disponibles del sistema. Elige las que mejor sirvan a las instrucciones."
        if allowed_tools is None
        else "Tienes acceso a un conjunto preseleccionado de herramientas. Elige las que mejor sirvan a las instrucciones."
    )

    planning_prompt = f"""Eres KAI ejecutando tu heartbeat autónomo. {tool_selection_note}

**HERRAMIENTAS DISPONIBLES ({len(selected_tools)}):**
{tools_description}

**CONTEXTO ACTUAL DEL USUARIO:**
- Notas recientes: {len(context_payload.get('notes', []))} notas
- Análisis completados: {len(context_payload.get('analysis_tasks', []))} análisis
- Eventos próximos: {len(context_payload.get('upcoming_events', []))} eventos
- Conversaciones recientes: {len(context_payload.get('recent_threads', []))} hilos

**INSTRUCCIONES DEL HEARTBEAT:**
{heartbeat_instructions}

**TU TAREA:**
Analiza las instrucciones y decide qué herramientas ejecutar. Puedes hacer DOS tipos de llamadas:
1. **Consulta/búsqueda**: para obtener información y enriquecer el análisis
2. **Acción**: para publicar, crear o enviar algo (ej: postear una reflexión, crear una nota)

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
    # Si allowed_tools es None, el LLM elige libremente de todas las herramientas disponibles.
    # Si allowed_tools es una lista vacía [], se omite la fase de herramientas.
    tool_results: List[Dict[str, Any]] = []
    if allowed_tools != []:
        tool_results = await _run_heartbeat_tool_phase(
            account_id=account_id,
            workspace_id=workspace_id,
            allowed_tools=allowed_tools,  # None = todas las herramientas
            context_payload=context_payload,
            heartbeat_instructions=heartbeat_instructions,
            llm=llm,
            main_llm=main_llm,
        )

    prompt = f"""{f'''PERSONALIDAD BASE KAI (compartida con agent.py):
    {kai_personality_preamble}

    ---
    ''' if kai_personality_preamble else ''}KAI heartbeat: análisis cualitativo y creativo.

Objetivo:
- Detectar ideas valiosas, oportunidades de innovación y conexiones no obvias.
- Priorizar señales humanas y estratégicas por sobre chequeos técnicos.
- Solo reportar riesgos técnicos cuando tengan impacto claro en decisiones, plazos o valor.

Importante - Reconocimiento de espacios de trabajo (workspaces):
- Cada nota, análisis, evento, hilo y memoria tiene asociado un workspace_id.
- SOLO relacionar elementos que pertenezcan al MISMO workspace_id.
- Si observas información de diferentes workspaces, identificar claramente cuándo NO están relacionados.
- Cuando la información es de workspaces distintos, menciona explícitamente que pertenece a diferentes contextos.
- El workspace actual es: {workspace_id or 'no especificado'}.

Instrucciones personalizadas:
{heartbeat_instructions}

Prioriza este orden:
1) Oportunidades e innovación aplicable
2) Síntesis de patrones (temas repetidos, tensión, momentum)
3) Acciones concretas de alto impacto
4) Riesgos operativos relevantes (sin caer en auditoría de integridad)

Formato de salida (JSON válido):
{{
    "insights": [
        {{
            "type": "opportunity|innovation|synthesis|follow_up|deadline|alert|insight",
            "title": "Título breve y claro",
            "insight_message": "1-2 párrafos con lectura cualitativa: qué pasa, por qué importa y qué patrón revela.",
            "confidence_score": 0.75,
            "action_suggestion": "Siguiente paso concreto y realista",
            "innovation_potential": "Cómo esta idea puede abrir una mejora o experimento útil",
            "related_items": [
                {{"kind": "note|analysis|event|memory|thread", "reference": "id o título", "reason": "vínculo breve"}}
            ]
        }}
    ]
}}

Guardarraíles:
- Máximo {max_insights} insights
- No inventes hechos
- Evita duplicar insights recientes
- Si no hay hallazgos sólidos, devuelve {{"insights": []}}
- Tono: ejecutivo, claro, creativo y accionable
- Idioma: español (genera todos los insights en español)

Contexto:
{json.dumps(context_payload, ensure_ascii=False, indent=2)}
{f'''
Revisión de conversaciones recientes ({context_payload.get("window", {}).get("lookback_days", "N/A")} días):
{context_payload.get("conversation_review", "")}
''' if context_payload.get("conversation_review") else ''}
{f'''
Resultados de herramientas ejecutadas:
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

        normalized_insights.append({
            "type": raw_insight.get("type") or "insight",
            "title": raw_insight.get("title"),
            "insight_message": insight_message,
            "confidence_score": raw_insight.get("confidence_score", 0.65),
            "action_suggestion": raw_insight.get("action_suggestion") or "",
            "innovation_potential": raw_insight.get("innovation_potential") or "",
            "related_items": related_items,
        })

    created_insights = await _save_autonomous_heartbeat_insights(account_id, normalized_insights, workspace_id)

    if created_insights and notify:
        await send_personal_message(account_id, {
            "type": "proactive_insight_created",
            "source": "autonomous_heartbeat",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "insights": created_insights,
        })

    return (
        f"Heartbeat autónomo completado para {account_id}: "
        f"{len(created_insights)} insight(s) nuevos guardados"
    )