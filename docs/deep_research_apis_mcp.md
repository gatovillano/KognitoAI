# 🌐 APIs Externas y Servidores MCP en Open Deep Research

## 📋 Resumen Ejecutivo

Open Deep Research utiliza **2 tipos de integraciones externas**:

1. **APIs de Búsqueda Web** - Para recopilar información
2. **Servidores MCP (Model Context Protocol)** - Para herramientas externas dinámicas

---

## 🔍 1. APIs de Búsqueda Web

### **Tavily Search API** (Principal) ⭐

**¿Qué es?**

- API de búsqueda optimizada para IA
- Diseñada específicamente para agentes de IA
- Proporciona resultados estructurados y contenido completo de páginas web

**Uso en Open Deep Research:**

```python
from tavily import AsyncTavilyClient

tavily_client = AsyncTavilyClient(api_key=settings.tavily_api_key)
results = await tavily_client.search(
    query="tu consulta",
    max_results=5,
    include_raw_content=True,  # Incluye contenido completo de páginas
    topic="general"  # Opciones: general, news, finance
)
```

**Características:**

- ✅ Búsqueda paralela de múltiples queries
- ✅ Extracción automática de contenido web
- ✅ Filtrado por tópico (general, noticias, finanzas)
- ✅ Resultados optimizados para LLMs

**Configuración requerida:**

```bash
# .env
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxx
```

**Costo:**

- Plan gratuito: 1,000 búsquedas/mes
- Plan Pro: $49/mes - 10,000 búsquedas
- Más info: <https://tavily.com/pricing>

---

### **OpenAI Native Web Search** (Alternativa)

**¿Qué es?**

- Búsqueda web integrada en modelos de OpenAI
- Disponible en GPT-4 y modelos superiores
- No requiere API adicional

**Uso:**

```python
# Se activa automáticamente cuando el modelo lo necesita
# No requiere código adicional
```

**Configuración:**

```python
config = {
    "search_api": "openai",
    "research_model": "openai:gpt-4"
}
```

**Ventajas:**

- ✅ Sin API adicional
- ✅ Integrado en el modelo
- ✅ Sin límites separados

**Desventajas:**

- ❌ Solo disponible en modelos OpenAI específicos
- ❌ Menos control sobre resultados
- ❌ Más costoso (incluido en tokens del modelo)

---

### **Anthropic Native Web Search** (Alternativa)

**¿Qué es?**

- Búsqueda web integrada en modelos Claude
- Similar a OpenAI Native Search

**Uso:**

```python
config = {
    "search_api": "anthropic",
    "research_model": "anthropic:claude-3-opus"
}
```

**Estado actual:**

- ⚠️ En beta
- ⚠️ Disponibilidad limitada

---

## 🔌 2. Servidores MCP (Model Context Protocol)

### **¿Qué es MCP?**

**Model Context Protocol** es un protocolo estándar para conectar **herramientas externas** a agentes de IA de forma dinámica.

**Analogía:**

- MCP es como un "USB" para herramientas de IA
- Permite conectar servicios externos sin modificar código
- Las herramientas se cargan dinámicamente en tiempo de ejecución

---

### **Arquitectura MCP en Open Deep Research**

```
┌─────────────────────────────────────┐
│   Open Deep Research Agent          │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   MultiServerMCPClient              │
│   (langchain-mcp-adapters)          │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   Servidor MCP Externo              │
│   (HTTP/WebSocket)                  │
└──────────────┬──────────────────────┘
               │
       ┌───────┼───────┐
       ▼       ▼       ▼
   ┌─────┐ ┌─────┐ ┌─────┐
   │Tool1│ │Tool2│ │ToolN│
   └─────┘ └─────┘ └─────┘
```

---

### **Configuración de Servidores MCP**

**Formato de configuración:**

```python
from external_agents.open_deep_research.src.open_deep_research.configuration import MCPConfig

mcp_config = MCPConfig(
    url="https://mcp-server.example.com",  # URL del servidor MCP
    tools=["database_query", "api_fetch"],  # Herramientas a cargar
    auth_required=True                      # Si requiere autenticación
)
```

**Ejemplo de uso:**

```python
config = {
    "configurable": {
        "mcp_config": {
            "url": "https://your-mcp-server.com",
            "tools": ["tool1", "tool2", "tool3"],
            "auth_required": True
        }
    }
}
```

---

### **Autenticación MCP**

Open Deep Research soporta **OAuth 2.0 Token Exchange** para autenticación:

```python
# Flujo de autenticación
1. Usuario tiene token de Supabase
2. Se intercambia por token MCP
3. Token MCP se usa para llamadas a herramientas

# Implementación
async def get_mcp_access_token(supabase_token, base_mcp_url):
    form_data = {
        "client_id": "mcp_default",
        "subject_token": supabase_token,
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "resource": base_mcp_url + "/mcp",
        "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
    }
    
    response = await session.post(
        base_mcp_url + "/oauth/token",
        data=form_data
    )
    return response.json()
```

---

### **Ejemplos de Servidores MCP**

**1. Servidor de Base de Datos**

```python
mcp_config = MCPConfig(
    url="https://db-mcp.example.com",
    tools=["query_database", "insert_record", "update_record"],
    auth_required=True
)

# El agente puede usar:
# - query_database(sql="SELECT * FROM users")
# - insert_record(table="users", data={...})
```

**2. Servidor de APIs Externas**

```python
mcp_config = MCPConfig(
    url="https://api-mcp.example.com",
    tools=["fetch_weather", "get_stock_price", "translate_text"],
    auth_required=False
)

# El agente puede usar:
# - fetch_weather(city="Buenos Aires")
# - get_stock_price(symbol="AAPL")
```

