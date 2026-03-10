import logging
import markdown
from typing import Type, Optional, Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)

class HTMLGeneratorInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de generación de HTML.
    Valida que el LLM proporcione todos los argumentos necesarios.
    """
    content: str = Field(
        ...,
        description="El contenido en formato Markdown o texto plano que se convertirá a HTML."
    )
    title: Optional[str] = Field(
        "Documento Generado por KognitoAI",
        description="El título del documento HTML. Se usará en la etiqueta <title>."
    )
    include_css: bool = Field(
        True,
        description="Si se debe incluir un CSS básico para mejorar la presentación del HTML. Por defecto es True."
    )

class HTMLGeneratorTool(BaseTool):
    args_schema: Type[BaseModel] = HTMLGeneratorInput
    name: str = "html_generator"
    description: str = (
        "Genera un documento HTML a partir de contenido en formato Markdown o texto plano. "
        "Útil para crear informes, resúmenes o cualquier contenido que necesite ser visualizado en un navegador web. "
        "El contenido se puede proporcionar en Markdown para un formato enriquecido. "
        "Se puede especificar un título y si se debe incluir un CSS básico para una mejor presentación."
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        logger.debug("HTMLGeneratorTool initialized.")

    async def _arun(self, content: str, title: Optional[str] = None, include_css: bool = True) -> str:
        """
        Genera un documento HTML a partir del contenido proporcionado.
        """
        logger.info(f"Generando HTML para el título: {title if title else 'Sin título'}")

        # Convertir Markdown a HTML
        html_content = markdown.markdown(content, extensions=['tables', 'fenced_code', 'toc', 'nl2br'])

        # CSS básico para una mejor presentación
        base_css = """
        <style>
            body { font-family: 'Arial', sans-serif; line-height: 1.6; color: #333; margin: 20px; background-color: #f4f4f4; }
            h1, h2, h3, h4, h5, h6 { color: #0056b3; margin-top: 1em; margin-bottom: 0.5em; }
            pre { background-color: #eee; padding: 10px; border-radius: 5px; overflow-x: auto; }
            code { font-family: 'Courier New', monospace; background-color: #e0e0e0; padding: 2px 4px; border-radius: 3px; }
            pre code { background-color: transparent; padding: 0; }
            table { width: 100%; border-collapse: collapse; margin-bottom: 1em; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            a { color: #007bff; text-decoration: none; }
            a:hover { text-decoration: underline; }
            blockquote { border-left: 4px solid #ccc; margin: 1.5em 10px; padding: 0.5em 10px; color: #666; }
            ul, ol { margin-bottom: 1em; }
        </style>
        """ if include_css else ""

        # Crear el HTML completo
        full_html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    {base_css}
</head>
<body>
    {html_content}
</body>
</html>
        """
        return full_html

    def _run(self, content: str, title: Optional[str] = None, include_css: bool = True) -> str:
        """
        Método síncrono para compatibilidad, delega en _arun.
        """
        import asyncio
        return asyncio.run(self._arun(content, title, include_css))

