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
from datetime import datetime

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
                config["token"] = resp.json()["access_token"]
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
                config["token"] = resp.json()["access_token"]
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
                workspaces = resp.json()
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
                threads = resp.json()["threads"]
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

def show_help():
    intro = """
[bold magenta]Kognito AI (KAI)[/bold magenta] es tu [bold cyan]exocerebro[/bold cyan] en la terminal. 🧠💻
Esta interfaz (KognitoCLI) te permite interactuar con un agente de IA avanzado que no solo conversa, sino que tiene [bold yellow]acceso directo a tu sistema[/bold yellow] para ejecutar tareas reales.
"""
    commands = """
[bold cyan]Metacomandos (/):[/bold cyan]
  [metacmd]/ws[/metacmd]          - Lista tus espacios de trabajo.
  [metacmd]/ws <nombre>[/metacmd] - Cambia de espacio de trabajo activo.
  [metacmd]/threads[/metacmd]     - Lista tus últimas 10 conversaciones.
  [metacmd]/thread <id>[/metacmd]  - Cambia a una conversación específica.
  [metacmd]/clear[/metacmd]       - Limpia la pantalla y refresca la UI.
  [metacmd]/help[/metacmd]        - Muestra esta guía completa.
  [metacmd]/exit[/metacmd]        - Cierra la sesión de chat.

[bold yellow]Comandos Locales (!):[/bold yellow]
  [metacmd]!<comando>[/metacmd]    - Ejecuta un comando bash directamente (ej: !ls -la).
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
                if resp.status_code == 200 and resp.json()["threads"]:
                    thread_id = resp.json()["threads"][0]["id"]
                else:
                    resp = await client.post(f"{api_url}/api/threads", json={"title": "CLI Chat"}, headers={"Authorization": f"Bearer {token}"})
                    if resp.status_code == 200:
                        if resp.status_code == 200:
                        thread_id = resp.json()["id"]
                    else:
                        console.print(f"[error]❌ Error creando hilo: {resp.text}[/error]")
                        return
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
            if cmd == "help": show_help(); continue
            if cmd == "clear": console.clear(); print_banner(); continue
            if cmd in ["ws", "workspace"]:
                if len(parts) == 1: await list_workspaces(api_url, token)
                else:
                    target = " ".join(parts[1:])
                    workspaces = await list_workspaces(api_url, token)
                    found = next((w for w in workspaces if target.lower() in w["name"].lower() or target in w["id"]), None)
                    if found:
                        current_workspace = {"id": found["id"], "name": found["name"]}
                        console.print(Panel(f"🏢 Workspace: [bold magenta]{found['name']}[/bold magenta]", border_style="magenta"))
                    else: console.print(f"[error]No se encontró '{target}'.[/error]\n")
                continue
            if cmd in ["threads", "thread"]:
                if len(parts) == 1: await list_threads(api_url, token)
                else:
                    target_id = parts[1]
                    threads = await list_threads(api_url, token)
                    found = next((t for t in threads if t["id"].startswith(target_id)), None)
                    if found:
                        thread_id = found["id"]
                        console.print(Panel(f"💬 Hilo cambiado a: [bold white]{found.get('title', thread_id)}[/bold white]", border_style="magenta"))
                    else: console.print(f"[error]No se encontró el hilo '{target_id}'.[/error]\n")
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