**3. Servidor de Archivos**

```python
mcp_config = MCPConfig(
    url="https://files-mcp.example.com",
    tools=["read_file", "write_file", "list_directory"],
    auth_required=True
)

# El agente puede usar:
# - read_file(path="/docs/report.pdf")
# - write_file(path="/output/result.txt", content="...")
```

---

### **Cómo funciona la carga de herramientas MCP**

```python
async def load_mcp_tools(config, existing_tool_names):
    # 1. Validar configuración
    if not mcp_config.url or not mcp_config.tools:
        return []
    
    # 2. Autenticar si es necesario
    if mcp_config.auth_required:
        mcp_tokens = await fetch_tokens(config)
        auth_headers = {"Authorization": f"Bearer {mcp_tokens['access_token']}"}
    
    # 3. Conectar al servidor MCP
    client = MultiServerMCPClient({
        "server_1": {
            "url": mcp_config.url + "/mcp",
            "headers": auth_headers,
            "transport": "streamable_http"
        }
    })
    
    # 4. Obtener herramientas disponibles
    available_tools = await client.get_tools()
    
    # 5. Filtrar solo las herramientas solicitadas
    configured_tools = [
        tool for tool in available_tools
        if tool.name in mcp_config.tools
    ]
    
    # 6. Envolver con manejo de errores
    return [wrap_mcp_authenticate_tool(tool) for tool in configured_tools]
```

---

## 🔑 Configuración Completa en Kognito AI

### **Variables de entorno necesarias:**

```bash
# === APIs de Búsqueda ===
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxx

# === Configuración de LLM (para búsqueda nativa) ===
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxx
GOOGLE_API_KEY=AIzaSy-xxxxxxxx  # Para Gemini

# === MCP (Opcional) ===
# Si usas servidores MCP, configura según tu servidor
MCP_SERVER_URL=https://your-mcp-server.com
SUPABASE_ACCESS_TOKEN=xxx  # Para autenticación MCP
```

---

## 📊 Comparación de APIs de Búsqueda

| Característica | Tavily | OpenAI Native | Anthropic Native |
|---------------|--------|---------------|------------------|
| **API Separada** | ✅ Sí | ❌ No | ❌ No |
| **Control de resultados** | ✅ Alto | ⚠️ Medio | ⚠️ Medio |
| **Contenido completo** | ✅ Sí | ⚠️ Limitado | ⚠️ Limitado |
| **Costo** | 💰 Bajo | 💰💰 Alto | 💰💰 Alto |
| **Configuración** | 🔧 Simple | 🔧 Muy simple | 🔧 Muy simple |
| **Disponibilidad** | ✅ General | ⚠️ Solo OpenAI | ⚠️ Beta |
| **Recomendado para** | Producción | Prototipado | Experimental |

---

## 🎯 Recomendaciones

### **Para Kognito AI:**

1. **Usar Tavily como principal** ✅
   - Mejor control
   - Más económico
   - Resultados optimizados para IA

2. **MCP como opcional** ⚠️
   - Solo si necesitas herramientas externas específicas
   - Requiere infraestructura adicional
   - Útil para integraciones empresariales

3. **Búsqueda nativa como fallback** 🔄
   - Si Tavily falla
   - Para pruebas rápidas

---

## 🚀 Configuración Recomendada para Kognito

```python
# tools/deep_research_tool_litellm.py

config = {
    "configurable": {
        # Búsqueda: Usar Tavily
        "search_api": "tavily",
        "tavily_api_key": settings.tavily_api_key,
        
        # MCP: Deshabilitado por defecto (opcional)
        "mcp_config": None,  # O configurar si tienes servidor MCP
        
        # Modelos: Usar LiteLLM de Kognito
        "research_model": "anthropic:claude-3.5-sonnet",
        "compression_model": "openai:gpt-4o-mini",
    }
}
```

---

## 📚 Recursos Adicionales

### **Tavily:**

- Documentación: <https://docs.tavily.com>
- Pricing: <https://tavily.com/pricing>
- API Reference: <https://docs.tavily.com/api-reference>

### **MCP (Model Context Protocol):**

- Especificación: <https://modelcontextprotocol.io>
- Ejemplos de servidores: <https://github.com/modelcontextprotocol>
- LangChain MCP Adapters: <https://github.com/langchain-ai/langchain-mcp-adapters>

### **Búsqueda Nativa:**

- OpenAI: <https://platform.openai.com/docs/guides/web-search>
- Anthropic: <https://docs.anthropic.com/claude/docs/web-search>

---

## ⚠️ Notas Importantes

1. **Tavily API Key es REQUERIDA** para usar Open Deep Research con búsqueda web
2. **MCP es OPCIONAL** - Solo necesario si quieres herramientas externas
3. **Búsqueda nativa** requiere modelos específicos (GPT-4+, Claude 3+)
4. **Costos** pueden acumularse rápidamente con investigaciones profundas
5. **Rate limits** de las APIs pueden afectar investigaciones con muchas unidades concurrentes

---

## 🔧 Troubleshooting

### **Error: "Tavily API key not found"**

```bash
# Solución: Añadir a .env
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxx
```

### **Error: "MCP server connection failed"**

```python
# Solución: Verificar configuración MCP
# O deshabilitar MCP si no lo necesitas
config["mcp_config"] = None
```

### **Error: "Rate limit exceeded"**

```python
# Solución: Reducir unidades concurrentes
config["max_concurrent_research_units"] = 2  # Reducido de 5
```
