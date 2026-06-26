"use client";

import { useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { TerminalSquare, X, ChevronDown, ChevronUp } from "lucide-react";
import { Button } from "@/components/ui/button";

// Importar xterm de forma dinámica (evita SSR – xterm solo funciona en el browser)
const PtyTerminal = dynamic(() => import("./PtyTerminal"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full text-sm text-white/40 font-mono">
      Cargando terminal…
    </div>
  ),
});

interface TerminalPanelProps {
  accountId: string;
  token: string;
  apiBaseUrl?: string;
}

/**
 * Panel flotante de terminal PTY con toggle show/hide.
 * Se puede colocar en cualquier layout del dashboard:
 *
 *   <TerminalPanel accountId={session.accountId} token={session.accessToken} />
 */
export default function TerminalPanel({
  accountId,
  token,
  apiBaseUrl,
}: TerminalPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);

  const handleToggle = useCallback(() => {
    setIsOpen((v) => !v);
    setIsCollapsed(false);
  }, []);

  return (
    <>
      {/* ── Botón flotante de apertura ──────────────────────────────── */}
      {!isOpen && (
        <button
          onClick={handleToggle}
          className="
            fixed bottom-6 right-6 z-40
            flex items-center gap-2 px-4 py-2.5
            rounded-2xl bg-[#0d1117] border border-white/10
            text-white/70 hover:text-white
            shadow-2xl shadow-black/60
            hover:border-white/20 hover:bg-[#161b22]
            transition-all duration-200 group
          "
          title="Abrir terminal PTY"
        >
          <TerminalSquare className="w-4 h-4 group-hover:text-green-400 transition-colors" />
          <span className="text-xs font-mono font-medium">Terminal</span>
        </button>
      )}

      {/* ── Panel de terminal ──────────────────────────────────────── */}
      {isOpen && (
        <div
          className={`
            fixed bottom-0 right-6 z-40
            w-[700px] max-w-[calc(100vw-3rem)]
            rounded-t-2xl overflow-hidden
            border border-white/10 border-b-0
            shadow-2xl shadow-black/80
            transition-all duration-300 ease-in-out
            ${isCollapsed ? "h-10" : "h-[420px]"}
          `}
        >
          {/* Barra superior del panel */}
          <div className="flex items-center gap-2 px-4 py-2 bg-[#161b22] border-b border-white/5 select-none">
            <TerminalSquare className="w-3.5 h-3.5 text-green-400" />
            <span className="text-xs text-white/50 font-mono flex-1">Terminal PTY — bash</span>

            <button
              onClick={() => setIsCollapsed((v) => !v)}
              className="text-white/30 hover:text-white/60 transition-colors p-0.5 rounded"
              title={isCollapsed ? "Expandir" : "Minimizar"}
            >
              {isCollapsed ? (
                <ChevronUp className="w-3.5 h-3.5" />
              ) : (
                <ChevronDown className="w-3.5 h-3.5" />
              )}
            </button>

            <button
              onClick={() => setIsOpen(false)}
              className="text-white/30 hover:text-red-400 transition-colors p-0.5 rounded"
              title="Cerrar"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Terminal xterm (se monta solo cuando está expandido) */}
          {!isCollapsed && (
            <PtyTerminal
              accountId={accountId}
              token={token}
              apiBaseUrl={apiBaseUrl}
              className="h-[380px]"
            />
          )}
        </div>
      )}
    </>
  );
}
