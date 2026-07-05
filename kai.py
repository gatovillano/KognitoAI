#!/usr/bin/env python3
import asyncio
import json
import os
import sys
import uuid
import tty
import select
import subprocess
import termios
import pty
import queue
import re
from pathlib import Path
from typing import Optional, Dict, Any, Generator, List, Union
from datetime import datetime, timedelta

import click
import httpx
import websockets
from rich.console import Console, Group, RenderableType
from rich.markdown import Markdown
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.theme import Theme
from rich.layout import Layout
from rich.status import Status
from rich.columns import Columns
from rich.box import ROUNDED, DOUBLE_EDGE, HEAVY
from rich.spinner import Spinner
from rich.table import Table
from rich.padding import Padding

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style as PromptStyle
from prompt_toolkit.formatted_text import HTML

# Importar el ejecutor compartido
try:
    from core.command_executor import CommandExecutor
except ImportError:
    class CommandExecutor:
        def execute(self, command, **kwargs):
            yield f"Error: No se pudo importar CommandExecutor de core."

# --- CONFIGURACIÓN DE ESTÉTICA ---
KOGNITO_THEME = Theme({
    "info": "bold cyan",
    "warning": "bold yellow",
    "error": "bold red",
    "success": "bold green",
    "kai": "bold magenta",
    "user": "bold dodger_blue1",
    "cmd": "bold spring_green3",
    "system": "dim white",
    "timestamp": "dim grey62",
    "border.kai": "magenta",
    "border.user": "dodger_blue1",
    "border.confirm": "bright_yellow",
    "tool": "italic yellow",
    "metacmd": "bold underline cyan",
})

console = Console(theme=KOGNITO_THEME)

pt_style = PromptStyle.from_dict({
    'prompt': 'bold #1e90ff',
    'command': 'italic #32cd32',
    'bottom-toolbar': 'bg:#333333 #ffffff',
})

# --- CONFIGURACIÓN DE RUTAS ---
CONFIG_DIR = Path.home() / ".kognito"
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_FILE = CONFIG_DIR / "history.txt"
DEFAULT_API_URL = "http://localhost:8889"

CONFIG_DIR.mkdir(exist_ok=True)

def load_config() -> Dict[str, Any]:
    if CONFIG_FILE.exists():
        try: return json.loads(CONFIG_FILE.read_text())
        except Exception: return {}
    return {}

def save_config(config: Dict[str, Any]):
    CONFIG_FILE.write_text(json.dumps(config, indent=2))

def get_api_url() -> str: return load_config().get("api_url", DEFAULT_API_URL)
def get_token() -> Optional[str]: return load_config().get("token")
def get_account_id() -> Optional[str]:
    token = get_token()
    if not token: return None
    try:
        import jwt
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload.get("sub")
    except Exception: return None

# --- LÓGICA DE SEGURIDAD ---
DANGEROUS_PATTERNS = [r"\brm\b", r"\bdelete\b", r"\bdrop\b", r"\btruncate\b", r"\bunlink\b", r"\b-rf\b"]
def is_dangerous_command(command: str) -> bool:
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE): return True
    return False

# --- COMPONENTES DE UI ---
def print_banner():
    try:
        from utils.ascii_logo import get_kognito_logo
        console.print(get_kognito_logo())
    except ImportError:
        console.print(Panel("[bold magenta]🧠 KOGNITO AI[/bold magenta]\n[dim]Terminal Interface v1.7[/dim]", border_style="magenta", box=DOUBLE_EDGE))

def create_message_panel(content: str, sender: str = "kai", current_tool: str = None) -> Union[Panel, Padding]:
    timestamp = datetime.now().strftime("%H:%M")
    if sender == "kai":
        tool_info = f" [tool]({current_tool})[/tool]" if current_tool else ""
        title = f"[kai]🤖 KAI[/kai]{tool_info} [timestamp]{timestamp}[/timestamp]"
        border = "magenta"
        renderable = Markdown(content)
        # Añadimos margen considerable (Padding) para los mensajes de KAI
        panel = Panel(renderable, title=title, title_align="left", border_style=border, box=ROUNDED, padding=(1, 4))
        return Padding(panel, (1, 6, 1, 2)) # Margen: Arriba 1, Derecha 6, Abajo 1, Izquierda 2
    
    elif sender == "user":
        title = f"[user]👤 TÚ[/user] [timestamp]{timestamp}[/timestamp]"
        border = "dodger_blue1"
        renderable = Text(content)
        panel = Panel(renderable, title=title, title_align="right", border_style=border, box=ROUNDED, padding=(1, 2))
        return Padding(panel, (1, 2, 1, 6)) # Margen invertido para el usuario
    
    else:
        title = f"[system]⚙️ SISTEMA[/system]"
        border = "white"
        renderable = Text(content, style="dim")
        return Panel(renderable, title=title, title_align="left", border_style=border, box=ROUNDED, padding=(0, 2))

async def confirm_action(session: PromptSession, command: str, explanation: str = "") -> bool:
    is_danger = is_dangerous_command(command)
    title = "🚨 [bold red]¡ALERTA DE ELIMINACIÓN![/bold red]" if is_danger else "⚠️ [bold yellow]CONFIRMACIÓN REQUERIDA[/bold yellow]"
    content = Group(Text("Acción solicitada:", style="bold white"), Panel(f"[cmd]{command}[/cmd]", border_style="spring_green3", box=ROUNDED), Text(f"\nExplicación: {explanation}" if explanation else "", style="italic grey70"))
    console.print("\n")
    console.print(Panel(content, title=title, border_style="red" if is_danger else "bright_yellow", box=HEAVY, padding=(1, 2)))
    while True:
        answer = await session.prompt_async(HTML('<b>¿Confirmar ejecución? (s/n): </b>'), style=pt_style)
        answer = answer.lower().strip()
        if answer in ['s', 'si', 'y', 'yes']: return True
        if answer in ['n', 'no']: return False

# --- COMANDOS CLI ---
@click.group()
def cli():
    """🧠 Kognito AI CLI - Tu exocerebro en la terminal."""
    pass

@cli.command()
@click.option('--url', default=DEFAULT_API_URL, help='URL de la API de Kognito')
def login(url):
    """Inicia sesión en Kognito AI."""
    save_config({"api_url": url})
    console.print(Panel.fit("🔐 [bold cyan]AUTENTICACIÓN REQUERIDA[/bold cyan]", border_style="cyan", box=ROUNDED))
    method = click.prompt("Método", type=click.Choice(['telegram', 'email']), default='telegram')
    if method == 'telegram': asyncio.run(login_telegram(url))
    else: asyncio.run(login_email(url))

async def login_telegram(api_url):
    identifier = click.prompt("Alias/ID de Telegram")
    async with httpx.AsyncClient() as client:
        try:
            with Status("[cyan]Solicitando código...", console=console):
                resp = await client.post(f"{api_url}/api/auth/request-code", json={"identifier": identifier})
            if resp.status_code != 200:
                console.print(f"[error]❌ Error:[/error] {resp.json().get('detail', 'Error')}")
                return
            console.print("[success]✅ Código enviado.[/success]")
            code = click.prompt("Introduce el código")
            with Status("[cyan]Verificando...", console=console):
                resp = await client.post(f"{api_url}/api/auth/verify-code", json={"identifier": identifier, "code": code})
            if resp.status_code == 200:
                config = load_config()
                config["token"] = resp.json().get("access_token", "")
                save_config(config)
                console.print(Panel("[bold green]🎉 ¡Sesión iniciada![/bold green]", border_style="green"))
            else: console.print(f"[error]❌ Código inválido.[/error]")
        except Exception as e: console.print(f"[error]❌ Error de conexión:[/error] {e}")

async def login_email(api_url):
    email = click.prompt("Email")
    password = click.prompt("Contraseña", hide_input=True)
    async with httpx.AsyncClient() as client:
        try:
            with Status("[cyan]Iniciando sesión...", console=console):
                resp = await client.post(f"{api_url}/api/auth/login", json={"email": email, "password": password})
            if resp.status_code == 200:
                config = load_config()
                config["token"] = resp.json().get("access_token", "")
                save_config(config)
                console.print(Panel("[bold green]🎉 ¡Sesión iniciada![/bold green]", border_style="green"))
            else: console.print(f"[error]❌ Credenciales incorrectas.[/error]")
        except Exception as e: console.print(f"[error]❌ Error de conexión:[/error] {e}")

