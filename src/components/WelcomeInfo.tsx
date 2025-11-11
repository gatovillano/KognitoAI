import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

const features = [
  {
    title: "1. Gestión de Conocimiento (RAG)",
    items: [
      "Colecciones y Documentos: Organiza tu información en colecciones temáticas para búsquedas semánticas eficientes.",
      "Integración con GitHub: Añade repositorios como fuente de conocimiento.",
      "Grafo de Conocimiento: Extrae entidades y relaciones para obtener respuestas más ricas.",
    ],
  },
  {
    title: "2. Análisis de Datos e Insights",
    items: [
      "Análisis Profundo: Obtén resúmenes, temas clave y análisis de sentimiento de tus documentos.",
      "Insights Proactivos: Kognito encuentra conexiones y brechas de conocimiento automáticamente.",
      "Análisis de Código y Conversaciones: Inspecciona código y revisa historiales de chat para encontrar patrones.",
    ],
  },
  {
    title: "3. Interacción Inteligente",
    items: [
      "Chat con Modos: Utiliza modos especializados para análisis, búsqueda web o investigación profunda.",
      "Transcripción de Audio: Graba y transcribe mensajes de voz directamente en el chat.",
      "Integración con Telegram: Interactúa con Kognito desde la comodidad de Telegram.",
    ],
  },
  {
    title: "4. Organización y Colaboración",
    items: [
      "Workspaces y Equipos: Crea espacios de trabajo aislados para organizar y compartir tu conocimiento con otros.",
      "Gestión de Contactos y Agenda: Vincula notas, documentos y eventos a perfiles de contacto.",
      "Formularios Dinámicos: Crea formularios personalizables para recolectar información estructurada.",
    ],
  },
];

export function WelcomeInfo() {
  return (
    <div className="w-full">
      <Accordion type="single" collapsible className="w-full">
        {features.map((feature, index) => (
          <AccordionItem value={`item-${index}`} key={index}>
            <AccordionTrigger className="text-lg font-semibold hover:no-underline">
              {feature.title}
            </AccordionTrigger>
            <AccordionContent>
              <ul className="list-disc space-y-2 pl-6 text-sm text-muted-foreground">
                {feature.items.map((item, itemIndex) => (
                  <li key={itemIndex}>{item}</li>
                ))}
              </ul>
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </div>
  );
}

export default WelcomeInfo;