# utils/advanced_text_analyzer.py

import logging
import asyncio
from typing import List, Dict, Optional, TypeVar, cast

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
    key_themes: List[ThemeReference] = Field(description="Una lista de hasta 8 conceptos o temas centrales del texto, cada uno con citas del texto.")
    central_concepts: List[str] = Field(description="Una lista de hasta 5 conceptos centrales del texto en el formato 'CONCEPTO: DEFINICIÓN DETALLADA'.")
    discipline: List[str] = Field(description="El area, disciplina o campo al que refiere el documento. Por ejemplo si es un documémico y de qué área, o si es un documento técnico, etc.').")
    authorial_tone: str = Field(description="El tono o la voz del autor (ej. 'Formal y Académico', 'Informal y Conversacional', 'Urgente y Directo', 'Escéptico y Crítico').")
    knowledge_gaps: List[str] = Field(description="Una lista de 3 a 5 preguntas inteligentes y abiertas que el texto inspira pero no responde. Deben ser preguntas, no afirmaciones.")
    final_reflections: List[str] = Field (description="Reflexiuón final sobre la importancia del contenido en el área que aborda, su aporte al conocimiento y apertura de temas de reflexión. Si se trata de documentos más técnicos o laborales pouedes hablar de las posibilidades que abre, proyectos posibles o recomendaciones de gestión")

