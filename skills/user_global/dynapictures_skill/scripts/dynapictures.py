"""
DynaPictures Skill - Generación dinámica de imágenes vía API.

Uso seguro de API Key mediante variable de entorno:
    export DYNAPICTURES_API_KEY="tu-api-key-aqui"

O mediante archivo de configuración:
    ~/.config/dynapictures/credentials.json
"""

import os
import json
import requests
from pathlib import Path
from typing import Optional, Any


# ─── Configuración ────────────────────────────────────────────────────────────

BASE_URL = "https://api.dynapictures.com"
CREDENTIALS_PATH = Path.home() / ".config" / "dynapictures" / "credentials.json"


def _get_api_key() -> str:
    """
    Obtiene la API Key de forma segura.
    Prioridad: variable de entorno > archivo de configuración.
    """
    api_key = os.environ.get("DYNAPICTURES_API_KEY")
    if api_key:
        return api_key

    if CREDENTIALS_PATH.exists():
        try:
            with open(CREDENTIALS_PATH, "r") as f:
                creds = json.load(f)
            api_key = creds.get("DYNAPICTURES_API_KEY")
            if api_key:
                return api_key
        except (json.JSONDecodeError, IOError):
            pass

    raise EnvironmentError(
        "No se encontró la API Key de DynaPictures. "
        "Configura la variable de entorno DYNAPICTURES_API_KEY o crea "
        f"el archivo {CREDENTIALS_PATH} con: "
        '{"DYNAPICTURES_API_KEY": "tu-api-key"}'
    )


def _get_headers() -> dict:
    """Genera los headers de autenticación."""
    return {
        "Authorization": f"Bearer {_get_api_key()}",
        "Content-Type": "application/json",
    }


def _request(method: str, endpoint: str, **kwargs) -> dict:
    """
    Realiza una request HTTP a la API de DynaPictures.
    """
    url = f"{BASE_URL}{endpoint}"
    headers = _get_headers()

    response = requests.request(method, url, headers=headers, timeout=120, **kwargs)

    if response.status_code == 401:
        raise PermissionError(
            "API Key inválida o expirada. Verifica tu API Key en dynapictures.com"
        )
    elif response.status_code == 404:
        raise ValueError(f"Recurso no encontrado: {endpoint}. Verifica el UID.")
    elif response.status_code == 429:
        retry_after = response.headers.get("Retry-After", "60")
        raise RuntimeError(
            f"Rate limit excedido. Reintenta después de {retry_after} segundos."
        )

    response.raise_for_status()
    return response.json()


# ─── Generación de Imágenes ───────────────────────────────────────────────────

def generate_image(
    template_uid: str,
    format: str = "png",
    metadata: Optional[str] = None,
    params: Optional[list] = None,
) -> dict:
    """
    Genera una imagen individual desde un template.

    Args:
        template_uid: UID del template en DynaPictures
        format: Formato de salida (png, jpeg, webp, avif). Default: png
        metadata: Datos personalizados opcionales
        params: Lista de objetos con personalización de capas.
                Cada objeto debe tener al menos {"name": "nombre_capa"}

    Returns:
        dict con keys: id, templateId, imageUrl, thumbnailUrl,
                       retinaThumbnailUrl, metadata, width, height

    Ejemplo:
        result = generate_image(
            template_uid="abc123def456",
            format="jpeg",
            params=[
                {"name": "headline", "text": "¡Hola Mundo!", "color": "#333"},
                {"name": "image1", "imageUrl": "https://example.com/photo.jpg"},
            ]
        )
        print(result["imageUrl"])
    """
    body: dict = {"format": format}
    if metadata:
        body["metadata"] = metadata
    if params:
        body["params"] = params

    return _request("POST", f"/designs/{template_uid}", json=body)


def generate_multipage(
    template_uid: str,
    pages: list,
    format: str = "png",
    metadata: Optional[str] = None,
) -> dict:
    """
    Genera múltiples páginas desde un template multipágina.

    Args:
        template_uid: UID del template multipágina
        pages: Lista de páginas, cada una con "index" y "layers"
        format: Formato de salida (png, jpeg, webp, avif). Default: png
        metadata: Datos personalizados opcionales

    Returns:
        dict con keys: templateId, templateName, pages (lista)

    Ejemplo:
        result = generate_multipage(
            template_uid="multipage_uid",
            pages=[
                {"index": 0, "layers": [{"name": "title", "text": "Slide 1"}]},
                {"index": 1, "layers": [{"name": "title", "text": "Slide 2"}]}
            ]
        )
    """
    body: dict = {"format": format, "pages": pages}
    if metadata:
        body["metadata"] = metadata

    return _request("POST", f"/designs/{template_uid}", json=body)


