"""
DynaPictures Skill - KAI OS Orquestador
Expone las funciones de dynapictures.py como herramientas LangChain.
"""
import os
import sys
import json
from typing import Optional, Any

# Añadir el directorio de scripts al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langchain_core.tools import BaseTool

# Importar funciones del módulo dynapictures
from dynapictures import (
    generate_image,
    generate_multipage,
    generate_pdf,
    delete_generated_image,
    batch_generate,
    list_templates,
    get_template,
    list_workspaces,
    create_workspace,
    update_workspace,
    delete_workspace,
    list_media,
    upload_media,
    get_media_asset,
    update_media_asset,
    delete_media_asset,
    subscribe_webhook,
    unsubscribe_webhook,
    download_image,
    setup_credentials,
    DynaPicturesClient,
)


def _result(result: Any) -> str:
    """Serializa el resultado a JSON string."""
    if isinstance(result, str):
        return result
    return json.dumps(result, indent=2, ensure_ascii=False)


# ── Herramientas individuales ──────────────────────────────────────────

class DynapicturesGenerateTool(BaseTool):
    """Genera una imagen usando un template de DynaPictures."""
    name = "dynapictures_generate"
    description = (
        "Genera una imagen usando un template de DynaPictures. "
        "Requiere template_uid. Opcional: format, metadata, params (lista de capas)."
    )

    def _run(
        self,
        template_uid: str,
        format: str = "png",
        metadata: str = "",
        params: Optional[list] = None,
    ) -> str:
        result = generate_image(
            template_uid=template_uid,
            format=format,
            metadata=metadata or None,
            params=params,
        )
        return _result(result)


class DynapicturesGenerateMultipageTool(BaseTool):
    """Genera imágenes multipage desde un template."""
    name = "dynapictures_generate_multipage"
    description = (
        "Genera múltiples páginas desde un template multipage. "
        "Requiere template_uid y pages (lista de páginas con index y layers)."
    )

    def _run(
        self,
        template_uid: str,
        pages: list,
        format: str = "png",
        metadata: str = "",
    ) -> str:
        result = generate_multipage(
            template_uid=template_uid,
            pages=pages,
            format=format,
            metadata=metadata or None,
        )
        return _result(result)


class DynapicturesGeneratePDFTool(BaseTool):
    """Genera un PDF desde un template multipage."""
    name = "dynapictures_generate_pdf"
    description = (
        "Genera un PDF desde un template multipage. "
        "Requiere template_uid y pages."
    )

    def _run(self, template_uid: str, pages: list, metadata: str = "") -> str:
        result = generate_pdf(
            template_uid=template_uid, pages=pages, metadata=metadata or None
        )
        return _result(result)


class DynapicturesDeleteImageTool(BaseTool):
    """Elimina una imagen generada."""
    name = "dynapictures_delete_image"
    description = "Elimina una imagen generada por su ID."

    def _run(self, image_id: str) -> str:
        result = delete_generated_image(image_id=image_id)
        return _result(result)


class DynapicturesBatchGenerateTool(BaseTool):
    """Genera múltiples imágenes en batch."""
    name = "dynapictures_batch_generate"
    description = (
        "Genera múltiples imágenes en batch. "
        "Requiere template_uid y variations (lista de variaciones)."
    )

    def _run(
        self,
        template_uid: str,
        variations: list,
        format: str = "png",
        metadata: str = "",
    ) -> str:
        result = batch_generate(
            template_uid=template_uid,
            variations=variations,
            format=format,
            metadata=metadata or None,
        )
        return _result(result)


class DynapicturesListTemplatesTool(BaseTool):
    """Lista todos los templates disponibles."""
    name = "dynapictures_list_templates"
    description = "Lista todos los templates disponibles en DynaPictures."

    def _run(self, workspace_id: str = "") -> str:
        result = list_templates(workspace_id=workspace_id or None)
        return _result(result)


class DynapicturesGetTemplateTool(BaseTool):
    """Obtiene detalles de un template."""
    name = "dynapictures_get_template"
    description = "Obtiene detalles de un template por su UID."

    def _run(self, template_uid: str) -> str:
        result = get_template(template_uid=template_uid)
        return _result(result)


class DynapicturesListWorkspacesTool(BaseTool):
    """Lista todos los workspaces."""
    name = "dynapictures_list_workspaces"
    description = "Lista todos los workspaces disponibles."

    def _run(self) -> str:
        result = list_workspaces()
        return _result(result)


class DynapicturesCreateWorkspaceTool(BaseTool):
    """Crea un nuevo workspace."""
    name = "dynapictures_create_workspace"
    description = "Crea un nuevo workspace en DynaPictures."

    def _run(self, name: str) -> str:
        result = create_workspace(name=name)
        return _result(result)


class DynapicturesMediaListTool(BaseTool):
    """Lista assets de la media library."""
    name = "dynapictures_list_media"
    description = "Lista todos los assets de la media library."

    def _run(self, workspace_id: str = "") -> str:
        result = list_media(workspace_id=workspace_id or None)
        return _result(result)


