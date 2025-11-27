# utils/advanced_text_analyzer.py

import logging
import asyncio
import re
from typing import List, Dict, Optional, TypeVar, cast, Type

# LangChain y Pydantic para robustez y estructura
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field # Usamos pydantic v2

logger = logging.getLogger(__name__)

# --- Modelos de Salida Pydantic para garantizar la estructura del LLM ---


class CollectionConnection(BaseModel):
    """Define una conexión específica encontrada entre documentos de una colección."""
    document_titles: List[str] = Field(description="Los títulos de los documentos entre los que se encontró la conexión.")
    insight: str = Field(description="Descripción de la sinergia, evolución o contradicción encontrada entre estos documentos.")

class ThemeQuote(BaseModel):
    """Define una cita o referencia relacionada con un tema transversal en un documento."""
    document_title: str = Field(description="El título del documento de donde se extrajo la cita.")
    quote: str = Field(description="La cita o fragmento relevante del documento relacionado con el tema. Cuida que las citas sean parrafos y oraciones completas y no fragmentos cortados arbitrariamente")


class ThemeReference(BaseModel):
    """Define un tema transversal con citas relacionadas de los documentos."""
    theme: str = Field(description="El nombre del tema transversal.")
    related_quotes: List[ThemeQuote] = Field(description="Lista de citas o fragmentos de los documentos relacionados con este tema.Cuida que las citas sean parrafos y oraciones completas y no fragmentos cortados arbitrariamente")


class SingleTextAnalysis(BaseModel):
    """Define la estructura de salida para el análisis de un único texto."""
    executive_summary: str = Field(description="Un resumen conciso que captura la esencia y las conclusiones principales del texto.")
    general_analysis: str = Field(description="Un análisis general extenso del documento que profundiza en el contexto, metodología, argumentos principales, implicaciones y relevancia (500-1000 palabras). Utiliza separación de parrafos pra facilitar la lectura")
    key_themes: List[ThemeReference] = Field(description="Una lista de hasta 12 conceptos o temas centrales del texto, cada uno con citas del texto y explicación detallada.")
    central_concepts: List[str] = Field(description="Una lista de hasta 8 conceptos centrales del texto en el formato 'CONCEPTO: DEFINICIÓN DETALLADA CON CONTEXTO Y EJEMPLOS'.")
    discipline: List[str] = Field(description="El area, disciplina o campo al que refiere el documento. Por ejemplo si es un documémico y de qué área, o si es un documento técnico, etc.').")
    authorial_tone: str = Field(description="El tono o la voz del autor (ej. 'Formal y Académico', 'Informal y Conversacional', 'Urgente y Directo', 'Escéptico y Crítico').")
    knowledge_gaps: List[str] = Field(description="Una lista de 5 a 8 preguntas inteligentes y abiertas que el texto inspira pero no responde. Deben ser preguntas, no afirmaciones.")
    exploration_questions: List[str] = Field(description="Una lista de 5 a 8 preguntas adicionales para explorar a partir del texto, que el texto inspira pero no responde directamente.")
    problematic_areas: List[str] = Field(description="Una lista de 3 a 5 áreas problemáticas, desafíos o puntos de controversia identificados en el texto.")
    final_reflections: List[str] = Field (description="Una lista de 3 a 5 reflexiones finales sobre la importancia del contenido en el área que aborda, su aporte al conocimiento y apertura de temas de reflexión. Si se trata de documentos más técnicos o laborales puedes hablar de las posibilidades que abre, proyectos posibles o recomendaciones de gestión")
    kai_synthesis: str = Field(description="Una síntesis única y profunda desde la perspectiva de KAI (Kognito AI) como exocerebro del usuario. Debe ser una reflexión de alto nivel (100-150 palabras) que conecte el contenido del documento con el contexto más amplio del conocimiento del usuario, identificando oportunidades, conexiones no obvias y valor estratégico.")