@cli.command()
@click.argument('command_str')
def run(command_str):
    """Ejecuta un comando en la terminal local."""
    executor = CommandExecutor()
    console.print(Panel(f"[info]Ejecutando:[/info] [cmd]{command_str}[/cmd]", border_style="spring_green3"))
    try:
        for output in executor.execute(command_str):
            console.print(output)
    except Exception as e:
        console.print(f"[error]Error ejecutando comando: {e}[/error]")
    console.print()


# --- HELPERS PARA APIS ---
def format_datetime(dt_str: str) -> str:
    if not dt_str: return "-"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y, %H:%M")
    except Exception:
        return dt_str.split("T")[0]

def make_sync_request(method: str, path: str, json_data: dict = None, params: dict = None, is_binary: bool = False):
    api_url = get_api_url()
    token = get_token()
    if not token:
        console.print("[warning]⚠️ No has iniciado sesión. Ejecuta 'kai login' primero.[/warning]")
        sys.exit(1)
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client() as client:
        try:
            resp = client.request(method, f"{api_url}{path}", headers=headers, json=json_data, params=params, timeout=30)
            if resp.status_code in [401, 403]:
                console.print("[error]❌ Error de autenticación. Inicia sesión con 'kai login'.[/error]")
                sys.exit(1)
            if resp.status_code >= 400:
                try: detail = resp.json().get("detail", resp.text)
                except Exception: detail = resp.text
                console.print(f"[error]❌ Error en la API ({resp.status_code}): {detail}[/error]")
                return None
            return resp.content if is_binary else resp.json()
        except Exception as e:
            console.print(f"[error]❌ Error de conexión: {e}[/error]")
            sys.exit(1)

# --- GRUPO: WORKSPACE ---
@cli.group()
def workspace():
    """🏢 Gestionar espacios de trabajo (workspaces)."""
    pass

@workspace.command(name="list")
def workspace_list():
    """Listar todos los espacios de trabajo."""
    data = make_sync_request("GET", "/api/workspaces")
    if not data: return
    workspaces = data.get("workspaces", [])
    if not workspaces:
        console.print("[info]No tienes ningún espacio de trabajo creado.[/info]")
        return
    
    table = Table(title="🏢 Espacios de Trabajo", border_style="cyan", box=ROUNDED)
    table.add_column("ID", style="dim", width=10)
    table.add_column("Nombre", style="bold magenta")
    table.add_column("Color", style="bold")
    table.add_column("System Prompt", style="italic grey70", max_width=40)
    table.add_column("Creado", style="dim")
    
    for ws in workspaces:
        color_hex = ws.get("color") or "#ffffff"
        color_text = Text(color_hex, style=color_hex)
        table.add_row(
            ws["id"][:8],
            ws["name"],
            color_text,
            ws.get("system_prompt") or "Sin prompt personalizado",
            format_datetime(ws.get("created_at"))
        )
    console.print(table)

@workspace.command(name="create")
@click.argument("name")
@click.option("--prompt", help="Prompt de sistema personalizado para el agente en este workspace.")
@click.option("--color", help="Color representativo en formato hexadecimal (ej: #ff00ff).")
def workspace_create(name, prompt, color):
    """Crear un nuevo espacio de trabajo."""
    payload = {"name": name, "system_prompt": prompt, "color": color}
    data = make_sync_request("POST", "/api/workspaces", json_data=payload)
    if data:
        console.print(Panel(f"[success]✅ Workspace creado exitosamente![/success]\n\n[bold]ID:[/bold] {data['id']}\n[bold]Nombre:[/bold] {data['name']}\n[bold]Color:[/bold] {data.get('color', '-')}", title="🏢 Nuevo Workspace", border_style="magenta", box=ROUNDED))

@workspace.command(name="delete")
@click.argument("workspace_id")
def workspace_delete(workspace_id):
    """Eliminar un espacio de trabajo por su ID."""
    if not click.confirm(f"¿Estás seguro de que deseas eliminar el workspace '{workspace_id}'? Esta acción es irreversible."):
        return
    
    api_url = get_api_url()
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    if len(workspace_id) < 36:
        data = make_sync_request("GET", "/api/workspaces")
        if data:
            found = next((w for w in data.get("workspaces", []) if w["id"].startswith(workspace_id)), None)
            if found: workspace_id = found["id"]
            
    with httpx.Client() as client:
        resp = client.delete(f"{api_url}/api/workspaces/{workspace_id}", headers=headers)
        if resp.status_code == 204:
            console.print(f"[success]✅ Workspace '{workspace_id}' eliminado correctamente.[/success]")
        else:
            console.print(f"[error]❌ Error eliminando workspace: {resp.text}[/error]")

@workspace.command(name="show")
@click.argument("workspace_id")
def workspace_show(workspace_id):
    """Mostrar los detalles de un espacio de trabajo."""
    if len(workspace_id) < 36:
        data = make_sync_request("GET", "/api/workspaces")
        if data:
            found = next((w for w in data.get("workspaces", []) if w["id"].startswith(workspace_id)), None)
            if found: workspace_id = found["id"]
            
    ws = make_sync_request("GET", f"/api/workspaces/{workspace_id}")
    if ws:
        content = f"[bold magenta]Nombre:[/bold magenta] {ws['name']}\n"
        content += f"[bold magenta]ID:[/bold magenta] {ws['id']}\n"
        content += f"[bold magenta]Color:[/bold magenta] {ws.get('color', '-')}\n"
        content += f"[bold magenta]Creado:[/bold magenta] {format_datetime(ws.get('created_at'))}\n\n"
        content += f"[bold magenta]System Prompt:[/bold magenta]\n{ws.get('system_prompt') or 'Sin prompt personalizado'}"
        console.print(Panel(content, title=f"🏢 Workspace: {ws['name']}", border_style="cyan", box=ROUNDED))

@workspace.command(name="share")
@click.argument("workspace_id")
@click.argument("email")
@click.option("--role", type=click.Choice(["owner", "editor", "viewer"]), default="viewer", help="Rol asignado al usuario")
def workspace_share(workspace_id, email, role):
    """Compartir un espacio de trabajo con otro usuario."""
    if len(workspace_id) < 36:
        data = make_sync_request("GET", "/api/workspaces")
        if data:
            found = next((w for w in data.get("workspaces", []) if w["id"].startswith(workspace_id)), None)
            if found: workspace_id = found["id"]
            
    payload = {"email": email, "role": role}
    data = make_sync_request("POST", f"/api/workspaces/{workspace_id}/share", json_data=payload)
    if data is not None:
        console.print(f"[success]✅ Workspace compartido con '{email}' con el rol '{role}'.[/success]")

# --- GRUPO: NOTE ---
@cli.group()
def note():
    """📝 Gestionar notas."""
    pass

@note.command(name="list")
@click.option("--workspace", help="Filtrar por ID o prefijo de workspace")
@click.option("--search", help="Buscar por término de texto en título o contenido")
@click.option("--category", help="Filtrar por categoría")
@click.option("--limit", default=10, type=int, help="Número máximo de notas")
def note_list(workspace, search, category, limit):
    """Listar notas del usuario."""
    ws_id = None
    if workspace:
        if len(workspace) < 36:
            ws_data = make_sync_request("GET", "/api/workspaces")
            if ws_data:
                found = next((w for w in ws_data.get("workspaces", []) if w["id"].startswith(workspace)), None)
                if found: ws_id = found["id"]
        else:
            ws_id = workspace
            
    payload = {
        "search_term": search,
        "workspace_id": ws_id,
        "category": category,
        "skip": 0,
        "limit": limit
    }
    
    data = make_sync_request("POST", "/api/notes/list-notes", json_data=payload)
    if not data: return
    notes = data.get("notes", [])
    if not notes:
        console.print("[info]No se encontraron notas.[/info]")
        return
        
    table = Table(title="📝 Notas de Kognito AI", border_style="magenta", box=ROUNDED)
    table.add_column("ID", style="dim")
    table.add_column("Título", style="bold white")
    table.add_column("Categoría", style="cyan")
    table.add_column("Favorita", style="yellow", justify="center")
    table.add_column("Workspace", style="green")
    table.add_column("Fecha", style="dim")
    
    for n in notes:
        starred = "⭐" if n.get("is_starred") else "-"
        ws_name = n.get("workspace_name") or "Global"
        table.add_row(
            str(n["id"]),
            n.get("title") or "Sin título",
            n.get("category") or "-",
            starred,
            ws_name,
            format_datetime(n.get("created_at"))
        )
    console.print(table)

