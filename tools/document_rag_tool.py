# tools/document_rag_tool.py

"""
Herramienta de LangChain para procesar documentos y añadir su contenido a la base de conocimiento (RAG) de un usuario.

Esta herramienta permite al agente de IA tomar el texto extraído de un documento, junto con su nombre de archivo,
un tema especificado por el usuario y metadatos opcionales, para dividirlo, incrustarlo y almacenarlo en la base de datos
vectorial del usuario. Es útil cuando un usuario sube un documento y desea que se guarde para referencia futura.
"""

import logging
import os
from typing import Any, Dict, List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from core.memory_manager import process_document_for_rag
from core.citation_models import Source, ToolOutputWithSources, create_document_source

logger = logging.getLogger(__name__)


class DocumentRAGInput(BaseModel):
    """Input schema for the Document RAG processing tool."""
    extracted_text: str = Field(..., description="The complete text content extracted from the document.")
    file_name: str = Field(..., description="The original name of the document file.")
    topic: str = Field(..., description="The topic or category for this document, as specified by the user.")


    workspace_id: Optional[str] = Field(
        description="El ID del workspace (UUID en formato string) para asociar el documento a un workspace específico, si aplica.",
        json_schema_extra={"type": "string"}
    )
    
    # Use account_id as the universal identifier for the user account
    account_id: str = Field(..., description="The unique universal identifier (UUID) of the user's account. This MUST be provided by the LLM.")
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional metadata for the document, e.g., {'author': 'John Doe', 'title': 'My Document'}"
    )
        
    


class DocumentRAGTool(BaseTool):
    name: str = "process_document_for_rag"
    description: str = """
    Useful when the user provides a document and wants its content added to their knowledge base (RAG).
    This tool takes the extracted text, file name, a user-specified topic, and optional metadata.
    It will split, embed, and store the content in the user's vector database.
    Use this when the user uploads a document AND indicates it should be saved for future reference.
    The LLM must extract all relevant data and provide the user's 'account_id'.
    """
    args_schema: type[BaseModel] = DocumentRAGInput
    return_direct: bool = False
    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")

    async def _arun(
            self,
            extracted_text: str,
            file_name: str,
            topic: str,
            workspace_id: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None,
            **kwargs: Any
    ) -> ToolOutputWithSources:

        """
        Use the tool asynchronously. Processes the document text for RAG storage and returns source information.
        """
        logger.info(f"📊 DocumentRAGTool _arun started for file: {file_name}, topic: {topic}, metadata: {metadata}")

        if not self.account_id:
            logger.error("❌ DocumentRAGTool: account_id not found. Cannot process document.")
            return ToolOutputWithSources(context_for_llm="Error: User ID not available to process document. Cannot proceed.", sources=[])

        metadata_to_pass = metadata if metadata else {}
        code_extensions = {'.py', '.java', '.cpp', '.c', '.js', '.ts', '.html', '.css', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.sh', '.bash'}
        file_ext = os.path.splitext(file_name)[1].lower()
        is_code = file_ext in code_extensions
        if not is_code and extracted_text:
            code_keywords = ['function ', 'class ', 'def ', 'import ', 'from ', 'export ', 'const ', 'let ', 'var ', 'if (', 'for (', 'while (', 'return ']
            extracted_text_lower = extracted_text.lower()
            is_code = any(keyword in extracted_text_lower for keyword in code_keywords)

        processed_chunks_count = await process_document_for_rag(
            extracted_text=extracted_text,
            file_name=file_name,
            topic=topic,
            account_id=self.account_id,
            workspace_id=workspace_id,
            metadata=metadata_to_pass,
        )

        if processed_chunks_count > 0:
            message = f"Documento '{file_name}' procesado y añadido a la base de conocimiento con {processed_chunks_count} fragmentos."
            sources = [create_document_source(source_id=1, title=file_name, file_path=file_name, snippet="", metadata={"topic": topic, "file_name": file_name})]
            return ToolOutputWithSources(context_for_llm=message, sources=sources)
        else:
            return ToolOutputWithSources(context_for_llm=f"Error: No se pudo procesar el documento '{file_name}'.", sources=[])