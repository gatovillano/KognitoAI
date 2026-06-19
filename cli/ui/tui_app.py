"""
cli/ui/tui_app.py — KognitoAI TUI  (Textual v8+)
Arquitectura: compose() construye todo el árbol; on_mount() carga datos async.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import (
    Button, Footer, Input, Label, ListView, ListItem,
    Static, TextArea,
)

from cli.core.config import CLIConfig
from cli.core.api_client import KognitoAPIClient

LOGO_MINI = "⬡ KognitoAI"


# ── Widget helpers ────────────────────────────────────────────────────────────

class MsgBubble(Widget):
    DEFAULT_CSS = """
    MsgBubble {
        layout: vertical;
        height: auto;
    }
    .msg-header-row {
        layout: horizontal;
        height: 1;
        margin-bottom: 0;
    }
    .msg-body {
        height: auto;
        margin-top: 0;
    }
    """

    def __init__(self, text: str, sender: str, ts: str = "", **kw):
        super().__init__(**kw)
        self._text = text
        self._sender = sender
        self._ts = ts

    def compose(self) -> ComposeResult:
        if self._sender == "user":
            label = "  Tú"
        else:
            label = "  KognitoAI"

        with Horizontal(classes="msg-header-row"):
            yield Static(label, classes="msg-sender")
            if self._ts:
                yield Static(f"  {self._ts}", classes="msg-timestamp")

        from rich.markdown import Markdown as RichMarkdown
        # Render markdown content inside a Static widget
        yield Static(RichMarkdown(self._text), classes="msg-body")


class ThreadItem(ListItem):
    def __init__(self, tid: str, title: str, **kw):
        super().__init__(**kw)
        self.tid = tid
        self.ttitle = title

    def compose(self) -> ComposeResult:
        short = self.ttitle[:22] + "…" if len(self.ttitle) > 24 else self.ttitle
        yield Static(f" 💬 {short}")


# ══════════════════════════════════════════════════════════════════════════════
# Login screen (shown when not authenticated)
# ══════════════════════════════════════════════════════════════════════════════

class LoginScreen(Widget):
    DEFAULT_CSS = """
    LoginScreen {
        align: center middle; background: #0a0e1a; height: 1fr; layout: vertical;
    }
    #lb { width: 58; background: #0f1629; border: solid #6C63FF; padding: 2 4; layout: vertical; align: center middle; }
    #ll { color: #6C63FF; text-style: bold; text-align: center; margin-bottom: 1; }
    #ls { color: #475569; text-align: center; margin-bottom: 2; }
    #le { color: #f87171; text-align: center; height: 1; }
    #login-btn { background: #6C63FF; color: white; border: none; width: 100%; height: 3; margin-top: 1; }
    #login-btn:hover { background: #8b85ff; }
    Input { margin-bottom: 1; background: #1a2035; color: #e2e8f0; border: solid #2d3a56; }
    Input:focus { border: solid #6C63FF; }
    Label { color: #94a3b8; }
    """

    def compose(self) -> ComposeResult:
        with Container(id="lb"):
            yield Static("⬡ KognitoAI CLI", id="ll")
            yield Static("Tu asistente corporativo de IA", id="ls")
            yield Label("Servidor")
            yield Input(placeholder="http://localhost:8000", id="url-in", value="http://localhost:8000")
            yield Label("Email")
            yield Input(placeholder="usuario@empresa.com", id="email-in")
            yield Label("Contraseña")
            yield Input(placeholder="••••••••", id="pass-in", password=True)
            yield Static("", id="le")
            yield Button("  Iniciar Sesión", id="login-btn")


# ══════════════════════════════════════════════════════════════════════════════
# Main TUI App
# ══════════════════════════════════════════════════════════════════════════════

class KognitoTUI(App):
    CSS_PATH = Path(__file__).parent / "app.tcss"

    BINDINGS = [
        Binding("ctrl+n", "new_thread", "Nuevo chat"),
        Binding("ctrl+d", "go_doc",     "Documentos"),
        Binding("ctrl+k", "go_code",    "Código"),
        Binding("ctrl+e", "export",     "Exportar"),
        Binding("ctrl+l", "toggle_sidebar", "Sidebar"),
        Binding("ctrl+q", "quit",       "Salir"),
    ]

    # reactive state
    cur_tab:       reactive[str]           = reactive("chat")
    cur_thread_id: reactive[Optional[str]] = reactive(None)
    cur_title:     reactive[str]           = reactive("Sin conversación")
    loading:       reactive[bool]          = reactive(False)

    def __init__(self):
        super().__init__()
        self.config = CLIConfig.load()
        self.client: Optional[KognitoAPIClient] = None
        self.threads: List[dict] = []

    # ── Compose ───────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield LoginScreen(id="login-screen")

        with Horizontal(id="app-layout"):

            # ── Sidebar ───────────────────────────────────────────────────────
            with Vertical(id="sidebar"):
                with Container(id="sb-header"):
                    yield Static(f" {LOGO_MINI}", id="logo-text")
                    yield Static(" CLI Terminal", id="logo-sub")
                yield Static("  CONVERSACIONES", id="threads-label")
                yield ListView(id="thread-list")
                yield Button("  + Nuevo Chat", id="new-chat-btn")
                with Container(id="sb-footer"):
                    yield Static("  Usuario", id="user-info")

            # ── Content area ──────────────────────────────────────────────────
            with Vertical(id="main-content"):

                # Tab bar
                with Horizontal(id="tab-bar"):
                    yield Button("💬 Chat",      id="tab-chat", classes="tab-btn")
                    yield Button("📝 Documento", id="tab-doc",  classes="tab-btn")
                    yield Button("💻 Código",    id="tab-code", classes="tab-btn")

                # ── Chat panel ────────────────────────────────────────────────
                with Vertical(id="chat-panel"):
                    with Container(id="thread-title-bar"):
                        yield Static("💬  Sin conversación", id="thread-title")
                    yield ScrollableContainer(id="messages-scroll")
                    yield Static("", id="typing-ind")
                    with Horizontal(id="input-bar"):
                        yield Input(
                            placeholder="Escribe tu mensaje… (Enter envía)",
                            id="chat-input",
                        )
                        yield Button("Enviar ▶", id="send-btn")

                # ── Doc panel ─────────────────────────────────────────────────
                with Vertical(id="doc-panel"):
                    with Horizontal(id="doc-toolbar"):
                        yield Button("💾 Guardar",       id="doc-save",   classes="doc-tool-btn")
                        yield Button("📄 Word",          id="doc-word",   classes="doc-tool-btn")
                        yield Button("🖨 PDF",           id="doc-pdf",    classes="doc-tool-btn")
                        yield Button("🤖 Mejorar con IA",id="doc-ai",     classes="doc-tool-btn")
                    yield TextArea(id="doc-editor", language="markdown", theme="monokai")
                    with Horizontal(id="doc-statusbar"):
                        yield Static("Markdown  |  KognitoAI CLI", id="doc-status")

                # ── Code panel ────────────────────────────────────────────────
                with Vertical(id="code-panel"):
                    with Horizontal(id="code-header"):
                        yield Static("💻 Editor de Código", id="code-title")
                        yield Button("📋 Copiar",          id="code-copy",   classes="code-btn")
                        yield Button("📄 Exportar PDF",    id="code-pdf",    classes="code-btn")
                        yield Button("🤖 Revisar con IA",  id="code-ai",     classes="code-btn")
                    yield TextArea(id="code-editor", language="python", theme="monokai")
                    yield Static("Python  |  ln 1  col 0", id="code-status")

        yield Footer()

    # ── Mount ─────────────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        if not self.config.is_authenticated:
            self.query_one("#login-screen").display = True
            self.query_one("#app-layout").display = False
            return
        from cli.core.auth import TokenValidator
        if self.config.token and TokenValidator.is_expired(self.config.token):
            self.notify("⚠️ Tu sesión ha expirado. Por favor inicia sesión nuevamente.", severity="warning")
            self.config.token = None
            self.config.account_id = None
            self.config.save()
            self.query_one("#login-screen").display = True
            self.query_one("#app-layout").display = False
            return

        self.query_one("#login-screen").display = False
        self.query_one("#app-layout").display = True
        self._init_authenticated_flow()

    def _init_authenticated_flow(self) -> None:
        self.client = KognitoAPIClient(self.config.api_url, self.config.token)
        try:
            name = (self.config.name or self.config.email or "Usuario")[:20]
            self.query_one("#user-info", Static).update(f"  {name}")
        except Exception:
            pass
        # Show chat tab, hide others
        self._apply_tab("chat")
        self.load_threads()

    # ── Tab switching ─────────────────────────────────────────────────────────

    def _apply_tab(self, tab: str) -> None:
        self.cur_tab = tab
        for panel_id, tab_id in [
            ("chat-panel", "tab-chat"),
            ("doc-panel",  "tab-doc"),
            ("code-panel", "tab-code"),
        ]:
            try:
                key = panel_id.split("-")[0]
                self.query_one(f"#{panel_id}").display = (key == tab)
                btn = self.query_one(f"#{tab_id}", Button)
                if key == tab:
                    btn.add_class("active")
                else:
                    btn.remove_class("active")
            except Exception:
                pass

    @on(Button.Pressed, "#tab-chat")
    def on_tab_chat(self, _) -> None: self._apply_tab("chat")

    @on(Button.Pressed, "#tab-doc")
    def on_tab_doc(self, _) -> None: self._apply_tab("doc")

    @on(Button.Pressed, "#tab-code")
    def on_tab_code(self, _) -> None: self._apply_tab("code")

    def action_go_doc(self)  -> None: self._apply_tab("doc")
    def action_go_code(self) -> None: self._apply_tab("code")

    # ── Thread loading ────────────────────────────────────────────────────────

    @work(exclusive=False, thread=True)
    async def load_threads(self) -> None:
        if not self.client:
            return
        try:
            data = await self.client.list_threads(limit=30)
            self.threads = data.get("threads", [])
            self.call_from_thread(self._populate_list)
        except Exception as e:
            self.notify(f"Error cargando chats: {e}", severity="error")

    def _populate_list(self) -> None:
        lv = self.query_one("#thread-list", ListView)
        lv.clear()
        for t in self.threads:
            lv.append(ThreadItem(t["id"], t.get("title", "Chat")))
        if self.config.last_thread_id:
            self._open_thread(self.config.last_thread_id, "")

    @on(ListView.Selected, "#thread-list")
    def on_thread_selected(self, ev: ListView.Selected) -> None:
        if isinstance(ev.item, ThreadItem):
            self._open_thread(ev.item.tid, ev.item.ttitle)

    def _open_thread(self, tid: str, title: str) -> None:
        self.cur_thread_id = tid
        self.cur_title = title or tid[:8]
        self.config.last_thread_id = tid
        self.config.save()
        try:
            self.query_one("#thread-title", Static).update(f"💬  {self.cur_title}")
        except Exception:
            pass
        self._fetch_messages(tid)

    @work(exclusive=True, thread=True)
    async def _fetch_messages(self, tid: str) -> None:
        if not self.client:
            return
        try:
            data = await self.client.get_thread_messages(tid, limit=50)
            msgs = data.get("messages", [])
            self.call_from_thread(self._render_msgs, msgs)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    def _render_msgs(self, msgs: list) -> None:
        try:
            scroll = self.query_one("#messages-scroll", ScrollableContainer)
        except Exception:
            return
        scroll.remove_children()
        for m in msgs:
            sender = m.get("sender", "ai")
            text   = m.get("text", "")
            ts = ""
            try:
                raw = str(m.get("created_at", ""))
                if raw:
                    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                    ts = dt.strftime("%H:%M")
            except Exception:
                pass
            scroll.mount(MsgBubble(text, sender, ts,
                                   classes="msg-user" if sender == "user" else "msg-ai"))
        scroll.scroll_end(animate=False)

    # ── Send message ──────────────────────────────────────────────────────────

    @on(Button.Pressed, "#send-btn")
    def on_send(self, _) -> None: self._send()

    @on(Input.Submitted, "#chat-input")
    def on_input_submitted(self, _) -> None: self._send()

    def _send(self) -> None:
        if not self.cur_thread_id:
            self.notify("Selecciona o crea un chat primero", severity="warning")
            return
        try:
            inp = self.query_one("#chat-input", Input)
        except Exception:
            return
        text = inp.value.strip()
        if not text:
            return
        inp.value = ""
        self._add_bubble(text, "user")
        self._do_stream(text)

    def _add_bubble(self, text: str, sender: str) -> None:
        try:
            scroll = self.query_one("#messages-scroll", ScrollableContainer)
            ts = datetime.now().strftime("%H:%M")
            scroll.mount(MsgBubble(text, sender, ts,
                                   classes="msg-user" if sender == "user" else "msg-ai"))
            scroll.scroll_end(animate=True)
        except Exception:
            pass

    @work(exclusive=False, thread=True)
    async def _do_stream(self, message: str) -> None:
        if not self.client:
            return
        self.call_from_thread(self._set_typing, True)
        full = ""
        try:
            async for chunk in self.client.send_message_stream(
                self.cur_thread_id,
                self.config.account_id,
                message,
                self.config.workspace_id,
            ):
                full += chunk
                # live preview in typing indicator
                preview = (full[-120:] if len(full) > 120 else full).replace("\n", " ")
                self.call_from_thread(
                    lambda p=preview: self.query_one("#typing-ind", Static).update(
                        f"[dim #6C63FF]{p}[/]"
                    )
                )
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        finally:
            self.call_from_thread(self._set_typing, False)
            if full:
                self.call_from_thread(self._add_bubble, full, "ai")

    def _set_typing(self, state: bool) -> None:
        try:
            ind = self.query_one("#typing-ind", Static)
            ind.update("[blink bold #6C63FF]  KognitoAI está escribiendo…[/]" if state else "")
            self.query_one("#send-btn", Button).disabled = state
        except Exception:
            pass

    # ── New Thread ────────────────────────────────────────────────────────────

    @on(Button.Pressed, "#new-chat-btn")
    def on_new_chat(self, _) -> None: self.action_new_thread()

    def action_new_thread(self) -> None:
        self._create_thread()

    @work(exclusive=False, thread=True)
    async def _create_thread(self) -> None:
        if not self.client:
            return
        try:
            data = await self.client.create_thread(
                title="Nuevo Chat",
                workspace_id=self.config.workspace_id,
            )
            tid, title = data["id"], data.get("title", "Nuevo Chat")
            self.call_from_thread(self._on_thread_created, tid, title)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    def _on_thread_created(self, tid: str, title: str) -> None:
        try:
            lv = self.query_one("#thread-list", ListView)
            lv.append(ThreadItem(tid, title))
        except Exception:
            pass
        self._open_thread(tid, title)
        self.notify("✅ Nuevo chat creado", timeout=2)

    # ── Doc actions ───────────────────────────────────────────────────────────

    @on(Button.Pressed, "#doc-word")
    def on_doc_word(self, _) -> None: self._export("word")

    @on(Button.Pressed, "#doc-pdf")
    def on_doc_pdf(self, _) -> None: self._export("pdf")

    @on(Button.Pressed, "#doc-save")
    def on_doc_save(self, _) -> None:
        try:
            content = self.query_one("#doc-editor", TextArea).text
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            from cli.core.security import validate_output_path
            path = validate_output_path(f"documento_{ts}.md")
            path.write_text(content, encoding="utf-8")
            self.notify(f"✅ Guardado: {path.name}", timeout=3)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#doc-ai")
    def on_doc_ai(self, _) -> None: self._improve_doc()

    def _export(self, fmt: str) -> None:
        try:
            content = self.query_one("#doc-editor", TextArea).text
        except Exception:
            return
        if not content.strip():
            self.notify("El documento está vacío", severity="warning")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = ".docx" if fmt == "word" else ".pdf"
        from cli.core.security import validate_output_path
        try:
            out = str(validate_output_path(f"documento_{ts}{ext}"))
            from cli.modules.doc_editor import export_to_word, export_to_pdf
            (export_to_word if fmt == "word" else export_to_pdf)(content, out)
            self.notify(f"✅ Exportado: {Path(out).name}", timeout=4)
        except Exception as e:
            self.notify(f"Error exportando: {e}", severity="error")

    def action_export(self) -> None:
        if self.cur_tab == "doc":
            self._export("pdf")
        elif self.cur_tab == "code":
            self._export_code()

    @work(exclusive=False, thread=True)
    async def _improve_doc(self) -> None:
        if not self.client:
            return
        if not self.cur_thread_id:
            self.notify("Abre un chat primero", severity="warning")
            return
        try:
            content = self.query_one("#doc-editor", TextArea).text
        except Exception:
            return
        if not content.strip():
            self.notify("El documento está vacío", severity="warning")
            return
        prompt = f"Mejora este documento en estilo corporativo, manteniendo el formato Markdown:\n\n{content[:3000]}"
        try:
            improved = await self.client.send_message(
                self.cur_thread_id, self.config.account_id, prompt
            )
            self.call_from_thread(
                lambda t=improved: self.query_one("#doc-editor", TextArea).load_text(t)
            )
            self.notify("✅ Documento mejorado", timeout=3)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    # ── Code actions ──────────────────────────────────────────────────────────

    @on(Button.Pressed, "#code-pdf")
    def on_code_pdf(self, _) -> None: self._export_code()

    def _export_code(self) -> None:
        try:
            code = self.query_one("#code-editor", TextArea).text
        except Exception:
            return
        if not code.strip():
            self.notify("El editor está vacío", severity="warning")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        from cli.core.security import validate_output_path
        try:
            out = str(validate_output_path(f"codigo_{ts}.pdf"))
            from cli.modules.doc_editor import export_code_to_pdf
            export_code_to_pdf(code, "python", out)
            self.notify(f"✅ Código exportado: {Path(out).name}", timeout=4)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#code-ai")
    def on_code_ai(self, _) -> None: self._review_code()

    @work(exclusive=False, thread=True)
    async def _review_code(self) -> None:
        if not self.cur_thread_id:
            self.notify("Abre un chat primero", severity="warning")
            return
        try:
            code = self.query_one("#code-editor", TextArea).text
        except Exception:
            return
        if not code.strip():
            self.notify("El editor está vacío", severity="warning")
            return
        prompt = f"Revisa este código, detecta bugs y sugiere mejoras:\n\n```python\n{code[:3000]}\n```"
        try:
            review = await self.client.send_message(
                self.cur_thread_id, self.config.account_id, prompt
            )
            self.call_from_thread(self._add_bubble, review, "ai")
            self._apply_tab("chat")
            self.notify("✅ Revisión enviada al chat", timeout=3)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#code-copy")
    def on_code_copy(self, _) -> None:
        try:
            code = self.query_one("#code-editor", TextArea).text
            import subprocess
            subprocess.run(["xclip", "-selection", "clipboard"], input=code.encode(), check=False)
            self.notify("✅ Código copiado al portapapeles", timeout=2)
        except Exception:
            self.notify("No se pudo copiar (instala xclip)", severity="warning")

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def action_toggle_sidebar(self) -> None:
        try:
            sb = self.query_one("#sidebar")
            sb.display = not sb.display
        except Exception:
            pass

    # ── Login flow ────────────────────────────────────────────────────────────

    @on(Button.Pressed, "#login-btn")
    def on_login_btn(self, _) -> None:
        self._do_login()

    @on(Input.Submitted, "#pass-in")
    def on_pass_submit(self, _) -> None:
        self._do_login()

    @work(exclusive=True, thread=True)
    async def _do_login(self) -> None:
        try:
            url   = self.query_one("#url-in",   Input).value.strip() or self.config.api_url
            email = self.query_one("#email-in", Input).value.strip()
            pwd   = self.query_one("#pass-in",  Input).value
            err   = self.query_one("#le",       Static)
        except Exception:
            return

        if not email or not pwd:
            self.call_from_thread(err.update, "⚠ Email y contraseña requeridos")
            return

        self.call_from_thread(err.update, "  Conectando…")
        try:
            client = await KognitoAPIClient.login(url, email, pwd)
            me     = await client.get_me()
            self.config.api_url   = url
            self.config.token     = client.token
            self.config.account_id = me.get("id") or me.get("account_id", "")
            self.config.email     = email
            self.config.name      = me.get("name", "")
            self.config.save()

            def _switch_views():
                self.query_one("#login-screen").display = False
                self.query_one("#app-layout").display = True
                self._init_authenticated_flow()

            self.call_from_thread(_switch_views)
        except Exception as e:
            self.call_from_thread(err.update, f"❌ {e}")
