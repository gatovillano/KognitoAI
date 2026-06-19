# tools/deep_research_tool.py

import logging
import os
import asyncio
from typing import Type, Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage
from core.agents.deep_researcher import compile_deep_researcher_graph
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import litellm
from litellm.exceptions import RateLimitError, ServiceUnavailableError
import httpx

from core.citation_models import ToolOutputWithSources, Source, SourceType
from core.database import SessionLocal, AnalysisTask
from utils.db_session import DBSession
from core.websocket_manager import manager as websocket_manager
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class DeepResearchInput(BaseModel):
    """Input for the Deep Research tool."""
    query: str = Field(description="The research query to be investigated in-depth.")

class DeepResearchTool(BaseTool):
    """
    A tool to perform in-depth research on a given query using a specialized agent.
    It compiles a detailed report by planning, executing research, and synthesizing findings.
    """
    name: str = "deep_research"
    description: str = (
        "Conduct deep research on complex topics. Provide a research query and get a comprehensive report. "
        "Required parameter: query (string) - the research topic to investigate."
    )
    args_schema: Type[BaseModel] = DeepResearchInput
    account_id: str
    workspace_id: Optional[str] = None
    telegram_id: Optional[str] = None
    progress_callback: Optional[Any] = Field(default=None, exclude=True)

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5),
        retry=(retry_if_exception_type(RateLimitError) |
               retry_if_exception_type(ServiceUnavailableError) |
               retry_if_exception_type(httpx.HTTPStatusError)),
        reraise=True
    )
    async def _run(self, query: str) -> Dict[str, Any]:
        """Use the tool."""
        logger.info(f"Executing Deep Research tool for query: '{query}' for account: {self.account_id}")
        
        try:
            logger.info("Compiling deep researcher graph...")
            graph = compile_deep_researcher_graph()
            logger.info("Deep researcher graph compiled successfully.")
            
            config = {"configurable": {"account_id": self.account_id}}
            
            # --- PROGRESS CALLBACK INTEGRATION ---
            if hasattr(self, 'progress_callback') and self.progress_callback:
                config["configurable"]["progress_callback"] = self.progress_callback
                logger.info("Progress callback injected into Deep Research graph configuration.")

            inputs = {
                "messages": [HumanMessage(content=query)],
                "account_id": self.account_id,
                "sources": [],  # Inicializar explícitamente para que override_reducer funcione correctamente
            }

            logger.info("Invoking Deep Research graph with inputs: %s", inputs)
            
            # Envolver la invocación en un bloque para capturar si se cancela
            try:
                final_state = await graph.ainvoke(inputs, config=config)
            except asyncio.CancelledError:
                logger.error("!!! [DeepResearchTool] EL PROCESO FUE CANCELADO DURANTE LA INVOCACIÓN DEL GRAFO !!!")
                raise
            except Exception as e:
                logger.error(f"!!! [DeepResearchTool] EXCEPCIÓN DURANTE LA INVOCACIÓN DEL GRAFO: {str(e)} !!!", exc_info=True)
                raise
                
            logger.info(f"Deep Research graph invocation completed. Final state keys: {final_state.keys()}")
            logger.debug("Full final state received: %s", final_state)
            
            if final_state and "final_report" in final_state:
                if final_state["final_report"] == "CLARIFICATION":
                    clarification_content = final_state["messages"][-1].content if final_state.get("messages") else None
                    if not clarification_content:
                        clarification_content = "El proceso de investigación profunda requiere clarificación adicional por parte del usuario, pero no se ha proporcionado un mensaje específico."
                    logger.info("Deep research requires clarification. Returning message: %s", clarification_content)
                    # Devolver en el formato esperado por el agente, pero sin fuentes
                    return ToolOutputWithSources(context_for_llm=str(clarification_content), sources=[]).model_dump()
                
                report = final_state["final_report"]
                raw_sources = final_state.get("sources", [])
                
                # No es necesario desempaquetar fuentes, el backend ya envía la lista directamente
                
                logger.info(f"Deep research completed.")
                logger.info(f"Found {len(raw_sources)} raw sources in state.")

                # Crear la lista de objetos Source
                sources_list: List[Source] = []
                if isinstance(raw_sources, list):
                    for i, raw_source in enumerate(raw_sources, start=1):
                        if isinstance(raw_source, dict):
                            # Intentamos obtener snippet de 'snippet' primero, luego 'content'
                            snippet_text = raw_source.get("snippet") or raw_source.get("content") or "No hay contenido disponible."
                            
                            # Leer el tipo real de la fuente, con fallback a WEB
                            raw_type = raw_source.get("type", "web")
                            try:
                                source_type = SourceType(raw_type) if raw_type else SourceType.WEB
                            except ValueError:
                                source_type = SourceType.WEB
                            
                            source_obj = Source(
                                id=i,
                                title=raw_source.get("title", "Fuente Desconocida"),
                                url=raw_source.get("url", ""),
                                snippet=str(snippet_text),
                                type=source_type
                            )
                            sources_list.append(source_obj)
                            logger.debug(f"✅ Fuente procesada: {source_obj.title} (type={source_type})")
                        else:
                            logger.warning(f"Elemento de fuente inesperado no es un diccionario: {raw_source}")
                else:
                    logger.warning(f"⚠️ raw_sources no es una lista después del desempaquetado: {type(raw_sources)}")


                # Crear el objeto de salida con fuentes, esquema y recomendaciones
                tool_output = ToolOutputWithSources(
                    context_for_llm=str(report) if report else "La investigación se completó pero el informe generado está vacío.",
                    sources=sources_list,
                    visual_schema=final_state.get("visual_schema"),
                    recommendations=final_state.get("recommendations", [])
                )
                
                # Devolver el diccionario serializado
                
                # --- SAVE TO DATABASE ---
                try:
                    async with DBSession(SessionLocal) as db_session:
                        # Construct a title
                        title = f"Investigación Profunda: {query[:50]}..."
                        
                        # Prepare result payload similar to api/analysis.py
                        # Deserializar formato de "override" para fuentes
                        final_sources = raw_sources
                        if isinstance(final_sources, dict) and final_sources.get("type") == "override":
                            final_sources = final_sources.get("value", [])
                        
                        result_payload = {
                            "final_report": report,
                            # Usar los objetos Source ya normalizados (con type='web') en lugar de los dicts crudos del grafo
                            "sources": [s.model_dump() for s in sources_list],
                            "recommendations": final_state.get("recommendations", []),
                            "visual_schema": final_state.get("visual_schema"),
                            "tool_used": "deep_research_tool.py",
                            "analysis_metadata": {
                                "tool_used": "deep_research_tool.py",
                                "analysis_type": "gap_development",
                                "query": query,
                                "workspace_id": self.workspace_id,
                                "created_at": datetime.now().isoformat()
                            }
                        }

                        new_task = AnalysisTask(
                            account_id=uuid.UUID(self.account_id),
                            file_name=title,
                            analysis_type="gap_development",
                            status="completed",
                            result_payload=result_payload
                        )
                        db_session.add(new_task)
                        await db_session.commit()
                        logger.info(f"Deep Research saved to DB with ID: {new_task.id}")
                        
                except Exception as e:
                    logger.error(f"Error saving Deep Research to DB: {e}", exc_info=True)
                    # We don't fail the tool execution just because DB save failed

                return tool_output.model_dump()
            else:
                error_message = "Error: The deep research process finished, but no final report was generated or the final state was unexpected."
                logger.error(error_message + " Final state: %s", final_state)
                return ToolOutputWithSources(context_for_llm=error_message, sources=[]).model_dump()

        except RateLimitError as e:
            logger.warning(f"Rate limit exceeded for DeepResearchTool. Retrying... Details: {str(e)}")
            raise
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning(f"HTTP 429 (Too Many Requests) encountered. Retrying... Details: {str(e)}")
                raise
            else:
                error_message = f"Error: An HTTP error occurred while trying to run the deep research. Details: {str(e)}"
                logger.error(f"An HTTP error occurred in DeepResearchTool: {e}. Response: {e.response.text if e.response else 'N/A'}", exc_info=True)
                return ToolOutputWithSources(context_for_llm=error_message, sources=[]).model_dump()
        except Exception as e:
            error_message = f"Error: An unexpected error occurred while trying to run the deep research. Details: {str(e)}"
            logger.error(f"An unexpected error occurred in DeepResearchTool: {e}", exc_info=True)
            return ToolOutputWithSources(context_for_llm=error_message, sources=[]).model_dump()

    async def _arun(self, query: str) -> Dict[str, Any]:
        """Use the tool asynchronously in background."""
        logger.info(f"Executing Async Deep Research tool for query: '{query}' for account: {self.account_id}")
        run_id = str(uuid.uuid4())
        
        async def _background_research():
            try:
                # Notify start via websocket
                await websocket_manager.send_personal_message({
                    "type": "tool_start",
                    "tool_name": "deep_research",
                    "taskId": run_id,
                    "message": f"Iniciando investigación profunda en segundo plano para: '{query}'"
                }, self.account_id)
                        
                graph = compile_deep_researcher_graph()
                config = {"configurable": {"account_id": self.account_id}}
                if hasattr(self, 'progress_callback') and self.progress_callback:
                    config["configurable"]["progress_callback"] = self.progress_callback
                
                inputs = {
                    "messages": [HumanMessage(content=query)],
                    "account_id": self.account_id,
                    "sources": [],
                }
                
                final_state = await graph.ainvoke(inputs, config=config)
                
                # Check for completion
                if final_state and "final_report" in final_state:
                    report = final_state["final_report"]
                    raw_sources = final_state.get("sources", [])
                    final_sources = raw_sources
                    if isinstance(final_sources, dict) and final_sources.get("type") == "override":
                        final_sources = final_sources.get("value", [])
                    
                    sources_list = []
                    if isinstance(final_sources, list):
                        for i, raw_source in enumerate(final_sources, start=1):
                            if isinstance(raw_source, dict):
                                source_type = SourceType.WEB
                                sources_list.append({
                                    "id": i,
                                    "title": raw_source.get("title", "Fuente Desconocida"),
                                    "url": raw_source.get("url", ""),
                                    "snippet": str(raw_source.get("snippet") or raw_source.get("content") or ""),
                                    "type": source_type.value
                                })

                    try:
                        async with DBSession(SessionLocal) as db_session:
                            title = f"Investigación Profunda: {query[:50]}..."
                            result_payload = {
                                "final_report": report,
                                "sources": sources_list,
                                "recommendations": final_state.get("recommendations", []),
                                "visual_schema": final_state.get("visual_schema"),
                                "tool_used": "deep_research_tool.py"
                            }
                            new_task = AnalysisTask(
                                account_id=uuid.UUID(self.account_id),
                                file_name=title,
                                analysis_type="gap_development",
                                status="completed",
                                result_payload=result_payload
                            )
                            db_session.add(new_task)
                            await db_session.commit()
                    except Exception as e:
                        logger.error(f"Error saving Deep Research to DB: {e}")

                    # Notify completion
                    msg = {
                        "type": "tool_end",
                        "tool_name": "deep_research",
                        "status": "completed",
                        "taskId": run_id,
                        "message": "Investigación profunda completada. Por favor, pide al agente que analice los resultados.",
                        "background_completion": True
                    }
                    await websocket_manager.send_personal_message(msg, self.account_id)

            except Exception as e:
                logger.error(f"Background deep research error: {e}", exc_info=True)
                msg = {
                    "type": "tool_error",
                    "tool_name": "deep_research",
                    "status": "failed",
                    "taskId": run_id,
                    "error": str(e),
                    "background_completion": True
                }
                await websocket_manager.send_personal_message(msg, self.account_id)
                        
        # Lanza el task sin bloquear
        asyncio.create_task(_background_research())
        
        # Devuelve inmediatamente al agente principal
        inmediate_response = (
            f"He iniciado la investigación profunda en segundo plano con ID de tarea: {run_id}. "
            f"Dile al usuario que estás investigando el tema '{query}' y que le notificarás cuando esté listo. "
            f"PUEDES SEGUIR RESPONDIENDO OTRAS PREGUNTAS MIENTRAS TANTO."
        )
        return ToolOutputWithSources(context_for_llm=inmediate_response, sources=[]).model_dump()