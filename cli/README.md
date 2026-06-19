# KognitoAI CLI

> CLI moderno con interfaz TUI corporativa para **KognitoAI** — chats sincronizados, editor de documentos Word/PDF y editor de código.

---

## Características

| Función | Descripción |
|---|---|
| 💬 **Chat TUI** | Conversaciones sincronizadas con el frontend web (plataforma `cli`) |
| 📝 **Editor de documentos** | Crea y edita Markdown, exporta a **Word (.docx)** o **PDF** con estilos corporativos |
| 💻 **Editor de código** | Escribe, revisa con IA y exporta código fuente a PDF |
| 🤖 **IA integrada** | Mejora documentos y revisa código directamente desde el TUI |
| 📁 **Workspace local** | Trabaja en la carpeta actual como workspace de archivos |
| 🌐 **Sincronización** | Los chats creados aparecen en el frontend web automáticamente |

---

## Instalación de dependencias

```bash
# Las dependencias principales ya están en requirements.txt:
# textual, rich, click, python-docx, reportlab

# Instalar dependencias adicionales si faltan:
pip install textual rich click python-docx reportlab
```

---

## Uso

### TUI interactivo (recomendado)

```bash
# Lanzar la interfaz TUI completa
python -m cli

# o equivalente
python -m cli tui
```

### Comandos headless

```bash
# Login
python -m cli login --url http://localhost:8000

# Estado de la sesión
python -m cli status

# Enviar mensaje directo
python -m cli chat "¿Qué es un LLM?"

# Exportar Markdown a PDF corporativo
python -m cli doc export mi_documento.md --format pdf --title "Informe Q2"

# Crear nuevo documento (con IA)
python -m cli doc new --title "Propuesta Comercial" --ai

# Configurar workspace
python -m cli config --workspace <WORKSPACE_ID>
```

---

## Estructura

```
cli/
├── main.py              # Punto de entrada Click (comandos)
├── core/
│   ├── api_client.py    # Cliente HTTP para KognitoAI API
│   └── config.py        # Configuración persistente (~/.kognitocli/config.json)
├── ui/
│   ├── tui_app.py       # Aplicación Textual TUI principal
│   └── app.tcss         # Estilos corporativos (dark theme)
└── modules/
    └── doc_editor.py    # Exportación Word/PDF con estilos corporativos
```

---

## Atajos de teclado (en TUI)

| Tecla | Acción |
|---|---|
| `Ctrl+N` | Nuevo chat |
| `Ctrl+D` | Ir a editor de documentos |
| `Ctrl+K` | Ir a editor de código |
| `Ctrl+E` | Exportar documento actual |
| `Ctrl+L` | Toggle sidebar |
| `Ctrl+Q` | Salir |
| `Enter` | Enviar mensaje |

---

## Sincronización con el frontend web

Los chats creados desde el CLI se guardan con `platform: "cli"` en la base de datos.
Aparecen automáticamente en el sidebar del frontend web junto a los chats normales.
