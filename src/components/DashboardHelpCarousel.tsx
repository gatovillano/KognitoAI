'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  BrainCircuit,
  BookOpen,
  Calendar,
  StickyNote,
  Users,
  ImageIcon,
  ClipboardList,
  BarChart,
  Library,
  Sparkles,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

const slideContent = [
    {
      icon: <BrainCircuit size={28} className="text-primary" />,
      title: "¿Qué es KognitoAI?",
      content: "KognitoAI es tu exocerebro digital, un copiloto inteligente diseñado para aumentar tu inteligencia y la de tu equipo. Centraliza tu información, la conecta de formas inesperadas y te ayuda a tomar decisiones más informadas, actuando como la memoria colectiva viviente de tu organización."
    },
    {
      icon: <Library size={28} className="text-primary" />,
      title: "Módulo de Conocimientos (RAG)",
      content: "Tu biblioteca personal y de equipo. Sube documentos (PDFs, webs, repositorios de GitHub) y organízalos en 'Colecciones'. Kognito los procesa para que puedas conversar con ellos, obtener resúmenes y recibir respuestas basadas en tu propia información."
    },
    {
      icon: <Calendar size={28} className="text-primary" />,
      title: "Módulo de Agenda",
      content: "Tu centro de organización temporal. Programa eventos, crea recordatorios y gestiona tus tareas directamente desde el chat. Vincula eventos a notas o perfiles de contacto para tener una visión 360° de tus compromisos."
    },
    {
      icon: <StickyNote size={28} className="text-primary" />,
      title: "Módulo de Notas",
      content: "Tu bloc de notas inteligente. Captura ideas, apuntes de reuniones o cualquier información al instante. Kognito integra tus notas en su base de conocimiento, permitiendo encontrar conexiones entre tus pensamientos y los documentos que has subido."
    },
    {
      icon: <Users size={28} className="text-primary" />,
      title: "Módulo de Perfiles de Contacto",
      content: "Crea un CRM personal. Registra perfiles para las personas con las que interactúas y vincula notas, eventos o documentos relacionados. Ten toda la información relevante sobre un contacto a un solo clic de distancia."
    },
    {
      icon: <ImageIcon size={28} className="text-primary" />,
      title: "Módulo de Galerías",
      content: "Tu archivo visual. Organiza imágenes en 'Galerías' o álbumes temáticos. Kognito genera miniaturas y te permite gestionar y visualizar tus recursos gráficos de forma ordenada y accesible."
    },
    {
      icon: <ClipboardList size={28} className="text-primary" />,
      title: "Módulo de Formularios",
      content: "Recolecta información de manera estructurada. Diseña formularios dinámicos para encuestas, feedback o cualquier tipo de recolección de datos. Las respuestas se almacenan y pueden ser analizadas por Kognito."
    },
    {
      icon: <BarChart size={28} className="text-primary" />,
      title: "Módulo de Análisis e Insights",
      content: "El poder predictivo de Kognito. Pide análisis profundos de tus datos para encontrar tendencias, temas clave y brechas de conocimiento. Además, el sistema genera 'Insights Proactivos' automáticamente, revelando conexiones que no habías visto."
    },
    {
      icon: <BookOpen size={28} className="text-primary" />,
      title: "Workspaces y Equipos",
      content: "Colaboración sin caos. Usa 'Workspaces' para separar contextos (ej. Personal, Trabajo) y crea 'Equipos' para compartir conocimiento y colaborar con otros usuarios en un entorno seguro y organizado."
    },
    {
      icon: <Sparkles size={28} className="text-primary" />,
      title: "¡Explora tu Nuevo Potencial!",
      content: "Esto es solo el comienzo. Kognito tiene muchas más funcionalidades esperando a ser descubiertas. Te invitamos a explorar, experimentar y conversar con tu nuevo copiloto de conocimiento. ¡El límite es tu curiosidad!"
    }
  ];


export function DashboardHelpCarousel() {
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
            <div key={index} className="w-full flex-shrink-0 h-full flex flex-col justify-center items-center text-center px-6">
              <div className="flex flex-col items-center max-w-md mx-auto">
                <div className="mb-6 p-4 rounded-full bg-primary/10 border border-primary/20">
                  {slide.icon}
                </div>
                <h3 className="text-2xl font-bold mb-6 text-foreground">{slide.title}</h3>
                <p className="text-base text-muted-foreground leading-relaxed text-center">
                  {slide.content}
                </p>
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
                currentIndex === i ? 'bg-primary' : 'bg-muted-foreground/30 hover:bg-muted-foreground/50'
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
