 Informe Detallado: Gestión del Contexto RAG en Open WebUI

  1. Introducción

  La Generación Aumentada por Recuperación (RAG) es una técnica crucial en sistemas de IA conversacionales que permite a los Large Language Models (LLM) acceder y utilizar información externa para generar
  respuestas más precisas, relevantes y actualizadas. En el proyecto Open WebUI, la gestión del contexto RAG es fundamental para enriquecer las interacciones del chat, permitiendo que el LLM responda
  preguntas basadas no solo en su conocimiento pre-entrenado, sino también en documentos específicos proporcionados por el usuario o en bases de conocimiento preexistentes.

  2. Arquitectura General de RAG

  La arquitectura RAG en Open WebUI se compone de varios módulos interconectados que trabajan en conjunto para:
   * Ingesta de Documentos: Procesar y preparar datos de diversas fuentes.
   * Almacenamiento Vectorial: Guardar representaciones numéricas (embeddings) de los documentos para una búsqueda eficiente.
   * Recuperación: Buscar y seleccionar los fragmentos de información más relevantes para una consulta dada.
   * Preparación del Contexto: Formatear la información recuperada y fusionarla con la consulta del usuario para el LLM.

  Los componentes clave identificados son:
   * `open_webui.retrieval.loaders.main.py`: Maneja la carga de documentos de diferentes tipos.
   * `open_webui.retrieval.vector.main.py`: Define la interfaz para la interacción con bases de datos vectoriales.
   * `open_webui.routers.retrieval.py`: Expone las APIs para el procesamiento de documentos y la configuración de RAG.
   * `open_webui.utils.middleware.py`: Actúa como un "middleware" en el flujo del chat, donde se orquesta la recuperación de RAG y la preparación del contexto.
   * `open_webui.retrieval.utils.py`: Contiene las funciones centrales para la consulta y recuperación de documentos de la base de datos vectorial.
   * `open_webui.utils.chat.py`: Gestiona la lógica de finalización del chat y delega la preparación del contexto al middleware.

  3. Ingesta de Documentos

  La ingesta de documentos es el primer paso en el proceso RAG, donde los datos brutos se transforman en un formato que puede ser buscado y utilizado por el LLM.

   * Fuentes de Documentos:
       * Archivos Subidos por el Usuario: A través de la ruta /process/file en retrieval.py, los usuarios pueden subir archivos (PDFs, documentos de texto, etc.). La clase Loader en loaders/main.py es la
         encargada de extraer el contenido de estos archivos, utilizando diversas herramientas y APIs externas (Tika, Datalab Marker, Docling, etc.) para manejar diferentes formatos y realizar OCR si es
         necesario.
       * Texto Directo: La ruta /process/text permite la ingesta de texto plano directamente.
       * Contenido Web/YouTube: Las rutas /process/web y /process/youtube permiten procesar URLs, extrayendo el contenido de páginas web o transcripciones de videos.
       * Bases de Conocimiento del Modelo: Los modelos pueden tener bases de conocimiento predefinidas asociadas, que son colecciones de documentos ya procesados y almacenados en la base de datos vectorial.

   * Procesamiento Común (`save_docs_to_vector_db` en `retrieval.py`):
       * Todos los tipos de contenido ingestado pasan por esta función para su preparación:
           * Chunking (División en Fragmentos): Los documentos grandes se dividen en fragmentos más pequeños (chunks) para adaptarse a la ventana de contexto del LLM. Se utilizan diferentes estrategias de
             división (RecursiveCharacterTextSplitter, TokenTextSplitter, MarkdownHeaderTextSplitter) configurables a través de TEXT_SPLITTER, CHUNK_SIZE y CHUNK_OVERLAP.
           * Embedding (Vectorización): Cada chunk de texto se convierte en un vector numérico (embedding) utilizando una embedding_function (definida en retrieval/utils.py). Esta función puede interactuar con
             diferentes motores de embedding (Ollama, OpenAI, Azure OpenAI) configurados en el sistema.
           * Almacenamiento en Base de Datos Vectorial: Los chunks (texto original, su embedding y metadatos relevantes como file_id, name, hash) se insertan en colecciones específicas dentro de la base de
             datos vectorial (VECTOR_DB_CLIENT). Las colecciones pueden ser por archivo (file-{file_id}) o bases de conocimiento generales.

  4. Proceso de Recuperación

  Cuando un usuario realiza una consulta en el chat, el sistema inicia un proceso de recuperación para encontrar la información más relevante.

   * Generación de Consultas (`generate_queries`):
       * En middleware.py, la función chat_completion_files_handler utiliza generate_queries (una función que probablemente invoca a un LLM) para expandir o refinar la consulta original del usuario en una o
         varias consultas de búsqueda más efectivas. Si no se generan consultas, se utiliza el mensaje original del usuario.

   * Recuperación de Fuentes (`get_sources_from_items` en `retrieval/utils.py`):
       * Esta es la función central que toma las consultas generadas y las items (archivos de usuario, bases de conocimiento, etc.) y realiza la búsqueda en la base de datos vectorial.
       * Tipos de Búsqueda:
           * Búsqueda Estándar (`query_collection`): Realiza una búsqueda de similitud vectorial directa. Calcula el embedding de la consulta y busca los k documentos más cercanos en el espacio vectorial.
           * Búsqueda Híbrida (`query_collection_with_hybrid_search`): Si ENABLE_RAG_HYBRID_SEARCH está activado, combina la búsqueda por similitud vectorial (semántica) con la búsqueda por palabras clave
             (BM25). Esto permite capturar tanto la relevancia conceptual como la coincidencia exacta de términos. Utiliza EnsembleRetriever de Langchain para combinar los resultados de ambos tipos de búsqueda.
       * Re-ranking (`RerankCompressor`): Después de la recuperación inicial, los documentos pueden pasar por un paso de re-ranking. La reranking_function (configurada en retrieval.py) evalúa la relevancia de
         los documentos recuperados en relación con la consulta, asignando una puntuación. Solo los TOP_K_RERANKER documentos con la puntuación más alta que superen un RELEVANCE_THRESHOLD se seleccionan para el
         contexto final. Esto mejora la calidad del contexto proporcionado al LLM.

  5. Preparación del Contexto para el LLM

  Una vez que se han recuperado los fragmentos de información más relevantes, se preparan para ser inyectados en el prompt del LLM.

   * Construcción del `context_string`:
       * En middleware.py, los sources recuperados se utilizan para construir una cadena de texto formateada llamada context_string. Cada fragmento de documento se envuelve en etiquetas <source id="..." 
         name="...">...</source>, donde el id permite la citación y el name proporciona una referencia legible.
       * Esto asegura que el LLM reciba el contenido de los documentos de manera estructurada y pueda identificar de dónde proviene cada pieza de información.

   * Aplicación de la Plantilla RAG (`rag_template`):
       * El context_string y el mensaje original del usuario (prompt) se pasan a la función rag_template (definida en open_webui.utils.task.py).
       * Esta función utiliza una plantilla predefinida (RAG_TEMPLATE en la configuración) para combinar el contexto recuperado con la consulta del usuario. La plantilla define cómo se presenta el contexto al
         LLM, típicamente incluyendo instrucciones sobre cómo usar el contexto y dónde insertarlo.

   * Inyección en los Mensajes del LLM:
       * El prompt final, que ahora contiene el contexto RAG, se inyecta en la lista de mensajes que se enviará al LLM.
       * Para la mayoría de los modelos, esto se hace añadiendo o actualizando un mensaje de sistema (add_or_update_system_message) con el prompt contextualizado.
       * Para los modelos de Ollama, se utiliza un "workaround" (prepend_to_first_user_message_content) que antepone el contexto directamente al primer mensaje del usuario, debido a las particularidades de cómo
         Ollama maneja los prompts del sistema.

   * `RAG_FULL_CONTEXT`:
       * La configuración RAG_FULL_CONTEXT permite que, en ciertos casos, se incluya el contenido completo de los documentos en el contexto del LLM, en lugar de solo los fragmentos más relevantes. Esto es útil
         para documentos pequeños o cuando se requiere una comprensión exhaustiva, pero debe usarse con precaución para evitar exceder los límites de tokens del LLM.

  6. Anexo: Contenido Completo de las Funciones Clave

  A continuación, se presenta el contenido completo de las funciones y clases mencionadas, extraídas directamente del código fuente.

  open_webui/retrieval/loaders/main.py

   ... first 179 lines hidden ...
   180                         for lang in self.params.get("ocr_lang").split(",")
   181                         if lang.strip()
   182                     ]
   183 
   184             endpoint = f"{self.url}/v1alpha/convert/file"
   185             r = requests.post(endpoint, files=files, data=params)
   186 
   187         if r.ok:
   188             result = r.json()
   189             document_data = result.get("document", {})
   190             text = document_data.get("md_content", "<No text content found>")
   191 
   192             metadata = {"Content-Type": self.mime_type} if self.mime_type else {}
   193 
   194             log.debug("Docling extracted text: %s", text)
   195 
   196             return [Document(page_content=text, metadata=metadata)]
   197         else:
   198             error_msg = f"Error calling Docling API: {r.reason}"
   199             if r.text:
   200                 try:
   201                     error_data = r.json()
   202                     if "detail" in error_data:
   203                         error_msg += f" - {error_data['detail']}"
   204                 except Exception:
   205                     error_msg += f" - {r.text}"
   206             raise Exception(f"Error calling Docling: {error_msg}")
   207 
   208 
   209 class Loader:
   210     def __init__(self, engine: str = "", **kwargs):
   211         self.engine = engine
   212         self.kwargs = kwargs
   213 
   214     def load(
   215         self, filename: str, file_content_type: str, file_path: str
   216     ) -> list[Document]:
   217         loader = self._get_loader(filename, file_content_type, file_path)
   218         docs = loader.load()
   219 
   220         return [
   221             Document(
   222                 page_content=ftfy.fix_text(doc.page_content), metadata=doc.metadata
   223             )
   224             for doc in docs
   225         ]
   226 
   227     def _is_text_file(self, file_ext: str, file_content_type: str) -> bool:
   228         return file_ext in known_source_ext or (
   229             file_content_type
   230             and file_content_type.find("text/") >= 0
   231             # Avoid text/html files being detected as text
   232             and not file_content_type.find("html") >= 0
   233         )
   234 
   235     def _get_loader(self, filename: str, file_content_type: str, file_path: str):
   236         file_ext = filename.split(".")[-1].lower()
   237 
   238         if (
   239             self.engine == "external"
   240             and self.kwargs.get("EXTERNAL_DOCUMENT_LOADER_URL")
   241             and self.kwargs.get("EXTERNAL_DOCUMENT_LOADER_API_KEY")
   242         ):
   243             loader = ExternalDocumentLoader(
   244                 file_path=file_path,
   245                 url=self.kwargs.get("EXTERNAL_DOCUMENT_LOADER_URL"),
   246                 api_key=self.kwargs.get("EXTERNAL_DOCUMENT_LOADER_API_KEY"),
   247                 mime_type=file_content_type,
   248             )
   249         elif self.engine == "tika" and self.kwargs.get("TIKA_SERVER_URL"):
   250             if self._is_text_file(file_ext, file_content_type):
   251                 loader = TextLoader(file_path, autodetect_encoding=True)
   252             else:
   253                 loader = TikaLoader(
   254                     url=self.kwargs.get("TIKA_SERVER_URL"),
   255                     file_path=file_path,
   256                     mime_type=file_content_type,
   257                     extract_images=self.kwargs.get("PDF_EXTRACT_IMAGES"),
   258                 )
   259         elif (
   260             self.engine == "datalab_marker"
   261             and self.kwargs.get("DATALAB_MARKER_API_KEY")
   262             and file_ext
   263             in [
   264                 "pdf",
   265                 "xls",
   266                 "xlsx",
   267                 "ods",
   268                 "doc",
   269                 "docx",
   270                 "odt",
   271                 "ppt",
   272                 "pptx",
   273                 "odp",
   274                 "html",
   275                 "epub",
   276                 "png",
   277                 "jpeg",
   278                 "jpg",
   279                 "webp",
   280                 "gif",
   281                 "tiff",
   282             ]
   283         ):
   284             loader = DatalabMarkerLoader(
   285                 file_path=file_path,
   286                 api_key=self.kwargs["DATALAB_MARKER_API_KEY"],
   287                 langs=self.kwargs.get("DATALAB_MARKER_LANGS"),
   288                 use_llm=self.kwargs.get("DATALAB_MARKER_USE_LLM", False),
   289                 skip_cache=self.kwargs.get("DATALAB_MARKER_SKIP_CACHE", False),
   290                 force_ocr=self.kwargs.get("DATALAB_MARKER_FORCE_OCR", False),
   291                 paginate=self.kwargs.get("DATALAB_MARKER_PAGINATE", False),
   292                 strip_existing_ocr=self.kwargs.get(
   293                     "DATALAB_MARKER_STRIP_EXISTING_OCR", False
   294                 ),
   295                 disable_image_extraction=self.kwargs.get(
   296                     "DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION", False
   297                 ),
   298                 output_format=self.kwargs.get(
   299                     "DATALAB_MARKER_OUTPUT_FORMAT", "markdown"
   300                 ),
   301             )
   302         elif self.engine == "docling" and self.kwargs.get("DOCLING_SERVER_URL"):
   303             if self._is_text_file(file_ext, file_content_type):
   304                 loader = TextLoader(file_path, autodetect_encoding=True)
   305             else:
   306                 # Build params for DoclingLoader
   307                 params = self.kwargs.get("DOCLING_PARAMS", {})
   308                 if not isinstance(params, dict):
   309                     try:
   310                         params = json.loads(params)
   311                     except json.JSONDecodeError:
   312                         log.error("Invalid DOCLING_PARAMS format, expected JSON object")
   313                         params = {}
   314 
   315                 loader = DoclingLoader(
   316                     url=self.kwargs.get("DOCLING_SERVER_URL"),
   317                     file_path=file_path,
   318                     mime_type=file_content_type,
   319                     params=params,
   320                 )
   321         elif (
   322             self.engine == "document_intelligence"
   323             and self.kwargs.get("DOCUMENT_INTELLIGENCE_ENDPOINT") != ""
   324             and self.kwargs.get("DOCUMENT_INTELLIGENCE_KEY") != ""
   325             and (
   326                 file_ext in ["pdf", "xls", "xlsx", "docx", "ppt", "pptx"]
   327                 or file_content_type
   328                 in [
   329                     "application/vnd.ms-excel",
   330                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
   331                     "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
   332                     "application/vnd.ms-powerpoint",
   333                     "application/vnd.openxmlformats-officedocument.presentationml.presentation",
   334                 ]
   335             )
   336         ):
   337             loader = AzureAIDocumentIntelligenceLoader(
   338                 file_path=file_path,
   339                 api_endpoint=self.kwargs.get("DOCUMENT_INTELLIGENCE_ENDPOINT"),
   340                 api_key=self.kwargs.get("DOCUMENT_INTELLIGENCE_KEY"),
   341             )
   342         elif (
   343             self.engine == "mistral_ocr"
   344             and self.kwargs.get("MISTRAL_OCR_API_KEY") != ""
   345             and file_ext
   346             in ["pdf"]  # Mistral OCR currently only supports PDF and images
   347         ):
   348             loader = MistralLoader(
   349                 api_key=self.kwargs.get("MISTRAL_OCR_API_KEY"), file_path=file_path
   350             )
   351         elif (
   352             self.engine == "external"
   353             and self.kwargs.get("MISTRAL_OCR_API_KEY") != ""
   354             and file_ext
   355             in ["pdf"]  # Mistral OCR currently only supports PDF and images
   356         ):
   357             loader = MistralLoader(
   358                 api_key=self.kwargs.get("MISTRAL_OCR_API_KEY"), file_path=file_path
   359             )
   360         else:
   361             if file_ext == "pdf":
   362                 loader = PyPDFLoader(
   363                     file_path, extract_images=self.kwargs.get("PDF_EXTRACT_IMAGES")
   364                 )
   365             elif file_ext == "csv":
   366                 loader = CSVLoader(file_path, autodetect_encoding=True)
   367             elif file_ext == "rst":
   368                 loader = UnstructuredRSTLoader(file_path, mode="elements")
   369             elif file_ext == "xml":
   370                 loader = UnstructuredXMLLoader(file_path)
   371             elif file_ext in ["htm", "html"]:
   372                 loader = BSHTMLLoader(file_path, open_encoding="unicode_escape")
   373             elif file_ext == "md":
   374                 loader = TextLoader(file_path, autodetect_encoding=True)
   375             elif file_content_type == "application/epub+zip":
   376                 loader = UnstructuredEPubLoader(file_path)
   377             elif (
   378                 file_content_type
   379                 == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
   380                 or file_ext == "docx"
   381             ):
   382                 loader = Docx2txtLoader(file_path)
   383             elif file_content_type in [
   384                 "application/vnd.ms-excel",
   385                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
   386             ] or file_ext in ["xls", "xlsx"]:
   387                 loader = UnstructuredExcelLoader(file_path)
   388             elif file_content_type in [
   389                 "application/vnd.ms-powerpoint",
   390                 "application/vnd.openxmlformats-officedocument.presentationml.presentation",
   391             ] or file_ext in ["ppt", "pptx"]:
   392                 loader = UnstructuredPowerPointLoader(file_path)
   393             elif file_ext == "msg":
   394                 loader = OutlookMessageLoader(file_path)
   395             elif file_ext == "odt":
   396                 loader = UnstructuredODTLoader(file_path)
   397             elif self._is_text_file(file_ext, file_content_type):
   398                 loader = TextLoader(file_path, autodetect_encoding=True)
   399             else:
   400                 loader = TextLoader(file_path, autodetect_encoding=True)
   401 
   402         return loader

  open_webui/retrieval/vector/main.py

    1 from pydantic import BaseModel
    2 from abc import ABC, abstractmethod
    3 from typing import Any, Dict, List, Optional, Union
    4 
    5 
    6 class VectorItem(BaseModel):
    7     id: str
    8     text: str
    9     vector: List[float | int]
   10     metadata: Any
   11 
   12 
   13 class GetResult(BaseModel):
   14     ids: Optional[List[List[str]]]
   15     documents: Optional[List[List[str]]]
   16     metadatas: Optional[List[List[Any]]]
   17 
   18 
   19 class SearchResult(GetResult):
   20     distances: Optional[List[List[float | int]]]
   21 
   22 
   23 class VectorDBBase(ABC):
   24     """
   25     Abstract base class for all vector database backends.
   26 
   27     Implementations of this class provide methods for collection management,
   28     vector insertion, deletion, similarity search, and metadata filtering.
   29 
   30     Any custom vector database integration must inherit from this class and
   31     implement all abstract methods.
   32     """
   33 
   34     @abstractmethod
   35     def has_collection(self, collection_name: str) -> bool:
   36         """Check if the collection exists in the vector DB."""
   37         pass
   38 
   39     @abstractmethod
   40     def delete_collection(self, collection_name: str) -> None:
   41         """Delete a collection from the vector DB."""
   42         pass
   43 
   44     @abstractmethod
   45     def insert(self, collection_name: str, items: List[VectorItem]) -> None:
   46         """Insert a list of vector items into a collection."""
   47         pass
   48 
   49     @abstractmethod
   50     def upsert(self, collection_name: str, items: List[VectorItem]) -> None:
   51         """Insert or update vector items in a collection."""
   52         pass
   53 
   54     @abstractmethod
   55     def search(
   56         self, collection_name: str, vectors: List[List[Union[float, int]]], limit: int
   57     ) -> Optional[SearchResult]:
   58         """Search for similar vectors in a collection."""
   59         pass
   60 
   61     @abstractmethod
   62     def query(
   63         self, collection_name: str, filter: Dict, limit: Optional[int] = None
   64     ) -> Optional[GetResult]:
   65         """Query vectors from a collection using metadata filter."""
   66         pass
   67 
   68     @abstractmethod
   69     def get(self, collection_name: str) -> Optional[GetResult]:
   70         """Retrieve all vectors from a collection."""
   71         pass
   72 
   73     @abstractmethod
   74     def delete(
   75         self,
   76         collection_name: str,
   77         ids: Optional[List[str]] = None,
   78         filter: Optional[Dict] = None,
   79     ) -> None:
   80         """Delete vectors by ID or filter from a collection."""
   81         pass
   82 
   83     @abstractmethod
   84     def reset(self) -> None:
   85         """Reset the vector database by removing all collections or those matching a condition."""
   86         pass

  open_webui/routers/retrieval.py (Funciones relevantes)

     1 # ... (imports and other code) ...
     2 
     3 def save_docs_to_vector_db(
     4     request: Request,
     5     docs,
     6     collection_name,
     7     metadata: Optional[dict] = None,
     8     overwrite: bool = False,
     9     split: bool = True,
    10     add: bool = False,
    11     user=None,
    12 ) -> bool:
    13     def _get_docs_info(docs: list[Document]) -> str:
    14         docs_info = set()
    15 
    16         # Trying to select relevant metadata identifying the document.
    17         for doc in docs:
    18             metadata = getattr(doc, "metadata", {})
    19             doc_name = metadata.get("name", "")
    20             if not doc_name:
    21                 doc_name = metadata.get("title", "")
    22             if not doc_name:
    23                 doc_name = metadata.get("source", "")
    24             if doc_name:
    25                 docs_info.add(doc_name)
    26 
    27         return ", ".join(docs_info)
    28 
    29     log.info(
    30         f"save_docs_to_vector_db: document {_get_docs_info(docs)} {collection_name}"
    31     )
    32 
    33     # Check if entries with the same hash (metadata.hash) already exist
    34     if metadata and "hash" in metadata:
    35         result = VECTOR_DB_CLIENT.query(
    36             collection_name=collection_name,
    37             filter={"hash": metadata["hash"]},
    38         )
    39 
    40         if result is not None:
    41             existing_doc_ids = result.ids[0]
    42             if existing_doc_ids:
    43                 log.info(f"Document with hash {metadata['hash']} already exists")
    44                 raise ValueError(ERROR_MESSAGES.DUPLICATE_CONTENT)
    45 
    46     if split:
    47         if request.app.state.config.TEXT_SPLITTER in ["", "character"]:
    48             text_splitter = RecursiveCharacterTextSplitter(
    49                 chunk_size=request.app.state.config.CHUNK_SIZE,
    50                 chunk_overlap=request.app.state.config.CHUNK_OVERLAP,
    51                 add_start_index=True,
    52             )
    53             docs = text_splitter.split_documents(docs)
    54         elif request.app.state.config.TEXT_SPLITTER == "token":
    55             log.info(
    56                 f"Using token text splitter: {request.app.state.config.TIKTOKEN_ENCODING_NAME}"
    57             )
    58 
    59             tiktoken.get_encoding(str(request.app.state.config.TIKTOKEN_ENCODING_NAME))
    60             text_splitter = TokenTextSplitter(
    61                 encoding_name=str(request.app.state.config.TIKTOKEN_ENCODING_NAME),
    62                 chunk_size=request.app.state.config.CHUNK_SIZE,
    63                 chunk_overlap=request.app.state.config.CHUNK_OVERLAP,
    64                 add_start_index=True,
    65             )
    66             docs = text_splitter.split_documents(docs)
    67         elif request.app.state.config.TEXT_SPLITTER == "markdown_header":
    68             log.info("Using markdown header text splitter")
    69 
    70             # Define headers to split on - covering most common markdown header levels
    71             headers_to_split_on = [
    72                 ("#", "Header 1"),
    73                 ("##", "Header 2"),
    74                 ("###", "Header 3"),
    75                 ("####", "Header 4"),
    76                 ("#####", "Header 5"),
    77                 ("######", "Header 6"),
    78             ]
    79 
    80             markdown_splitter = MarkdownHeaderTextSplitter(
    81                 headers_to_split_on=headers_to_split_on,
    82                 strip_headers=False,  # Keep headers in content for context
    83             )
    84 
    85             md_split_docs = []
    86             for doc in docs:
    87                 md_header_splits = markdown_splitter.split_text(doc.page_content)
    88                 text_splitter = RecursiveCharacterTextSplitter(
    89                     chunk_size=request.app.state.config.CHUNK_SIZE,
    90                     chunk_overlap=request.app.state.config.CHUNK_OVERLAP,
    91                     add_start_index=True,
    92                 )
    93                 md_header_splits = text_splitter.split_documents(md_header_splits)
    94 
    95                 # Convert back to Document objects, preserving original metadata
    96                 for split_chunk in md_header_splits:
    97                     headings_list = []
    98                     # Extract header values in order based on headers_to_split_on
    99                     for _, header_meta_key_name in headers_to_split_on:
   100                         if header_meta_key_name in split_chunk.metadata:
   101                             headings_list.append(
   102                                 split_chunk.metadata[header_meta_key_name]
   103                             )
   104 
   105                     md_split_docs.append(
   106                         Document(
   107                             page_content=split_chunk.page_content,
   108                             metadata={**doc.metadata, "headings": headings_list},
   109                         )
   110                     )
   111 
   112             docs = md_split_docs
   113         else:
   114             raise ValueError(ERROR_MESSAGES.DEFAULT("Invalid text splitter"))
   115 
   116     if len(docs) == 0:
   117         raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)
   118 
   119     texts = [doc.page_content for doc in docs]
   120     metadatas = [
   121         {
   122             **doc.metadata,
   123             **(metadata if metadata else {}),
   124             "embedding_config": json.dumps(
   125                 {
   126                     "engine": request.app.state.config.RAG_EMBEDDING_ENGINE,
   127                     "model": request.app.state.config.RAG_EMBEDDING_MODEL,
   128                 }
   129             ),
   130         }
   131         for doc in docs
   132     ]
   133 
   134     # ChromaDB does not like datetime formats
   135     # for meta-data so convert them to string.
   136     for metadata in metadatas:
   137         for key, value in metadata.items():
   138             if (
   139                 isinstance(value, datetime)
   140                 or isinstance(value, list)
   141                 or isinstance(value, dict)
   142             ):
   143                 metadata[key] = str(value)
   144 
   145     try:
   146         if VECTOR_DB_CLIENT.has_collection(collection_name=collection_name):
   147             log.info(f"collection {collection_name} already exists")
   148 
   149             if overwrite:
   150                 VECTOR_DB_CLIENT.delete_collection(collection_name=collection_name)
   151                 log.info(f"deleting existing collection {collection_name}")
   152             elif add is False:
   153                 log.info(
   154                     f"collection {collection_name} already exists, overwrite is False and add is False"
   155                 )
   156                 return True
   157 
   158         log.info(f"adding to collection {collection_name}")
   159         embedding_function = get_embedding_function(
   160             request.app.state.config.RAG_EMBEDDING_ENGINE,
   161             request.app.state.config.RAG_EMBEDDING_MODEL,
   162             request.app.state.ef,
   163             (
   164                 request.app.state.config.RAG_OPENAI_API_BASE_URL
   165                 if request.app.state.config.RAG_EMBEDDING_ENGINE == "openai"
   166                 else (
   167                     request.app.state.config.RAG_OLLAMA_BASE_URL
   168                     if request.app.state.config.RAG_EMBEDDING_ENGINE == "ollama"
   169                     else request.app.state.config.RAG_AZURE_OPENAI_BASE_URL
   170                 )
   171             ),
   172             (
   173                 request.app.state.config.RAG_OPENAI_API_KEY
   174                 if request.app.state.config.RAG_EMBEDDING_ENGINE == "openai"
   175                 else (
   176                     request.app.state.config.RAG_OLLAMA_API_KEY
   177                     if request.app.state.config.RAG_EMBEDDING_ENGINE == "ollama"
   178                     else request.app.state.config.RAG_AZURE_OPENAI_API_KEY
   179                 )
   180             ),
   181             request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
   182             azure_api_version=(
   183                 request.app.state.config.RAG_AZURE_OPENAI_API_VERSION
   184                 if request.app.state.config.RAG_EMBEDDING_ENGINE == "azure_openai"
   185                 else None
   186             ),
   187         )
   188 
   189         embeddings = embedding_function(
   190             list(map(lambda x: x.replace("\n", " "), texts)),
   191             prefix=RAG_EMBEDDING_CONTENT_PREFIX,
   192             user=user,
   193         )
   194 
   195         items = [
   196             {
   197                 "id": str(uuid.uuid4()),
   198                 "text": text,
   199                 "vector": embeddings[idx],
   200                 "metadata": metadatas[idx],
   201             }
   202             for idx, text in enumerate(texts)
   203         ]
   204 
   205         VECTOR_DB_CLIENT.insert(
   206             collection_name=collection_name,
   207             items=items,
   208         )
   209 
   210         return True
   211     except Exception as e:
   212         log.exception(e)
   213         raise e
   214 
   215 # ... (other functions and API routes) ...

  open_webui/utils/middleware.py (Funciones relevantes)

   ... first 172 lines hidden ...
   173             else:
   174                 knowledge_files.append(item)
   175 
   176         files = form_data.get("files", [])
   177         files.extend(knowledge_files)
   178         form_data["files"] = files
   179 
   180     variables = form_data.pop("variables", None)
   181 
   182     # Process the form_data through the pipeline
   183     try:
   184         form_data = await process_pipeline_inlet_filter(
   185             request, form_data, user, models
   186         )
   187     except Exception as e:
   188         raise e
   189 
   190     try:
   191         filter_functions = [
   192             Functions.get_function_by_id(filter_id)
   193             for filter_id in get_sorted_filter_ids(
   194                 request, model, metadata.get("filter_ids", [])
   195             )
   196         ]
   197 
   198         form_data, flags = await process_filter_functions(
   199             request=request,
   200             filter_functions=filter_functions,
   201             filter_type="inlet",
   202             form_data=form_data,
   203             extra_params=extra_params,
   204         )
   205     except Exception as e:
   206         raise Exception(f"Error: {e}")
   207 
   208     features = form_data.pop("features", None)
   209     if features:
   210         if "memory" in features and features["memory"]:
   211             form_data = await chat_memory_handler(
   212                 request, form_data, extra_params, user
   213             )
   214 
   215         if "web_search" in features and features["web_search"]:
   216             form_data = await chat_web_search_handler(
   217                 request, form_data, extra_params, user
   218             )
   219 
   220         if "image_generation" in features and features["image_generation"]:
   221             form_data = await chat_image_generation_handler(
   222                 request, form_data, extra_params, user
   223             )
   224 
   225         if "code_interpreter" in features and features["code_interpreter"]:
   226             form_data["messages"] = add_or_update_user_message(
   227                 (
   228                     request.app.state.config.CODE_INTERPRETER_PROMPT_TEMPLATE
   229                     if request.app.state.config.CODE_INTERPRETER_PROMPT_TEMPLATE != ""
   230                     else DEFAULT_CODE_INTERPRETER_PROMPT
   231                 ),
   232                 form_data["messages"],
   233             )
   234 
   235     tool_ids = form_data.pop("tool_ids", None)
   236     files = form_data.pop("files", None)
   237 
   238     # Remove files duplicates
   239     if files:
   240         files = list({json.dumps(f, sort_keys=True): f for f in files}.values())
   241 
   242     metadata = {
   243         **metadata,
   244         "tool_ids": tool_ids,
   245         "files": files,
   246     }
   247     form_data["metadata"] = metadata
   248 
   249     # Server side tools
   250     tool_ids = metadata.get("tool_ids", None)
   251     # Client side tools
   252     tool_servers = metadata.get("tool_servers", None)
   253 
   254     log.debug(f"{tool_ids=}")
   255     log.debug(f"{tool_servers=}")
   256 
   257     tools_dict = {}
   258 
   259     if tool_ids:
   260         tools_dict = get_tools(
   261             request,
   262             tool_ids,
   263             user,
   264             {
   265                 **extra_params,
   266                 "__model__": models[task_model_id],
   267                 "__messages__": form_data["messages"],
   268                 "__files__": metadata.get("files", []),
   269             },
   270         )
   271 
   272     if tool_servers:
   273         for tool_server in tool_servers:
   274             tool_specs = tool_server.pop("specs", [])
   275 
   276             for tool in tool_specs:
   277                 tools_dict[tool["name"]] = {
   278                     "spec": tool,
   279                     "direct": True,
   280                     "server": tool_server,
   281                 }
   282 
   283     if tools_dict:
   284         if metadata.get("function_calling") == "native":
   285             # If the function calling is native, then call the tools function calling handler
   286             metadata["tools"] = tools_dict
   287             form_data["tools"] = [
   288                 {"type": "function", "function": tool.get("spec", {})}
   289                 for tool in tools_dict.values()
   290             ]
   291         else:
   292             # If the function calling is not native, then call the tools function calling handler
   293             try:
   294                 form_data, flags = await chat_completion_tools_handler(
   295                     request, form_data, extra_params, user, models, tools_dict
   296                 )
   297                 sources.extend(flags.get("sources", []))
   298             except Exception as e:
   299                 log.exception(e)
   300 
   301     try:
   302         form_data, flags = await chat_completion_files_handler(request, form_data, user)
   303         sources.extend(flags.get("sources", []))
   304     except Exception as e:
   305         log.exception(e)
   306 
   307     # If context is not empty, insert it into the messages
   308     if len(sources) > 0:
   309         context_string = ""
   310         citation_idx_map = {}
   311 
   312         for source in sources:
   313             is_tool_result = source.get("tool_result", False)
   314 
   315             if "document" in source and not is_tool_result:
   316                 for document_text, document_metadata in zip(
   317                     source["document"], source["metadata"]
   318                 ):
   319                     source_name = source.get("source", {}).get("name", None)
   320                     source_id = (
   321                         document_metadata.get("source", None)
   322                         or source.get("source", {}).get("id", None)
   323                         or "N/A"
   324                     )
   325 
   326                     if source_id not in citation_idx_map:
   327                         citation_idx_map[source_id] = len(citation_idx_map) + 1
   328 
   329                     context_string += (
   330                         f'<source id="{citation_idx_map[source_id]}"'
   331                         + (f' name="{source_name}"' if source_name else "")
   332                         + f">{document_text}</source>\n"
   333                     )
   334 
   335         context_string = context_string.strip()
   336 
   337         prompt = get_last_user_message(form_data["messages"])
   338         if prompt is None:
   339             raise Exception("No user message found")
   340 
   341         if context_string == "":
   342             if request.app.state.config.RELEVANCE_THRESHOLD == 0:
   343                 log.debug(
   344                     f"With a 0 relevancy threshold for RAG, the context cannot be empty"
   345                 )
   346         else:
   347             # Workaround for Ollama 2.0+ system prompt issue
   348             # TODO: replace with add_or_update_system_message
   349             if model.get("owned_by") == "ollama":
   350                 form_data["messages"] = prepend_to_first_user_message_content(
   351                     rag_template(
   352                         request.app.state.config.RAG_TEMPLATE, context_string, prompt
   353                     ),
   354                     form_data["messages"],
   355                 )
   356             else:
   357                 form_data["messages"] = add_or_update_system_message(
   358                     rag_template(
   359                         request.app.state.config.RAG_TEMPLATE, context_string, prompt
   360                     ),
   361                     form_data["messages"],
   362                 )
   363 
   364     # If there are citations, add them to the data_items
   365     sources = [
   366         source
   367         for source in sources
   368         if source.get("source", {}).get("name", "")
   369         or source.get("source", {}).get("id", "")
   370     ]
   371 
   372     if len(sources) > 0:
   373         events.append({"sources": sources})
   374 
   375     if model_knowledge:
   376         await event_emitter(
   377             {
   378                 "type": "status",
   379                 "data": {
   380                     "action": "knowledge_search",
   381                     "query": user_message,
   382                     "done": True,
   383                     "hidden": True,
   384                 },
   385             }
   386         )
   387 
   388     return form_data, metadata, events
   389 
   390 
   391 async def process_chat_response(
   392     request, response, form_data, user, metadata, model, events, tasks
   393 ):
   394     # ... (function content) ...
   395     pass # Content omitted for brevity, as it primarily handles post-LLM response processing and background tasks.

  open_webui/retrieval/utils.py (Funciones relevantes)

   ... first 522 lines hidden ...
   523             ):
   524                 if item.get("file", {}).get("data", {}).get("content", ""):
   525                     # Manual Full Mode Toggle
   526                     # Used from chat file modal, we can assume that the file content will be available from item.get("file").get("data", {}).get("content")
   527                     query_result = {
   528                         "documents": [
   529                             [item.get("file", {}).get("data", {}).get("content", "")]
   530                         ],
   531                         "metadatas": [
   532                             [
   533                                 {
   534                                     "file_id": item.get("id"),
   535                                     "name": item.get("name"),
   536                                     **item.get("file")
   537                                     .get("data", {})
   538                                     .get("metadata", {}),
   539                                 }
   540                             ]
   541                         ],
   542                     }
   543                 elif item.get("id"):
   544                     file_object = Files.get_file_by_id(item.get("id"))
   545                     if file_object:
   546                         query_result = {
   547                             "documents": [[file_object.data.get("content", "")]],
   548                             "metadatas": [
   549                                 [
   550                                     {
   551                                         "file_id": item.get("id"),
   552                                         "name": file_object.filename,
   553                                         "source": file_object.filename,
   554                                     }
   555                                 ]
   556                             ],
   557                         }
   558             else:
   559                 # Fallback to collection names
   560                 if item.get("legacy"):
   561                     collection_names.append(f"{item['id']}")
   562                 else:
   563                     collection_names.append(f"file-{item['id']}")
   564 
   565         elif item.get("type") == "collection":
   566             if (
   567                 item.get("context") == "full"
   568                 or request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL
   569             ):
   570                 # Manual Full Mode Toggle for Collection
   571                 knowledge_base = Knowledges.get_knowledge_by_id(item.get("id"))
   572 
   573                 if knowledge_base and (
   574                     user.role == "admin"
   575                     or has_access(user.id, "read", knowledge_base.access_control)
   576                 ):
   577 
   578                     file_ids = knowledge_base.data.get("file_ids", [])
   579 
   580                     documents = []
   581                     metadatas = []
   582                     for file_id in file_ids:
   583                         file_object = Files.get_file_by_id(file_id)
   584 
   585                         if file_object:
   586                             documents.append(file_object.data.get("content", ""))
   587                             metadatas.append(
   588                                 {
   589                                     "file_id": file_id,
   590                                     "name": file_object.filename,
   591                                     "source": file_object.filename,
   592                                 }
   593                             )
   594 
   595                     query_result = {
   596                         "documents": [documents],
   597                         "metadatas": [metadatas],
   598                     }
   599             else:
   600                 # Fallback to collection names
   601                 if item.get("legacy"):
   602                     collection_names = item.get("collection_names", [])
   603                 else:
   604                     collection_names.append(item["id"])
   605 
   606         elif item.get("docs"):
   607             # BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL
   608             query_result = {
   609                 "documents": [[doc.get("content") for doc in item.get("docs")]],
   610                 "metadatas": [[doc.get("metadata") for doc in item.get("docs")]],
   611             }
   612         elif item.get("collection_name"):
   613             # Direct Collection Name
   614             collection_names.append(item["collection_name"])
   615         elif item.get("collection_names"):
   616             # Collection Names List
   617             collection_names.extend(item["collection_names"])
   618 
   619         # If query_result is None
   620         # Fallback to collection names and vector search the collections
   621         if query_result is None and collection_names:
   622             collection_names = set(collection_names).difference(extracted_collections)
   623             if not collection_names:
   624                 log.debug(f"skipping {item} as it has already been extracted")
   625                 continue
   626 
   627             try:
   628                 if full_context:
   629                     query_result = get_all_items_from_collections(collection_names)
   630                 else:
   631                     query_result = None  # Initialize to None
   632                     if hybrid_search:
   633                         try:
   634                             query_result = query_collection_with_hybrid_search(
   635                                 collection_names=collection_names,
   636                                 queries=queries,
   637                                 embedding_function=embedding_function,
   638                                 k=k,
   639                                 reranking_function=reranking_function,
   640                                 k_reranker=k_reranker,
   641                                 r=r,
   642                                 hybrid_bm25_weight=hybrid_bm25_weight,
   643                             )
   644                         except Exception as e:
   645                             log.debug(
   646                                 "Error when using hybrid search, using non hybrid search as fallback."
   647                             )
   648 
   649                     # fallback to non-hybrid search
   650                     if not hybrid_search and query_result is None:
   651                         query_result = query_collection(
   652                             collection_names=collection_names,
   653                             queries=queries,
   654                             embedding_function=embedding_function,
   655                             k=k,
   656                         )
   657             except Exception as e:
   658                 log.exception(e)
   659 
   660             extracted_collections.extend(collection_names)
   661 
   662         if query_result:
   663             if "data" in item:
   664                 del item["data"]
   665             query_results.append({**query_result, "file": item})
   666 
   667     sources = []
   668     for query_result in query_results:
   669         try:
   670             if "documents" in query_result:
   671                 if "metadatas" in query_result:
   672                     source = {
   673                         "source": query_result["file"],
   674                         "document": query_result["documents"][0],
   675                         "metadata": query_result["metadatas"][0],
   676                     }
   677                     if "distances" in query_result and query_result["distances"]:
   678                         source["distances"] = query_result["distances"][0]
   679 
   680                     sources.append(source)
   681         except Exception as e:
   682             log.exception(e)
   683 
   684     return sources
   685 
   686 
   687 def get_embedding_function(
   688     embedding_engine,
   689     embedding_model,
   690     embedding_function,
   691     url,
   692     key,
   693     embedding_batch_size,
   694     azure_api_version=None,
   695 ):
   696     if embedding_engine == "":
   697         return lambda query, prefix=None, user=None: embedding_function.encode(
   698             query, **({"prompt": prefix} if prefix else {})
   699         ).tolist()
   700     elif embedding_engine in ["ollama", "openai", "azure_openai"]:
   701         func = lambda query, prefix=None, user=None: generate_embeddings(
   702             engine=embedding_engine,
   703             model=embedding_model,
   704             text=query,
   705             prefix=prefix,
   706             url=url,
   707             key=key,
   708             user=user,
   709             azure_api_version=azure_api_version,
   710         )
   711 
   712         def generate_multiple(query, prefix, user, func):
   713             if isinstance(query, list):
   714                 embeddings = []
   715                 for i in range(0, len(query), embedding_batch_size):
   716                     embeddings.extend(
   717                         func(
   718                             query[i : i + embedding_batch_size],
   719                             prefix=prefix,
   720                             user=user,
   721                         )
   722                     )
   723                 return embeddings
   724             else:
   725                 return func(query, prefix, user)
   726 
   727         return lambda query, prefix=None, user=None: generate_multiple(
   728             query, prefix, user, func
   729         )
   730     else:
   731         raise ValueError(f"Unknown embedding engine: {embedding_engine}")
   732 
   733 
   734 def get_reranking_function(reranking_engine, reranking_model, reranking_function):
   735     if reranking_function is None:
   736         return None
   737     if reranking_engine == "external":
   738         return lambda sentences, user=None: reranking_function.predict(
   739             sentences, user=user
   740         )
   741     else:
   742         return lambda sentences, user=None: reranking_function.predict(sentences)
   743 
   744 
   745 # ... (other functions) ...

  open_webui/utils/chat.py (Funciones relevantes)

     1 # ... (imports and other code) ...
     2 
     3 async def generate_chat_completion(
     4     request: Request,
     5     form_data: dict,
     6     user: Any,
     7     bypass_filter: bool = False,
     8 ):
     9     log.debug(f"generate_chat_completion: {form_data}")
    10     if BYPASS_MODEL_ACCESS_CONTROL:
    11         bypass_filter = True
    12 
    13     if hasattr(request.state, "metadata"):
    14         if "metadata" not in form_data:
    15             form_data["metadata"] = request.state.metadata
    16         else:
    17             form_data["metadata"] = {
    18                 **form_data["metadata"],
    19                 **request.state.metadata,
    20             }
    21 
    22     if getattr(request.state, "direct", False) and hasattr(request.state, "model"):
    23         models = {
    24             request.state.model["id"]: request.state.model,
    25         }
    26         log.debug(f"direct connection to model: {models}")
    27     else:
    28         models = request.app.state.MODELS
    29 
    30     model_id = form_data["model"]
    31     if model_id not in models:
    32         raise Exception("Model not found")
    33 
    34     model = models[model_id]
    35 
    36     if getattr(request.state, "direct", False):
    37         return await generate_direct_chat_completion(
    38             request, form_data, user=user, models=models
    39         )
    40     else:
    41         # Check if user has access to the model
    42         if not bypass_filter and user.role == "user":
    43             try:
    44                 check_model_access(user, model)
    45             except Exception as e:
    46                 raise e
    47 
    48         if model.get("owned_by") == "arena":
    49             model_ids = model.get("info", {}).get("meta", {}).get("model_ids")
    50             filter_mode = model.get("info", {}).get("meta", {}).get("filter_mode")
    51             if model_ids and filter_mode == "exclude":
    52                 model_ids = [
    53                     model["id"]
    54                     for model in list(request.app.state.MODELS.values())
    55                     if model.get("owned_by") != "arena" and model["id"] not in model_ids
    56                 ]
    57 
    58             selected_model_id = None
    59             if isinstance(model_ids, list) and model_ids:
    60                 selected_model_id = random.choice(model_ids)
    61             else:
    62                 model_ids = [
    63                     model["id"]
    64                     for model in list(request.app.state.MODELS.values())
    65                     if model.get("owned_by") != "arena"
    66                 ]
    67                 selected_model_id = random.choice(model_ids)
    68 
    69             form_data["model"] = selected_model_id
    70 
    71             if form_data.get("stream") == True:
    72 
    73                 async def stream_wrapper(stream):
    74                     yield f"data: {json.dumps({'selected_model_id': selected_model_id})}\n\n"
    75                     async for chunk in stream:
    76                         yield chunk
    77 
    78                 response = await generate_chat_completion(
    79                     request, form_data, user, bypass_filter=True
    80                 )
    81                 return StreamingResponse(
    82                     stream_wrapper(response.body_iterator),
    83                     media_type="text/event-stream",
    84                     background=response.background,
    85                 )
    86             else:
    87                 return {
    88                     **(
    89                         await generate_chat_completion(
    90                             request, form_data, user, bypass_filter=True
    91                         )
    92                     ),
    93                     "selected_model_id": selected_model_id,
    94                 }
    95 
    96         if model.get("pipe"):
    97             # Below does not require bypass_filter because this is the only route the uses this function and it is already bypassing the filter
    98             return await generate_function_chat_completion(
    99                 request, form_data, user=user, models=models
   100             )
   101         if model.get("owned_by") == "ollama":
   102             # Using /ollama/api/chat endpoint
   103             form_data = convert_payload_openai_to_ollama(form_data)
   104             response = await generate_ollama_chat_completion(
   105                 request=request,
   106                 form_data=form_data,
   107                 user=user,
   108                 bypass_filter=bypass_filter,
   109             )
   110             if form_data.get("stream"):
   111                 response.headers["content-type"] = "text/event-stream"
   112                 return StreamingResponse(
   113                     convert_streaming_response_ollama_to_openai(response),
   114                     headers=dict(response.headers),
   115                     background=response.background,
   116                 )
   117             else:
   118                 return convert_response_ollama_to_openai(response)
   119         else:
   120             return await generate_openai_chat_completion(
   121                 request=request,
   122                 form_data=form_data,
   123                 user=user,
   124                 bypass_filter=bypass_filter,
   125             )
   126 
   127 
   128 chat_completion = generate_chat_completion
   129 
   130 # ... (other functions) ...