@note.command(name="create")
@click.argument("content")
@click.option("--title", help="Título de la nota")
@click.option("--category", help="Categoría de la nota")
@click.option("--workspace", help="ID o prefijo del workspace")
def note_create(content, title, category, workspace):
    """Crear una nueva nota."""
    ws_id = None
    if workspace:
        if len(workspace) < 36:
            ws_data = make_sync_request("GET", "/api/workspaces")
            if ws_data:
                found = next((w for w in ws_data.get("workspaces", []) if w["id"].startswith(workspace)), None)
                if found: ws_id = found["id"]
        else:
            ws_id = workspace
            
    payload = {
        "title": title,
        "content": content,
        "category": category,
        "workspace_id": ws_id
    }
    
    data = make_sync_request("POST", "/api/add-note", json_data=payload)
    if data:
        console.print(Panel(f"[success]✅ Nota creada exitosamente![/success]\n\n[bold]ID:[/bold] {data['id']}\n[bold]Título:[/bold] {data.get('title') or 'Sin título'}\n[bold]Categoría:[/bold] {data.get('category') or '-'}", title="📝 Nueva Nota", border_style="green", box=ROUNDED))

@note.command(name="show")
@click.argument("note_id", type=int)
def note_show(note_id):
    """Mostrar los detalles y contenido de una nota."""
    note = make_sync_request("GET", f"/api/notes/{note_id}")
    if note:
        title = note.get("title") or "Nota sin título"
        metadata = f"[dim]Categoría: {note.get('category') or '-'} | Workspace: {note.get('workspace_name') or 'Global'} | Creada: {format_datetime(note.get('created_at'))}[/dim]\n"
        starred = " ⭐ (Favorita)" if note.get("is_starred") else ""
        
        console.print(Panel(
            Group(
                Text.from_markup(metadata + starred + "\n"),
                Markdown(note.get("content", ""))
            ),
            title=f"📝 {title}",
            border_style="magenta",
            box=ROUNDED,
            padding=(1, 2)
        ))

@note.command(name="update")
@click.argument("note_id", type=int)
@click.option("--title", help="Nuevo título")
@click.option("--content", help="Nuevo contenido")
@click.option("--category", help="Nueva categoría")
@click.option("--star/--unstar", default=None, help="Marcar como favorita / quitar favorita")
def note_update(note_id, title, content, category, star):
    """Actualizar una nota existente."""
    payload = {"note_id": note_id}
    if title is not None: payload["title"] = title
    if content is not None: payload["content"] = content
    if category is not None: payload["category"] = category
    if star is not None: payload["is_starred"] = star
    
    data = make_sync_request("POST", "/api/update-note", json_data=payload)
    if data:
        console.print(f"[success]✅ Nota {note_id} actualizada correctamente.[/success]")

@note.command(name="delete")
@click.argument("note_id", type=int)
def note_delete(note_id):
    """Eliminar una nota."""
    if not click.confirm(f"¿Estás seguro de que deseas eliminar la nota {note_id}?"):
        return
    payload = {"note_id": note_id}
    data = make_sync_request("POST", "/api/delete-note", json_data=payload)
    if data:
        console.print(f"[success]✅ Nota {note_id} eliminada correctamente.[/success]")

@note.command(name="pdf")
@click.argument("note_id", type=int)
@click.option("--output", help="Ruta del archivo PDF de salida")
def note_pdf(note_id, output):
    """Exportar nota a un archivo PDF estilizado."""
    payload = {"note_id": note_id, "format": "markdown"}
    data = make_sync_request("POST", "/api/notes/generate-pdf", json_data=payload, is_binary=True)
    if data:
        if not output:
            output = f"nota_{note_id}.pdf"
        Path(output).write_bytes(data)
        console.print(f"[success]✅ PDF generado y guardado en: [bold]{output}[/bold][/success]")

# --- GRUPO: TASK ---
@cli.group()
def task():
    """✅ Gestionar tareas (todos)."""
    pass

@task.command(name="list")
@click.option("--workspace", help="Filtrar por ID o prefijo de workspace")
@click.option("--completed/--pending", default=None, help="Filtrar por tareas completadas o pendientes")
@click.option("--status", help="Filtrar por estado (ej: 'To Do', 'In Progress', 'Done')")
@click.option("--search", help="Buscar por término en la descripción")
def task_list(workspace, completed, status, search):
    """Listar las tareas del usuario."""
    ws_id = None
    if workspace:
        if len(workspace) < 36:
            ws_data = make_sync_request("GET", "/api/workspaces")
            if ws_data:
                found = next((w for w in ws_data.get("workspaces", []) if w["id"].startswith(workspace)), None)
                if found: ws_id = found["id"]
        else:
            ws_id = workspace
            
    params = {}
    if ws_id: params["workspace_id"] = ws_id
    if completed is not None: params["is_completed"] = str(completed).lower()
    if status: params["status"] = status
    if search: params["search_term"] = search
    
    tasks = make_sync_request("GET", "/api/tasks", params=params)
    if not tasks: return
    if not tasks:
        console.print("[info]No se encontraron tareas.[/info]")
        return
        
    table = Table(title="✅ Tareas de Kognito AI", border_style="spring_green3", box=ROUNDED)
    table.add_column("ID", style="dim", width=8)
    table.add_column("Descripción", style="bold white", max_width=50)
    table.add_column("Completado", justify="center")
    table.add_column("Estado", style="cyan")
    table.add_column("F. Límite (End Date)", style="yellow")
    table.add_column("Workspace", style="green")
    
    for t in tasks:
        comp_str = "[green]✔ Sí[/green]" if t.get("is_completed") else "[red]✗ No[/red]"
        ws_val = t.get("workspace_id")
        ws_str = ws_val[:8] if ws_val else "Global"
        table.add_row(
            t["id"][:8],
            t.get("description") or "",
            comp_str,
            t.get("status") or "Pending",
            format_datetime(t.get("end_date")),
            ws_str
        )
    console.print(table)

@task.command(name="create")
@click.argument("description")
@click.option("--start", help="Fecha de inicio (YYYY-MM-DD HH:MM)")
@click.option("--end", help="Fecha de vencimiento (YYYY-MM-DD HH:MM)")
@click.option("--workspace", help="ID o prefijo del workspace")
def task_create(description, start, end, workspace):
    """Crear una nueva tarea."""
    ws_id = None
    if workspace:
        if len(workspace) < 36:
            ws_data = make_sync_request("GET", "/api/workspaces")
            if ws_data:
                found = next((w for w in ws_data.get("workspaces", []) if w["id"].startswith(workspace)), None)
                if found: ws_id = found["id"]
        else:
            ws_id = workspace
            
    payload = {
        "description": description,
        "workspace_id": ws_id
    }
    if start:
        try: payload["start_date"] = datetime.strptime(start, "%Y-%m-%d %H:%M").isoformat()
        except ValueError: console.print("[error]❌ Formato de fecha start inválido. Use YYYY-MM-DD HH:MM[/error]"); return
    if end:
        try: payload["end_date"] = datetime.strptime(end, "%Y-%m-%d %H:%M").isoformat()
        except ValueError: console.print("[error]❌ Formato de fecha end inválido. Use YYYY-MM-DD HH:MM[/error]"); return
        
    data = make_sync_request("POST", "/api/tasks", json_data=payload)
    if data:
        console.print(Panel(f"[success]✅ Tarea creada exitosamente![/success]\n\n[bold]ID:[/bold] {data['id']}\n[bold]Descripción:[/bold] {data.get('description')}\n[bold]Estado:[/bold] {data.get('status')}", title="✅ Nueva Tarea", border_style="spring_green3", box=ROUNDED))

@task.command(name="update")
@click.argument("task_id")
@click.option("--description", help="Nueva descripción")
@click.option("--status", help="Nuevo estado de la tarea")
@click.option("--completed/--pending", default=None, help="Marcar como completada o pendiente")
def task_update(task_id, description, status, completed):
    """Actualizar una tarea existente."""
    if len(task_id) < 36:
        tasks = make_sync_request("GET", "/api/tasks")
        if tasks:
            found = next((t for t in tasks if t["id"].startswith(task_id)), None)
            if found: task_id = found["id"]
            
    payload = {}
    if description is not None: payload["description"] = description
    if status is not None: payload["status"] = status
    if completed is not None: payload["is_completed"] = completed
    
    data = make_sync_request("PUT", f"/api/tasks/{task_id}", json_data=payload)
    if data:
        console.print(f"[success]✅ Tarea {task_id[:8]} actualizada correctamente.[/success]")