def generate_pdf(
    template_uid: str,
    pages: list,
    metadata: Optional[str] = None,
) -> dict:
    """
    Genera un PDF desde un template multipágina.

    Args:
        template_uid: UID del template
        pages: Lista de páginas con sus capas
        metadata: Datos personalizados opcionales

    Returns:
        dict con la información del PDF generado
    """
    body: dict = {"pages": pages}
    if metadata:
        body["metadata"] = metadata

    return _request("POST", f"/designs/{template_uid}/pdf", json=body)


def delete_generated_image(image_id: str) -> dict:
    """
    Elimina una imagen generada.

    Args:
        image_id: ID de la imagen a eliminar

    Returns:
        dict con el resultado de la operación
    """
    return _request("DELETE", f"/images/{image_id}")


# ─── Batch Generation ─────────────────────────────────────────────────────────

def batch_generate(
    template_uid: str,
    variations: list,
    format: str = "png",
    metadata: Optional[str] = None,
) -> list:
    """
    Genera múltiples imágenes en batch desde un template.

    Args:
        template_uid: UID del template
        variations: Lista de variaciones, cada una con "params"
        format: Formato de salida. Default: png
        metadata: Datos personalizados opcionales

    Returns:
        Lista de dicts con las imágenes generadas

    Ejemplo:
        products = [
            {"name": "Producto A", "price": "$19.99"},
            {"name": "Producto B", "price": "$29.99"},
        ]
        variations = [
            {"params": [{"name": "product_name", "text": p["name"]},
                        {"name": "price", "text": p["price"]}]}
            for p in products
        ]
        results = batch_generate(
            template_uid="product_template_uid",
            variations=variations,
            format="jpeg"
        )
    """
    results = []
    for variation in variations:
        body: dict = {"format": format}
        if metadata:
            body["metadata"] = metadata
        body.update(variation)

        result = _request("POST", f"/designs/{template_uid}", json=body)
        results.append(result)

    return results


# ─── Templates ────────────────────────────────────────────────────────────────

def list_templates(workspace_id: Optional[str] = None) -> list:
    """
    Lista todos los templates disponibles.

    Args:
        workspace_id: ID opcional del workspace para filtrar

    Returns:
        Lista de templates
    """
    params = {}
    if workspace_id:
        params["workspaceId"] = workspace_id

    return _request("GET", "/templates", params=params)


def get_template(template_uid: str) -> dict:
    """
    Obtiene detalles de un template específico.

    Args:
        template_uid: UID del template

    Returns:
        dict con la información del template
    """
    return _request("GET", f"/templates/{template_uid}")


# ─── Workspaces ───────────────────────────────────────────────────────────────

def list_workspaces() -> list:
    """
    Lista todos los workspaces.

    Returns:
        Lista de workspaces
    """
    return _request("GET", "/workspaces")


def create_workspace(name: str) -> dict:
    """
    Crea un nuevo workspace.

    Args:
        name: Nombre del workspace

    Returns:
        dict con la información del workspace creado
    """
    return _request("POST", "/workspaces", json={"name": name})


def update_workspace(workspace_id: str, name: str) -> dict:
    """
    Actualiza un workspace existente.

    Args:
        workspace_id: ID del workspace
        name: Nuevo nombre

    Returns:
        dict con la información actualizada
    """
    return _request("PUT", f"/workspaces/{workspace_id}", json={"name": name})


def delete_workspace(workspace_id: str) -> dict:
    """
    Elimina un workspace.

    Args:
        workspace_id: ID del workspace

    Returns:
        dict con el resultado de la operación
    """
    return _request("DELETE", f"/workspaces/{workspace_id}")


# ─── Media Library ────────────────────────────────────────────────────────────

def list_media(workspace_id: Optional[str] = None) -> list:
    """
    Lista archivos en la media library.

    Args:
        workspace_id: ID opcional del workspace para filtrar

    Returns:
        Lista de archivos multimedia
    """
    params = {}
    if workspace_id:
        params["workspaceId"] = workspace_id

    return _request("GET", "/media", params=params)


