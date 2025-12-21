"use client";

import { useEffect } from "react";
import { useWebSocketContext } from "@/contexts/WebSocketContext";
import { toast } from "sonner";
import { BellRing, Sparkles } from "lucide-react";

// Define la estructura del payload del mensaje que esperamos del backend
interface ProactiveInsightPayload {
  type: "proactive_insight";
  content: string;
  insight_type: string;
  confidence: number;
  action_suggestion?: string;
  insight_id: string;
}

/**
 * Un componente "invisible" que se encarga de escuchar los insights proactivos
 * que llegan por WebSocket y mostrarlos como notificaciones (toasts).
 */
export function ProactiveInsightNotifier() {
  const { registerMessageHandler } = useWebSocketContext();

  useEffect(() => {
    // Define el manejador para los mensajes de insights
    const handler = (message: any) => {
      // Nos aseguramos de que el mensaje es del tipo que nos interesa
      if (message.type === "proactive_insight") {
        const payload = message as ProactiveInsightPayload;

        // Usamos la librería `sonner` para mostrar un toast.
        // Es un toast enriquecido con un ícono y un título.
        toast(payload.content, {
          icon: <Sparkles className="h-5 w-5 text-yellow-400" />,
          description: `Insight de tipo: ${payload.insight_type}. Confianza: ${(payload.confidence * 100).toFixed(0)}%`,
          action: {
            label: "Ver detalle",
            onClick: () => {
              // TODO: Implementar navegación a la página del insight
              console.log(`Navegar al insight con ID: ${payload.insight_id}`);
              // Por ejemplo: router.push(`/insights/${payload.insight_id}`);
            },
          },
        });
      }
    };

    // Registra el manejador y obtiene la función de limpieza.
    const unregister = registerMessageHandler(handler);

    // Limpieza: la función devuelta por registerMessageHandler se encarga de desregistrar.
    return unregister;
  }, [registerMessageHandler]);

  // Este componente no renderiza nada en el DOM, solo maneja lógica.
  return null;
}