@task.command(name="delete")
@click.argument("task_id")
def task_delete(task_id):
    """Eliminar una tarea."""
    if len(task_id) < 36:
        tasks = make_sync_request("GET", "/api/tasks")
        if tasks:
            found = next((t for t in tasks if t["id"].startswith(task_id)), None)
            if found: task_id = found["id"]
            
    if not click.confirm(f"¿Estás seguro de que deseas eliminar la tarea '{task_id[:8]}'?"):
        return
        
    api_url = get_api_url()
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client() as client:
        resp = client.delete(f"{api_url}/api/tasks/{task_id}", headers=headers)
        if resp.status_code == 204:
            console.print(f"[success]✅ Tarea '{task_id[:8]}' eliminada correctamente.[/success]")
        else:
            console.print(f"[error]❌ Error eliminando tarea: {resp.text}[/error]")

# --- GRUPO: EVENT ---
@cli.group()
def event():
    """📅 Gestionar eventos de la agenda."""
    pass

@event.command(name="list")
@click.option("--workspace", help="Filtrar por ID o prefijo de workspace")
@click.option("--past", is_flag=True, help="Incluir eventos pasados")
def event_list(workspace, past):
    """Listar los eventos de la agenda."""
    ws_id = None
    if workspace:
        if len(workspace) < 36:
            ws_data = make_sync_request("GET", "/api/workspaces")
            if ws_data:
                found = next((w for w in ws_data.get("workspaces", []) if w["id"].startswith(workspace)), None)
                if found: ws_id = found["id"]
        else:
            ws_id = workspace
            
    params = {"include_past": str(past).lower()}
    if ws_id: params["workspace_id"] = ws_id
    
    events = make_sync_request("GET", "/api/agenda/events", params=params)
    if not events: return
    if not events:
        console.print("[info]No se encontraron eventos en la agenda.[/info]")
        return
        
    table = Table(title="📅 Eventos en la Agenda", border_style="yellow", box=ROUNDED)
    table.add_column("ID", style="dim")
    table.add_column("Resumen/Título", style="bold white")
    table.add_column("Descripción", style="grey70", max_width=40)
    table.add_column("Fecha y Hora", style="cyan")
    table.add_column("Fin", style="cyan")
    table.add_column("Ubicación", style="italic")
    table.add_column("Workspace", style="green")
    
    for e in events:
        ws_val = e.get("workspace_id")
        ws_str = ws_val[:8] if ws_val else "Global"
        
        start_dt = f"{e.get('event_date')} {e.get('event_time')}"
        end_dt = "-"
        if e.get("end_date"):
            end_dt = f"{e.get('end_date')} {e.get('end_time') or ''}"
            
        table.add_row(
            str(e["id"]),
            e.get("summary") or "Sin resumen",
            e.get("description") or "-",
            start_dt,
            end_dt,
            e.get("location") or "-",
            ws_str
        )
    console.print(table)

@event.command(name="create")
@click.argument("summary")
@click.argument("date")  # YYYY-MM-DD
@click.argument("time")  # HH:MM
@click.option("--desc", default="", help="Descripción del evento")
@click.option("--end-date", help="Fecha de fin (YYYY-MM-DD)")
@click.option("--end-time", help="Hora de fin (HH:MM)")
@click.option("--location", help="Ubicación física o digital")
@click.option("--workspace", help="ID o prefijo del workspace")
def event_create(summary, date, time, desc, end_date, end_time, location, workspace):
    """Crear un nuevo evento en la agenda."""
    ws_id = None
    if workspace:
        if len(workspace) < 36:
            ws_data = make_sync_request("GET", "/api/workspaces")
            if ws_data:
                found = next((w for w in ws_data.get("workspaces", []) if w["id"].startswith(workspace)), None)
                if found: ws_id = found["id"]
        else:
            ws_id = workspace
            
    payload = {
        "summary": summary,
        "description": desc,
        "event_date": date,
        "event_time": time,
        "end_date": end_date,
        "end_time": end_time,
        "location": location,
        "workspace_id": ws_id
    }
    
    data = make_sync_request("POST", "/api/add-event", json_data=payload)
    if data:
        console.print(Panel(f"[success]✅ Evento agendado exitosamente![/success]\n\n[bold]ID:[/bold] {data.get('id')}\n[bold]Título:[/bold] {data.get('summary')}\n[bold]Fecha/Hora:[/bold] {data.get('event_date')} {data.get('event_time')}", title="📅 Nuevo Evento", border_style="yellow", box=ROUNDED))

@event.command(name="cancel")
@click.argument("event_id", type=int)
def event_cancel(event_id):
    """Cancelar un evento de la agenda."""
    if not click.confirm(f"¿Estás seguro de que deseas cancelar el evento {event_id}?"):
        return
    payload = {"event_id": event_id}
    data = make_sync_request("POST", "/api/cancel-event", json_data=payload)
    if data:
        console.print(f"[success]✅ Evento {event_id} cancelado correctamente.[/success]")

# --- GRUPO: MEMORY ---
@cli.group()
def memory():
    """🧠 Gestionar memorias del agente."""
    pass

@memory.command(name="list")
def memory_list():
    """Listar las memorias guardadas en el exocerebro."""
    data = make_sync_request("GET", "/api/memories")
    if not data: return
    if not data:
        console.print("[info]No se encontraron memorias en tu exocerebro.[/info]")
        return
        
    table = Table(title="🧠 Memorias en el Exocerebro", border_style="bright_magenta", box=ROUNDED)
    table.add_column("ID", style="dim", width=12)
    table.add_column("Título/Tema", style="bold white")
    table.add_column("Contenido", style="italic grey70", max_width=50)
    table.add_column("Tipo", style="cyan")
    table.add_column("Creada", style="dim")
    
    for m in data:
        table.add_row(
            m["id"][:12],
            m.get("title") or "Sin título",
            m.get("content") or "",
            m.get("type") or "general_memory",
            format_datetime(m.get("created_at"))
        )
    console.print(table)

@memory.command(name="create")
@click.argument("content")
@click.option("--title", help="Título o tema representativo de la memoria")
@click.option("--type", default="general_memory", help="Tipo de memoria (ej: general_memory, user_memory)")
def memory_create(content, title, type):
    """Añadir una nueva memoria al exocerebro."""
    payload = {
        "title": title,
        "content": content,
        "type": type
    }
    data = make_sync_request("POST", "/api/memories", json_data=payload)
    if data:
        console.print("[success]✅ Memoria añadida al exocerebro exitosamente.[/success]")

@memory.command(name="delete")
@click.argument("memory_id")
def memory_delete(memory_id):
    """Eliminar una memoria por su ID."""
    if len(memory_id) < 36:
        data = make_sync_request("GET", "/api/memories")
        if data:
            found = next((m for m in data if m["id"].startswith(memory_id)), None)
            if found: memory_id = found["id"]
            
    if not click.confirm(f"¿Deseas eliminar la memoria '{memory_id[:12]}' del exocerebro?"):
        return
        
    api_url = get_api_url()
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client() as client:
        resp = client.delete(f"{api_url}/api/memories/{memory_id}", headers=headers)
        if resp.status_code == 200:
            console.print(f"[success]✅ Memoria '{memory_id[:12]}' eliminada correctamente del exocerebro.[/success]")
        else:
            console.print(f"[error]❌ Error eliminando memoria: {resp.text}[/error]")

# --- GRUPO: THREAD ---
@cli.group()
def thread():
    """💬 Gestionar hilos de conversación."""
    pass

@thread.command(name="list")
@click.option("--limit", default=10, type=int, help="Límite de conversaciones a listar")
def thread_list(limit):
    """Listar las conversaciones (hilos de chat)."""
    params = {"limit": limit}
    data = make_sync_request("GET", "/api/threads", params=params)
    if not data: return
    threads = data.get("threads", [])
    if not threads:
        console.print("[info]No se encontraron hilos de chat.[/info]")
        return
        
    table = Table(title="💬 Conversaciones Recientes", border_style="magenta", box=ROUNDED)
    table.add_column("ID", style="dim")
    table.add_column("Título", style="bold white")
    table.add_column("Fijado", justify="center")
    table.add_column("Plataforma", style="cyan")
    table.add_column("Workspace", style="green")
    table.add_column("Creado", style="dim")
    
    for t in threads:
        pinned = "📌" if t.get("isPinned") else "-"
        ws_val = t.get("workspace_id")
        ws_str = ws_val[:8] if ws_val else "Global"
        table.add_row(
            t["id"][:8],
            t.get("title") or "Sin título",
            pinned,
            t.get("platform") or "web",
            ws_str,
            format_datetime(t.get("created_at"))
        )
    console.print(table)