def upload_media(file_path: str, workspace_id: Optional[str] = None) -> dict:
    """
    Sube una imagen a la media library.

    Args:
        file_path: Ruta local del archivo a subir
        workspace_id: ID opcional del workspace destino

    Returns:
        dict con la información del archivo subido
    """
    api_key = _get_api_key()
    url = f"{BASE_URL}/media"

    headers = {"Authorization": f"Bearer {api_key}"}

    data = {}
    if workspace_id:
        data["workspaceId"] = workspace_id

    with open(file_path, "rb") as f:
        files = {"file": f}
        response = requests.post(
            url, headers=headers, data=data, files=files, timeout=120
        )

    response.raise_for_status()
    return response.json()


def get_media_asset(asset_id: str) -> dict:
    """
    Obtiene información de un asset multimedia.

    Args:
        asset_id: ID del asset

    Returns:
        dict con la información del asset
    """
    return _request("GET", f"/media/{asset_id}")


def update_media_asset(asset_id: str, **kwargs) -> dict:
    """
    Actualiza un asset multimedia.

    Args:
        asset_id: ID del asset
        **kwargs: Campos a actualizar

    Returns:
        dict con la información actualizada
    """
    return _request("PUT", f"/media/{asset_id}", json=kwargs)


def delete_media_asset(asset_id: str) -> dict:
    """
    Elimina un asset multimedia.

    Args:
        asset_id: ID del asset

    Returns:
        dict con el resultado de la operación
    """
    return _request("DELETE", f"/media/{asset_id}")


# ─── Webhooks ─────────────────────────────────────────────────────────────────

def subscribe_webhook(url: str, events: Optional[list] = None) -> dict:
    """
    Suscribe un webhook para notificaciones de eventos.

    Args:
        url: URL del webhook que recibirá las notificaciones
        events: Lista de eventos a escuchar (opcional)

    Returns:
        dict con la información de la suscripción
    """
    body: dict = {"url": url}
    if events:
        body["events"] = events

    return _request("POST", "/webhooks", json=body)


def unsubscribe_webhook(webhook_id: str) -> dict:
    """
    Cancela una suscripción de webhook.

    Args:
        webhook_id: ID del webhook a eliminar

    Returns:
        dict con el resultado de la operación
    """
    return _request("DELETE", f"/webhooks/{webhook_id}")


# ─── Utilidades ───────────────────────────────────────────────────────────────

def download_image(image_url: str, output_path: str) -> str:
    """
    Descarga una imagen generada a disco local.

    Args:
        image_url: URL de la imagen generada
        output_path: Ruta local donde guardar la imagen

    Returns:
        str: Ruta del archivo guardado
    """
    response = requests.get(image_url, timeout=60)
    response.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(response.content)

    return output_path


def setup_credentials(api_key: str) -> str:
    """
    Configura las credenciales de forma segura en el archivo local.

    Args:
        api_key: API Key de DynaPictures

    Returns:
        str: Ruta del archivo de credenciales
    """
    CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)

    creds = {"DYNAPICTURES_API_KEY": api_key}
    with open(CREDENTIALS_PATH, "w") as f:
        json.dump(creds, f, indent=2)

    os.chmod(CREDENTIALS_PATH, 0o600)

    return str(CREDENTIALS_PATH)


# ─── Clase de conveniencia ────────────────────────────────────────────────────

class DynaPicturesClient:
    """
    Cliente de conveniencia para la API de DynaPictures.

    Uso:
        client = DynaPicturesClient()
        result = client.generate_image(
            template_uid="abc123",
            params=[{"name": "title", "text": "Hola"}]
        )
        print(result["imageUrl"])
    """

    def __init__(self, api_key: Optional[str] = None):
        if api_key:
            os.environ["DYNAPICTURES_API_KEY"] = api_key

    generate_image = staticmethod(generate_image)
    generate_multipage = staticmethod(generate_multipage)
    generate_pdf = staticmethod(generate_pdf)
    delete_generated_image = staticmethod(delete_generated_image)
    batch_generate = staticmethod(batch_generate)
    list_templates = staticmethod(list_templates)
    get_template = staticmethod(get_template)
    list_workspaces = staticmethod(list_workspaces)
    create_workspace = staticmethod(create_workspace)
    update_workspace = staticmethod(update_workspace)
    delete_workspace = staticmethod(delete_workspace)
    list_media = staticmethod(list_media)
    upload_media = staticmethod(upload_media)
    get_media_asset = staticmethod(get_media_asset)
    update_media_asset = staticmethod(update_media_asset)
    delete_media_asset = staticmethod(delete_media_asset)
    subscribe_webhook = staticmethod(subscribe_webhook)
    unsubscribe_webhook = staticmethod(unsubscribe_webhook)
    download_image = staticmethod(download_image)
    setup_credentials = staticmethod(setup_credentials)