╭─────────────────────────────────────────────────╮
│  > ok haz un documento con el informe completo  │
╰─────────────────────────────────────────────────╯

✦ Aquí tienes el informe completo sobre la gestión del contexto RAG en el proyecto Open WebUI, incluyendo el anexo con el código de las funciones clave.

  ---

  Informe Detallado: Gestión del Contexto RAG en Open WebUI

  1. Introducción

  La Generación Aumentada por Recuperación (RAG) es una técnica fundamental en los sistemas de inteligencia artificial conversacionales modernos. Permite a los Large Language Models (LLM) ir más allá de su
  conocimiento pre-entrenado, accediendo y utilizando información externa y en tiempo real para generar respuestas más precisas, relevantes y actualizadas. En el proyecto Open WebUI, la implementación de RAG
  es un pilar central para enriquecer las interacciones del chat, posibilitando que el LLM responda preguntas basadas en documentos específicos proporcionados por el usuario (como archivos subidos) o en bases
  de conocimiento preexistentes.

  Este informe detalla la arquitectura y el flujo de trabajo de la gestión del contexto RAG en Open WebUI, desde la ingesta de documentos hasta la preparación final del prompt para el LLM, con un enfoque en
  cómo se manejan las consultas de los usuarios y las bases de conocimiento.

  2. Arquitectura General de RAG

  La arquitectura RAG en Open WebUI es modular y está diseñada para una integración fluida de diversas fuentes de información. Se compone de los siguientes módulos principales:

   * Módulo de Carga (`open_webui.retrieval.loaders`): Encargado de procesar y extraer contenido de diferentes tipos de documentos.
   * Módulo de Base de Datos Vectorial (`open_webui.retrieval.vector`): Proporciona una interfaz abstracta para interactuar con varias bases de datos vectoriales, donde se almacenan los embeddings de los
     documentos.
   * Módulo de Enrutamiento (`open_webui.routers.retrieval`): Expone las APIs para la ingesta de documentos y la configuración de los parámetros de RAG.
   * Módulo de Utilidades de Recuperación (`open_webui.retrieval.utils`): Contiene la lógica central para la búsqueda, recuperación y re-ranking de documentos.
   * Módulo de Middleware de Chat (`open_webui.utils.middleware`): Orquesta el flujo de RAG, integrando la recuperación de documentos en el proceso de manejo de mensajes del chat.
   * Módulo de Utilidades de Chat (`open_webui.utils.chat`): Gestiona la finalización del chat y delega la preparación del contexto al middleware.

  3. Ingesta de Documentos

  La ingesta es el primer paso crucial, donde los datos brutos se transforman en un formato que puede ser vectorizado y buscado.

   * Fuentes de Documentos Soportadas:
       * Archivos Subidos por el Usuario: A través de la ruta /process/file en open_webui/routers/retrieval.py, los usuarios pueden cargar una amplia variedad de formatos de documentos (PDFs, DOCX, CSV, HTML,
         etc.). La clase Loader en open_webui/retrieval/loaders/main.py es la responsable de la extracción de contenido. Esta clase es altamente configurable y puede utilizar motores de extracción externos como
         Tika, Datalab Marker o Docling para manejar formatos complejos y realizar Reconocimiento Óptico de Caracteres (OCR) si es necesario.
       * Texto Directo: La ruta /process/text permite la ingesta de contenido de texto plano directamente, útil para fragmentos de información cortos o generados dinámicamente.
       * Contenido Web y YouTube: Las rutas /process/web y /process/youtube facilitan la extracción de contenido de URLs, incluyendo páginas web completas y transcripciones de videos de YouTube.
       * Bases de Conocimiento Preexistentes: El sistema permite asociar bases de conocimiento predefinidas (colecciones de documentos ya procesados y almacenados en la base de datos vectorial) a modelos
         específicos.

   * Procesamiento de Documentos (`save_docs_to_vector_db` en `open_webui/routers/retrieval.py`):
       * Independientemente de la fuente, todos los documentos pasan por la función save_docs_to_vector_db para su preparación antes de ser almacenados en la base de datos vectorial.
       * Chunking (División en Fragmentos): Los documentos extensos se dividen en fragmentos más pequeños (chunks). Esto es esencial para ajustarse a las limitaciones de la ventana de contexto de los LLM y para
         mejorar la granularidad de la recuperación. El proyecto soporta varias estrategias de división:
           * RecursiveCharacterTextSplitter: Divide el texto recursivamente basándose en una lista de caracteres.
           * TokenTextSplitter: Divide el texto basándose en un número máximo de tokens, utilizando un codificador tiktoken.
           * MarkdownHeaderTextSplitter: Especialmente útil para documentos Markdown, divide el texto basándose en los encabezados.
          Los parámetros CHUNK_SIZE (tamaño máximo de cada fragmento) y CHUNK_OVERLAP (cantidad de texto que se solapa entre fragmentos adyacentes para mantener el contexto) son configurables.
       * Embedding (Vectorización): Cada chunk de texto se transforma en un vector numérico de alta dimensión (embedding). Este proceso se realiza utilizando una embedding_function (obtenida a través de
         get_embedding_function en open_webui/retrieval/utils.py), que puede interactuar con diferentes motores de embedding como Ollama, OpenAI o Azure OpenAI. Los embeddings capturan el significado semántico
         del texto, permitiendo búsquedas basadas en la similitud conceptual.
       * Almacenamiento en Base de Datos Vectorial: Los chunks resultantes (que incluyen el texto original, su embedding y metadatos relevantes como el ID del archivo, nombre, hash, etc.) se insertan en
         colecciones específicas dentro de la base de datos vectorial (VECTOR_DB_CLIENT, cuya interfaz se define en open_webui/retrieval/vector/main.py). Las colecciones pueden ser dedicadas a archivos
         individuales (ej., file-{file_id}) o a bases de conocimiento más amplias.

  4. Proceso de Recuperación

  Cuando un usuario interactúa con el chat, el sistema inicia un proceso de recuperación para identificar y extraer la información más relevante que pueda ayudar al LLM a formular una respuesta informada.

   * Generación de Consultas (`generate_queries`):
       * Dentro de open_webui/utils/middleware.py, la función chat_completion_files_handler es la encargada de iniciar la fase de recuperación. Primero, utiliza generate_queries (una función que probablemente
         invoca a un LLM auxiliar) para expandir o refinar la consulta original del usuario en una o varias consultas de búsqueda más efectivas. Esto ayuda a capturar la intención del usuario de manera más
         precisa. Si no se generan consultas, se utiliza el mensaje original del usuario como consulta.

   * Recuperación de Fuentes (`get_sources_from_items` en `open_webui/retrieval/utils.py`):
       * Esta es la función central que toma las consultas generadas y una lista de items (que pueden ser archivos subidos por el usuario, notas, colecciones de conocimiento o resultados de búsqueda web). Su
         objetivo es buscar y recuperar los documentos o fragmentos de documentos más relevantes de la base de datos vectorial.
       * Tipos de Búsqueda:
           * Búsqueda Estándar (`query_collection`): Realiza una búsqueda de similitud vectorial directa. Calcula el embedding de la consulta y busca los k documentos más cercanos en el espacio vectorial.
           * Búsqueda Híbrida (`query_collection_with_hybrid_search`): Si la configuración ENABLE_RAG_HYBRID_SEARCH está activada, esta función combina dos enfoques de búsqueda para una recuperación más
             robusta:
               * Búsqueda por Similitud Vectorial (Semántica): Utiliza los embeddings para encontrar documentos conceptualmente similares a la consulta.
               * Búsqueda por Palabras Clave (BM25): Realiza una búsqueda tradicional basada en la frecuencia de términos, útil para capturar coincidencias exactas de palabras clave.
              La combinación se realiza mediante EnsembleRetriever de Langchain, que permite ponderar la importancia de cada tipo de búsqueda. Si la búsqueda híbrida falla, el sistema puede recurrir a la
  búsqueda estándar.
       * Re-ranking (`RerankCompressor`): Después de la recuperación inicial, los documentos obtenidos pueden pasar por un paso de re-ranking. La reranking_function (configurada en
         open_webui/routers/retrieval.py) evalúa la relevancia de los documentos recuperados en relación

ℹ Request cancelled.
 

╭─────────────────────────────────────────────────────────────────────────────────────────────────────╮
│  > no pero me refiero a un documento real formato markdown . ponlo en la carpeta raiz del proyecto  │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────╯

