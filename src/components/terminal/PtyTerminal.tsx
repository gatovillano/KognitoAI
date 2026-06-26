"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { WebLinksAddon } from "@xterm/addon-web-links";
import { X, Maximize2, Minimize2, TerminalSquare } from "lucide-react";

interface PtyTerminalProps {
  accountId: string;
  token: string;
  /** URL base del backend, por defecto usa NEXT_PUBLIC_API_URL */
  apiBaseUrl?: string;
  onClose?: () => void;
  className?: string;
  cmd?: string;
  sessionId?: string;
}

/**
 * Terminal PTY interactiva en tiempo real usando xterm.js + WebSocket.
 *
 * Protocolo:
 *   cliente → servidor: JSON { type: "input",  data: "<chars>" }
 *                              { type: "resize", cols: N, rows: N }
 *   servidor → cliente: JSON { type: "output", data: "<text>" }
 *                              { type: "error",  data: "<msg>"  }
 */
export default function PtyTerminal({
  accountId,
  token,
  apiBaseUrl,
  onClose,
  className = "",
  cmd,
  sessionId,
}: PtyTerminalProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<Terminal | null>(null);
  const fitRef = useRef<FitAddon | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);

  // ── Construir URL WebSocket ──────────────────────────────────────────────
  const buildWsUrl = useCallback(() => {
    const base = apiBaseUrl || process.env.NEXT_PUBLIC_API_URL || (typeof window !== "undefined" ? window.location.origin : "http://localhost:8000");
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
      console.error("PTY: Error parsing apiBaseUrl", e);
    }
    let url = `${wsProtocol}://${wsHost}/ws/terminal/${accountId}?token=${encodeURIComponent(token)}`;
    if (cmd) {
      url += `&cmd=${encodeURIComponent(cmd)}`;
    }
    // Si se proporciona sessionId, añadir para enganchar a una sesión PTY existente
    if (sessionId) {
      url += `&session_id=${encodeURIComponent(sessionId)}`;
    }
    return url;
  }, [accountId, token, apiBaseUrl, cmd, sessionId]);

  // ── Inicializar xterm + WebSocket ────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current) return;

    // 1. Crear terminal xterm
    const term = new Terminal({
      cursorBlink: true,
      fontSize: 13,
      fontFamily: '"JetBrains Mono", "Fira Code", "Cascadia Code", monospace',
      theme: {
        background: "#0d1117",
        foreground: "#e6edf3",
        cursor: "#58a6ff",
        selectionBackground: "#388bfd33",
        black: "#21262d",
        red: "#ff7b72",
        green: "#3fb950",
        yellow: "#d29922",
        blue: "#58a6ff",
        magenta: "#bc8cff",
        cyan: "#39c5cf",
        white: "#b1bac4",
        brightBlack: "#6e7681",
        brightRed: "#ffa198",
        brightGreen: "#56d364",
        brightYellow: "#e3b341",
        brightBlue: "#79c0ff",
        brightMagenta: "#d2a8ff",
        brightCyan: "#56d4dd",
        brightWhite: "#f0f6fc",
      },
      allowTransparency: true,
      scrollback: 5000,
      convertEol: true,
    });

    const fit = new FitAddon();
    term.loadAddon(fit);
    term.loadAddon(new WebLinksAddon());
    term.open(containerRef.current);
    fit.fit();

    termRef.current = term;
    fitRef.current = fit;

    // 2. Conectar WebSocket
    const wsUrl = buildWsUrl();
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      term.writeln(
        "\x1b[32m✓ Terminal PTY conectada\x1b[0m\r\n"
      );
      // Enviar tamaño inicial
      const dims = fit.proposeDimensions();
      if (dims) {
        ws.send(JSON.stringify({ type: "resize", cols: dims.cols, rows: dims.rows }));
      }
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "output" && msg.data) {
          term.write(msg.data);
        } else if (msg.type === "error") {
          term.writeln(`\x1b[31m${msg.data}\x1b[0m`);
        }
      } catch {
        // Mensaje binario plano
        term.write(event.data);
      }
    };

    ws.onclose = (ev) => {
      setConnected(false);
      term.writeln(
        `\r\n\x1b[33m⚡ Conexión cerrada${ev.reason ? `: ${ev.reason}` : ""}\x1b[0m`
      );
    };

    ws.onerror = () => {
      setConnected(false);
      term.writeln("\r\n\x1b[31m✗ Error de conexión WebSocket\x1b[0m");
    };

    // 3. Enviar input al PTY
    term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "input", data }));
      }
    });

    // 4. Resize observer para ajustar el PTY cuando cambia el contenedor
    const resizeObserver = new ResizeObserver(() => {
      try {
        fit.fit();
        const dims = fit.proposeDimensions();
        if (dims && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "resize", cols: dims.cols, rows: dims.rows }));
        }
      } catch {
        // ignorar errores de resize si el componente se desmonta
      }
    });
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    return () => {
      resizeObserver.disconnect();
      ws.close();
      term.dispose();
      termRef.current = null;
      fitRef.current = null;
      wsRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accountId, token, sessionId]);

  // ── Toggle maximizar ─────────────────────────────────────────────────────
  const handleMaximize = () => {
    setIsMaximized((v) => !v);
    setTimeout(() => {
      fitRef.current?.fit();
      const dims = fitRef.current?.proposeDimensions();
      if (dims && wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({ type: "resize", cols: dims.cols, rows: dims.rows })
        );
      }
    }, 100);
  };

  return (
    <div
      className={`
        flex flex-col rounded-2xl overflow-hidden border border-white/10
        bg-[#0d1117] shadow-2xl shadow-black/60
        transition-all duration-300
        ${isMaximized ? "fixed inset-4 z-50" : ""}
        ${className}
      `}
    >
      {/* ── Barra de título tipo macOS ──────────────────────────────────── */}
      <div className="flex items-center gap-2 px-4 py-2.5 bg-[#161b22] border-b border-white/5 select-none shrink-0">
        {/* Traffic lights */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={onClose}
            className="w-3 h-3 rounded-full bg-[#ff5f56] hover:brightness-110 transition-all"
            title="Cerrar"
          />
          <div className="w-3 h-3 rounded-full bg-[#ffbd2e]" />
          <button
            onClick={handleMaximize}
            className="w-3 h-3 rounded-full bg-[#27c93f] hover:brightness-110 transition-all"
            title={isMaximized ? "Restaurar" : "Maximizar"}
          />
        </div>

        {/* Título central */}
        <div className="flex-1 flex justify-center items-center gap-1.5">
          <TerminalSquare className="w-3.5 h-3.5 text-white/40" />
          <span className="text-xs text-white/40 font-mono truncate max-w-[400px]" title={cmd || "bash"}>
            {cmd ? `PTY: ${cmd}` : "bash"}
          </span>
          {/* Indicador de estado */}
          <span
            className={`ml-1 w-1.5 h-1.5 rounded-full ${
              connected ? "bg-green-500 animate-pulse" : "bg-red-500/60"
            }`}
          />
        </div>

        {/* Botón maximizar a la derecha */}
        <button
          onClick={handleMaximize}
          className="text-white/30 hover:text-white/70 transition-colors"
          title={isMaximized ? "Restaurar" : "Maximizar"}
        >
          {isMaximized ? (
            <Minimize2 className="w-3.5 h-3.5" />
          ) : (
            <Maximize2 className="w-3.5 h-3.5" />
          )}
        </button>
      </div>

      {/* ── Contenedor xterm ─────────────────────────────────────────────── */}
      <div
        ref={containerRef}
        className="flex-1 min-h-0 p-2"
        style={{ background: "#0d1117" }}
      />
    </div>
  );
}