class DynapicturesUploadMediaTool(BaseTool):
    """Sube una imagen a la media library."""
    name = "dynapictures_upload_media"
    description = "Sube una imagen a la media library. Requiere file_path local."

    def _run(self, file_path: str, workspace_id: str = "") -> str:
        result = upload_media(
            file_path=file_path, workspace_id=workspace_id or None
        )
        return _result(result)


class DynapicturesSetupCredentialsTool(BaseTool):
    """Configura las credenciales de DynaPictures."""
    name = "dynapictures_setup_credentials"
    description = (
        "Configura la API key de DynaPictures de forma segura. "
        "La guarda en ~/.config/dynapictures/credentials.json con permisos 600."
    )

    def _run(self, api_key: str) -> str:
        path = setup_credentials(api_key=api_key)
        return f"Credenciales guardadas en: {path}"


class DynapicturesDownloadTool(BaseTool):
    """Descarga una imagen generada."""
    name = "dynapictures_download"
    description = "Descarga una imagen generada a disco local."

    def _run(self, image_url: str, output_path: str) -> str:
        result = download_image(image_url=image_url, output_path=output_path)
        return f"✅ Imagen guardada en: {result}"


# ── Orquestador principal ──────────────────────────────────────────────

class Dynapictures(BaseTool):
    """Orquestador principal de DynaPictures. Unifica todas las operaciones."""
    name = "dynapictures"
    description = (
        "Interactúa con la API de DynaPictures para generar y gestionar imágenes dinámicas.\n"
        "Acciones disponibles:\n"
        "- 'generate': Genera imagen (params: template_uid, format, metadata, params)\n"
        "- 'generate_multipage': Genera multipage (params: template_uid, pages, format, metadata)\n"
        "- 'generate_pdf': Genera PDF (params: template_uid, pages, metadata)\n"
        "- 'delete_image': Elimina imagen (params: image_id)\n"
        "- 'batch_generate': Genera en batch (params: template_uid, variations, format, metadata)\n"
        "- 'list_templates': Lista templates (params: workspace_id)\n"
        "- 'get_template': Obtiene template (params: template_uid)\n"
        "- 'list_workspaces': Lista workspaces\n"
        "- 'create_workspace': Crea workspace (params: name)\n"
        "- 'list_media': Lista media (params: workspace_id)\n"
        "- 'upload_media': Sube imagen (params: file_path, workspace_id)\n"
        "- 'setup_credentials': Configura API key (params: api_key)\n"
        "- 'download': Descarga imagen (params: image_url, output_path)"
    )

    def _run(
        self,
        action: str,
        template_uid: str = "",
        format: str = "png",
        metadata: str = "",
        params: Optional[list] = None,
        pages: Optional[list] = None,
        image_id: str = "",
        variations: Optional[list] = None,
        workspace_id: str = "",
        name: str = "",
        file_path: str = "",
        api_key: str = "",
        image_url: str = "",
        output_path: str = "",
    ) -> str:
        try:
            if action == "generate":
                if not template_uid:
                    return "❌ 'template_uid' es requerido"
                result = generate_image(template_uid, format, metadata or None, params)
            elif action == "generate_multipage":
                if not template_uid or not pages:
                    return "❌ 'template_uid' y 'pages' son requeridos"
                result = generate_multipage(template_uid, pages, format, metadata or None)
            elif action == "generate_pdf":
                if not template_uid or not pages:
                    return "❌ 'template_uid' y 'pages' son requeridos"
                result = generate_pdf(template_uid, pages, metadata or None)
            elif action == "delete_image":
                if not image_id:
                    return "❌ 'image_id' es requerido"
                result = delete_generated_image(image_id)
            elif action == "batch_generate":
                if not template_uid or not variations:
                    return "❌ 'template_uid' y 'variations' son requeridos"
                result = batch_generate(template_uid, variations, format, metadata or None)
            elif action == "list_templates":
                result = list_templates(workspace_id or None)
            elif action == "get_template":
                if not template_uid:
                    return "❌ 'template_uid' es requerido"
                result = get_template(template_uid)
            elif action == "list_workspaces":
                result = list_workspaces()
            elif action == "create_workspace":
                if not name:
                    return "❌ 'name' es requerido"
                result = create_workspace(name)
            elif action == "list_media":
                result = list_media(workspace_id or None)
            elif action == "upload_media":
                if not file_path:
                    return "❌ 'file_path' es requerido"
                result = upload_media(file_path, workspace_id or None)
            elif action == "setup_credentials":
                if not api_key:
                    return "❌ 'api_key' es requerido"
                path = setup_credentials(api_key)
                return f"✅ Credenciales guardadas en: {path}"
            elif action == "download":
                if not image_url or not output_path:
                    return "❌ 'image_url' y 'output_path' son requeridos"
                result = download_image(image_url, output_path)
                return f"✅ Imagen guardada en: {result}"
            else:
                return f"❌ Acción no soportada: {action}"
            return _result(result)
        except Exception as e:
            return f"❌ Error: {str(e)}"
