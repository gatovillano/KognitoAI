"""
browser_use_skill — automatización de navegador para KognitoAI.

Implementación sobre **Playwright** (ya instalado en el proyecto) en lugar del
CLI `browser-use`, que nunca estuvo instalado y hacía que todas las acciones
devolvieran "browser-use command not found" sin abrir ningún navegador.

La sesión del navegador es persistente y vive en un hilo dedicado con su propio
event loop, de modo que las llamadas sucesivas (open -> state -> click -> ...)
reutilizan la misma pestaña en lugar de relanzar el navegador cada vez.
"""

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Any, Optional
import asyncio
import json
import os
import threading
import time


# --------------------------------------------------------------------------- #
# Configuración
# --------------------------------------------------------------------------- #
def _is_headless() -> bool:
    """Headless por defecto salvo que se pida lo contrario o que exista DISPLAY."""
    env = os.getenv("BROWSER_USE_HEADLESS")
    if env is not None:
        return env.strip().lower() not in ("0", "false", "no", "")
    return not (os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY"))


def _screenshot_dir() -> str:
    candidates = [
        os.getenv("BROWSER_USE_SCREENSHOT_DIR"),
        os.path.join(os.getcwd(), ".playwright-mcp"),
        "/tmp",
    ]
    for c in candidates:
        if c and os.path.isdir(c):
            return c
    return "/tmp"


# --------------------------------------------------------------------------- #
# Hilo dedicado con su propio event loop (evita conflictos con el loop del
# servidor MCP / FastAPI, que ya puede estar corriendo).
# --------------------------------------------------------------------------- #
class _BrowserSession:
    def __init__(self) -> None:
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._playwright = None
        self._browser = None
        self._context = None
        self._pages: list = []
        self._active_index = 0

    # -- gestión del hilo ------------------------------------------------- #
    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is not None and not self._loop.is_closed():
            return self._loop
        ready = threading.Event()

        def _run_loop() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            ready.set()
            loop.run_forever()

        self._thread = threading.Thread(
            target=_run_loop, daemon=True, name="BrowserUseLoop"
        )
        self._thread.start()
        ready.wait(timeout=10)
        if self._loop is None:
            raise RuntimeError("No se pudo inicializar el event loop del navegador.")
        return self._loop

    def run(self, coro, timeout: float = 120.0):
        """Ejecuta una corrutina en el hilo dedicado y devuelve su resultado."""
        loop = self._ensure_loop()
        fut = asyncio.run_coroutine_threadsafe(coro, loop)
        return fut.result(timeout=timeout)

    # -- ciclo de vida del navegador -------------------------------------- #
    async def _ensure_browser(self):
        if self._browser is not None and self._browser.is_connected():
            if self._context is None or len(self._pages) == 0:
                await self._new_context()
            return

        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=_is_headless(),
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        await self._new_context()

    async def _new_context(self) -> None:
        self._context = await self._browser.new_context(viewport={"width": 1280, "height": 800})
        self._pages = [await self._context.new_page()]
        self._active_index = 0

    @property
    def page(self):
        if not self._pages:
            raise RuntimeError("No hay ninguna pestaña abierta. Usa primero action='open'.")
        return self._pages[self._active_index]

    async def close(self) -> None:
        for closer in (self._context, self._browser, self._playwright):
            if closer is None:
                continue
            try:
                await (closer.stop() if hasattr(closer, "stop") else closer.close())
            except Exception:
                pass
        self._context = self._browser = self._playwright = None
        self._pages = []


_SESSION = _BrowserSession()


# --------------------------------------------------------------------------- #
# Esquema de entrada (idéntico al histórico para no romper el cache MCP)
# --------------------------------------------------------------------------- #
class BrowserUseInput(BaseModel):
    """Input for browser-use skill"""
    action: str = Field(description="Action to perform: 'open', 'state', 'click', 'input', 'type', 'screenshot', 'close', 'back', 'scroll_down', 'scroll_up', 'tab_list', 'tab_new', 'tab_switch', 'tab_close', 'get_title', 'get_html', 'get_text', 'wait', 'cookies_get', 'cookies_set', 'cookies_clear', 'eval'")
    url: Optional[str] = Field(default=None, description="URL to navigate to (for 'open' action)")
    element_index: Optional[int] = Field(default=None, description="Element index for click/input (from state)")
    text: Optional[str] = Field(default=None, description="Text to type or input")
    path: Optional[str] = Field(default=None, description="Path for screenshot")
    amount: Optional[int] = Field(default=None, description="Scroll amount in pixels")
    tab_index: Optional[int] = Field(default=None, description="Tab index for switch/close")
    selector: Optional[str] = Field(default=None, description="CSS selector for wait or get_html")
    javascript: Optional[str] = Field(default=None, description="JavaScript code for eval action")
    domain: Optional[str] = Field(default=None, description="Domain for cookies")
    name: Optional[str] = Field(default=None, description="Cookie name")
    value: Optional[str] = Field(default=None, description="Cookie value")
    timeout: Optional[int] = Field(default=30000, description="Timeout in milliseconds")


# --------------------------------------------------------------------------- #
# Acciones (async, se ejecutan en el hilo dedicado)
# --------------------------------------------------------------------------- #
_SCAN_JS = """
() => {
  const sel = 'a, button, input, textarea, select, [role=button], [onclick], [contenteditable=true]';
  const nodes = Array.from(document.querySelectorAll(sel));
  nodes.forEach((el, i) => el.setAttribute('data-bu-idx', String(i)));
  return nodes.map((el, i) => {
    const label = (el.innerText || el.value || el.getAttribute('aria-label') ||
                   el.getAttribute('placeholder') || el.getAttribute('name') || '').trim();
    return { index: i, tag: el.tagName.toLowerCase(), text: label.slice(0, 120),
             id: el.id || null, name: el.getAttribute('name') || null };
  });
}
"""


async def _do_open(url: str) -> str:
    page = _SESSION.page
    await page.goto(url, wait_until="domcontentloaded", timeout=45000)
    title = await page.title()
    return f"Navegado a {page.url}\nTítulo: {title}"


async def _do_state() -> str:
    page = _SESSION.page
    await page.wait_for_load_state("domcontentloaded")
    items = await page.evaluate(_SCAN_JS)
    lines = [f"URL: {page.url}", f"Página: {await page.title()}", f"Elementos interactivos: {len(items)}"]
    for it in items[:80]:
        lines.append(f"  [{it['index']}] <{it['tag']}> {it['text']}")
    if len(items) > 80:
        lines.append(f"  ... y {len(items) - 80} más")
    return "\n".join(lines)


async def _do_click(index: int) -> str:
    page = _SESSION.page
    locator = page.locator(f"[data-bu-idx='{index}']")
    if await locator.count() == 0:
        return (
            f"Error: no existe el elemento con índice {index}. "
            "Ejecuta action='state' para obtener los índices actualizados."
        )
    await locator.first.scroll_into_view_if_needed(timeout=10000)
    await locator.first.click(timeout=20000)
    await page.wait_for_load_state("domcontentloaded")
    return f"Clic en elemento [{index}]. URL actual: {page.url}"


async def _do_input(index: int, text: str, clear: bool = True) -> str:
    page = _SESSION.page
    locator = page.locator(f"[data-bu-idx='{index}']")
    if await locator.count() == 0:
        return f"Error: no existe el elemento con índice {index}. Ejecuta action='state' primero."
    el = locator.first
    if clear:
        try:
            await el.fill("", timeout=10000)
        except Exception:
            pass
    await el.type(text, delay=20, timeout=20000)
    return f"Texto escrito en [{index}]: {text!r}"


async def _do_screenshot(path: Optional[str]) -> str:
    page = _SESSION.page
    target = path or os.path.join(_screenshot_dir(), f"browser-{int(time.time() * 1000)}.png")
    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
    await page.screenshot(path=target, full_page=False)
    return f"Captura guardada en {target}"


async def _do_back() -> str:
    page = _SESSION.page
    await page.go_back(wait_until="domcontentloaded")
    return f"Navegado atrás. URL actual: {page.url}"


async def _do_scroll(amount: int, down: bool) -> str:
    page = _SESSION.page
    await page.mouse.wheel(0, amount if down else -amount)
    await asyncio.sleep(0.4)
    y = await page.evaluate("window.scrollY")
    return f"Scroll {'hacia abajo' if down else 'hacia arriba'} ({amount}px). scrollY={y}"


async def _do_tab_list() -> str:
    lines = []
    for i, p in enumerate(_SESSION._pages):
        mark = "*" if i == _SESSION._active_index else " "
        lines.append(f"{mark} [{i}] {p.url}")
    return "\n".join(lines) or "No hay pestañas abiertas."


async def _do_tab_new(url: Optional[str]) -> str:
    await _SESSION._ensure_browser()
    page = await _SESSION._context.new_page()
    if url:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
    _SESSION._pages.append(page)
    _SESSION._active_index = len(_SESSION._pages) - 1
    return f"Nueva pestaña abierta ({page.url}). Índice: {_SESSION._active_index}"


async def _do_tab_switch(index: int) -> str:
    if index < 0 or index >= len(_SESSION._pages):
        return f"Error: índice de pestaña {index} fuera de rango (hay {len(_SESSION._pages)})."
    _SESSION._active_index = index
    return f"Pestaña activa: [{index}] {_SESSION._pages[index].url}"


async def _do_tab_close(index: Optional[int]) -> str:
    idx = _SESSION._active_index if index is None else index
    if idx < 0 or idx >= len(_SESSION._pages):
        return f"Error: índice de pestaña {idx} fuera de rango (hay {len(_SESSION._pages)})."
    page = _SESSION._pages.pop(idx)
    try:
        await page.close()
    except Exception:
        pass
    if not _SESSION._pages:
        await _SESSION._new_context()
        return "Se cerró la última pestaña; se abrió una nueva."
    _SESSION._active_index = min(idx, len(_SESSION._pages) - 1)
    return f"Pestaña [{idx}] cerrada. Ahora activa: {_SESSION.page.url}"


async def _do_get_html(selector: Optional[str]) -> str:
    page = _SESSION.page
    html = await page.evaluate(
        "(sel) => sel ? (document.querySelector(sel)?.outerHTML ?? 'Selector no encontrado: ' + sel) : document.documentElement.outerHTML",
        selector,
    )
    if len(html) > 20000:
        return html[:20000] + f"\n... [truncado, {len(html)} chars totales]"
    return html


async def _do_get_text() -> str:
    return await _SESSION.page.evaluate("document.body ? document.body.innerText : ''")


async def _do_wait(selector: str, timeout_ms: int) -> str:
    try:
        await _SESSION.page.wait_for_selector(selector, timeout=timeout_ms)
        return f"Elemento '{selector}' apareció."
    except Exception as e:
        return f"Timeout: el elemento '{selector}' no apareció en {timeout_ms} ms ({e})"


async def _do_cookies_get(url: Optional[str]) -> str:
    cookies = await _SESSION._context.cookies(url) if url else await _SESSION._context.cookies()
    return json.dumps(
        [{k: c[k] for k in ("name", "value", "domain", "path", "expires")} for c in cookies],
        ensure_ascii=False,
        indent=2,
    )


async def _do_cookies_set(domain: str, name: str, value: str) -> str:
    await _SESSION._context.add_cookies(
        [{"name": name, "value": value, "domain": domain, "path": "/"}]
    )
    return f"Cookie '{name}' establecida para {domain}."


async def _do_cookies_clear(url: Optional[str]) -> str:
    cookies = await _SESSION._context.cookies(url) if url else await _SESSION._context.cookies()
    await _SESSION._context.clear_cookies()
    return f"{len(cookies)} cookies eliminadas."


async def _do_eval(javascript: str) -> str:
    result = await _SESSION.page.evaluate(javascript)
    if isinstance(result, (dict, list)):
        return json.dumps(result, ensure_ascii=False, indent=2)
    return str(result)


# --------------------------------------------------------------------------- #
# Tool
# --------------------------------------------------------------------------- #
class BrowserUseSkill(BaseTool):
    name: str = "browser_use_skill"
    description: str = """Browser automation skill for web testing, form filling, screenshots, and data extraction.
Use when the user needs to navigate websites, interact with web pages, fill forms, take screenshots, or extract information from web pages.
IMPORTANT: call action='state' before 'click'/'input' to obtain valid element indexes.

Actions:
- open: Navigate to URL
- state: Get current page state with clickable elements
- click: Click element by index
- input/type: Type text
- screenshot: Take screenshot
- close: Close browser
- back: Go back in history
- scroll_down/scroll_up: Scroll page
- tab_list/tab_new/tab_switch/tab_close: Tab management
- get_title/get_html/get_text: Extract data
- wait: Wait for element/text
- cookies_get/set/clear: Cookie management
- eval: Execute JavaScript"""
    args_schema: Type[BaseModel] = BrowserUseInput

    def _run(self, action: str, **kwargs) -> str:
        """Execute browser automation commands (Playwright)."""
        timeout_ms = kwargs.get("timeout") or 30000
        try:
            timeout_s = max(30.0, min(float(timeout_ms) / 1000.0 + 30.0, 180.0))
        except Exception:
            timeout_s = 60.0

        try:
            with _SESSION._lock:
                return self._dispatch(action, kwargs, timeout_ms)
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    def _dispatch(self, action: str, kwargs: dict, timeout_ms: int) -> str:
        run = _SESSION.run

        if action == "open":
            url = kwargs.get("url")
            if not url:
                return "Error: URL is required for 'open' action"
            if not url.startswith(("http://", "https://", "about:", "file:")):
                url = "https://" + url
            run(_SESSION._ensure_browser())
            return run(_do_open(url), timeout_s)

        if action == "state":
            run(_SESSION._ensure_browser())
            return run(_do_state(), timeout_s)

        if action == "click":
            idx = kwargs.get("element_index")
            if idx is None:
                return "Error: element_index is required for 'click' action"
            run(_SESSION._ensure_browser())
            return run(_do_click(int(idx)), timeout_s)

        if action in ("input", "type"):
            idx, text = kwargs.get("element_index"), kwargs.get("text")
            if idx is None:
                return "Error: element_index is required for 'input' action"
            if not text:
                return "Error: text is required for 'input' action"
            run(_SESSION._ensure_browser())
            return run(_do_input(int(idx), str(text)), timeout_s)

        if action == "screenshot":
            run(_SESSION._ensure_browser())
            return run(_do_screenshot(kwargs.get("path")), timeout_s)

        if action == "close":
            run(_SESSION.close(), timeout_s)
            return "Navegador cerrado."

        if action == "back":
            run(_SESSION._ensure_browser())
            return run(_do_back(), timeout_s)

        if action in ("scroll_down", "scroll_up"):
            run(_SESSION._ensure_browser())
            return run(
                _do_scroll(int(kwargs.get("amount") or 500), action == "scroll_down"),
                timeout_s,
            )

        if action == "tab_list":
            run(_SESSION._ensure_browser())
            return run(_do_tab_list(), timeout_s)

        if action == "tab_new":
            run(_SESSION._ensure_browser())
            return run(_do_tab_new(kwargs.get("url")), timeout_s)

        if action == "tab_switch":
            idx = kwargs.get("tab_index")
            if idx is None:
                return "Error: tab_index is required for 'tab_switch' action"
            run(_SESSION._ensure_browser())
            return run(_do_tab_switch(int(idx)), timeout_s)

        if action == "tab_close":
            run(_SESSION._ensure_browser())
            return run(_do_tab_close(kwargs.get("tab_index")), timeout_s)

        if action == "get_title":
            run(_SESSION._ensure_browser())
            return run(_SESSION.page.title(), timeout_s)

        if action == "get_html":
            run(_SESSION._ensure_browser())
            return run(_do_get_html(kwargs.get("selector")), timeout_s)

        if action == "get_text":
            run(_SESSION._ensure_browser())
            return run(_do_get_text(), timeout_s)

        if action == "wait":
            selector = kwargs.get("selector")
            if not selector:
                return "Error: selector is required for 'wait' action"
            run(_SESSION._ensure_browser())
            return run(_do_wait(selector, timeout_ms), timeout_s)

        if action == "cookies_get":
            run(_SESSION._ensure_browser())
            return run(_do_cookies_get(kwargs.get("url")), timeout_s)

        if action == "cookies_set":
            domain, name, value = kwargs.get("domain"), kwargs.get("name"), kwargs.get("value")
            if not all([domain, name, value]):
                return "Error: domain, name, and value are required for 'cookies_set' action"
            run(_SESSION._ensure_browser())
            return run(_do_cookies_set(domain, name, value), timeout_s)

        if action == "cookies_clear":
            run(_SESSION._ensure_browser())
            return run(_do_cookies_clear(kwargs.get("url")), timeout_s)

        if action == "eval":
            js = kwargs.get("javascript")
            if not js:
                return "Error: javascript is required for 'eval' action"
            run(_SESSION._ensure_browser())
            return run(_do_eval(js), timeout_s)

        return f"Error: Unknown action '{action}'"


# For use as a direct tool
def browser_use_action(action: str, **kwargs) -> str:
    """Helper function to use browser automation"""
    tool = BrowserUseSkill()
    return tool._run(action, **kwargs)
