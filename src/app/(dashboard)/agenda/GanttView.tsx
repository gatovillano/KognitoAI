'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Chart } from 'react-google-charts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import apiClient from '@/lib/api';
import { AgendaEvent, TaskResponse } from './types';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { toast } from 'sonner';
import { GanttChartSquare, Info } from 'lucide-react';

export function GanttView() {
  const [items, setItems] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchItems = useCallback(async () => {
    setIsLoading(true);
    try {
      const [eventsResponse, tasksResponse] = await Promise.all([
        apiClient.post('/api/list-events', { include_past: true }),
        apiClient.get('/api/tasks')
      ]);

      const columns = [
        { type: 'string', label: 'Task ID' },
        { type: 'string', label: 'Task Name' },
        { type: 'string', label: 'Resource' },
        { type: 'date', label: 'Start Date' },
        { type: 'date', label: 'End Date' },
        { type: 'number', label: 'Duration' },
        { type: 'number', label: 'Percent Complete' },
        { type: 'string', label: 'Dependencies' },
      ];

      const rows: any[] = [];

      eventsResponse.data.filter((event: AgendaEvent) => event.status !== 'Completado').forEach((event: AgendaEvent) => {
        const start = new Date(event.event_datetime_local);
        const end = event.end_date ? new Date(event.end_date) : new Date(start.getTime() + 60 * 60 * 1000);
        
        rows.push([
          `event-${event.id}`,
          event.summary,
          'Evento',
          start,
          end,
          null,
          0,
          null,
        ]);
      });

      tasksResponse.data.filter((task: TaskResponse) => !task.is_completed).forEach((task: TaskResponse) => {
        const start = task.start_date ? new Date(task.start_date) : new Date(task.created_at);
        const end = task.end_date ? new Date(task.end_date) : (task.due_date ? new Date(task.due_date) : new Date(start.getTime() + 24 * 60 * 60 * 1000));
        
        rows.push([
          `task-${task.id}`,
          task.description,
          'Tarea',
          start,
          end,
          null,
          task.is_completed ? 100 : 0,
          null,
        ]);
      });

      setItems([columns as any, ...rows]);
    } catch (error) {
      console.error('Error fetching items for Gantt:', error);
      toast.error('Error al cargar datos del Gantt.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  const options = {
    height: items.length * 45 + 50,
    gantt: {
      trackHeight: 40,
      barHeight: 30,
      barCornerRadius: 8,
      palette: [
        {
          color: '#8b5cf6', // violet for events
          dark: '#6d28d9',
          light: '#c4b5fd'
        },
        {
          color: '#10b981', // green for tasks
          dark: '#059669',
          light: '#6ee7b7'
        }
      ],
      criticalPathEnabled: false,
      innerGridHorizLine: {
        stroke: '#e2e8f0',
        strokeWidth: 1
      },
      innerGridTrack: { fill: 'transparent' },
      innerGridDarkTrack: { fill: 'rgba(0,0,0,0.02)' },
      labelStyle: {
        fontName: 'Inter',
        fontSize: 12,
        color: '#64748b'
      }
    },
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <LoadingSpinner />
        <p className="text-muted-foreground font-medium animate-pulse">Generando cronograma...</p>
      </div>
    );
  }

  return (
    <Card className="border-border/40 bg-card/40 backdrop-blur-xl rounded-[2.5rem] overflow-hidden shadow-sm animate-in fade-in zoom-in-95 duration-700">
      <CardHeader className="p-8 pb-4 flex flex-row items-center justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-primary/10 text-primary">
              <GanttChartSquare className="h-6 w-6" />
            </div>
            <CardTitle className="text-2xl font-black tracking-tight">Cronograma de Actividades</CardTitle>
          </div>
          <p className="text-muted-foreground text-sm font-medium">Visualización temporal de tus compromisos y responsabilidades.</p>
        </div>
        <div className="flex items-center gap-2 bg-primary/5 px-4 py-2 rounded-2xl border border-primary/10">
           <Info className="h-4 w-4 text-primary" />
           <span className="text-[10px] font-black uppercase tracking-widest text-primary">Vista Interactiva</span>
        </div>
      </CardHeader>
      <CardContent className="p-8">
        {items.length > 1 ? (
          <div className="rounded-[2rem] overflow-hidden border border-border/40 bg-background/50 p-4 shadow-inner">
            <Chart
              chartType="Gantt"
              width="100%"
              height={`${Math.max(400, items.length * 45 + 50)}px`}
              data={items}
              options={options}
            />
          </div>
        ) : (
          <div className="py-20 text-center border-2 border-dashed border-border/40 rounded-[2.5rem] bg-card/20">
            <p className="text-xs font-black text-muted-foreground/60 uppercase tracking-[0.2em]">No hay suficientes datos para generar el diagrama</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
