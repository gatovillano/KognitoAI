'use client';

import React from 'react';
import { Badge } from '@/components/ui/badge';

interface CustomTooltipProps {
  active?: boolean;
  payload?: any[];
  label?: string | number;
}



export function CustomChartTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) {
    return null;
  }

  const data = payload[0];
  const mainTopic = data.payload.topic;
  const mentions = data.value;
  const description = data.payload.description || "Agrupación de temas relacionados";
  const topics = data.payload.topics || [];

  return (
    <div className="bg-background/95 backdrop-blur-xl border border-border/50 rounded-xl p-4 shadow-strong max-w-sm">
      {/* Header del tooltip */}
      <div className="flex items-center gap-2 mb-3">
        <div className="w-3 h-3 rounded-full bg-primary"></div>
        <h3 className="font-semibold text-foreground text-base">{mainTopic}</h3>
      </div>

      {/* Descripción del concepto */}
      <div className="mb-3 p-3 bg-muted/20 rounded-lg border border-border/30">
        <p className="text-sm text-foreground leading-relaxed">{description}</p>
      </div>

      {/* Número de menciones */}
      <div className="flex items-center justify-between mb-3 p-2 bg-muted/30 rounded-lg">
        <span className="text-sm text-muted-foreground">Menciones totales:</span>
        <span className="font-bold text-primary text-lg">{mentions}</span>
      </div>

      {/* Temas agrupados */}
      {topics.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Temas Incluidos ({topics.length}):
          </p>
          <div className="flex flex-wrap gap-1.5">
            {topics.slice(0, 6).map((topic: string, index: number) => (
              <Badge
                key={index}
                variant="secondary"
                className="text-xs px-2 py-1 bg-primary/10 text-primary border-primary/20 hover:bg-primary/20 transition-colors"
              >
                {topic}
              </Badge>
            ))}
            {topics.length > 6 && (
              <Badge
                variant="outline"
                className="text-xs px-2 py-1 text-muted-foreground border-dashed"
              >
                +{topics.length - 6} más
              </Badge>
            )}
          </div>
        </div>
      )}

      {/* Footer con información adicional */}
      <div className="mt-3 pt-2 border-t border-border/30">
        <p className="text-xs text-muted-foreground">
          💡 Agrupados por similitud semántica
        </p>
      </div>
    </div>
  );
}