@thread.command(name="create")
@click.option("--title", default="Nuevo Chat", help="Título del hilo")
@click.option("--workspace", help="ID o prefijo del workspace")
def thread_create(title, workspace):
    """Crear una nueva conversación."""
    ws_id = None
    if workspace:
        if len(workspace) < 36:
            ws_data = make_sync_request("GET", "/api/workspaces")
            if ws_data:
                found = next((w for w in ws_data.get("workspaces", []) if w["id"].startswith(workspace)), None)
                if found: ws_id = found["id"]
        else:
            ws_id = workspace
            
    payload = {
        "title": title,
        "platform": "cli",
        "workspace_id": ws_id
    }
    data = make_sync_request("POST", "/api/threads", json_data=payload)
    if data:
        console.print(Panel(f"[success]✅ Hilo de chat creado exitosamente![/success]\n\n[bold]ID:[/bold] {data['id']}\n[bold]Título:[/bold] {data.get('title')}", title="💬 Nuevo Hilo de Chat", border_style="magenta", box=ROUNDED))

@thread.command(name="delete")
@click.argument("thread_id")
def thread_delete(thread_id):
    """Eliminar un hilo de conversación por su ID."""
    if len(thread_id) < 36:
        params = {"limit": 50}
        data = make_sync_request("GET", "/api/threads", params=params)
        if data:
            found = next((t for t in data.get("threads", []) if t["id"].startswith(thread_id)), None)
            if found: thread_id = found["id"]
            
    if not click.confirm(f"¿Estás seguro de que deseas eliminar el hilo '{thread_id[:8]}'?"):
        return
        
    api_url = get_api_url()
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client() as client:
        resp = client.delete(f"{api_url}/api/threads/{thread_id}", headers=headers)
        if resp.status_code == 200:
            console.print(f"[success]✅ Hilo '{thread_id[:8]}' eliminado correctamente.[/success]")
        else:
            console.print(f"[error]❌ Error eliminando hilo: {resp.text}[/error]")



@cli.command()
def chat():
    """Inicia la interfaz de chat interactiva."""
    token = get_token()
    if not token:
        console.print("[warning]⚠️ No has iniciado sesión. Ejecuta 'kai login' primero.[/warning]")
        return
    asyncio.run(interactive_chat())

# --- LÓGICA DE METACOMANDOS ---
async def list_workspaces(api_url, token):
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{api_url}/api/workspaces", headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 200:
                workspaces = resp.json().get("workspaces", [])
                table = Table(title="🏢 Espacios de Trabajo", border_style="cyan", box=ROUNDED)
                table.add_column("ID", style="dim")
                table.add_column("Nombre", style="bold magenta")
                table.add_column("Rol", style="green")
                for ws in workspaces: table.add_row(ws["id"][:8], ws["name"], ws.get("role", "member"))
                console.print(table)
                return workspaces
        except Exception as e: console.print(f"[error]Error: {e}[/error]")
    return []

async def list_threads(api_url, token):
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{api_url}/api/threads?limit=10", headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 200:
                threads = resp.json().get("threads", [])
                table = Table(title="💬 Conversaciones Recientes", border_style="magenta", box=ROUNDED)
                table.add_column("ID", style="dim")
                table.add_column("Título", style="bold white")
                table.add_column("Fecha", style="dim")
                for t in threads:
                    date_str = t.get("updated_at", "").split("T")[0]
                    table.add_row(t["id"][:8], t.get("title", "Sin título"), date_str)
                console.print(table)
                return threads
        except Exception as e: console.print(f"[error]Error: {e}[/error]")
    return []

