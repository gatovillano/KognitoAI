# tools/cognee_conceptual_processing_tool.py
"""
Herramienta para procesar documentos conceptualmente usando Cognee.

Esta herramienta permite procesar documentos de forma conceptual,
extrayendo citas importantes, relaciones temáticas y perfiles de ideas
usando la integración con Cognee. Crea un grafo de conocimiento detallado
para entender mejor el contenido semántico y las conexiones entre ideas.
"""
import logging
import asyncio
import os # Importar el módulo os
import json # Importar json para parsear el resultado limpiado
import uuid # Importar uuid para validar account_id
from typing import Dict, List, Any, Optional, Union # Importar Union

from pydantic import BaseModel, Field, model_validator, RootModel
from langchain_core.tools import BaseTool

# Importaciones específicas del proyecto
from core.config import settings
# Asegúrate de que estas importaciones son correctas según la estructura de tu proyecto
# Por ejemplo, si CogneeIntegration está en knowledge_graph.cognee_integration
from knowledge_graph.graph_database import GraphDB
from knowledge_graph.cognee_integration import CogneeIntegration
# Asumiendo que get_full_document_content está en core.memory_manager
from core.memory_manager import get_full_document_content

# Configuración de logging específica para esta herramienta
logger = logging.getLogger(__name__)
# Asegurarse de que el logger de esta herramienta tenga un FileHandler
# para logs específicos, si aún no lo tiene.
log_file_path = "logs/cognee_conceptual_processing.log"
log_dir = os.path.dirname(log_file_path)
if log_dir and not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Verificar si ya existe un FileHandler para evitar duplicados
if not any(isinstance(handler, logging.FileHandler) and handler.baseFilename == os.path.abspath(log_file_path) for handler in logger.handlers):
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

logger.setLevel(logging.DEBUG) # Asegurar que el nivel sea DEBUG para esta herramienta
logger.propagate = False # Evitar que los logs se propaguen a loggers superiores y se dupliquen

class DocumentsInput(BaseModel):
    documents: List[Dict[str, Any]] = Field(
        description="Lista de documentos a procesar. Cada documento debe tener 'file_name' y opcionalmente 'content'."
    )
    dataset_name: str = Field(
        "default",
        description="Nombre del dataset para el procesamiento (opcional, por defecto 'default')"
    )

class DocumentTitlesInput(BaseModel):
    document_titles: List[str] = Field(
        description="Lista de nombres de archivos de documentos a procesar (sin contenido explícito)."
    )
    dataset_name: str = Field(
        "default",
        description="Nombre del dataset para el procesamiento (opcional, por defecto 'default')"
    )

class CogneeConceptualProcessingSchema(RootModel[Union[DocumentsInput, DocumentTitlesInput]]):
    """
    Schema para la herramienta de procesamiento conceptual con Cognee.
    Define los parámetros de entrada que la herramienta espera, permitiendo
    ya sea una lista de 'documents' o una lista de 'document_titles'.
    """
    root: Union[DocumentsInput, DocumentTitlesInput]

    @model_validator(mode='before')
    def parse_input_string(cls, value):
        # Si Langchain envuelve la entrada en un diccionario con la clave 'root'
        if isinstance(value, dict) and 'root' in value:
            value = value['root'] # Desempaquetar el valor real

        if isinstance(value, str):
            try:
                # Intentar parsear la cadena como JSON
                parsed_value = json.loads(value)
                return parsed_value
            except json.JSONDecodeError:
                raise ValueError("La entrada es una cadena pero no es un JSON válido.")
        return value



