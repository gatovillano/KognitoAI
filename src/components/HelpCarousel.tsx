'use client';

import { useState } from 'react';
import Image from 'next/image';
import { Button } from '@/components/ui/button';
import {
  Bot,
  Library,
  Notebook,
  Calendar,
  BrainCircuit,
  MessageSquare,
  Users,
  Wrench,
  LifeBuoy,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

const slideContent = [
    {
      icon: <Image src="/logo-simple.png" alt="KAI Logo" width={40} height={40} />,
      illustration: <Bot size={48} className="text-slate-300 dark:text-slate-600" />,
      title: "¿Qué es KAI? Tu Co-Piloto Inteligente",
      content: "KAI (Knowledge & Augmented Intelligence) es tu exocerebro digital. No solo almacena información, sino que la entiende, la conecta y te ayuda a usarla de forma inteligente para potenciar la inteligencia colectiva de tu equipo."
    },
    {
      icon: <MessageSquare size={24} className="text-cyan-500" />,
      illustration: <MessageSquare size={48} className="text-slate-300 dark:text-slate-600" />,
      title: "El Chat Inteligente (Web y Telegram)",
      content: "Interactúa con KAI de forma natural. Haz preguntas, genera contenido, resume información y más. KAI aprende de cada interacción para darte respuestas más personalizadas, disponible tanto en la web como en Telegram."
    },
    {
      icon: <Library size={24} className="text-cyan-500" />,
      illustration: <Library size={48} className="text-slate-300 dark:text-slate-600" />,
      title: "Gestión de Conocimiento (RAG)",
      content: "Transforma tus documentos (PDF, DOCX, TXT) en una base de conocimiento viva. KAI los procesa, entiende su significado y te permite hacer consultas sobre ellos, organizándolos en colecciones temáticas para búsquedas precisas."
    },
    {
      icon: <Notebook size={24} className="text-cyan-500" />,
      illustration: <Notebook size={48} className="text-slate-300 dark:text-slate-600" />,
      title: "Notas y Memorias",
      content: "Captura ideas, apuntes y tareas en notas rápidas. Además, KAI guarda 'memorias' sobre tus preferencias e intereses para personalizar la experiencia y conectar información de formas inesperadas."
    },
    {
      icon: <Calendar size={24} className="text-cyan-500" />,
      illustration: <Calendar size={48} className="text-slate-300 dark:text-slate-600" />,
      title: "Agenda y Recordatorios",
      content: "Gestiona tu calendario con lenguaje natural. Pide a KAI que agende reuniones o te ponga recordatorios. Mantén tu día organizado y enfócate en lo importante, KAI te avisará cuando lo necesites."
    },
    {
      icon: <Users size={24} className="text-cyan-500" />,
      illustration: <Users size={48} className="text-slate-300 dark:text-slate-600" />,
      title: "Equipos y Workspaces",
      content: "Organiza a tus colaboradores en equipos y crea Workspaces dedicados para cada proyecto. Centraliza documentos, notas y conversaciones para fomentar el conocimiento compartido y la colaboración eficiente."
    },
    {
      icon: <BrainCircuit size={24} className="text-cyan-500" />,
      illustration: <BrainCircuit size={48} className="text-slate-300 dark:text-slate-600" />,
      title: "Insights Proactivos",
      content: "KAI no solo responde, también piensa. Analiza continuamente tu información para encontrar conexiones ocultas, detectar duplicidades, señalar brechas de conocimiento y ofrecerte recomendaciones inteligentes."
    },
    {
      icon: <Wrench size={24} className="text-cyan-500" />,
      illustration: <Wrench size={48} className="text-slate-300 dark:text-slate-600" />,
      title: "Herramientas Avanzadas",
      content: "Expande tus capacidades con herramientas como el análisis web integral, el explorador de repositorios de GitHub para entender tu código, y el generador de mapas mentales para visualizar ideas complejas."
    },
    {
      icon: <LifeBuoy size={24} className="text-cyan-500" />,
      illustration: <LifeBuoy size={48} className="text-slate-300 dark:text-slate-600" />,
      title: "Soporte y Comunidad",
      content: "Nunca estarás solo. Accede a tutoriales, contacta a nuestro equipo de soporte y únete a la comunidad KAI para compartir experiencias y contribuir al crecimiento de la plataforma. Tu feedback es vital."
    }
  ];


export function HelpCarousel() {
  const [currentIndex, setCurrentIndex] = useState(0);

  const nextSlide = () => {
    setCurrentIndex((prevIndex) => (prevIndex + 1) % slideContent.length);
  };

  const prevSlide = () => {
    setCurrentIndex((prevIndex) => (prevIndex - 1 + slideContent.length) % slideContent.length);
  };
  
  const goToSlide = (index: number) => {
    setCurrentIndex(index);
  };

  return (
    <div className="relative w-full h-full flex flex-col justify-between p-6">
      <div className="overflow-hidden relative h-full">
        <div
          className="flex transition-transform duration-500 ease-in-out h-full"
          style={{ transform: `translateX(-${currentIndex * 100}%)` }}
        >
          {slideContent.map((slide, index) => (
            <div key={index} className="w-full flex-shrink-0 h-full flex flex-col justify-between items-center text-center px-4">
              <div className="flex flex-col items-center">
                <div className="mb-4">{slide.icon}</div>
                <h3 className="text-lg font-semibold mb-2">{slide.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {slide.content}
                </p>
              </div>
              <div className="mt-4">
                {slide.illustration}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex justify-between items-center pt-4">
        <Button
          variant="outline"
          size="icon"
          className="rounded-full bg-background/60 hover:bg-background/80"
          onClick={prevSlide}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <div className="flex gap-2">
          {slideContent.map((_, i) => (
            <button
              key={i}
              className={`w-2 h-2 rounded-full transition-colors ${
                currentIndex === i ? 'bg-cyan-500' : 'bg-muted-foreground/30 hover:bg-muted-foreground/50'
              }`}
              onClick={() => goToSlide(i)}
              aria-label={`Go to slide ${i + 1}`}
            />
          ))}
        </div>
        <Button
          variant="outline"
          size="icon"
          className="rounded-full bg-background/60 hover:bg-background/80"
          onClick={nextSlide}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
