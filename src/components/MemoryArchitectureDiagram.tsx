'use client';

import React from 'react';
import Link from 'next/link';
import { CircuitBrainLogo } from './CircuitBrainLogo';
import { MessageSquare, Layers, Network, ShieldCheck, Target, Zap, Brain, Rocket, ArrowRight } from 'lucide-react';

export function MemoryArchitectureDiagram() {
  return (
    <section className="w-full max-w-6xl mx-auto flex flex-col items-center gap-10 py-16 px-4">
      {/* Title */}
      <div className="text-center max-w-3xl">
        <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight mb-2">
          Arquitectura de <span className="text-cyan-400">Memoria</span> de <span className="bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">KognitoAI</span>
        </h2>
        <p className="text-slate-400 text-sm">
          Tres niveles. Un conocimiento que evoluciona.
        </p>
      </div>

      {/* Intro Header Banner Card */}
      <div className="w-full max-w-4xl p-5 rounded-2xl bg-slate-900/60 border border-slate-800 flex items-center gap-5 shadow-lg">
        <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shrink-0">
          <CircuitBrainLogo size={36} glow={false} />
        </div>
        <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
          KognitoAI combina memoria <span className="text-cyan-400 font-semibold">conversacional</span>, <span className="text-blue-400 font-semibold">vectorial</span> y <span className="text-purple-400 font-semibold">en grafo</span> para ofrecer respuestas más profundas, relevantes y confiables.
        </p>
      </div>

      {/* Main Architecture Container (ARQUITECTURA HÍBRIDA) */}
      <div className="w-full max-w-4xl p-6 sm:p-8 rounded-3xl bg-slate-950/80 border border-slate-800/90 shadow-2xl relative overflow-hidden flex flex-col gap-8">
        <div className="text-center">
          <span className="text-[10px] uppercase tracking-[0.3em] font-extrabold text-slate-400 block mb-1">
            ARQUITECTURA HÍBRIDA
          </span>
        </div>

        {/* 3 Level Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 relative z-10 items-stretch">
          {/* Level 1: Memoria Conversacional */}
          <div className="flex flex-col items-center text-center p-6 rounded-2xl bg-slate-900/50 border border-slate-800 hover:border-cyan-500/40 transition-all group">
            <span className="text-[9px] font-mono text-cyan-400 uppercase tracking-widest mb-1 font-bold">NIVEL 1</span>
            <h4 className="text-xs font-bold text-white mb-4">Memoria Conversacional</h4>
            <div className="w-16 h-16 rounded-full bg-cyan-500/10 border border-cyan-500/40 flex items-center justify-center text-cyan-400 mb-4 group-hover:scale-105 transition-transform shadow-[0_0_15px_rgba(6,182,212,0.2)]">
              <MessageSquare size={26} />
            </div>
            <span className="text-xs font-extrabold text-cyan-400 mb-2">PostgreSQL</span>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Guarda el historial completo de conversaciones para contexto inmediato y continuidad.
            </p>
          </div>

          {/* Level 2: Memoria Vectorial */}
          <div className="flex flex-col items-center text-center p-6 rounded-2xl bg-slate-900/50 border border-slate-800 hover:border-blue-500/40 transition-all group">
            <span className="text-[9px] font-mono text-blue-400 uppercase tracking-widest mb-1 font-bold">NIVEL 2</span>
            <h4 className="text-xs font-bold text-white mb-4">Memoria Vectorial</h4>
            <div className="w-16 h-16 rounded-full bg-blue-500/10 border border-blue-500/40 flex items-center justify-center text-blue-400 mb-4 group-hover:scale-105 transition-transform shadow-[0_0_15px_rgba(59,130,246,0.2)]">
              <Layers size={26} />
            </div>
            <span className="text-xs font-extrabold text-blue-400 mb-2">PGVector</span>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Buscar y recuperar información semántica relevante con búsqueda híbrida y embeddings.
            </p>
          </div>

          {/* Level 3: Memoria en Grafo */}
          <div className="flex flex-col items-center text-center p-6 rounded-2xl bg-slate-900/50 border border-slate-800 hover:border-purple-500/40 transition-all group">
            <span className="text-[9px] font-mono text-purple-400 uppercase tracking-widest mb-1 font-bold">NIVEL 3</span>
            <h4 className="text-xs font-bold text-white mb-4">Memoria en Grafo</h4>
            <div className="w-16 h-16 rounded-full bg-purple-500/10 border border-purple-500/40 flex items-center justify-center text-purple-400 mb-4 group-hover:scale-105 transition-transform shadow-[0_0_15px_rgba(168,85,247,0.2)]">
              <Network size={26} />
            </div>
            <span className="text-xs font-extrabold text-purple-400 mb-2">Neo4j</span>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Organiza el conocimiento en relaciones semánticas y descubre conexiones latentes.
            </p>
          </div>
        </div>

        {/* Transfer Bar (TRANSFERENCIA AUTOMÁTICA) */}
        <div className="pt-4 border-t border-slate-800/80 flex flex-col items-center text-center gap-1.5">
          <span className="text-[10px] font-extrabold text-cyan-400 uppercase tracking-widest">
            TRANSFERENCIA AUTOMÁTICA
          </span>
          <p className="text-xs text-slate-400">
            La información fluye entre niveles para mantenerse actualizada, enriquecida y siempre disponible.
          </p>
        </div>
      </div>

      {/* Key Benefits Grid (BENEFICIOS CLAVE) */}
      <div className="w-full max-w-4xl p-6 sm:p-8 rounded-3xl bg-slate-950/80 border border-slate-800/90 shadow-2xl flex flex-col gap-6">
        <div className="text-center">
          <span className="text-[10px] uppercase tracking-[0.3em] font-extrabold text-slate-400 block">
            BENEFICIOS CLAVE
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Menos alucinaciones */}
          <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 flex flex-col items-center text-center gap-2">
            <div className="p-3 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
              <ShieldCheck size={20} />
            </div>
            <span className="text-xs font-bold text-cyan-400">Menos alucinaciones</span>
            <span className="text-[11px] text-slate-400">Conocimiento verificado y estructurado.</span>
          </div>

          {/* Mayor precisión */}
          <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 flex flex-col items-center text-center gap-2">
            <div className="p-3 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/30">
              <Target size={20} />
            </div>
            <span className="text-xs font-bold text-blue-400">Mayor precisión</span>
            <span className="text-[11px] text-slate-400">Recuperación semántica y relaciones inteligentes.</span>
          </div>

          {/* Contexto persistente */}
          <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 flex flex-col items-center text-center gap-2">
            <div className="p-3 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/30">
              <Zap size={20} />
            </div>
            <span className="text-xs font-bold text-purple-400">Contexto persistente</span>
            <span className="text-[11px] text-slate-400">Memoria a largo plazo en múltiples niveles.</span>
          </div>

          {/* Aprendizaje continuo */}
          <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 flex flex-col items-center text-center gap-2">
            <div className="p-3 rounded-full bg-pink-500/10 text-pink-400 border border-pink-500/30">
              <Brain size={20} />
            </div>
            <span className="text-xs font-bold text-pink-400">Aprendizaje continuo</span>
            <span className="text-[11px] text-slate-400">El sistema evoluciona con cada interacción.</span>
          </div>
        </div>
      </div>

      {/* Footer Pill CTA Banner */}
      <div className="w-full max-w-4xl p-4 sm:p-5 rounded-full bg-slate-950 border border-purple-500/50 hover:border-cyan-400 transition-all flex flex-col sm:flex-row items-center justify-between gap-4 px-8 shadow-[0_0_20px_rgba(168,85,247,0.2)]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 flex items-center justify-center">
            <Rocket size={18} />
          </div>
          <span className="text-xs sm:text-sm font-bold text-slate-200">
            Activa el exocerebro de tu equipo.
          </span>
        </div>
        <Link href="/beta" className="flex items-center gap-3 text-xs text-cyan-400 hover:text-white font-mono transition-colors">
          <span>Conoce más en <strong className="text-purple-400">kognitoai.cloud</strong></span>
          <div className="w-7 h-7 rounded-full bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <ArrowRight size={14} />
          </div>
        </Link>
      </div>
    </section>
  );
}
