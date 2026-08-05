'use client';

import React from 'react';
import Link from 'next/link';
import { CircuitBrainLogo } from './CircuitBrainLogo';
import { Landmark, FileText, UserCheck, Users, Scale, Database, Shield, MessageSquare, Globe, ArrowRight } from 'lucide-react';

export function PublicSectorDiagram() {
  return (
    <section className="w-full max-w-6xl mx-auto flex flex-col items-center gap-10 py-16 px-4">
      {/* Header */}
      <div className="w-full text-left">
        <span className="text-xs font-extrabold uppercase tracking-[0.25em] text-slate-400 block mb-1">
          CASO DE USO
        </span>
        <h2 className="text-3xl sm:text-4xl md:text-5xl font-black text-white tracking-tight mb-2">
          INSTITUCIONES <span className="bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-400 bg-clip-text text-transparent">PÚBLICAS</span>
        </h2>
        <div className="w-20 h-0.5 bg-gradient-to-r from-cyan-400 to-purple-500 rounded-full mb-4" />
        <p className="text-slate-300 text-sm sm:text-base">
          Más conocimiento institucional. Mejores <span className="text-purple-400 font-semibold">decisiones públicas</span>.
        </p>
      </div>

      {/* Main Diagram & Features Box */}
      <div className="w-full p-6 sm:p-10 rounded-3xl bg-slate-950/80 border border-slate-800/90 shadow-2xl relative overflow-hidden flex flex-col gap-10">
        <div className="absolute top-0 left-1/4 w-80 h-80 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />

        {/* Top Graphic: Building -> Central Brain -> 4 Nodes */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center relative z-10 py-4">
          
          {/* Left: Building Graphic */}
          <div className="lg:col-span-4 flex flex-col items-center justify-center p-8 rounded-2xl bg-slate-900/40 border border-slate-800/80 relative">
            <div className="w-20 h-20 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 mb-3 shadow-[0_0_20px_rgba(6,182,212,0.2)]">
              <Landmark size={40} />
            </div>
            <span className="text-xs font-bold text-white uppercase tracking-wider">Institución</span>
            <span className="text-[10px] text-slate-400">Sector Público & Gobierno</span>
          </div>

          {/* Center: Glowing Circuit Brain Core */}
          <div className="lg:col-span-4 flex flex-col items-center justify-center relative">
            <div className="p-5 rounded-full bg-slate-900 border border-purple-500/40 shadow-[0_0_35px_rgba(168,85,247,0.3)]">
              <CircuitBrainLogo size={80} />
            </div>
          </div>

          {/* Right: 4 Branching Output Nodes */}
          <div className="lg:col-span-4 flex flex-col gap-3">
            {/* Expedientes */}
            <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-cyan-500/40 transition-all">
              <span className="text-xs font-bold text-slate-200 uppercase tracking-wider">EXPEDIENTES</span>
              <div className="w-9 h-9 rounded-full bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
                <FileText size={16} />
              </div>
            </div>

            {/* Ciudadanos */}
            <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-blue-500/40 transition-all">
              <span className="text-xs font-bold text-slate-200 uppercase tracking-wider">CIUDADANOS</span>
              <div className="w-9 h-9 rounded-full bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
                <UserCheck size={16} />
              </div>
            </div>

            {/* Equipos */}
            <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-purple-500/40 transition-all">
              <span className="text-xs font-bold text-slate-200 uppercase tracking-wider">EQUIPOS</span>
              <div className="w-9 h-9 rounded-full bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400">
                <Users size={16} />
              </div>
            </div>

            {/* Normativa */}
            <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-indigo-500/40 transition-all">
              <span className="text-xs font-bold text-slate-200 uppercase tracking-wider">NORMATIVA</span>
              <div className="w-9 h-9 rounded-full bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                <Scale size={16} />
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Feature List Points */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-6 border-t border-slate-800/80">
          <div className="flex items-center gap-3 p-3.5 rounded-xl bg-slate-900/40 border border-slate-800/60">
            <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 shrink-0">
              <Database size={18} />
            </div>
            <span className="text-xs text-slate-300">Centraliza <strong className="text-cyan-400">información</strong> institucional</span>
          </div>

          <div className="flex items-center gap-3 p-3.5 rounded-xl bg-slate-900/40 border border-slate-800/60">
            <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20 shrink-0">
              <Shield size={18} />
            </div>
            <span className="text-xs text-slate-300">Conserva el <strong className="text-purple-400">conocimiento</strong> organizacional</span>
          </div>

          <div className="flex items-center gap-3 p-3.5 rounded-xl bg-slate-900/40 border border-slate-800/60">
            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20 shrink-0">
              <MessageSquare size={18} />
            </div>
            <span className="text-xs text-slate-300">Responde con <strong className="text-blue-400">contexto</strong> y trazabilidad</span>
          </div>

          <div className="flex items-center gap-3 p-3.5 rounded-xl bg-slate-900/40 border border-slate-800/60">
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shrink-0">
              <Users size={18} />
            </div>
            <span className="text-xs text-slate-300">Facilita la <strong className="text-indigo-400">colaboración</strong> entre equipos</span>
          </div>
        </div>

        {/* Footer Bar */}
        <div className="pt-4 border-t border-slate-800/80 flex flex-col sm:flex-row items-center justify-between gap-3 text-center sm:text-left">
          <p className="text-xs text-slate-400">
            La <span className="text-cyan-400 font-bold">memoria inteligente</span> para instituciones que gestionan conocimiento.
          </p>
          <Link href="/beta" className="flex items-center gap-2 text-xs text-cyan-400 hover:text-white font-mono transition-colors">
            <Globe size={14} />
            <span>kognitoai.cloud</span>
          </Link>
        </div>
      </div>
    </section>
  );
}
