'use client';

import React, { useState, useMemo } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { 
  HelpCircle, 
  Search, 
  ArrowLeft, 
  Mail, 
  ChevronDown, 
  Lock, 
  Cpu
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface FaqItem {
  id: number;
  pregunta: string;
  respuesta: string;
  categoria: "general" | "tecnologia" | "seguridad";
}

const faqs: FaqItem[] = [
    {
      id: 1,
      categoria: "general",
      pregunta: "¿Qué es Kognito AI?",
      respuesta: "KognitoAI es un exocerebro digital colaborativo que integra Inteligencia Artificial avanzada, bases de datos vectoriales y grafos de conocimiento neuronales. Su objetivo es actuar como un compañero digital y exocerebro que asimila y organiza la sabiduría de tu organización o la tuya propia."
    },
    {
      id: 2,
      categoria: "general",
      pregunta: "¿Qué es la Soberanía Cognitiva?",
      respuesta: "Es el derecho y la capacidad técnica de retener el control total de tus datos, tu conocimiento indexado y tus trayectorias de pensamiento de la IA. A diferencia de las soluciones propietarias tradicionales, KognitoAI te permite correr todo de forma local o en tu nube privada, previniendo que tu propiedad intelectual sea utilizada para entrenar modelos externos."
    },
    {
      id: 3,
      categoria: "tecnologia",
      pregunta: "¿Cómo se integra con mis sistemas?",
      respuesta: "KognitoAI expone una API REST moderna basada en FastAPI que permite conectarlo con ERPs, CRMs, Notion, Slack y repositorios Git. Además, incluye un cliente conversacional de Telegram ultra optimizado para capturar pensamientos y consultarle en tiempo real."
    },
    {
      id: 4,
      categoria: "tecnologia",
      pregunta: "¿Qué base de datos y modelos utiliza?",
      respuesta: "Utiliza PostgreSQL con la extensión pgvector para el almacenamiento semántico indexado, y Neo4j para el Grafo de Conocimiento Neuronal. Es multi-modelo, soportando APIs comerciales como Claude, GPT-4, Gemini y modelos locales abiertos (como Llama 3 o Mistral) a través de Ollama."
    },
    {
      id: 5,
      categoria: "seguridad",
      pregunta: "¿Cómo protege Kognito mis datos?",
      respuesta: "Implementamos cifrado completo en tránsito (TLS 1.3) y en reposo (AES-256), controles granulares de roles integrados en AuthContext y despliegue modular con Docker, garantizando que puedas aislar completamente el sistema de Internet si tu política lo requiere."
    },
    {
      id: 6,
      categoria: "seguridad",
      pregunta: "¿Cumple con normativas de protección de datos?",
      respuesta: "Sí. Al estar diseñado bajo el principio de Soberanía Cognitiva y permitir despliegues 100% self-hosted, Kognito facilita el cumplimiento riguroso de normativas como GDPR, CCPA y regulaciones locales de manejo de información empresarial."
    }
  ];

export default function FaqPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [activeCategory, setActiveCategory] = useState<"todos" | "general" | "tecnologia" | "seguridad">("todos");
  const [openId, setOpenId] = useState<number | null>(null);

  // Filtrado y búsqueda
  const filteredFaqs = useMemo(() => {
    return faqs.filter(faq => {
      const matchesSearch = 
        faq.pregunta.toLowerCase().includes(searchTerm.toLowerCase()) || 
        faq.respuesta.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesCategory = 
        activeCategory === "todos" || 
        faq.categoria === activeCategory;
      return matchesSearch && matchesCategory;
    });
  }, [searchTerm, activeCategory]);

  const toggleOpen = (id: number) => {
    setOpenId(openId === id ? null : id);
  };

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
              Dudas Comunes
            </span>
            <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-foreground">
              Preguntas Frecuentes
            </h1>
          </div>
          <p className="text-muted-foreground text-sm max-w-md leading-relaxed">
            Resuelve de forma inmediata tus inquietudes sobre soberanía, seguridad de datos, integración y el núcleo del motor cognitivo.
          </p>
        </div>
      </div>

      {/* Search and Filters */}
      <section className="flex flex-col md:flex-row gap-4 items-center justify-between">
        {/* Search Input */}
        <div className="relative w-full md:max-w-md group">
          <div className="absolute -inset-0.5 bg-gradient-to-r from-cyan-500/20 to-blue-600/20 rounded-full blur opacity-20 group-hover:opacity-40 transition duration-500"></div>
          <div className="relative">
            <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
            <Input
              type="text"
              placeholder="Buscar en preguntas o respuestas..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-11 h-12 rounded-full bg-card/60 backdrop-blur-sm border-border/40 text-sm w-full"
            />
          </div>
        </div>

        {/* Categories Tab list */}
        <div className="flex flex-wrap gap-2 justify-center w-full md:w-auto">
          {["todos", "general", "tecnologia", "seguridad"].map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat as any)}
              className={`px-4.5 py-2.5 rounded-full text-xs font-bold uppercase tracking-wider transition-colors border ${
                activeCategory === cat
                  ? "bg-foreground text-background border-foreground shadow-sm"
                  : "bg-muted/40 text-muted-foreground border-border/40 hover:text-foreground hover:bg-muted/60"
              }`}
            >
              {cat === "todos" ? "Todos" : cat === "general" ? "General" : cat === "tecnologia" ? "Tecnología" : "Seguridad"}
            </button>
          ))}
        </div>
      </section>

      {/* Accordion List */}
      <section className="flex flex-col gap-4 max-w-4xl mx-auto w-full min-h-[300px]">
        <AnimatePresence mode="popLayout">
          {filteredFaqs.map((faq) => {
            const isOpen = openId === faq.id;
            return (
              <motion.div
                key={faq.id}
                layout
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.98 }}
                transition={{ duration: 0.2 }}
                className={`rounded-2xl border transition-all duration-300 ${
                  isOpen 
                    ? "bg-card border-cyan-500/30 shadow-xl shadow-cyan-500/[0.01]" 
                    : "bg-card/60 border-border/40 hover:border-border"
                }`}
              >
                <button
                  onClick={() => toggleOpen(faq.id)}
                  className="w-full p-6 text-left flex items-center justify-between gap-6 cursor-pointer focus:outline-none"
                >
                  <div className="flex items-center gap-4">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center border flex-shrink-0 ${
                      faq.categoria === "general" 
                        ? "bg-blue-500/10 border-blue-500/20 text-blue-500"
                        : faq.categoria === "tecnologia"
                        ? "bg-cyan-500/10 border-cyan-500/20 text-cyan-500"
                        : "bg-purple-500/10 border-purple-500/20 text-purple-500"
                    }`}>
                      {faq.categoria === "general" ? <HelpCircle className="w-4 h-4" /> : faq.categoria === "tecnologia" ? <Cpu className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
                    </div>
                    <span className="font-bold text-foreground text-base md:text-lg leading-snug">
                      {faq.pregunta}
                    </span>
                  </div>
                  <ChevronDown className={`w-5 h-5 text-muted-foreground flex-shrink-0 transition-transform duration-300 ${
                    isOpen ? "transform rotate-180 text-cyan-500" : ""
                  }`} />
                </button>

                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.25, ease: "easeInOut" }}
                      className="overflow-hidden"
                    >
                      <div className="px-6 pb-6 pt-1 text-muted-foreground text-sm md:text-base leading-relaxed border-t border-border/20">
                        {faq.respuesta}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}

          {filteredFaqs.length === 0 && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center py-16 text-muted-foreground flex flex-col items-center gap-3 bg-muted/20 rounded-2xl border border-dashed border-border/60"
            >
              <HelpCircle className="w-10 h-10 opacity-20" />
              <p className="font-semibold text-sm">No se encontraron resultados para tu búsqueda.</p>
            </motion.div>
          )}
        </AnimatePresence>
      </section>

      {/* Still have questions? Call to Action */}
      <section className="w-full max-w-3xl mx-auto glass-card rounded-3xl border border-border/40 p-8 flex flex-col md:flex-row items-center justify-between gap-6 bg-background/50">
        <div className="flex items-center gap-4 text-center md:text-left flex-col md:flex-row">
          <div className="w-12 h-12 rounded-full bg-cyan-500/10 flex items-center justify-center border border-cyan-500/20 text-cyan-500 flex-shrink-0">
            <Mail className="w-5 h-5" />
          </div>
          <div>
            <h4 className="font-bold text-foreground text-lg">¿Tienes otra consulta en particular?</h4>
            <p className="text-muted-foreground text-xs leading-relaxed mt-0.5">Estamos listos para resolver todas tus dudas de integración e infraestructura.</p>
          </div>
        </div>
        <Link href="/presentacion/contacto">
          <Button className="rounded-full font-bold bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white shadow-md shadow-cyan-500/10 px-6">
            Escríbenos
          </Button>
        </Link>
      </section>

    </div>
  );
}