# --- FUNCIONES ASÍNCRONAS PARA EL CHAT INTERACTIVO ---
async def list_notes(api_url, token, workspace_id=None):
    async with httpx.AsyncClient() as client:
        try:
            payload = {
                "search_term": None,
                "workspace_id": workspace_id,
                "category": None,
                "skip": 0,
                "limit": 15
            }
            resp = await client.post(f"{api_url}/api/notes/list-notes", json=payload, headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 200:
                notes = resp.json().get("notes", [])
                if not notes:
                    console.print("[info]No tienes notas creadas.[/info]")
                    return
                table = Table(title="📝 Notas de Kognito AI", border_style="magenta", box=ROUNDED)
                table.add_column("ID", style="dim")
                table.add_column("Título", style="bold white")
                table.add_column("Categoría", style="cyan")
                table.add_column("Favorita", style="yellow", justify="center")
                table.add_column("Workspace", style="green")
                for n in notes:
                    starred = "⭐" if n.get("is_starred") else "-"
                    table.add_row(str(n["id"]), n.get("title") or "Sin título", n.get("category") or "-", starred, n.get("workspace_name") or "Global")
                console.print(table)
        except Exception as e: console.print(f"[error]Error: {e}[/error]")

async def show_note_content(api_url, token, note_id):
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{api_url}/api/notes/{note_id}", headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 200:
                note = resp.json() if isinstance(resp.json(), dict) else {}
                title = note.get("title") or "Nota sin título"
                metadata = f"[dim]Categoría: {note.get('category') or '-'} | Workspace: {note.get('workspace_name') or 'Global'} | Creada: {format_datetime(note.get('created_at'))}[/dim]\n"
                starred = " ⭐ (Favorita)" if note.get("is_starred") else ""
                console.print(Panel(
                    Group(
                        Text.from_markup(metadata + starred + "\n"),
                        Markdown(note.get("content", ""))
                    ),
                    title=f"📝 {title}",
                    border_style="magenta",
                    box=ROUNDED,
                    padding=(1, 2)
                ))
            else:
                console.print(f"[error]Error: {resp.text}[/error]")
        except Exception as e: console.print(f"[error]Error: {e}[/error]")

async def list_tasks_chat(api_url, token, workspace_id=None):
    async with httpx.AsyncClient() as client:
        try:
            params = {}
            if workspace_id: params["workspace_id"] = workspace_id
            resp = await client.get(f"{api_url}/api/tasks", params=params, headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 200:
                tasks = resp.json().get("tasks", [])
                if not tasks:
                    console.print("[info]No tienes tareas pendientes.[/info]")
                    return
                table = Table(title="✅ Tareas de Kognito AI", border_style="spring_green3", box=ROUNDED)
                table.add_column("ID", style="dim")
                table.add_column("Descripción", style="bold white", max_width=50)
                table.add_column("Completado", justify="center")
                table.add_column("Estado", style="cyan")
                for t in tasks:
                    comp_str = "[green]✔ Sí[/green]" if t.get("is_completed") else "[red]✗ No[/red]"
                    table.add_row(t["id"][:8], t.get("description") or "", comp_str, t.get("status") or "Pending")
                console.print(table)
        except Exception as e: console.print(f"[error]Error: {e}[/error]")

async def list_events_chat(api_url, token, workspace_id=None):
    async with httpx.AsyncClient() as client:
        try:
            params = {}
            if workspace_id: params["workspace_id"] = workspace_id
            resp = await client.get(f"{api_url}/api/agenda/events", params=params, headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 200:
                events = resp.json().get("events", [])
                if not events:
                    console.print("[info]No tienes eventos en tu agenda.[/info]")
                    return
                table = Table(title="📅 Eventos en la Agenda", border_style="yellow", box=ROUNDED)
                table.add_column("ID", style="dim")
                table.add_column("Resumen/Título", style="bold white")
                table.add_column("Fecha y Hora", style="cyan")
                table.add_column("Ubicación", style="italic")
                for e in events:
                    start_dt = f"{e.get('event_date')} {e.get('event_time')}"
                    table.add_row(str(e["id"]), e.get("summary") or "Sin resumen", start_dt, e.get("location") or "-")
                console.print(table)
        except Exception as e: console.print(f"[error]Error: {e}[/error]")

async def list_memories_chat(api_url, token):
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{api_url}/api/memories", headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 200:
                memories = resp.json().get("memories", [])
                if not memories:
                    console.print("[info]No tienes memorias guardadas.[/info]")
                    return
                table = Table(title="🧠 Memorias en el Exocerebro", border_style="bright_magenta", box=ROUNDED)
                table.add_column("ID", style="dim")
                table.add_column("Título/Tema", style="bold white")
                table.add_column("Contenido", style="italic grey70", max_width=50)
                for m in memories:
                    table.add_row(m["id"][:8], m.get("title") or "Sin título", m.get("content") or "")
                console.print(table)
        except Exception as e: console.print(f"[error]Error: {e}[/error]")


async def prompt_workspace_create(api_url, token, session):
    try:
        name = await session.prompt_async(HTML('<b>🏢 Nombre del Workspace: </b>'), style=pt_style)
        if not name.strip(): return console.print("[warning]Cancelado: Nombre vacío.[/warning]")
        prompt = await session.prompt_async(HTML('<b>📝 System Prompt (Opcional): </b>'), style=pt_style)
        color = await session.prompt_async(HTML('<b>🎨 Color Hexadecimal (Opcional, ej: #ff00ff): </b>'), style=pt_style)
        
        payload = {"name": name.strip()}
        if prompt.strip(): payload["system_prompt"] = prompt.strip()
        if color.strip(): payload["color"] = color.strip()
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{api_url}/api/workspaces", json=payload, headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 201:
                console.print(f"[success]✅ Workspace '{name.strip()}' creado con éxito.[/success]")
            else:
                console.print(f"[error]Error al crear workspace: {resp.text}[/error]")
    except Exception as e: console.print(f"[error]Error: {e}[/error]")

async def prompt_note_create(api_url, token, session, workspace_id):
    try:
        title = await session.prompt_async(HTML('<b>📝 Título de la Nota (Opcional): </b>'), style=pt_style)
        category = await session.prompt_async(HTML('<b>🏷️ Categoría (Opcional): </b>'), style=pt_style)
        content = await session.prompt_async(HTML('<b>✍️ Contenido: </b>'), style=pt_style)
        if not content.strip(): return console.print("[warning]Cancelado: Contenido vacío.[/warning]")
        
        payload = {
            "title": title.strip() if title.strip() else None,
            "content": content.strip(),
            "category": category.strip() if category.strip() else None,
            "workspace_id": workspace_id
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{api_url}/api/add-note", json=payload, headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 200:
                console.print("[success]✅ Nota creada correctamente.[/success]")
            else:
                console.print(f"[error]Error al crear nota: {resp.text}[/error]")
    except Exception as e: console.print(f"[error]Error: {e}[/error]")

async def prompt_task_create(api_url, token, session, workspace_id):
    try:
        desc = await session.prompt_async(HTML('<b>✅ Descripción de la Tarea: </b>'), style=pt_style)
        if not desc.strip(): return console.print("[warning]Cancelado: Descripción vacía.[/warning]")
        end_date = await session.prompt_async(HTML('<b>📅 Fecha límite (Opcional, YYYY-MM-DD HH:MM): </b>'), style=pt_style)
        
        payload = {
            "description": desc.strip(),
            "workspace_id": workspace_id
        }
        if end_date.strip():
            try:
                payload["end_date"] = datetime.strptime(end_date.strip(), "%Y-%m-%d %H:%M").isoformat()
            except ValueError:
                console.print("[error]❌ Formato de fecha inválido. Se guardará sin fecha límite.[/error]")
                
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{api_url}/api/tasks", json=payload, headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 201:
                console.print("[success]✅ Tarea creada correctamente.[/success]")
            else:
                console.print(f"[error]Error al crear tarea: {resp.text}[/error]")
    except Exception as e: console.print(f"[error]Error: {e}[/error]")

async def prompt_event_create(api_url, token, session, workspace_id):
    try:
        summary = await session.prompt_async(HTML('<b>📅 Título/Resumen del Evento: </b>'), style=pt_style)
        if not summary.strip(): return console.print("[warning]Cancelado: Título vacío.[/warning]")
        date = await session.prompt_async(HTML('<b>📆 Fecha (YYYY-MM-DD): </b>'), style=pt_style)
        time = await session.prompt_async(HTML('<b>⏰ Hora (HH:MM): </b>'), style=pt_style)
        desc = await session.prompt_async(HTML('<b>📝 Descripción (Opcional): </b>'), style=pt_style)
        location = await session.prompt_async(HTML('<b>📍 Ubicación (Opcional): </b>'), style=pt_style)
        
        if not date.strip() or not time.strip():
            return console.print("[warning]Cancelado: Fecha y hora son requeridas.[/warning]")
            
        payload = {
            "summary": summary.strip(),
            "description": desc.strip(),
            "event_date": date.strip(),
            "event_time": time.strip(),
            "location": location.strip() if location.strip() else None,
            "workspace_id": workspace_id
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{api_url}/api/add-event", json=payload, headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 200:
                console.print("[success]✅ Evento agendado correctamente.[/success]")
            else:
                console.print(f"[error]Error al agendar evento: {resp.text}[/error]")
    except Exception as e: console.print(f"[error]Error: {e}[/error]")

async def prompt_memory_add(api_url, token, session):
    try:
        content = await session.prompt_async(HTML('<b>🧠 Contenido de la Memoria: </b>'), style=pt_style)
        if not content.strip(): return console.print("[warning]Cancelado: Contenido vacío.[/warning]")
        title = await session.prompt_async(HTML('<b>🏷️ Título/Tema (Opcional): </b>'), style=pt_style)
        
        payload = {
            "content": content.strip(),
            "title": title.strip() if title.strip() else "Memoria CLI"
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{api_url}/api/memories", json=payload, headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 200:
                console.print("[success]✅ Memoria guardada correctamente.[/success]")
            else:
                console.print(f"[error]Error al guardar memoria: {resp.text}[/error]")
    except Exception as e: console.print(f"[error]Error: {e}[/error]")

async def complete_task_chat(api_url, token, task_id):
    async with httpx.AsyncClient() as client:
        try:
            if len(task_id) < 36:
                resp_list = await client.get(f"{api_url}/api/tasks", headers={"Authorization": f"Bearer {token}"})
                if resp_list.status_code == 200:
                    found = next((t for t in resp_list.json() if t["id"].startswith(task_id)), None)
                    if found: task_id = found["id"]
            
            payload = {"is_completed": True}
            resp = await client.put(f"{api_url}/api/tasks/{task_id}", json=payload, headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 200:
                console.print(f"[success]✅ Tarea {task_id[:8]} marcada como completada.[/success]")
            else:
                console.print(f"[error]Error al completar tarea: {resp.text}[/error]")
        except Exception as e: console.print(f"[error]Error: {e}[/error]")

async def delete_task_chat(api_url, token, task_id):
    async with httpx.AsyncClient() as client:
        try:
            if len(task_id) < 36:
                resp_list = await client.get(f"{api_url}/api/tasks", headers={"Authorization": f"Bearer {token}"})
                if resp_list.status_code == 200:
                    found = next((t for t in resp_list.json() if t["id"].startswith(task_id)), None)
                    if found: task_id = found["id"]
            
            resp = await client.delete(f"{api_url}/api/tasks/{task_id}", headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 204:
                console.print(f"[success]✅ Tarea {task_id[:8]} eliminada.[/success]")
            else:
                console.print(f"[error]Error al eliminar tarea: {resp.text}[/error]")
        except Exception as e: console.print(f"[error]Error: {e}[/error]")

async def cancel_event_chat(api_url, token, event_id):
    async with httpx.AsyncClient() as client:
        try:
            payload = {"event_id": int(event_id)}
            resp = await client.post(f"{api_url}/api/cancel-event", json=payload, headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 200:
                console.print(f"[success]✅ Evento {event_id} cancelado.[/success]")
            else:
                console.print(f"[error]Error al cancelar evento: {resp.text}[/error]")
        except Exception as e: console.print(f"[error]Error: {e}[/error]")

async def delete_workspace_chat(api_url, token, workspace_id):
    async with httpx.AsyncClient() as client:
        try:
            if len(workspace_id) < 36:
                resp_list = await client.get(f"{api_url}/api/workspaces", headers={"Authorization": f"Bearer {token}"})
                if resp_list.status_code == 200:
                    found = next((w for w in resp_list.json().get("workspaces", []) if w["id"].startswith(workspace_id)), None)
                    if found: workspace_id = found["id"]
            
            resp = await client.delete(f"{api_url}/api/workspaces/{workspace_id}", headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 204:
                console.print(f"[success]✅ Workspace {workspace_id[:8]} eliminado.[/success]")
            else:
                console.print(f"[error]Error al eliminar workspace: {resp.text}[/error]")
        except Exception as e: console.print(f"[error]Error: {e}[/error]")

async def delete_note_chat(api_url, token, note_id):
    async with httpx.AsyncClient() as client:
        try:
            payload = {"note_id": int(note_id)}
            resp = await client.post(f"{api_url}/api/delete-note", json=payload, headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 200:
                console.print(f"[success]✅ Nota {note_id} eliminada.[/success]")
            else:
                console.print(f"[error]Error al eliminar nota: {resp.text}[/error]")
        except Exception as e: console.print(f"[error]Error: {e}[/error]")

async def delete_memory_chat(api_url, token, memory_id):
    async with httpx.AsyncClient() as client:
        try:
            if len(memory_id) < 36:
                resp_list = await client.get(f"{api_url}/api/memories", headers={"Authorization": f"Bearer {token}"})
                if resp_list.status_code == 200:
                    found = next((m for m in resp_list.json() if m["id"].startswith(memory_id)), None)
                    if found: memory_id = found["id"]
            
            resp = await client.delete(f"{api_url}/api/memories/{memory_id}", headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 200:
                console.print(f"[success]✅ Memoria {memory_id[:8]} eliminada.[/success]")
            else:
                console.print(f"[error]Error al eliminar memoria: {resp.text}[/error]")
        except Exception as e: console.print(f"[error]Error: {e}[/error]")

async def create_thread_chat(api_url, token, title, workspace_id=None):
    async with httpx.AsyncClient() as client:
        try:
            payload = {
                "title": title or "Nuevo Chat",
                "platform": "cli",
                "workspace_id": workspace_id
            }
            resp = await client.post(f"{api_url}/api/threads", json=payload, headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 200:
                new_id = resp.json().get("id", "")
                console.print(f"[success]✅ Hilo creado exitosamente: {new_id[:8]}[/success]")
                return new_id
            else:
                console.print(f"[error]Error al crear hilo: {resp.text}[/error]")
        except Exception as e: console.print(f"[error]Error: {e}[/error]")
    return None

async def delete_thread_chat(api_url, token, thread_id):
    async with httpx.AsyncClient() as client:
        try:
            if len(thread_id) < 36:
                resp_list = await client.get(f"{api_url}/api/threads", headers={"Authorization": f"Bearer {token}"})
                if resp_list.status_code == 200:
                    found = next((t for t in resp_list.json().get("threads", []) if t["id"].startswith(thread_id)), None)
                    if found: thread_id = found["id"]
            
            resp = await client.delete(f"{api_url}/api/threads/{thread_id}", headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 200:
                console.print(f"[success]✅ Hilo {thread_id[:8]} eliminado.[/success]")
            else:
                console.print(f"[error]Error al eliminar hilo: {resp.text}[/error]")
        except Exception as e: console.print(f"[error]Error: {e}[/error]")

def show_help():
    intro = """
[bold magenta]Kognito AI (KAI)[/bold magenta] es tu [bold cyan]exocerebro[/bold cyan] en la terminal. 🧠💻
Esta interfaz (KognitoCLI) te permite interactuar con un agente de IA avanzado que no solo conversa, sino que tiene [bold yellow]acceso directo a tu sistema[/bold yellow] para ejecutar tareas reales.
"""
    commands = """
[bold cyan]Metacomandos de Conversación (/) :[/bold cyan]
  [metacmd]/help[/metacmd]                 - Muestra esta guía completa.
  [metacmd]/clear[/metacmd]                - Limpia la pantalla y refresca la UI.
  [metacmd]/exit[/metacmd]                 - Cierra la sesión de chat.

[bold magenta]Metacomandos de Espacios de Trabajo (/) :[/bold magenta]
  [metacmd]/ws[/metacmd]                   - Lista tus espacios de trabajo.
  [metacmd]/ws <nombre>[/metacmd]          - Cambia de espacio de trabajo activo.
  [metacmd]/workspace create[/metacmd]    - Crea interactivamente un workspace.
  [metacmd]/workspace delete <id>[/metacmd] - Elimina un workspace.

[bold yellow]Metacomandos de Tareas y Agenda (/) :[/bold yellow]
  [metacmd]/tasks[/metacmd]                 - Lista tus tareas.
  [metacmd]/task create[/metacmd]          - Crea una tarea interactiva.
  [metacmd]/task complete <id>[/metacmd]   - Marca una tarea como completada.
  [metacmd]/events[/metacmd]                - Lista tus eventos de agenda.
  [metacmd]/event create[/metacmd]         - Crea un evento interactivo.
  [metacmd]/event cancel <id>[/metacmd]    - Cancela un evento de agenda.

[bold green]Metacomandos de Notas y Memorias (/) :[/bold green]
  [metacmd]/notes[/metacmd]                 - Lista tus notas.
  [metacmd]/note show <id>[/metacmd]        - Muestra el contenido renderizado de una nota.
  [metacmd]/note create[/metacmd]          - Crea una nota interactiva.
  [metacmd]/memories[/metacmd]              - Lista memorias en tu exocerebro.
  [metacmd]/memory add[/metacmd]            - Añade una memoria interactiva.

[bold cyan]Metacomandos de Hilos / Chat (/) :[/bold cyan]
  [metacmd]/threads[/metacmd]              - Lista tus últimas 10 conversaciones.
  [metacmd]/thread <id>[/metacmd]           - Cambia a una conversación específica.
  [metacmd]/thread create[/metacmd]        - Crea una nueva conversación.
  [metacmd]/thread delete <id>[/metacmd]      - Elimina una conversación por ID.


[bold yellow]Comandos Locales (!):[/bold yellow]
  [metacmd]!<comando>[/metacmd]             - Ejecuta un comando bash directamente (ej: !ls -la).
"""
    help_group = Group(
        Panel(intro, border_style="magenta", title="🤖 ¿QUÉ ES KOGNITOCLI?", box=ROUNDED),
        Panel(commands, border_style="cyan", title="📖 GUÍA DE COMANDOS", box=ROUNDED)
    )
    console.print(help_group)

async def interactive_chat():
    api_url = get_api_url()
    token = get_token()
    account_id = get_account_id()
    if not account_id: return console.print("[error]❌ Token inválido.[/error]")

    thread_id = None
    current_workspace = {"id": None, "name": "Global"}
    
    async with httpx.AsyncClient() as client:
        try:
            with Status("[dim]Sincronizando...", console=console):
                resp = await client.get(f"{api_url}/api/threads?limit=1", headers={"Authorization": f"Bearer {token}"})
                threads_data = resp.json() if isinstance(resp.json(), dict) else {}
                if resp.status_code == 200 and threads_data.get("threads"):
                    thread_id = threads_data["threads"][0]["id"]
                else:
                    resp = await client.post(f"{api_url}/api/threads", json={"title": "CLI Chat"}, headers={"Authorization": f"Bearer {token}"})
                    if resp.status_code == 200:
                        thread_id = resp.json().get("id", "")
                    else:
                        console.print(f"[error]❌ Error creando hilo: {resp.text}[/error]")
                        return
        except Exception as e: return console.print(f"[error]❌ Error: {e}[/error]")

    print_banner()
    console.print(f"[system]Hilo activo: {thread_id} | '/help' para ayuda.[/system]\n")

    session = PromptSession(history=FileHistory(str(HISTORY_FILE)))
    def get_toolbar(): 
        ws_name = current_workspace["name"]
        return HTML(f' <b>KAI</b> | Hilo: {thread_id[:8]} | WS: <style color="#ff00ff"><b>{ws_name}</b></style> | <b>/help</b> ')

    while True:
        try:
            user_input = await session.prompt_async(HTML('<style color="#1e90ff"><b>➤ Tú: </b></style>'), style=pt_style, bottom_toolbar=get_toolbar)
        except (EOFError, KeyboardInterrupt): break
        if user_input.lower() in ['salir', 'exit', 'quit', '/exit']: break
        if not user_input.strip(): continue

        # --- METACOMANDOS (/) ---
        if user_input.startswith("/"):
            parts = user_input[1:].split()
            cmd = parts[0].lower()
            subcmd = parts[1].lower() if len(parts) > 1 else None
            
            if cmd == "help":
                show_help()
                continue
            elif cmd == "clear":
                console.clear()
                print_banner()
                continue

            elif cmd == "ws" or cmd == "workspace":
                if subcmd == "create":
                    await prompt_workspace_create(api_url, token, session)
                elif subcmd == "delete":
                    if len(parts) > 2:
                        await delete_workspace_chat(api_url, token, parts[2])
                    else:
                        console.print("[warning]Uso: /workspace delete <workspace_id>[/warning]")
                elif not subcmd or subcmd == "list" or subcmd == "ls":
                    await list_workspaces(api_url, token)
                else:
                    target = " ".join(parts[1:])
                    workspaces = await list_workspaces(api_url, token)
                    found = next((w for w in workspaces if target.lower() in w["name"].lower() or target in w["id"]), None)
                    if found:
                        current_workspace = {"id": found["id"], "name": found["name"]}
                        console.print(Panel(f"🏢 Workspace: [bold magenta]{found['name']}[/bold magenta]", border_style="magenta"))
                    else:
                        console.print(f"[error]No se encontró '{target}'.[/error]\n")
                continue
            elif cmd == "threads" or (cmd == "thread" and (not subcmd or subcmd in ["list", "ls"])):
                await list_threads(api_url, token)
                continue
            elif cmd == "thread":
                if subcmd == "create":
                    title = " ".join(parts[2:]) if len(parts) > 2 else "Nuevo Chat"
                    new_id = await create_thread_chat(api_url, token, title, current_workspace["id"])
                    if new_id:
                        thread_id = new_id
                elif subcmd == "delete":
                    if len(parts) > 2:
                        await delete_thread_chat(api_url, token, parts[2])
                        if parts[2] in thread_id:
                            threads = await list_threads(api_url, token)
                            if threads:
                                thread_id = threads[0]["id"]
                            else:
                                thread_id = None
                    else:
                        console.print("[warning]Uso: /thread delete <thread_id>[/warning]")
                else:
                    target_id = parts[1]
                    threads = await list_threads(api_url, token)
                    found = next((t for t in threads if t["id"].startswith(target_id)), None)
                    if found:
                        thread_id = found["id"]
                        console.print(Panel(f"💬 Hilo cambiado a: [bold white]{found.get('title', thread_id)}[/bold white]", border_style="magenta"))
                    else: console.print(f"[error]No se encontró el hilo '{target_id}'.[/error]\n")
                continue
            elif cmd == "notes" or cmd == "note":
                if not subcmd or subcmd in ["list", "ls"]:
                    await list_notes(api_url, token, current_workspace["id"])
                elif subcmd == "create":
                    await prompt_note_create(api_url, token, session, current_workspace["id"])
                elif subcmd == "show":
                    if len(parts) > 2:
                        await show_note_content(api_url, token, parts[2])
                    else:
                        console.print("[warning]Uso: /note show <note_id>[/warning]")
                elif subcmd == "delete":
                    if len(parts) > 2:
                        await delete_note_chat(api_url, token, parts[2])
                    else:
                        console.print("[warning]Uso: /note delete <note_id>[/warning]")
                else:
                    console.print("[warning]Subcomando de nota no reconocido. Intente: list, create, show, delete[/warning]")
                continue
            elif cmd == "tasks" or cmd == "task":
                if not subcmd or subcmd in ["list", "ls"]:
                    await list_tasks_chat(api_url, token, current_workspace["id"])
                elif subcmd == "create":
                    await prompt_task_create(api_url, token, session, current_workspace["id"])
                elif subcmd == "complete":
                    if len(parts) > 2:
                        await complete_task_chat(api_url, token, parts[2])
                    else:
                        console.print("[warning]Uso: /task complete <task_id>[/warning]")
                elif subcmd == "delete":
                    if len(parts) > 2:
                        await delete_task_chat(api_url, token, parts[2])
                    else:
                        console.print("[warning]Uso: /task delete <task_id>[/warning]")
                else:
                    console.print("[warning]Subcomando de tarea no reconocido. Intente: list, create, complete, delete[/warning]")
                continue
            elif cmd == "events" or cmd == "event":
                if not subcmd or subcmd in ["list", "ls"]:
                    await list_events_chat(api_url, token, current_workspace["id"])
                elif subcmd == "create":
                    await prompt_event_create(api_url, token, session, current_workspace["id"])
                elif subcmd == "cancel":
                    if len(parts) > 2:
                        await cancel_event_chat(api_url, token, parts[2])
                    else:
                        console.print("[warning]Uso: /event cancel <event_id>[/warning]")
                else:
                    console.print("[warning]Subcomando de evento no reconocido. Intente: list, create, cancel[/warning]")
                continue
            elif cmd == "memories" or cmd == "memory":
                if not subcmd or subcmd in ["list", "ls"]:
                    await list_memories_chat(api_url, token)
                elif subcmd == "create" or subcmd == "add":
                    await prompt_memory_add(api_url, token, session)
                elif subcmd == "delete":
                    if len(parts) > 2:
                        await delete_memory_chat(api_url, token, parts[2])
                    else:
                        console.print("[warning]Uso: /memory delete <memory_id>[/warning]")
                else:
                    console.print("[warning]Subcomando de memoria no reconocido. Intente: list, create, delete[/warning]")
                continue

        # --- COMANDOS LOCALES (!) ---
        if user_input.startswith("!"):
            cmd = user_input[1:].strip()
            if cmd:
                if is_dangerous_command(cmd) and not await confirm_action(session, cmd, "Comando destructivo."): continue
                executor = CommandExecutor()
                console.print(Panel(f"[info]Ejecutando local:[/info] [cmd]{cmd}[/cmd]", border_style="spring_green3"))
                try:
                    for output in executor.execute(cmd):
                        console.print(output)
                except Exception as e:
                    console.print(f"[error]Error: {e}[/error]")
                console.print()
                continue

        await process_message(api_url, token, account_id, thread_id, user_input, session, current_workspace["id"])

async def process_message(api_url, token, account_id, thread_id, message, session: PromptSession, workspace_id: str = None):
    ws_url = api_url.replace("http", "ws") + f"/ws/{account_id}?token={token}"
    try:
        async with websockets.connect(ws_url) as websocket:
            async with httpx.AsyncClient() as client:
                payload = {"thread_id": thread_id, "account_id": account_id, "user_message": message}
                if workspace_id: payload["workspace_id"] = workspace_id
                chat_resp = await client.post(f"{api_url}/api/chat", json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=30)
                if chat_resp.status_code != 202: return console.print(create_message_panel(f"Error: {chat_resp.text}", "system"))
                task_id = chat_resp.json().get("taskId")

            full_response = ""
            current_tool = None
            with Live(Spinner("dots", text="[dim]KAI está pensando...[/dim]"), refresh_per_second=15, console=console) as live:
                while True:
                    try:
                        # Timeout para evitar bloqueos
                        try:
                            raw_data = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                        except asyncio.TimeoutError:
                            console.print("[warning]⚠️ Timeout esperando respuesta[/warning]")
                            break
                        
                        # Manejo de ping
                        if raw_data == "ping" or (isinstance(raw_data, str) and raw_data.strip() == "ping"):
                            continue
                        
                        data = json.loads(raw_data)
                        if data.get("taskId") != task_id: continue
                        msg_type = data.get("type")
                        if msg_type == "tool_start":
                            current_tool = data.get("tool_name", "herramienta")
                            live.update(Group(Spinner("bouncingBar", text=f"[yellow]Usando: {current_tool}...[/yellow]"), create_message_panel(full_response or "...", "kai", current_tool)))
                        elif msg_type == "tool_end":
                            current_tool = None
                            live.update(create_message_panel(full_response or "Procesando...", "kai"))
                        elif msg_type == "request_approval":
                            live.stop()
                            approved = await confirm_action(session, data.get("command", ""), data.get("explanation", ""))
                            await websocket.send(json.dumps({"type": "approval_response", "taskId": task_id, "approved": approved}))
                            live.start()
                        elif msg_type == "stream_chunk":
                            full_response += data.get("chunk", "")
                            live.update(create_message_panel(full_response, "kai", current_tool))
                        elif msg_type in ["stream_end", "final_response"]:
                            live.update(create_message_panel(full_response, "kai"))
                            break
                        elif msg_type == "error":
                            live.update(create_message_panel(f"❌ Error: {data.get('error_message')}", "system"))
                            break
                    except Exception: break
            console.print()
    except Exception as e: console.print(create_message_panel(f"❌ Error WebSocket: {e}", "system"))

if __name__ == "__main__": cli()