class CollectionAnalysis(BaseModel):
    """Define la estructura de salida para el análisis de una colección de textos."""
    collection_summary: str = Field(description="Un resumen analítico que sintetiza la información de TODOS los documentos como un todo. No es necesario que sea tan corto")
    cross_cutting_themes: List[ThemeReference] = Field(description="Lista de hasta 10 temas recurrentes de los documentos que puedes identificar, cada uno con citas relacionadas de los documentos. Puedes agruparlos en algún concepto que los englobe cuando hay similitud semántica")
    central_concepts: List[str] = Field(description="Una lista de hasta 5 conceptos, ideas o tesis centrales de la colección en el formato 'CONCEPTO: DEFINICIÓN'.")
    concept_relationships: List[str] = Field(description="Una lista de hasta 5 descripciones de cómo los conceptos centrales se relacionan entre sí en la colección.")
    identified_connections: List[CollectionConnection] = Field(description="Lista de insights específicos que conectan dos o más documentos.")
    emergent_knowledge_gaps: List[str] = Field(description="Lista de preguntas o áreas que la colección en su conjunto no responde o deja abiertas.")
    final_reflections: List[str] = Field (description="Reflexiuón final sobre la importancia del contenido en el área que aborda, su aporte al conocimiento y apertura de temas de reflexión. Si se trata de documentos más técnicos o laborales pouedes hablar de las posibilidades que abre, proyectos posibles o recomendaciones de gestión")


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
                model="gemini-2.5-flash",
                temperature=0.1,
                disable_streaming=False  # Habilita streaming
            )
            logger.info("Modelo Gemini inicializado.")
        return self._gemini_model

    async def _run_analysis_with_parser(self, prompt: str, output_parser: PydanticOutputParser) -> BaseModel:
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

            parsed_output = await output_parser.aparse(response_content)
            return parsed_output
        except Exception as e:
            logger.error(f"Fallo en el pipeline de análisis y parseo del LLM: {e}", exc_info=True)
            raise ValueError(f"No se pudo obtener una respuesta JSON válida del LLM. Error: {e}")

    async def analyze_single_text(self, text: str) -> SingleTextAnalysis:
        """
        Ejecuta un análisis completo y estructurado sobre un único fragmento de texto.
        """
        if not text or len(text.split()) < 30:
            return SingleTextAnalysis(
                executive_summary=text, key_themes=[], central_concepts=[],
                discipline=[], authorial_tone="N/A", knowledge_gaps=[], final_reflections=[]
            )

        prompt = f"""
<<<<<<< HEAD
        Eres un analista experto en análisis textual de conocimientos. Realiza un análisis exhaustivo y detallado del siguiente texto.

        INSTRUCCIONES ESPECÍFICAS:
        1. **Resumen ejecutivo**: Conciso pero completo (50-80 palabras)

        2. **Análisis general**: EXTENSO y profundo (400-600 palabras) que incluya:
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

        4. **Conceptos centrales**: Hasta 8 conceptos en formato 'CONCEPTO: DEFINICIÓN DETALLADA CON CONTEXTO Y EJEMPLOS'

        5. **Disciplina**: Área(s) de conocimiento específica(s)

        6. **Tono del autor**: Descripción precisa del estilo y enfoque

        7. **Brechas de conocimiento**: 5-8 preguntas inteligentes y abiertas que el texto inspira

        8. **Reflexiones finales**: 3-5 reflexiones sobre importancia, aportes y proyecciones

        Para los temas clave y conceptos centrales, utiliza nombres precisos y relevantes al contexto del texto, priorizando términos específicos del dominio o categorías reconocibles por el usuario.

        IMPORTANTE: Los temas clave deben seguir EXACTAMENTE la estructura JSON mostrada arriba, con "theme" y "related_quotes" como campos obligatorios.
=======
        Eres un analista experto en analisis textual de conocimientos. Analiza el siguiente texto en profundidad.
        Extrae el resumen, los temas clave, los conceptos centrales con sus definiciones, el área de conocimiento, el tono del autor y las brechas de conocimiento que revela.
        Para los temas clave y conceptos centrales, utiliza nombres precisos y relevantes al contexto del texto, priorizando términos específicos del dominio o categorías reconocibles por el usuario. Los conceptos centrales deben estar en el formato 'CONCEPTO: DEFINICIÓN'.
>>>>>>> parent of 8b033aa (Feat: Implement workspace-level data filtering and enhance analysis)

        Texto a analizar:
        ---
        {text}
        ---
        """
        parser = PydanticOutputParser(pydantic_object=SingleTextAnalysis)
        result = await self._run_analysis_with_parser(prompt, parser)
        return cast(SingleTextAnalysis, result)

    async def analyze_collection(self, documents: List[Dict[str, str]]) -> CollectionAnalysis:
        """
        Analiza una colección de documentos para encontrar temas transversales, conexiones y brechas de conocimiento emergentes.
        """
        if not documents:
            raise ValueError("La colección de documentos está vacía.")
            
        full_context_text = ""
        for i, doc in enumerate(documents):
            title = doc.get('title', f"Documento {i+1}")
            content_snippet = (doc.get('content', '')[:1000] + '...') if len(doc.get('content', '')) > 1000 else doc.get('content', '')
            full_context_text += f"--- INICIO DOCUMENTO: '{title}' ---\n{content_snippet}\n--- FIN DOCUMENTO: '{title}' ---\n\n"

        prompt = f"""
        Eres un analista de investigación experto en síntesis de conocimiento. Analiza esta colección de documentos.
        Tu tarea es encontrar las conexiones, patrones, temas emergentes con citas relacionadas de los documentos, conceptos centrales con sus definiciones y las relaciones entre estos conceptos que existen **entre** ellos.
        Para los temas emergentes y conceptos centrales, utiliza nombres claros y específicos que reflejen el contenido y el contexto de los documentos, asegurándote de que sean relevantes para el usuario. Los conceptos centrales deben estar en el formato 'CONCEPTO: DEFINICIÓN'. Para cada tema transversal, incluye citas o fragmentos relevantes de los documentos que lo ilustran.

        Colección de documentos:
        {full_context_text}
        """
        parser = PydanticOutputParser(pydantic_object=CollectionAnalysis)
        result = await self._run_analysis_with_parser(prompt, parser)
        return cast(CollectionAnalysis, result)

# --- INSTANCIA ÚNICA ---
# Se crea una única instancia del analizador para ser importada y reutilizada en toda la aplicación.
# Esto asegura que el modelo de Gemini solo se cargue una vez.
text_analyzer = AdvancedTextAnalyzer()
