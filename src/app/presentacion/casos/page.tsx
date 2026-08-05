'use client';

import React, { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Building2, 
  Atom, 
  GraduationCap, 
  ArrowLeft, 
  ArrowRight, 
  Check, 
  Sparkles,
  AlertTriangle,
  Clock,
  HelpCircle
} from "lucide-react";
import { Button } from "@/components/ui/button";

type CasoType = "empresa" | "investigador" | "estudiante";
type SubTabType = "historia" | "mecanica" | "caracteristicas";

export default function CasosPage() {
  const [activeCaso, setActiveCaso] = useState<CasoType>("empresa");
  const [activeSubTab, setActiveSubTab] = useState<SubTabType>("historia");

  const casos = {
    empresa: {
      id: "empresa",
      titulo: "Transformación Organizacional",
      badge: "Empresas & Startups",
      description: "Centraliza el conocimiento corporativo, automatiza minutas y recibe respuestas relacionales cruzadas de forma proactiva directamente en Telegram.",
      icon: <Building2 className="w-5 h-5 text-blue-500" />,
      features: [
        "Indexación automática de PDFs, contratos y correos vía API.",
        "Compañero digital de operaciones entrenado en políticas internas.",
        "Resúmenes automáticos y estructuración de trayectorias cognitivas.",
        "Cumplimiento riguroso de soberanía de datos con cifrado local."
      ],
      relatoCaos: "Lunes por la mañana en la startup 'FastRoute'. La directora de operaciones pasa 3 horas buscando en hilos antiguos de Slack y carpetas desorganizadas de Google Drive un anexo firmado en 2023 sobre el seguro de contenedores refrigerados. Al no encontrarlo a tiempo, el cliente cancela un envío internacional crítico, generando pérdidas de $15,000 USD y frustración generalizada.",
      relatoKognito: "Con KognitoAI, la directora simplemente abre su Telegram en el celular y pregunta: '¿Qué cobertura de frío acordamos en 2023?'. Kognito localiza la póliza contractual en PDF, la cruza relacionalmente con una nota de voz que el CEO grabó informalmente en junio, y responde en 5 segundos con el porcentaje exacto y el contacto de la aseguradora. El envío se procesa con éxito.",
      flujoPasoAPaso: [
        { step: 1, title: "Estímulo de Ingesta", desc: "El CEO graba una nota de voz en Telegram camino a una reunión: 'Atlas cubre hasta $10,000 USD por falla eléctrica en contenedores fríos'." },
        { step: 2, title: "Procesamiento de Audio", desc: "Kognito transcribe, auto-clasifica conceptualmente con tags (#seguro, #atlas) y crea relaciones con documentos de pólizas pasados." },
        { step: 3, title: "Inferencia en Neo4j", desc: "Se teje un hilo relacional tridimensional entre el contrato oficial del drive corporativo y la nota de voz reciente del CEO." },
        { step: 4, title: "Consulta Instantánea", desc: "Cualquier miembro del equipo consulta en lenguaje natural y recibe el brief unificado con exactitud regulatoria." }
      ],
      mockDashboard: {
        title: "Kognito Business Hub",
        metric1: { label: "Conocimiento Indexado", value: "24.8 GB" },
        metric2: { label: "Hilos Conversacionales", value: "1,240" },
        logs: [
          { time: "09:14 AM", user: "Admin", action: "Indexó base de conocimiento Q3_Plan_V2.pdf" },
          { time: "11:32 AM", user: "CEO Bot", action: "Generó reporte automático de tendencias competitivas" },
          { time: "03:45 PM", user: "Marketing Team", action: "Consultó trayectoria cognitiva de la campaña anterior" }
        ],
        visualElement: (
          <div className="flex flex-col gap-3">
            <div className="p-3 bg-blue-500/10 rounded-xl border border-blue-500/20 text-xs text-blue-600 dark:text-cyan-400 font-mono">
              $ kai-agent --mode=corporate --analyze-gaps
            </div>
            <div className="text-xs text-muted-foreground leading-relaxed">
              &gt; Analizando brechas en documentación de soporte... <br />
              <span className="text-emerald-500 font-bold">&gt; ¡Brecha detectada!</span> Falta información sobre la integración con pasarelas de pago de la API v3.
            </div>
          </div>
        )
      }
    },
    investigador: {
      id: "investigador",
      titulo: "Ciencia y Descubrimiento",
      badge: "Académicos & Científicos",
      description: "Mapea literatura científica de forma tridimensional, detecta brechas de conocimiento inesperadas entre artículos y formula nuevas hipótesis validadas por IA.",
      icon: <Atom className="w-5 h-5 text-purple-500" />,
      features: [
        "Visualización tridimensional de grafos de referencias cruzadas.",
        "Extracción automática de gaps científicos e hipótesis.",
        "Búsqueda semántica inteligente en millones de artículos indexados.",
        "Módulo de exportación de reportes estructurados para publicaciones."
      ],
      relatoCaos: "El Dr. Alejandro lleva 6 meses leyendo papers sobre la proteína X y la fatiga celular celular. Su escritorio es una maraña de notas adhesivas, libretas e hilos inconexos. Pasa semanas tratando de dilucidar por qué un paper japonés de 2018 y un estudio alemán de 2022 presentan conclusiones contradictorias, perdiéndose en detalles metodológicos irrelevantes.",
      relatoKognito: "Alejandro sube su catálogo a Kognito. El motor de sinapsis analiza las metodologías y alerta de inmediato: 'Inconsistencia detectada: Japón usó incubación a 37°C, Alemania usó 35°C, alterando la síntesis proteica'. Kognito detecta la brecha en segundos, ahorrándole meses de experimentos de laboratorio redundantes.",
      flujoPasoAPaso: [
        { step: 1, title: "Carga de Biblioteca", desc: "El investigador sube 150 archivos PDF de papers de biología celular al workspace académico." },
        { step: 2, title: "Extracción Metodológica", desc: "Modelos locales estructuran parámetros específicos: líneas celulares, reactivos, temperaturas y reactores." },
        { step: 3, title: "Cruzado de Datos en Grafo", desc: "Neo4j mapea las metodologías encontrando contradicciones y nodos huérfanos que representan vacíos de literatura." },
        { step: 4, title: "Alerta de Hipótesis", desc: "El panel académico de Kognito genera una propuesta de hipótesis lista para pruebas húmedas de laboratorio." }
      ],
      mockDashboard: {
        title: "Kognito Research Console",
        metric1: { label: "Artículos Científicos", value: "4,820" },
        metric2: { label: "Conexiones de Grafo", value: "32,840" },
        logs: [
          { time: "08:00 AM", user: "Lab-Net", action: "Mapeó correlaciones entre paper A y paper B" },
          { time: "02:10 PM", user: "AI Researcher", action: "Detectó brecha científica en mecanismos de transporte celular" },
          { time: "05:15 PM", user: "Physics Dept", action: "Exportó subgrafo de física cuántica aplicada" }
        ],
        visualElement: (
          <div className="flex items-center justify-center p-4 rounded-xl bg-purple-500/10 border border-purple-500/20 aspect-video relative">
            <div className="absolute w-3 h-3 rounded-full bg-cyan-400 animate-ping" />
            <div className="absolute w-2 h-2 rounded-full bg-cyan-400" />
            <div className="flex flex-col items-center gap-1">
              <span className="text-xs font-bold text-foreground">Relaciones de literatura</span>
              <span className="text-[10px] text-muted-foreground">32,840 nodos activos en Neo4j</span>
            </div>
          </div>
        )
      }
    },
    estudiante: {
      id: "estudiante",
      titulo: "Aprendizaje Potenciado",
      badge: "Estudiantes de Alto Rendimiento",
      description: "Organiza tus apuntes universitarios, genera cuestionarios interactivos basados en tus clases y visualiza diagramas de flujo lógicos para comprender temas complejos.",
      icon: <GraduationCap className="w-5 h-5 text-pink-500" />,
      features: [
        "Creación automática de mapas conceptuales a partir de audios y PDF.",
        "Generador dinámico de tarjetas de memorización (Flashcards).",
        "Tutor conversacional 24/7 integrado en Telegram.",
        "Seguimiento visual del progreso cognitivo y retención."
      ],
      relatoCaos: "Sofía está abrumada en vísperas del examen final de anatomía médica. Tiene 300 diapositivas y 15 audios de clases grabadas. Pasa toda la noche memorizando a ciegas fichas de papel tradicionales, sin saber qué conceptos domina y cuáles olvidará a los 10 minutos de entrar al aula, sufriendo un bloqueo por estrés de retención.",
      relatoKognito: "Sofía alimenta a Kognito con sus audios y apuntes. El sistema genera flashcards adaptativas con repetición espaciada basadas exclusivamente en sus puntos débiles de aprendizaje. En el transporte público camino al examen final, Sofía repasa con Telegram de forma interactiva y obtiene la calificación máxima sintiéndose segura.",
      flujoPasoAPaso: [
        { step: 1, title: "Captura de Clase", desc: "Sofía graba la lección sobre neuroanatomía y la envía directamente a Kognito a través del bot corporativo." },
        { step: 2, title: "Transcripción y Filtro", desc: "El software transcribe concepto anatómico y aísla la terminología clave explicada por el catedrático." },
        { step: 3, title: "Generación de Flashcards", desc: "Kognito construye tarjetas de estudio basadas en la curva de olvido y las debilidades cognitivas de Sofía." },
        { step: 4, title: "Sesión Interactiva", desc: "Un examen simulado se despliega en su celular vía chat, validando sus respuestas en tiempo récord." }
      ],
      mockDashboard: {
        title: "Kognito Study Room",
        metric1: { label: "Flashcards Generadas", value: "340" },
        metric2: { label: "Horas de Estudio AI", value: "84 hrs" },
        logs: [
          { time: "10:30 AM", user: "Tutor Bot", action: "Creó cuestionario dinámico de Neuroanatomía" },
          { time: "04:12 PM", user: "Study Session", action: "Completó trayectoria: 'Fisiología Celular'" },
          { time: "07:30 PM", user: "System", action: "Generó mapa conceptual interactivo de Álgebra Lineal" }
        ],
        visualElement: (
          <div className="flex flex-col gap-2.5">
            <div className="p-3 bg-pink-500/5 rounded-xl border border-pink-500/20 text-xs">
              <span className="font-bold text-foreground block mb-1">Pregunta de Fisiología:</span>
              ¿Cuál es la función principal de la bomba sodio-potasio?
            </div>
            <div className="text-[11px] text-emerald-500 font-bold flex items-center gap-1.5 pl-2">
              <Check className="w-3.5 h-3.5" />
              <span>Correcto: Mantener el potencial de membrana en reposo.</span>
            </div>
          </div>
        )
      }
    }
  };

  const activeData = casos[activeCaso];

  return (
    <div className="flex flex-col gap-12 py-8">
      
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
              Casos de Uso Aplicados
            </span>
            <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-foreground">
              Respuestas a la medida de tu rol
            </h1>
          </div>
          <p className="text-muted-foreground text-sm max-w-md leading-relaxed">
            Explora las historias reales y los flujos mecánicos que ilustran cómo KognitoAI reemplaza el desorden operativo por el control cognitivo.
          </p>
        </div>
      </div>

      {/* Tab Switcher */}
      <div className="flex justify-center p-2 rounded-2xl bg-muted/40 border border-border/40 max-w-2xl mx-auto w-full gap-2">
        {(["empresa", "investigador", "estudiante"] as CasoType[]).map((tab) => (
          <button
            key={tab}
            onClick={() => {
              setActiveCaso(tab);
              setActiveSubTab("historia"); // Reset sub-tab on change for predictability
            }}
            className={`flex-1 flex items-center justify-center gap-2.5 py-3 rounded-xl text-xs md:text-sm font-bold tracking-tight transition-all uppercase border ${
              activeCaso === tab
                ? "bg-background text-foreground shadow-sm border-border/40"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/40 border-transparent"
            }`}
          >
            {casos[tab].icon}
            <span className="hidden sm:inline">{casos[tab].badge.split(" ")[0]}</span>
          </button>
        ))}
      </div>

      {/* Dynamic Case Workspace Showcase */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeCaso}
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -15 }}
          transition={{ duration: 0.3 }}
          className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start"
        >
          {/* Left Column: Interactive Storytelling and Navigation */}
          <div className="lg:col-span-7 flex flex-col gap-6">
            
            {/* Header Details */}
            <div className="flex flex-col gap-3">
              <span className="text-[10px] font-extrabold uppercase px-3 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-600 dark:text-cyan-400 w-fit">
                {activeData.badge}
              </span>
              <h2 className="text-2xl md:text-3xl font-extrabold tracking-tight text-foreground">
                {activeData.titulo}
              </h2>
              <p className="text-muted-foreground text-sm leading-relaxed">
                {activeData.description}
              </p>
            </div>

            {/* Sub-Tab Navigation for Information Chunking */}
            <div className="flex border-b border-border/40 gap-5 pb-2 mb-2 w-full overflow-x-auto">
              {[
                { id: "historia", label: "📖 La Historia", color: "border-cyan-500 text-cyan-500" },
                { id: "mecanica", label: "⚙️ Flujo Paso a Paso", color: "border-purple-500 text-purple-500" },
                { id: "caracteristicas", label: "🔬 Ficha Técnica", color: "border-pink-500 text-pink-500" }
              ].map((subTab) => {
                const isSubActive = activeSubTab === subTab.id;
                return (
                  <button
                    key={subTab.id}
                    onClick={() => setActiveSubTab(subTab.id as SubTabType)}
                    className={`pb-2 text-[10px] md:text-xs font-bold uppercase tracking-wider border-b-2 transition-all whitespace-nowrap ${
                      isSubActive 
                        ? `${subTab.color} font-extrabold scale-[1.02]` 
                        : "border-transparent text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {subTab.label}
                  </button>
                );
              })}
            </div>

            {/* Tab Contents */}
            <div className="min-h-[220px]">
              <AnimatePresence mode="wait">
                {activeSubTab === "historia" && (
                  <motion.div
                    key="historia"
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 10 }}
                    className="grid grid-cols-1 md:grid-cols-2 gap-4"
                  >
                    {/* Caso de Caos */}
                    <div className="p-5 rounded-2xl border border-red-500/20 bg-red-500/[0.015] shadow-sm flex flex-col gap-2.5 relative overflow-hidden">
                      <div className="absolute top-0 right-0 p-3 opacity-[0.03]">
                        <AlertTriangle className="w-16 h-16 text-red-500" />
                      </div>
                      <span className="text-[10px] font-extrabold uppercase text-red-500 tracking-wider flex items-center gap-1.5">
                        <AlertTriangle className="w-3.5 h-3.5" />
                        El Caos Tradicional
                      </span>
                      <p className="text-xs text-foreground/80 leading-relaxed">
                        {activeData.relatoCaos}
                      </p>
                    </div>

                    {/* Caso de Kognito */}
                    <div className="p-5 rounded-2xl border border-emerald-500/20 bg-emerald-500/[0.015] shadow-sm flex flex-col gap-2.5 relative overflow-hidden">
                      <div className="absolute top-0 right-0 p-3 opacity-[0.03]">
                        <Sparkles className="w-16 h-16 text-emerald-500" />
                      </div>
                      <span className="text-[10px] font-extrabold uppercase text-emerald-500 tracking-wider flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5 text-emerald-500" />
                        La Sincronía KognitoAI
                      </span>
                      <p className="text-xs text-foreground/80 leading-relaxed">
                        {activeData.relatoKognito}
                      </p>
                    </div>
                  </motion.div>
                )}

                {activeSubTab === "mecanica" && (
                  <motion.div
                    key="mecanica"
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 10 }}
                    className="flex flex-col gap-4 pl-4 border-l border-border/40 ml-2"
                  >
                    {activeData.flujoPasoAPaso.map((step, idx) => (
                      <div key={idx} className="relative flex flex-col gap-1">
                        {/* Circle marker */}
                        <span className="absolute -left-[22px] top-0.5 w-3 h-3 rounded-full bg-cyan-500 border border-background shadow" />
                        <span className="text-xs font-bold text-foreground flex items-center gap-1.5">
                          <span className="text-[10px] font-mono text-cyan-500 font-extrabold">Paso {step.step}:</span>
                          {step.title}
                        </span>
                        <p className="text-xs text-muted-foreground leading-relaxed pl-1">
                          {step.desc}
                        </p>
                      </div>
                    ))}
                  </motion.div>
                )}

                {activeSubTab === "caracteristicas" && (
                  <motion.div
                    key="caracteristicas"
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 10 }}
                    className="grid grid-cols-1 md:grid-cols-2 gap-3"
                  >
                    {activeData.features.map((feature, idx) => (
                      <div key={idx} className="p-4 rounded-xl border border-border/40 bg-muted/20 flex items-start gap-3">
                        <div className="w-5 h-5 rounded-full bg-cyan-500/10 flex items-center justify-center text-cyan-500 border border-cyan-500/20 mt-0.5 flex-shrink-0">
                          <Check className="w-3.5 h-3.5" />
                        </div>
                        <span className="text-xs text-foreground/80 leading-normal">{feature}</span>
                      </div>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

          </div>

          {/* Right Column: Telemetry Dashboard & Log Activity */}
          <div className="lg:col-span-5 glass-card rounded-[2rem] border border-border/40 shadow-2xl p-6 relative overflow-hidden bg-background/40 lg:sticky lg:top-8">
            <div className="flex items-center justify-between border-b border-border/40 pb-4 mb-6">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
                <span className="w-2.5 h-2.5 rounded-full bg-yellow-500" />
                <span className="w-2.5 h-2.5 rounded-full bg-green-500" />
                <span className="text-xs font-bold text-foreground/70 ml-2">{activeData.mockDashboard.title}</span>
              </div>
              <span className="text-[10px] font-bold text-cyan-500 bg-cyan-500/10 px-2 py-0.5 rounded-full border border-cyan-500/20 uppercase animate-pulse">
                Sincronizado
              </span>
            </div>

            {/* Metrics */}
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="p-4 rounded-xl bg-card border border-border/40 flex flex-col gap-1 shadow-sm">
                <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">{activeData.mockDashboard.metric1.label}</span>
                <span className="text-xl font-black text-foreground">{activeData.mockDashboard.metric1.value}</span>
              </div>
              <div className="p-4 rounded-xl bg-card border border-border/40 flex flex-col gap-1 shadow-sm">
                <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">{activeData.mockDashboard.metric2.label}</span>
                <span className="text-xl font-black text-foreground">{activeData.mockDashboard.metric2.value}</span>
              </div>
            </div>

            {/* Visual element preview */}
            <div className="p-5 rounded-2xl bg-card/60 border border-border/40 mb-6 shadow-inner">
              {activeData.mockDashboard.visualElement}
            </div>

            {/* Event log activity */}
            <div className="flex flex-col gap-2">
              <span className="text-[10px] font-bold uppercase text-muted-foreground tracking-wider">Actividad del Exocerebro</span>
              <div className="flex flex-col gap-2 bg-muted/20 p-3 rounded-xl border border-border/40">
                {activeData.mockDashboard.logs.map((log, idx) => (
                  <div key={idx} className="flex justify-between items-center text-[10px] text-muted-foreground border-b border-border/20 last:border-0 pb-1.5 last:pb-0">
                    <span className="font-mono text-cyan-600 dark:text-cyan-400">{log.time}</span>
                    <span className="font-semibold text-foreground/80 truncate max-w-[200px]">{log.action}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </motion.div>
      </AnimatePresence>

      {/* Subpage CTA Navigation */}
      <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mt-8 border-t border-border/40 pt-12">
        <Link href="/presentacion/contacto" className="w-full sm:w-auto">
          <Button className="w-full sm:w-auto rounded-full bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white font-bold h-12 px-8">
            Hazte Beta Tester
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </Link>
        <Link href="/presentacion/faq" className="w-full sm:w-auto">
          <Button variant="outline" className="w-full sm:w-auto rounded-full border-border/60 font-bold h-12 px-8">
            Ver Dudas Frecuentes
          </Button>
        </Link>
      </div>

    </div>
  );
}
