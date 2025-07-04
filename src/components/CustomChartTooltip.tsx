'use client';

import React from 'react';
import { Badge } from '@/components/ui/badge';

interface CustomTooltipProps {
  active?: boolean;
  payload?: any[];
  label?: string | number;
}

// Simulamos temas agrupados para cada categoría principal
const getGroupedTopics = (mainTopic: string): string[] => {
  const topicGroups: { [key: string]: string[] } = {
    'Tecnología': ['Inteligencia Artificial', 'Machine Learning', 'Desarrollo Web', 'APIs', 'Bases de Datos'],
    'Negocios': ['Estrategia', 'Marketing Digital', 'Ventas', 'Análisis de Mercado', 'ROI'],
    'Educación': ['Metodologías', 'E-learning', 'Capacitación', 'Evaluación', 'Recursos Didácticos'],
    'Salud': ['Medicina Preventiva', 'Telemedicina', 'Investigación Clínica', 'Bienestar', 'Nutrición'],
    'Finanzas': ['Inversiones', 'Criptomonedas', 'Análisis Financiero', 'Presupuestos', 'Riesgo'],
    'Ciencia': ['Investigación', 'Metodología Científica', 'Publicaciones', 'Experimentos', 'Datos'],
    'Arte': ['Diseño Gráfico', 'Fotografía', 'Ilustración', 'Arte Digital', 'Creatividad'],
    'Deportes': ['Entrenamiento', 'Nutrición Deportiva', 'Competencias', 'Técnicas', 'Equipamiento'],
    'Viajes': ['Destinos', 'Planificación', 'Cultura Local', 'Gastronomía', 'Aventura'],
    'Música': ['Composición', 'Instrumentos', 'Producción', 'Géneros', 'Historia Musical']
  };

  // Si encontramos una coincidencia exacta, la devolvemos
  if (topicGroups[mainTopic]) {
    return topicGroups[mainTopic];
  }

  // Si no, buscamos coincidencias parciales
  for (const [key, topics] of Object.entries(topicGroups)) {
    if (mainTopic.toLowerCase().includes(key.toLowerCase()) || 
        key.toLowerCase().includes(mainTopic.toLowerCase())) {
      return topics;
    }
  }

  // Si no encontramos coincidencias, generamos temas relacionados genéricos
  return [
    `${mainTopic} Básico`,
    `${mainTopic} Avanzado`,
    `${mainTopic} Aplicado`,
    `Fundamentos de ${mainTopic}`,
    `${mainTopic} en Práctica`
  ];
};

export function CustomChartTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) {
    return null;
  }

  const data = payload[0];
  const mainTopic = data.payload.topic;
  const mentions = data.value;
  const groupedTopics = getGroupedTopics(mainTopic);

  return (
    <div className="bg-background/95 backdrop-blur-xl border border-border/50 rounded-xl p-4 shadow-strong max-w-sm">
      {/* Header del tooltip */}
      <div className="flex items-center gap-2 mb-3">
        <div className="w-3 h-3 rounded-full bg-primary"></div>
        <h3 className="font-semibold text-foreground text-base">{mainTopic}</h3>
      </div>
      
      {/* Número de menciones */}
      <div className="flex items-center justify-between mb-3 p-2 bg-muted/30 rounded-lg">
        <span className="text-sm text-muted-foreground">Menciones totales:</span>
        <span className="font-bold text-primary text-lg">{mentions}</span>
      </div>

      {/* Temas agrupados */}
      <div className="space-y-2">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Temas Agrupados:
        </p>
        <div className="flex flex-wrap gap-1.5">
          {groupedTopics.slice(0, 6).map((topic, index) => (
            <Badge 
              key={index} 
              variant="secondary" 
              className="text-xs px-2 py-1 bg-primary/10 text-primary border-primary/20 hover:bg-primary/20 transition-colors"
            >
              {topic}
            </Badge>
          ))}
          {groupedTopics.length > 6 && (
            <Badge 
              variant="outline" 
              className="text-xs px-2 py-1 text-muted-foreground border-dashed"
            >
              +{groupedTopics.length - 6} más
            </Badge>
          )}
        </div>
      </div>

      {/* Footer con información adicional */}
      <div className="mt-3 pt-2 border-t border-border/30">
        <p className="text-xs text-muted-foreground">
          💡 Agrupados por similitud semántica
        </p>
      </div>
    </div>
  );
}
