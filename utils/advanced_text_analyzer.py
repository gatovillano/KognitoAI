# utils/advanced_text_analyzer.py

import logging
import asyncio
from typing import List, Dict, Optional

# LangChain y Pydantic para robustez y estructura
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic.v1 import BaseModel, Field # Usamos pydantic v1 por compatibilidad con LangChain

logger = logging.getLogger(__name__)

# --- Modelos de Salida Pydantic para garantizar la estructura del LLM ---

class SingleTextAnalysis(BaseModel):
    """Define la estructura de salida para el análisis de un único texto."""
    executive_summary: str = Field(description="Un resumen conciso que captura la esencia y las conclusiones principales del texto.")
    key_themes: List[str] = Field(description="Una lista de hasta 8 conceptos o temas centrales del texto.")
    sentiment_analysis: str = Field(description="El sentimiento general del texto (ej. 'Positivo', 'Negativo', 'Neutral', 'Ambivalente').")
    authorial_tone: str = Field(description="El tono o la voz del autor (ej. 'Formal y Académico', 'Informal y Conversacional', 'Urgente y Directo', 'Escéptico y Crítico').")
    knowledge_gaps: List[str] = Field(description="Una lista de 3 a 5 preguntas inteligentes y abiertas que el texto inspira pero no responde. Deben ser preguntas, no afirmaciones.")

class CollectionConnection(BaseModel):
    """Define una conexión específica encontrada entre documentos de una colección."""
    document_titles: List[str] = Field(description="Los títulos de los documentos entre los que se encontró la conexión.")
    insight: str = Field(description="Descripción de la sinergia, evolución o contradicción encontrada entre estos documentos.")

class CollectionAnalysis(BaseModel):
    """Define la estructura de salida para el análisis de una colección de textos."""
    collection_summary: str = Field(description="Un resumen ejecutivo que sintetiza la información de TODOS los documentos como un todo.")
    cross_cutting_themes: List[str] = Field(description="Lista de hasta 10 temas que aparecen repetidamente en varios documentos.")
    identified_connections: List[CollectionConnection] = Field(description="Lista de insights específicos que conectan dos o más documentos.")
    emergent_knowledge_gaps: List[str] = Field(description="Lista de preguntas o áreas que la colección en su conjunto no responde o deja abiertas.")


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
            self._gemini_model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)
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
            parsed_output = await output_parser.aparse(response.content)
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
                executive_summary=text, key_themes=[], sentiment_analysis="Neutral",
                authorial_tone="N/A", knowledge_gaps=[]
            )

        prompt = f"""
        Eres un analista estratégico. Analiza el siguiente texto en profundidad.
        Extrae el resumen, los temas clave, el sentimiento, el tono del autor y las brechas de conocimiento que revela.

        Texto a analizar:
        ---
        {text}
        ---
        """
        parser = PydanticOutputParser(pydantic_object=SingleTextAnalysis)
        return await self._run_analysis_with_parser(prompt, parser)

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
        Tu tarea es encontrar las conexiones, patrones, y temas emergentes que existen **entre** ellos.

        Colección de documentos:
        {full_context_text}
        """
        parser = PydanticOutputParser(pydantic_object=CollectionAnalysis)
        return await self._run_analysis_with_parser(prompt, parser)

# --- INSTANCIA ÚNICA ---
# Se crea una única instancia del analizador para ser importada y reutilizada en toda la aplicación.
# Esto asegura que el modelo de Gemini solo se cargue una vez.
text_analyzer = AdvancedTextAnalyzer()