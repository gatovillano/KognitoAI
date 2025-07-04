'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  Bot,
  Library,
  Notebook,
  Calendar,
  BrainCircuit,
  MessageSquare,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

const slideContent = [
    {
      icon: <BrainCircuit size={28} className="text-primary" />,
      title: "¿Qué es KAI? Tu Exocerebro Digital y Memoria Colectiva",
      content: "KAI (Knowledge & Augmented Intelligence) no es solo una inteligencia artificial; es tu exocerebro digital y la memoria colectiva viviente de tu equipo. Nuestra misión fundamental es aumentar la inteligencia colectiva, actuando como un co-piloto inteligente que conecta ideas, personas y conocimiento. Beneficios clave: Acelera la colaboración, facilita la toma de decisiones informadas y potencia las capacidades humanas al centralizar y contextualizar toda tu información."
    },
    {
      icon: <MessageSquare size={28} className="text-primary" />,
      title: "El Chat Inteligente: Tu Interfaz Principal con KAI",
      content: "Conversaciones Dinámicas: Interactúa con KAI en lenguaje natural para obtener respuestas instantáneas, resumir documentos extensos, generar borradores de texto o explorar nuevas ideas. Contexto Persistente: KAI recuerda tus conversaciones anteriores y tu base de conocimiento personal para ofrecer respuestas más relevantes y personalizadas. Asistencia Proactiva: Recibe sugerencias inteligentes basadas en el contexto de tus chats y las necesidades de tu equipo. Integración: Utiliza el chat para acceder y gestionar todas las demás funcionalidades de KAI, desde programar eventos hasta buscar documentos."
    },
    {
      icon: <Library size={28} className="text-primary" />,
      title: "Gestión de Conocimiento (RAG): Construye tu Base de Datos Inteligente",
      content: "Recuperación Aumentada por Generación (RAG): Sube y organiza tus documentos (PDFs, TXT, DOCX, etc.) para que KAI los procese, los entienda y los utilice como fuente de verdad. Colecciones de Conocimiento: Agrupa documentos por temas, proyectos o equipos para crear bases de conocimiento especializadas y facilitar la búsqueda. Extracción Inteligente: KAI extrae automáticamente información clave, conceptos y relaciones de tus documentos, haciéndolos accesibles y consultables al instante. Respuestas Contextualizadas: Cuando preguntas a KAI, no solo busca en la web; prioriza y utiliza la información de tus documentos para darte respuestas precisas y directamente aplicables a tu contexto."
    },
    {
      icon: <Notebook size={28} className="text-primary" />,
      title: "Notas y Memorias: Captura y Organiza Cada Idea",
      content: "Notas Rápidas: Guarda ideas, apuntes de reuniones, listas de tareas o cualquier información relevante que necesites recordar. Puedes categorizarlas para una mejor organización. Memoria a Largo Plazo: KAI almacena hechos, preferencias, hábitos e intereses que declares en tus conversaciones, construyendo un perfil más completo de ti y tus necesidades. Conexión Inteligente: Tanto tus notas como tus memorias se integran en la base de conocimiento de KAI, permitiendo que la IA encuentre conexiones inesperadas y te ofrezca insights proactivos. Acceso Fácil: Recupera tus notas y memorias en cualquier momento, ya sea buscando por palabras clave o pidiéndole a KAI que te las resuma."
    },
    {
      icon: <Calendar size={28} className="text-primary" />,
      title: "Agenda y Recordatorios: Optimiza tu Tiempo y Compromisos",
      content: "Programación de Eventos: Crea y gestiona tus eventos, reuniones y citas directamente desde KAI. Simplemente dile \"agenda una reunión para mañana a las 10 AM\" y KAI se encargará. Recordatorios Personalizados: Establece recordatorios para cualquier tarea o compromiso, desde \"recuérdame llamar a Juan en 30 minutos\" hasta \"avísame el lunes sobre el informe\". Sincronización: Mantén tu agenda personal y de equipo organizada, asegurando que nunca pierdas una fecha límite o un compromiso importante. Visión General: Consulta tu agenda para el día, la semana o cualquier fecha específica para tener siempre una visión clara de tus próximos pasos."
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
