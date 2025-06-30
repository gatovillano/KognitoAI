import os
import io
import logging
from fastapi import UploadFile
from PIL import Image

from tools.image_background_eraser_tool import ImageBackgroundEraserTool

logger = logging.getLogger(__name__)

async def process_image_with_background_eraser(file: UploadFile) -> str:
    """
    Recibe un archivo de imagen, elimina su fondo y devuelve la ruta del archivo resultante.
    """
    try:
        # Guardar el archivo temporalmente
        upload_dir = "/tmp/kognito_uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        file_extension = os.path.splitext(file.filename)[1]
        temp_file_path = os.path.join(upload_dir, f"uploaded_image_{os.urandom(8).hex()}{file_extension}")
        
        with open(temp_file_path, "wb") as buffer:
            while True:
                chunk = await file.read(1024)
                if not chunk:
                    break
                buffer.write(chunk)
        
        logger.info(f"Archivo temporal guardado en: {temp_file_path}")

        # Usar la herramienta ImageBackgroundEraserTool
        eraser_tool = ImageBackgroundEraserTool()
        output_data = await eraser_tool._arun(temp_file_path) # Usar _arun para ejecución asíncrona

        # Guardar los datos de salida en un archivo temporal
        output_file_path = os.path.join(upload_dir, f"processed_image_{os.urandom(8).hex()}.png")
        with open(output_file_path, "wb") as output_file:
            output_file.write(output_data)
        
        logger.info(f"Imagen procesada guardada en: {output_file_path}")

        # Limpiar el archivo temporal original
        os.remove(temp_file_path)
        logger.info(f"Archivo temporal original eliminado: {temp_file_path}")

        if os.path.exists(output_file_path):
            return output_file_path
        else:
            logger.error(f"No se pudo guardar la imagen procesada en: {output_file_path}")
            raise Exception("Error al guardar la imagen procesada.")

    except Exception as e:
        logger.error(f"Error en process_image_with_background_eraser: {e}", exc_info=True)
        raise
