"""
cli/main.py
Punto de entrada principal del CLI de KognitoAI.
Uso: python -m cli [COMMAND] o kognito [COMMAND]
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme

# Asegurar que el root del proyecto esté en el path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.core.config import CLIConfig

console = Console(theme=Theme({
    "info": "bold #6C63FF",
    "success": "bold #10b981",
    "warning": "bold #f59e0b",
    "error": "bold #f87171",
    "muted": "#475569",
}))

LOGO = """
[bold #6C63FF]
 ██╗  ██╗ ██████╗  ██████╗ ███╗  ██╗██╗████████╗ ██████╗
 ██║ ██╔╝██╔═══██╗██╔════╝ ████╗ ██║██║╚══██╔══╝██╔═══██╗
 █████╔╝ ██║   ██║██║  ███╗██╔██╗██║██║   ██║   ██║   ██║
 ██╔═██╗ ██║   ██║██║   ██║██║╚████║██║   ██║   ██║   ██║
 ██║  ██╗╚██████╔╝╚██████╔╝██║ ╚███║██║   ██║   ╚██████╔╝
 ╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚══╝╚═╝   ╚═╝    ╚═════╝
[/bold #6C63FF]
[muted]   Tu asistente corporativo de IA — CLI v1.0.0[/muted]
"""


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context):
    """KognitoAI CLI — Tu asistente corporativo de IA en la terminal."""
    if ctx.invoked_subcommand is None:
        # Lanzar TUI directamente si no se da subcomando
        _launch_tui()


# ── TUI command ───────────────────────────────────────────────────────────────

@cli.command("tui")
def cmd_tui():
    """Abrir la interfaz TUI interactiva completa."""
    _launch_tui()


def _launch_tui():
    """Lanza la aplicación Textual TUI."""
    try:
        from cli.ui.tui_app import KognitoTUI
        app = KognitoTUI()
        app.run()
    except ImportError as e:
        console.print(f"[error]Error importando TUI: {e}[/error]")
        console.print("[muted]Asegúrate de instalar: pip install textual[/muted]")
        sys.exit(1)


# ── Login command ─────────────────────────────────────────────────────────────

@cli.command("login")
@click.option("--url", default=None, help="URL del servidor KognitoAI")
@click.option("--email", prompt=True, help="Email del usuario")
@click.option("--password", prompt=True, hide_input=True, help="Contraseña")
def cmd_login(url: str | None, email: str, password: str):
    """Autenticarse con el servidor KognitoAI."""
    config = CLIConfig.load()
    target_url = url or config.api_url

    async def _login():
        from cli.core.api_client import KognitoAPIClient
        console.print(f"[info]Conectando a {target_url}…[/info]")
        try:
            client = await KognitoAPIClient.login(target_url, email, password)
            me = await client.get_me()
            config.api_url = target_url
            config.token = client.token
            config.account_id = me.get("id") or me.get("account_id", "")
            config.email = email
            config.name = me.get("name", "")
            config.save()
            console.print(Panel(
                f"[success]✅ Sesión iniciada como[/success]\n"
                f"[bold white]{me.get('name', email)}[/bold white]\n"
                f"[muted]{email}[/muted]",
                border_style="#6C63FF",
            ))
        except Exception as e:
            console.print(f"[error]❌ Login fallido: {e}[/error]")
            sys.exit(1)

    asyncio.run(_login())


# ── Status command ────────────────────────────────────────────────────────────

@cli.command("status")
def cmd_status():
    """Mostrar estado de la configuración y conexión."""
    config = CLIConfig.load()
    table = Table(title="Estado de KognitoAI CLI", border_style="#6C63FF", show_header=False)
    table.add_column("Campo", style="bold #6C63FF", width=20)
    table.add_column("Valor", style="white")
    table.add_row("Servidor", config.api_url)
    table.add_row("Autenticado", "✅ Sí" if config.is_authenticated else "❌ No")
    table.add_row("Email", config.email or "—")
    table.add_row("Nombre", config.name or "—")
    table.add_row("Workspace", config.workspace_id or "Global")
    table.add_row("Último chat", config.last_thread_id or "—")
    console.print(table)


# ── Chat command (headless) ────────────────────────────────────────────────────

@cli.command("chat")
@click.argument("message")
@click.option("--thread", "-t", default=None, help="ID del hilo de chat")
def cmd_chat(message: str, thread: str | None):
    """Enviar un mensaje al agente (modo headless, sin TUI)."""
    config = CLIConfig.load()
    from cli.core.auth import require_auth
    try:
        require_auth(config)
    except RuntimeError as e:
        console.print(f"[error]{e}[/error]")
        sys.exit(1)

    async def _send():
        from cli.core.api_client import KognitoAPIClient
        client = KognitoAPIClient(config.api_url, config.token)
        thread_id = thread or config.last_thread_id
        if not thread_id:
            console.print("[info]Creando nuevo hilo…[/info]")
            data = await client.create_thread()
            thread_id = data["id"]
            config.last_thread_id = thread_id
            config.save()

        console.print(f"\n[bold white]Tú:[/bold white] {message}\n")
        console.print("[bold #10b981]KognitoAI:[/bold #10b981] ", end="")
        full = ""
        async for chunk in client.send_message_stream(
            thread_id, config.account_id, message, config.workspace_id
        ):
            console.print(chunk, end="", highlight=False)
            full += chunk
        console.print("\n")

    asyncio.run(_send())


# ── Doc commands ──────────────────────────────────────────────────────────────

@cli.group("doc")
def cmd_doc():
    """Comandos para creación y exportación de documentos."""
    pass


@cmd_doc.command("export")
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--format", "-f", type=click.Choice(["word", "pdf"]), default="pdf")
@click.option("--output", "-o", default=None, help="Ruta de salida")
@click.option("--title", "-t", default="Documento", help="Título del documento")
def cmd_doc_export(input_file: str, format: str, output: str | None, title: str):
    """Exportar un archivo Markdown a Word o PDF corporativo."""
    from cli.core.security import validate_output_path
    content = Path(input_file).read_text(encoding="utf-8")
    ext = ".docx" if format == "word" else ".pdf"
    
    raw_out = output or str(Path(input_file).with_suffix(ext))
    try:
        out = str(validate_output_path(raw_out))
    except ValueError as e:
        console.print(f"[error]{e}[/error]")
        sys.exit(1)

    try:
        from cli.modules.doc_editor import export_to_word, export_to_pdf
        console.print(f"[info]Exportando a {format.upper()}…[/info]")
        if format == "word":
            export_to_word(content, out, title=title)
        else:
            export_to_pdf(content, out, title=title)
        console.print(f"[success]✅ Guardado en: {out}[/success]")
    except Exception as e:
        console.print(f"[error]Error: {e}[/error]")
        sys.exit(1)


@cmd_doc.command("new")
@click.option("--title", "-t", prompt="Título del documento", help="Título")
@click.option("--ai", is_flag=True, help="Generar contenido inicial con IA")
@click.option("--message", "-m", default=None, help="Instrucción para la IA")
def cmd_doc_new(title: str, ai: bool, message: str | None):
    """Crear un nuevo documento. Con --ai genera contenido automáticamente."""
    from cli.core.security import sanitize_filename
    config = CLIConfig.load()
    filename = sanitize_filename(title.lower().replace(" ", "_")) + ".md"
    filepath = Path.cwd() / filename

    if ai:
        from cli.core.auth import require_auth
        try:
            require_auth(config)
        except RuntimeError as e:
            console.print(f"[error]{e}[/error]")
            sys.exit(1)

        async def _gen():
            from cli.core.api_client import KognitoAPIClient
            client = KognitoAPIClient(config.api_url, config.token)
            prompt = message or f"Crea el contenido inicial para un documento corporativo titulado '{title}'. Usa formato Markdown con secciones bien estructuradas."
            if not config.last_thread_id:
                data = await client.create_thread(title=f"Doc: {title}")
                config.last_thread_id = data["id"]
                config.save()

            console.print(f"[info]Generando contenido con IA para '{title}'…[/info]")
            content = await client.send_message(
                config.last_thread_id, config.account_id, prompt
            )
            filepath.write_text(f"# {title}\n\n{content}", encoding="utf-8")
            console.print(f"[success]✅ Documento creado: {filepath}[/success]")

        asyncio.run(_gen())
    else:
        filepath.write_text(f"# {title}\n\n", encoding="utf-8")
        console.print(f"[success]✅ Documento creado: {filepath}[/success]")
        console.print("[muted]Edítalo con tu editor favorito o usa: kognito tui[/muted]")


# ── Config command ────────────────────────────────────────────────────────────

@cli.command("config")
@click.option("--workspace", "-w", default=None, help="Workspace ID a usar")
@click.option("--api-url", default=None, help="URL del servidor")
@click.option("--reset", is_flag=True, help="Resetear configuración")
def cmd_config(workspace: str | None, api_url: str | None, reset: bool):
    """Configurar el CLI de KognitoAI."""
    config = CLIConfig.load()
    if reset:
        CLIConfig().save()
        console.print("[success]✅ Configuración reseteada[/success]")
        return
    if workspace:
        config.workspace_id = workspace
        console.print(f"[success]✅ Workspace configurado: {workspace}[/success]")
    if api_url:
        config.api_url = api_url
        console.print(f"[success]✅ URL configurada: {api_url}[/success]")
    config.save()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    cli()


if __name__ == "__main__":
    main()