✦ Entendido. Generaré un informe completo en formato Markdown y lo guardaré en la carpeta raíz del proyecto.

  Aquí está el contenido del informe:

    1 # Informe de Gestión del Contexto RAG en Open WebUI
    2 
    3 ## 1. Introducción
    4 
    5 La Generación Aumentada por Recuperación (RAG) es una técnica crucial en sistemas de IA conversacionales que permite a los Large Language Models (LLM) acceder y utilizar información externa para
      generar respuestas más precisas, relevantes y actualizadas. En el proyecto Open WebUI, la gestión del contexto RAG es fundamental para enriquecer las interacciones del chat, permitiendo que el LLM
      responda preguntas basadas no solo en su conocimiento pre-entrenado, sino también en documentos específicos proporcionados por el usuario o en bases de conocimiento preexistentes.
    6 
    7 ## 2. Arquitectura General de RAG
    8 
    9 La arquitectura RAG en Open WebUI se compone de varios módulos interconectados que trabajan en conjunto para:
   10 *   **Ingesta de Documentos:** Procesar y preparar datos de diversas fuentes.
   11 *   **Almacenamiento Vectorial:** Guardar representaciones numéricas (embeddings) de los documentos para una búsqueda eficiente.
   12 *   **Recuperación:** Buscar y seleccionar los fragmentos de información más relevantes para una consulta dada.
   13 *   **Preparación del Contexto:** Formatear la información recuperada y fusionarla con la consulta del usuario para el LLM.
   14 
   15 Los componentes clave identificados son:
   16 *   **`open_webui.retrieval.loaders.main.py`**: Maneja la carga de documentos de diferentes tipos.
   17 *   **`open_webui.retrieval.vector.main.py`**: Define la interfaz para la interacción con bases de datos vectoriales.
   18 *   **`open_webui.routers.retrieval.py`**: Expone las APIs para el procesamiento de documentos y la configuración de RAG.
   19 *   **`open_webui.utils.middleware.py`**: Actúa como un "middleware" en el flujo del chat, donde se orquesta la recuperación de RAG y la preparación del contexto.
   20 *   **`open_webui.retrieval.utils.py`**: Contiene las funciones centrales para la consulta y recuperación de documentos de la base de datos vectorial.
   21 *   **`open_webui.utils.chat.py`**: Gestiona la lógica de finalización del chat y delega la preparación del contexto al middleware.
   22 
   23 ## 3. Ingesta de Documentos
   24 
   25 La ingesta de documentos es el primer paso en el proceso RAG, donde los datos brutos se transforman en un formato que puede ser buscado y utilizado por el LLM.
   26 
   27 *   **Fuentes de Documentos:**
   28     *   **Archivos Subidos por el Usuario:** A través de la ruta `/process/file` en `retrieval.py`, los usuarios pueden subir archivos (PDFs, documentos de texto, etc.). La clase `Loader` en
      `loaders/main.py` es la encargada de extraer el contenido de estos archivos, utilizando diversas herramientas y APIs externas (Tika, Datalab Marker, Docling, etc.) para manejar diferentes formatos
      y realizar OCR si es necesario.
   29     *   **Texto Directo:** La ruta `/process/text` permite la ingesta de texto plano directamente.
   30     *   **Contenido Web/YouTube:** Las rutas `/process/web` y `/process/youtube` permiten procesar URLs, extrayendo el contenido de páginas web o transcripciones de videos.
   31     *   **Bases de Conocimiento del Modelo:** Los modelos pueden tener bases de conocimiento predefinidas asociadas, que son colecciones de documentos ya procesados y almacenados en la base de
      datos vectorial.
   32 
   33 *   **Procesamiento Común (`save_docs_to_vector_db` en `retrieval.py`):**
   34     *   Todos los tipos de contenido ingestado pasan por esta función para su preparación:
   35         *   **Chunking (División en Fragmentos):** Los documentos grandes se dividen en fragmentos más pequeños (`chunks`) para adaptarse a la ventana de contexto del LLM. Se utilizan diferentes
      estrategias de división (`RecursiveCharacterTextSplitter`, `TokenTextSplitter`, `MarkdownHeaderTextSplitter`) configurables a través de `TEXT_SPLITTER`, `CHUNK_SIZE` y `CHUNK_OVERLAP`.
   36         *   **Embedding (Vectorización):** Cada `chunk` de texto se convierte en un vector numérico (embedding) utilizando una `embedding_function` (definida en `retrieval/utils.py`). Esta función
      puede interactuar con diferentes motores de embedding (Ollama, OpenAI, Azure OpenAI) configurados en el sistema.
   37         *   **Almacenamiento en Base de Datos Vectorial:** Los `chunks` (texto original, su embedding y metadatos relevantes como `file_id`, `name`, `hash`) se insertan en colecciones específicas
      dentro de la base de datos vectorial (`VECTOR_DB_CLIENT`). Las colecciones pueden ser por archivo (`file-{file_id}`) o bases de conocimiento generales.
   38 
   39 ### 4. Proceso de Recuperación
   40 
   41 Cuando un usuario realiza una consulta en el chat, el sistema inicia un proceso de recuperación para encontrar la información más relevante.
   42 
   43 *   **Generación de Consultas (`generate_queries`):**
   44     *   En `middleware.py`, la función `chat_completion_files_handler` utiliza `generate_queries` (una función que probablemente invoca a un LLM) para expandir o refinar la consulta original del
      usuario en una o varias consultas de búsqueda más efectivas. Si no se generan consultas, se utiliza el mensaje original del usuario.
   45 
   46 *   **Recuperación de Fuentes (`get_sources_from_items` en `retrieval/utils.py`):**
   47     *   Esta es la función central que toma las consultas generadas y las `items` (archivos de usuario, bases de conocimiento, etc.) y realiza la búsqueda en la base de datos vectorial.
   48     *   **Tipos de Búsqueda:**
   49         *   **Búsqueda Estándar (`query_collection`):** Realiza una búsqueda de similitud vectorial directa. Calcula el embedding de la consulta y busca los `k` documentos más cercanos en el
      espacio vectorial.
   50         *   **Búsqueda Híbrida (`query_collection_with_hybrid_search`):** Si `ENABLE_RAG_HYBRID_SEARCH` está activado, combina la búsqueda por similitud vectorial (semántica) con la búsqueda por
      palabras clave (BM25). Esto permite capturar tanto la relevancia conceptual como la coincidencia exacta de términos. Utiliza `EnsembleRetriever` de Langchain para combinar los resultados de ambos
      tipos de búsqueda.
   51     *   **Re-ranking (`RerankCompressor`):** Después de la recuperación inicial, los documentos pueden pasar por un paso de re-ranking. La `reranking_function` (configurada en `retrieval.py`)
      evalúa la relevancia de los documentos recuperados en relación con la consulta, asignando una puntuación. Solo los `TOP_K_RERANKER` documentos con la puntuación más alta que superen un
      `RELEVANCE_THRESHOLD` se seleccionan para el contexto final. Esto mejora la calidad del contexto proporcionado al LLM.
   52 
   53 ### 5. Preparación del Contexto para el LLM
   54 
   55 Una vez que se han recuperado los fragmentos de información más relevantes, se preparan para ser inyectados en el prompt del LLM.
   56 
   57 *   **Construcción del `context_string`:**
   58     *   En `middleware.py`, los `sources` recuperados se utilizan para construir una cadena de texto formateada llamada `context_string`. Cada fragmento de documento se envuelve en etiquetas
      `<source id="..." name="...">...</source>`, donde el `id` permite la citación y el `name` proporciona una referencia legible.
   59     *   Esto asegura que el LLM reciba el contenido de los documentos de manera estructurada y pueda identificar de dónde proviene cada pieza de información.
   60 
   61 *   **Aplicación de la Plantilla RAG (`rag_template`):**
   62     *   El `context_string` y el mensaje original del usuario (`prompt`) se pasan a la función `rag_template` (definida en `open_webui.utils.task.py`).
   63     *   Esta función utiliza una plantilla predefinida (`RAG_TEMPLATE` en la configuración) para combinar el contexto recuperado con la consulta del usuario. La plantilla define cómo se presenta el
      contexto al LLM, típicamente incluyendo instrucciones sobre cómo usar el contexto y dónde insertarlo.
   64 
   65 *   **Inyección en los Mensajes del LLM:**
   66     *   El prompt final, que ahora contiene el contexto RAG, se inyecta en la lista de mensajes que se enviará al LLM.
   67     *   Para la mayoría de los modelos, esto se hace añadiendo o actualizando un mensaje de sistema (`add_or_update_system_message`) con el prompt contextualizado.
   68     *   Para los modelos de Ollama, se utiliza un "workaround" (`prepend_to_first_user_message_content`) que antepone el contexto directamente al primer mensaje del usuario, debido a las
      particularidades de cómo Ollama maneja los prompts del sistema.
   69 
   70 *   **`RAG_FULL_CONTEXT`:**
   71     *   La configuración `RAG_FULL_CONTEXT` permite que, en ciertos casos, se incluya el contenido completo de los documentos en el contexto del LLM, en lugar de solo los fragmentos más relevantes.
      Esto es útil para documentos pequeños o cuando se requiere una comprensión exhaustiva, pero debe usarse con precaución para evitar exceder los límites de tokens del LLM.
   72 
   73 ## 6. Anexo: Contenido Completo de las Funciones Clave
   74 
   75 ### `open_webui/retrieval/loaders/main.py`
  import requests
  import logging
  import ftfy
  import sys
  import json

  from langchain_community.document_loaders import (
      AzureAIDocumentIntelligenceLoader,
      BSHTMLLoader,
      CSVLoader,
      Docx2txtLoader,
      OutlookMessageLoader,
      PyPDFLoader,
      TextLoader,
      UnstructuredEPubLoader,
      UnstructuredExcelLoader,
      UnstructuredODTLoader,
      UnstructuredPowerPointLoader,
      UnstructuredRSTLoader,
      UnstructuredXMLLoader,
      YoutubeLoader,
  )
  from langchain_core.documents import Document

  from open_webui.retrieval.loaders.external_document import ExternalDocumentLoader

  from open_webui.retrieval.loaders.mistral import MistralLoader
  from open_webui.retrieval.loaders.datalab_marker import DatalabMarkerLoader

  from open_webui.env import SRC_LOG_LEVELS, GLOBAL_LOG_LEVEL

  logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
  log = logging.getLogger(__name__)
  log.setLevel(SRC_LOG_LEVELS["RAG"])

  known_source_ext = [
      "go",
      "py",
      "java",
      "sh",
      "bat",
      "ps1",
      "cmd",
      "js",
      "ts",
      "css",
      "cpp",
      "hpp",
      "h",
      "c",
      "cs",
      "sql",
      "log",
      "ini",
      "pl",
      "pm",
      "r",
      "dart",
      "dockerfile",
      "env",
      "php",
      "hs",
      "hsc",
      "lua",
      "nginxconf",
      "conf",
      "m",
      "mm",
      "plsql",
      "perl",
      "rb",
      "rs",
      "db2",
      "scala",
      "bash",
      "swift",
      "vue",
      "svelte",
      "ex",
      "exs",
      "erl",
      "tsx",
      "jsx",
      "hs",
      "lhs",
      "json",
  ]

  class TikaLoader:
      def __init__(self, url, file_path, mime_type=None, extract_images=None):
          self.url = url
          self.file_path = file_path
          self.mime_type = mime_type

          self.extract_images = extract_images

      def load(self) -> list[Document]:
          with open(self.file_path, "rb") as f:
              data = f.read()

          if self.mime_type is not None:
              headers = {"Content-Type": self.mime_type}
          else:
              headers = {}

          if self.extract_images == True:
              headers["X-Tika-PDFextractInlineImages"] = "true"

          endpoint = self.url
          if not endpoint.endswith("/"):
              endpoint += "/"
          endpoint += "tika/text"

          r = requests.put(endpoint, data=data, headers=headers)

          if r.ok:
              raw_metadata = r.json()
              text = raw_metadata.get("X-TIKA:content", "<No text content found>").strip()

              if "Content-Type" in raw_metadata:
                  headers["Content-Type"] = raw_metadata["Content-Type"]

              log.debug("Tika extracted text: %s", text)

              return [Document(page_content=text, metadata=headers)]
          else:
              raise Exception(f"Error calling Tika: {r.reason}")

  class DoclingLoader:
      def __init__(self, url, file_path=None, mime_type=None, params=None):
          self.url = url.rstrip("/")
          self.file_path = file_path
          self.mime_type = mime_type

          self.params = params or {}

      def load(self) -> list[Document]:
          with open(self.file_path, "rb") as f:
              files = {
                  "files": (
                      self.file_path,
                      f,
                      self.mime_type or "application/octet-stream",
                  )
              }

              params = {"image_export_mode": "placeholder", "table_mode": "accurate"}

              if self.params:
                  if self.params.get("do_picture_description"):
                      params["do_picture_description"] = self.params.get(
                          "do_picture_description"
                      )

                      picture_description_mode = self.params.get(
                          "picture_description_mode", ""
                      ).lower()

                      if picture_description_mode == "local" and self.params.get(
                          "picture_description_local", {}
                      ):
                          params["picture_description_local"] = json.dumps(
                              self.params.get("picture_description_local", {})
                          )

                      elif picture_description_mode == "api" and self.params.get(
                          "picture_description_api", {}
                      ):
                          params["picture_description_api"] = json.dumps(
                              self.params.get("picture_description_api", {})
                          )

                  if self.params.get("ocr_engine") and self.params.get("ocr_lang"):
                      params["ocr_engine"] = self.params.get("ocr_engine")
                      params["ocr_lang"] = [
                          lang.strip()
                          for lang in self.params.get("ocr_lang").split(",")
                          if lang.strip()
                      ]

              endpoint = f"{self.url}/v1alpha/convert/file"
              r = requests.post(endpoint, files=files, data=params)

          if r.ok:
              result = r.json()
              document_data = result.get("document", {})
              text = document_data.get("md_content", "<No text content found>")

              metadata = {"Content-Type": self.mime_type} if self.mime_type else {}

              log.debug("Docling extracted text: %s", text)

              return [Document(page_content=text, metadata=metadata)]
          else:
              error_msg = f"Error calling Docling API: {r.reason}"
              if r.text:
                  try:
                      error_data = r.json()
                      if "detail" in error_data:
                          error_msg += f" - {error_data['detail']}"
                  except Exception:
                      error_msg += f" - {r.text}"
              raise Exception(f"Error calling Docling: {error_msg}")

  class Loader:
      def __init__(self, engine: str = "", **kwargs):
          self.engine = engine
          self.kwargs = kwargs

      def load(
          self, filename: str, file_content_type: str, file_path: str
      ) -> list[Document]:
          loader = self._get_loader(filename, file_content_type, file_path)
          docs = loader.load()

          return [
              Document(
                  page_content=ftfy.fix_text(doc.page_content), metadata=doc.metadata
              )
              for doc in docs
          ]

      def _is_text_file(self, file_ext: str, file_content_type: str) -> bool:
          return file_ext in known_source_ext or (
              file_content_type
              and file_content_type.find("text/") >= 0
  Avoid text/html files being detected as text
              and not file_content_type.find("html") >= 0
          )

      def _get_loader(self, filename: str, file_content_type: str, file_path: str):
          file_ext = filename.split(".")[-1].lower()

          if (
              self.engine == "external"
              and self.kwargs.get("EXTERNAL_DOCUMENT_LOADER_URL")
              and self.kwargs.get("EXTERNAL_DOCUMENT_LOADER_API_KEY")
          ):
              loader = ExternalDocumentLoader(
                  file_path=file_path,
                  url=self.kwargs.get("EXTERNAL_DOCUMENT_LOADER_URL"),
                  api_key=self.kwargs.get("EXTERNAL_DOCUMENT_LOADER_API_KEY"),
                  mime_type=file_content_type,
              )
          elif self.engine == "tika" and self.kwargs.get("TIKA_SERVER_URL"):
              if self._is_text_file(file_ext, file_content_type):
                  loader = TextLoader(file_path, autodetect_encoding=True)
              else:
                  loader = TikaLoader(
                      url=self.kwargs.get("TIKA_SERVER_URL"),
                      file_path=file_path,
                      mime_type=file_content_type,
                      extract_images=self.kwargs.get("PDF_EXTRACT_IMAGES"),
                  )
          elif (
              self.engine == "datalab_marker"
              and self.kwargs.get("DATALAB_MARKER_API_KEY")
              and file_ext
              in [
                  "pdf",
                  "xls",
                  "xlsx",
                  "ods",
                  "doc",
                  "docx",
                  "odt",
                  "ppt",
                  "pptx",
                  "odp",
                  "html",
                  "epub",
                  "png",
                  "jpeg",
                  "jpg",
                  "webp",
                  "gif",
                  "tiff",
              ]
          ):
              loader = DatalabMarkerLoader(
                  file_path=file_path,
                  api_key=self.kwargs["DATALAB_MARKER_API_KEY"],
                  langs=self.kwargs.get("DATALAB_MARKER_LANGS"),
                  use_llm=self.kwargs.get("DATALAB_MARKER_USE_LLM", False),
                  skip_cache=self.kwargs.get("DATALAB_MARKER_SKIP_CACHE", False),
                  force_ocr=self.kwargs.get("DATALAB_MARKER_FORCE_OCR", False),
                  paginate=self.kwargs.get("DATALAB_MARKER_PAGINATE", False),
                  strip_existing_ocr=self.kwargs.get(
                      "DATALAB_MARKER_STRIP_EXISTING_OCR", False
                  ),
                  disable_image_extraction=self.kwargs.get(
                      "DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION", False
                  ),
                  output_format=self.kwargs.get(
                      "DATALAB_MARKER_OUTPUT_FORMAT", "markdown"
                  ),
              )
          elif self.engine == "docling" and self.kwargs.get("DOCLING_SERVER_URL"):
              if self._is_text_file(file_ext, file_content_type):
                  loader = TextLoader(file_path, autodetect_encoding=True)
              else:
  Build params for DoclingLoader
                  params = self.kwargs.get("DOCLING_PARAMS", {})
                  if not isinstance(params, dict):
                      try:
                          params = json.loads(params)
                      except json.JSONDecodeError:
                          log.error("Invalid DOCLING_PARAMS format, expected JSON object")
                          params = {}

                  loader = DoclingLoader(
                      url=self.kwargs.get("DOCLING_SERVER_URL"),
                      file_path=file_path,
                      mime_type=file_content_type,
                      params=params,
                  )
          elif (
              self.engine == "document_intelligence"
              and self.kwargs.get("DOCUMENT_INTELLIGENCE_ENDPOINT") != ""
              and self.kwargs.get("DOCUMENT_INTELLIGENCE_KEY") != ""
              and (
                  file_ext in ["pdf", "xls", "xlsx", "docx", "ppt", "pptx"]
                  or file_content_type
                  in [
                      "application/vnd.ms-excel",
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                      "application/vnd.ms-powerpoint",
                      "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                  ]
              )
          ):
              loader = AzureAIDocumentIntelligenceLoader(
                  file_path=file_path,
                  api_endpoint=self.kwargs.get("DOCUMENT_INTELLIGENCE_ENDPOINT"),
                  api_key=self.kwargs.get("DOCUMENT_INTELLIGENCE_KEY"),
              )
          elif (
              self.engine == "mistral_ocr"
              and self.kwargs.get("MISTRAL_OCR_API_KEY") != ""
              and file_ext
              in ["pdf"]  # Mistral OCR currently only supports PDF and images
          ):
              loader = MistralLoader(
                  api_key=self.kwargs.get("MISTRAL_OCR_API_KEY"), file_path=file_path
              )
          elif (
              self.engine == "external"
              and self.kwargs.get("MISTRAL_OCR_API_KEY") != ""
              and file_ext
              in ["pdf"]  # Mistral OCR currently only supports PDF and images
          ):
              loader = MistralLoader(
                  api_key=self.kwargs.get("MISTRAL_OCR_API_KEY"), file_path=file_path
              )
          else:
              if file_ext == "pdf":
                  loader = PyPDFLoader(
                      file_path, extract_images=self.kwargs.get("PDF_EXTRACT_IMAGES")
                  )
              elif file_ext == "csv":
                  loader = CSVLoader(file_path, autodetect_encoding=True)
              elif file_ext == "rst":
                  loader = UnstructuredRSTLoader(file_path, mode="elements")
              elif file_ext == "xml":
                  loader = UnstructuredXMLLoader(file_path)
              elif file_ext in ["htm", "html"]:
                  loader = BSHTMLLoader(file_path, open_encoding="unicode_escape")
              elif file_ext == "md":
                  loader = TextLoader(file_path, autodetect_encoding=True)
              elif file_content_type == "application/epub+zip":
                  loader = UnstructuredEPubLoader(file_path)
              elif (
                  file_content_type
                  == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                  or file_ext == "docx"
              ):
                  loader = Docx2txtLoader(file_path)
              elif file_content_type in [
                  "application/vnd.ms-excel",
                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
              ] or file_ext in ["xls", "xlsx"]:
                  loader = UnstructuredExcelLoader(file_path)
              elif file_content_type in [
                  "application/vnd.ms-powerpoint",
                  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
              ] or file_ext in ["ppt", "pptx"]:
                  loader = UnstructuredPowerPointLoader(file_path)
              elif file_ext == "msg":
                  loader = OutlookMessageLoader(file_path)
              elif file_ext == "odt":
                  loader = UnstructuredODTLoader(file_path)
              elif self._is_text_file(file_ext, file_content_type):
                  loader = TextLoader(file_path, autodetect_encoding=True)
              else:
                  loader = TextLoader(file_path, autodetect_encoding=True)

          return loader

   1 
   2 ### `open_webui/retrieval/vector/main.py`
  from pydantic import BaseModel
  from abc import ABC, abstractmethod
  from typing import Any, Dict, List, Optional, Union

  class VectorItem(BaseModel):
      id: str
      text: str
      vector: List[float | int]
      metadata: Any

  class GetResult(BaseModel):
      ids: Optional[List[List[str]]]
      documents: Optional[List[List[str]]]
      metadatas: Optional[List[List[Any]]]

  class SearchResult(GetResult):
      distances: Optional[List[List[float | int]]]

  class VectorDBBase(ABC):
      """
      Abstract base class for all vector database backends.

      Implementations of this class provide methods for collection management,
      vector insertion, deletion, similarity search, and metadata filtering.

      Any custom vector database integration must inherit from this class and
      implement all abstract methods.
      """

      @abstractmethod
      def has_collection(self, collection_name: str) -> bool:
          """Check if the collection exists in the vector DB."""
          pass

      @abstractmethod
      def delete_collection(self, collection_name: str) -> None:
          """Delete a collection from the vector DB."""
          pass

      @abstractmethod
      def insert(self, collection_name: str, items: List[VectorItem]) -> None:
          """Insert a list of vector items into a collection."""
          pass

      @abstractmethod
      def upsert(self, collection_name: str, items: List[VectorItem]) -> None:
          """Insert or update vector items in a collection."""
          pass

      @abstractmethod
      def search(
          self, collection_name: str, vectors: List[List[Union[float, int]]], limit: int
      ) -> Optional[SearchResult]:
          """Search for similar vectors in a collection."""
          pass

      @abstractmethod
      def query(
          self, collection_name: str, filter: Dict, limit: Optional[int] = None
      ) -> Optional[GetResult]:
          """Query vectors from a collection using metadata filter."""
          pass

      @abstractmethod
      def get(self, collection_name: str) -> Optional[GetResult]:
          """Retrieve all vectors from a collection."""
          pass

      @abstractmethod
      def delete(
          self,
          collection_name: str,
          ids: Optional[List[str]] = None,
          filter: Optional[Dict] = None,
      ) -> None:
          """Delete vectors by ID or filter from a collection."""
          pass

      @abstractmethod
      def reset(self) -> None:
          """Reset the vector database by removing all collections or those matching a condition."""
          pass

   1 
   2 ### `open_webui/routers/retrieval.py` (Funciones relevantes)
  import json
  import logging
  import mimetypes
  import os
  import shutil
  import asyncio

  import uuid
  from datetime import datetime
  from pathlib import Path
  from typing import Iterator, List, Optional, Sequence, Union

  from fastapi import (
      Depends,
      FastAPI,
      File,
      Form,
      HTTPException,
      UploadFile,
      Request,
      status,
      APIRouter,
  )
  from fastapi.middleware.cors import CORSMiddleware
  from fastapi.concurrency import run_in_threadpool
  from pydantic import BaseModel
  import tiktoken

  from langchain.text_splitter import RecursiveCharacterTextSplitter, TokenTextSplitter
  from langchain_text_splitters import MarkdownHeaderTextSplitter
  from langchain_core.documents import Document

  from open_webui.models.files import FileModel, Files
  from open_webui.models.knowledge import Knowledges
  from open_webui.storage.provider import Storage

  from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT

  Document loaders
  from open_webui.retrieval.loaders.main import Loader
  from open_webui.retrieval.loaders.youtube import YoutubeLoader

  Web search engines
  from open_webui.retrieval.web.main import SearchResult
  from open_webui.retrieval.web.utils import get_web_loader
  from open_webui.retrieval.web.brave import search_brave
  from open_webui.retrieval.web.kagi import search_kagi
  from open_webui.retrieval.web.mojeek import search_mojeek
  from open_webui.retrieval.web.bocha import search_bocha
  from open_webui.retrieval.web.duckduckgo import search_duckduckgo
  from open_webui.retrieval.web.google_pse import search_google_pse
  from open_webui.retrieval.web.jina_search import search_jina
  from open_webui.retrieval.web.searchapi import search_searchapi
  from open_webui.retrieval.web.serpapi import search_serpapi
  from open_webui.retrieval.web.searxng import search_searxng
  from open_webui.retrieval.web.yacy import search_yacy
  from open_webui.retrieval.web.serper import search_serper
  from open_webui.retrieval.web.serply import search_serply
  from open_webui.retrieval.web.serpstack import search_serpstack
  from open_webui.retrieval.web.tavily import search_tavily
  from open_webui.retrieval.web.bing import search_bing
  from open_webui.retrieval.web.exa import search_exa
  from open_webui.retrieval.web.perplexity import search_perplexity
  from open_webui.retrieval.web.sougou import search_sougou
  from open_webui.retrieval.web.firecrawl import search_firecrawl
  from open_webui.retrieval.web.external import search_external

  from open_webui.retrieval.utils import (
      get_embedding_function,
      get_reranking_function,
      get_model_path,
      query_collection,
      query_collection_with_hybrid_search,
      query_doc,
      query_doc_with_hybrid_search,
  )
  from open_webui.utils.misc import (
      calculate_sha256_string,
  )
  from open_webui.utils.auth import get_admin_user, get_verified_user

  from open_webui.config import (
      ENV,
      RAG_EMBEDDING_MODEL_AUTO_UPDATE,
      RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
      RAG_RERANKING_MODEL_AUTO_UPDATE,
      RAG_RERANKING_MODEL_TRUST_REMOTE_CODE,
      UPLOAD_DIR,
      DEFAULT_LOCALE,
      RAG_EMBEDDING_CONTENT_PREFIX,
      RAG_EMBEDDING_QUERY_PREFIX,
  )
  from open_webui.env import (
      SRC_LOG_LEVELS,
      DEVICE_TYPE,
      DOCKER,
      SENTENCE_TRANSFORMERS_BACKEND,
      SENTENCE_TRANSFORMERS_MODEL_KWARGS,
      SENTENCE_TRANSFORMERS_CROSS_ENCODER_BACKEND,
      SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS,
  )

  from open_webui.constants import ERROR_MESSAGES

  log = logging.getLogger(__name__)
  log.setLevel(SRC_LOG_LEVELS["RAG"])

  ##########################################
  #
  Utility functions
  #
  ##########################################

  def get_ef(
      engine: str,
      embedding_model: str,
      auto_update: bool = False,
  ):
      ef = None
      if embedding_model and engine == "":
          from sentence_transformers import SentenceTransformer

          try:
              ef = SentenceTransformer(
                  get_model_path(embedding_model, auto_update),
                  device=DEVICE_TYPE,
                  trust_remote_code=RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
                  backend=SENTENCE_TRANSFORMERS_BACKEND,
                  model_kwargs=SENTENCE_TRANSFORMERS_MODEL_KWARGS,
              )
          except Exception as e:
              log.debug(f"Error loading SentenceTransformer: {e}")

      return ef

  def get_rf(
      engine: str = "",
      reranking_model: Optional[str] = None,
      external_reranker_url: str = "",
      external_reranker_api_key: str = "",
      auto_update: bool = False,
  ):
      rf = None
      if reranking_model:
          if any(model in reranking_model for model in ["jinaai/jina-colbert-v2"]):
              try:
                  from open_webui.retrieval.models.colbert import ColBERT

                  rf = ColBERT(
                      get_model_path(reranking_model, auto_update),
                      env="docker" if DOCKER else None,
                  )

              except Exception as e:
                  log.error(f"ColBERT: {e}")
                  raise Exception(ERROR_MESSAGES.DEFAULT(e))
          else:
              if engine == "external":
                  try:
                      from open_webui.retrieval.models.external import ExternalReranker

                      rf = ExternalReranker(
                          url=external_reranker_url,
                          api_key=external_reranker_api_key,
                          model=reranking_model,
                      )
                  except Exception as e:
                      log.error(f"ExternalReranking: {e}")
                      raise Exception(ERROR_MESSAGES.DEFAULT(e))
              else:
                  import sentence_transformers

                  try:
                      rf = sentence_transformers.CrossEncoder(
                          get_model_path(reranking_model, auto_update),
                          device=DEVICE_TYPE,
                          trust_remote_code=RAG_RERANKING_MODEL_TRUST_REMOTE_CODE,
                          backend=SENTENCE_TRANSFORMERS_CROSS_ENCODER_BACKEND,
                          model_kwargs=SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS,
                      )
                  except Exception as e:
                      log.error(f"CrossEncoder: {e}")
                      raise Exception(ERROR_MESSAGES.DEFAULT("CrossEncoder error"))

      return rf

  ##########################################
  #
  API routes
  #
  ##########################################

  router = APIRouter()

  class CollectionNameForm(BaseModel):
      collection_name: Optional[str] = None

  class ProcessUrlForm(CollectionNameForm):
      url: str

  class SearchForm(BaseModel):
      queries: List[str]

  @router.get("/")
  async def get_status(request: Request):
      return {
          "status": True,
          "chunk_size": request.app.state.config.CHUNK_SIZE,
          "chunk_overlap": request.app.state.config.CHUNK_OVERLAP,
          "template": request.app.state.config.RAG_TEMPLATE,
          "embedding_engine": request.app.state.config.RAG_EMBEDDING_ENGINE,
          "embedding_model": request.app.state.config.RAG_EMBEDDING_MODEL,
          "reranking_model": request.app.state.config.RAG_RERANKING_MODEL,
          "embedding_batch_size": request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
      }

  @router.get("/embedding")
  async def get_embedding_config(request: Request, user=Depends(get_admin_user)):
      return {
          "status": True,
          "embedding_engine": request.app.state.config.RAG_EMBEDDING_ENGINE,
          "embedding_model": request.app.state.config.RAG_EMBEDDING_MODEL,
          "embedding_batch_size": request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
          "openai_config": {
              "url": request.app.state.config.RAG_OPENAI_API_BASE_URL,
              "key": request.app.state.config.RAG_OPENAI_API_KEY,
          },
          "ollama_config": {
              "url": request.app.state.config.RAG_OLLAMA_BASE_URL,
              "key": request.app.state.config.RAG_OLLAMA_API_KEY,
          },
          "azure_openai_config": {
              "url": request.app.state.config.RAG_AZURE_OPENAI_BASE_URL,
              "key": request.app.state.config.RAG_AZURE_OPENAI_API_KEY,
              "version": request.app.state.config.RAG_AZURE_OPENAI_API_VERSION,
          },
      }

  class OpenAIConfigForm(BaseModel):
      url: str
      key: str

  class OllamaConfigForm(BaseModel):
      url: str
      key: str

  class AzureOpenAIConfigForm(BaseModel):
      url: str
      key: str
      version: str

  class EmbeddingModelUpdateForm(BaseModel):
      openai_config: Optional[OpenAIConfigForm] = None
      ollama_config: Optional[OllamaConfigForm] = None
      azure_openai_config: Optional[AzureOpenAIConfigForm] = None
      embedding_engine: str
      embedding_model: str
      embedding_batch_size: Optional[int] = 1

  @router.post("/embedding/update")
  async def update_embedding_config(
      request: Request, form_data: EmbeddingModelUpdateForm, user=Depends(get_admin_user)
  ):
      log.info(
          f"Updating embedding model: {request.app.state.config.RAG_EMBEDDING_MODEL} to {form_data.embedding_model}"
      )
      try:
          request.app.state.config.RAG_EMBEDDING_ENGINE = form_data.embedding_engine
          request.app.state.config.RAG_EMBEDDING_MODEL = form_data.embedding_model

          if request.app.state.config.RAG_EMBEDDING_ENGINE in [
              "ollama",
              "openai",
              "azure_openai",
          ]:
              if form_data.openai_config is not None:
                  request.app.state.config.RAG_OPENAI_API_BASE_URL = (
                      form_data.openai_config.url
                  )
                  request.app.state.config.RAG_OPENAI_API_KEY = (
                      form_data.openai_config.key
                  )

              if form_data.ollama_config is not None:
                  request.app.state.config.RAG_OLLAMA_BASE_URL = (
                      form_data.ollama_config.url
                  )
                  request.app.state.config.RAG_OLLAMA_API_KEY = (
                      form_data.ollama_config.key
                  )

              if form_data.azure_openai_config is not None:
                  request.app.state.config.RAG_AZURE_OPENAI_BASE_URL = (
                      form_data.azure_openai_config.url
                  )
                  request.app.state.config.RAG_AZURE_OPENAI_API_KEY = (
                      form_data.azure_openai_config.key
                  )
                  request.app.state.config.RAG_AZURE_OPENAI_API_VERSION = (
                      form_data.azure_openai_config.version
                  )

              request.app.state.config.RAG_EMBEDDING_BATCH_SIZE = (
                  form_data.embedding_batch_size
              )

          request.app.state.ef = get_ef(
              request.app.state.config.RAG_EMBEDDING_ENGINE,
              request.app.state.config.RAG_EMBEDDING_MODEL,
          )

          request.app.state.EMBEDDING_FUNCTION = get_embedding_function(
              request.app.state.config.RAG_EMBEDDING_ENGINE,
              request.app.state.config.RAG_EMBEDDING_MODEL,
              request.app.state.ef,
              (
                  request.app.state.config.RAG_OPENAI_API_BASE_URL
                  if request.app.state.config.RAG_EMBEDDING_ENGINE == "openai"
                  else (
                      request.app.state.config.RAG_OLLAMA_BASE_URL
                      if request.app.state.config.RAG_EMBEDDING_ENGINE == "ollama"
                      else request.app.state.config.RAG_AZURE_OPENAI_BASE_URL
                  )
              ),
              (
                  request.app.state.config.RAG_OPENAI_API_KEY
                  if request.app.state.config.RAG_EMBEDDING_ENGINE == "openai"
                  else (
                      request.app.state.config.RAG_OLLAMA_API_KEY
                      if request.app.state.config.RAG_EMBEDDING_ENGINE == "ollama"
                      else request.app.state.config.RAG_AZURE_OPENAI_API_KEY
                  )
              ),
              request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
              azure_api_version=(
                  request.app.state.config.RAG_AZURE_OPENAI_API_VERSION
                  if request.app.state.config.RAG_EMBEDDING_ENGINE == "azure_openai"
                  else None
              ),
          )

          return {
              "status": True,
              "embedding_engine": request.app.state.config.RAG_EMBEDDING_ENGINE,
              "embedding_model": request.app.state.config.RAG_EMBEDDING_MODEL,
              "embedding_batch_size": request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
              "openai_config": {
                  "url": request.app.state.config.RAG_OPENAI_API_BASE_URL,
                  "key": request.app.state.config.RAG_OPENAI_API_KEY,
              },
              "ollama_config": {
                  "url": request.app.state.config.RAG_OLLAMA_BASE_URL,
                  "key": request.app.state.config.RAG_OLLAMA_API_KEY,
              },
              "azure_openai_config": {
                  "url": request.app.state.config.RAG_AZURE_OPENAI_BASE_URL,
                  "key": request.app.state.config.RAG_AZURE_OPENAI_API_KEY,
                  "version": request.app.state.config.RAG_AZURE_OPENAI_API_VERSION,
              },
          }
      except Exception as e:
          log.exception(f"Problem updating embedding model: {e}")
          raise HTTPException(
              status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail=ERROR_MESSAGES.DEFAULT(e),
          )

  @router.get("/config")
  async def get_rag_config(request: Request, user=Depends(get_admin_user)):
      return {
          "status": True,
  RAG settings
          "RAG_TEMPLATE": request.app.state.config.RAG_TEMPLATE,
          "TOP_K": request.app.state.config.TOP_K,
          "BYPASS_EMBEDDING_AND_RETRIEVAL": request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL,
          "RAG_FULL_CONTEXT": request.app.state.config.RAG_FULL_CONTEXT,
  Hybrid search settings
          "ENABLE_RAG_HYBRID_SEARCH": request.app.state.config.ENABLE_RAG_HYBRID_SEARCH,
          "TOP_K_RERANKER": request.app.state.config.TOP_K_RERANKER,
          "RELEVANCE_THRESHOLD": request.app.state.config.RELEVANCE_THRESHOLD,
          "HYBRID_BM25_WEIGHT": request.app.state.config.HYBRID_BM25_WEIGHT,
  Content extraction settings
          "CONTENT_EXTRACTION_ENGINE": request.app.state.config.CONTENT_EXTRACTION_ENGINE,
          "PDF_EXTRACT_IMAGES": request.app.state.config.PDF_EXTRACT_IMAGES,
          "DATALAB_MARKER_API_KEY": request.app.state.config.DATALAB_MARKER_API_KEY,
          "DATALAB_MARKER_LANGS": request.app.state.config.DATALAB_MARKER_LANGS,
          "DATALAB_MARKER_SKIP_CACHE": request.app.state.config.DATALAB_MARKER_SKIP_CACHE,
          "DATALAB_MARKER_FORCE_OCR": request.app.state.config.DATALAB_MARKER_FORCE_OCR,
          "DATALAB_MARKER_PAGINATE": request.app.state.config.DATALAB_MARKER_PAGINATE,
          "DATALAB_MARKER_STRIP_EXISTING_OCR": request.app.state.config.DATALAB_MARKER_STRIP_EXISTING_OCR,
          "DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION": request.app.state.config.DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION,
          "DATALAB_MARKER_USE_LLM": request.app.state.config.DATALAB_MARKER_USE_LLM,
          "DATALAB_MARKER_OUTPUT_FORMAT": request.app.state.config.DATALAB_MARKER_OUTPUT_FORMAT,
          "EXTERNAL_DOCUMENT_LOADER_URL": request.app.state.config.EXTERNAL_DOCUMENT_LOADER_URL,
          "EXTERNAL_DOCUMENT_LOADER_API_KEY": request.app.state.config.EXTERNAL_DOCUMENT_LOADER_API_KEY,
          "TIKA_SERVER_URL": request.app.state.config.TIKA_SERVER_URL,
          "DOCLING_SERVER_URL": request.app.state.config.DOCLING_SERVER_URL,
          "DOCLING_OCR_ENGINE": request.app.state.config.DOCLING_OCR_ENGINE,
          "DOCLING_OCR_LANG": request.app.state.config.DOCLING_OCR_LANG,
          "DOCLING_DO_PICTURE_DESCRIPTION": request.app.state.config.DOCLING_DO_PICTURE_DESCRIPTION,
          "DOCLING_PICTURE_DESCRIPTION_MODE": request.app.state.config.DOCLING_PICTURE_DESCRIPTION_MODE,
          "DOCLING_PICTURE_DESCRIPTION_LOCAL": request.app.state.config.DOCLING_PICTURE_DESCRIPTION_LOCAL,
          "DOCLING_PICTURE_DESCRIPTION_API": request.app.state.config.DOCLING_PICTURE_DESCRIPTION_API,
          "DOCUMENT_INTELLIGENCE_ENDPOINT": request.app.state.config.DOCUMENT_INTELLIGENCE_ENDPOINT,
          "DOCUMENT_INTELLIGENCE_KEY": request.app.state.config.DOCUMENT_INTELLIGENCE_KEY,
          "MISTRAL_OCR_API_KEY": request.app.state.config.MISTRAL_OCR_API_KEY,
  Reranking settings
          "RAG_RERANKING_MODEL": request.app.state.config.RAG_RERANKING_MODEL,
          "RAG_RERANKING_ENGINE": request.app.state.config.RAG_RERANKING_ENGINE,
          "RAG_EXTERNAL_RERANKER_URL": request.app.state.config.RAG_EXTERNAL_RERANKER_URL,
          "RAG_EXTERNAL_RERANKER_API_KEY": request.app.state.config.RAG_EXTERNAL_RERANKER_API_KEY,
  Chunking settings
          "TEXT_SPLITTER": request.app.state.config.TEXT_SPLITTER,
          "CHUNK_SIZE": request.app.state.config.CHUNK_SIZE,
          "CHUNK_OVERLAP": request.app.state.config.CHUNK_OVERLAP,
  File upload settings
          "FILE_MAX_SIZE": request.app.state.config.FILE_MAX_SIZE,
          "FILE_MAX_COUNT": request.app.state.config.FILE_MAX_COUNT,
          "FILE_IMAGE_COMPRESSION_WIDTH": request.app.state.config.FILE_IMAGE_COMPRESSION_WIDTH,
          "FILE_IMAGE_COMPRESSION_HEIGHT": request.app.state.config.FILE_IMAGE_COMPRESSION_HEIGHT,
          "ALLOWED_FILE_EXTENSIONS": request.app.state.config.ALLOWED_FILE_EXTENSIONS,
  Integration settings
          "ENABLE_GOOGLE_DRIVE_INTEGRATION": request.app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION,
          "ENABLE_ONEDRIVE_INTEGRATION": request.app.state.config.ENABLE_ONEDRIVE_INTEGRATION,
  Web search settings
          "web": {
              "ENABLE_WEB_SEARCH": request.app.state.config.ENABLE_WEB_SEARCH,
              "WEB_SEARCH_ENGINE": request.app.state.config.WEB_SEARCH_ENGINE,
              "WEB_SEARCH_TRUST_ENV": request.app.state.config.WEB_SEARCH_TRUST_ENV,
              "WEB_SEARCH_RESULT_COUNT": request.app.state.config.WEB_SEARCH_RESULT_COUNT,
              "WEB_SEARCH_CONCURRENT_REQUESTS": request.app.state.config.WEB_SEARCH_CONCURRENT_REQUESTS,
              "WEB_SEARCH_DOMAIN_FILTER_LIST": request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
              "BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL": request.app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL,
              "BYPASS_WEB_SEARCH_WEB_LOADER": request.app.state.config.BYPASS_WEB_SEARCH_WEB_LOADER,
              "SEARXNG_QUERY_URL": request.app.state.config.SEARXNG_QUERY_URL,
              "YACY_QUERY_URL": request.app.state.config.YACY_QUERY_URL,
              "YACY_USERNAME": request.app.state.config.YACY_USERNAME,
              "YACY_PASSWORD": request.app.state.config.YACY_PASSWORD,
              "GOOGLE_PSE_API_KEY": request.app.state.config.GOOGLE_PSE_API_KEY,
              "GOOGLE_PSE_ENGINE_ID": request.app.state.config.GOOGLE_PSE_ENGINE_ID,
              "BRAVE_SEARCH_API_KEY": request.app.state.config.BRAVE_SEARCH_API_KEY,
              "KAGI_SEARCH_API_KEY": request.app.state.config.KAGI_SEARCH_API_KEY,
              "MOJEEK_SEARCH_API_KEY": request.app.state.config.MOJEEK_SEARCH_API_KEY,
              "BOCHA_SEARCH_API_KEY": request.app.state.config.BOCHA_SEARCH_API_KEY,
              "SERPSTACK_API_KEY": request.app.state.config.SERPSTACK_API_KEY,
              "SERPSTACK_HTTPS": request.app.state.config.SERPSTACK_HTTPS,
              "SERPER_API_KEY": request.app.state.config.SERPER_API_KEY,
              "SERPLY_API_KEY": request.app.state.config.SERPLY_API_KEY,
              "TAVILY_API_KEY": request.app.state.config.TAVILY_API_KEY,
              "SEARCHAPI_API_KEY": request.app.state.config.SEARCHAPI_API_KEY,
              "SEARCHAPI_ENGINE": request.app.state.config.SEARCHAPI_ENGINE,
              "SERPAPI_API_KEY": request.app.state.config.SERPAPI_API_KEY,
              "SERPAPI_ENGINE": request.app.state.config.SERPAPI_ENGINE,
              "JINA_API_KEY": request.app.state.config.JINA_API_KEY,
              "BING_SEARCH_V7_ENDPOINT": request.app.state.config.BING_SEARCH_V7_ENDPOINT,
              "BING_SEARCH_V7_SUBSCRIPTION_KEY": request.app.state.config.BING_SEARCH_V7_SUBSCRIPTION_KEY,
              "EXA_API_KEY": request.app.state.config.EXA_API_KEY,
              "PERPLEXITY_API_KEY": request.app.state.config.PERPLEXITY_API_KEY,
              "PERPLEXITY_MODEL": request.app.state.config.PERPLEXITY_MODEL,
              "PERPLEXITY_SEARCH_CONTEXT_USAGE": request.app.state.config.PERPLEXITY_SEARCH_CONTEXT_USAGE,
              "SOUGOU_API_SID": request.app.state.config.SOUGOU_API_SID,
              "SOUGOU_API_SK": request.app.state.config.SOUGOU_API_SK,
              "WEB_LOADER_ENGINE": request.app.state.config.WEB_LOADER_ENGINE,
              "ENABLE_WEB_LOADER_SSL_VERIFICATION": request.app.state.config.ENABLE_WEB_LOADER_SSL_VERIFICATION,
              "PLAYWRIGHT_WS_URL": request.app.state.config.PLAYWRIGHT_WS_URL,
              "PLAYWRIGHT_TIMEOUT": request.app.state.config.PLAYWRIGHT_TIMEOUT,
              "FIRECRAWL_API_KEY": request.app.state.config.FIRECRAWL_API_KEY,
              "FIRECRAWL_API_BASE_URL": request.app.state.config.FIRECRAWL_API_BASE_URL,
              "TAVILY_EXTRACT_DEPTH": request.app.state.config.TAVILY_EXTRACT_DEPTH,
              "EXTERNAL_WEB_SEARCH_URL": request.app.state.config.EXTERNAL_WEB_SEARCH_URL,
              "EXTERNAL_WEB_SEARCH_API_KEY": request.app.state.config.EXTERNAL_WEB_SEARCH_API_KEY,
              "EXTERNAL_WEB_LOADER_URL": request.app.state.config.EXTERNAL_WEB_LOADER_URL,
              "EXTERNAL_WEB_LOADER_API_KEY": request.app.state.config.EXTERNAL_WEB_LOADER_API_KEY,
              "YOUTUBE_LOADER_LANGUAGE": request.app.state.config.YOUTUBE_LOADER_LANGUAGE,
              "YOUTUBE_LOADER_PROXY_URL": request.app.state.config.YOUTUBE_LOADER_PROXY_URL,
              "YOUTUBE_LOADER_TRANSLATION": request.app.state.YOUTUBE_LOADER_TRANSLATION,
          },
      }

  class WebConfig(BaseModel):
      ENABLE_WEB_SEARCH: Optional[bool] = None
      WEB_SEARCH_ENGINE: Optional[str] = None
      WEB_SEARCH_TRUST_ENV: Optional[bool] = None
      WEB_SEARCH_RESULT_COUNT: Optional[int] = None
      WEB_SEARCH_CONCURRENT_REQUESTS: Optional[int] = None
      WEB_SEARCH_DOMAIN_FILTER_LIST: Optional[List[str]] = []
      BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL: Optional[bool] = None
      BYPASS_WEB_SEARCH_WEB_LOADER: Optional[bool] = None
      SEARXNG_QUERY_URL: Optional[str] = None
      YACY_QUERY_URL: Optional[str] = None
      YACY_USERNAME: Optional[str] = None
      YACY_PASSWORD: Optional[str] = None
      GOOGLE_PSE_API_KEY: Optional[str] = None
      GOOGLE_PSE_ENGINE_ID: Optional[str] = None
      BRAVE_SEARCH_API_KEY: Optional[str] = None
      KAGI_SEARCH_API_KEY: Optional[str] = None
      MOJEEK_SEARCH_API_KEY: Optional[str] = None
      BOCHA_SEARCH_API_KEY: Optional[str] = None
      SERPSTACK_API_KEY: Optional[str] = None
      SERPSTACK_HTTPS: Optional[bool] = None
      SERPER_API_KEY: Optional[str] = None
      SERPLY_API_KEY: Optional[str] = None
      TAVILY_API_KEY: Optional[str] = None
      SEARCHAPI_API_KEY: Optional[str] = None
      SEARCHAPI_ENGINE: Optional[str] = None
      SERPAPI_API_KEY: Optional[str] = None
      SERPAPI_ENGINE: Optional[str] = None
      JINA_API_KEY: Optional[str] = None
      BING_SEARCH_V7_ENDPOINT: Optional[str] = None
      BING_SEARCH_V7_SUBSCRIPTION_KEY: Optional[str] = None
      EXA_API_KEY: Optional[str] = None
      PERPLEXITY_API_KEY: Optional[str] = None
      PERPLEXITY_MODEL: Optional[str] = None
      PERPLEXITY_SEARCH_CONTEXT_USAGE: Optional[str] = None
      SOUGOU_API_SID: Optional[str] = None
      SOUGOU_API_SK: Optional[str] = None
      WEB_LOADER_ENGINE: Optional[str] = None
      ENABLE_WEB_LOADER_SSL_VERIFICATION: Optional[bool] = None
      PLAYWRIGHT_WS_URL: Optional[str] = None
      PLAYWRIGHT_TIMEOUT: Optional[int] = None
      FIRECRAWL_API_KEY: Optional[str] = None
      FIRECRAWL_API_BASE_URL: Optional[str] = None
      TAVILY_EXTRACT_DEPTH: Optional[str] = None
      EXTERNAL_WEB_SEARCH_URL: Optional[str] = None
      EXTERNAL_WEB_SEARCH_API_KEY: Optional[str] = None
      EXTERNAL_WEB_LOADER_URL: Optional[str] = None
      EXTERNAL_WEB_LOADER_API_KEY: Optional[str] = None
      YOUTUBE_LOADER_LANGUAGE: Optional[List[str]] = None
      YOUTUBE_LOADER_PROXY_URL: Optional[str] = None
      YOUTUBE_LOADER_TRANSLATION: Optional[str] = None

  class ConfigForm(BaseModel):
  RAG settings
      RAG_TEMPLATE: Optional[str] = None
      TOP_K: Optional[int] = None
      BYPASS_EMBEDDING_AND_RETRIEVAL: Optional[bool] = None
      RAG_FULL_CONTEXT: Optional[bool] = None

  Hybrid search settings
      ENABLE_RAG_HYBRID_SEARCH: Optional[bool] = None
      TOP_K_RERANKER: Optional[int] = None
      RELEVANCE_THRESHOLD: Optional[float] = None
      HYBRID_BM25_WEIGHT: Optional[float] = None

  Content extraction settings
      CONTENT_EXTRACTION_ENGINE: Optional[str] = None
      PDF_EXTRACT_IMAGES: Optional[bool] = None
      DATALAB_MARKER_API_KEY: Optional[str] = None
      DATALAB_MARKER_LANGS: Optional[str] = None
      DATALAB_MARKER_SKIP_CACHE: Optional[bool] = None
      DATALAB_MARKER_FORCE_OCR: Optional[bool] = None
      DATALAB_MARKER_PAGINATE: Optional[bool] = None
      DATALAB_MARKER_STRIP_EXISTING_OCR: Optional[bool] = None
      DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION: Optional[bool] = None
      DATALAB_MARKER_USE_LLM: Optional[bool] = None
      DATALAB_MARKER_OUTPUT_FORMAT: Optional[str] = None
      EXTERNAL_DOCUMENT_LOADER_URL: Optional[str] = None
      EXTERNAL_DOCUMENT_LOADER_API_KEY: Optional[str] = None

      TIKA_SERVER_URL: Optional[str] = None
      DOCLING_SERVER_URL: Optional[str] = None
      DOCLING_OCR_ENGINE: Optional[str] = None
      DOCLING_OCR_LANG: Optional[str] = None
      DOCLING_DO_PICTURE_DESCRIPTION: Optional[bool] = None
      DOCLING_PICTURE_DESCRIPTION_MODE: Optional[str] = None
      DOCLING_PICTURE_DESCRIPTION_LOCAL: Optional[dict] = None
      DOCLING_PICTURE_DESCRIPTION_API: Optional[dict] = None
      DOCUMENT_INTELLIGENCE_ENDPOINT: Optional[str] = None
      DOCUMENT_INTELLIGENCE_KEY: Optional[str] = None
      MISTRAL_OCR_API_KEY: Optional[str] = None

  Reranking settings
      RAG_RERANKING_MODEL: Optional[str] = None
      RAG_RERANKING_ENGINE: Optional[str] = None
      RAG_EXTERNAL_RERANKER_URL: Optional[str] = None
      RAG_EXTERNAL_RERANKER_API_KEY: Optional[str] = None

  Chunking settings
      TEXT_SPLITTER: Optional[str] = None
      CHUNK_SIZE: Optional[int] = None
      CHUNK_OVERLAP: Optional[int] = None

  File upload settings
      FILE_MAX_SIZE: Optional[int] = None
      FILE_MAX_COUNT: Optional[int] = None
      FILE_IMAGE_COMPRESSION_WIDTH: Optional[int] = None
      FILE_IMAGE_COMPRESSION_HEIGHT: Optional[int] = None
      ALLOWED_FILE_EXTENSIONS: Optional[List[str]] = None

  Integration settings
      ENABLE_GOOGLE_DRIVE_INTEGRATION: Optional[bool] = None
      ENABLE_ONEDRIVE_INTEGRATION: Optional[bool] = None

  Web search settings
      web: Optional[WebConfig] = None

  @router.post("/config/update")
  async def update_rag_config(
      request: Request, form_data: ConfigForm, user=Depends(get_admin_user)
  ):
      log.info(
          f"Updating reranking model: {request.app.state.config.RAG_RERANKING_MODEL} to {form_data.RAG_RERANKING_MODEL}"
      )
      try:
          request.app.state.config.RAG_RERANKING_MODEL = (
              form_data.RAG_RERANKING_MODEL
              if form_data.RAG_RERANKING_MODEL is not None
              else request.app.state.config.RAG_RERANKING_MODEL
          )

          try:
              request.app.state.rf = get_rf(
                  request.app.state.config.RAG_RERANKING_ENGINE,
                  request.app.state.config.RAG_RERANKING_MODEL,
                  request.app.state.config.RAG_EXTERNAL_RERANKER_URL,
                  request.app.state.config.RAG_EXTERNAL_RERANKER_API_KEY,
                  True,
              )

              request.app.state.RERANKING_FUNCTION = get_reranking_function(
                  request.app.state.config.RAG_RERANKING_ENGINE,
                  request.app.state.config.RAG_RERANKING_MODEL,
                  request.app.state.rf,
              )
          except Exception as e:
              log.error(f"Error loading reranking model: {e}")
              request.app.state.config.ENABLE_RAG_HYBRID_SEARCH = False
      except Exception as e:
          log.exception(f"Problem updating reranking model: {e}")
          raise HTTPException(
              status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail=ERROR_MESSAGES.DEFAULT(e),
          )

  Chunking settings
      request.app.state.config.TEXT_SPLITTER = (
          form_data.TEXT_SPLITTER
          if form_data.TEXT_SPLITTER is not None
          else request.app.state.config.TEXT_SPLITTER
      )
      request.app.state.config.CHUNK_SIZE = (
          form_data.CHUNK_SIZE
          if form_data.CHUNK_SIZE is not None
          else request.app.state.config.CHUNK_SIZE
      )
      request.app.state.config.CHUNK_OVERLAP = (
          form_data.CHUNK_OVERLAP
          if form_data.CHUNK_OVERLAP is not None
          else request.app.state.config.CHUNK_OVERLAP
      )

  File upload settings
      request.app.state.config.FILE_MAX_SIZE = form_data.FILE_MAX_SIZE
      request.app.state.config.FILE_MAX_COUNT = form_data.FILE_MAX_COUNT
      request.app.state.config.FILE_IMAGE_COMPRESSION_WIDTH = (
          form_data.FILE_IMAGE_COMPRESSION_WIDTH
      )
      request.app.state.config.FILE_IMAGE_COMPRESSION_HEIGHT = (
          form_data.FILE_IMAGE_COMPRESSION_HEIGHT
      )
      request.app.state.config.ALLOWED_FILE_EXTENSIONS = (
          form_data.ALLOWED_FILE_EXTENSIONS
          if form_data.ALLOWED_FILE_EXTENSIONS is not None
          else request.app.state.config.ALLOWED_FILE_EXTENSIONS
      )

  Integration settings
      request.app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION = (
          form_data.ENABLE_GOOGLE_DRIVE_INTEGRATION
          if form_data.ENABLE_GOOGLE_DRIVE_INTEGRATION is not None
          else request.app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION
      )
      request.app.state.config.ENABLE_ONEDRIVE_INTEGRATION = (
          form_data.ENABLE_ONEDRIVE_INTEGRATION
          if form_data.ENABLE_ONEDRIVE_INTEGRATION is not None
          else request.app.state.config.ENABLE_ONEDRIVE_INTEGRATION
      )

      if form_data.web is not None:
  Web search settings
          request.app.state.config.ENABLE_WEB_SEARCH = form_data.web.ENABLE_WEB_SEARCH
          request.app.state.config.WEB_SEARCH_ENGINE = form_data.web.WEB_SEARCH_ENGINE
          request.app.state.config.WEB_SEARCH_TRUST_ENV = (
              form_data.web.WEB_SEARCH_TRUST_ENV
          )
          request.app.state.config.WEB_SEARCH_RESULT_COUNT = (
              form_data.web.WEB_SEARCH_RESULT_COUNT
          )
          request.app.state.config.WEB_SEARCH_CONCURRENT_REQUESTS = (
              form_data.web.WEB_SEARCH_CONCURRENT_REQUESTS
          )
          request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST = (
              form_data.web.WEB_SEARCH_DOMAIN_FILTER_LIST
          )
          request.app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL = (
              form_data.web.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL
          )
          request.app.state.config.BYPASS_WEB_SEARCH_WEB_LOADER = (
              form_data.web.BYPASS_WEB_SEARCH_WEB_LOADER
          )
          request.app.state.config.SEARXNG_QUERY_URL = form_data.web.SEARXNG_QUERY_URL
          request.app.state.config.YACY_QUERY_URL = form_data.web.YACY_QUERY_URL
          request.app.state.config.YACY_USERNAME = form_data.web.YACY_USERNAME
          request.app.state.config.YACY_PASSWORD = form_data.web.YACY_PASSWORD
          request.app.state.config.GOOGLE_PSE_API_KEY = form_data.web.GOOGLE_PSE_API_KEY
          request.app.state.config.GOOGLE_PSE_ENGINE_ID = (
              form_data.web.GOOGLE_PSE_ENGINE_ID
          )
          request.app.state.config.BRAVE_SEARCH_API_KEY = (
              form_data.web.BRAVE_SEARCH_API_KEY
          )
          request.app.state.config.KAGI_SEARCH_API_KEY = form_data.web.KAGI_SEARCH_API_KEY
          request.app.state.config.MOJEEK_SEARCH_API_KEY = (
              form_data.web.MOJEEK_SEARCH_API_KEY
          )
          request.app.state.config.BOCHA_SEARCH_API_KEY = (
              form_data.web.BOCHA_SEARCH_API_KEY
          )
          request.app.state.config.SERPSTACK_API_KEY = form_data.web.SERPSTACK_API_KEY
          request.app.state.config.SERPSTACK_HTTPS = form_data.web.SERPSTACK_HTTPS
          request.app.state.config.SERPER_API_KEY = form_data.web.SERPER_API_KEY
          request.app.state.config.SERPLY_API_KEY = form_data.web.SERPLY_API_KEY
          request.app.state.config.TAVILY_API_KEY = form_data.web.TAVILY_API_KEY
          request.app.state.config.SEARCHAPI_API_KEY = form_data.web.SEARCHAPI_API_KEY
          request.app.state.config.SEARCHAPI_ENGINE = form_data.web.SEARCHAPI_ENGINE
          request.app.state.config.SERPAPI_API_KEY = form_data.web.SERPAPI_API_KEY
          request.app.state.config.SERPAPI_ENGINE = form_data.web.SERPAPI_ENGINE
          request.app.state.config.JINA_API_KEY = form_data.web.JINA_API_KEY
          request.app.state.config.BING_SEARCH_V7_ENDPOINT = (
              form_data.web.BING_SEARCH_V7_ENDPOINT
          )
          request.app.state.config.BING_SEARCH_V7_SUBSCRIPTION_KEY = (
              form_data.web.BING_SEARCH_V7_SUBSCRIPTION_KEY
          )
          request.app.state.config.EXA_API_KEY = form_data.web.EXA_API_KEY
          request.app.state.config.PERPLEXITY_API_KEY = form_data.web.PERPLEXITY_API_KEY
          request.app.state.config.PERPLEXITY_MODEL = form_data.web.PERPLEXITY_MODEL
          request.app.state.config.PERPLEXITY_SEARCH_CONTEXT_USAGE = (
              form_data.web.PERPLEXITY_SEARCH_CONTEXT_USAGE
          )
          request.app.state.config.SOUGOU_API_SID = form_data.web.SOUGOU_API_SID
          request.app.state.config.SOUGOU_API_SK = form_data.web.SOUGOU_API_SK

  Web loader settings
          request.app.state.config.WEB_LOADER_ENGINE = form_data.web.WEB_LOADER_ENGINE
          request.app.state.config.ENABLE_WEB_LOADER_SSL_VERIFICATION = (
              form_data.web.ENABLE_WEB_LOADER_SSL_VERIFICATION
          )
          request.app.state.config.PLAYWRIGHT_WS_URL = form_data.web.PLAYWRIGHT_WS_URL
          request.app.state.config.PLAYWRIGHT_TIMEOUT = form_data.web.PLAYWRIGHT_TIMEOUT
          request.app.state.config.FIRECRAWL_API_KEY = form_data.web.FIRECRAWL_API_KEY
          request.app.state.config.FIRECRAWL_API_BASE_URL = (
              form_data.web.FIRECRAWL_API_BASE_URL
          )
          request.app.state.config.EXTERNAL_WEB_SEARCH_URL = (
              form_data.web.EXTERNAL_WEB_SEARCH_URL
          )
          request.app.state.config.EXTERNAL_WEB_SEARCH_API_KEY = (
              form_data.web.EXTERNAL_WEB_SEARCH_API_KEY
          )
          request.app.state.config.EXTERNAL_WEB_LOADER_URL = (
              form_data.web.EXTERNAL_WEB_LOADER_URL
          )
          request.app.state.config.EXTERNAL_WEB_LOADER_API_KEY = (
              form_data.web.EXTERNAL_WEB_LOADER_API_KEY
          )
          request.app.state.config.TAVILY_EXTRACT_DEPTH = (
              form_data.web.TAVILY_EXTRACT_DEPTH
          )
          request.app.state.config.YOUTUBE_LOADER_LANGUAGE = (
              form_data.web.YOUTUBE_LOADER_LANGUAGE
          )
          request.app.state.config.YOUTUBE_LOADER_PROXY_URL = (
              form_data.web.YOUTUBE_LOADER_PROXY_URL
          )
          request.app.state.YOUTUBE_LOADER_TRANSLATION = (
              form_data.web.YOUTUBE_LOADER_TRANSLATION
          )

      return {
          "status": True,
  RAG settings
          "RAG_TEMPLATE": request.app.state.config.RAG_TEMPLATE,
          "TOP_K": request.app.state.config.TOP_K,
          "BYPASS_EMBEDDING_AND_RETRIEVAL": request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL,
          "RAG_FULL_CONTEXT": request.app.state.config.RAG_FULL_CONTEXT,
  Hybrid search settings
          "ENABLE_RAG_HYBRID_SEARCH": request.app.state.config.ENABLE_RAG_HYBRID_SEARCH,
          "TOP_K_RERANKER": request.app.state.config.TOP_K_RERANKER,
          "RELEVANCE_THRESHOLD": request.app.state.config.RELEVANCE_THRESHOLD,
          "HYBRID_BM25_WEIGHT": request.app.state.config.HYBRID_BM25_WEIGHT,
  Content extraction settings
          "CONTENT_EXTRACTION_ENGINE": request.app.state.config.CONTENT_EXTRACTION_ENGINE,
          "PDF_EXTRACT_IMAGES": request.app.state.config.PDF_EXTRACT_IMAGES,
          "DATALAB_MARKER_API_KEY": request.app.state.config.DATALAB_MARKER_API_KEY,
          "DATALAB_MARKER_LANGS": request.app.state.config.DATALAB_MARKER_LANGS,
          "DATALAB_MARKER_SKIP_CACHE": request.app.state.config.DATALAB_MARKER_SKIP_CACHE,
          "DATALAB_MARKER_FORCE_OCR": request.app.state.config.DATALAB_MARKER_FORCE_OCR,
          "DATALAB_MARKER_PAGINATE": request.app.state.config.DATALAB_MARKER_PAGINATE,
          "DATALAB_MARKER_STRIP_EXISTING_OCR": request.app.state.config.DATALAB_MARKER_STRIP_EXISTING_OCR,
          "DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION": request.app.state.config.DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION,
          "DATALAB_MARKER_USE_LLM": request.app.state.config.DATALAB_MARKER_USE_LLM,
          "DATALAB_MARKER_OUTPUT_FORMAT": request.app.state.config.DATALAB_MARKER_OUTPUT_FORMAT,
          "EXTERNAL_DOCUMENT_LOADER_URL": request.app.state.config.EXTERNAL_DOCUMENT_LOADER_URL,
          "EXTERNAL_DOCUMENT_LOADER_API_KEY": request.app.state.config.EXTERNAL_DOCUMENT_LOADER_API_KEY,
          "TIKA_SERVER_URL": request.app.state.config.TIKA_SERVER_URL,
          "DOCLING_SERVER_URL": request.app.state.config.DOCLING_SERVER_URL,
          "DOCLING_OCR_ENGINE": request.app.state.config.DOCLING_OCR_ENGINE,
          "DOCLING_OCR_LANG": request.app.state.config.DOCLING_OCR_LANG,
          "DOCLING_DO_PICTURE_DESCRIPTION": request.app.state.config.DOCLING_DO_PICTURE_DESCRIPTION,
          "DOCLING_PICTURE_DESCRIPTION_MODE": request.app.state.config.DOCLING_PICTURE_DESCRIPTION_MODE,
          "DOCLING_PICTURE_DESCRIPTION_LOCAL": request.app.state.config.DOCLING_PICTURE_DESCRIPTION_LOCAL,
          "DOCLING_PICTURE_DESCRIPTION_API": request.app.state.config.DOCLING_PICTURE_DESCRIPTION_API,
          "DOCUMENT_INTELLIGENCE_ENDPOINT": request.app.state.config.DOCUMENT_INTELLIGENCE_ENDPOINT,
          "DOCUMENT_INTELLIGENCE_KEY": request.app.state.config.DOCUMENT_INTELLIGENCE_KEY,
          "MISTRAL_OCR_API_KEY": request.app.state.config.MISTRAL_OCR_API_KEY,
  Reranking settings
          "RAG_RERANKING_MODEL": request.app.state.config.RAG_RERANKING_MODEL,
          "RAG_RERANKING_ENGINE": request.app.state.config.RAG_RERANKING_ENGINE,
          "RAG_EXTERNAL_RERANKER_URL": request.app.state.config.RAG_EXTERNAL_RERANKER_URL,
          "RAG_EXTERNAL_RERANKER_API_KEY": request.app.state.config.RAG_EXTERNAL_RERANKER_API_KEY,
  Chunking settings
          "TEXT_SPLITTER": request.app.state.config.TEXT_SPLITTER,
          "CHUNK_SIZE": request.app.state.config.CHUNK_SIZE,
          "CHUNK_OVERLAP": request.app.state.config.CHUNK_OVERLAP,
  File upload settings
          "FILE_MAX_SIZE": request.app.state.config.FILE_MAX_SIZE,
          "FILE_MAX_COUNT": request.app.state.config.FILE_MAX_COUNT,
          "FILE_IMAGE_COMPRESSION_WIDTH": request.app.state.config.FILE_IMAGE_COMPRESSION_WIDTH,
          "FILE_IMAGE_COMPRESSION_HEIGHT": request.app.state.config.FILE_IMAGE_COMPRESSION_HEIGHT,
          "ALLOWED_FILE_EXTENSIONS": request.app.state.config.ALLOWED_FILE_EXTENSIONS,
  Integration settings
          "ENABLE_GOOGLE_DRIVE_INTEGRATION": request.app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION,
          "ENABLE_ONEDRIVE_INTEGRATION": request.app.state.config.ENABLE_ONEDRIVE_INTEGRATION,
  Web search settings
          "web": {
              "ENABLE_WEB_SEARCH": request.app.state.config.ENABLE_WEB_SEARCH,
              "WEB_SEARCH_ENGINE": request.app.state.config.WEB_SEARCH_ENGINE,
              "WEB_SEARCH_TRUST_ENV": request.app.state.config.WEB_SEARCH_TRUST_ENV,
              "WEB_SEARCH_RESULT_COUNT": request.app.state.config.WEB_SEARCH_RESULT_COUNT,
              "WEB_SEARCH_CONCURRENT_REQUESTS": request.app.state.config.WEB_SEARCH_CONCURRENT_REQUESTS,
              "WEB_SEARCH_DOMAIN_FILTER_LIST": request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
              "BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL": request.app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL,
              "BYPASS_WEB_SEARCH_WEB_LOADER": request.app.state.config.BYPASS_WEB_SEARCH_WEB_LOADER,
              "SEARXNG_QUERY_URL": request.app.state.config.SEARXNG_QUERY_URL,
              "YACY_QUERY_URL": request.app.state.config.YACY_QUERY_URL,
              "YACY_USERNAME": request.app.state.config.YACY_USERNAME,
              "YACY_PASSWORD": request.app.state.config.YACY_PASSWORD,
              "GOOGLE_PSE_API_KEY": request.app.state.config.GOOGLE_PSE_API_KEY,
              "GOOGLE_PSE_ENGINE_ID": request.app.state.config.GOOGLE_PSE_ENGINE_ID,
              "BRAVE_SEARCH_API_KEY": request.app.state.config.BRAVE_SEARCH_API_KEY,
              "KAGI_SEARCH_API_KEY": request.app.state.config.KAGI_SEARCH_API_KEY,
              "MOJEEK_SEARCH_API_KEY": request.app.state.config.MOJEEK_SEARCH_API_KEY,
              "BOCHA_SEARCH_API_KEY": request.app.state.config.BOCHA_SEARCH_API_KEY,
              "SERPSTACK_API_KEY": request.app.state.config.SERPSTACK_API_KEY,
              "SERPSTACK_HTTPS": request.app.state.config.SERPSTACK_HTTPS,
              "SERPER_API_KEY": request.app.state.config.SERPER_API_KEY,
              "SERPLY_API_KEY": request.app.state.config.SERPLY_API_KEY,
              "TAVILY_API_KEY": request.app.state.config.TAVILY_API_KEY,
              "SEARCHAPI_API_KEY": request.app.state.config.SEARCHAPI_API_KEY,
              "SEARCHAPI_ENGINE": request.app.state.config.SEARCHAPI_ENGINE,
              "SERPAPI_API_KEY": request.app.state.config.SERPAPI_API_KEY,
              "SERPAPI_ENGINE": request.app.state.config.SERPAPI_ENGINE,
              "JINA_API_KEY": request.app.state.config.JINA_API_KEY,
              "BING_SEARCH_V7_ENDPOINT": request.app.state.config.BING_SEARCH_V7_ENDPOINT,
              "BING_SEARCH_V7_SUBSCRIPTION_KEY": request.app.state.config.BING_SEARCH_V7_SUBSCRIPTION_KEY,
              "EXA_API_KEY": request.app.state.config.EXA_API_KEY,
              "PERPLEXITY_API_KEY": request.app.state.config.PERPLEXITY_API_KEY,
              "PERPLEXITY_MODEL": request.app.state.config.PERPLEXITY_MODEL,
              "PERPLEXITY_SEARCH_CONTEXT_USAGE": request.app.state.config.PERPLEXITY_SEARCH_CONTEXT_USAGE,
              "SOUGOU_API_SID": request.app.state.config.SOUGOU_API_SID,
              "SOUGOU_API_SK": request.app.state.config.SOUGOU_API_SK,
              "WEB_LOADER_ENGINE": request.app.state.config.WEB_LOADER_ENGINE,
              "ENABLE_WEB_LOADER_SSL_VERIFICATION": request.app.state.config.ENABLE_WEB_LOADER_SSL_VERIFICATION,
              "PLAYWRIGHT_WS_URL": request.app.state.config.PLAYWRIGHT_WS_URL,
              "PLAYWRIGHT_TIMEOUT": request.app.state.config.PLAYWRIGHT_TIMEOUT,
              "FIRECRAWL_API_KEY": request.app.state.config.FIRECRAWL_API_KEY,
              "FIRECRAWL_API_BASE_URL": request.app.state.config.FIRECRAWL_API_BASE_URL,
              "TAVILY_EXTRACT_DEPTH": request.app.state.config.TAVILY_EXTRACT_DEPTH,
              "EXTERNAL_WEB_SEARCH_URL": request.app.state.config.EXTERNAL_WEB_SEARCH_URL,
              "EXTERNAL_WEB_SEARCH_API_KEY": request.app.state.config.EXTERNAL_WEB_SEARCH_API_KEY,
              "EXTERNAL_WEB_LOADER_URL": request.app.state.config.EXTERNAL_WEB_LOADER_URL,
              "EXTERNAL_WEB_LOADER_API_KEY": request.app.state.config.EXTERNAL_WEB_LOADER_API_KEY,
              "YOUTUBE_LOADER_LANGUAGE": request.app.state.config.YOUTUBE_LOADER_LANGUAGE,
              "YOUTUBE_LOADER_PROXY_URL": request.app.state.config.YOUTUBE_LOADER_PROXY_URL,
              "YOUTUBE_LOADER_TRANSLATION": request.app.state.YOUTUBE_LOADER_TRANSLATION,
          },
      }

  ####################################
  #
  Document process and retrieval
  #
  ####################################

  def save_docs_to_vector_db(
      request: Request,
      docs,
      collection_name,
      metadata: Optional[dict] = None,
      overwrite: bool = False,
      split: bool = True,
      add: bool = False,
      user=None,
  ) -> bool:
      def _get_docs_info(docs: list[Document]) -> str:
          docs_info = set()

  Trying to select relevant metadata identifying the document.
          for doc in docs:
              metadata = getattr(doc, "metadata", {})
              doc_name = metadata.get("name", "")
              if not doc_name:
                  doc_name = metadata.get("title", "")
              if not doc_name:
                  doc_name = metadata.get("source", "")
              if doc_name:
                  docs_info.add(doc_name)

          return ", ".join(docs_info)

      log.info(
          f"save_docs_to_vector_db: document {_get_docs_info(docs)} {collection_name}"
      )

  Check if entries with the same hash (metadata.hash) already exist
      if metadata and "hash" in metadata:
          result = VECTOR_DB_CLIENT.query(
              collection_name=collection_name,
              filter={"hash": metadata["hash"]},
          )

          if result is not None:
              existing_doc_ids = result.ids[0]
              if existing_doc_ids:
                  log.info(f"Document with hash {metadata['hash']} already exists")
                  raise ValueError(ERROR_MESSAGES.DUPLICATE_CONTENT)

      if split:
          if request.app.state.config.TEXT_SPLITTER in ["", "character"]:
              text_splitter = RecursiveCharacterTextSplitter(
                  chunk_size=request.app.state.config.CHUNK_SIZE,
                  chunk_overlap=request.app.state.config.CHUNK_OVERLAP,
                  add_start_index=True,
              )
              docs = text_splitter.split_documents(docs)
          elif request.app.state.config.TEXT_SPLITTER == "token":
              log.info(
                  f"Using token text splitter: {request.app.state.config.TIKTOKEN_ENCODING_NAME}"
              )

              tiktoken.get_encoding(str(request.app.state.config.TIKTOKEN_ENCODING_NAME))
              text_splitter = TokenTextSplitter(
                  encoding_name=str(request.app.state.config.TIKTOKEN_ENCODING_NAME),
                  chunk_size=request.app.state.config.CHUNK_SIZE,
                  chunk_overlap=request.app.state.config.CHUNK_OVERLAP,
                  add_start_index=True,
              )
              docs = text_splitter.split_documents(docs)
          elif request.app.state.config.TEXT_SPLITTER == "markdown_header":
              log.info("Using markdown header text splitter")

  Define headers to split on - covering most common markdown header levels
              headers_to_split_on = [
                  ("#", "Header 1"),
                  ("##", "Header 2"),
                  ("###", "Header 3"),
                  ("####", "Header 4"),
                  ("#####", "Header 5"),
                  ("######", "Header 6"),
              ]

              markdown_splitter = MarkdownHeaderTextSplitter(
                  headers_to_split_on=headers_to_split_on,
                  strip_headers=False,  # Keep headers in content for context
              )

              md_split_docs = []
              for doc in docs:
                  md_header_splits = markdown_splitter.split_text(doc.page_content)
                  text_splitter = RecursiveCharacterTextSplitter(
                      chunk_size=request.app.state.config.CHUNK_SIZE,
                      chunk_overlap=request.app.state.config.CHUNK_OVERLAP,
                      add_start_index=True,
                  )
                  md_header_splits = text_splitter.split_documents(md_header_splits)

  Convert back to Document objects, preserving original metadata
                  for split_chunk in md_header_splits:
                      headings_list = []
  Extract header values in order based on headers_to_split_on
                      for _, header_meta_key_name in headers_to_split_on:
                          if header_meta_key_name in split_chunk.metadata:
                              headings_list.append(
                                  split_chunk.metadata[header_meta_key_name]
                              )

                      md_split_docs.append(
                          Document(
                              page_content=split_chunk.page_content,
                              metadata={**doc.metadata, "headings": headings_list},
                          )
                      )

              docs = md_split_docs
          else:
              raise ValueError(ERROR_MESSAGES.DEFAULT("Invalid text splitter"))

      if len(docs) == 0:
          raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)

      texts = [doc.page_content for doc in docs]
      metadatas = [
          {
              **doc.metadata,
              **(metadata if metadata else {}),
              "embedding_config": json.dumps(
                  {
                      "engine": request.app.state.config.RAG_EMBEDDING_ENGINE,
                      "model": request.app.state.config.RAG_EMBEDDING_MODEL,
                  }
              ),
          }
          for doc in docs
      ]

  ChromaDB does not like datetime formats
  for meta-data so convert them to string.
      for metadata in metadatas:
          for key, value in metadata.items():
              if (
                  isinstance(value, datetime)
                  or isinstance(value, list)
                  or isinstance(value, dict)
              ):
                  metadata[key] = str(value)

      try:
          if VECTOR_DB_CLIENT.has_collection(collection_name=collection_name):
              log.info(f"collection {collection_name} already exists")

              if overwrite:
                  VECTOR_DB_CLIENT.delete_collection(collection_name=collection_name)
                  log.info(f"deleting existing collection {collection_name}")
              elif add is False:
                  log.info(
                      f"collection {collection_name} already exists, overwrite is False and add is False"
                  )
                  return True

          log.info(f"adding to collection {collection_name}")
          embedding_function = get_embedding_function(
              request.app.state.config.RAG_EMBEDDING_ENGINE,
              request.app.state.config.RAG_EMBEDDING_MODEL,
              request.app.state.ef,
              (
                  request.app.state.config.RAG_OPENAI_API_BASE_URL
                  if request.app.state.config.RAG_EMBEDDING_ENGINE == "openai"
                  else (
                      request.app.state.config.RAG_OLLAMA_BASE_URL
                      if request.app.state.config.RAG_EMBEDDING_ENGINE == "ollama"
                      else request.app.state.config.RAG_AZURE_OPENAI_BASE_URL
                  )
              ),
              (
                  request.app.state.config.RAG_OPENAI_API_KEY
                  if request.app.state.config.RAG_EMBEDDING_ENGINE == "openai"
                  else (
                      request.app.state.config.RAG_OLLAMA_API_KEY
                      if request.app.state.config.RAG_EMBEDDING_ENGINE == "ollama"
                      else request.app.state.config.RAG_AZURE_OPENAI_API_KEY
                  )
              ),
              request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
              azure_api_version=(
                  request.app.state.config.RAG_AZURE_OPENAI_API_VERSION
                  if request.app.state.config.RAG_EMBEDDING_ENGINE == "azure_openai"
                  else None
              ),
          )

          embeddings = embedding_function(
              list(map(lambda x: x.replace("\n", " "), texts)),
              prefix=RAG_EMBEDDING_CONTENT_PREFIX,
              user=user,
          )

          items = [
              {
                  "id": str(uuid.uuid4()),
                  "text": text,
                  "vector": embeddings[idx],
                  "metadata": metadatas[idx],
              }
              for idx, text in enumerate(texts)
          ]

          VECTOR_DB_CLIENT.insert(
              collection_name=collection_name,
              items=items,
          )

          return True
      except Exception as e:
          log.exception(e)
          raise e

  class ProcessFileForm(BaseModel):
      file_id: str
      content: Optional[str] = None
      collection_name: Optional[str] = None

  @router.post("/process/file")
  def process_file(
      request: Request,
      form_data: ProcessFileForm,
      user=Depends(get_verified_user),
  ):
      try:
          file = Files.get_file_by_id(form_data.file_id)

          collection_name = form_data.collection_name

          if collection_name is None:
              collection_name = f"file-{file.id}"

          if form_data.content:
  Update the content in the file
  Usage: /files/{file_id}/data/content/update, /files/ (audio file upload pipeline)

              try:
  /files/{file_id}/data/content/update
                  VECTOR_DB_CLIENT.delete_collection(collection_name=f"file-{file.id}")
              except:
  Audio file upload pipeline
                  pass

              docs = [
                  Document(
                      page_content=form_data.content.replace("<br/>", "\n"),
                      metadata={
                          **file.meta,
                          "name": file.filename,
                          "created_by": file.user_id,
                          "file_id": file.id,
                          "source": file.filename,
                      },
                  )
              ]

              text_content = form_data.content
          elif form_data.collection_name:
  Check if the file has already been processed and save the content
  Usage: /knowledge/{id}/file/add, /knowledge/{id}/file/update

              result = VECTOR_DB_CLIENT.query(
                  collection_name=f"file-{file.id}", filter={"file_id": file.id}
              )

              if result is not None and len(result.ids[0]) > 0:
                  docs = [
                      Document(
                          page_content=result.documents[0][idx],
                          metadata=result.metadatas[0][idx],
                      )
                      for idx, id in enumerate(result.ids[0])
                  ]
              else:
                  docs = [
                      Document(
                          page_content=file.data.get("content", ""),
                          metadata={
                              **file.meta,
                              "name": file.filename,
                              "created_by": file.user_id,
                              "file_id": file.id,
                              "source": file.filename,
                          },
                      )
                  ]

              text_content = file.data.get("content", "")
          else:
  Process the file and save the content
  Usage: /files/
              file_path = file.path
              if file_path:
                  file_path = Storage.get_file(file_path)
                  loader = Loader(
                      engine=request.app.state.config.CONTENT_EXTRACTION_ENGINE,
                      DATALAB_MARKER_API_KEY=request.app.state.config.DATALAB_MARKER_API_KEY,
                      DATALAB_MARKER_LANGS=request.app.state.config.DATALAB_MARKER_LANGS,
                      DATALAB_MARKER_SKIP_CACHE=request.app.state.config.DATALAB_MARKER_SKIP_CACHE,
                      DATALAB_MARKER_FORCE_OCR=request.app.state.config.DATALAB_MARKER_FORCE_OCR,
                      DATALAB_MARKER_PAGINATE=request.app.state.config.DATALAB_MARKER_PAGINATE,
                      DATALAB_MARKER_STRIP_EXISTING_OCR=request.app.state.config.DATALAB_MARKER_STRIP_EXISTING_OCR,
                      DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION=request.app.state.config.DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION,
                      DATALAB_MARKER_USE_LLM=request.app.state.config.DATALAB_MARKER_USE_LLM,
                      DATALAB_MARKER_OUTPUT_FORMAT=request.app.state.config.DATALAB_MARKER_OUTPUT_FORMAT,
                      EXTERNAL_DOCUMENT_LOADER_URL=request.app.state.config.EXTERNAL_DOCUMENT_LOADER_URL,
                      EXTERNAL_DOCUMENT_LOADER_API_KEY=request.app.state.config.EXTERNAL_DOCUMENT_LOADER_API_KEY,
                      TIKA_SERVER_URL=request.app.state.config.TIKA_SERVER_URL,
                      DOCLING_SERVER_URL=request.app.state.config.DOCLING_SERVER_URL,
                      DOCLING_PARAMS={
                          "ocr_engine": request.app.state.config.DOCLING_OCR_ENGINE,
                          "ocr_lang": request.app.state.config.DOCLING_OCR_LANG,
                          "do_picture_description": request.app.state.config.DOCLING_DO_PICTURE_DESCRIPTION,
                          "picture_description_mode": request.app.state.config.DOCLING_PICTURE_DESCRIPTION_MODE,
                          "picture_description_local": request.app.state.config.DOCLING_PICTURE_DESCRIPTION_LOCAL,
                          "picture_description_api": request.app.state.config.DOCLING_PICTURE_DESCRIPTION_API,
                      },
                      PDF_EXTRACT_IMAGES=request.app.state.config.PDF_EXTRACT_IMAGES,
                      DOCUMENT_INTELLIGENCE_ENDPOINT=request.app.state.config.DOCUMENT_INTELLIGENCE_ENDPOINT,
                      DOCUMENT_INTELLIGENCE_KEY=request.app.state.config.DOCUMENT_INTELLIGENCE_KEY,
                      MISTRAL_OCR_API_KEY=request.app.state.config.MISTRAL_OCR_API_KEY,
                  )
                  docs = loader.load(
                      file.filename, file.meta.get("content_type"), file_path
                  )

                  docs = [
                      Document(
                          page_content=doc.page_content,
                          metadata={
                              **doc.metadata,
                              "name": file.filename,
                              "created_by": file.user_id,
                              "file_id": file.id,
                              "source": file.filename,
                          },
                      )
                      for doc in docs
                  ]
              else:
                  docs = [
                      Document(
                          page_content=file.data.get("content", ""),
                          metadata={
                              **file.meta,
                              "name": file.filename,
                              "created_by": file.user_id,
                              "file_id": file.id,
                              "source": file.filename,
                          },
                      )
                  ]
              text_content = " ".join([doc.page_content for doc in docs])

          log.debug(f"text_content: {text_content}")
          Files.update_file_data_by_id(
              file.id,
              {"content": text_content},
          )

          hash = calculate_sha256_string(text_content)
          Files.update_file_hash_by_id(file.id, hash)

          if not request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL:
              try:
                  result = save_docs_to_vector_db(
                      request,
                      docs=docs,
                      collection_name=collection_name,
                      metadata={
                          "file_id": file.id,
                          "name": file.filename,
                          "hash": hash,
                      },
                      add=(True if form_data.collection_name else False),
                      user=user,
                  )

                  if result:
                      Files.update_file_metadata_by_id(
                          file.id,
                          {
                              "collection_name": collection_name,
                          },
                      )

                      return {
                          "status": True,
                          "collection_name": collection_name,
                          "filename": file.filename,
                          "content": text_content,
                      }
              except Exception as e:
                  raise e
          else:
              return {
                  "status": True,
                  "collection_name": None,
                  "filename": file.filename,
                  "content": text_content,
              }

      except Exception as e:
          log.exception(e)
          if "No pandoc was found" in str(e):
              raise HTTPException(
                  status_code=status.HTTP_400_BAD_REQUEST,
                  detail=ERROR_MESSAGES.PANDOC_NOT_INSTALLED,
              )
          else:
              raise HTTPException(
                  status_code=status.HTTP_400_BAD_REQUEST,
                  detail=str(e),
              )

  class ProcessTextForm(BaseModel):
      name: str
      content: str
      collection_name: Optional[str] = None

  @router.post("/process/text")
  def process_text(
      request: Request,
      form_data: ProcessTextForm,
      user=Depends(get_verified_user),
  ):
      collection_name = form_data.collection_name
      if collection_name is None:
          collection_name = calculate_sha256_string(form_data.content)

      docs = [
          Document(
              page_content=form_data.content,
              metadata={"name": form_data.name, "created_by": user.id},
          )
      ]
      text_content = form_data.content
      log.debug(f"text_content: {text_content}")

      result = save_docs_to_vector_db(request, docs, collection_name, user=user)
      if result:
          return {
              "status": True,
              "collection_name": collection_name,
              "content": text_content,
          }
      else:
          raise HTTPException(
              status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail=ERROR_MESSAGES.DEFAULT(),
          )

  @router.post("/process/youtube")
  def process_youtube_video(
      request: Request, form_data: ProcessUrlForm, user=Depends(get_verified_user)
  ):
      try:
          collection_name = form_data.collection_name
          if not collection_name:
              collection_name = calculate_sha256_string(form_data.url)[:63]

          loader = YoutubeLoader(
              form_data.url,
              language=request.app.state.config.YOUTUBE_LOADER_LANGUAGE,
              proxy_url=request.app.state.config.YOUTUBE_LOADER_PROXY_URL,
          )

          docs = loader.load()
          content = " ".join([doc.page_content for doc in docs])
          log.debug(f"text_content: {content}")

          save_docs_to_vector_db(
              request, docs, collection_name, overwrite=True, user=user
          )

          return {
              "status": True,
              "collection_name": collection_name,
              "filename": form_data.url,
              "file": {
                  "data": {
                      "content": content,
                  },
                  "meta": {
                      "name": form_data.url,
                  },
              },
          }
      except Exception as e:
          log.exception(e)
          raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail=ERROR_MESSAGES.DEFAULT(e),
          )

  @router.post("/process/web")
  def process_web(
      request: Request, form_data: ProcessUrlForm, user=Depends(get_verified_user)
  ):
      try:
          collection_name = form_data.collection_name
          if not collection_name:
              collection_name = calculate_sha256_string(form_data.url)[:63]

          loader = get_web_loader(
              form_data.url,
              verify_ssl=request.app.state.config.ENABLE_WEB_LOADER_SSL_VERIFICATION,
              requests_per_second=request.app.state.config.WEB_SEARCH_CONCURRENT_REQUESTS,
          )
          docs = loader.load()
          content = " ".join([doc.page_content for doc in docs])

          log.debug(f"text_content: {content}")

          if not request.app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL:
              save_docs_to_vector_db(
                  request, docs, collection_name, overwrite=True, user=user
              )
          else:
              collection_name = None

          return {
              "status": True,
              "collection_name": collection_name,
              "filename": form_data.url,
              "file": {
                  "data": {
                      "content": content,
                  },
                  "meta": {
                      "name": form_data.url,
                      "source": form_data.url,
                  },
              },
          }
      except Exception as e:
          log.exception(e)
          raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail=ERROR_MESSAGES.DEFAULT(e),
          )

  def search_web(request: Request, engine: str, query: str) -> list[SearchResult]:
      """Search the web using a search engine and return the results as a list of SearchResult objects.
      Will look for a search engine API key in environment variables in the following order:
       - SEARXNG_QUERY_URL
       - YACY_QUERY_URL + YACY_USERNAME + YACY_PASSWORD
       - GOOGLE_PSE_API_KEY + GOOGLE_PSE_ENGINE_ID
       - BRAVE_SEARCH_API_KEY
       - KAGI_SEARCH_API_KEY
       - MOJEEK_SEARCH_API_KEY
       - BOCHA_SEARCH_API_KEY
       - SERPSTACK_API_KEY
       - SERPER_API_KEY
       - SERPLY_API_KEY
       - TAVILY_API_KEY
       - EXA_API_KEY
       - PERPLEXITY_API_KEY
       - SOUGOU_API_SID + SOUGOU_API_SK
       - SEARCHAPI_API_KEY + SEARCHAPI_ENGINE (by default google)
       - SERPAPI_API_KEY + SERPAPI_ENGINE (by default google)
      Args:
          query (str): The query to search for
      """

  TODO: add playwright to search the web
      if engine == "searxng":
          if request.app.state.config.SEARXNG_QUERY_URL:
              return search_searxng(
                  request.app.state.config.SEARXNG_QUERY_URL,
                  query,
                  request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                  request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
              )
          else:
              raise Exception("No SEARXNG_QUERY_URL found in environment variables")
      elif engine == "yacy":
          if request.app.state.config.YACY_QUERY_URL:
              return search_yacy(
                  request.app.state.config.YACY_QUERY_URL,
                  request.app.state.config.YACY_USERNAME,
                  request.app.state.config.YACY_PASSWORD,
                  query,
                  request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                  request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
              )
          else:
              raise Exception("No YACY_QUERY_URL found in environment variables")
      elif engine == "google_pse":
          if (
              request.app.state.config.GOOGLE_PSE_API_KEY
              and request.app.state.config.GOOGLE_PSE_ENGINE_ID
          ):
              return search_google_pse(
                  request.app.state.config.GOOGLE_PSE_API_KEY,
                  request.app.state.config.GOOGLE_PSE_ENGINE_ID,
                  query,
                  request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                  request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
              )
          else:
              raise Exception(
                  "No GOOGLE_PSE_API_KEY or GOOGLE_PSE_ENGINE_ID found in environment variables"
              )
      elif engine == "brave":
          if request.app.state.config.BRAVE_SEARCH_API_KEY:
              return search_brave(
                  request.app.state.config.BRAVE_SEARCH_API_KEY,
                  query,
                  request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                  request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
              )
          else:
              raise Exception("No BRAVE_SEARCH_API_KEY found in environment variables")
      elif engine == "kagi":
          if request.app.state.config.KAGI_SEARCH_API_KEY:
              return search_kagi(
                  request.app.state.config.KAGI_SEARCH_API_KEY,
                  query,
                  request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                  request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
              )
          else:
              raise Exception("No KAGI_SEARCH_API_KEY found in environment variables")
      elif engine == "mojeek":
          if request.app.state.config.MOJEEK_SEARCH_API_KEY:
              return search_mojeek(
                  request.app.state.config.MOJEEK_SEARCH_API_KEY,
                  query,
                  request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                  request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
              )
          else:
              raise Exception("No MOJEEK_SEARCH_API_KEY found in environment variables")
      elif engine == "bocha":
          if request.app.state.config.BOCHA_SEARCH_API_KEY:
              return search_bocha(
                  request.app.state.config.BOCHA_SEARCH_API_KEY,
                  query,
                  request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                  request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
              )
          else:
              raise Exception("No BOCHA_SEARCH_API_KEY found in environment variables")
      elif engine == "serpstack":
          if request.app.state.config.SERPSTACK_API_KEY:
              return search_serpstack(
                  request.app.state.config.SERPSTACK_API_KEY,
                  query,
                  request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                  request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
                  https_enabled=request.app.state.config.SERPSTACK_HTTPS,
              )
          else:
              raise Exception("No SERPSTACK_API_KEY found in environment variables")
      elif engine == "serper":
          if request.app.state.config.SERPER_API_KEY:
              return search_serper(
                  request.app.state.config.SERPER_API_KEY,
                  query,
                  request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                  request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
              )
          else:
              raise Exception("No SERPER_API_KEY found in environment variables")
      elif engine == "serply":
          if request.app.state.config.SERPLY_API_KEY:
              return search_serply(
                  request.app.state.config.SERPLY_API_KEY,
                  query,
                  request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                  request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
              )
          else:
              raise Exception("No SERPLY_API_KEY found in environment variables")
      elif engine == "duckduckgo":
          return search_duckduckgo(
              query,
              request.app.state.config.WEB_SEARCH_RESULT_COUNT,
              request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
          )
      elif engine == "tavily":
          if request.app.state.config.TAVILY_API_KEY:
              return search_tavily(
                  request.app.state.config.TAVILY_API_KEY,
                  query,
                  request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                  request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
              )
          else:
              raise Exception("No TAVILY_API_KEY found in environment variables")
      elif engine == "exa":
          if request.app.state.config.EXA_API_KEY:
              return search_exa(
                  request.app.state.config.EXA_API_KEY,
                  query,
                  request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                  request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
              )
          else:
              raise Exception("No EXA_API_KEY found in environment variables")
      elif engine == "searchapi":
          if request.app.state.config.SEARCHAPI_API_KEY:
              return search_searchapi(
                  request.app.state.config.SEARCHAPI_API_KEY,
                  request.app.state.config.SEARCHAPI_ENGINE,
                  query,
                  request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                  request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
              )
          else:
              raise Exception("No SEARCHAPI_API_KEY found in environment variables")
      elif engine == "serpapi":
          if request.app.state.config.SERPAPI_API_KEY:
              return search_serpapi(
                  request.app.state.config.SERPAPI_API_KEY,
                  request.app.state.config.SERPAPI_ENGINE,
                  query,
                  request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                  request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
              )
          else:
              raise Exception("No SERPAPI_API_KEY found in environment variables")
      elif engine == "jina":
          return search_jina(
              request.app.state.config.JINA_API_KEY,
              query,
              request.app.state.config.WEB_SEARCH_RESULT_COUNT,
          )
      elif engine == "bing":
          return search_bing(
              request.app.state.config.BING_SEARCH_V7_SUBSCRIPTION_KEY,
              request.app.state.config.BING_SEARCH_V7_ENDPOINT,
              str(DEFAULT_LOCALE),
              query,
              request.app.state.config.WEB_SEARCH_RESULT_COUNT,
              request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
          )
      elif engine == "exa":
          return search_exa(
              request.app.state.config.EXA_API_KEY,
              query,
              request.app.state.config.WEB_SEARCH_RESULT_COUNT,
              request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
          )
      elif engine == "perplexity":
          return search_perplexity(
              request.app.state.config.PERPLEXITY_API_KEY,
              query,
              request.app.state.config.WEB_SEARCH_RESULT_COUNT,
              request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
              model=request.app.state.config.PERPLEXITY_MODEL,
              search_context_usage=request.app.state.config.PERPLEXITY_SEARCH_CONTEXT_USAGE,
          )
      elif engine == "sougou":
          if (
              request.app.state.config.SOUGOU_API_SID
              and request.app.state.config.SOUGOU_API_SK
          ):
              return search_sougou(
                  request.app.state.config.SOUGOU_API_SID,
                  request.app.state.config.SOUGOU_API_SK,
                  query,
                  request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                  request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
              )
          else:
              raise Exception(
                  "No SOUGOU_API_SID or SOUGOU_API_SK found in environment variables"
              )
      elif engine == "firecrawl":
          return search_firecrawl(
              request.app.state.config.FIRECRAWL_API_BASE_URL,
              request.app.state.config.FIRECRAWL_API_KEY,
              query,
              request.app.state.config.FIRECRAWL_API_KEY,
              query,
              request.app.state.config.WEB_SEARCH_RESULT_COUNT,
              request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
          )
      elif engine == "external":
          return search_external(
              request.app.state.config.EXTERNAL_WEB_SEARCH_URL,
              request.app.state.config.EXTERNAL_WEB_SEARCH_API_KEY,
              query,
              request.app.state.config.WEB_SEARCH_RESULT_COUNT,
              request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
          )
      else:
          raise Exception("No search engine API key found in environment variables")

  @router.post("/process/web/search")
  async def process_web_search(
      request: Request, form_data: SearchForm, user=Depends(get_verified_user)
  ):

      urls = []
      try:
          logging.info(
              f"trying to web search with {request.app.state.config.WEB_SEARCH_ENGINE, form_data.queries}"
          )

          search_tasks = [
              run_in_threadpool(
                  search_web,
                  request,
                  request.app.state.config.WEB_SEARCH_ENGINE,
                  query,
              )
              for query in form_data.queries
          ]

          search_results = await asyncio.gather(*search_tasks)

          for result in search_results:
              if result:
                  for item in result:
                      if item and item.link:
                          urls.append(item.link)

          urls = list(dict.fromkeys(urls))
          log.debug(f"urls: {urls}")

      except Exception as e:
          log.exception(e)

          raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail=ERROR_MESSAGES.WEB_SEARCH_ERROR(e),
          )

      try:
          if request.app.state.config.BYPASS_WEB_SEARCH_WEB_LOADER:
              search_results = [
                  item for result in search_results for item in result if result
              ]

              docs = [
                  Document(
                      page_content=result.snippet,
                      metadata={
                          "source": result.link,
                          "title": result.title,
                          "snippet": result.snippet,
                          "link": result.link,
                      },
                  )
                  for result in search_results
                  if hasattr(result, "snippet")
              ]
          else:
              loader = get_web_loader(
                  urls,
                  verify_ssl=request.app.state.config.ENABLE_WEB_LOADER_SSL_VERIFICATION,
                  requests_per_second=request.app.state.config.WEB_SEARCH_CONCURRENT_REQUESTS,
                  trust_env=request.app.state.config.WEB_SEARCH_TRUST_ENV,
              )
              docs = await loader.aload()

          urls = [
              doc.metadata.get("source") for doc in docs if doc.metadata.get("source")
          ]  # only keep the urls returned by the loader

          if request.app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL:
              return {
                  "status": True,
                  "collection_name": None,
                  "filenames": urls,
                  "docs": [
                      {
                          "content": doc.page_content,
                          "metadata": doc.metadata,
                      }
                      for doc in docs
                  ],
                  "loaded_count": len(docs),
              }
          else:
  Create a single collection for all documents
              collection_name = (
                  f"web-search-{calculate_sha256_string('-'.join(form_data.queries))}"[
                      :63
                  ]
              )
   1 
   2 ### `open_webui/utils/middleware.py` (Funciones relevantes)
  import time
  import logging
  import sys
  import os
  import base64

  import asyncio
  from aiocache import cached
  from typing import Any, Optional
  import random
  import json
  import html
  import inspect
  import re
  import ast

  from uuid import uuid4
  from concurrent.futures import ThreadPoolExecutor

  from fastapi import Request, HTTPException
  from starlette.responses import Response, StreamingResponse

  from open_webui.models.chats import Chats
  from open_webui.models.folders import Folders
  from open_webui.models.users import Users
  from open_webui.socket.main import (
      get_event_call,
      get_event_emitter,
      get_active_status_by_user_id,
  )
  from open_webui.routers.tasks import (
      generate_queries,
      generate_title,
      generate_follow_ups,
      generate_image_prompt,
      generate_chat_tags,
  )
  from open_webui.routers.retrieval import process_web_search, SearchForm
  from open_webui.routers.images import (
      load_b64_image_data,
      image_generations,
      GenerateImageForm,
      upload_image,
  )
  from open_webui.routers.pipelines import (
      process_pipeline_inlet_filter,
      process_pipeline_outlet_filter,
  )
  from open_webui.routers.memories import query_memory, QueryMemoryForm

  from open_webui.utils.webhook import post_webhook

  from open_webui.models.users import UserModel
  from open_webui.models.functions import Functions
  from open_webui.models.models import Models

  from open_webui.retrieval.utils import get_sources_from_items

  from open_webui.utils.chat import generate_chat_completion
  from open_webui.utils.task import (
      get_task_model_id,
      rag_template,
      tools_function_calling_generation_template,
  )
  from open_webui.utils.misc import (
      deep_update,
      get_message_list,
      add_or_update_system_message,
      add_or_update_user_message,
      get_last_user_message,
      get_last_assistant_message,
      prepend_to_first_user_message_content,
      convert_logit_bias_input_to_json,
  )
  from open_webui.utils.tools import get_tools
  from open_webui.utils.plugin import load_function_module_by_id
  from open_webui.utils.filter import (
      get_sorted_filter_ids,
      process_filter_functions,
  )
  from open_webui.utils.code_interpreter import execute_code_jupyter

  from open_webui.tasks import create_task

  from open_webui.config import (
      CACHE_DIR,
      DEFAULT_TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE,
      DEFAULT_CODE_INTERPRETER_PROMPT,
  )
  from open_webui.env import (
      SRC_LOG_LEVELS,
      GLOBAL_LOG_LEVEL,
      BYPASS_MODEL_ACCESS_CONTROL,
      ENABLE_REALTIME_CHAT_SAVE,
  )
  from open_webui.constants import TASKS

  logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
  log = logging.getLogger(__name__)
  log.setLevel(SRC_LOG_LEVELS["MAIN"])

  async def chat_completion_tools_handler(
      request: Request, body: dict, extra_params: dict, user: UserModel, models, tools
  ) -> tuple[dict, dict]:
      async def get_content_from_response(response) -> Optional[str]:
          content = None
          if hasattr(response, "body_iterator"):
              async for chunk in response.body_iterator:
                  data = json.loads(chunk.decode("utf-8"))
                  content = data["choices"][0]["message"]["content"]

  Cleanup any remaining background tasks if necessary
              if response.background is not None:
                  await response.background()
          else:
              content = response["choices"][0]["message"]["content"]
          return content

      def get_tools_function_calling_payload(messages, task_model_id, content):
          user_message = get_last_user_message(messages)
          history = "\n".join(
              f"{message['role'].upper()}: \"\"\"{message['content']}\"\"\""
              for message in messages[::-1][:4]
          )

          prompt = f"History:\n{history}\nQuery: {user_message}"

          return {
              "model": task_model_id,
              "messages": [
                  {"role": "system", "content": content},
                  {"role": "user", "content": f"Query: {prompt}"},
              ],
              "stream": False,
              "metadata": {"task": str(TASKS.FUNCTION_CALLING)},
          }

      event_caller = extra_params["__event_call__"]
      metadata = extra_params["__metadata__"]

      task_model_id = get_task_model_id(
          body["model"],
          request.app.state.config.TASK_MODEL,
          request.app.state.config.TASK_MODEL_EXTERNAL,
          models,
      )

      skip_files = False
      sources = []

      specs = [tool["spec"] for tool in tools.values()]
      tools_specs = json.dumps(specs)

      if request.app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE != "":
          template = request.app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE
      else:
          template = DEFAULT_TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE

      tools_function_calling_prompt = tools_function_calling_generation_template(
          template, tools_specs
      )
      payload = get_tools_function_calling_payload(
          body["messages"], task_model_id, tools_function_calling_prompt
      )

      try:
          response = await generate_chat_completion(request, form_data=payload, user=user)
          log.debug(f"{response=}")
          content = await get_content_from_response(response)
          log.debug(f"{content=}")

          if not content:
              return body, {}

          try:
              content = content[content.find("{") : content.rfind("}") + 1]
              if not content:
                  raise Exception("No JSON object found in the response")

              result = json.loads(content)

              async def tool_call_handler(tool_call):
                  nonlocal skip_files

                  log.debug(f"{tool_call=}")

                  tool_function_name = tool_call.get("name", None)
                  if tool_function_name not in tools:
                      return body, {}

                  tool_function_params = tool_call.get("parameters", {})

                  try:
                      tool = tools[tool_function_name]

                      spec = tool.get("spec", {})
                      allowed_params = (
                          spec.get("parameters", {}).get("properties", {}).keys()
                      )
                      tool_function_params = {
                          k: v
                          for k, v in tool_function_params.items()
                          if k in allowed_params
                      }

                      if tool.get("direct", False):
                          tool_result = await event_caller(
                              {
                                  "type": "execute:tool",
                                  "data": {
                                      "id": str(uuid4()),
                                      "name": tool_function_name,
                                      "params": tool_function_params,
                                      "server": tool.get("server", {}),
                                      "session_id": metadata.get("session_id", None),
                                  },
                              }
                          )
                      else:
                          tool_function = tool["callable"]
                          tool_result = await tool_function(**tool_function_params)

                  except Exception as e:
                      tool_result = str(e)

                  tool_result_files = []
                  if isinstance(tool_result, list):
                      for item in tool_result:
  check if string
                          if isinstance(item, str) and item.startswith("data:"):
                              tool_result_files.append(item)
                              tool_result.remove(item)

                  if isinstance(tool_result, dict) or isinstance(tool_result, list):
                      tool_result = json.dumps(tool_result, indent=2)

                  if isinstance(tool_result, str):
                      tool = tools[tool_function_name]
                      tool_id = tool.get("tool_id", "")

                      tool_name = (
                          f"{tool_id}/{tool_function_name}"
                          if tool_id
                          else f"{tool_function_name}"
                      )

  Citation is enabled for this tool
                      sources.append(
                          {
                              "source": {
                                  "name": (f"TOOL:{tool_name}"),
                              },
                              "document": [tool_result],
                              "metadata": [
                                  {
                                      "source": (f"TOOL:{tool_name}"),
                                      "parameters": tool_function_params,
                                  }
                              ],
                              "tool_result": True,
                          }
                      )
  Citation is not enabled for this tool
                      body["messages"] = add_or_update_user_message(
                          f"\nTool {tool_name} Output: {tool_result}",
                          body["messages"],
                      )

                      if (
                          tools[tool_function_name]
                          .get("metadata", {})
                          .get("file_handler", False)
                      ):
                          skip_files = True

  check if "tool_calls" in result
              if result.get("tool_calls"):
                  for tool_call in result.get("tool_calls"):
                      await tool_call_handler(tool_call)
              else:
                  await tool_call_handler(result)

          except Exception as e:
              log.debug(f"Error: {e}")
              content = None
      except Exception as e:
          log.debug(f"Error: {e}")
          content = None

      log.debug(f"tool_contexts: {sources}")

      if skip_files and "files" in body.get("metadata", {}):
          del body["metadata"]["files"]

      return body, {"sources": sources}

  async def chat_memory_handler(
      request: Request, form_data: dict, extra_params: dict, user
  ):
      try:
          results = await query_memory(
              request,
              QueryMemoryForm(
                  **{
                      "content": get_last_user_message(form_data["messages"]) or "",
                      "k": 3,
                  }
              ),
              user,
          )
      except Exception as e:
          log.debug(e)
          results = None

      user_context = ""
      if results and hasattr(results, "documents"):
          if results.documents and len(results.documents) > 0:
              for doc_idx, doc in enumerate(results.documents[0]):
                  created_at_date = "Unknown Date"

                  if results.metadatas[0][doc_idx].get("created_at"):
                      created_at_timestamp = results.metadatas[0][doc_idx]["created_at"]
                      created_at_date = time.strftime(
                          "%Y-%m-%d", time.localtime(created_at_timestamp)
                      )

                  user_context += f"{doc_idx + 1}. [{created_at_date}] {doc}\n"

      form_data["messages"] = add_or_update_system_message(
          f"User Context:\n{user_context}\n", form_data["messages"], append=True
      )

      return form_data

  async def chat_web_search_handler(
      request: Request, form_data: dict, extra_params: dict, user
  ):
      event_emitter = extra_params["__event_emitter__"]
      await event_emitter(
          {
              "type": "status",
              "data": {
                  "action": "web_search",
                  "description": "Generating search query",
                  "done": False,
              },
          }
      )

      messages = form_data["messages"]
      user_message = get_last_user_message(messages)

      queries = []
      try:
          res = await generate_queries(
              request,
              {
                  "model": form_data["model"],
                  "messages": messages,
                  "prompt": user_message,
                  "type": "web_search",
              },
              user,
          )

          response = res["choices"][0]["message"]["content"]

          try:
              bracket_start = response.find("{")
              bracket_end = response.rfind("}") + 1

              if bracket_start == -1 or bracket_end == -1:
                  raise Exception("No JSON object found in the response")

              response = response[bracket_start:bracket_end]
              queries = json.loads(response)
              queries = queries.get("queries", [])
          except Exception as e:
              queries = [response]

      except Exception as e:
          log.exception(e)
          queries = [user_message]

  Check if generated queries are empty
      if len(queries) == 1 and queries[0].strip() == "":
          queries = [user_message]

  Check if queries are not found
      if len(queries) == 0:
          await event_emitter(
              {
                  "type": "status",
                  "data": {
                      "action": "web_search",
                      "description": "No search query generated",
                      "done": True,
                  },
              }
          )
          return form_data

      await event_emitter(
          {
              "type": "status",
              "data": {
                  "action": "web_search",
                  "description": "Searching the web",
                  "done": False,
              },
          }
      )

      try:
          results = await process_web_search(
              request,
              SearchForm(queries=queries),
              user=user,
          )

          if results:
              files = form_data.get("files", [])

              if results.get("collection_names"):
                  for col_idx, collection_name in enumerate(
                      results.get("collection_names")
                  ):
                      files.append(
                          {
                              "collection_name": collection_name,
                              "name": ", ".join(queries),
                              "type": "web_search",
                              "urls": results["filenames"],
                              "queries": queries,
                          }
                      )
              elif results.get("docs"):
  Invoked when bypass embedding and retrieval is set to True
                  docs = results["docs"]
                  files.append(
                      {
                          "docs": docs,
                          "name": ", ".join(queries),
                          "type": "web_search",
                          "urls": results["filenames"],
                          "queries": queries,
                      }
                  )

              form_data["files"] = files

              await event_emitter(
                  {
                      "type": "status",
                      "data": {
                          "action": "web_search",
                          "description": "Searched {{count}} sites",
                          "urls": results["filenames"],
                          "done": True,
                      },
                  }
              )
          else:
              await event_emitter(
                  {
                      "type": "status",
                      "data": {
                          "action": "web_search",
                          "description": "No search results found",
                          "done": True,
                          "error": True,
                      },
                  }
              )

      except Exception as e:
          log.exception(e)
          await event_emitter(
              {
                  "type": "status",
                  "data": {
                      "action": "web_search",
                      "description": "An error occurred while searching the web",
                      "queries": queries,
                      "done": True,
                      "error": True,
                  },
              }
          )

      return form_data

  async def chat_image_generation_handler(
      request: Request, form_data: dict, extra_params: dict, user
  ):
      __event_emitter__ = extra_params["__event_emitter__"]
      await __event_emitter__(
          {
              "type": "status",
              "data": {"description": "Generating an image", "done": False},
          }
      )

      messages = form_data["messages"]
      user_message = get_last_user_message(messages)

      prompt = user_message
      negative_prompt = ""

      if request.app.state.config.ENABLE_IMAGE_PROMPT_GENERATION:
          try:
              res = await generate_image_prompt(
                  request,
                  {
                      "model": form_data["model"],
                      "messages": messages,
                  },
                  user,
              )

              response = res["choices"][0]["message"]["content"]

              try:
                  bracket_start = response.find("{")
                  bracket_end = response.rfind("}") + 1

                  if bracket_start == -1 or bracket_end == -1:
                      raise Exception("No JSON object found in the response")

                  response = response[bracket_start:bracket_end]
                  response = json.loads(response)
                  prompt = response.get("prompt", [])
              except Exception as e:
                  prompt = user_message

          except Exception as e:
              log.exception(e)
              prompt = user_message

      system_message_content = ""

      try:
          images = await image_generations(
              request=request,
              form_data=GenerateImageForm(**{"prompt": prompt}),
              user=user,
          )

          await __event_emitter__(
              {
                  "type": "status",
                  "data": {"description": "Generated an image", "done": True},
              }
          )

          await __event_emitter__(
              {
                  "type": "files",
                  "data": {
                      "files": [
                          {
                              "type": "image",
                              "url": image["url"],
                          }
                          for image in images
                      ]
                  },
              }
          )

          system_message_content = "<context>User is shown the generated image, tell the user that the image has been generated</context>"
      except Exception as e:
          log.exception(e)
          await __event_emitter__(
              {
                  "type": "status",
                  "data": {
                      "description": f"An error occurred while generating an image",
                      "done": True,
                  },
              }
          )

          system_message_content = "<context>Unable to generate an image, tell the user that an error occurred</context>"

      if system_message_content:
          form_data["messages"] = add_or_update_system_message(
              system_message_content, form_data["messages"]
          )

      return form_data

  async def chat_completion_files_handler(
      request: Request, body: dict, user: UserModel
  ) -> tuple[dict, dict[str, list]]:
      sources = []

      if files := body.get("metadata", {}).get("files", None):
          queries = []
          try:
              queries_response = await generate_queries(
                  request,
                  {
                      "model": body["model"],
                      "messages": body["messages"],
                      "type": "retrieval",
                  },
                  user,
              )
              queries_response = queries_response["choices"][0]["message"]["content"]

              try:
                  bracket_start = queries_response.find("{")
                  bracket_end = queries_response.rfind("}") + 1

                  if bracket_start == -1 or bracket_end == -1:
                      raise Exception("No JSON object found in the response")

                  queries_response = queries_response[bracket_start:bracket_end]
                  queries_response = json.loads(queries_response)
              except Exception as e:
                  queries_response = {"queries": [queries_response]}

              queries = queries_response.get("queries", [])
          except:
              pass

          if len(queries) == 0:
              queries = [get_last_user_message(body["messages"])]

          try:
  Offload get_sources_from_items to a separate thread
              loop = asyncio.get_running_loop()
              with ThreadPoolExecutor() as executor:
                  sources = await loop.run_in_executor(
                      executor,
                      lambda: get_sources_from_items(
                          request=request,
                          items=files,
                          queries=queries,
                          embedding_function=lambda query, prefix: request.app.state.EMBEDDING_FUNCTION(
                              query, prefix=prefix, user=user
                          ),
                          k=request.app.state.config.TOP_K,
                          reranking_function=(
                              (
                                  lambda sentences: request.app.state.RERANKING_FUNCTION(
                                      sentences, user=user
                                  )
                              )
                              if request.app.state.RERANKING_FUNCTION
                              else None
                          ),
                          k_reranker=request.app.state.config.TOP_K_RERANKER,
                          r=request.app.state.config.RELEVANCE_THRESHOLD,
                          hybrid_bm25_weight=request.app.state.config.HYBRID_BM25_WEIGHT,
                          hybrid_search=request.app.state.config.ENABLE_RAG_HYBRID_SEARCH,
                          full_context=request.app.state.config.RAG_FULL_CONTEXT,
                          user=user,
                      ),
                  )
          except Exception as e:
              log.exception(e)

          log.debug(f"rag_contexts:sources: {sources}")

      return body, {"sources": sources}

  def apply_params_to_form_data(form_data, model):
      params = form_data.pop("params", {})
      custom_params = params.pop("custom_params", {})

      open_webui_params = {
          "stream_response": bool,
          "function_calling": str,
          "system": str,
      }

      for key in list(params.keys()):
          if key in open_webui_params:
              del params[key]

      if custom_params:
  Attempt to parse custom_params if they are strings
          for key, value in custom_params.items():
              if isinstance(value, str):
                  try:
  Attempt to parse the string as JSON
                      custom_params[key] = json.loads(value)
                  except json.JSONDecodeError:
  If it fails, keep the original string
                      pass

  If custom_params are provided, merge them into params
          params = deep_update(params, custom_params)

      if model.get("owned_by") == "ollama":
  Ollama specific parameters
          form_data["options"] = params
      else:
          if isinstance(params, dict):
              for key, value in params.items():
                  if value is not None:
                      form_data[key] = value

          if "logit_bias" in params and params["logit_bias"] is not None:
              try:
                  form_data["logit_bias"] = json.loads(
                      convert_logit_bias_input_to_json(params["logit_bias"])
                  )
              except Exception as e:
                  log.exception(f"Error parsing logit_bias: {e}")

      return form_data

  async def process_chat_payload(request, form_data, user, metadata, model):
  Pipeline Inlet -> Filter Inlet -> Chat Memory -> Chat Web Search -> Chat Image Generation
  -> Chat Code Interpreter (Form Data Update) -> (Default) Chat Tools Function Calling
  -> Chat Files

      form_data = apply_params_to_form_data(form_data, model)
      log.debug(f"form_data: {form_data}")

      event_emitter = get_event_emitter(metadata)
      event_call = get_event_call(metadata)

      extra_params = {
          "__event_emitter__": event_emitter,
          "__event_call__": event_call,
          "__user__": user.model_dump() if isinstance(user, UserModel) else {},
          "__metadata__": metadata,
          "__request__": request,
          "__model__": model,
      }

  Initialize events to store additional event to be sent to the client
  Initialize contexts and citation
      if getattr(request.state, "direct", False) and hasattr(request.state, "model"):
          models = {
              request.state.model["id"]: request.state.model,
          }
      else:
          models = request.app.state.MODELS

      task_model_id = get_task_model_id(
          form_data["model"],
          request.app.state.config.TASK_MODEL,
          request.app.state.config.TASK_MODEL_EXTERNAL,
          models,
      )

      events = []
      sources = []

  Folder "Project" handling
  Check if the request has chat_id and is inside of a folder
      chat_id = metadata.get("chat_id", None)
      if chat_id and user:
          chat = Chats.get_chat_by_id_and_user_id(chat_id, user.id)
          if chat and chat.folder_id:
              folder = Folders.get_folder_by_id_and_user_id(chat.folder_id, user.id)

              if folder and folder.data:
                  if "system_prompt" in folder.data:
                      form_data["messages"] = add_or_update_system_message(
                          folder.data["system_prompt"], form_data["messages"]
                      )
                  if "files" in folder.data:
                      form_data["files"] = [
                          *folder.data["files"],
                          *form_data.get("files", []),
                      ]

  Model "Knowledge" handling
      user_message = get_last_user_message(form_data["messages"])
      model_knowledge = model.get("info", {}).get("meta", {}).get("knowledge", False)

      if model_knowledge:
          await event_emitter(
              {
                  "type": "status",
                  "data": {
                      "action": "knowledge_search",
                      "query": user_message,
                      "done": False,
                  },
              }
          )

          knowledge_files = []
          for item in model_knowledge:
              if item.get("collection_name"):
                  knowledge_files.append(
                      {
                          "id": item.get("collection_name"),
                          "name": item.get("name"),
                          "legacy": True,
                      }
                  )
              elif item.get("collection_names"):
                  knowledge_files.append(
                      {
                          "name": item.get("name"),
                          "type": "collection",
                          "collection_names": item.get("collection_names"),
                          "legacy": True,
                      }
                  )
              else:
                  knowledge_files.append(item)

          files = form_data.get("files", [])
          files.extend(knowledge_files)
          form_data["files"] = files

      variables = form_data.pop("variables", None)

  Process the form_data through the pipeline
      try:
          form_data = await process_pipeline_inlet_filter(
              request, form_data, user, models
          )
      except Exception as e:
          raise e

      try:
          filter_functions = [
              Functions.get_function_by_id(filter_id)
              for filter_id in get_sorted_filter_ids(
                  request, model, metadata.get("filter_ids", [])
              )
          ]

          form_data, flags = await process_filter_functions(
              request=request,
              filter_functions=filter_functions,
              filter_type="inlet",
              form_data=form_data,
              extra_params=extra_params,
          )
      except Exception as e:
          raise Exception(f"Error: {e}")

      features = form_data.pop("features", None)
      if features:
          if "memory" in features and features["memory"]:
              form_data = await chat_memory_handler(
                  request, form_data, extra_params, user
              )

          if "web_search" in features and features["web_search"]:
              form_data = await chat_web_search_handler(
                  request, form_data, extra_params, user
              )

          if "image_generation" in features and features["image_generation"]:
              form_data = await chat_image_generation_handler(
                  request, form_data, extra_params, user
              )

          if "code_interpreter" in features and features["code_interpreter"]:
              form_data["messages"] = add_or_update_user_message(
                  (
                      request.app.state.config.CODE_INTERPRETER_PROMPT_TEMPLATE
                      if request.app.state.config.CODE_INTERPRETER_PROMPT_TEMPLATE != ""
                      else DEFAULT_CODE_INTERPRETER_PROMPT
                  ),
                  form_data["messages"],
              )

      tool_ids = form_data.pop("tool_ids", None)
      files = form_data.pop("files", None)

  Remove files duplicates
      if files:
          files = list({json.dumps(f, sort_keys=True): f for f in files}.values())

      metadata = {
          **metadata,
          "tool_ids": tool_ids,
          "files": files,
      }
      form_data["metadata"] = metadata

  Server side tools
      tool_ids = metadata.get("tool_ids", None)
  Client side tools
      tool_servers = metadata.get("tool_servers", None)

      log.debug(f"{tool_ids=}")
      log.debug(f"{tool_servers=}")

      tools_dict = {}

      if tool_ids:
          tools_dict = get_tools(
              request,
              tool_ids,
              user,
              {
                  **extra_params,
                  "__model__": models[task_model_id],
                  "__messages__": form_data["messages"],
                  "__files__": metadata.get("files", []),
              },
          )

      if tool_servers:
          for tool_server in tool_servers:
              tool_specs = tool_server.pop("specs", [])

              for tool in tool_specs:
                  tools_dict[tool["name"]] = {
                      "spec": tool,
                      "direct": True,
                      "server": tool_server,
                  }

      if tools_dict:
          if metadata.get("function_calling") == "native":
  If the function calling is native, then call the tools function calling handler
              metadata["tools"] = tools_dict
              form_data["tools"] = [
                  {"type": "function", "function": tool.get("spec", {})}
                  for tool in tools_dict.values()
              ]
          else:
  If the function calling is not native, then call the tools function calling handler
              try:
                  form_data, flags = await chat_completion_tools_handler(
                      request, form_data, extra_params, user, models, tools_dict
                  )
                  sources.extend(flags.get("sources", []))
              except Exception as e:
                  log.exception(e)

      try:
          form_data, flags = await chat_completion_files_handler(request, form_data, user)
          sources.extend(flags.get("sources", []))
      except Exception as e:
          log.exception(e)

  If context is not empty, insert it into the messages
      if len(sources) > 0:
          context_string = ""
          citation_idx_map = {}

          for source in sources:
              is_tool_result = source.get("tool_result", False)

              if "document" in source and not is_tool_result:
                  for document_text, document_metadata in zip(
                      source["document"], source["metadata"]
                  ):
                      source_name = source.get("source", {}).get("name", None)
                      source_id = (
                          document_metadata.get("source", None)
                          or source.get("source", {}).get("id", None)
                          or "N/A"
                      )

                      if source_id not in citation_idx_map:
                          citation_idx_map[source_id] = len(citation_idx_map) + 1

                      context_string += (
                          f'<source id="{citation_idx_map[source_id]}"'
                           + (f' name="{source_name}"' if source_name else "")
                           + f">{document_text}</source>\n"
                      )

          context_string = context_string.strip()

          prompt = get_last_user_message(form_data["messages"])
          if prompt is None:
              raise Exception("No user message found")

          if context_string == "":
              if request.app.state.config.RELEVANCE_THRESHOLD == 0:
                  log.debug(
                      f"With a 0 relevancy threshold for RAG, the context cannot be empty"
                  )
          else:
  Workaround for Ollama 2.0+ system prompt issue
  TODO: replace with add_or_update_system_message
              if model.get("owned_by") == "ollama":
                  form_data["messages"] = prepend_to_first_user_message_content(
                      rag_template(
                          request.app.state.config.RAG_TEMPLATE, context_string, prompt
                      ),
                      form_data["messages"],
                  )
              else:
                  form_data["messages"] = add_or_update_system_message(
                      rag_template(
                          request.app.state.config.RAG_TEMPLATE, context_string, prompt
                      ),
                      form_data["messages"],
                  )

  If there are citations, add them to the data_items
      sources = [
          source
          for source in sources
          if source.get("source", {}).get("name", "")
          or source.get("source", {}).get("id", "")
      ]

      if len(sources) > 0:
          events.append({"sources": sources})

      if model_knowledge:
          await event_emitter(
              {
                  "type": "status",
                  "data": {
                      "action": "knowledge_search",
                      "query": user_message,
                      "done": True,
                      "hidden": True,
                  },
              }
              )

      return form_data, metadata, events

  async def process_chat_response(
      request, response, form_data, user, metadata, model, events, tasks
  ):
      async def background_tasks_handler():
          message_map = Chats.get_messages_by_chat_id(metadata["chat_id"])
          message = message_map.get(metadata["message_id"]) if message_map else None

          if message:
              message_list = get_message_list(message_map, metadata["message_id"])

  Remove details tags and files from the messages.
  as get_message_list creates a new list, it does not affect
  the original messages outside of this handler

              messages = []
              for message in message_list:
                  content = message.get("content", "")
                  if isinstance(content, list):
                      for item in content:
                          if item.get("type") == "text":
                              content = item["text"]
                              break

                  if isinstance(content, str):
                      content = re.sub(
                          r"<details\b[^>]>.?</details>|!\[.*?\]\(.*?\)",
                          "",
                          content,
                          flags=re.S | re.I,
                      ).strip()

                  messages.append(
                      {
                          **message,
                          "role": message.get(
                              "role", "assistant"
                          ),  # Safe fallback for missing role
                          "content": content,
                      }
                  )

              if tasks and messages:
                  if (
                      TASKS.FOLLOW_UP_GENERATION in tasks
                      and tasks[TASKS.FOLLOW_UP_GENERATION]
                  ):
                      res = await generate_follow_ups(
                          request,
                          {
                              "model": message["model"],
                              "messages": messages,
                              "message_id": metadata["message_id"],
                              "chat_id": metadata["chat_id"],
                          },
                          user,
                      )

                      if res and isinstance(res, dict):
                          if len(res.get("choices", [])) == 1:
                              follow_ups_string = (
                                  res.get("choices", [])[0]
                                  .get("message", {})
                                  .get("content", "")
                              )
                          else:
                              follow_ups_string = ""

                          follow_ups_string = follow_ups_string[
                              follow_ups_string.find("{") : follow_ups_string.rfind("}")
                               + 1
                          ]

                          try:
                              follow_ups = json.loads(follow_ups_string).get(
                                  "follow_ups", []
                              )

                              Chats.upsert_message_to_chat_by_id_and_message_id(
                                  metadata["chat_id"],
                                  metadata["message_id"],
                                  {
                                      "followUps": follow_ups,
                                  },
                              )

                              await event_emitter(
                                  {
                                      "type": "chat:message:follow_ups",
                                      "data": {
                                          "follow_ups": follow_ups,
                                      },
                                  }
                              )
                          except Exception as e:
                              pass

                  if TASKS.TITLE_GENERATION in tasks:
                      user_message = get_last_user_message(messages)
                      if user_message and len(user_message) > 100:
                          user_message = user_message[:100] + "..."

                      if tasks[TASKS.TITLE_GENERATION]:

                          res = await generate_title(
                              request,
                              {
                                  "model": message["model"],
                                  "messages": messages,
                                  "chat_id": metadata["chat_id"],
                              },
                              user,
                          )

                          if res and isinstance(res, dict):
                              if len(res.get("choices", [])) == 1:
                                  title_string = (
                                      res.get("choices", [])[0]
                                      .get("message", {})
                                      .get(
                                          "content", message.get("content", user_message)
                                      )
                                  )
                              else:
                                  title_string = ""

                              title_string = title_string[
                                  title_string.find("{") : title_string.rfind("}") + 1
                              ]

                              try:
                                  title = json.loads(title_string).get(
                                      "title", user_message
                                  )
                              except Exception as e:
                                  title = ""

                              if not title:
                                  title = messages[0].get("content", user_message)

                              Chats.update_chat_title_by_id(metadata["chat_id"], title)

                              await event_emitter(
                                  {
                                      "type": "chat:title",
                                      "data": title,
                                  }
                              )
                      elif len(messages) == 2:
                          title = messages[0].get("content", user_message)

                          Chats.update_chat_title_by_id(metadata["chat_id"], title)

                          await event_emitter(
                              {
                                  "type": "chat:title",
                                  "data": message.get("content", user_message),
                              }
                          )

                  if TASKS.TAGS_GENERATION in tasks and tasks[TASKS.TAGS_GENERATION]:
                      res = await generate_chat_tags(
                          request,
                          {
                              "model": message["model"],
                              "messages": messages,
                              "chat_id": metadata["chat_id"],
                          },
                          user,
                      )

                      if res and isinstance(res, dict):
                          if len(res.get("choices", [])) == 1:
                              tags_string = (
                                  res.get("choices", [])[0]
                                  .get("message", {})
                                  .get("content", "")
                              )
                          else:
                              tags_string = ""

                          tags_string = tags_string[
                              tags_string.find("{") : tags_string.rfind("}") + 1
                          ]

                          try:
                              tags = json.loads(tags_string).get("tags", [])
                              Chats.update_chat_tags_by_id(
                                  metadata["chat_id"], tags, user
                              )

                              await event_emitter(
                                  {
                                      "type": "chat:tags",
                                      "data": tags,
                                  }
                              )
                          except Exception as e:
                              pass

      event_emitter = None
      event_caller = None
      if (
          "session_id" in metadata
          and metadata["session_id"]
          and "chat_id" in metadata
          and metadata["chat_id"]
          and "message_id" in metadata
          and metadata["message_id"]
      ):
          event_emitter = get_event_emitter(metadata)
          event_caller = get_event_call(metadata)

  Non-streaming response
      if not isinstance(response, StreamingResponse):
          if event_emitter:
              if "error" in response:
                  error = response["error"].get("detail", response["error"])
                  Chats.upsert_message_to_chat_by_id_and_message_id(
                      metadata["chat_id"],
                      metadata["message_id"],
                      {
                          "error": {"content": error},
                      },
                  )

              if "selected_model_id" in response:
                  Chats.upsert_message_to_chat_by_id_and_message_id(
                      metadata["chat_id"],
                      metadata["message_id"],
                      {
                          "selectedModelId": response["selected_model_id"],
                      },
                  )

              choices = response.get("choices", [])
              if choices and choices[0].get("message", {}).get("content"):
                  content = response["choices"][0]["message"]["content"]

                  if content:

                      await event_emitter(
                          {
                              "type": "chat:completion",
                              "data": response,
                          }
                      )

                      title = Chats.get_chat_title_by_id(metadata["chat_id"])

                      await event_emitter(
                          {
                              "type": "chat:completion",
                              "data": {
                                  "done": True,
                                  "content": content,
                                  "title": title,
                              },
                          }
                      )

  Save message in the database
                      Chats.upsert_message_to_chat_by_id_and_message_id(
                          metadata["chat_id"],
                          metadata["message_id"],
                          {
                              "role": "assistant",
                              "content": content,
                          },
                      )

  Send a webhook notification if the user is not active
                      if not get_active_status_by_user_id(user.id):
                          webhook_url = Users.get_user_webhook_url_by_id(user.id)
                          if webhook_url:
                              post_webhook(
                                  request.app.state.WEBUI_NAME,
                                  webhook_url,
                                  f"{title} - {request.app.state.config.WEBUI_URL}/c/{metadata['chat_id']}\n\n{content}",
                                  {
                                      "action": "chat",
                                      "message": content,
                                      "title": title,
                                      "url": f"{request.app.state.config.WEBUI_URL}/c/{metadata['chat_id']}",
                                  },
                              )

                      await background_tasks_handler()

              if events and isinstance(events, list) and isinstance(response, dict):
                  extra_response = {}
                  for event in events:
                      if isinstance(event, dict):
                          extra_response.update(event)
                      else:
                          extra_response[event] = True

                  response = {
                      **extra_response,
                      **response,
                  }

              return response
          else:
              if events and isinstance(events, list) and isinstance(response, dict):
                  extra_response = {}
                  for event in events:
                      if isinstance(event, dict):
                          extra_response.update(event)
                      else:
                          extra_response[event] = True

                  response = {
                      **extra_response,
                      **response,
                  }

              return response

  Non standard response
      if not any(
          content_type in response.headers["Content-Type"]
          for content_type in ["text/event-stream", "application/x-ndjson"]
      ):
          return response

      extra_params = {
          "__event_emitter__": event_emitter,
          "__event_call__": event_caller,
          "__user__": user.model_dump() if isinstance(user, UserModel) else {},
          "__metadata__": metadata,
          "__request__": request,
          "__model__": model,
      }
      filter_functions = [
          Functions.get_function_by_id(filter_id)
          for filter_id in get_sorted_filter_ids(
              request, model, metadata.get("filter_ids", [])
          )
      ]

  Streaming response
      if event_emitter and event_caller:
          task_id = str(uuid4())  # Create a unique task ID.
          model_id = form_data.get("model", "")

          Chats.upsert_message_to_chat_by_id_and_message_id(
              metadata["chat_id"],
              metadata["message_id"],
              {
                  "model": model_id,
              },
          )

          def split_content_and_whitespace(content):
              content_stripped = content.rstrip()
              original_whitespace = (
                  content[len(content_stripped) :]
                  if len(content) > len(content_stripped)
                  else ""
              )
              return content_stripped, original_whitespace

          def is_opening_code_block(content):
              backtick_segments = content.split("
  `")
  Even number of segments means the last backticks are opening a new block
              return len(backtick_segments) > 1 and len(backtick_segments) % 2 == 0

  Handle as a background task
          async def response_handler(response, events):
              def serialize_content_blocks(content_blocks, raw=False):
                  content = ""

                  for block in content_blocks:
                      if block["type"] == "text":
                          content = f"{content}{block['content'].strip()}\n"
                      elif block["type"] == "tool_calls":
                          attributes = block.get("attributes", {})

                          tool_calls = block.get("content", [])
                          results = block.get("results", [])

                          if results:

                              tool_calls_display_content = ""
                              for tool_call in tool_calls:

                                  tool_call_id = tool_call.get("id", "")
                                  tool_name = tool_call.get("function", {}).get(
                                      "name", ""
                                  )
                                  tool_arguments = tool_call.get("function", {}).get(
                                      "arguments", ""
                                  )

                                  tool_result = None
                                  tool_result_files = None
                                  for result in results:
                                      if tool_call_id == result.get("tool_call_id", ""):
                                          tool_result = result.get("content", None)
                                          tool_result_files = result.get("files", None)
                                          break

                                  if tool_result:
                                      tool_calls_display_content = f'{tool_calls_display_content}\n<details type="tool_calls" done="true" id="{tool_call_id}" name="{tool_name}"
  arguments="{html.escape(json.dumps(tool_arguments))}" result="{html.escape(json.dumps(tool_result, ensure_ascii=False))}" files="{html.escape(json.dumps(tool_result_files)) if tool_result_files else
  ""}">\n<summary>Tool Executed</summary>\n</details>\n'
                                  else:
                                      tool_calls_display_content = f'{tool_calls_display_content}\n<details type="tool_calls" done="false" id="{tool_call_id}" name="{tool_name}"
  arguments="{html.escape(json.dumps(tool_arguments))}">\n<summary>Executing...</summary>\n</details>'

                              if not raw:
                                  content = f"{content}\n{tool_calls_display_content}\n\n"
                          else:
                              tool_calls_display_content = ""

                              for tool_call in tool_calls:
                                  tool_call_id = tool_call.get("id", "")
                                  tool_name = tool_call.get("function", {}).get(
                                      "name", ""
                                  )
                                  tool_arguments = tool_call.get("function", {}).get(
                                      "arguments", ""
                                  )

                                  tool_calls_display_content = f'{tool_calls_display_content}\n<details type="tool_calls" done="false" id="{tool_call_id}" name="{tool_name}"
  arguments="{html.escape(json.dumps(tool_arguments))}">\n<summary>Executing...</summary>\n</details>'

                              if not raw:
                                  content = f"{content}\n{tool_calls_display_content}\n\n"

                      elif block["type"] == "reasoning":
                          reasoning_display_content = "\n".join(
                              (f"> {line}" if not line.startswith(">") else line)
                              for line in block["content"].splitlines()
                          )

                          reasoning_duration = block.get("duration", None)

                          if reasoning_duration is not None:
                              if raw:
                                  content = f'{content}\n{block["start_tag"]}{block["content"]}{block["end_tag"]}\n'
                              else:
                                  content = f'{content}\n<details type="reasoning" done="true" duration="{reasoning_duration}">\n<summary>Thought for {reasoning_duration}
  seconds</summary>\n{reasoning_display_content}\n</details>\n'
                          else:
                              if raw:
                                  content = f'{content}\n{block["start_tag"]}{block["content"]}{block["end_tag"]}\n'
                              else:
                                  content = f'{content}\n<details type="reasoning" done="false">\n<summary>Thinking…</summary>\n{reasoning_display_content}\n</details>\n'

                      elif block["type"] == "code_interpreter":
                          attributes = block.get("attributes", {})
                          output = block.get("output", None)
                          lang = attributes.get("lang", "")

                          content_stripped, original_whitespace = (
                              split_content_and_whitespace(content)
                          )
                          if is_opening_code_block(content_stripped):
  Remove trailing backticks that would open a new block
                              content = (
                                  content_stripped.rstrip("`").rstrip()
                                   + original_whitespace
                              )
                          else:
  Keep content as is - either closing backticks or no backticks
                              content = content_stripped + original_whitespace

                          if output:
                              output = html.escape(json.dumps(output))

                              if raw:
                                  content = f'{content}\n<code_interpreter type="code" lang="{lang}">\n{block["content"]}\n</code_interpreter>\n`output\n{output}\n
  `\n'
                              else:
                                  content = f'{content}\n<details type="code_interpreter" done="true" output="{output}">\n<summary>Analyzed</summary>\n`{lang}\n{block["content"]}\n
  `\n</details>\n'
                          else:
                              if raw:
                                  content = f'{content}\n<code_interpreter type="code" lang="{lang}">\n{block["content"]}\n</code_interpreter>\n'
                              else:
                                  content = f'{content}\n<details type="code_interpreter" done="false">\n<summary>Analyzing...</summary>\n`{lang}\n{block["content"]}\n
  `\n</details>\n'

                      else:
                          block_content = str(block["content"]).strip()
                          content = f"{content}{block['type']}: {block_content}\n"

                  return content.strip()

              def convert_content_blocks_to_messages(content_blocks):
                  messages = []

                  temp_blocks = []
                  for idx, block in enumerate(content_blocks):
                      if block["type"] == "tool_calls":
                          messages.append(
                              {
                                  "role": "assistant",
                                  "content": serialize_content_blocks(temp_blocks),
                                  "tool_calls": block.get("content"),
                              }
                          )

                          results = block.get("results", [])

                          for result in results:
                              messages.append(
                                  {
                                      "role": "tool",
                                      "tool_call_id": result["tool_call_id"],
                                      "content": result["content"],
                                  }
                              )
                          temp_blocks = []
                      else:
                          temp_blocks.append(block)

                  if temp_blocks:
                      content = serialize_content_blocks(temp_blocks)
                      if content:
                          messages.append(
                              {
                                  "role": "assistant",
                                  "content": content,
                              }
                          )

                  return messages

              def tag_content_handler(content_type, tags, content, content_blocks):
                  end_flag = False

                  def extract_attributes(tag_content):
                      """Extract attributes from a tag if they exist."""
                      attributes = {}
                      if not tag_content:  # Ensure tag_content is not None
                          return attributes
  Match attributes in the format: key="value" (ignores single quotes for simplicity)
                      matches = re.findall(r'(\w+)\s*=\s*"([^"]+)"', tag_content)
                      for key, value in matches:
                          attributes[key] = value
                      return attributes

                  if content_blocks[-1]["type"] == "text":
                      for start_tag, end_tag in tags:

                          start_tag_pattern = rf"{re.escape(start_tag)}"
                          if start_tag.startswith("<") and start_tag.endswith(">"):
  Match start tag e.g., <tag> or <tag attr="value">
  remove both '<' and '>' from start_tag
  Match start tag with attributes
                              start_tag_pattern = (
                                  rf"<{re.escape(start_tag[1:-1])}(\s.*?)?>"
                              )

                          match = re.search(start_tag_pattern, content)
                          if match:
                              attr_content = (
                                  match.group(1) if match.group(1) else ""
                              )  # Ensure it's not None
                              attributes = extract_attributes(
                                  attr_content
                              )  # Extract attributes safely

  Capture everything before and after the matched tag
                              before_tag = content[
                                  : match.start()
                              ]  # Content before opening tag
                              after_tag = content[
                                  match.end() :
                              ]  # Content after opening tag

  Remove the start tag and after from the currently handling text block
                              content_blocks[-1]["content"] = content_blocks[-1][
                                  "content"
                              ].replace(match.group(0) + after_tag, "")

                              if before_tag:
                                  content_blocks[-1]["content"] = before_tag

                              if not content_blocks[-1]["content"]:
                                  content_blocks.pop()

  Append the new block
                              content_blocks.append(
                                  {
                                      "type": content_type,
                                      "start_tag": start_tag,
                                      "end_tag": end_tag,
                                      "attributes": attributes,
                                      "content": "",
                                      "started_at": time.time(),
                                  }
                              )

                              if after_tag:
                                  content_blocks[-1]["content"] = after_tag
                                  tag_content_handler(
                                      content_type, tags, after_tag, content_blocks
                                  )

                              break
                  elif content_blocks[-1]["type"] == content_type:
                      start_tag = content_blocks[-1]["start_tag"]
                      end_tag = content_blocks[-1]["end_tag"]

                      if end_tag.startswith("<") and end_tag.endswith(">"):
  Match end tag e.g., </tag>
                          end_tag_pattern = rf"{re.escape(end_tag)}"
                      else:
  Handle cases where end_tag is just a tag name
                          end_tag_pattern = rf"{re.escape(end_tag)}"

  Check if the content has the end tag
                      if re.search(end_tag_pattern, content):
                          end_flag = True

                          block_content = content_blocks[-1]["content"]
  Strip start and end tags from the content
                          start_tag_pattern = rf"<{re.escape(start_tag)}(.*?)>"
                          block_content = re.sub(
                              start_tag_pattern, "", block_content
                          ).strip()

                          end_tag_regex = re.compile(end_tag_pattern, re.DOTALL)
                          split_content = end_tag_regex.split(block_content, maxsplit=1)

  Content inside the tag
                          block_content = (
                              split_content[0].strip() if split_content else ""
                          )

  Leftover content (everything after </tag>)
                          leftover_content = (
                              split_content[1].strip() if len(split_content) > 1 else ""
                          )

                          if block_content:
                              content_blocks[-1]["content"] = block_content
                              content_blocks[-1]["ended_at"] = time.time()
                              content_blocks[-1]["duration"] = int(
                                  content_blocks[-1]["ended_at"]
                                   - content_blocks[-1]["started_at"]
                              )

  Reset the content_blocks by appending a new text block
                              if content_type != "code_interpreter":
                                  if leftover_content:

                                      content_blocks.append(
                                          {
                                              "type": "text",
                                              "content": leftover_content,
                                          }
                                      )
                                  else:
                                      content_blocks.append(
                                          {
                                              "type": "text",
                                              "content": "",
                                          }
                                      )

                          else:
  Remove the block if content is empty
                              content_blocks.pop()

                              if leftover_content:
                                  content_blocks.append(
                                      {
                                          "type": "text",
                                          "content": leftover_content,
                                      }
                                  )
                              else:
                                  content_blocks.append(
                                      {
                                          "type": "text",
                                          "content": "",
                                      }
                                  )

  Clean processed content
                          start_tag_pattern = rf"{re.escape(start_tag)}"
                          if start_tag.startswith("<") and start_tag.endswith(">"):
  Match start tag e.g., <tag> or <tag attr="value">
  remove both '<' and '>' from start_tag
  Match start tag with attributes
                              start_tag_pattern = (
                                  rf"<{re.escape(start_tag[1:-1])}(\s.*?)?>"
                              )

                          content = re.sub(
                              rf"{start_tag_pattern}(.|\n)*?{re.escape(end_tag)}",
                              "",
                              content,
                              flags=re.DOTALL,
                          )

                  return content, content_blocks, end_flag

              message = Chats.get_message_by_id_and_message_id(
                  metadata["chat_id"], metadata["message_id"]
              )

              tool_calls = []

              last_assistant_message = None
              try:
                  if form_data["messages"][-1]["role"] == "assistant":
                      last_assistant_message = get_last_assistant_message(
                          form_data["messages"]
                      )
              except Exception as e:
                  pass

              content = (
                  message.get("content", "")
                  if message
                  else last_assistant_message if last_assistant_message else ""
              )

              content_blocks = [
                  {
                      "type": "text",
                      "content": content,
                  }
              ]

  We might want to disable this by default
              DETECT_REASONING = True
              DETECT_SOLUTION = True
              DETECT_CODE_INTERPRETER = metadata.get("features", {}).get(
                  "code_interpreter", False
              )

              reasoning_tags = [
                  ("<think>", "</think>"),
                  ("<thinking>", "</thinking>"),
                  ("<reason>", "</reason>"),
                  ("<reasoning>", "</reasoning>"),
                  ("<thought>", "</thought>"),
                  ("<Thought>", "</Thought>"),
                  ("<|begin_of_thought|>", "<|end_of_thought|>"),
                  ("◁think▷", "◁/think▷"),
              ]

              code_interpreter_tags = [("<code_interpreter>", "</code_interpreter>")]

              solution_tags = [("<|begin_of_solution|>", "<|end_of_solution|>")]

              try:
                  for event in events:
                      await event_emitter(
                          {
                              "type": "chat:completion",
                              "data": event,
                          }
                      )

  Save message in the database
                      Chats.upsert_message_to_chat_by_id_and_message_id(
                          metadata["chat_id"],
                          metadata["message_id"],
                          {
                              **event,
                          },
                      )

                  async def stream_body_handler(response, form_data):
                      nonlocal content
                      nonlocal content_blocks

                      response_tool_calls = []

                      async for line in response.body_iterator:
                          line = line.decode("utf-8") if isinstance(line, bytes) else line
                          data = line

  Skip empty lines
                          if not data.strip():
                              continue

  "data:" is the prefix for each event
                          if not data.startswith("data:"):
                              continue

  Remove the prefix
                          data = data[len("data:") :].strip()

                          try:
                              data = json.loads(data)

                              data, _ = await process_filter_functions(
                                  request=request,
                                  filter_functions=filter_functions,
                                  filter_type="stream",
                                  form_data=data,
                                  extra_params={"__body__": form_data, **extra_params},
                              )

                              if data:
                                  if "event" in data:
                                      await event_emitter(data.get("event", {}))

                                  if "selected_model_id" in data:
                                      model_id = data["selected_model_id"]
                                      Chats.upsert_message_to_chat_by_id_and_message_id(
                                          metadata["chat_id"],
                                          metadata["message_id"],
                                          {
                                              "selectedModelId": model_id,
                                          },
                                      )
                                  else:
                                      choices = data.get("choices", [])
                                      if not choices:
                                          error = data.get("error", {})
                                          if error:
                                              await event_emitter(
                                                  {
                                                      "type": "chat:completion",
                                                      "data": {
                                                          "error": error,
                                                      },
                                                  }
                                              )
                                          usage = data.get("usage", {})
                                          if usage:
                                              await event_emitter(
                                                  {
                                                      "type": "chat:completion",
                                                      "data": {
                                                          "usage": usage,
                                                      },
                                                  }
                                              )
                                          continue

                                      delta = choices[0].get("delta", {})
                                      delta_tool_calls = delta.get("tool_calls", None)

                                      if delta_tool_calls:
                                          for delta_tool_call in delta_tool_calls:
                                              tool_call_index = delta_tool_call.get(
                                                  "index"
                                              )

                                              if tool_call_index is not None:
  Check if the tool call already exists
                                                  current_response_tool_call = None
                                                  for (
                                                      response_tool_call
                                                  ) in response_tool_calls:
                                                      if (
                                                          response_tool_call.get("index")
                                                          == tool_call_index
                                                      ):
                                                          current_response_tool_call = (
                                                              response_tool_call
                                                          )
                                                          break

                                                  if current_response_tool_call is None:
  Add the new tool call
                                                      delta_tool_call.setdefault(
                                                          "function", {}
                                                      )
                                                      delta_tool_call[
                                                          "function"
                                                      ].setdefault("name", "")
                                                      delta_tool_call[
                                                          "function"
                                                      ].setdefault("arguments", "")
                                                      response_tool_calls.append(
                                                          delta_tool_call
                                                      )
                                                  else:
  Update the existing tool call
                                                      delta_name = delta_tool_call.get(
                                                          "function", {}
                                                      ).get("name")
                                                      delta_arguments = (
                                                          delta_tool_call.get(
                                                              "function", {}
                                                          ).get("arguments")
                                                      )

                                                      if delta_name:
                                                          current_response_tool_call[
                                                              "function"
                                                          ]["name"] += delta_name

                                                      if delta_arguments:
                                                          current_response_tool_call[
                                                              "function"
                                                          ][
                                                              "arguments"
                                                          ] += delta_arguments

                                      value = delta.get("content")

                                      reasoning_content = (
                                          delta.get("reasoning_content")
                                          or delta.get("reasoning")
                                          or delta.get("thinking")
                                      )
                                      if reasoning_content:
                                          if (
                                              not content_blocks
                                              or content_blocks[-1]["type"] != "reasoning"
                                          ):
                                              reasoning_block = {
                                                  "type": "reasoning",
                                                  "start_tag": "think",
                                                  "end_tag": "/think",
                                                  "attributes": {
                                                      "type": "reasoning_content"
                                                  },
                                                  "content": "",
                                                  "started_at": time.time(),
                                              }
                                              content_blocks.append(reasoning_block)
                                          else:
                                              reasoning_block = content_blocks[-1]

                                          reasoning_block["content"] += reasoning_content

                                          data = {
                                              "content": serialize_content_blocks(
                                                  content_blocks
                                              )
                                          }

                                      if value:
                                          if (
                                              content_blocks
                                              and content_blocks[-1]["type"]
                                              == "reasoning"
                                              and content_blocks[-1]
                                              .get("attributes", {})
                                              .get("type")
                                              == "reasoning_content"
                                          ):
                                              reasoning_block = content_blocks[-1]
                                              reasoning_block["ended_at"] = time.time()
                                              reasoning_block["duration"] = int(
                                                  reasoning_block["ended_at"]
                                                   - reasoning_block["started_at"]
                                              )

                                              content_blocks.append(
                                                  {
                                                      "type": "text",
                                                      "content": "",
                                                  }
                                              )

                                          content = f"{content}{value}"
                                          if not content_blocks:
                                              content_blocks.append(
                                                  {
                                                      "type": "text",
                                                      "content": "",
                                                  }
                                              )

                                          content_blocks[-1]["content"] = (
                                              content_blocks[-1]["content"] + value
   1 
   2 ### `open_webui/retrieval/utils.py` (Funciones relevantes)
   3 
   ... first 519 lines hidden ...
   520             if (
   521                 item.get("context") == "full"
   522                 or request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL
   523             ):
   524                 if item.get("file", {}).get("data", {}).get("content", ""):
   525                     # Manual Full Mode Toggle
   526                     # Used from chat file modal, we can assume that the file content will be available from item.get("file").get("data", {}).get("content")
   527                     query_result = {
   528                         "documents": [
   529                             [item.get("file", {}).get("data", {}).get("content", "")]
   530                         ],
   531                         "metadatas": [
   532                             [
   533                                 {
   534                                     "file_id": item.get("id"),
   535                                     "name": item.get("name"),
   536                                     **item.get("file")
   537                                     .get("data", {})
   538                                     .get("metadata", {}),
   539                                 }
   540                             ]
   541                         ],
   542                     }
   543                 elif item.get("id"):
   544                     file_object = Files.get_file_by_id(item.get("id"))
   545                     if file_object:
   546                         query_result = {
   547                             "documents": [[file_object.data.get("content", "")]],
   548                             "metadatas": [
   549                                 [
   550                                     {
   551                                         "file_id": item.get("id"),
   552                                         "name": file_object.filename,
   553                                         "source": file_object.filename,
   554                                     }
   555                                 ]
   556                             ],
   557                         }
   558             else:
   559                 # Fallback to collection names
   560                 if item.get("legacy"):
   561                     collection_names.append(f"{item['id']}")
   562                 else:
   563                     collection_names.append(f"file-{item['id']}")
   564 
   565         elif item.get("type") == "collection":
   566             if (
   567                 item.get("context") == "full"
   568                 or request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL
   569             ):
   570                 # Manual Full Mode Toggle for Collection
   571                 knowledge_base = Knowledges.get_knowledge_by_id(item.get("id"))
   572 
   573                 if knowledge_base and (
   574                     user.role == "admin"
   575                     or has_access(user.id, "read", knowledge_base.access_control)
   576                 ):
   577 
   578                     file_ids = knowledge_base.data.get("file_ids", [])
   579 
   580                     documents = []
   581                     metadatas = []
   582                     for file_id in file_ids:
   583                         file_object = Files.get_file_by_id(file_id)
   584 
   585                         if file_object:
   586                             documents.append(file_object.data.get("content", ""))
   587                             metadatas.append(
   588                                 {
   589                                     "file_id": file_id,
   590                                     "name": file_object.filename,
   591                                     "source": file_object.filename,
   592                                 }
   593                             )
   594 
   595                     query_result = {
   596                         "documents": [documents],
   597                         "metadatas": [metadatas],
   598                     }
   599             else:
   600                 # Fallback to collection names
   601                 if item.get("legacy"):
   602                     collection_names = item.get("collection_names", [])
   603                 else:
   604                     collection_names.append(item["id"])
   605 
   606         elif item.get("docs"):
   607             # BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL
   608             query_result = {
   609                 "documents": [[doc.get("content") for doc in item.get("docs")]],
   610                 "metadatas": [[doc.get("metadata") for doc in item.get("docs")]],
   611             }
   612         elif item.get("collection_name"):
   613             # Direct Collection Name
   614             collection_names.append(item["collection_name"])
   615         elif item.get("collection_names"):
   616             # Collection Names List
   617             collection_names.extend(item["collection_names"])
   618 
   619         # If query_result is None
   620         # Fallback to collection names and vector search the collections
   621         if query_result is None and collection_names:
   622             collection_names = set(collection_names).difference(extracted_collections)
   623             if not collection_names:
   624                 log.debug(f"skipping {item} as it has already been extracted")
   625                 continue
   626 
   627             try:
   628                 if full_context:
   629                     query_result = get_all_items_from_collections(collection_names)
   630                 else:
   631                     query_result = None  # Initialize to None
   632                     if hybrid_search:
   633                         try:
   634                             query_result = query_collection_with_hybrid_search(
   635                                 collection_names=collection_names,
   636                                 queries=queries,
   637                                 embedding_function=embedding_function,
   638                                 k=k,
   639                                 reranking_function=reranking_function,
   640                                 k_reranker=k_reranker,
   641                                 r=r,
   642                                 hybrid_bm25_weight=hybrid_bm25_weight,
   643                             )
   644                         except Exception as e:
   645                             log.debug(
   646                                 "Error when using hybrid search, using non hybrid search as fallback."
   647                             )
   648 
   649                     # fallback to non-hybrid search
   650                     if not hybrid_search and query_result is None:
   651                         query_result = query_collection(
   652                             collection_names=collection_names,
   653                             queries=queries,
   654                             embedding_function=embedding_function,
   655                             k=k,
   656                         )
   657             except Exception as e:
   658                 log.exception(e)
   659 
   660             extracted_collections.extend(collection_names)
   661 
   662         if query_result:
   663             if "data" in item:
   664                 del item["data"]
   665             query_results.append({**query_result, "file": item})
   666 
   667     sources = []
   668     for query_result in query_results:
   669         try:
   670             if "documents" in query_result:
   671                 if "metadatas" in query_result:
   672                     source = {
   673                         "source": query_result["file"],
   674                         "document": query_result["documents"][0],
   675                         "metadata": query_result["metadatas"][0],
   676                     }
   677                     if "distances" in query_result and query_result["distances"]:
   678                         source["distances"] = query_result["distances"][0]
   679 
   680                     sources.append(source)
   681         except Exception as e:
   682             log.exception(e)
   683 
   684     return sources
   685 
   686 
   687 def get_embedding_function(
   688     embedding_engine,
   689     embedding_model,
   690     embedding_function,
   691     url,
   692     key,
   693     embedding_batch_size,
   694     azure_api_version=None,
   695 ):
   696     if embedding_engine == "":
   697         return lambda query, prefix=None, user=None: embedding_function.encode(
   698             query, **({"prompt": prefix} if prefix else {})
   699         ).tolist()
   700     elif embedding_engine in ["ollama", "openai", "azure_openai"]:
   701         func = lambda query, prefix=None, user=None: generate_embeddings(
   702             engine=embedding_engine,
   703             model=embedding_model,
   704             text=query,
   705             prefix=prefix,
   706             url=url,
   707             key=key,
   708             user=user,
   709             azure_api_version=azure_api_version,
   710         )
   711 
   712         def generate_multiple(query, prefix, user, func):
   713             if isinstance(query, list):
   714                 embeddings = []
   715                 for i in range(0, len(query), embedding_batch_size):
   716                     embeddings.extend(
   717                         func(
   718                             query[i : i + embedding_batch_size],
   719                             prefix=prefix,
   720                             user=user,
   721                         )
   722                     )
   723                 return embeddings
   724             else:
   725                 return func(query, prefix, user)
   726 
   727         return lambda query, prefix=None, user=None: generate_multiple(
   728             query, prefix, user, func
   729         )
   730     else:
   731         raise ValueError(f"Unknown embedding engine: {embedding_engine}")
   732 
   733 
   734 def get_reranking_function(reranking_engine, reranking_model, reranking_function):
   735     if reranking_function is None:
   736         return None
   737     if reranking_engine == "external":
   738         return lambda sentences, user=None: reranking_function.predict(
   739             sentences, user=user
   740         )
   741     else:
   742         return lambda sentences, user=None: reranking_function.predict(sentences)

   ... first 221 lines hidden ...
   222                     for model in list(request.app.state.MODELS.values())
   223                     if model.get("owned_by") != "arena"
   224                 ]
   225                 selected_model_id = random.choice(model_ids)
   226 
   227             form_data["model"] = selected_model_id
   228 
   229             if form_data.get("stream") == True:
   230 
   231                 async def stream_wrapper(stream):
   232                     yield f"data: {json.dumps({'selected_model_id': selected_model_id})}\n\n"
   233                     async for chunk in stream:
   234                         yield chunk
   235 
   236                 response = await generate_chat_completion(
   237                     request, form_data, user, bypass_filter=True
   238                 )
   239                 return StreamingResponse(
   240                     stream_wrapper(response.body_iterator),
   241                     media_type="text/event-stream",
   242                     background=response.background,
   243                 )
   244             else:
   245                 return {
   246                     **(
   247                         await generate_chat_completion(
   248                             request, form_data, user, bypass_filter=True
   249                         )
   250                     ),
   251                     "selected_model_id": selected_model_id,
   252                 }
   253 
   254         if model.get("pipe"):
   255             # Below does not require bypass_filter because this is the only route the uses this function and it is already bypassing the filter
   256             return await generate_function_chat_completion(
   257                 request, form_data, user=user, models=models
   258             )
   259         if model.get("owned_by") == "ollama":
   260             # Using /ollama/api/chat endpoint
   261             form_data = convert_payload_openai_to_ollama(form_data)
   262             response = await generate_ollama_chat_completion(
   263                 request=request,
   264                 form_data=form_data,
   265                 user=user,
   266                 bypass_filter=bypass_filter,
   267             )
   268             if form_data.get("stream"):
   269                 response.headers["content-type"] = "text/event-stream"
   270                 return StreamingResponse(
   271                     convert_streaming_response_ollama_to_openai(response),
   272                     headers=dict(response.headers),
   273                     background=response.background,
   274                 )
   275             else:
   276                 return convert_response_ollama_to_openai(response)
   277         else:
   278             return await generate_openai_chat_completion(
   279                 request=request,
   280                 form_data=form_data,
   281                 user=user,
   282                 bypass_filter=bypass_filter,
   283             )
   284 
   285 
   286 chat_completion = generate_chat_completion
   287 
   288 
   289 async def chat_completed(request: Request, form_data: dict, user: Any):
   290     if not request.app.state.MODELS:
   291         await get_all_models(request, user=user)
   292 
   293     if getattr(request.state, "direct", False) and hasattr(request.state, "model"):
   294         models = {
   295             request.state.model["id"]: request.state.model,
   296         }
   297     else:
   298         models = request.app.state.MODELS
   299 
   300     data = form_data
   301     model_id = data["model"]
   302     if model_id not in models:
   303         raise Exception("Model not found")
   304 
   305     model = models[model_id]
   306 
   307     try:
   308         data = await process_pipeline_outlet_filter(request, data, user, models)
   309     except Exception as e:
   310         return Exception(f"Error: {e}")
   311 
   312     metadata = {
   313         "chat_id": data["chat_id"],
   314         "message_id": data["id"],
   315         "filter_ids": data.get("filter_ids", []),
   316         "session_id": data["session_id"],
   317         "user_id": user.id,
   318     }
   319 
   320     extra_params = {
   321         "__event_emitter__": get_event_emitter(metadata),
   322         "__event_call__": get_event_call(metadata),
   323         "__user__": user.model_dump() if isinstance(user, UserModel) else {},
   324         "__metadata__": metadata,
   325         "__request__": request,
   326         "__model__": model,
   327     }
   328 
   329     try:
   330         filter_functions = [
   331             Functions.get_function_by_id(filter_id)
   332             for filter_id in get_sorted_filter_ids(
   333                 request, model, metadata.get("filter_ids", [])
   334             )
   335         ]
   336 
   337         result, _ = await process_filter_functions(
   338             request=request,
   339             filter_functions=filter_functions,
   340             filter_type="outlet",
   341             form_data=data,
   342             extra_params=extra_params,
   343         )
   344         return result
   345     except Exception as e:
   346         return Exception(f"Error: {e}")
   347 
   348 
   349 async def chat_action(request: Request, action_id: str, form_data: dict, user: Any):
   350     if "." in action_id:
   351         action_id, sub_action_id = action_id.split(".")
   352     else:
   353         sub_action_id = None
   354 
   355     action = Functions.get_function_by_id(action_id)
   356     if not action:
   357         raise Exception(f"Action not found: {action_id}")
   358 
   359     if not request.app.state.MODELS:
   360         await get_all_models(request, user=user)
   361 
   362     if getattr(request.state, "direct", False) and hasattr(request.state, "model"):
   363         models = {
   364             request.state.model["id"]: request.state.model,
   365         }
   366     else:
   367         models = request.app.state.MODELS
   368 
   369     data = form_data
   370     model_id = data["model"]
   371 
   372     if model_id not in models:
   373         raise Exception("Model not found")
   374     model = models[model_id]
   375 
   376     __event_emitter__ = get_event_emitter(
   377         {
   378             "chat_id": data["chat_id"],
   379             "message_id": data["id"],
   380             "session_id": data["session_id"],
   381             "user_id": user.id,
   382         }
   383     )
   384     __event_call__ = get_event_call(
   385         {
   386             "chat_id": data["chat_id"],
   387             "message_id": data["id"],
   388             "session_id": data["session_id"],
   389             "user_id": user.id,
   390         }
   391     )
   392 
   393     function_module, _, _ = get_function_module_from_cache(request, action_id)
   394 
   395     if hasattr(function_module, "valves") and hasattr(function_module, "Valves"):
   396         valves = Functions.get_function_valves_by_id(action_id)
   397         function_module.valves = function_module.Valves(**(valves if valves else {}))
   398 
   399     if hasattr(function_module, "action"):
   400         try:
   401             action = function_module.action
   402 
   403             # Get the signature of the function
   404             sig = inspect.signature(action)
   405             params = {"body": data}
   406 
   407             # Extra parameters to be passed to the function
   408             extra_params = {
   409                 "__model__": model,
   410                 "__id__": sub_action_id if sub_action_id is not None else action_id,
   411                 "__event_emitter__": __event_emitter__,
   412                 "__event_call__": __event_call__,
   413                 "__request__": request,
   414             }
   415 
   416             # Add extra params in contained in function signature
   417             for key, value in extra_params.items():
   418                 if key in sig.parameters:
   419                     params[key] = value
   420 
   421             if "__user__" in sig.parameters:
   422                 __user__ = user.model_dump() if isinstance(user, UserModel) else {}
   423 
   424                 try:
   425                     if hasattr(function_module, "UserValves"):
   426                         __user__["valves"] = function_module.UserValves(
   427                             **Functions.get_user_valves_by_id_and_user_id(
   428                                 action_id, user.id
   429                             )
   430                         )
   431                 except Exception as e:
   432                     log.exception(f"Failed to get user values: {e}")
   433 
   434                 params = {**params, "__user__": __user__}
   435 
   436             if inspect.iscoroutinefunction(action):
   437                 data = await action(**params)
   438             else:
   439                 data = action(**params)
   440 
   441         except Exception as e:
   442             return Exception(f"Error: {e}")
   443 
   444     return data


ℹ ⚠️  Response truncated due to token limits.
 
   ... first 956 lines hidden ...
    957         context_string = ""
    958         citation_idx_map = {}
    959 
    960         for source in sources:
    961             is_tool_result = source.get("tool_result", False)
    962 
    963             if "document" in source and not is_tool_result:
    964                 for document_text, document_metadata in zip(
    965                     source["document"], source["metadata"]
    966                 ):
    967                     source_name = source.get("source", {}).get("name", None)
    968                     source_id = (
    969                         document_metadata.get("source", None)
    970                         or source.get("source", {}).get("id", None)
    971                         or "N/A"
    972                     )
    973 
    974                     if source_id not in citation_idx_map:
    975                         citation_idx_map[source_id] = len(citation_idx_map) + 1
    976 
    977                     context_string += (
    978                         f'<source id="{citation_idx_map[source_id]}"'
    979                         + (f' name="{source_name}"' if source_name else "")
    980                         + f">{document_text}</source>\n"
    981                     )
    982 
    983         context_string = context_string.strip()
    984 
    985         prompt = get_last_user_message(form_data["messages"])
    986         if prompt is None:
    987             raise Exception("No user message found")
    988 
    989         if context_string == "":
    990             if request.app.state.config.RELEVANCE_THRESHOLD == 0:
    991                 log.debug(
    992                     f"With a 0 relevancy threshold for RAG, the context cannot be empty"
    993                 )
    994         else:
    995             # Workaround for Ollama 2.0+ system prompt issue
    996             # TODO: replace with add_or_update_system_message
    997             if model.get("owned_by") == "ollama":
    998                 form_data["messages"] = prepend_to_first_user_message_content(
    999                     rag_template(
   1000                         request.app.state.config.RAG_TEMPLATE, context_string, prompt
   1001                     ),
   1002                     form_data["messages"],
   1003                 )
   1004             else:
   1005                 form_data["messages"] = add_or_update_system_message(
   1006                     rag_template(
   1007                         request.app.state.config.RAG_TEMPLATE, context_string, prompt
   1008                     ),
   1009                     form_data["messages"],
   1010                 )
   1011 
   1012     # If there are citations, add them to the data_items
   1013     sources = [
   1014         source
   1015         for source in sources
   1016         if source.get("source", {}).get("name", "")
   1017         or source.get("source", {}).get("id", "")
   1018     ]
   1019 
   1020     if len(sources) > 0:
   1021         events.append({"sources": sources})
   1022 
   1023     if model_knowledge:
   1024         await event_emitter(
   1025             {
   1026                 "type": "status",
   1027                 "data": {
   1028                     "action": "knowledge_search",
   1029                     "query": user_message,
   1030                     "done": True,
   1031                     "hidden": True,
   1032                 },
   1033             }
   1034         )
   1035 
   1036     return form_data, metadata, events
   1037 
   1038 
   1039 async def process_chat_response(
   1040     request, response, form_data, user, metadata, model, events, tasks
   1041 ):
   1042     async def background_tasks_handler():
   1043         message_map = Chats.get_messages_by_chat_id(metadata["chat_id"])
   1044         message = message_map.get(metadata["message_id"]) if message_map else None
   1045 
   1046         if message:
   1047             message_list = get_message_list(message_map, metadata["message_id"])
   1048 
   1049             # Remove details tags and files from the messages.
   1050             # as get_message_list creates a new list, it does not affect
   1051             # the original messages outside of this handler
   1052 
   1053             messages = []
   1054             for message in message_list:
   1055                 content = message.get("content", "")
   1056                 if isinstance(content, list):
   1057                     for item in content:
   1058                         if item.get("type") == "text":
   1059                             content = item["text"]
   1060                             break
   1061 
   1062                 if isinstance(content, str):
   1063                     content = re.sub(
   1064                         r"<details\b[^>]*>.*?</details>|!\[.*?\]\(.*?\)",
   1065                         "",
   1066                         content,
   1067                         flags=re.S | re.I,
   1068                     ).strip()
   1069 
   1070                 messages.append(
   1071                     {
   1072                         **message,
   1073                         "role": message.get(
   1074                             "role", "assistant"
   1075                         ),  # Safe fallback for missing role
   1076                         "content": content,
   1077                     }
   1078                 )
   1079 
   1080             if tasks and messages:
   1081                 if (
   1082                     TASKS.FOLLOW_UP_GENERATION in tasks
   1083                     and tasks[TASKS.FOLLOW_UP_GENERATION]
   1084                 ):
   1085                     res = await generate_follow_ups(
   1086                         request,
   1087                         {
   1088                             "model": message["model"],
   1089                             "messages": messages,
   1090                             "message_id": metadata["message_id"],
   1091                             "chat_id": metadata["chat_id"],
   1092                         },
   1093                         user,
   1094                     )
   1095 
   1096                     if res and isinstance(res, dict):
   1097                         if len(res.get("choices", [])) == 1:
   1098                             follow_ups_string = (
   1099                                 res.get("choices", [])[0]
   1100                                 .get("message", {})
   1101                                 .get("content", "")
   1102                             )
   1103                         else:
   1104                             follow_ups_string = ""
   1105 
   1106                         follow_ups_string = follow_ups_string[
   1107                             follow_ups_string.find("{") : follow_ups_string.rfind("}")
   1108                             + 1
   1109                         ]
   1110 
   1111                         try:
   1112                             follow_ups = json.loads(follow_ups_string).get(
   1113                                 "follow_ups", []
   1114                             )
   1115 
   1116                             Chats.upsert_message_to_chat_by_id_and_message_id(
   1117                                 metadata["chat_id"],
   1118                                 metadata["message_id"],
   1119                                 {
   1120                                     "followUps": follow_ups,
   1121                                 },
   1122                             )
   1123 
   1124                             await event_emitter(
   1125                                 {
   1126                                     "type": "chat:message:follow_ups",
   1127                                     "data": {
   1128                                         "follow_ups": follow_ups,
   1129                                     },
   1130                                 }
   1131                             )
   1132                         except Exception as e:
   1133                             pass
   1134 
   1135                 if TASKS.TITLE_GENERATION in tasks:
   1136                     user_message = get_last_user_message(messages)
   1137                     if user_message and len(user_message) > 100:
   1138                         user_message = user_message[:100] + "..."
   1139 
   1140                     if tasks[TASKS.TITLE_GENERATION]:
   1141 
   1142                         res = await generate_title(
   1143                             request,
   1144                             {
   1145                                 "model": message["model"],
   1146                                 "messages": messages,
   1147                                 "chat_id": metadata["chat_id"],
   1148                             },
   1149                             user,
   1150                         )
   1151 
   1152                         if res and isinstance(res, dict):
   1153                             if len(res.get("choices", [])) == 1:
   1154                                 title_string = (
   1155                                     res.get("choices", [])[0]
   1156                                     .get("message", {})
   1157                                     .get(
   1158                                         "content", message.get("content", user_message)
   1159                                     )
   1160                                 )
   1161                             else:
   1162                                 title_string = ""
   1163 
   1164                             title_string = title_string[
   1165                                 title_string.find("{") : title_string.rfind("}") + 1
   1166                             ]
   1167 
   1168                             try:
   1169                                 title = json.loads(title_string).get(
   1170                                     "title", user_message
   1171                                 )
   1172                             except Exception as e:
   1173                                 title = ""
   1174 
   1175                             if not title:
   1176                                 title = messages[0].get("content", user_message)
   1177 
   1178                             Chats.update_chat_title_by_id(metadata["chat_id"], title)
   1179 

