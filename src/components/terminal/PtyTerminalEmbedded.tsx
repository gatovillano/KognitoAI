"use client";

import { useEffect, useRef, useState } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { WebLinksAddon } from "@xterm/addon-web-links";
import "@xterm/xterm/css/xterm.css";

interface PtyTerminalEmbeddedProps {
  sessionId: string;
  accountId: string;
  token: string;
  apiBaseUrl?: string;
  initialCommand?: string;
  className?: string;
  /** true mientras el comando sigue en ejecución; false = finalizada (solo lectura) */
  active?: boolean;
}

/**
 * Terminal PTY embebida en el chat, en tiempo real (estilo kogniterm-desktop).
 * - Se monta en cuanto llega tool_start (antes de que termine el comando).
 * - Desplegada y persistente: no colapsada, altura fija, sobrevive al fin
 *   del comando (queda como historial finalizada).
 * - Interactiva: todo lo tecleado se envía por WS al PTY del servidor
 *   (passwords, confirmaciones y/n, Ctrl+C, flechas).
 */
export default function PtyTerminalEmbedded({
  sessionId,
  accountId,
  token,
  apiBaseUrl,
  initialCommand,
  className,
  active = true,
}: PtyTerminalEmbeddedProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<Terminal | null>(null);
  const fitRef = useRef<FitAddon | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const activeRef = useRef(active);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  activeRef.current = active;

  const displayCommand =
    initialCommand && initialCommand !== "terminal_executor"
      ? initialCommand
      : "bash";

  function scrollChatIfFollowing() {
    const scroller = hostRef.current?.closest(
      "[data-chat-scroll]"
    ) as HTMLElement | null;
    // El contenedor de scroll del chat usa ref directa (scrollAreaRef), así
    // que como fallback se busca cualquier ancestro con scroll.
    const el =
      scroller ??
      (hostRef.current?.closest(
        ".overflow-y-auto"
      ) as HTMLElement | null);
    if (!el) return;
    const distanceFromBottom =
      el.scrollHeight - el.scrollTop - el.clientHeight;
    if (distanceFromBottom < 140) {
      el.scrollTo({ top: el.scrollHeight });
    }
  }

  function fitTerminal() {
    const term = termRef.current;
    const fit = fitRef.current;
    if (!term || !fit) return;
    try {
      fit.fit();
      const dims = fit.proposeDimensions();
      const ws = wsRef.current;
      if (dims && ws && ws.readyState === WebSocket.OPEN) {
        ws.send(
          JSON.stringify({ type: "resize", cols: dims.cols, rows: dims.rows })
        );
      }
    } catch {
      /* ignorar errores transitorios de resize */
    }
  }

  async function handleCopy() {
    try {
      const term = termRef.current;
      const selection = term?.getSelection();
      const text =
        selection || (term as any)?.getBuffer?.() || initialCommand || "";
      const toCopy =
        typeof text === "string" ? text : selection || "";
      if (toCopy) {
        await navigator.clipboard.writeText(toCopy);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
    } catch {
      /* portapapeles no disponible */
    }
  }

  function sendCtrlC() {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "input", data: "\x03" }));
    }
  }

  useEffect(() => {
    if (!hostRef.current) return;
    if (!sessionId || !accountId || !token) {
      setError("Faltan credenciales para la terminal");
      return;
    }

    const term = new Terminal({
      cols: 80,
      rows: 16,
      scrollback: 5000,
      cursorBlink: true,
      convertEol: true,
      fontSize: 12,
      fontFamily:
        "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
      theme: {
        background: "#05070d",
        foreground: "#f4f4f5",
        cursor: "#e4e4e7",
        selectionBackground: "rgba(255, 255, 255, 0.28)",
        black: "#0d1117",
        red: "#f85142",
        green: "#3fb950",
        yellow: "#d29922",
        blue: "#58a6ff",
        magenta: "#bc8cff",
        cyan: "#39d0d8",
        white: "#e6edf3",
      },
    });

    const fit = new FitAddon();
    term.loadAddon(fit);
    term.loadAddon(new WebLinksAddon());
    term.open(hostRef.current);
    termRef.current = term;
    fitRef.current = fit;
    fitTerminal();
    // Habilitar/deshabilitar stdin según estado inicial
    term.options.disableStdin = !activeRef.current;

    const base =
      apiBaseUrl ||
      process.env.NEXT_PUBLIC_API_URL ||
      (typeof window !== "undefined" ? window.location.origin : "http://localhost:8000");
    let wsProtocol = "ws";
    let wsHost = "localhost:8000";
    if (typeof window !== "undefined") {
      wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
      wsHost = window.location.host;
    }
    try {
      const url = new URL(base);
      wsProtocol = url.protocol === "https:" ? "wss" : "ws";
      wsHost = url.host;
    } catch (e) {
      console.error("PTY: Error parsing apiBaseUrl, using window.location", e);
    }
    const wsUrl = `${wsProtocol}://${wsHost}/ws/terminal/${accountId}?token=${encodeURIComponent(
      token
    )}&session_id=${encodeURIComponent(sessionId)}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setError(null);
      // El comando ya se está ejecutando en el PTY del servidor
      // (creado por terminal_executor): NO reenviar initialCommand.
      fitTerminal();
      if (activeRef.current) {
        try {
          term.focus();
        } catch {}
      }
    };

    ws.onmessage = (event) => {
      // Ignorar latidos del servidor: no son salida del comando.
      if (event.data === "ping" || event.data === "pong") return;
      try {
        const msg = JSON.parse(event.data);
        // Filtrar por sesión: varias terminales coexisten y el broadcast
        // incluye outputs de todas. Sin session_id (compat) se acepta.
        if (msg.session_id && msg.session_id !== sessionId) return;
        if (msg.type === "output" && msg.data) {
          term.write(msg.data, () => scrollChatIfFollowing());
        } else if (msg.type === "error" && msg.data) {
          term.writeln(`\x1b[31m${msg.data}\x1b[0m`);
        }
      } catch {
        term.write(event.data, () => scrollChatIfFollowing());
      }
    };

    ws.onerror = () => {
      setError("Error de conexión con la terminal");
    };

    ws.onclose = () => {
      setIsConnected(false);
    };

    // Input interactivo: todo lo tecleado va al PTY (solo si sigue activa)
    const dataDisposable = term.onData((data) => {
      const sock = wsRef.current;
      if (activeRef.current && sock && sock.readyState === WebSocket.OPEN) {
        sock.send(JSON.stringify({ type: "input", data }));
      }
    });

    const observer = new ResizeObserver(() => fitTerminal());
    if (hostRef.current) observer.observe(hostRef.current);

    return () => {
      dataDisposable.dispose();
      observer.disconnect();
      try {
        ws.close();
      } catch {}
      wsRef.current = null;
      term.dispose();
      termRef.current = null;
      fitRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, accountId, token, apiBaseUrl]);

  // Reflejar cambios de estado activo/finalizada sin remontar la terminal
  useEffect(() => {
    if (termRef.current) {
      termRef.current.options.disableStdin = !active;
    }
    if (active && isConnected) {
      try {
        termRef.current?.focus();
      } catch {}
    }
    if (!active && termRef.current) {
      termRef.current.writeln("\x1b[33m[Terminal finalizada]\x1b[0m");
    }
  }, [active, isConnected]);

  return (
    <div
      className={`w-full overflow-hidden transition-all ${
        className || ""
      }`}
    >
      {/* Cabecera estilo kogniterm-desktop */}
      <div className="flex items-center gap-2.5 px-4 py-2 text-[12px] select-none">
        <div className="flex items-center gap-1.5 mr-1">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
        </div>

        <span className="text-[11px] font-mono text-slate-400">terminal</span>
        <span
          className="truncate font-mono text-slate-200 text-[11.5px] max-w-sm"
          title={displayCommand}
        >
          $ {displayCommand}
        </span>

        <div className="flex-1" />

        {active && isConnected && (
          <span className="rounded-full bg-amber-500/20 px-2.5 py-0.5 text-[10.5px] font-medium text-amber-200 animate-pulse">
            interactiva: escribe aquí
          </span>
        )}
        {active && !isConnected && (
          <span className="rounded-full bg-emerald-500/20 px-2.5 py-0.5 text-[10.5px] font-medium text-emerald-300">
            {error ? "reconectando" : "ejecutando"}
          </span>
        )}
        {!active && (
          <span className="rounded-full bg-white/[0.05] px-2.5 py-0.5 text-[10.5px] text-slate-400">
            finalizada
          </span>
        )}

        <button
          className={`h-6 px-2.5 rounded-full flex items-center gap-1.5 transition-all text-[11px] font-medium ml-1.5 ${
            copied
              ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
              : "text-slate-400 hover:text-white hover:bg-white/[0.08]"
          }`}
          onClick={handleCopy}
          onMouseDown={(e) => e.preventDefault()}
          title={copied ? "¡Copiado!" : "Copiar contenido de la terminal"}
        >
          {copied ? <span>Copiado</span> : <span>Copiar</span>}
        </button>
      </div>

      <div
        ref={hostRef}
        className="h-56 w-full px-2 py-1 cursor-text select-text"
        onClick={() => active && termRef.current?.focus()}
      />

      {/* Pie de terminal */}
      <div className="flex items-center gap-2 px-4 py-1.5 text-[11px] text-slate-400 select-none">
        {active ? (
          <>
            <span>Envío interactivo activo: flechas, contraseñas y Ctrl+C.</span>
            <div className="flex-1" />
            <button
              className="rounded-full bg-white/[0.08] hover:bg-white/[0.14] px-2.5 py-0.5 text-[11px] font-mono text-slate-200 hover:text-white transition-all active:scale-95"
              title="Enviar señal Ctrl+C (interrumpir)"
              onClick={sendCtrlC}
            >
              Ctrl+C
            </button>
          </>
        ) : (
          <span>Salida de ejecución vinculada al proceso del agente.</span>
        )}
      </div>

      {error && (
        <div className="px-4 py-1.5 text-[11px] text-red-400 bg-red-900/20">
          {error}
        </div>
      )}
    </div>
  );
}
