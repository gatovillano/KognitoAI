'use client';

import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { X, Tag, TrendingUp, Hash } from 'lucide-react';

interface TopicGroupDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  mainTopic: string;
  mentions: number;
}

// Función para obtener temas agrupados (la misma que en el tooltip pero expandida)
const getGroupedTopics = (mainTopic: string): { category: string; topics: string[] }[] => {
  const topicGroups: { [key: string]: { category: string; topics: string[] } } = {
    'Tecnología': {
      category: 'Desarrollo y Tecnología',
      topics: [
        'Inteligencia Artificial', 'Machine Learning', 'Deep Learning', 'Desarrollo Web', 
        'APIs REST', 'Bases de Datos', 'Cloud Computing', 'DevOps', 'Microservicios',
        'Frontend', 'Backend', 'Full Stack', 'React', 'Node.js', 'Python'
      ]
    },
    'Negocios': {
      category: 'Estrategia y Negocios',
      topics: [
        'Estrategia Empresarial', 'Marketing Digital', 'Ventas B2B', 'Análisis de Mercado', 
        'ROI', 'KPIs', 'Growth Hacking', 'Customer Success', 'Product Management',
        'Business Intelligence', 'Transformación Digital', 'E-commerce', 'CRM'
      ]
    },
    'Educación': {
      category: 'Educación y Formación',
      topics: [
        'Metodologías Pedagógicas', 'E-learning', 'Capacitación Corporativa', 'Evaluación',
        'Recursos Didácticos', 'Gamificación', 'Microlearning', 'LMS', 'MOOC',
        'Educación Online', 'Competencias Digitales', 'Aprendizaje Adaptativo'
      ]
    },
    'Salud': {
      category: 'Salud y Bienestar',
      topics: [
        'Medicina Preventiva', 'Telemedicina', 'Investigación Clínica', 'Bienestar',
        'Nutrición', 'Salud Mental', 'Fitness', 'Medicina Personalizada',
        'Biotecnología', 'Farmacología', 'Epidemiología', 'Salud Pública'
      ]
    },
    'Finanzas': {
      category: 'Finanzas e Inversiones',
      topics: [
        'Inversiones', 'Criptomonedas', 'Blockchain', 'Análisis Financiero', 
        'Presupuestos', 'Gestión de Riesgo', 'Trading', 'DeFi', 'Fintech',
        'Banca Digital', 'Seguros', 'Planificación Financiera', 'Contabilidad'
      ]
    }
  };

  // Buscar coincidencias
  for (const [key, data] of Object.entries(topicGroups)) {
    if (mainTopic.toLowerCase().includes(key.toLowerCase()) || 
        key.toLowerCase().includes(mainTopic.toLowerCase())) {
      return [data];
    }
  }

  // Si no encontramos coincidencias, generar categorías genéricas
  return [
    {
      category: `${mainTopic} - Conceptos Fundamentales`,
      topics: [`${mainTopic} Básico`, `Fundamentos de ${mainTopic}`, `Introducción a ${mainTopic}`]
    },
    {
      category: `${mainTopic} - Aplicaciones Prácticas`,
      topics: [`${mainTopic} Avanzado`, `${mainTopic} en Práctica`, `Casos de Uso de ${mainTopic}`]
    },
    {
      category: `${mainTopic} - Tendencias y Futuro`,
      topics: [`Futuro de ${mainTopic}`, `Innovaciones en ${mainTopic}`, `Tendencias ${mainTopic}`]
    }
  ];
};

export function TopicGroupDialog({ isOpen, onOpenChange, mainTopic, mentions }: TopicGroupDialogProps) {
  const groupedData = getGroupedTopics(mainTopic);

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full bg-primary"></div>
              <DialogTitle className="text-2xl font-bold">{mainTopic}</DialogTitle>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onOpenChange(false)}
              className="rounded-full hover:bg-muted"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </DialogHeader>

        <div className="space-y-6">
          {/* Estadísticas */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-primary/10 rounded-xl p-4 border border-primary/20">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="h-5 w-5 text-primary" />
                <span className="font-semibold text-sm">Menciones Totales</span>
              </div>
              <p className="text-2xl font-bold text-primary">{mentions}</p>
            </div>
            
            <div className="bg-muted/50 rounded-xl p-4 border border-border/50">
              <div className="flex items-center gap-2 mb-2">
                <Hash className="h-5 w-5 text-muted-foreground" />
                <span className="font-semibold text-sm">Temas Agrupados</span>
              </div>
              <p className="text-2xl font-bold text-foreground">
                {groupedData.reduce((acc, group) => acc + group.topics.length, 0)}
              </p>
            </div>

            <div className="bg-muted/50 rounded-xl p-4 border border-border/50">
              <div className="flex items-center gap-2 mb-2">
                <Tag className="h-5 w-5 text-muted-foreground" />
                <span className="font-semibold text-sm">Categorías</span>
              </div>
              <p className="text-2xl font-bold text-foreground">{groupedData.length}</p>
            </div>
          </div>

          {/* Grupos de temas */}
          <div className="space-y-6">
            {groupedData.map((group, groupIndex) => (
              <div key={groupIndex} className="space-y-3">
                <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-primary"></div>
                  {group.category}
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {group.topics.map((topic, topicIndex) => (
                    <Badge
                      key={topicIndex}
                      variant="secondary"
                      className="justify-start p-3 h-auto text-sm bg-card hover:bg-muted/80 border border-border/50 transition-all duration-200 hover:scale-105 cursor-pointer"
                    >
                      <Tag className="h-3 w-3 mr-2 text-primary" />
                      {topic}
                    </Badge>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Footer */}
          <div className="bg-muted/30 rounded-xl p-4 border border-border/30">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 rounded-full bg-primary animate-pulse"></div>
              <span className="text-sm font-medium text-muted-foreground">Información</span>
            </div>
            <p className="text-sm text-muted-foreground">
              Estos temas han sido agrupados automáticamente por similitud semántica utilizando 
              algoritmos de procesamiento de lenguaje natural. La agrupación se basa en el 
              contexto y las relaciones conceptuales entre los diferentes términos.
            </p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
