'use client';

import React from 'react';
import Link from 'next/link';
import { CircuitBrainLogo } from './CircuitBrainLogo';
import { User, Users, GraduationCap, MessageSquare, FileText, Edit3, Calendar, Globe, ArrowRight } from 'lucide-react';

export function PillarsDiagram() {
  return (
    <section className="w-full max-w-6xl mx-auto flex flex-col items-center gap-12 py-16 px-4">
      {/* Central Brain with 3 Branch Pipelines */}
      <div className="relative w-full flex flex-col items-center">
        {/* Top Header */}
        <div className="text-center mb-8">
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black text-white tracking-tight mb-3">
            El <span className="bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-400 bg-clip-text text-transparent">exocerebro</span> para personas, equipos e investigadores.
          </h2>
          <p className="text-slate-400 text-sm sm:text-base max-w-2xl mx-auto">
            Transforma información en <span className="text-cyan-400 font-semibold">conocimiento</span>. Potencia tu mente. Multiplica tu <span className="text-purple-400 font-semibold">impacto</span>.
          </p>
        </div>

        {/* Brain & Pillars Diagram Graphic */}
        <div className="w-full relative py-8 my-4 bg-slate-950/40 rounded-3xl border border-slate-800/80 backdrop-blur-md p-6 sm:p-10 overflow-hidden">
          <div className="absolute top-0 right-0 w-96 h-96 bg-purple-500/5 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-0 left-0 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />

          {/* Glowing Central Brain Core */}
          <div className="flex flex-col items-center justify-center mb-12 relative z-10">
            <div className="p-4 rounded-full bg-slate-900/90 border border-cyan-500/30 shadow-[0_0_30px_rgba(6,182,212,0.3)]">
              <CircuitBrainLogo size={72} />
            </div>
          </div>

          {/* 3 Target Pillars Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 relative z-10">
            {/* Personas */}
            <div className="flex flex-col items-center text-center p-6 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-cyan-500/40 transition-all duration-300 group hover:-translate-y-1">
              <div className="w-14 h-14 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 mb-4 group-hover:scale-110 transition-transform shadow-[0_0_15px_rgba(6,182,212,0.2)]">
                <User size={26} />
              </div>
              <h3 className="text-lg font-extrabold text-cyan-400 uppercase tracking-wider mb-2">
                Personas
              </h3>
              <p className="text-xs text-slate-300 leading-relaxed max-w-xs">
                Organiza tu conocimiento, aprende más y toma mejores decisiones.
              </p>
            </div>

            {/* Equipos */}
            <div className="flex flex-col items-center text-center p-6 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-purple-500/40 transition-all duration-300 group hover:-translate-y-1">
              <div className="w-14 h-14 rounded-2xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400 mb-4 group-hover:scale-110 transition-transform shadow-[0_0_15px_rgba(168,85,247,0.2)]">
                <Users size={26} />
              </div>
              <h3 className="text-lg font-extrabold text-purple-400 uppercase tracking-wider mb-2">
                Equipos
              </h3>
              <p className="text-xs text-slate-300 leading-relaxed max-w-xs">
                Colabora con inteligencia, centraliza información y logra más juntos.
              </p>
            </div>

            {/* Investigadores */}
            <div className="flex flex-col items-center text-center p-6 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-indigo-500/40 transition-all duration-300 group hover:-translate-y-1">
              <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 mb-4 group-hover:scale-110 transition-transform shadow-[0_0_15px_rgba(99,102,241,0.2)]">
                <GraduationCap size={26} />
              </div>
              <h3 className="text-lg font-extrabold text-indigo-400 uppercase tracking-wider mb-2">
                Investigadores
              </h3>
              <p className="text-xs text-slate-300 leading-relaxed max-w-xs">
                Investiga con profundidad, conserva el contexto y descubre nuevas conexiones.
              </p>
            </div>
          </div>

          {/* Bottom Capability Modules Bar (4 Columns) */}
          <div className="mt-10 pt-8 border-t border-slate-800/80 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 relative z-10">
            {/* Chats */}
            <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/60 flex items-start gap-3">
              <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 shrink-0">
                <MessageSquare size={18} />
              </div>
              <div className="flex flex-col">
                <span className="text-xs font-bold text-white mb-0.5">Chats</span>
                <span className="text-[11px] text-slate-400 leading-normal">Conversaciones inteligentes con contexto.</span>
              </div>
            </div>

            {/* Documentos */}
            <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/60 flex items-start gap-3">
              <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20 shrink-0">
                <FileText size={18} />
              </div>
              <div className="flex flex-col">
                <span className="text-xs font-bold text-white mb-0.5">Documentos</span>
                <span className="text-[11px] text-slate-400 leading-normal">Almacena, lee y analiza todos tus documentos.</span>
              </div>
            </div>

            {/* Notas */}
            <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/60 flex items-start gap-3">
              <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20 shrink-0">
                <Edit3 size={18} />
              </div>
              <div className="flex flex-col">
                <span className="text-xs font-bold text-white mb-0.5">Notas</span>
                <span className="text-[11px] text-slate-400 leading-normal">Captura ideas y conecta lo que realmente importa.</span>
              </div>
            </div>

            {/* Agenda */}
            <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/60 flex items-start gap-3">
              <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shrink-0">
                <Calendar size={18} />
              </div>
              <div className="flex flex-col">
                <span className="text-xs font-bold text-white mb-0.5">Agenda</span>
                <span className="text-[11px] text-slate-400 leading-normal">Organiza tareas, reuniones y fechas clave.</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Slogan & Pill CTA */}
        <div className="flex flex-col sm:flex-row items-center justify-between w-full max-w-4xl pt-4 gap-4">
          <p className="text-xs text-slate-400">
            Un solo lugar. <span className="text-purple-400 font-bold">Todo tu conocimiento</span>. Siempre contigo.
          </p>
          <Link href="/beta">
            <button className="px-6 py-2 rounded-full border border-purple-500/60 bg-slate-950 text-cyan-300 hover:text-white font-mono text-xs tracking-wider shadow-[0_0_15px_rgba(168,85,247,0.3)] hover:shadow-[0_0_20px_rgba(6,182,212,0.5)] transition-all">
              kognitoai.cloud
            </button>
          </Link>
        </div>
      </div>
    </section>
  );
}
