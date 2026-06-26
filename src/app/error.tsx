'use client';

import React, { useEffect } from 'react';
import { motion } from 'framer-motion';
import { AlertOctagon, RotateCcw, Home, ArrowLeft, Terminal } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function GlobalError({ error, reset }: ErrorProps) {
  const router = useRouter();

  useEffect(() => {
    // Loguear el error a la consola o a un servicio de monitoreo en producción
    console.error('Kognito AI Global Error Captured:', error);
  }, [error]);

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-6 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-zinc-950 via-purple-950/20 to-black text-foreground relative overflow-hidden select-none">
      
      {/* Elementos ambientales de fondo */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-purple-600/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 left-1/3 w-[300px] h-[300px] bg-indigo-500/5 rounded-full blur-[100px] pointer-events-none" />
      
      <motion.div 
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="w-full max-w-xl backdrop-blur-xl bg-zinc-900/40 border border-zinc-800/80 rounded-2xl p-8 md:p-10 shadow-2xl relative z-10 flex flex-col items-center text-center"
      >
        {/* Ícono animado futurista */}
        <div className="relative mb-6">
          <motion.div 
            animate={{ 
              scale: [1, 1.05, 1],
              opacity: [0.8, 1, 0.8]
            }}
            transition={{ 
              duration: 3, 
              repeat: Infinity,
              ease: "easeInOut"
            }}
            className="absolute inset-0 rounded-full bg-purple-500/20 blur-md"
          />
          <div className="w-16 h-16 rounded-full bg-purple-500/10 border border-purple-500/30 flex items-center justify-center relative z-10 text-purple-400">
            <AlertOctagon size={32} className="stroke-[1.5]" />
          </div>
        </div>

        {/* Títulos */}
        <h1 className="text-3xl font-bold tracking-tight text-white mb-3">
          Error en la Matrix Cognitiva
        </h1>
        <p className="text-zinc-400 max-w-md text-sm md:text-base mb-8 leading-relaxed">
          Kognito AI detectó una anomalía inesperada al cargar este componente. La sesión de red o el flujo del sistema se ha visto interrumpido de forma segura.
        </p>

        {/* Botones de acción premium */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full mb-8">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => reset()}
            className="flex items-center justify-center gap-2 py-3 px-5 rounded-xl font-medium bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-600/20 border border-purple-500/30 transition-colors"
          >
            <RotateCcw size={18} />
            Reintentar Acción
          </motion.button>
          
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => router.push('/')}
            className="flex items-center justify-center gap-2 py-3 px-5 rounded-xl font-medium bg-zinc-800/80 hover:bg-zinc-800 text-zinc-200 border border-zinc-700/60 transition-colors"
          >
            <Home size={18} />
            Volver al Inicio
          </motion.button>
        </div>

        {/* Botón secundario para regresar */}
        <button 
          onClick={() => window.history.back()}
          className="flex items-center gap-2 text-zinc-500 hover:text-zinc-300 text-sm transition-colors mb-6 group"
        >
          <ArrowLeft size={16} className="transform group-hover:-translate-x-0.5 transition-transform" />
          Regresar a la página anterior
        </button>

        {/* Panel técnico colapsable (Consola del Sistema) */}
        <div className="w-full text-left">
          <details className="group border border-zinc-800/40 rounded-xl overflow-hidden bg-black/20">
            <summary className="flex items-center justify-between p-3.5 text-xs text-zinc-500 hover:text-zinc-300 cursor-pointer transition-colors font-medium list-none [&::-webkit-details-marker]:hidden">
              <span className="flex items-center gap-2">
                <Terminal size={14} className="text-zinc-600" />
                Detalles Técnicos del Sistema
              </span>
              <span className="text-[10px] bg-zinc-800/60 text-zinc-400 px-2 py-0.5 rounded border border-zinc-700/30 group-open:hidden">
                Mostrar
              </span>
              <span className="text-[10px] bg-purple-950/40 text-purple-300 px-2 py-0.5 rounded border border-purple-900/30 hidden group-open:inline">
                Ocultar
              </span>
            </summary>
            
            <div className="p-4 border-t border-zinc-800/40 font-mono text-[11px] text-zinc-400 bg-zinc-950/80 overflow-x-auto max-h-[150px] leading-relaxed">
              <div className="text-red-400 font-semibold mb-1">
                [EXCEPCIÓN_CAPTURADA]
              </div>
              <div className="text-zinc-300">{error.name || 'Error'}: {error.message || 'No message provided'}</div>
              {error.digest && (
                <div className="text-zinc-500 mt-1">
                  ID del Error: <span className="text-purple-400">{error.digest}</span>
                </div>
              )}
              {error.stack && (
                <pre className="mt-2 text-zinc-500 leading-normal text-[10px] max-w-full">
                  {error.stack}
                </pre>
              )}
            </div>
          </details>
        </div>

      </motion.div>
    </div>
  );
}
