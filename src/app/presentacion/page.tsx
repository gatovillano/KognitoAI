'use client';

import React, { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Brain, 
  Cpu, 
  Lock, 
  Network, 
  ArrowRight, 
  Sparkles, 
  Play, 
  CheckCircle, 
  ShieldAlert, 
  TrendingUp, 
  MessageSquare,
  Database,
  ArrowUpRight,
  Server,
  Wrench,
  Terminal,
  Send,
  AppWindow,
  Sliders,
  Code,
  User,
  ClipboardList,
  FolderOpen,
  Settings,
  Bot,
  FileText
} from "lucide-react";
import { Button } from "@/components/ui/button";

export default function PresentacionPage() {
  const [activeStep, setActiveStep] = useState(0);
  const [simulationRunning, setSimulationRunning] = useState(false);
  const [selectedModule, setSelectedModule] = useState("core");
  const [selectedUxModule, setSelectedUxModule] = useState("conocimientos");
  const [showTechAudit, setShowTechAudit] = useState(false);

  const uxModules = [
    {
      id: "conocimientos",
      name: "Biblioteca de Conocimientos",
      icon: <Brain className="w-5 h-5 text-purple-500" />,
      tagline: "El motor de sinapsis relacional. No es un disco duro, es una red de sabiduría activa.",
      difference: "En Notion o Google Drive, tus PDFs y documentos mueren en carpetas estáticas y aisladas. En KognitoAI, el módulo de Conocimientos procesa tus archivos mediante un motor híbrido (Vectorial + Grafo en Neo4j), extrayendo entidades e ideas clave para tejer un mapa de relaciones tridimensional.",
      whyUnique: "Cuando le haces una pregunta al agente, este no realiza una simple búsqueda por coincidencia de palabras. El agente 'camina' a través del grafo relacional. Si subiste un correo de marketing en 2024 y un PDF técnico hoy, Kognito conecta ambas ideas de forma asociativa, revelando brechas de conocimiento e insights proactivos que ningún otro software puede detectar.",
      genericVsKognito: {
        generic: "Búsqueda por palabras clave aisladas. Carpetas mudas. Datos desconectados.",
        kognito: "Navegación tridimensional por sinapsis conceptual. El agente razona cruzando ideas de archivos diferentes de forma autónoma."
      },
      mockUi: null // Handled dynamically via KnowledgeGraphSimulation
    },
    {
      id: "escritorio",
      name: "Escritorio Neuronal",
      icon: <AppWindow className="w-5 h-5 text-cyan-500" />,
      tagline: "Tu panel de mando analítico. Control en tiempo real sobre la carga cognitiva de tu organización.",
      difference: "Un dashboard corporativo común te muestra gráficos estáticos de ventas o visitas. El Escritorio Neuronal de Kognito te ofrece una ventana viva a los procesos de pensamiento del agente, mostrando la carga de la memoria, telemetría cognitiva en tiempo real y canales activos.",
      whyUnique: "Centraliza todas tus integraciones, como tus hilos de chat de Telegram sincronizados en tiempo real y tu consola de prompts rápidos. Te permite ver exactamente qué perfiles de IA se están ejecutando y qué nivel de soberanía de datos tiene cada uno.",
      genericVsKognito: {
        generic: "Gráficos de ventas fríos e inactivos. Reportes que se leen una vez al mes.",
        kognito: "Telemetría viva de la inteligencia de tu organización. Monitoreo de sinapsis y flujos de razonamiento activos."
      },
      mockUi: (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-border/40 pb-2">
            <span className="text-[10px] font-mono text-cyan-500">Kognito Workspace Console</span>
            <span className="text-[9px] px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-500 font-bold uppercase">Sincronizado</span>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div className="p-2 bg-muted/40 border border-border/40 rounded-xl flex flex-col gap-0.5">
              <span className="text-[8px] text-muted-foreground uppercase font-bold">Carga Memoria</span>
              <span className="text-xs font-black text-foreground">84.2%</span>
            </div>
            <div className="p-2 bg-muted/40 border border-border/40 rounded-xl flex flex-col gap-0.5">
              <span className="text-[8px] text-muted-foreground uppercase font-bold">Nodos Grafo</span>
              <span className="text-xs font-black text-foreground">32,840</span>
            </div>
            <div className="p-2 bg-muted/40 border border-border/40 rounded-xl flex flex-col gap-0.5">
              <span className="text-[8px] text-muted-foreground uppercase font-bold">Trayectorias</span>
              <span className="text-xs font-black text-foreground">1,240</span>
            </div>
          </div>
          <div className="p-3 rounded-xl bg-cyan-500/5 border border-cyan-500/20 flex flex-col gap-1 text-[10px] font-mono">
            <div className="flex justify-between text-cyan-500 font-bold">
              <span>&gt; pipeline_status</span>
              <span>online</span>
            </div>
            <p className="text-muted-foreground text-[9px] leading-normal">
              Agente \"CEO Assistant\" cargado con restricción local AES-256. Esperando estímulos de Telegram...
            </p>
          </div>
        </div>
      )
    },
    {
      id: "agenda",
      name: "Agenda Cognitiva",
      icon: <Sliders className="w-5 h-5 text-emerald-500" />,
      tagline: "El planificador que piensa. Asistente proactivo que te prepara antes de cada cita.",
      difference: "Una agenda convencional solo te avisa que tienes una reunión a las 5:00 PM. La Agenda Cognitiva de Kognito se conecta a tu memoria a largo plazo para estructurar tu día con inteligencia contextual.",
      whyUnique: "El agente analiza quiénes asisten a tu próxima reunión, busca en el Grafo de Conocimientos notas anteriores de esas personas o temas relacionados, y te envía automáticamente un resumen ejecutivo y puntos clave sugeridos por Telegram 15 minutos antes de empezar.",
      genericVsKognito: {
        generic: "Recordatorios de texto mudos. Tienes que buscar manualmente la información de tu reunión.",
        kognito: "Búsqueda autónoma de contexto. Tu exocerebro te susurra al oído todo lo que necesitas saber antes de entrar."
      },
      mockUi: (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-border/40 pb-2">
            <span className="text-[10px] font-mono text-cyan-500">Cognitive Scheduler Module</span>
            <span className="text-[9px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 font-bold uppercase">Proactivo</span>
          </div>
          <div className="p-3 bg-muted/40 border border-border/40 rounded-xl flex flex-col gap-2">
            <div className="flex justify-between items-center">
              <span className="text-[10px] font-bold text-foreground">Reunión de Alianzas Comerciales</span>
              <span className="text-[8px] font-mono text-emerald-500">Hoy 16:00</span>
            </div>
            <div className="p-2 bg-emerald-500/5 border border-emerald-500/20 rounded-lg text-[9px] text-muted-foreground leading-relaxed">
              <span className="font-extrabold text-foreground block mb-0.5">🧠 Breve Cognitivo del Exocerebro:</span>
              \"Eduardo (asistente) mencionó en la nota del 14 de Mayo que prefiere contratos self-hosted. Recomiendo proponer el pipeline de Docker.\"
            </div>
          </div>
        </div>
      )
    },
    {
      id: "notas",
      name: "Notas de Memoria Activa",
      icon: <Code className="w-5 h-5 text-amber-500" />,
      tagline: "Las notas no se archivan: evolucionan. Trayectorias cognitivas autogestionadas.",
      difference: "En herramientas como Notion, Evernote o Apple Notes, las notas son páginas de texto estáticas que debes ordenar y categorizar manualmente. Con KognitoAI, tus notas son 'Trayectorias Cognitivas' vivas.",
      whyUnique: "Cada vez que escribes una nota o envías una nota de voz por Telegram, el agente la analiza de forma conceptual, la auto-etiqueta semánticamente, extrae tareas pendientes para tu agenda y la vincula de inmediato con el resto de nodos en tu base de conocimientos sin que tengas que mover un dedo.",
      genericVsKognito: {
        generic: "Texto plano inerte que se pierde en carpetas. Requiere organización y mantenimiento manual exhaustivo.",
        kognito: "Soporte activo. Tu IA refina, conecta y actualiza las notas, convirtiéndolas en bloques dinámicos de tu exocerebro."
      },
      mockUi: (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-border/40 pb-2">
            <span className="text-[10px] font-mono text-cyan-500">Kognito Memory Commit Console</span>
            <span className="text-[9px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-500 font-bold uppercase">Memory Commit</span>
          </div>
          <div className="flex flex-col gap-2 p-3 bg-muted/40 border border-border/40 rounded-xl">
            <span className="text-[10px] font-bold text-foreground">Idea: Expansión de Arquitectura Híbrida</span>
            <p className="text-[9px] text-muted-foreground leading-normal italic">
              \"Necesitamos migrar las tareas pesadas a un cluster local...\"
            </p>
            <div className="flex gap-2.5 mt-1 border-t border-border/20 pt-2 text-[8px] text-amber-500 font-semibold uppercase">
              <span>Tags de IA: #docker #local-llm #arquitectura</span>
              <span className="text-emerald-500">Sincronizado al Grafo ✓</span>
            </div>
          </div>
        </div>
      )
    },
    {
      id: "chat",
      name: "Chat Conversacional",
      icon: <MessageSquare className="w-5 h-5 text-indigo-500" />,
      tagline: "Consola de prompts y sandboxes interactivos. Ejecución de código y diagramas Mermaid en vivo.",
      difference: "No es un chat plano que solo devuelve respuestas de texto. El Chat de Kognito interactúa con tu sistema de archivos local, genera diagramas interactivos en tiempo real y ejecuta código en entornos aislados seguros.",
      whyUnique: "Permite al agente invocar herramientas internas durante la charla. Por ejemplo, al solicitar 'analiza el código del proyecto y dibuja un flujo', el agente autogenera un diagrama interactivo en formato Mermaid que se compila de inmediato en la pantalla sin intermediarios.",
      genericVsKognito: {
        generic: "Texto estático inerte. Sin interacción con el entorno del sistema local.",
        kognito: "Chat con capacidades físicas. Generación de diagramas y sandbox de código seguro."
      },
      mockUi: (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-border/40 pb-2">
            <span className="text-[10px] font-mono text-indigo-500">Interactive Chat & Sandbox</span>
            <span className="text-[9px] px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-500 font-bold uppercase">Multi-Agent</span>
          </div>
          <div className="flex flex-col gap-3 max-h-[190px] overflow-y-auto">
            <div className="flex flex-col gap-1 items-end self-end max-w-[85%]">
              <span className="text-[8px] text-muted-foreground uppercase font-bold">Tú</span>
              <div className="p-2.5 rounded-2xl bg-indigo-600 text-white text-[9px] leading-relaxed shadow-md">
                Genera el flujo de autenticación del backend.
              </div>
            </div>
            <div className="flex flex-col gap-1 items-start self-start max-w-[85%]">
              <span className="text-[8px] text-muted-foreground uppercase font-bold">KognitoAI Agent</span>
              <div className="p-2.5 rounded-2xl bg-muted/40 border border-border/40 text-[9px] leading-relaxed text-foreground flex flex-col gap-2">
                <span>Generando diagrama relacional en tiempo real...</span>
                <div className="p-2 bg-slate-900 border border-white/5 rounded-lg text-[8px] font-mono text-cyan-300">
                  graph TD<br />
                  A[Cliente] --&gt;|POST /login| B(FastAPI JWT)<br />
                  B --&gt;|Verifica hash| C[(PostgreSQL)]
                </div>
              </div>
            </div>
          </div>
        </div>
      )
    },
    {
      id: "perfiles",
      name: "Perfiles Cognitivos",
      icon: <User className="w-5 h-5 text-pink-500" />,
      tagline: "Segmentación absoluta de contexto y soberanía. Un agente para cada rol de tu organización.",
      difference: "En lugar de tener una sola IA genérica donde debes re-explicar las reglas, Kognito cuenta con Perfiles Cognitivos aislados (CEO Assistant, Auditor de Software, Revisor Legal, Académico).",
      whyUnique: "Cada perfil cuenta con su propio subconjunto de secretos, claves API mapeadas de forma privada y accesos exclusivos dentro del Grafo de Conocimientos. Esto garantiza segregación total y evita fugas de información interdepartamentales de forma nativa.",
      genericVsKognito: {
        generic: "Un solo chat generalista donde mezclas finanzas corporativas con código técnico.",
        kognito: "Segregación estricta por perfiles. Memoria y secretos aislados en silos autónomos."
      },
      mockUi: (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-border/40 pb-2">
            <span className="text-[10px] font-mono text-pink-500">Cognitive Profile Controller</span>
            <span className="text-[9px] px-2 py-0.5 rounded-full bg-pink-500/10 text-pink-500 font-bold uppercase">Silo Aislado</span>
          </div>
          <div className="flex flex-col gap-2">
            <div className="p-2.5 rounded-xl border border-pink-500/20 bg-pink-500/5 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-pink-500 animate-pulse" />
                <span className="text-[10px] font-bold text-foreground">Auditor Legal</span>
              </div>
              <span className="text-[8px] font-mono text-muted-foreground uppercase font-bold">Activo</span>
            </div>
            <div className="p-2 border border-border/40 rounded-xl bg-muted/20 text-[8px] text-muted-foreground flex flex-col gap-1">
              <div><strong className="text-foreground">Directiva:</strong> \"Verificar regulatorias de IP en cada doc.\"</div>
              <div><strong className="text-foreground">Grafo Restringido:</strong> /graphs/legal/ (Lectura/Escritura)</div>
            </div>
          </div>
        </div>
      )
    },
    {
      id: "formularios",
      name: "Formularios Cognitivos",
      icon: <ClipboardList className="w-5 h-5 text-teal-500" />,
      tagline: "Captura inteligente y adaptativa. Los datos se validan, estructuran y vinculan al instante.",
      difference: "Los formularios tradicionales como Typeform o Google Forms solo guardan texto estático en una hoja de cálculo fría que nadie analiza. Los Formularios Cognitivos de Kognito son dinámicos y conversacionales.",
      whyUnique: "El formulario adapta las siguientes preguntas en base a las respuestas anteriores del usuario gracias al motor de razonamiento del agente, y escribe las respuestas estructuradas directamente en Neo4j y pgvector, activando disparadores automáticos mediante webhooks.",
      genericVsKognito: {
        generic: "Hojas de cálculo estáticas que requieren transcripción y análisis manual posterior.",
        kognito: "Ingesta inteligente autónoma. Relaciones indexadas al instante en la base neuronal."
      },
      mockUi: (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-border/40 pb-2">
            <span className="text-[10px] font-mono text-teal-500">Adaptive Feedback Engine</span>
            <span className="text-[9px] px-2 py-0.5 rounded-full bg-teal-500/10 text-teal-500 font-bold uppercase">Formulario Inteligente</span>
          </div>
          <div className="flex flex-col gap-2 p-3 bg-muted/40 border border-border/40 rounded-xl">
            <span className="text-[9px] font-bold text-foreground">Paso 3 de 5: Detalles de Seguridad</span>
            <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
              <div className="bg-teal-500 h-1.5 rounded-full" style={{ width: '60%' }} />
            </div>
            <div className="p-2.5 rounded bg-background border border-border/40 text-[9px] leading-relaxed text-muted-foreground">
              <strong className="text-foreground">Pregunta sugerida por IA:</strong> \"Dado que almacenas datos locales, ¿qué algoritmo de cifrado utilizas?\"
            </div>
          </div>
        </div>
      )
    },
    {
      id: "galerias",
      name: "Galerías de Medios",
      icon: <FolderOpen className="w-5 h-5 text-amber-500" />,
      tagline: "Visión y catalogación multimodal. Indexación visual dentro de tu mapa de sinapsis.",
      difference: "No es una simple carpeta de fotos. El módulo de Galerías de Kognito corre de forma local modelos de visión artificial y reconocimiento de texto (OCR) para indexar de manera semántica cada imagen o gráfico subido.",
      whyUnique: "Permite realizar búsquedas inteligentes por texto dentro de las fotos o por conceptos visuales (ej. 'Busca fotos del pizarrón de la reunión de Docker de la semana pasada'). Kognito las vincula al Grafo de Conocimientos relacionándolas con las notas escritas ese mismo día.",
      genericVsKognito: {
        generic: "Carpetas mudas de archivos visuales imposibles de buscar a nivel de contenido semántico.",
        kognito: "Indexación relacional multimodal. El agente 've' y contextualiza tus imágenes dentro del exocerebro."
      },
      mockUi: (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-border/40 pb-2">
            <span className="text-[10px] font-mono text-amber-500">Multi-Modal Vision Board</span>
            <span className="text-[9px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-500 font-bold uppercase">Vision & OCR</span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="aspect-video bg-muted/40 border border-border/40 rounded-xl relative overflow-hidden flex items-center justify-center">
              <span className="text-[8px] font-bold text-foreground">Pizarra: Docker</span>
              <span className="absolute bottom-1 left-1 px-1 py-0.5 rounded bg-amber-500/90 text-white text-[6px] font-bold uppercase">OCR: \"Docker run\"</span>
            </div>
            <div className="p-2 border border-border/40 bg-muted/20 rounded-xl text-[8px] text-muted-foreground flex flex-col gap-1">
              <span className="font-extrabold text-foreground">Análisis de Visión:</span>
              \"Diagrama de contenedores. Conectado al nodo de la Nota del Plan Q4.\"
            </div>
          </div>
        </div>
      )
    },
    {
      id: "admin",
      name: "Consola de Administración",
      icon: <Settings className="w-5 h-5 text-slate-500" />,
      tagline: "Sala de control de secretos, procesos asíncronos y programación de agentes autónomos.",
      difference: "No es un panel de configuración genérico. Es un centro operativo de orquestación donde puedes coordinar secretos corporativos, llaves API, y tareas de fondo autónomas.",
      whyUnique: "Permite programar de manera visual cuándo el agente debe despertarse en segundo plano para realizar tareas pesadas (ej. 'Escanear páginas web del sector a las 3:00 AM, resumirlas y agregarlas al Grafo'). Gestiona contraseñas con cifrado de nivel bancario de forma local.",
      genericVsKognito: {
        generic: "Configuraciones en archivos de texto .env que solo un desarrollador experto puede tocar.",
        kognito: "Consola de control interactiva para calendarizar agentes y salvaguardar llaves y soberanía de datos."
      },
      mockUi: (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-border/40 pb-2">
            <span className="text-[10px] font-mono text-slate-500">Secrets & Agent Scheduler</span>
            <span className="text-[9px] px-2 py-0.5 rounded-full bg-slate-500/10 text-slate-500 font-bold uppercase">Control Panel</span>
          </div>
          <div className="flex flex-col gap-2">
            <div className="flex justify-between items-center text-[9px] bg-muted/40 p-2 border border-border/40 rounded-xl">
              <span className="font-bold text-foreground">WebScraper_Competencia</span>
              <span className="text-emerald-500 font-mono">Diario 03:00 AM</span>
            </div>
            <div className="flex justify-between items-center text-[9px] bg-muted/40 p-2 border border-border/40 rounded-xl">
              <span className="font-bold text-foreground">llm7_api_key</span>
              <span className="text-muted-foreground font-mono">••••••••••••••••</span>
            </div>
          </div>
        </div>
      )
    },
    {
      id: "documents",
      name: "OnlyOffice",
      icon: <FileText className="w-5 h-5 text-emerald-500" />,
      tagline: "Editor de documentos autohospedado en tiempo real. Word, Excel y PowerPoint 100% integrados.",
      difference: "En lugar de usar Google Docs o Office 365, que envían tu información confidencial a nubes externas de terceros, KognitoAI integra un servidor OnlyOffice autohospedado dentro de la infraestructura local de tu empresa para co-editar en tiempo real con total privacidad.",
      whyUnique: "El agente de IA puede invocar herramientas directamente sobre estos archivos. Puedes pedirle al agente: 'Crea una propuesta comercial en Word' o 'Puebla el presupuesto de Excel con los datos del análisis', y la IA escribirá y dará formato nativo al documento (.docx, .xlsx) de manera autónoma.",
      genericVsKognito: {
        generic: "Edición web aislada que expone tu telemetría y propiedad intelectual a nubes de terceros.",
        kognito: "Servidor autohospedado de edición colaborativa en tiempo real con asistencia física de IA local."
      },
      mockUi: (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-border/40 pb-2">
            <span className="text-[10px] font-mono text-emerald-500">OnlyOffice Co-Editing Server</span>
            <span className="text-[9px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 font-bold uppercase">Soberano</span>
          </div>
          <div className="flex flex-col gap-2 p-3 bg-muted/40 border border-border/40 rounded-xl font-mono text-[9px]">
            <div className="flex justify-between items-center text-foreground font-bold">
              <span>📄 propuesta_seguridad.docx</span>
              <span className="text-emerald-500 text-[8px]">Co-editando</span>
            </div>
            <div className="p-2 bg-slate-900 border border-white/5 rounded-lg text-[8px] text-cyan-300 leading-normal">
              <span className="text-white/40">// El Agente está insertando una tabla de RAG...</span><br />
              &gt; edit_onlyoffice_document_tool(action="insert_table", table_data=[["Módulo", "Soberanía"], ["Neo4j", "Local"]])
            </div>
          </div>
        </div>
      )
    },
    {
      id: "workspaces",
      name: "Workspaces",
      icon: <Bot className="w-5 h-5 text-indigo-500" />,
      tagline: "Silos de colaboración independientes. Contextos y bases de datos aisladas para tus proyectos o clientes.",
      difference: "Tus chats, archivos, bases vectoriales y notas no están mezclados en un solo pozo sin estructurar. Con Workspaces, organizas entornos de trabajo independientes de forma segura para cada departamento, cliente o proyecto.",
      whyUnique: "Cada espacio tiene su propia base de datos Neo4j y colección vectorial. Al cambiar de workspace, el agente de IA automáticamente reconfigura su memoria y sus llaves API locales, garantizando segregación absoluta de información y evitando fugas accidentales.",
      genericVsKognito: {
        generic: "Un único pozo de conocimiento o chat generalista donde mezclas información confidencial de clientes.",
        kognito: "Entornos estancos de memoria activa. Segmentación estricta de prompts, secretos y conocimiento."
      },
      mockUi: (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-border/40 pb-2">
            <span className="text-[10px] font-mono text-indigo-500">Workspace Context Switcher</span>
            <span className="text-[9px] px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-500 font-bold uppercase">Silo de Memoria</span>
          </div>
          <div className="flex flex-col gap-2">
            <div className="p-2 border border-indigo-500/30 bg-indigo-500/5 rounded-xl flex items-center justify-between text-[10px] font-bold">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
                <span>Workspace: Cliente Alpha</span>
              </div>
              <span className="text-[8px] font-mono text-muted-foreground uppercase">Activo</span>
            </div>
            <div className="p-2 border border-border/40 bg-muted/20 rounded-xl text-[8px] text-muted-foreground flex flex-col gap-1 font-mono">
              <div><strong className="text-foreground">Base de Datos:</strong> neo4j://graph-alpha</div>
              <div><strong className="text-foreground">Memoria Vectorial:</strong> pgvector://alpha-collection</div>
              <div><strong className="text-foreground">Acceso de IA:</strong> Restringido a documentos de Alpha</div>
            </div>
          </div>
        </div>
      )
    }
  ];

  const modules = [
    {
      id: "core",
      name: "Core Logic (El Cerebro)",
      icon: <Brain className="w-5 h-5 text-pink-500" />,
      shortDesc: "El motor de toma de decisiones del agente. Orquesta los flujos recursivos (LangGraph) y gestiona los proveedores de LLM de forma inteligente.",
      tech: ["Python 3.11", "LangGraph", "LangChain"],
      files: ["core/agent.py", "core/llm_manager.py", "core/memory/"],
      details: "Es el núcleo intelectual de KognitoAI. Se encarga de analizar los estímulos recibidos, seleccionar dinámicamente qué herramientas y modelos (locales vía Ollama o en la nube) son idóneos para resolver cada tarea, y ejecutar los bucles iterativos de auto-crítica cognitiva.",
      highlight: "Permite bucles de auto-corrección lógica antes de responder.",
      codeSnippet: `class CognitiveAgent:
  def __init__(self, llm_provider):
    self.llm = LLMManager(provider=llm_provider)
    self.graph = LangGraphEngine()

  async def think(self, stimulus):
    context = await self.retrieve_hybrid_context(stimulus)
    trajectory = await self.graph.run_loop(stimulus, context)
    return trajectory`
    },
    {
      id: "api",
      name: "Backend API Central",
      icon: <Server className="w-5 h-5 text-cyan-500" />,
      shortDesc: "Pasarela y orquestador central. Gestiona seguridad mediante JWT, chats en tiempo real por WebSockets e indexación de archivos.",
      tech: ["FastAPI", "Uvicorn", "Python JWT"],
      files: ["api/notes.py", "api/llm.py", "run_api.py"],
      details: "Una API REST moderna y robusta construida sobre FastAPI. Actúa como el centro neurálgico de comunicaciones, recibiendo peticiones del frontend Next.js, autenticando usuarios, gestionando historiales de chat de forma asíncrona y distribuyendo tareas hacia los clientes.",
      highlight: "Asíncrono, altamente concurrente y optimizado para sockets.",
      codeSnippet: `@app.post("/api/chat/send")
async def send_message(message: ChatMessage, user = Depends(get_current_user)):
    # Inicializa el pipeline del exocerebro
    agent = CognitiveAgent(user.preferred_provider)
    response = await agent.think(message.content)
    return {"status": "success", "data": response}`
    },
    {
      id: "graph",
      name: "Grafo de Conocimiento",
      icon: <Network className="w-5 h-5 text-purple-500" />,
      shortDesc: "Asociación relacional profunda basada en Neo4j. Mapea la sinapsis conectando conceptos, notas y personas de tu organización.",
      tech: ["Neo4j Community", "Cypher Queries", "GraphDB"],
      files: ["knowledge_graph/adapter.py", "knowledge_graph/queries.py"],
      details: "A diferencia de un buscador clásico que solo ve palabras sueltas, Kognito mapea relaciones lógicas en una base de datos de grafos Neo4j. Conecta proyectos paralelos, personas asignadas, notas e ideas, lo que permite al agente derivar deducciones lógicas de segundo orden.",
      highlight: "Exploración de trayectorias relacionales mediante Cypher.",
      codeSnippet: `MATCH (n:Concept {name: $concept})-[r:RELATES_TO*1..2]-(connected)
RETURN connected.name, r.type, connected.type
LIMIT 15`
    },
    {
      id: "telegram",
      name: "Telegram Bot & Panel",
      icon: <Send className="w-5 h-5 text-blue-500" />,
      shortDesc: "Tu exocerebro viaja contigo. Captura notas de voz, imágenes o PDFs en tiempo real directamente desde tu canal de mensajería.",
      tech: ["python-telegram-bot", "Telegram Webhooks", "Panel de Control"],
      files: ["run_telegram_bot.py", "telegram_client/", "telegram_panel/"],
      details: "Un bot robusto e interactivo que convierte tu Telegram diario en una terminal de captura analítica de alto rendimiento. Envíale enlaces, fotos, documentos o audios; el bot los procesa instantáneamente, los indexa en tu memoria digital y te ofrece alertas proactivas.",
      highlight: "Captura cognitiva en movilidad en menos de 2 segundos.",
      codeSnippet: `async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    saved_path = await file.download_to_drive()
    # Ejecuta herramienta de indexación de documentos
    await indexer.process_file(saved_path)
    await update.message.reply_text("Documento indexado con éxito en el grafo.")`
    },
    {
      id: "tools",
      name: "Herramientas del Agente",
      icon: <Wrench className="w-5 h-5 text-emerald-500" />,
      shortDesc: "Capacidades de acción autónoma en el mundo exterior. Permite realizar búsquedas web, analizar código local y extraer resúmenes.",
      tech: ["Python scripts", "Web Scrapers", "Code Parsers"],
      files: ["tools/search.py", "tools/notes.py", "tools/code_analyzer.py"],
      details: "El agente no es un mero modelo conversacional pasivo; cuenta con más de 15 scripts específicos de Python que puede ejecutar de forma inteligente cuando detecta que su memoria estática no basta para resolver el estímulo del usuario.",
      highlight: "Ecosistema modular de capacidades extensibles de forma simple.",
      codeSnippet: `# tool_definition: tools/code_analyzer.py
def analyze_code_structure(file_path):
    with open(file_path, 'r') as f:
        tree = ast.parse(f.read())
    # Extrae clases, métodos y dependencias para el contexto
    return inspect_syntax_tree(tree)`
    },
    {
      id: "frontend",
      name: "Frontend UI Next.js",
      icon: <AppWindow className="w-5 h-5 text-amber-500" />,
      shortDesc: "La interfaz de escritorio definitiva. Diseñada con diseño premium, glassmorphism, gráficos de grafos tridimensionales y chats dinámicos.",
      tech: ["Next.js 15", "React 19", "Tailwind CSS", "Framer Motion"],
      files: ["src/app/page.tsx", "src/components/forms/", "src/utils/api.js"],
      details: "Un panel de control web suntuoso y ultra-fluido que consolida la experiencia. Incorpora gráficos dinámicos de rendimiento, visualizadores tridimensionales interactivos de tus redes cognitivas, gestores de chats fluidos y consolas de configuración avanzadas.",
      highlight: "Experiencia Premium Wow factor con micro-animaciones inmersivas.",
      codeSnippet: `export default function ResponseCard({ data }) {
  return (
    <motion.div 
      whileHover={{ scale: 1.01 }} 
      className="glass-card p-6 border border-border/40 rounded-3xl"
    >
      <BrainHeader responseType={data.type} />
      <MarkdownRenderer content={data.content} />
    </motion.div>
  );
}`
    },
    {
      id: "ops",
      name: "Infraestructura & DevOps",
      icon: <Sliders className="w-5 h-5 text-slate-500" />,
      shortDesc: "Aislamiento hermético e infraestructura local lista. Garantiza que tu conocimiento no dependa de APIs corporativas externas.",
      tech: ["Docker", "Docker Compose", "pgvector", "Redis Cache"],
      files: ["docker-compose.yml", "Dockerfile.core.hybrid"],
      details: "Todo KognitoAI se ejecuta sobre contenedores independientes coordinados por Docker Compose. Esto permite un despliegue local inmediato, encapsulando tus bases de datos PostgreSQL y Neo4j y tus orquestadores de memoria bajo tu propio control y firewall.",
      highlight: "Arquitectura autogestionada (self-hosted) enfocada en seguridad estricta.",
      codeSnippet: `version: '3.8'
services:
  core-agent:
    build: 
      context: .
      dockerfile: Dockerfile.core.hybrid
    volumes:
      - .:/app
    depends_on:
      - neo4j
      - pgvector`
    }
  ];

  const pillars = [
    {
      title: "Soberanía Cognitiva",
      description: "Tu conocimiento te pertenece. Protege tu propiedad intelectual alojando todo en tu propia infraestructura con control absoluto sobre los datos.",
      icon: <Lock className="w-8 h-8 text-cyan-500" />,
      color: "from-cyan-500/10 to-blue-500/5",
      borderColor: "group-hover:border-cyan-500/30"
    },
    {
      title: "Compañero Digital",
      description: "Un exocerebro que aprende de tus interacciones diarias a través de Telegram o Web, asimilando tu estilo de razonamiento, tono y prioridades.",
      icon: <Brain className="w-8 h-8 text-blue-500" />,
      color: "from-blue-500/10 to-indigo-500/5",
      borderColor: "group-hover:border-blue-500/30"
    },
    {
      title: "Grafos de Conocimiento",
      description: "No es solo búsqueda semántica. Kognito mapea relaciones profundas entre tus proyectos e ideas mediante un motor neuronal basado en Neo4j.",
      icon: <Network className="w-8 h-8 text-purple-500" />,
      color: "from-purple-500/10 to-pink-500/5",
      borderColor: "group-hover:border-purple-500/30"
    }
  ];

  const steps = [
    {
      title: "Captura de Estímulo",
      description: "Pregunta textual o archivo recibido por el usuario (vía Telegram, Web o API).",
      detail: "Se analiza el canal y se activa el perfil de contexto correspondiente.",
      icon: <MessageSquare className="w-5 h-5 text-cyan-400" />
    },
    {
      title: "Recuperación Híbrida (RAG)",
      description: "Búsqueda vectorial en pgvector combinada con exploración relacional en Neo4j.",
      detail: "Se extraen tanto los datos semánticos como la red de conexiones del grafo.",
      icon: <Database className="w-5 h-5 text-blue-400" />
    },
    {
      title: "Razonamiento Cíclico",
      description: "Orquestación LangGraph que ejecuta bucles de razonamiento lógico y refinamiento.",
      detail: "El agente detecta inconsistencias y valida hipótesis de forma proactiva.",
      icon: <Cpu className="w-5 h-5 text-purple-400" />
    },
    {
      title: "Acción & Síntesis",
      description: "Formulación de respuesta soberana optimizada para el usuario.",
      detail: "Se almacena la nueva trayectoria cognitiva en la memoria a largo plazo.",
      icon: <Sparkles className="w-5 h-5 text-pink-400" />
    }
  ];

  const runSimulation = () => {
    if (simulationRunning) return;
    setSimulationRunning(true);
    setActiveStep(0);
    
    let currentStep = 0;
    const interval = setInterval(() => {
      if (currentStep < 3) {
        currentStep++;
        setActiveStep(currentStep);
      } else {
        clearInterval(interval);
        setSimulationRunning(false);
      }
    }, 2500);
  };

  return (
    <div className="flex flex-col gap-24 items-center w-full max-w-6xl mx-auto px-4 md:px-0">
      
      {/* 1. HERO SECTION (FOCUSED ON CLIENT VALUE & EMOTION) */}
      <section className="relative w-full flex flex-col items-center text-center gap-6 pt-12">
        {/* Centered Large Logo */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7 }}
          className="relative w-36 h-36 md:w-44 md:h-44 mb-2 select-none pointer-events-none drop-shadow-[0_0_30px_rgba(6,182,212,0.15)] dark:drop-shadow-[0_0_40px_rgba(6,182,212,0.25)]"
        >
          <Image
            src="/logo-simple.png"
            alt="KognitoAI Logo"
            fill
            className="object-contain"
            priority
          />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-600 dark:text-cyan-400 text-xs font-extrabold uppercase tracking-widest mb-2 hover:bg-cyan-500/15 transition-colors cursor-default"
        >
          <Sparkles className="w-3.5 h-3.5" />
          Tu Conocimiento Corporativo, Seguro y Activo
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.6 }}
          className="text-4xl md:text-6xl font-extrabold tracking-tight leading-[1.1] text-foreground max-w-4xl"
        >
          Construye el <span className="text-gradient">Exocerebro Digital</span> de tu empresa
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="text-muted-foreground text-base md:text-lg max-w-3xl leading-relaxed mt-2"
        >
          Centraliza PDFs, minutas, chats y notas en una base de conocimientos privada. 
          Un compañero inteligente que razona contigo, se integra con tus herramientas diarias (como Telegram) 
          y opera con soberanía de datos total.
        </motion.p>

        {/* CTA Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.6 }}
          className="flex flex-col sm:flex-row items-center gap-4 mt-6 w-full justify-center"
        >
          <Link href="/presentacion/contacto" className="w-full sm:w-auto">
            <Button className="w-full sm:w-auto rounded-full text-base font-bold h-12 px-8 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white shadow-lg shadow-cyan-500/10 hover:shadow-xl hover:shadow-cyan-500/20 hover:scale-[1.02] transition-all">
              Solicitar Demo Gratuita
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </Link>
          <Link href="/presentacion/casos" className="w-full sm:w-auto">
            <Button variant="outline" className="w-full sm:w-auto rounded-full text-base font-bold h-12 px-8 border-border/60 hover:bg-muted/50 hover:scale-[1.02] transition-all">
              Ver Historias Reales
            </Button>
          </Link>
        </motion.div>
      </section>

      {/* 2. THE DILEMMA SECTION: EMPATHY FOR THE END CLIENT */}
      <section className="w-full grid grid-cols-1 md:grid-cols-2 gap-8 items-stretch border-t border-b border-border/20 py-16 my-4">
        {/* The Pain */}
        <div className="p-8 rounded-[2rem] border border-red-500/15 bg-red-500/[0.01] flex flex-col justify-between">
          <div className="flex flex-col gap-4">
            <div className="w-12 h-12 rounded-2xl bg-red-500/10 flex items-center justify-center border border-red-500/20 text-red-500">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold text-foreground">El Caos Operativo de Hoy</h3>
            <p className="text-muted-foreground text-sm leading-relaxed">
              Tu equipo pierde un promedio de 2.5 horas diarias buscando información en correos, 
              chats de WhatsApp, carpetas de Drive y notas personales. Cuando un empleado clave se retira, 
              su experiencia y conocimiento se van con él, dejando a la empresa vulnerable.
            </p>
          </div>
          <span className="text-xs text-red-500 font-bold uppercase tracking-wider mt-6 block">
            Problema: Pérdida de Productividad y Know-how
          </span>
        </div>

        {/* The Solution */}
        <div className="p-8 rounded-[2rem] border border-emerald-500/15 bg-emerald-500/[0.01] flex flex-col justify-between">
          <div className="flex flex-col gap-4">
            <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20 text-emerald-500">
              <Brain className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold text-foreground">El Exocerebro con KognitoAI</h3>
            <p className="text-muted-foreground text-sm leading-relaxed">
              Toda la memoria de tu organización queda unificada de forma segura. Cualquier colaborador 
              puede consultar documentos y obtener respuestas contextuales instantáneas. KognitoAI conecta los cabos 
              sueltos automáticamente usando grafos relacionales y se anticipa a tus necesidades.
            </p>
          </div>
          <span className="text-xs text-emerald-500 font-bold uppercase tracking-wider mt-6 block">
            Solución: Centralización Inteligente y Soberana
          </span>
        </div>
      </section>

      {/* 3. UX MODULES SHOWCASE (WHAT THE CLIENT WILL ACTUALLY USE DAILY) */}
      <section className="w-full flex flex-col gap-12 pt-4">
        <div className="flex flex-col items-center text-center gap-3">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-600 dark:text-purple-400 text-xs font-extrabold uppercase tracking-widest w-fit">
            <Sparkles className="w-3.5 h-3.5" />
            Entorno de Trabajo Simplificado
          </div>
          <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight text-foreground">
            Herramientas diseñadas para la acción
          </h2>
          <p className="text-muted-foreground text-sm max-w-2xl">
            No son herramientas ordinarias de notas o calendarios. Cada módulo se conecta 
            directamente con la memoria activa de tu organización para asistirte de manera proactiva.
          </p>
        </div>

        {/* Two-Column Side-by-Side Panel Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start max-w-6xl mx-auto w-full">
          
          {/* LEFT COLUMN: Vertical Navigation Menu (4 of 12 cols) */}
          <div className="lg:col-span-4 flex flex-col gap-2.5 p-4 rounded-[2rem] bg-muted/40 border border-border/40 max-h-[640px] overflow-y-auto custom-scrollbar shadow-inner w-full">
            <span className="text-[10px] font-extrabold uppercase tracking-widest text-muted-foreground/80 px-2 mb-1 block">
              Módulos del Exocerebro ({uxModules.length})
            </span>
            <div className="flex flex-col gap-1.5">
              {uxModules.map((mod) => {
                const isActive = selectedUxModule === mod.id;
                return (
                  <button
                    key={mod.id}
                    onClick={() => setSelectedUxModule(mod.id)}
                    className={`flex items-center gap-3.5 p-3 rounded-2xl text-left transition-all border w-full group ${
                      isActive
                        ? "bg-background text-foreground shadow-lg border-border/50 scale-[1.01]"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted/40 border-transparent"
                    }`}
                  >
                    <div className={`p-2 rounded-xl shrink-0 transition-colors ${
                      isActive ? "bg-purple-500/10 text-purple-500 dark:text-purple-400" : "bg-muted/85 text-muted-foreground group-hover:bg-muted"
                    }`}>
                      {mod.icon}
                    </div>
                    <div className="flex flex-col min-w-0">
                      <span className="text-xs font-extrabold tracking-wide text-foreground">
                        {mod.name}
                      </span>
                      <span className="text-[10px] text-muted-foreground truncate max-w-[220px] mt-0.5">
                        {mod.tagline}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* RIGHT COLUMN: Active Content Card Panel (8 of 12 cols) */}
          <div className="lg:col-span-8 w-full">
            {(() => {
              const activeUx = uxModules.find(m => m.id === selectedUxModule) || uxModules[0];
              return (
                <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-stretch">
                  
                  {/* Left Side of Panel: Description Card (7 of 12 active cols) */}
                  <div className="md:col-span-7 flex flex-col gap-6 p-6 md:p-8 rounded-[2rem] glass-card border border-border/40 shadow-2xl relative overflow-hidden bg-background/30 justify-between">
                    <div className="absolute top-0 right-0 w-48 h-48 bg-purple-500/5 rounded-full blur-3xl pointer-events-none" />
                    
                    <div className="flex flex-col gap-5">
                      {/* Title & Tagline */}
                      <div className="flex flex-col gap-2">
                        <span className="text-xs font-bold text-purple-500 uppercase tracking-widest font-mono">Módulo Operativo</span>
                        <h3 className="text-2xl font-black text-foreground">{activeUx.name}</h3>
                        <p className="text-sm md:text-base font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-500 to-indigo-600 dark:from-purple-400 dark:to-cyan-300 leading-normal">
                          "{activeUx.tagline}"
                        </p>
                      </div>

                      {/* La Particularidad */}
                      <div className="flex flex-col gap-2 border-t border-border/20 pt-4">
                        <span className="text-xs font-extrabold uppercase text-muted-foreground tracking-wider">¿Cómo funciona para ti?</span>
                        <p className="text-muted-foreground text-xs md:text-sm leading-relaxed">{activeUx.difference}</p>
                      </div>

                      {/* Por qué es único */}
                      <div className="flex flex-col gap-2">
                        <span className="text-xs font-extrabold uppercase text-cyan-600 dark:text-cyan-400 tracking-wider">El valor de Kognito</span>
                        <p className="text-muted-foreground text-xs md:text-sm leading-relaxed font-medium">{activeUx.whyUnique}</p>
                      </div>

                      {/* Generic vs Kognito Comparison Grid */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-2">
                        <div className="p-3 rounded-xl border border-red-500/25 bg-red-500/[0.015] flex flex-col gap-1">
                          <span className="text-[9px] font-bold uppercase text-red-500 tracking-wider font-mono">Herramienta Convencional</span>
                          <p className="text-[10px] text-muted-foreground/80 leading-normal">{activeUx.genericVsKognito.generic}</p>
                        </div>
                        <div className="p-3 rounded-xl border border-emerald-500/25 bg-emerald-500/[0.015] flex flex-col gap-1">
                          <span className="text-[9px] font-bold uppercase text-emerald-500 tracking-wider font-mono">KognitoAI</span>
                          <p className="text-[10px] text-foreground/80 leading-normal">{activeUx.genericVsKognito.kognito}</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Right Side of Panel: Interactive Mockup / Simulator (5 of 12 active cols) */}
                  <div className="md:col-span-5 flex flex-col justify-center p-6 rounded-[2rem] glass-card border border-border/40 shadow-2xl relative overflow-hidden bg-background/50 aspect-square md:aspect-auto">
                    <div className="absolute inset-0 bg-gradient-to-tr from-purple-500/5 to-cyan-500/5 pointer-events-none rounded-3xl" />
                    <div className="w-full relative z-10">
                      {activeUx.id === "conocimientos" ? (
                        <KnowledgeGraphSimulation />
                      ) : (
                        activeUx.mockUi
                      )}
                    </div>
                  </div>
                  
                </div>
              );
            })()}
          </div>
          
        </div>
      </section>

      {/* 4. COGNITIVE PROCESS SIMULATOR (HOW THE SYSTEM THINKS) */}
      <section className="w-full max-w-5xl mx-auto glass-card rounded-[2.5rem] border border-border/40 p-8 md:p-12 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />
        
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
          {/* Simulator Info */}
          <div className="lg:col-span-5 flex flex-col gap-6">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-500 text-xs font-bold w-fit uppercase">
              <Cpu className="w-3.5 h-3.5" />
              Ciclo de Razonamiento
            </div>
            <h2 className="text-3xl font-extrabold tracking-tight text-foreground leading-tight">
              ¿Cómo razona KognitoAI?
            </h2>
            <p className="text-muted-foreground text-sm leading-relaxed">
              KognitoAI no inventa respuestas de forma pasiva. Ejecuta un ciclo riguroso de búsqueda local, cruce de información en grafos y validación lógica antes de responder.
            </p>
            <Button 
              onClick={runSimulation}
              disabled={simulationRunning}
              className="rounded-full bg-gradient-to-r from-blue-500 to-indigo-600 text-white font-bold h-11 shadow-md w-full sm:w-fit"
            >
              {simulationRunning ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Ejecutando simulación...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Play className="w-4 h-4" />
                  Ver ciclo de razonamiento
                </span>
              )}
            </Button>
          </div>

          {/* Simulator Steps Display */}
          <div className="lg:col-span-7 flex flex-col gap-4 relative">
            <div className="absolute left-7 top-6 bottom-6 w-0.5 bg-border/40 pointer-events-none z-0" />

            {steps.map((step, idx) => {
              const isActive = activeStep === idx;
              const isCompleted = activeStep > idx;

              return (
                <div 
                  key={step.title}
                  className={`flex gap-5 items-start p-4 rounded-2xl transition-all duration-300 relative z-10 ${
                    isActive 
                      ? "bg-muted/70 shadow-sm border border-border/40" 
                      : "opacity-60"
                  }`}
                >
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 relative z-10 transition-colors duration-300 ${
                    isActive 
                      ? "bg-cyan-500 text-white ring-4 ring-cyan-500/10" 
                      : isCompleted
                      ? "bg-emerald-500 text-white"
                      : "bg-muted border border-border"
                  }`}>
                    {isCompleted ? (
                      <CheckCircle className="w-3.5 h-3.5" />
                    ) : (
                      <span className="text-[10px] font-bold">{idx + 1}</span>
                    )}
                  </div>

                  <div className="flex-1 flex flex-col gap-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-foreground">{step.title}</span>
                      {isActive && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 font-extrabold uppercase animate-pulse">
                          Procesando
                        </span>
                      )}
                    </div>
                    <p className="text-muted-foreground text-xs leading-relaxed">{step.description}</p>
                    {isActive && (
                      <motion.div 
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        className="mt-2 text-[11px] p-2.5 rounded-lg bg-background/50 border border-border/20 text-cyan-600 dark:text-cyan-400 font-medium flex items-center gap-2"
                      >
                        {step.icon}
                        <span>{step.detail}</span>
                      </motion.div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 5. THREE PILLARS OF TRUST */}
      <section className="w-full max-w-6xl mx-auto flex flex-col gap-10">
        <div className="flex flex-col items-center text-center gap-3">
          <h2 className="text-3xl font-extrabold tracking-tight text-foreground">
            Diseñado bajo principios corporativos rigurosos
          </h2>
          <p className="text-muted-foreground text-sm max-w-2xl">
            A diferencia de los asistentes de IA comerciales estándar, Kognito opera bajo una arquitectura blindada.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {pillars.map((pillar, idx) => (
            <motion.div
              key={pillar.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.1, duration: 0.5 }}
              className={`group flex flex-col p-8 rounded-3xl bg-gradient-to-b ${pillar.color} border border-border/40 hover:border-border transition-all duration-300 hover:shadow-xl hover:shadow-cyan-500/[0.02]`}
            >
              <div className="w-14 h-14 rounded-2xl bg-background border border-border/40 flex items-center justify-center mb-6 shadow-sm group-hover:scale-105 transition-transform duration-300">
                {pillar.icon}
              </div>
              <h3 className="text-xl font-bold text-foreground mb-3">{pillar.title}</h3>
              <p className="text-muted-foreground text-xs leading-relaxed">{pillar.description}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* 6. COLLAPSIBLE TECHNICAL AUDIT PANEL (DEV/CTO ACCORDION) */}
      <section className="w-full max-w-6xl mx-auto flex flex-col gap-6 border-t border-border/20 pt-16">
        <div className="flex flex-col items-center text-center gap-3">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-600 dark:text-cyan-400 text-xs font-extrabold uppercase tracking-widest w-fit">
            <Code className="w-3.5 h-3.5" />
            Consola de Auditoría Técnica
          </div>
          <h2 className="text-2xl md:text-3xl font-extrabold tracking-tight text-foreground">
            ¿Eres parte del equipo de tecnología o seguridad?
          </h2>
          <p className="text-muted-foreground text-sm max-w-xl">
            Explora las entrañas de la arquitectura, rutas de archivos del repositorio y código fuente de KognitoAI.
          </p>
          <Button 
            variant="outline" 
            onClick={() => setShowTechAudit(!showTechAudit)}
            className="rounded-full border-cyan-500/30 text-cyan-600 dark:text-cyan-400 font-bold mt-2"
          >
            {showTechAudit ? "Ocultar Auditoría Técnica" : "Abrir Auditoría de Arquitectura"}
          </Button>
        </div>

        <AnimatePresence>
          {showTechAudit && (
            <motion.div 
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden w-full pt-4"
            >
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                {/* Modules List (Left Column) */}
                <div className="lg:col-span-5 flex flex-col gap-3">
                  {modules.map((mod) => {
                    const isActive = selectedModule === mod.id;
                    return (
                      <button
                        key={mod.id}
                        onClick={() => setSelectedModule(mod.id)}
                        className={`flex items-start gap-4 p-4 rounded-2xl text-left transition-all duration-300 border ${
                          isActive
                            ? "bg-muted/70 border-border/80 shadow-md ring-2 ring-cyan-500/10 scale-[1.01]"
                            : "bg-transparent border-transparent hover:bg-muted/30 hover:border-border/30 opacity-75 hover:opacity-100"
                        }`}
                      >
                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 border shadow-inner transition-transform duration-300 ${
                          isActive 
                            ? "bg-background border-border scale-105" 
                            : "bg-muted/50 border-border/40"
                        }`}>
                          {mod.icon}
                        </div>
                        <div className="flex-1 flex flex-col gap-1">
                          <span className="font-extrabold text-sm text-foreground">{mod.name}</span>
                          <p className="text-muted-foreground text-xs leading-normal line-clamp-2">{mod.shortDesc}</p>
                        </div>
                      </button>
                    );
                  })}
                </div>

                {/* Module Detail Pane (Right Column) */}
                <div className="lg:col-span-7 flex flex-col gap-6 p-6 md:p-8 rounded-[2rem] glass-card border border-border/40 shadow-2xl relative overflow-hidden bg-background/40 min-h-[480px] justify-between">
                  <div className="absolute top-0 right-0 w-48 h-48 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />
                  
                  {(() => {
                    const activeMod = modules.find(m => m.id === selectedModule) || modules[0];
                    return (
                      <>
                        <div className="flex flex-col gap-4">
                          <div className="flex items-center justify-between border-b border-border/40 pb-4">
                            <div className="flex items-center gap-3">
                              <div className="w-10 h-10 rounded-xl bg-cyan-500/10 flex items-center justify-center border border-cyan-500/20">
                                {activeMod.icon}
                              </div>
                              <div className="flex flex-col">
                                <span className="text-xs font-bold text-cyan-500 uppercase tracking-widest font-mono">Módulo Técnico</span>
                                <h3 className="text-xl font-extrabold text-foreground">{activeMod.name}</h3>
                              </div>
                            </div>
                            <span className="text-[10px] font-bold text-emerald-500 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full uppercase">
                              Operativo
                            </span>
                          </div>

                          <div className="flex flex-col gap-1.5">
                            <span className="text-[10px] font-bold uppercase text-muted-foreground tracking-wider">Descripción del Código</span>
                            <p className="text-muted-foreground text-xs md:text-sm leading-relaxed">{activeMod.details}</p>
                          </div>

                          <div className="flex flex-wrap gap-2 pt-2">
                            {activeMod.tech.map((t) => (
                              <span key={t} className="text-[9px] font-extrabold uppercase px-2.5 py-1 rounded-md bg-muted text-muted-foreground border border-border/40 shadow-sm">
                                {t}
                              </span>
                            ))}
                          </div>

                          <div className="flex flex-col gap-2 bg-muted/20 border border-border/30 rounded-xl p-3.5 mt-2">
                            <span className="text-[10px] font-bold uppercase text-muted-foreground tracking-wider flex items-center gap-1.5 font-mono">
                              <Terminal className="w-3.5 h-3.5 text-cyan-500" />
                              Rutas del Repositorio
                            </span>
                            <div className="flex flex-wrap gap-2">
                              {activeMod.files.map((file) => (
                                <span key={file} className="text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-background border border-border/40 text-foreground/80">
                                  {file}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>

                        {/* Code Mock Window */}
                        <div className="mt-4 flex flex-col rounded-2xl bg-slate-950 dark:bg-slate-900 border border-white/10 text-white font-mono shadow-2xl relative overflow-hidden">
                          <div className="flex items-center justify-between border-b border-white/5 px-4 py-2 text-[10px] text-white/40 bg-slate-900/50">
                            <span className="flex items-center gap-1.5">
                              <span className="w-2 h-2 rounded-full bg-cyan-400" />
                              {activeMod.files[0]}
                            </span>
                            <span className="text-[9px] text-cyan-500 uppercase tracking-widest font-extrabold">Preview Código</span>
                          </div>
                          <pre className="text-[10px] md:text-[11px] leading-relaxed text-cyan-300 overflow-x-auto p-4 max-h-[160px]">
                            <code>{activeMod.codeSnippet}</code>
                          </pre>
                        </div>

                        <div className="mt-4 border-t border-border/30 pt-4 flex items-center gap-2 text-xs font-semibold text-cyan-600 dark:text-cyan-400">
                          <Sparkles className="w-4 h-4 text-cyan-500 flex-shrink-0 animate-pulse" />
                          <span>Beneficio clave: {activeMod.highlight}</span>
                        </div>
                      </>
                    );
                  })()}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </section>

      {/* 7. EXPANDED NAVIGATION CARDS */}
      <section className="w-full max-w-6xl mx-auto flex flex-col gap-10 border-t border-border/20 pt-16">
        <div className="flex flex-col items-center text-center gap-2">
          <h2 className="text-3xl font-extrabold text-foreground">
            Explora más sobre Kognito
          </h2>
          <p className="text-muted-foreground text-sm max-w-xl">
            Profundiza en la tecnología, casos de estudio o agenda una demostración con nuestro equipo.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 w-full">
          
          <Link href="/presentacion/funcionamiento" className="group">
            <div className="h-full rounded-3xl p-6 bg-gradient-to-br from-blue-500/5 to-cyan-500/5 border border-border/40 hover:border-blue-500/20 hover:shadow-xl hover:shadow-blue-500/[0.01] hover:-translate-y-1 transition-all duration-300 flex flex-col justify-between">
              <div>
                <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center mb-6 group-hover:scale-105 transition-transform duration-300 border border-blue-500/20 shadow-inner">
                  <Cpu className="w-6 h-6 text-blue-500" />
                </div>
                <h3 className="text-lg font-bold text-foreground mb-2 group-hover:text-primary transition-colors flex items-center gap-1.5">
                  ¿Cómo funciona?
                  <ArrowUpRight className="w-4 h-4 opacity-50 group-hover:opacity-100 transition-opacity" />
                </h3>
                <p className="text-muted-foreground text-xs leading-relaxed">
                  Arquitectura técnica, flujo de microservicios, bases relacionales y grafos de conocimiento neuronales.
                </p>
              </div>
              <span className="text-[10px] font-bold text-blue-500 mt-6 block uppercase tracking-wider">
                Explorar Arquitectura
              </span>
            </div>
          </Link>

          <Link href="/presentacion/casos" className="group">
            <div className="h-full rounded-3xl p-6 bg-gradient-to-br from-emerald-500/5 to-teal-500/5 border border-border/40 hover:border-emerald-500/20 hover:shadow-xl hover:shadow-emerald-500/[0.01] hover:-translate-y-1 transition-all duration-300 flex flex-col justify-between">
              <div>
                <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center mb-6 group-hover:scale-105 transition-transform duration-300 border border-emerald-500/20 shadow-inner">
                  <TrendingUp className="w-6 h-6 text-emerald-500" />
                </div>
                <h3 className="text-lg font-bold text-foreground mb-2 group-hover:text-primary transition-colors flex items-center gap-1.5">
                  Casos de Uso
                  <ArrowUpRight className="w-4 h-4 opacity-50 group-hover:opacity-100 transition-opacity" />
                </h3>
                <p className="text-muted-foreground text-xs leading-relaxed">
                  Aplicaciones reales y dinámicas para empresas, científicos, investigadores y estudiantes de alto rendimiento.
                </p>
              </div>
              <span className="text-[10px] font-bold text-emerald-500 mt-6 block uppercase tracking-wider">
                Ver Aplicaciones
              </span>
            </div>
          </Link>

          <Link href="/presentacion/faq" className="group">
            <div className="h-full rounded-3xl p-6 bg-gradient-to-br from-purple-500/5 to-indigo-500/5 border border-border/40 hover:border-purple-500/20 hover:shadow-xl hover:shadow-purple-500/[0.01] hover:-translate-y-1 transition-all duration-300 flex flex-col justify-between">
              <div>
                <div className="w-12 h-12 rounded-xl bg-purple-500/10 flex items-center justify-center mb-6 group-hover:scale-105 transition-transform duration-300 border border-purple-500/20 shadow-inner">
                  <Brain className="w-6 h-6 text-purple-500" />
                </div>
                <h3 className="text-lg font-bold text-foreground mb-2 group-hover:text-primary transition-colors flex items-center gap-1.5">
                  Dudas Frecuentes
                  <ArrowUpRight className="w-4 h-4 opacity-50 group-hover:opacity-100 transition-opacity" />
                </h3>
                <p className="text-muted-foreground text-xs leading-relaxed">
                  Respuestas detalladas sobre soberanía, integraciones personalizadas y seguridad robusta de datos.
                </p>
              </div>
              <span className="text-[10px] font-bold text-purple-500 mt-6 block uppercase tracking-wider">
                Resolver Preguntas
              </span>
            </div>
          </Link>

          <Link href="/presentacion/contacto" className="group">
            <div className="h-full rounded-3xl p-6 bg-gradient-to-br from-pink-500/5 to-rose-500/5 border border-border/40 hover:border-pink-500/20 hover:shadow-xl hover:shadow-pink-500/[0.01] hover:-translate-y-1 transition-all duration-300 flex flex-col justify-between">
              <div>
                <div className="w-12 h-12 rounded-xl bg-pink-500/10 flex items-center justify-center mb-6 group-hover:scale-105 transition-transform duration-300 border border-pink-500/20 shadow-inner">
                  <Sparkles className="w-6 h-6 text-pink-500" />
                </div>
                <h3 className="text-lg font-bold text-foreground mb-2 group-hover:text-primary transition-colors flex items-center gap-1.5">
                  Solicita una Demo
                  <ArrowUpRight className="w-4 h-4 opacity-50 group-hover:opacity-100 transition-opacity" />
                </h3>
                <p className="text-muted-foreground text-xs leading-relaxed">
                  Conéctate directamente con nuestros ingenieros para realizar una integración personalizada con tus sistemas actuales.
                </p>
              </div>
              <span className="text-[10px] font-bold text-pink-500 mt-6 block uppercase tracking-wider">
                Agendar Sesión
              </span>
            </div>
          </Link>

        </div>
      </section>

      {/* 8. ULTIMATE CALL TO ACTION */}
      <section className="w-full max-w-4xl mx-auto rounded-[2.5rem] bg-gradient-to-r from-cyan-500 to-blue-600 p-12 text-center text-white relative overflow-hidden shadow-2xl group mb-8">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.05)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.05)_1px,transparent_1px)] bg-[size:3rem_3rem] pointer-events-none" />
        <div className="absolute -top-32 -left-32 w-80 h-80 bg-white/10 rounded-full blur-3xl pointer-events-none" />
        
        <div className="relative z-10 flex flex-col items-center gap-6 max-w-2xl mx-auto">
          <Brain className="w-12 h-12 text-cyan-200 animate-bounce" />
          <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight">
            Comienza a construir tu exocerebro hoy mismo
          </h2>
          <p className="text-cyan-100 text-sm md:text-base leading-relaxed">
            Obtén acceso completo e instantáneo al escritorio analítico, integra tus hilos de Telegram y automatiza la extracción de sabiduría organizacional en minutos.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 mt-4 w-full justify-center">
            <Link href="/login" className="w-full sm:w-auto">
              <Button className="w-full sm:w-auto rounded-full bg-white text-blue-600 hover:bg-cyan-50 font-bold h-12 px-8 shadow-lg hover:scale-[1.02] transition-all">
                Iniciar Sesión
              </Button>
            </Link>
            <Link href="/presentacion/contacto" className="w-full sm:w-auto">
              <Button variant="outline" className="w-full sm:w-auto rounded-full border-white/40 text-white hover:bg-white/10 font-bold h-12 px-8">
                Hablar con un Experto
              </Button>
            </Link>
          </div>
        </div>
      </section>
      
    </div>
  );
}

