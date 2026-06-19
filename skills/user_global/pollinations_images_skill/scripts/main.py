"""
Pollinations Images Skill - Generación de imágenes con IA
Usa la API gratuita de Pollinations.ai para generar imágenes desde texto.
"""

import requests
import os
import time
import json
from pathlib import Path
from langchain_core.tools import BaseTool


class PollinationsImageGenerator(BaseTool):
    """Herramienta para generar imágenes usando la API de Pollinations.ai"""
    
    name: str = "pollinations_generate_image"
    description: str = (
        "Genera imágenes usando la API gratuita de Pollinations.ai. "
        "Parámetros: prompt (descripción de la imagen), model (flux, turbo, gptimage, etc.), "
        "width (ancho, default 1024), height (alto, default 1024), seed (opcional, para reproducibilidad), "
        "nologo (true/false, default true), enhance (true/false, default false). "
        "Retorna la URL de la imagen generada."
    )

    def _run(
        self,
        prompt: str,
        model: str = "flux",
        width: int = 1024,
        height: int = 1024,
        seed: int = None,
        nologo: bool = True,
        enhance: bool = False,
        save_path: str = None,
    ) -> str:
        try:
            # Construir la URL de la API
            encoded_prompt = requests.utils.quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            
            # Parámetros
            params = {
                "model": model,
                "width": width,
                "height": height,
                "nologo": str(nologo).lower(),
                "enhance": str(enhance).lower(),
            }
            
            if seed is not None:
                params["seed"] = seed
            
            # API key opcional (para mayor rate limit)
            api_key = os.environ.get("POLLINATIONS_API_KEY")
            if api_key:
                params["key"] = api_key
            
            # Hacer la petición
            response = requests.get(url, params=params, timeout=120)
            
            if response.status_code == 200:
                # Es una imagen binaria
                content_type = response.headers.get("content-type", "")
                
                if "image" in content_type:
                    # Guardar la imagen si se especifica ruta
                    if save_path:
                        save_dir = Path(save_path)
                        save_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Determinar extensión
                        ext = "png"
                        if "jpeg" in content_type or "jpg" in content_type:
                            ext = "jpg"
                        elif "webp" in content_type:
                            ext = "webp"
                        
                        timestamp = int(time.time())
                        filename = f"pollinations_{timestamp}.{ext}"
                        filepath = save_dir / filename
                        
                        with open(filepath, "wb") as f:
                            f.write(response.content)
                        
                        return json.dumps({
                            "success": True,
                            "image_url": url,
                            "saved_to": str(filepath),
                            "size_bytes": len(response.content),
                            "model": model,
                            "width": width,
                            "height": height,
                            "prompt": prompt,
                        }, ensure_ascii=False)
                    else:
                        # Guardar en /tmp por defecto
                        tmp_dir = Path("/tmp/pollinations_images")
                        tmp_dir.mkdir(parents=True, exist_ok=True)
                        
                        ext = "png"
                        if "jpeg" in content_type or "jpg" in content_type:
                            ext = "jpg"
                        
                        timestamp = int(time.time())
                        filename = f"pollinations_{timestamp}.{ext}"
                        filepath = tmp_dir / filename
                        
                        with open(filepath, "wb") as f:
                            f.write(response.content)
                        
                        return json.dumps({
                            "success": True,
                            "image_url": url,
                            "saved_to": str(filepath),
                            "size_bytes": len(response.content),
                            "model": model,
                            "width": width,
                            "height": height,
                            "prompt": prompt,
                        }, ensure_ascii=False)
                else:
                    return json.dumps({
                        "success": False,
                        "error": f"Respuesta no es imagen. Content-Type: {content_type}",
                        "response_text": response.text[:500],
                    }, ensure_ascii=False)
            
            elif response.status_code == 429:
                return json.dumps({
                    "success": False,
                    "error": "Rate limit excedido. Espera unos segundos y reintenta.",
                    "status_code": 429,
                }, ensure_ascii=False)
            
            else:
                return json.dumps({
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text[:500]}",
                    "status_code": response.status_code,
                }, ensure_ascii=False)
        
        except requests.exceptions.Timeout:
            return json.dumps({
                "success": False,
                "error": "Timeout: la generación tardó demasiado. Reintenta con un prompt más simple.",
            }, ensure_ascii=False)
        
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error inesperado: {str(e)}",
            }, ensure_ascii=False)


class PollinationsImageURL(BaseTool):
    """Herramienta que solo genera la URL de la imagen sin descargarla."""
    
    name: str = "pollinations_get_image_url"
    description: str = (
        "Genera la URL de una imagen de Pollinations.ai sin descargarla. "
        "Útil para obtener la URL y usarla en HTML, markdown, etc. "
        "Parámetros: prompt, model (flux, turbo, gptimage), width, height, seed, nologo, enhance."
    )

    def _run(
        self,
        prompt: str,
        model: str = "flux",
        width: int = 1024,
        height: int = 1024,
        seed: int = None,
        nologo: bool = True,
        enhance: bool = False,
    ) -> str:
        try:
            encoded_prompt = requests.utils.quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            
            params = {
                "model": model,
                "width": width,
                "height": height,
                "nologo": str(nologo).lower(),
                "enhance": str(enhance).lower(),
            }
            
            if seed is not None:
                params["seed"] = seed
            
            api_key = os.environ.get("POLLINATIONS_API_KEY")
            if api_key:
                params["key"] = api_key
            
            # Construir URL completa con parámetros
            param_str = "&".join(f"{k}={v}" for k, v in params.items())
            full_url = f"{url}?{param_str}"
            
            return json.dumps({
                "success": True,
                "image_url": full_url,
                "model": model,
                "width": width,
                "height": height,
                "prompt": prompt,
            }, ensure_ascii=False)
        
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
            }, ensure_ascii=False)


class PollinationsBatchGenerator(BaseTool):
    """Genera múltiples imágenes de una vez."""
    
    name: str = "pollinations_batch_generate"
    description: str = (
        "Genera múltiples imágenes con la misma configuración pero diferente seed. "
        "Parámetros: prompt, count (número de imágenes, default 4), model, width, height, "
        "nologo, enhance, save_path (carpeta donde guardar)."
    )

    def _run(
        self,
        prompt: str,
        count: int = 4,
        model: str = "flux",
        width: int = 1024,
        height: int = 1024,
        nologo: bool = True,
        enhance: bool = False,
        save_path: str = None,
    ) -> str:
        import random
        
        results = []
        base_seed = random.randint(1, 999999)
        
        for i in range(count):
            seed = base_seed + i
            generator = PollinationsImageGenerator()
            result = generator._run(
                prompt=prompt,
                model=model,
                width=width,
                height=height,
                seed=seed,
                nologo=nologo,
                enhance=enhance,
                save_path=save_path,
            )
            results.append(json.loads(result))
        
        successful = sum(1 for r in results if r.get("success"))
        
        return json.dumps({
            "success": successful > 0,
            "total_requested": count,
            "total_generated": successful,
            "results": results,
        }, ensure_ascii=False)


# Instancias globales para uso directo
pollinations_generate_image = PollinationsImageGenerator()
pollinations_get_image_url = PollinationsImageURL()
pollinations_batch_generate = PollinationsBatchGenerator()