class CollectionAnalysis(BaseModel):
    """Define la estructura de salida para el análisis de una colección de textos."""
    collection_summary: str = Field(description="Un resumen analítico que sintetiza la información de TODOS los documentos como un todo. Debe ser comprehensivo y detallado (200-300 palabras)")
    cross_cutting_themes: List[ThemeReference] = Field(description="Lista de hasta 10 temas recurrentes de los documentos que puedes identificar, cada uno con citas relacionadas de los documentos. Puedes agruparlos en algún concepto que los englobe cuando hay similitud semántica")
    central_concepts: List[str] = Field(description="Una lista de hasta 8 conceptos, ideas o tesis centrales de la colección en el formato 'CONCEPTO: DEFINICIÓN DETALLADA'. Destaca con negrita el nombre de los conceptos")
    concept_relationships: List[str] = Field(description="Una lista de hasta 8 descripciones detalladas de cómo los conceptos centrales se relacionan entre sí en la colección.")
    identified_connections: List[CollectionConnection] = Field(description="Lista de insights específicos que conectan dos o más documentos. Incluye sinergias, evoluciones, contradicciones o complementariedades.")
    emergent_knowledge_gaps: List[str] = Field(description="Lista de 5-8 preguntas inteligentes o áreas que la colección en su conjunto no responde o deja abiertas.")
    exploration_questions: List[str] = Field(description="Lista de 5-8 preguntas adicionales para explorar a partir de la colección, que el texto inspira pero no responde directamente.")
    problematic_areas: List[str] = Field(description="Una lista de 3 a 5 áreas problemáticas o desafíos comunes/emergentes identificados a través de la colección de documentos.")
    final_reflections: List[str] = Field(description="3-5 reflexiones finales sobre la importancia del contenido en el área que aborda, su aporte al conocimiento y apertura de temas de reflexión. Si se trata de documentos más técnicos o laborales puedes hablar de las posibilidades que abre, proyectos posibles o recomendaciones de gestión")
    collection_insights: List[str] = Field(description="3-5 insights únicos que emergen del análisis conjunto de todos los documentos, que no serían evidentes analizando documentos individuales")
    methodological_notes: List[str] = Field(description="2-3 observaciones sobre la metodología, enfoque o perspectiva común en los documentos analizados")
    kai_synthesis: str = Field(description="Una síntesis de alto nivel desde la perspectiva de KAI (Kognito AI) como exocerebro del usuario. Debe ser una reflexión estratégica (150-200 palabras) que conecte el contenido de la colección con el contexto más amplio del conocimiento del usuario, identificando patrones emergentes, oportunidades de acción y valor estratégico único que surge del análisis conjunto.")


# --- Clase Principal del Analizador ---