function KnowledgeGraphSimulation() {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>("note");
  const [isScanning, setIsScanning] = useState(false);
  const [scanStep, setScanStep] = useState(0);

  const nodes = [
    { id: "note", label: "Nota: Plan Q4", type: "nota", x: 25, y: 30, color: "bg-cyan-500", glowColor: "shadow-cyan-500/30", details: "Propuesta de migración a Docker y cluster local." },
    { id: "pdf", label: "Contrato Legal.pdf", type: "documento", x: 75, y: 25, color: "bg-purple-500", glowColor: "shadow-purple-500/30", details: "Restricción de soberanía de datos y NDA." },
    { id: "concept", label: "Concepto: Riesgo IP", type: "concepto", x: 50, y: 70, color: "bg-pink-500", glowColor: "shadow-pink-500/30", details: "Pérdida de propiedad intelectual en nubes públicas." },
    { id: "telegram", label: "Audio de Telegram", type: "interacción", x: 15, y: 75, color: "bg-blue-500", glowColor: "shadow-blue-500/30", details: "Feedback de cliente sobre servidores privados." },
    { id: "meeting", label: "Cita: Demo Docker", type: "evento", x: 80, y: 75, color: "bg-emerald-500", glowColor: "shadow-emerald-500/30", details: "Sesión de despliegue local programada." }
  ];

  const links = [
    { source: "note", target: "concept", sourceX: 25, sourceY: 30, targetX: 50, targetY: 70, label: "evalúa" },
    { source: "pdf", target: "concept", sourceX: 75, sourceY: 25, targetX: 50, targetY: 70, label: "regula" },
    { source: "telegram", target: "note", sourceX: 15, sourceY: 75, targetX: 25, targetY: 30, label: "solicita" },
    { source: "pdf", target: "meeting", sourceX: 75, sourceY: 25, targetX: 80, targetY: 75, label: "planifica" },
    { source: "note", target: "pdf", sourceX: 25, sourceY: 30, targetX: 75, targetY: 25, label: "Inferencia IA", inferred: true }
  ];

  const startScan = () => {
    if (isScanning) return;
    setIsScanning(true);
    setScanStep(1);
    
    // Step 1: Telegram highlights
    setTimeout(() => {
      setScanStep(2);
      setSelectedNode("note");
      // Step 2: Note highlights
      setTimeout(() => {
        setScanStep(3);
        setSelectedNode("concept");
        // Step 3: Concept highlights
        setTimeout(() => {
          setScanStep(4);
          setSelectedNode("pdf");
          setTimeout(() => {
            setIsScanning(false);
            setScanStep(0);
          }, 3500);
        }, 2000);
      }, 2000);
    }, 2000);
  };

  const getConnectedNodes = (nodeId: string) => {
    const connected = new Set<string>([nodeId]);
    links.forEach(l => {
      if (l.source === nodeId) connected.add(l.target);
      if (l.target === nodeId) connected.add(l.source);
    });
    return connected;
  };

  const activeNodeDetails = nodes.find(n => n.id === selectedNode) || nodes[0];

  return (
    <div className="flex flex-col gap-4 w-full">
      <div className="flex items-center justify-between border-b border-border/40 pb-2">
        <span className="text-[10px] font-mono text-cyan-500 tracking-wider">Kognito Relational Synapse Engine</span>
        <button 
          onClick={startScan}
          disabled={isScanning}
          className="text-[9px] px-2 py-1 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 font-extrabold uppercase hover:bg-purple-500/20 active:scale-95 transition-all flex items-center gap-1"
        >
          <Sparkles className="w-3.5 h-3.5 text-purple-400 animate-pulse" />
          {isScanning ? "Escaneando..." : "Simular Sinapsis"}
        </button>
      </div>

      {/* Main Interactive Graph Arena */}
      <div className="relative aspect-[4/3] rounded-2xl bg-slate-950/40 border border-border/40 overflow-hidden shadow-inner">
        {/* Floating grid bg */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(128,128,128,0.015)_1px,transparent_1px),linear-gradient(to_bottom,rgba(128,128,128,0.015)_1px,transparent_1px)] bg-[size:1.5rem_1.5rem]" />
        
        {/* SVG Links */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none" xmlns="http://www.w3.org/2000/svg">
          {links.map((link, idx) => {
            const isHovered = hoveredNode ? (hoveredNode === link.source || hoveredNode === link.target) : true;
            const isScanningActive = isScanning && (
              (scanStep === 1 && link.source === "telegram" && link.target === "note") ||
              (scanStep === 2 && link.source === "note" && link.target === "concept") ||
              (scanStep === 3 && link.source === "pdf" && link.target === "concept") ||
              (scanStep === 4 && link.source === "note" && link.target === "pdf")
            );

            return (
              <g key={idx}>
                {/* Background thick path for hover ease */}
                <line 
                  x1={`${link.sourceX}%`} 
                  y1={`${link.sourceY}%`} 
                  x2={`${link.targetX}%`} 
                  y2={`${link.targetY}%`} 
                  stroke="transparent" 
                  strokeWidth="10" 
                />
                {/* Actual line */}
                <line 
                  x1={`${link.sourceX}%`} 
                  y1={`${link.sourceY}%`} 
                  x2={`${link.targetX}%`} 
                  y2={`${link.targetY}%`} 
                  stroke={link.inferred ? "#ec4899" : "#3b82f6"} 
                  strokeWidth={link.inferred ? "1.5" : "1"} 
                  strokeDasharray={link.inferred ? "4" : "0"}
                  className={`transition-opacity duration-300 ${
                    isScanningActive ? "stroke-purple-400 stroke-2" : isHovered ? "opacity-40" : "opacity-10"
                  }`}
                />
              </g>
            );
          })}
        </svg>

        {/* Nodes layer */}
        {nodes.map((node) => {
          const isSelected = selectedNode === node.id;
          const isHovered = hoveredNode ? getConnectedNodes(hoveredNode).has(node.id) : true;
          
          let isScanningFocus = false;
          if (isScanning) {
            if (scanStep === 1 && node.id === "telegram") isScanningFocus = true;
            if (scanStep === 2 && node.id === "note") isScanningFocus = true;
            if (scanStep === 3 && node.id === "concept") isScanningFocus = true;
            if (scanStep === 4 && node.id === "pdf") isScanningFocus = true;
          }

          return (
            <motion.div
              key={node.id}
              style={{ left: `${node.x}%`, top: `${node.y}%` }}
              className="absolute -translate-x-1/2 -translate-y-1/2 z-20 cursor-pointer"
              onMouseEnter={() => setHoveredNode(node.id)}
              onMouseLeave={() => setHoveredNode(null)}
              onClick={() => setSelectedNode(node.id)}
              animate={{
                y: [0, -3, 0],
              }}
              transition={{
                duration: 4,
                repeat: Infinity,
                ease: "easeInOut",
                delay: node.x * 0.05
              }}
            >
              {/* Outer pulsing ring for selected or scanning */}
              {(isSelected || isScanningFocus) && (
                <span className="absolute inset-0 -m-2 rounded-full border border-purple-500 animate-ping opacity-60 pointer-events-none" />
              )}

              {/* Node core visual */}
              <div 
                className={`relative flex items-center justify-center p-2 rounded-xl border transition-all duration-300 ${
                  isScanningFocus 
                    ? "bg-purple-950 border-purple-400 scale-110 shadow-lg shadow-purple-500/30" 
                    : isSelected 
                    ? "bg-slate-900 border-cyan-500 scale-105 shadow-md shadow-cyan-500/20" 
                    : isHovered 
                    ? "bg-slate-950/80 border-border/80" 
                    : "bg-slate-950/30 border-border/20 opacity-40"
                }`}
              >
                {/* Node colored dot */}
                <span className={`w-2.5 h-2.5 rounded-full ${node.color} mr-1.5 shadow ${node.glowColor}`} />
                <span className="text-[9px] font-bold text-foreground tracking-tight select-none">
                  {node.label}
                </span>
              </div>
            </motion.div>
          );
        })}

        {/* Small floating HUD instructions */}
        <div className="absolute top-2 left-2 pointer-events-none bg-slate-950/60 border border-white/5 rounded px-1.5 py-0.5 text-[8px] text-white/40 uppercase font-mono">
          Neo4j Graph Simulation Mode
        </div>
      </div>

      {/* Node Detail Card Overlay */}
      <AnimatePresence mode="wait">
        <motion.div
          key={selectedNode || "none"}
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 5 }}
          className="p-3.5 bg-muted/40 border border-border/40 rounded-xl flex flex-col gap-1.5 min-h-[95px] justify-center transition-all duration-300"
        >
          {isScanning ? (
            <div className="flex flex-col gap-1 text-[10px] leading-relaxed">
              <div className="flex items-center gap-1.5 font-bold text-purple-400">
                <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-ping" />
                <span>[AGENT SYNAPSE] Procesando consulta en Neo4j...</span>
              </div>
              <p className="text-muted-foreground text-[9px] leading-normal">
                {scanStep === 1 && "🔌 Paso 1: Analizando estímulo auditivo del cliente en base vectorial."}
                {scanStep === 2 && "🔌 Paso 2: Buscando trayectorias asociadas en notas del Plan Q4."}
                {scanStep === 3 && "🔌 Paso 3: Identificando restricciones regulatorias de Riesgo IP."}
                {scanStep === 4 && "🔌 Paso 4: Extrayendo cláusulas de almacenamiento local en PDF."}
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-1 text-[10px]">
              <div className="flex justify-between items-center border-b border-border/20 pb-1">
                <span className="font-extrabold text-foreground flex items-center gap-1">
                  <span className={`w-1.5 h-1.5 rounded-full ${activeNodeDetails.color}`} />
                  {activeNodeDetails.label}
                </span>
                <span className="text-[8px] font-mono text-muted-foreground uppercase">{activeNodeDetails.type}</span>
              </div>
              <p className="text-muted-foreground text-[9px] leading-normal">{activeNodeDetails.details}</p>
              <div className="flex gap-2.5 mt-1 text-[7px] text-cyan-600 dark:text-cyan-400 uppercase font-bold tracking-wider font-mono">
                <span>Neo4j Node ID: {selectedNode}</span>
                <span>Vector Dimension: 1536</span>
              </div>
            </div>
          )}
        </motion.div>
      </AnimatePresence>

      {/* Inferred Insight Box */}
      {isScanning && scanStep === 4 && (
        <motion.div 
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="p-3 bg-purple-500/10 border border-purple-500/20 text-purple-400 dark:text-purple-300 rounded-xl text-[10px] leading-normal"
        >
          <span className="font-extrabold block mb-0.5">🧠 Inferencia del Exocerebro:</span>
          "El Audio de Telegram del cliente solicita estricta soberanía de datos. El Plan Q4 propone migrar a Docker en cluster local, lo cual cumple plenamente con las restricciones de soberanía especificadas en el Contrato Legal.pdf frente al Riesgo de IP en nubes públicas."
        </motion.div>
      )}
    </div>
  );
}
