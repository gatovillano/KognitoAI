import logging
import os
import io
from PIL import Image
from rembg import remove # Se requiere la instalación de 'rembg' y 'Pillow'
from typing import Optional, Type, Any

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)

class ImageBackgroundEraserInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de eliminación de fondo de imágenes.
    Valida que el argumento necesario sea proporcionado por el LLM.
    """
    image_path: str = Field(
        ...,
        description="La ruta del archivo de imagen local del cual se desea eliminar el fondo."
    )

class ImageBackgroundEraserTool(BaseTool):
    account_id: Optional[str] = Field(None, description="ID de la cuenta asociada a esta herramienta.")
    workspace_id: Optional[str] = Field(None, description="ID del espacio de trabajo del usuario, inyectado automáticamente.")
    telegram_id: Optional[int] = Field(None, description="ID de Telegram del usuario, inyectado automáticamente.")
    name: str = "image_background_eraser"
    description: str = (
        "Útil para eliminar el fondo de una imagen. "
        "Recibe la ruta de un archivo de imagen local y devuelve los datos de la imagen PNG sin fondo directamente."
    )
    args_schema: Type[BaseModel] = ImageBackgroundEraserInput
    return_direct: bool = False  # El agente debe procesar la respuesta.

    async def _arun(self, image_path: str, **kwargs: Any) -> bytes:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona para eliminar el fondo de una imagen.
        
        Args:
            image_path: La ruta del archivo de imagen local.
            **kwargs: Argumentos adicionales (no utilizados).
            
        Returns:
            Los datos de la imagen PNG sin fondo como bytes.
        """
        if not os.path.exists(image_path):
            raise ValueError(f"El archivo de imagen no existe en la ruta especificada: {image_path}")

        try:
            logger.info(f"Eliminando el fondo de la imagen: {image_path}")
            with open(image_path, 'rb') as i:
                input_data = i.read()

            output_data = remove(input_data)
            logger.info(f"Fondo de la imagen eliminado exitosamente.")
            return output_data
        except Exception as e:
            logger.error(f"Error al eliminar el fondo de la imagen: {e}", exc_info=True)
            raise Exception(f"Error al eliminar el fondo de la imagen: {str(e)}")

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("image_background_eraser no soporta ejecución síncrona.")

if __name__ == "__main__":
    # Ejemplo de uso (requiere una imagen de prueba)
    # Crear una imagen de prueba si no existe
    test_image_path = "test_image.png"
    if not os.path.exists(test_image_path):
        try:
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (100, 100), color = 0xFF0000) # Rojo en formato entero
            d = ImageDraw.Draw(img)
            d.ellipse((20, 20, 80, 80), fill=(0, 0, 255))
            img.save(test_image_path)
            print(f"Imagen de prueba '{test_image_path}' creada.")
        except ImportError:
            print("Pillow no está instalado. No se puede crear la imagen de prueba.")
            print("Por favor, instala Pillow: pip install Pillow")
            exit()
    
    print(f"Probando la herramienta ImageBackgroundEraserTool con {test_image_path}...")
    tool = ImageBackgroundEraserTool()
    result = tool.run(test_image_path)
    print(f"Resultado: {result}")
    if os.path.exists(result):
        print(f"Verifica la imagen en: {result}")
    else:
        print("La operación falló.")
