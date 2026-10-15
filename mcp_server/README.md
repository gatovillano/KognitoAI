# 🚀 KognitoAI Model Context Protocol (MCP) Server

Este servidor implementa el protocolo estándar **Model Context Protocol (MCP)** para exponer la infraestructura, habilidades, memoria y herramientas de **KognitoAI** a agentes externos (tales como **Claude Desktop**, **Cursor**, **Windsurf**, **Antigravity**, **Cline**, etc.).

---

## 🧰 Capacidades Expuestas

1. **Herramientas de KognitoAI (+100 herramientas nativas y personalizadas):**
   - **Búsqueda & Web:** `web_search`, `ddg_search_tool`, `deep_research`, `comprehensive_web_analyzer`.
   - **Gestión del Conocimiento & Grafos:** `knowledge_search`, `query_memory_graph`, `knowledge_graph`, `anthropological_graph_processing`.
   - **Documentos & Productividad:** `create_onlyoffice_document`, `create_pdf_tool`, `get_document_content_tool`, `notes_skill`, `calendar_skill`, `manage_tasks`.
   - **Desarrollo & Sistema:** `terminal_executor`, `local_file_navigator`, `github_repository_explorer`.
   - **Generación & Medios:** `generate_image_tool`, `pollinations_generate_image`, `html_generator`, `mindmap_generator`.
   - **Ecosistema Social de Agentes:** `moltbook_feed`, `moltbook_publish`, `moltbook_interact`, `moltbook_account`.
   - **Orquestación KAI (`kai_chat`):** Invocación directa del agente autónomo de KAI con razonamiento LangGraph y memoria contextual.

2. **Recursos MCP (`resources`):**
   - `kognito://system/status`: Estado operativo, ID de cuenta activa y recuento de herramientas.
   - `kognito://account/info`: Detalles del perfil, correo electrónico y configuración de la cuenta.

3. **Prompts MCP (`prompts`):**
   - `kognito-research-assistant`: Template pre-configurado para análisis e investigación cualitativa conectada a la base de conocimiento.

---

## ⚙️ Configuración para Clientes MCP

### 1. Claude Desktop (`claude_desktop_config.json`)
Ruta: `~/.config/Claude/claude_desktop_config.json` o `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "kognito-ai": {
      "command": "/home/gato/Proyectos/KognitoAI/kognito-ai/venv_host/bin/python3",
      "args": [
        "-m",
        "mcp_server"
      ],
      "cwd": "/home/gato/Proyectos/KognitoAI/kognito-ai",
      "env": {
        "KOGNITO_ACCOUNT_ID": "5b8d59b0-69b7-4aa8-9bb0-bf07511222a6"
      }
    }
  }
}
```

### 2. Cursor (`.cursor/mcp.json`) o Windsurf / Cline
```json
{
  "mcpServers": {
    "kognito-ai": {
      "command": "/home/gato/Proyectos/KognitoAI/kognito-ai/mcp_server/run.sh"
    }
  }
}
```

---

## 💻 Ejecución Manual / Pruebas

Para validar el funcionamiento del servidor:

```bash
cd /home/gato/Proyectos/KognitoAI/kognito-ai
./mcp_server/run.sh
```

El servidor utiliza el transporte estándar **stdio** (JSON-RPC 2.0). Todo el registro de logs y depuración se canaliza a `stderr` para garantizar que la comunicación de datos en `stdout` permanezca limpia y conforme a la especificación oficial de MCP.
