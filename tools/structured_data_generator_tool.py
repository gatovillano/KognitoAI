# tools/structured_data_generator_tool.py

import logging
import os
import uuid
import re
from typing import Any, Type, Optional, List, Dict
from datetime import datetime

import pandas as pd
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from core.config import settings
from api.galleries import MEDIA_ROOT

logger = logging.getLogger(__name__)

class StructuredDataGeneratorInput(BaseModel):
    """Input schema for the Structured Data Generator tool."""
    data: List[Dict[str, Any]] = Field(
        ...,
        description="Lista de diccionarios que representan las filas de datos. Cada diccionario debe tener las mismas claves (columnas)."
    )
    format: str = Field(
        "csv",
        description="El formato del archivo a generar: 'csv', 'excel' (o 'xlsx'), 'ods'."
    )
    filename: Optional[str] = Field(
        None,
        description="Nombre opcional para el archivo generado. Si no se proporciona, se usará uno aleatorio."
    )
    title: Optional[str] = Field(
        "Datos Estructurados",
        description="Título descriptivo para el conjunto de datos."
    )

class StructuredDataGeneratorTool(BaseTool):
    """
    A LangChain tool that generates structured data files (CSV, Excel, ODS) from a list of dictionaries.
    """
    name: str = "structured_data_generator_tool"
    description: str = (
        "Genera archivos de datos estructurados (CSV, Excel, ODS) a partir de una lista de datos. "
        "Úsala cuando el usuario necesite descargar una tabla, un reporte o un conjunto de datos organizado. "
        "Formatos soportados: 'csv', 'excel' (xlsx), 'ods'."
    )
    
    account_id: Optional[str] = Field(None, description="User account ID.")
    workspace_id: Optional[str] = Field(None, description="Current workspace ID.")
    
    args_schema: Type[BaseModel] = StructuredDataGeneratorInput
    return_direct: bool = False

    async def _arun(
        self, 
        data: List[Dict[str, Any]], 
        format: str = "csv", 
        filename: Optional[str] = None, 
        title: str = "Datos Estructurados", 
        **kwargs: Any
    ) -> Any:
        """
        Executes the tool logic asynchronously.
        """
        format = format.lower()
        if format not in ["csv", "excel", "xlsx", "ods"]:
            return {
                "context_for_llm": f"Error: Formato '{format}' no soportado. Usa 'csv', 'excel' o 'ods'.",
                "sources": []
            }

        logger.info(f"Generating {format} file. Title: {title}")
        
        try:
            # 0. Cleanup old files
            from utils.file_cleanup import cleanup_old_generated_files
            cleanup_old_generated_files()
            
            # 1. Create directory for generated files
            output_dir = os.path.join(MEDIA_ROOT, "generated_data")
            os.makedirs(output_dir, exist_ok=True)
            
            # 2. Determine extension and engine
            ext = ".csv"
            if format in ["excel", "xlsx"]:
                ext = ".xlsx"
            elif format == "ods":
                ext = ".ods"
            
            # 3. Determine final filename
            suffix = uuid.uuid4().hex[:4]
            if not filename:
                filename = f"data_{uuid.uuid4().hex[:8]}{ext}"
            else:
                name_part, ext_part = os.path.splitext(filename)
                if not ext_part:
                    ext_part = ext
                filename = f"{name_part}_{suffix}{ext_part}"
            
            # Clean filename
            filename = re.sub(r'[^\w\.-]', '_', filename)
            file_path = os.path.join(output_dir, filename)
            
            # 4. Create DataFrame and save
            df = pd.DataFrame(data)
            
            if ext == ".csv":
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
            elif ext == ".xlsx":
                df.to_excel(file_path, index=False, engine='openpyxl')
            elif ext == ".ods":
                df.to_excel(file_path, index=False, engine='odf') # Pandas uses odf engine for .ods via to_excel
            
            logger.info(f"✅ File successfully generated at: {file_path}")
            
            # 5. Construct download URL
            base_url = settings.api_server_url.rstrip("/")
            download_url = f"{base_url}/media/generated_data/{filename}"
            
            return {
                "context_for_llm": f"Archivo {format.upper()} generado exitosamente: '{title}'. La URL de descarga es: {download_url}.",
                "sources": [
                    {
                        "id": 1,
                        "title": f"📊 Datos: {title} ({format.upper()})",
                        "url": download_url,
                        "snippet": f"Archivo de datos estructurados generado en formato {format.upper()}. Título: {title}",
                        "type": "document",
                        "metadata": {
                            "filename": filename,
                            "file_path": file_path,
                            "generated_at": datetime.now().isoformat(),
                            "format": format,
                            "rows": len(data)
                        }
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Error generating structured data file: {e}", exc_info=True)
            return {
                "context_for_llm": f"Ocurrió un error al intentar generar el archivo {format.upper()}: {e}",
                "sources": []
            }

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """Synchronous execution is not supported."""
        raise NotImplementedError("structured_data_generator_tool does not support synchronous execution.")
