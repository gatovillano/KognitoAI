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
}

/**
 * Terminal PTY embebida dentro del chat.
 * Se conecta automáticamente y muestra salida en tiempo real.
 * No tiene botones de toggle/maximizar - controlado por el contenedor.
 */
export default function PtyTerminalEmbedded({
  sessionId,
  accountId,
  token,
  apiBaseUrl,
  initialCommand,
  className,
}: PtyTerminalEmbeddedProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!terminalRef.current) return;

    // Inicializar terminal
    const term = new Terminal({
      cursorBlink: true,
      convertEol: true,
      scrollback: 5000,
      theme: {
        background: "#0d1117",
        foreground: "#e6edf3",
        cursor: "#58a6ff",
        selectionBackground: "#264f78",
        black: "#0d1117",
        red: "#f85142",
        green: "#3fb950",
        yellow: "#d29922",
        blue: "#58a6ff",
        magenta: "#bc8cff",
        cyan: "#39d0d8",
        white: "#e6edf3",
        brightBlack: "#161b22",
        brightRed: "#ff7b72",
        brightGreen: "#a3ff66",
        brightYellow: "#ffdb79",
        brightBlue: "#79c6ff",
        brightMagenta: "#d2a8ff",
        brightCyan: "#57ffff",
        brightWhite: "#ffffff",
      },
      fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
      fontSize: 13,
      lineHeight: 1.2,
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.loadAddon(new WebLinksAddon());

    term.open(terminalRef.current);
    fitAddon.fit();

    termRef.current = term;
    fitAddonRef.current = fitAddon;

    // Conectar WebSocket
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
      console.error("PTY: Error parsing apiBaseUrl, using window.location", e);
    }
    const wsUrl = `${wsProtocol}://${wsHost}/ws/terminal/${accountId}?token=${encodeURIComponent(token)}&session_id=${sessionId}`;
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setError(null);
      if (initialCommand && !sessionId) {
        ws.send(JSON.stringify({ type: "input", data: initialCommand + "\n" }));
      }
      if (fitAddonRef.current && termRef.current) {
        const dims = fitAddonRef.current.proposeDimensions();
        if (dims) {
          ws.send(JSON.stringify({ type: "resize", cols: dims.cols, rows: dims.rows }));
        }
      }
      term.focus();
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "output" && termRef.current) {
          termRef.current.write(msg.data);
        } else if (msg.type === "error" && termRef.current) {
          termRef.current.writeln(`\x1b[31m${msg.data}\x1b[0m`);
        }
      } catch {
        // Mensaje de texto plano
        if (termRef.current) {
          termRef.current.write(event.data);
        }
      }
    };

    ws.onerror = (e) => {
      console.error("PTY WebSocket error:", e);
      setError("Error de conexión con la terminal");
    };

    ws.onclose = () => {
      setIsConnected(false);
      if (termRef.current) {
        termRef.current.writeln("\x1b[33m[Terminal desconectada]\x1b[0m");
      }
    };

    // Enviar datos al escribir en la terminal
    term.onData((data) => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "input", data }));
      }
    });

    // Resize handler
    const resizeHandler = () => {
      if (fitAddonRef.current) {
        fitAddonRef.current.fit();
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "resize", cols: term.cols, rows: term.rows }));
        }
      }
    };

    window.addEventListener("resize", resizeHandler);

    return () => {
      window.removeEventListener("resize", resizeHandler);
      if (ws) {
        ws.close();
      }
      if (term) {
        term.dispose();
      }
    };
  }, [sessionId, accountId, token, apiBaseUrl, initialCommand]);

  return (
    <div className={`relative bg-[#0d1117] rounded-lg overflow-hidden border border-white/10 ${className || ""}`}>
      {/* Header minimal */}
      <div className="flex items-center gap-2 px-3 py-1.5 bg-[#161b22] border-b border-white/5 text-xs font-mono">
        <span className="text-green-400">●</span>
        <span className="text-white/60 flex-1 truncate" title={initialCommand || "Terminal PTY — bash"}>
          {initialCommand ? `PTY: ${initialCommand}` : "Terminal PTY — bash"}
        </span>
        {isConnected ? (
          <span className="text-green-400 text-[10px]">Conectado</span>
        ) : (
          <span className="text-yellow-400 text-[10px]">Conectando...</span>
        )}
      </div>
      
      {/* Terminal container */}
      <div 
        ref={terminalRef} 
        className="h-[280px] w-full cursor-text" 
        onClick={() => termRef.current?.focus()}
      />
      
      {/* Error overlay */}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-red-900/20 text-red-400 text-sm">
          {error}
        </div>
      )}
    </div>
  );
}