class CogneeConceptualProcessingTool(BaseTool):
    """
    Herramienta para procesar documentos conceptualmente usando Cognee.

    Esta herramienta extrae citas, relaciones temáticas y perfiles de ideas
    de los documentos del usuario, creando un grafo de conocimiento conceptual.
    Proporciona una comprensión profunda de los conceptos e ideas en los documentos analizados.
    """
    name: str = "cognee_conceptual_processing"
    description: str = """
    Procesa documentos de forma conceptual, extrayendo citas importantes,
    relaciones temáticas y perfiles de ideas. Crea un grafo de conocimiento
    detallado para entender mejor el contenido semántico y las conexiones
    entre ideas de los documentos. Proporciona una comprensión profunda
    de los conceptos e ideas en los documentos analizados.

    Puedes proporcionar una lista de documentos usando 'documents' (lista de objetos con 'file_name' y opcionalmente 'content')
    o una lista de nombres de archivos usando 'document_titles' (lista de strings con los nombres de archivos).
    Si solo proporcionas el nombre del archivo, la herramienta intentará recuperar el contenido automáticamente usando el 'account_id'.

    Parámetros de entrada:
    - documents (lista de objetos, opcional): [{"file_name": "mi_archivo.txt", "content": "Texto opcional aquí..."}, ...]
    - document_titles (lista de strings, opcional): ["mi_archivo1.pdf", "mi_archivo2.docx"]
    - dataset_name (string, opcional): Nombre para agrupar el procesamiento (por defecto 'default').
    - account_id (string, **requerido**): El ID UUID de la cuenta del usuario. Este parámetro se inyecta automáticamente a la herramienta y NO debe ser proporcionado por el LLM en el `tool_input`.

   USO RECOMENDADO:
   Proporciona la lista de documentos usando 'document_titles' (solo nombres de archivo) o 'documents' (con 'file_name'). La herramienta intentará obtener el contenido si no está incluido.

   EJEMPLOS DE USO (la herramienta espera un diccionario como entrada, NO incluyas 'account_id' aquí):
   1. Procesar por nombres de archivo (recomendado si el contenido está en DB):
       {
           "document_titles": ["mi_archivo.txt", "otro_documento.pdf"]
       }
   2. Procesar proporcionando contenido (si el contenido no está en DB o ya lo tienes):
       {
           "documents": [
               {"file_name": "mi_archivo.txt", "content": "Texto completo aquí..."},
               {"file_name": "otro_documento.pdf", "content": "Contenido del PDF..."}
           ]
       }
   3. Combinando ambos:
        {
           "documents": [{"file_name": "con_contenido.txt", "content": "Texto..."}],
           "document_titles": ["solo_nombre.pdf"]
        }
    """
    args_schema: type[BaseModel] = CogneeConceptualProcessingSchema
    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")
    workspace_id: Optional[str] = Field(None, description="El ID del espacio de trabajo, inyectado automáticamente si está disponible.")
    telegram_id: Optional[str] = Field(None, description="El ID de Telegram del usuario, inyectado automáticamente si está disponible.")
    thread_id: Optional[str] = Field(None, description="El ID del hilo de conversación, inyectado automáticamente si está disponible.")
    cognee_integration: Optional[CogneeIntegration] = None
    graph_db: Optional[GraphDB] = None

    # @model_validator(mode='after')
    # def initialize_integration(self) -> 'CogneeConceptualProcessingTool':
    #     """
    #     Inicializa la integración con Cognee (y Neo4j) después de crear la instancia.
    #     Esto asegura que la conexión esté lista antes de usar la herramienta.
    #     """
    #     try:
    #         # Inicializar conexión Neo4j usando settings
    #         neo4j_uri = settings.neo4j_uri
    #         neo4j_user = settings.neo4j_user
    #         neo4j_password = settings.neo4j_password
    #
    #         if not neo4j_uri or not neo4j_user or not neo4j_password:
    #             logger.warning("⚠️ Configuración de Neo4j incompleta para CogneeConceptualProcessingTool. Asegúrate de que NEO4J_URI, NEO4J_USER y NEO4J_PASSWORD estén definidos.")
    #             self.cognee_integration = None
    #             self.graph_db = None # Asegurarse de que graph_db también sea None
    #             return self
    #
    #         # Crear instancia de GraphDB
    #         self.graph_db = GraphDB(neo4j_uri, neo4j_user, neo4j_password)
    #         self.graph_db.connect() # Intentar conectar
    #
    #         # Crear integración con Cognee
    #         self.cognee_integration = CogneeIntegration(self.graph_db)
    #         logger.info("✅ Integración con Cognee inicializada correctamente para CogneeConceptualProcessingTool")
    #     except Exception as e:
    #         logger.error(f"❌ Error inicializando la integración con Cognee para la herramienta: {e}", exc_info=True)
    #         self.cognee_integration = None
    #         self.graph_db = None
    #     return self

    async def _prepare_documents(self, account_id: str, document_info_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prepara los documentos para el procesamiento, reconstruyendo contenido si es necesario.

        Itera sobre la lista de diccionarios de información de documentos recibida,
        obtiene el contenido si no está presente y formatea la salida para Cognee.

        Args:
            account_id: ID de la cuenta del usuario.
            document_info_list: Lista de diccionarios, cada uno con 'file_name' (o 'title') y opcionalmente 'content'.

        Returns:
            Lista de documentos preparados con contenido completo y metadatos necesarios.
        """
        prepared_documents = []
        for doc_info in document_info_list:
            try:
                # Obtener el nombre del archivo, aceptando 'file_name' o 'title'
                file_name = doc_info.get("file_name") or doc_info.get("title")
                if not file_name or not isinstance(file_name, str):
                     logger.warning(f"⚠️ Información de documento inválida o incompleta (falta 'file_name' o 'title'): {doc_info}")
                     continue # Saltar este documento inválido

                content = doc_info.get("content")

                # Si el contenido ya está proporcionado, usarlo
                if content and isinstance(content, str) and len(content.strip()) > 0:
                    prepared_documents.append({
                        "file_name": file_name, # Usar file_name consistentemente
                        "content": content.strip(),
                        "metadata": {"account_id": account_id, "file_name": file_name}
                    })
                    logger.info(f"✅ Documento '{file_name}' preparado con contenido proporcionado.")
                    continue

                # Si no hay contenido, intentar reconstruir (asume que get_full_document_content es async)
                logger.info(f"🔄 Intentando reconstruir contenido para: {file_name}")
                full_content = await get_full_document_content(
                    account_id=account_id,
                    file_name=file_name
                )

                if full_content and isinstance(full_content, str) and len(full_content.strip()) > 0:
                    prepared_documents.append({
                        "file_name": file_name,
                        "content": full_content.strip(),
                        "metadata": {"account_id": account_id, "file_name": file_name}
                    })
                    logger.info(f"✅ Contenido reconstruido exitosamente para: {file_name}. Longitud: {len(full_content.strip())} chars.")
                else:
                    logger.warning(f"⚠️ No se pudo reconstruir contenido para: {file_name}. Documento omitido.")
            except Exception as e:
                logger.error(f"❌ Error preparando documento {file_name}: {e}", exc_info=True)
                # Continuar con el siguiente documento si hay un error en este

        return prepared_documents

    async def _process_documents_conceptually(self, account_id: str, documents: List[Dict[str, Any]], dataset_name: str) -> Dict[str, Any]:
        """
        Procesa los documentos conceptualmente usando Cognee.

        Llama a la integración de Cognee para realizar el procesamiento.
        Incluye lógica para intentar limpiar y parsear la respuesta JSON
        si el LLM devuelve una cadena malformada.

        Args:
            account_id: ID de la cuenta del usuario.
            documents: Lista de documentos preparados con contenido y metadatos.
            dataset_name: Nombre del dataset.

        Returns:
            Resultado del procesamiento conceptual (diccionario JSON) o un diccionario de error.
        """
        if not self.cognee_integration:
            logger.error("❌ _process_documents_conceptually llamado pero cognee_integration no está inicializado.")
            return {
                "error": "Integración con Cognee no disponible",
                "status": "error",
                "details": "La conexión con Neo4j o Cognee no pudo ser establecida durante la inicialización."
            }

        try:
            # Procesar documentos conceptualmente
            result = await self.cognee_integration.process_documents_conceptually(
                documents=documents,
                dataset_name=dataset_name
            )

            # Si el resultado es una cadena, intentar limpiar y parsear JSON
            if isinstance(result, str):
                logger.warning("⚠️ El LLM devolvió una cadena en lugar de JSON. Intentando limpiar y parsear...")
                # Usar la instancia de CogneeIntegration ya inicializada
                cleaned_json = self.cognee_integration._clean_malformed_json(result)

                if cleaned_json:
                    try:
                        parsed_result = json.loads(cleaned_json)
                        logger.info("✅ JSON limpiado y parseado correctamente.")
                        return parsed_result
                    except json.JSONDecodeError as parse_error:
                        logger.error(f"❌ Error parseando JSON incluso después de limpiar: {parse_error}. Contenido limpiado: '{cleaned_json}'", exc_info=True)
                        return {
                            "error": "No se pudo parsear la respuesta JSON, incluso después de limpiar",
                            "status": "error",
                            "details": str(parse_error)
                        }
                else:
                    logger.warning("⚠️ No se pudo limpiar la respuesta JSON para extraer JSON válido.")
                    return {
                        "error": "No se pudo limpiar ni parsear la respuesta JSON",
                        "status": "error",
                        "details": "La respuesta del LLM no contenía un JSON válido ni pudo ser limpiada."
                    }

            # Si el resultado ya es un diccionario (como se espera si no hay error de formato)
            if isinstance(result, dict):
                 logger.info("✅ Procesamiento conceptual completado. El LLM devolvió un diccionario.")
                 return result

            # Si el resultado no es ni string ni dict (inesperado)
            logger.error(f"❌ Resultado inesperado del procesamiento conceptual: {type(result).__name__}. Resultado: {result}")
            return {
                "error": "Resultado inesperado del procesamiento conceptual.",
                "status": "error",
                "details": f"El procesamiento devolvió un tipo inesperado: {type(result).__name__}"
            }


        except Exception as e:
            logger.error(f"❌ Error general en _process_documents_conceptually: {e}", exc_info=True)
            return {
                "error": str(e),
                "status": "error",
                "details": "Error durante el procesamiento conceptual de documentos."
            }

    def _run(self, **kwargs) -> Dict[str, Any]:
        """
        Ejecuta la herramienta de forma síncrona (utilizando asyncio.run para llamar a _arun).
        """
        try:
            return asyncio.run(self._arun(
                tool_input_json=kwargs.get("tool_input_json", json.dumps(kwargs)),
                **kwargs
            ))
        except Exception as e:
            logger.error(f"❌ Error en la ejecución síncrona de CogneeConceptualProcessingTool: {e}", exc_info=True)
            return {
                "error": str(e),
                "status": "error",
                "details": "Error durante la ejecución síncrona del procesamiento conceptual."
            }

    async def _arun(self, documents: Optional[List[Dict[str, Any]]] = None, document_titles: Optional[List[str]] = None, dataset_name: str = "default", run_manager: Optional[Any] = None, **kwargs) -> Dict[str, Any]:
        """
        Versión asíncrona de la ejecución de la herramienta.
        Maneja la obtención del account_id y la preparación de los documentos.
        """
        effective_account_id = self.account_id

        # La lógica para obtener account_id del run_manager ya no es necesaria aquí,
        # ya que se inyecta directamente en la instancia de la herramienta.
        # Si se necesita el workspace_id, se puede obtener del run_manager si no se pasa directamente.
        if not effective_account_id or not isinstance(effective_account_id, str):
            logger.error("❌ account_id es requerido pero no se pudo obtener del atributo de la herramienta.")
            return {
                "error": "Se requiere account_id",
                "status": "error",
                "details": "No se proporcionó un ID de cuenta válido a la instancia de la herramienta."
            }

        # Validar que effective_account_id sea un UUID válido
        try:
            uuid_obj = uuid.UUID(effective_account_id)
        except Exception:
            logger.error(f"❌ account_id inválido (no es un UUID válido): {effective_account_id}")
            return {
                "error": "account_id inválido (no UUID)",
                "status": "error",
                "details": f"El account_id proporcionado ('{effective_account_id}') no es un UUID válido."
            }

        # Verificar que se proporcionó al menos una lista de documentos o títulos
        if not documents and not document_titles:
            logger.error("❌ No se proporcionaron documentos ni títulos de documentos.")
            return {
                "error": "Se requieren documentos",
                "status": "error",
                "details": "Debes proporcionar una lista de documentos o títulos de documentos."
            }

        # Consolidar la información de los documentos
        document_info_list = []
        if documents:
            # Si 'documents' es una lista de diccionarios, usarla directamente
            if isinstance(documents, list):
                 document_info_list.extend(documents)
            else:
                 logger.warning(f"⚠️ El parámetro 'documents' no es una lista: {type(documents).__name__}")

        if document_titles:
            # Si 'document_titles' es una lista de strings (nombres de archivo)
            if isinstance(document_titles, list):
                for title in document_titles:
                    if isinstance(title, str):
                         document_info_list.append({"file_name": title}) # Mapear título a file_name
                    else:
                         logger.warning(f"⚠️ Elemento inválido en document_titles (no es string): {type(title).__name__}")
            else:
                 logger.warning(f"⚠️ El parámetro 'document_titles' no es una lista: {type(document_titles).__name__}")

        if not document_info_list:
             logger.error("❌ La lista final de información de documentos está vacía después de procesar la entrada.")
             return {
                "error": "No se proporcionó información de documento válida",
                "status": "error",
                "details": "La lista de documentos o títulos estaba vacía o contenía formatos incorrectos."
            }


        try:
            # Preparar documentos (obtener contenido si es necesario)
            prepared_documents = await self._prepare_documents(effective_account_id, document_info_list)

            if not prepared_documents:
                logger.error("❌ _prepare_documents no devolvió ningún documento preparado.")
                return {
                    "error": "No se pudieron preparar los documentos",
                    "status": "error",
                    "details": "No se pudo reconstruir el contenido de ningún documento válido proporcionado."
                }

            # Procesar documentos conceptualmente usando la integración de Cognee
            result = await self._process_documents_conceptually(effective_account_id, prepared_documents, dataset_name)

            # El resultado ya viene parseado (o con error dict) de _process_documents_conceptually
            return result

        except Exception as e:
            logger.error(f"❌ Error general en la ejecución asíncrona de CogneeConceptualProcessingTool: {e}", exc_info=True)
            return {
                "error": str(e),
                "status": "error",
                "details": "Error durante la ejecución del procesamiento conceptual."
            }
