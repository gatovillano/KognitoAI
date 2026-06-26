'use client';

import React, { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Cpu, 
  Database, 
  GitBranch, 
  Layers, 
  Settings, 
  ChevronRight, 
  Terminal, 
  ArrowLeft,
  ArrowRight,
  Sparkles,
  Zap,
  Server,
  Code,
  CheckCircle,
  Send,
  Wrench
} from "lucide-react";
import { Button } from "@/components/ui/button";

export default function FuncionamientoPage() {
  const [activeTab, setActiveTab] = useState<"flujo" | "datos" | "tecnologias">("flujo");

  const agentSteps = [
    {
      num: "01",
      title: "Identificación de Identidad",
      desc: "KognitoAI asocia la petición a un perfil cognitivo, cargando su estilo, tono de voz y restricciones de soberanía de datos de manera estricta.",
      meta: "ContextLoader • redis session"
    },
    {
      num: "02",
      title: "Extracción Semántica & Relacional",
      desc: "Se consulta la memoria de largo plazo (pgvector) y se exploran las conexiones en el Grafo de Conocimiento (Neo4j) para obtener una comprensión holística del tema.",
      meta: "HybridRAG • postgresql + neo4j"
    },
    {
      num: "03",
      title: "Bucle de Razonamiento y Crítica",
      desc: "A través de LangGraph, el agente realiza iteraciones de pensamiento secuenciales, detectando contradicciones lógicas y refinando hipótesis antes de contestar.",
      meta: "CognitiveLoop • langgraph agent"
    },
    {
      num: "04",
      title: "Almacenamiento de Trajectory",
      desc: "La respuesta y el camino lógico tomado se guardan en la base de datos de trayectorias, reforzando el aprendizaje continuo de la organización.",
      meta: "MemoryCommit • pgvector insert"
    }
  ];

  const microservices = [
    {
      name: "API Central (FastAPI)",
      role: "Orquestador principal y pasarela de seguridad. Gestiona la autenticación JWT de usuarios, sesiones de chat asíncronas y colas de tareas concurrentes.",
      icon: <Server className="w-5 h-5 text-cyan-500" />,
      tech: ["Python 3.11", "FastAPI", "Uvicorn", "JWT"]
    },
    {
      name: "LangGraph Engine (Core AI)",
      role: "Controla los bucles de razonamiento lógico. Permite al agente autocorregirse, contrastar contradicciones en el contexto y decidir de forma autónoma qué herramientas invocar.",
      icon: <Cpu className="w-5 h-5 text-pink-500" />,
      tech: ["LangGraph", "LangChain", "llm_manager.py", "Ollama/Gemini"]
    },
    {
      name: "Neo4j Graph Database",
      role: "Mapea relaciones explícitas e implícitas entre conceptos, notas, proyectos y personas, constituyendo la red asociativa profunda (sinapsis) del exocerebro.",
      icon: <GitBranch className="w-5 h-5 text-purple-500" />,
      tech: ["Neo4j Community", "Cypher Queries", "GraphDB"]
    },
    {
      name: "Almacén Vectorial (PGVector)",
      role: "Base de datos PostgreSQL híbrida optimizada para embeddings de alta dimensionalidad. Facilita la recuperación semántica (HybridRAG) veloz de notas y documentos.",
      icon: <Database className="w-5 h-5 text-blue-500" />,
      tech: ["PostgreSQL", "pgvector", "SQLAlchemy"]
    },
    {
      name: "Telegram Bot & Panel",
      role: "Canal móvil de captura cognitiva. Permite interactuar con tu IA mediante notas de voz, imágenes o archivos en tiempo real, respaldado por un panel de control.",
      icon: <Send className="w-5 h-5 text-emerald-500" />,
      tech: ["python-telegram-bot", "Webhooks", "telegram_panel/"]
    },
    {
      name: "Capacidades del Agente (Tools)",
      role: "scripts de Python independientes que otorgan capacidades autónomas del mundo real: búsquedas en la web, análisis sintáctico de código local o automatización de notas.",
      icon: <Wrench className="w-5 h-5 text-amber-500" />,
      tech: ["Python scripts", "Web Scrapers", "Code Analyzers"]
    }
  ];

  const techStack = [
    { category: "Backend & Core AI", items: ["Python 3.11", "FastAPI", "LangChain", "LangGraph", "Ollama / Local LLMs", "Google Gemini API"] },
    { category: "Bases de Datos & Caché", items: ["PostgreSQL", "pgvector", "Neo4j Graph Database", "Redis (Cache & Queues)"] },
    { category: "Frontend & Visualización", items: ["Next.js 15 (React 19)", "Tailwind CSS", "Framer Motion", "Recharts", "ReactFlow / Cytoscape"] },
    { category: "DevOps & Infraestructura", items: ["Docker & Compose", "Nginx", "GitHub Actions", "Self-Hosted Deployment"] }
  ];

  return (
    <div className="flex flex-col gap-16">
      
      {/* Back navigation & Title */}
      <div className="flex flex-col gap-4">
        <Link 
          href="/presentacion" 
          className="inline-flex items-center gap-2 text-sm font-semibold text-muted-foreground hover:text-foreground w-fit transition-colors group"
        >
          <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
          Volver al Inicio
        </Link>
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="flex flex-col gap-3">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-600 dark:text-cyan-400 text-xs font-extrabold uppercase tracking-widest w-fit">
              Tecnología & Arquitectura
            </span>
            <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-foreground">
              ¿Cómo opera el exocerebro digital?
            </h1>
          </div>
          <p className="text-muted-foreground text-sm max-w-md leading-relaxed">
            Una mirada en profundidad al flujo cognitivo y la arquitectura distribuida 
            que hacen de KognitoAI una plataforma líder en Inteligencia Aumentada.
          </p>
        </div>
      </div>

      {/* Interactive Architecture Console */}
      <section className="glass-card rounded-[2.5rem] border border-border/40 overflow-hidden shadow-2xl">
        {/* Console Header Tabs */}
        <div className="flex border-b border-border/40 bg-muted/30 p-2 gap-1 overflow-x-auto">
          <button
            onClick={() => setActiveTab("flujo")}
            className={`flex items-center gap-2 px-5 py-3 rounded-full text-xs font-bold uppercase tracking-wider transition-all ${
              activeTab === "flujo" 
                ? "bg-background text-foreground shadow-sm border border-border/40" 
                : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
            }`}
          >
            <Cpu className="w-4 h-4" />
            Flujo del Agente
          </button>
          <button
            onClick={() => setActiveTab("datos")}
            className={`flex items-center gap-2 px-5 py-3 rounded-full text-xs font-bold uppercase tracking-wider transition-all ${
              activeTab === "datos" 
                ? "bg-background text-foreground shadow-sm border border-border/40" 
                : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
            }`}
          >
            <Layers className="w-4 h-4" />
            Arquitectura de Servicios
          </button>
          <button
            onClick={() => setActiveTab("tecnologias")}
            className={`flex items-center gap-2 px-5 py-3 rounded-full text-xs font-bold uppercase tracking-wider transition-all ${
              activeTab === "tecnologias" 
                ? "bg-background text-foreground shadow-sm border border-border/40" 
                : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
            }`}
          >
            <Code className="w-4 h-4" />
            Stack Tecnológico
          </button>
        </div>

        {/* Console Content Screen */}
        <div className="p-8 md:p-10 min-h-[400px] flex items-center justify-center relative bg-background/50">
          
          <AnimatePresence mode="wait">
            
            {/* Tab: Flujo del Agente */}
            {activeTab === "flujo" && (
              <motion.div
                key="flujo"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.3 }}
                className="w-full grid grid-cols-1 md:grid-cols-4 gap-6"
              >
                {agentSteps.map((step, idx) => (
                  <div key={step.num} className="relative flex flex-col p-6 rounded-2xl bg-card border border-border/40 hover:border-border/80 transition-all duration-300 hover:shadow-lg">
                    {idx < 3 && (
                      <ChevronRight className="hidden md:block absolute -right-4 top-1/2 -translate-y-1/2 text-muted-foreground/40 w-6 h-6 z-10" />
                    )}
                    <span className="text-4xl font-black text-cyan-500/10 mb-4 block">
                      {step.num}
                    </span>
                    <span className="text-[10px] font-bold text-cyan-500 block uppercase tracking-wider font-mono mb-2">
                      {step.meta}
                    </span>
                    <h3 className="text-base font-bold text-foreground mb-2">{step.title}</h3>
                    <p className="text-muted-foreground text-xs leading-relaxed">{step.desc}</p>
                  </div>
                ))}
              </motion.div>
            )}

            {/* Tab: Arquitectura de Servicios */}
            {activeTab === "datos" && (
              <motion.div
                key="datos"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.3 }}
                className="w-full grid grid-cols-1 md:grid-cols-2 gap-8"
              >
                {microservices.map((service) => (
                  <div key={service.name} className="flex gap-5 p-6 rounded-2xl bg-card border border-border/40">
                    <div className="w-12 h-12 rounded-xl bg-muted flex items-center justify-center flex-shrink-0 border border-border/60">
                      {service.icon}
                    </div>
                    <div className="flex flex-col gap-2">
                      <h3 className="font-bold text-base text-foreground">{service.name}</h3>
                      <p className="text-muted-foreground text-xs leading-relaxed">{service.role}</p>
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {service.tech.map((t) => (
                          <span key={t} className="text-[9px] font-extrabold uppercase px-2 py-0.5 rounded bg-muted text-muted-foreground border border-border/30">
                            {t}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </motion.div>
            )}

            {/* Tab: Stack Tecnológico */}
            {activeTab === "tecnologias" && (
              <motion.div
                key="tecnologias"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.3 }}
                className="w-full grid grid-cols-1 md:grid-cols-2 gap-8"
              >
                {techStack.map((stack) => (
                  <div key={stack.category} className="p-6 rounded-2xl bg-card border border-border/40 flex flex-col gap-4">
                    <h3 className="text-sm font-extrabold text-foreground tracking-wider uppercase border-b border-border/40 pb-2 flex items-center gap-2">
                      <Zap className="w-4 h-4 text-cyan-500" />
                      {stack.category}
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {stack.items.map((item) => (
                        <span 
                          key={item} 
                          className="px-3.5 py-1.5 rounded-full bg-muted/60 text-muted-foreground hover:text-foreground hover:bg-muted border border-border/40 hover:border-border transition-colors text-xs font-semibold"
                        >
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </motion.div>
            )}

          </AnimatePresence>

        </div>
      </section>

      {/* Immersive Deep Dive Callout */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-10 items-center max-w-5xl mx-auto py-8">
        <div className="flex flex-col gap-6">
          <h2 className="text-3xl font-extrabold tracking-tight text-foreground leading-tight">
            Diseñado para cumplir con la Soberanía de Datos real
          </h2>
          <p className="text-muted-foreground text-sm leading-relaxed">
            KognitoAI está diseñado sobre contenedores aislados de Docker, lo que te permite correr la API central, los grafos de Neo4j y los modelos de IA de forma completamente self-hosted en tu propia red. 
          </p>
          <div className="flex flex-col gap-3 text-sm text-muted-foreground font-semibold">
            <div className="flex items-center gap-3">
              <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0" />
              <span>Cero filtrado de datos a servidores externos</span>
            </div>
            <div className="flex items-center gap-3">
              <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0" />
              <span>Soporte nativo para modelos locales y abiertos</span>
            </div>
            <div className="flex items-center gap-3">
              <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0" />
              <span>Cifrado robusto AES-256 en reposo y tránsito</span>
            </div>
          </div>
        </div>

        <div className="p-6 rounded-3xl bg-slate-950 dark:bg-slate-900 border border-white/10 text-white font-mono shadow-2xl relative group overflow-hidden">
          <div className="absolute top-2 left-2 flex gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
            <span className="w-2.5 h-2.5 rounded-full bg-yellow-500" />
            <span className="w-2.5 h-2.5 rounded-full bg-green-500" />
          </div>
          <div className="mt-4 flex items-center justify-between border-b border-white/5 pb-2 text-[10px] text-white/40">
            <span>docker-compose.yml</span>
            <Terminal className="w-3.5 h-3.5" />
          </div>
          <pre className="text-[11px] leading-relaxed text-cyan-400 overflow-x-auto pt-4 space-y-1">
            <code>{`services:
  api:
    image: kognito/core-api:latest
    environment:
      - VECTOR_STORE=pgvector
      - GRAPH_STORE=neo4j
    ports:
      - "8000:8000"
  
  neo4j:
    image: neo4j:5.12-community
    volumes:
      - neo4j_data:/data`}</code>
          </pre>
          <div className="absolute bottom-0 right-0 p-4 bg-gradient-to-l from-slate-950 to-transparent text-[10px] text-white/50">
            Click para copiar configuración
          </div>
        </div>
      </section>

      {/* Subpage CTA Navigation */}
      <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mt-8 border-t border-border/40 pt-12">
        <Link href="/presentacion/casos" className="w-full sm:w-auto">
          <Button className="w-full sm:w-auto rounded-full bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white font-bold h-12 px-8">
            Ver Casos de Uso
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </Link>
        <Link href="/presentacion/faq" className="w-full sm:w-auto">
          <Button variant="outline" className="w-full sm:w-auto rounded-full border-border/60 font-bold h-12 px-8">
            Preguntas Frecuentes
          </Button>
        </Link>
      </div>

    </div>
  );
}
