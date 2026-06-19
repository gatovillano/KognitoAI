---
name: pollinations-images
description: |
  Generación de imágenes usando la API gratuita de Pollinations.ai.
  Soporta generación individual, batch, y obtención de URLs sin descargar.
  No requiere API key para uso básico (con rate limit).
license: MIT
compatibility: Python 3.10+, requests
metadata:
  author: KognitoAI Team
  version: "1.0.0"
  category: image-generation
allowed-tools: |
  pollinations_generate_image
  pollinations_get_image_url
  pollinations_batch_generate
---

# Pollinations Images Skill 🌸

## Short Description
Genera imágenes usando la API gratuita de Pollinations.ai. Sin login, sin costo, resultados instantáneos.

## Full Description
Pollinations.ai es una plataforma open-source de generación de IA con sede en Berlín. Ofrece generación de imágenes, texto, audio y video a través de APIs gratuitas. Esta skill permite generar imágenes de alta calidad desde descripciones de texto (prompts) usando modelos como Flux, GPT Image, Turbo y más.

**Ventajas:**
- ✅ No requiere login para uso básico
- ✅ No requiere API key (aunque una key aumenta el rate limit)
- ✅ Múltiples modelos disponibles (Flux, Turbo, GPT Image, etc.)
- ✅ Soporta batch generation
- ✅ URLs directas para usar en HTML/Markdown

---

## When to Use This Skill

**Usa esta skill cuando:**
- El usuario pida generar una imagen desde texto
- Necesites imágenes para presentaciones, marketing, contenido
- Quieras crear variaciones de una imagen (batch)
- Necesites la URL de una imagen para incrustar en HTML/Markdown

**No uses esta skill si:**
- Necesitas imágenes con derechos de autor garantizados
- Requieres consistencia absoluta de marca
- Necesitas generar imágenes NSFW (los filtros de seguridad están activos)

---

## Available Tools

### 1. `pollinations_generate_image`
Genera y descarga una imagen. Retorna la ruta local donde se guardó.

**Parámetros:**
| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `prompt` | str | **requerido** | Descripción de la imagen |
| `model` | str | `flux` | Modelo: `flux`, `turbo`, `gptimage`, `midijourney` |
| `width` | int | `1024` | Ancho en píxeles |
| `height` | int | `1024` | Alto en píxeles |
| `seed` | int | `None` | Semilla para reproducibilidad |
| `nologo` | bool | `True` | Quitar marca de agua |
| `enhance` | bool | `False` | Mejorar prompt con IA |
| `save_path` | str | `None` | Carpeta destino (default: `/tmp/pollinations_images/`) |

### 2. `pollinations_get_image_url`
Solo retorna la URL de la imagen sin descargarla. Ideal para HTML/Markdown.

**Parámetros:** Mismos que arriba (excepto `save_path`).

### 3. `pollinations_batch_generate`
Genera múltiples imágenes con seeds diferentes.

**Parámetros adicionales:**
| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `count` | int | `4` | Número de imágenes a generar |

---

## Modelos Disponibles

| Modelo | Estilo | Velocidad | Calidad |
|--------|--------|-----------|---------|
| `flux` | Generalista, artístico | Media | ⭐⭐⭐⭐⭐ |
| `turbo` | Rápido, bueno para iterar | Muy rápida | ⭐⭐⭐⭐ |
| `gptimage` | Estilo DALL-E | Media | ⭐⭐⭐⭐ |
| `midijourney` | Estilo Midjourney | Lenta | ⭐⭐⭐⭐⭐ |

---

## Ejemplos de Uso

### Generar una imagen simple
```python
result = pollinations_generate_image._run(
    prompt="A futuristic cyberpunk city at night with neon lights and flying cars",
    model="flux",
    width=1024,
    height=1024
)
```

### Generar en batch (variaciones)
```python
result = pollinations_batch_generate._run(
    prompt="A serene Japanese garden with cherry blossoms and a koi pond",
    count=4,
    model="flux",
    save_path="/home/gato/imagenes/"
)
```

### Obtener solo la URL
```python
result = pollinations_get_image_url._run(
    prompt="A golden retriever puppy playing in a meadow",
    model="turbo"
)
```

### Imagen con seed fijo (reproducible)
```python
result = pollinations_generate_image._run(
    prompt="A mystical forest with glowing mushrooms",
    model="flux",
    seed=42,
    nologo=True,
    enhance=True
)
```

---

## API Reference

### Endpoints
- **Imagen:** `GET https://image.pollinations.ai/prompt/{prompt}`
- **Unificado:** `GET https://gen.pollinations.ai/image/{prompt}`

### Parámetros URL
- `model`: Nombre del modelo
- `width`: Ancho (px)
- `height`: Alto (px)
- `seed`: Semilla numérica
- `nologo`: `true`/`false`
- `enhance`: `true`/`false`
- `key`: API key (opcional)

### cURL Example
```bash
curl 'https://image.pollinations.ai/prompt/a%20beautiful%20sunset?model=flux&width=1024&height=1024&nologo=true' -o imagen.png
```

---

## Configuración de API Key (Opcional)

Para mayor rate limit y features premium:

```bash
export POLLINATIONS_API_KEY="tu-api-key"
```

Obtén tu key en: https://enter.pollinations.ai

---

## Rate Limits

| Plan | Límite |
|------|--------|
| Sin key | ~5 requests/min |
| Con key | ~30 requests/min |
| Pollen credits | Ilimitado ($1 ≈ 1 Pollen) |

---

## Troubleshooting

| Error | Solución |
|-------|----------|
| `429 Too Many Requests` | Espera 30-60 segundos y reintenta |
| `Timeout` | Reduce el tamaño de imagen o usa modelo `turbo` |
| Imagen no generada | Revisa el prompt, evita contenido bloqueado |
| Calidad baja | Usa `model=flux` o activa `enhance=True` |

---

## Notas Técnicas

- Las imágenes generadas se guardan por defecto en `/tmp/pollinations_images/`
- El formato de salida es PNG o JPEG según el modelo
- Los seeds permiten reproducir exactamente la misma imagen
- El parámetro `enhance` usa un modelo de texto para mejorar el prompt automáticamente
