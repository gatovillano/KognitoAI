# tools/document_rag_tool.py

"""
Herramienta de LangChain para procesar documentos y añadir su contenido a la base de conocimiento (RAG) de un usuario.

Esta herramienta permite al agente de IA tomar el texto extraído de un documento, junto con su nombre de archivo,
un tema especificado por el usuario y metadatos opcionales, para dividirlo, incrustarlo y almacenarlo en la base de datos
vectorial del usuario. Es útil cuando un usuario sube un documento y desea que se guarde para referencia futura.
"""

import logging
from typing import Any, Optional, Dict

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from core.memory_manager import process_document_for_rag

logger = logging.getLogger(__name__)

class DocumentRAGInput(BaseModel):
    """Input schema for the Document RAG processing tool."""
    extracted_text: str = Field(..., description="The complete text content extracted from the document.")
    file_name: str = Field(..., description="The original name of the document file.")
    topic: str = Field(..., description="The topic or category for this document, as specified by the user.")
    
    # Use account_id as the universal identifier for the user account
    account_id: str = Field(..., description="The unique universal identifier (UUID) of the user's account. This MUST be provided by the LLM.")
    
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional dictionary of additional document metadata for filtering. The LLM should extract these from the user's query or the document itself.",
        json_schema_extra={
            "type": "object",
            "properties": {
                "author": {"type": "string"},
                "title": {"type": "string"},
                "creation_date": {"type": "string"},
                "file_extension": {"type": "string"}
            },
            "additionalProperties": True
        }
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

    async def _arun(
        self, 
        extracted_text: str, 
        file_name: str, 
        topic: str, 
        account_id: str, 
        metadata: Optional[Dict[str, Any]] = None, 
        **kwargs: Any
    ) -> str:
        """
        Use the tool asynchronously. Processes the document text for RAG storage.
        """
        logger.info(f"📊 DocumentRAGTool _arun started for file: {file_name}, topic: {topic}, metadata: {metadata}")

        if not account_id:
            logger.error("❌ DocumentRAGTool: account_id not found. Cannot process document.")
            return "Error: User ID not available to process document. Cannot proceed."

        metadata_to_pass = metadata if metadata else {}

        logger.info(f"💾 Calling process_document_for_rag for user {account_id}, file '{file_name}', topic '{topic}', metadata: {metadata_to_pass}")
        
        try:
            chunks_count = await process_document_for_rag(
                account_id=account_id,
                file_name=file_name,
                extracted_text=extracted_text,
                topic=topic,
                metadata=metadata_to_pass
            )

            if chunks_count > 0:
                logger.info(f"✅ RAG processing successful for {file_name}. {chunks_count} chunks added.")
                return f"Document '{file_name}' processed and {chunks_count} chunks added to your knowledge base under the topic '{topic}'. You can now ask me questions about this document."
            else:
                logger.error(f"❌ RAG processing failed for {file_name}. No chunks added.")
                return f"Error processing document '{file_name}'. Could not add its content to your knowledge base. Please check the logs."
        except Exception as e:
            logger.error(f"❌ Error in DocumentRAGTool for user {account_id}: {e}", exc_info=True)
            return f"An error occurred while processing the document: {e}"

    def _run(self, **kwargs: Any) -> str:
        logger.error("❌ Synchronous _run method of DocumentRAGTool was called! This should not happen.")
        raise NotImplementedError("DocumentRAGTool does not support synchronous execution.")
