# 🔬 KognitoAI Deep Research MCP Server

Servidor de **Model Context Protocol (MCP)** dedicado exclusivamente a las capacidades de **Deep Research** (`api/deep_research.py`) de KognitoAI. 

Permite a cualquier agente o cliente compatible con MCP (**Claude Desktop**, **Cursor**, **Antigravity**, **Windsurf**, **Cline**, etc.) realizar investigaciones exhaustivas, multi-etapa y con verificación cruzada de fuentes en la web.

---

## 🛠️ Herramientas Expuestas (Tools)

| Herramienta | Tipo | Parámetros Clave | Descripción |
| :--- | :--- | :--- | :--- |
| `deep_research` | Síncrona | `query` (req), `llm_model`, `llm_provider`, `fast_llm_model`, `api_key`, `temperature`, `account_id`, `workspace_id` | Ejecuta una investigación profunda completa sobre un tema y retorna el informe final con resumen, hallazgos, recomendaciones y fuentes. Usa automáticamente el LLM configurado del cliente o el modelo especificado en la llamada. Si el agente requiere orientación, devuelve un estado `clarification_needed`. |
| `start_deep_research` | Asíncrona | `query` (req), `llm_model`, `llm_provider`, `fast_llm_model`, `api_key`, `temperature`, `account_id`, `workspace_id` | Inicia la investigación en segundo plano con el LLM del cliente y devuelve de inmediato un `run_id`. Ideal para clientes con tiempos de espera limitados (*timeouts*). |
| `check_deep_research_status` | Consulta | `run_id` (req) | Consulta el progreso (0-100%), mensajes de avance y obtiene el reporte final de un `run_id`. |
| `deep_research_clarify` | Interacción | `run_id` (req), `user_response` (req), `account_id` | Responde a una pregunta de clarificación solicitada por el agente de investigación para reanudar el proceso. |
| `export_deep_research_pdf` | Exportación | `title` (req), `final_report` (req), `sources`, `recommendations`, `workspace_id` | Compila el informe de investigación 1:1 en un documento PDF profesional y lo guarda en el almacenamiento de documentos del usuario. |

---

## 🤖 Uso del LLM del Cliente

El servidor MCP y la API de Deep Research adaptan automáticamente el modelo LLM a utilizar:
1. **Modelo personalizado por llamada**: Puedes especificar directamente `llm_model` (ej. `"openai/gpt-4o"`, `"anthropic/claude-3.5-sonnet"`, `"gemini-2.5-flash"`), `llm_provider` y `api_key` en los argumentos de la herramienta.
2. **Modelo configurado por el usuario**: Si no se especifican parámetros directos, el sistema carga automáticamente la configuración del usuario cliente (`Account.llm_model`, `Account.fast_llm_model`, proveedor y temperatura) de la base de datos de KognitoAI.
3. **Mapeo transparente de `api_user`**: Las llamadas que antes usaban `"api_user"` y caían al modelo global del administrador ahora resuelven automáticamente la cuenta del cliente activo.

---

## 📚 Recursos (Resources)

- `deep-research://status`: Estado de salud del motor de Deep Research, cuenta activa y herramientas cargadas.
- `deep-research://jobs`: Resumen en tiempo real de los trabajos de investigación activos y recientes.

---

## 💡 Prompts

- `deep-research-analyst`: Plantilla estructurada para guiar a los agentes externos a formular investigaciones rigurosas y exhaustivas sobre un tema dado.

---

## ⚙️ Configuración para Clientes MCP

### 1. Claude Desktop (`claude_desktop_config.json`)
Ruta en Linux: `~/.config/Claude/claude_desktop_config.json`  
Ruta en Windows: `%APPDATA%\Claude\claude_desktop_config.json`  
Ruta en macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "kognito-deep-research": {
      "command": "/home/gato/Proyectos/KognitoAI/run_deep_research_mcp.sh",
      "env": {
        "KOGNITO_ACCOUNT_ID": "5b8d59b0-69b7-4aa8-9bb0-bf07511222a6"
      }
    }
  }
}
```

O llamando directamente al entorno Python virtual:

```json
{
  "mcpServers": {
    "kognito-deep-research": {
      "command": "/home/gato/Proyectos/KognitoAI/venv_host/bin/python3",
      "args": ["-m", "mcp_deep_research"],
      "cwd": "/home/gato/Proyectos/KognitoAI",
      "env": {
        "KOGNITO_ACCOUNT_ID": "5b8d59b0-69b7-4aa8-9bb0-bf07511222a6"
      }
    }
  }
}
```

### 2. Cursor (`.cursor/mcp.json` o configuración de MCP en Cursor Settings)

```json
{
  "mcpServers": {
    "kognito-deep-research": {
      "command": "/home/gato/Proyectos/KognitoAI/run_deep_research_mcp.sh"
    }
  }
}
```

### 3. Antigravity / Gemini CLI

Puedes registrarlo en la configuración MCP de Antigravity:

```json
{
  "mcpServers": {
    "deep-research": {
      "command": "/home/gato/Proyectos/KognitoAI/run_deep_research_mcp.sh"
    }
  }
}
```

### 4. Modo de Red SSE (Server-Sent Events)

Si tienes agentes remotos o deseas ejecutar el servidor MCP a través de la red HTTP:

```bash
./run_deep_research_mcp.sh --transport sse --host 0.0.0.0 --port 8000
```

Y conectar clientes MCP a la URL SSE:
`http://localhost:8000/sse`

---

## 🧪 Validación y Pruebas

Para comprobar que el servidor se inicia e interactúa correctamente:

```bash
./run_deep_research_mcp.sh
```

El servidor utiliza el transporte estándar **stdio** (JSON-RPC 2.0). Todos los logs de diagnóstico se dirigen a `stderr` para asegurar que el canal de datos `stdout` permanezca estrictamente conforme a la especificación de MCP.
