import logging
import os
import io
from PIL import Image
from rembg import remove # Se requiere la instalación de 'rembg' y 'Pillow'

from langchain_core.tools import Tool

logger = logging.getLogger(__name__)

class ImageBackgroundEraserTool(Tool):
    name = "image_background_eraser"
    description = (
        "Útil para eliminar el fondo de una imagen. "
        "Recibe la ruta de un archivo de imagen local y devuelve la ruta de la imagen con el fondo eliminado. "
        "La imagen de salida se guardará en el mismo directorio que la entrada con '_no_bg' añadido al nombre. "
        "Ejemplo: image_background_eraser(image_path='/path/to/image.png')"
    )
    func = None  # Se define como atributo para compatibilidad con LangChain

    def _run(self, image_path: str) -> str:
        """
        Elimina el fondo de una imagen.
        """
        # Asignar _run a func para compatibilidad con LangChain
        self.func = self._run
        if not os.path.exists(image_path):
            return f"Error: El archivo de imagen no existe en la ruta especificada: {image_path}"

        try:
            logger.info(f"Eliminando el fondo de la imagen: {image_path}")
            with open(image_path, 'rb') as i:
                input_data = i.read()

            output_data = remove(input_data)

            base, ext = os.path.splitext(image_path)
            output_path = f"{base}_no_bg{ext}"

            with open(output_path, 'wb') as o:
                o.write(output_data)

            logger.info(f"Fondo de la imagen eliminado. Imagen guardada en: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error al eliminar el fondo de la imagen: {e}", exc_info=True)
            return f"Error al eliminar el fondo de la imagen: {str(e)}"

    async def _arun(self, image_path: str) -> str:
        """
        Método asíncrono para eliminar el fondo de una imagen (no implementado, usa _run).
        """
        return self._run(image_path)

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