class AdvancedTextAnalyzer:
    """
    Una clase encapsulada para realizar análisis de texto avanzados usando modelos de lenguaje.
    Gestiona la inicialización de modelos y proporciona métodos de análisis robustos.
    """
    _gemini_model: Optional[ChatGoogleGenerativeAI] = None

    async def _get_model(self) -> ChatGoogleGenerativeAI:
        """Inicializa el modelo Gemini de forma singleton y asíncrona."""
        if self._gemini_model is None:
            logger.info("Inicializando modelo Gemini para análisis de texto avanzado...")
            # Aquí puedes poner el nombre del modelo que prefieras de tu config
            self._gemini_model = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                temperature=0.1,
                disable_streaming=False  # Habilita streaming
            )
            logger.info("Modelo Gemini inicializado.")
        return self._gemini_model

    _PydanticType = TypeVar('_PydanticType', bound=BaseModel)

    async def _run_analysis_with_parser(self, prompt: str, output_parser: PydanticOutputParser, pydantic_object: Type[_PydanticType]) -> _PydanticType:
        """
        Función centralizada y robusta para ejecutar una llamada al LLM y parsear la salida.
        """
        llm = await self._get_model()
        full_prompt = f"{prompt}\n\n{output_parser.get_format_instructions()}"

        try:
            response = await llm.ainvoke([HumanMessage(content=full_prompt)])
            # Ensure we have a string response content
            response_content = response.content
            if isinstance(response_content, list):
                # If content is a list, join it into a string
                response_content = " ".join(str(item) for item in response_content)
            elif not isinstance(response_content, str):
                response_content = str(response_content)

            # Intentar extraer el JSON si está envuelto en un bloque de código Markdown
            json_match = re.search(r"```json\n(.*?)```", response_content, re.DOTALL)
            if json_match:
                json_string = json_match.group(1)
                logger.debug(f"JSON extraído de bloque Markdown: {json_string}")
            else:
                json_string = response_content
                logger.debug(f"No se encontró bloque Markdown, intentando parsear directamente: {json_string}")

            parsed_output = await output_parser.aparse(json_string)
            return cast(pydantic_object, parsed_output)
        except Exception as e:
            logger.error(f"Fallo en el pipeline de análisis y parseo del LLM: {e}", exc_info=True)
            raise ValueError(f"No se pudo obtener una respuesta JSON válida del LLM. Error: {e}")

    async def analyze_single_text(self, text: str, document_title: str = "Documento analizado") -> SingleTextAnalysis:
        """
        Ejecuta un análisis completo y estructurado sobre un único fragmento de texto.
        """
        if not text or len(text.split()) < 30:
            return SingleTextAnalysis(
                executive_summary=text, general_analysis="Texto insuficiente para análisis detallado",
                key_themes=[], central_concepts=[], discipline=[], authorial_tone="N/A",
                knowledge_gaps=[], final_reflections=[]
            )

        prompt = f"""
        Eres KAI (Kognito AI), un analista experto en análisis textual de conocimientos que actúa como exocerebro proactivo del usuario. Realiza un análisis exhaustivo y detallado del siguiente texto. Asegúrate de que todo el contenido generado esté en español.
 
        INSTRUCCIONES ESPECÍFICAS:
        1. **Resumen ejecutivo**: Conciso pero completo (50-80 palabras) en español.

        2. **Análisis general**: EXTENSO y profundo (500-1000 palabras) redactado en varios párrafos separados para facilitar la lectura, que incluya:
           - Contexto histórico, teórico o práctico del documento
           - Metodología o enfoque utilizado por el autor
           - Argumentos principales y su estructura lógica
           - Implicaciones teóricas y prácticas
           - Relevancia en el campo de conocimiento
           - Conexiones con otros temas o disciplinas
           - Evaluación crítica del contenido
           - Fortalezas y debilidades del texto
           - Audiencia objetivo y propósito del documento
           - Contribuciones originales o innovadoras
           - Limitaciones o sesgos identificados

        3. **Temas clave**: Hasta 12 temas importantes del texto. ESTRUCTURA REQUERIDA para cada tema:
           {{
             "theme": "Nombre del tema específico",
             "related_quotes": [
               {{
                 "document_title": "{document_title}",
                 "quote": "Cita textual completa del documento (párrafo u oración completa)"
               }}
             ]
           }}
           - Cada tema debe tener al menos 1-2 citas relevantes del texto
           - Las citas deben ser párrafos u oraciones completas, no fragmentos cortados
           - Usa nombres de temas específicos y descriptivos

        4. **Conceptos centrales**: Hasta 8 conceptos en formato 'CONCEPTO: DEFINICIÓN DETALLADA CON CONTEXTO Y EJEMPLOS. Destaca los conceptos en negrita'

        5. **Disciplina**: Área(s) de conocimiento específica(s)

        6. **Tono del autor**: Descripción precisa del estilo y enfoque

        7. **Brechas de conocimiento**: 5-8 preguntas inteligentes y abiertas que el texto inspira

        8. **Preguntas para explorar**: 5-8 preguntas adicionales para explorar a partir del texto, que el texto inspira pero no responde directamente.

        9. **Problemáticas**: 3-5 áreas problemáticas, desafíos o puntos de controversia identificados en el texto.

        10. **Reflexiones finales**: 3-5 reflexiones sobre importancia, aportes y proyecciones

        11. **Síntesis de KAI**: Como exocerebro del usuario, genera una reflexión estratégica de alto nivel (100-150 palabras) que:
            - Conecte este documento con el contexto más amplio del conocimiento del usuario
            - Identifique oportunidades de acción o aplicación práctica
            - Señale conexiones no obvias con otros dominios o áreas de interés
            - Destaque el valor estratégico único de este contenido
            - Proponga formas de aprovechar este conocimiento de manera proactiva
            - Adopta un tono reflexivo, estratégico y orientado a la acción

        Para los temas clave y conceptos centrales, utiliza nombres precisos y relevantes al contexto del texto, priorizando términos específicos del dominio o categorías reconocibles por el usuario.

        IMPORTANTE: Los temas clave deben seguir EXACTAMENTE la estructura JSON mostrada arriba, con "theme" y "related_quotes" como campos obligatorios.

        Texto a analizar:
        ---
        {text}
        ---
        """
        parser = PydanticOutputParser(pydantic_object=SingleTextAnalysis)
        result = await self._run_analysis_with_parser(prompt, parser, SingleTextAnalysis)
        return cast(SingleTextAnalysis, result)

    async def analyze_collection(self, documents: List[Dict[str, str]]) -> CollectionAnalysis:
        """
        Analiza una colección de documentos para encontrar temas transversales, conexiones y brechas de conocimiento emergentes.
        """
        if not documents:
            return CollectionAnalysis(
                collection_summary="No se proporcionaron textos para analizar.",
                cross_cutting_themes=[],
                central_concepts=[],
                concept_relationships=[],
                identified_connections=[],
                emergent_knowledge_gaps=[],
                final_reflections=[],
                collection_insights=[],
                methodological_notes=[]
            )
            
        full_context_text = ""
        for i, doc in enumerate(documents):
            title = doc.get('title', f"Documento {i+1}")
            content_snippet = (doc.get('content', '')[:1000] + '...') if len(doc.get('content', '')) > 1000 else doc.get('content', '')
            full_context_text += f"--- INICIO DOCUMENTO: '{title}' ---\n{content_snippet}\n--- FIN DOCUMENTO: '{title}' ---\n\n"

        output_parser = PydanticOutputParser(pydantic_object=CollectionAnalysis)
        prompt = f"""
        Eres KAI (Kognito AI), un analista de investigación experto en síntesis de conocimiento que actúa como exocerebro proactivo del usuario. Analiza esta colección de documentos. Asegúrate de que todo el contenido generado esté en español.
 
        INSTRUCCIONES ESPECÍFICAS PARA EL ANÁLISIS DE COLECCIÓN:
        Tu tarea es generar un análisis exhaustivo de la colección de documentos, asegurándote de incluir TODOS los siguientes campos en tu respuesta JSON, siguiendo las descripciones y formatos indicados. Todo el contenido generado debe estar en español:

        1.  **collection_summary**: Un resumen analítico que sintetiza la información de TODOS los documentos como un todo. Debe ser comprehensivo y detallado (200-300 palabras).
        2.  **cross_cutting_themes**: Una lista de hasta 10 temas recurrentes que identificas entre los documentos. Cada tema debe incluir citas relevantes de los documentos que lo ilustren. Agrupa conceptos similares semánticamente.
        3.  **central_concepts**: Una lista de hasta 8 conceptos, ideas o tesis centrales de la colección. Cada uno debe estar en el formato 'CONCEPTO: DEFINICIÓN DETALLADA'. Destaca el nombre del concepto en negrita.
        4.  **concept_relationships**: Una lista de hasta 8 descripciones detalladas de cómo los conceptos centrales se relacionan entre sí dentro de la colección.
        5.  **identified_connections**: Una lista de insights específicos que conectan dos o más documentos. Incluye sinergias, evoluciones, contradicciones o complementariedades. Cada conexión debe especificar los títulos de los documentos involucrados y una descripción del insight.
        6.  **emergent_knowledge_gaps**: Una lista de 5-8 preguntas inteligentes o áreas que la colección en su conjunto no responde o deja abiertas.
        7.  **exploration_questions**: Una lista de 5-8 preguntas adicionales para explorar a partir de la colección, que el texto inspira pero no responde directamente.
        8.  **problematic_areas**: Una lista de 3 a 5 áreas problemáticas o desafíos comunes/emergentes identificados a través de la colección de documentos.
        9.  **final_reflections**: 3-5 reflexiones finales sobre la importancia del contenido en el área que aborda, su aporte al conocimiento y apertura de temas de reflexión. Si se trata de documentos más técnicos o laborales, puedes hablar de las posibilidades que abre, proyectos posibles o recomendaciones de gestión.
        10. **collection_insights**: 3-5 insights únicos que emergen del análisis conjunto de todos los documentos, que no serían evidentes analizando documentos individuales.
        11. **methodological_notes**: 2-3 observaciones sobre la metodología, enfoque o perspectiva común en los documentos analizados.
        12. **kai_synthesis**: Como exocerebro del usuario, genera una síntesis estratégica de alto nivel (150-200 palabras) que:
            - Conecte el contenido de esta colección con el contexto más amplio del conocimiento del usuario
            - Identifique patrones emergentes y oportunidades estratégicas únicas que surgen del análisis conjunto
            - Señale conexiones no obvias entre los documentos y con otros dominios
            - Destaque el valor estratégico único de esta colección como un todo
            - Proponga acciones concretas o áreas de exploración prioritarias
            - Adopta un tono reflexivo, estratégico y orientado a la acción

        Asegúrate de que cada campo esté presente en la salida JSON, incluso si está vacío (en cuyo caso, usa un array vacío `[]` para las listas o un string vacío `""` para los strings).

        Colección de documentos:
        {full_context_text}
        """
        result = await self._run_analysis_with_parser(prompt, output_parser, CollectionAnalysis)
        return cast(CollectionAnalysis, result)

# --- INSTANCIA ÚNICA ---
# Se crea una única instancia del analizador para ser importada y reutilizada en toda la aplicación.
# Esto asegura que el modelo de Gemini solo se cargue una vez.
text_analyzer = AdvancedTextAnalyzer()
