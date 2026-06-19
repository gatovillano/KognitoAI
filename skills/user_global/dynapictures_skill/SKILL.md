---
name: dynapictures-skill
description: |
  Generate dynamic images using predefined templates via the DynaPictures REST API.
  Supports single-page image generation, multi-page templates, PDF generation,
  batch processing, template management, workspace management, and media library operations.
  API key is configured securely via the DYNAPICTURES_API_KEY environment variable.
license: MIT
compatibility: Python 3.10+, requires async runtime
metadata:
  author: KognitoAI Team
  version: "1.0.0"
  category: image-generation
allowed-tools: |
  dynapictures
---

# DynaPictures Skill 🎨

## Short Description
Generate dynamic images using predefined templates via the DynaPictures REST API.

## Full Description
DynaPictures is an image generation platform that lets you create dynamic visuals using predefined templates. This skill provides a complete async client for the DynaPictures REST API, supporting:

- **Single-page image generation** — Customize text, images, colors, and styles in template layers
- **Multi-page templates** — Generate multiple images in one request
- **PDF generation** — Create multi-page PDFs from templates
- **Batch processing** — Generate multiple images in a single batch request
- **Template management** — List and inspect available templates
- **Workspace management** — Create, update, delete workspaces
- **Media library** — Upload, list, update, and delete assets

---

## 🔐 Secure API Key Configuration

**NEVER hardcode the API key in scripts or code.** Always use environment variables.

### Setup

Set the `DYNAPICTURES_API_KEY` environment variable:

```bash
# Linux / macOS
export DYNAPICTURES_API_KEY="your-api-key-here"
```

### Getting Your API Key
1. Sign up at [dynapictures.com](https://dynapictures.com)
2. Go to your account page or the API Console for a specific template
3. Copy your API key
4. Set it as the `DYNAPICTURES_API_KEY` environment variable

### Security Best Practices
- **Environment variables only** — Never commit API keys to code or repositories
- **Least privilege** — Use separate API keys for different environments
- **Rotation** — Rotate keys periodically
- **No logging** — The skill never logs or exposes the API key

---

## When to Use This Skill

**Use this skill when:**
- The user wants to generate images from DynaPictures templates
- You need to create dynamic visuals for social media, marketing, reports, etc.
- The user wants to manage templates, workspaces, or media assets
- Batch image generation is needed

**Do not use this skill if:**
- The user doesn't have a DynaPictures account or API key
- You need to create templates from scratch (use the DynaPictures web UI first)

---

## How to Use It

All operations go through the `dynapictures` tool with an `action` parameter.

### Actions Available

| Action | Description | Required Params |
|--------|-------------|-----------------|
| `generate_image` | Generate a single-page image | `template_uid`, `params` |
| `generate_multipage` | Generate multi-page images | `template_uid`, `pages` |
| `generate_pdf` | Generate a multi-page PDF | `template_uid`, `pages` |
| `delete_image` | Delete a generated image | `image_id` |
| `batch_generate` | Batch generate images | `template_uid`, `batch_params` |
| `list_templates` | List all templates | — |
| `get_template` | Get template details | `template_uid` |
| `list_workspaces` | List workspaces | — |
| `create_workspace` | Create a workspace | `workspace_name` |
| `update_workspace` | Update a workspace | `workspace_id`, `workspace_name` |
| `delete_workspace` | Delete a workspace | `workspace_id` |
| `list_assets` | List media assets | — |
| `upload_image` | Upload image to library | `image_url` |
| `load_asset` | Load a specific asset | `asset_id` |
| `update_asset` | Update an asset | `asset_id`, `asset_name` |
| `delete_asset` | Delete an asset | `asset_id` |

### 1. Generate a Single-Page Image

Params format — each object in the `params` array represents a layer to customize:

```json
{
  "action": "generate_image",
  "template_uid": "debcaw6f99",
  "params": [
    {"name": "title", "text": "Hello World!", "color": "#333"},
    {"name": "image1", "imageUrl": "https://example.com/photo.jpg", "imagePosition": "cover"}
  ],
  "format": "png",
  "metadata": "optional custom data"
}
```

Response:
```json
{
  "id": "c13bd141c7",
  "templateId": "debcaw6f99",
  "imageUrl": "https://api.dynapictures.com/images/xxx/yyy.png",
  "thumbnailUrl": "...",
  "retinaThumbnailUrl": "...",
  "width": 1000,
  "height": 1500
}
```

### 2. Generate Multi-Page Images

```json
{
  "action": "generate_multipage",
  "template_uid": "b394d5f371",
  "pages": [
    {"index": 0, "layers": [{"name": "text1", "text": "Page 1"}]},
    {"index": 1, "layers": [{"name": "text1", "text": "Page 2"}]}
  ],
  "format": "jpeg"
}
```

### 3. Generate a PDF

```json
{
  "action": "generate_pdf",
  "template_uid": "b394d5f371",
  "pages": [
    {"index": 0, "layers": [{"name": "title", "text": "My Report"}]}
  ]
}
```

### 4. List Templates

```json
{"action": "list_templates"}
```

### 5. Batch Generate

```json
{
  "action": "batch_generate",
  "template_uid": "debcaw6f99",
  "batch_params": [
    [{"name": "title", "text": "Image 1"}],
    [{"name": "title", "text": "Image 2"}]
  ],
  "format": "png"
}
```

---

## Layer Parameter Reference

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | String | **Required.** Layer name from template |
| `text` | String | Text content for text layers |
| `color` | String | Text color (`#000000`, `rgb(0,0,0)`) |
| `backgroundColor` | String | Background color |
| `borderColor` | String | Border color |
| `borderWidth` | String | Border width (e.g. `1px`) |
| `borderRadius` | String | Border radius (e.g. `5px`, `50%`) |
| `imageUrl` | String | Image URL for image layers |
| `imagePosition` | String | `crop`, `ai_face`, `cover`, `align` |
| `imageAlignH` | String | `left`, `center`, `right`, `full` |
| `imageAlignV` | String | `top`, `center`, `bottom`, `full` |
| `imageEffect` | String | CSS filter (`grayscale(100%)`, `blur(4px)`, etc.) |
| `opacity` | Number | Transparency (0=hidden, 1=visible) |
| `chartColor` | String | Chart bar/line color |
| `chartLabelColor` | String | Chart label color |
| `chartDataLabels` | Array | X-axis labels |
| `chartDataValues` | Array | Y-axis data values |

### Output Formats
- `png` (default), `jpeg`, `webp`, `avif`, `pdf`

---

## Error Handling

- **Missing API key**: "Configuration Error: DynaPictures API key is required..."
- **HTTP errors**: "HTTP Error 401: Unauthorized" / "HTTP Error 404: Not Found"
- **Missing parameters**: "Error: template_uid and params are required..."
- **Network errors**: "Request Error: Connection refused..."

---

## Technical Specifications

- **Base URL**: `https://api.dynapictures.com`
- **Authentication**: Bearer token in `Authorization` header
- **Timeout**: 60 seconds per request
- **Async**: Uses `httpx.AsyncClient`
- **Response format**: JSON

---

## Troubleshooting

| Error | Solution |
|-------|----------|
| "API key is required" | Set `DYNAPICTURES_API_KEY` env var |
| "HTTP Error 401" | Invalid/expired API key |
| "HTTP Error 429" | Rate limit — wait and retry |
| "HTTP Error 404" | Verify template_uid or image_id |
