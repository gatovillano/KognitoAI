'use client';

import React from 'react';
import { Chart } from 'react-google-charts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface ProjectItem {
  id: string;
  type: 'task' | 'event';
  description: string;
  summary?: string;
  created_at?: string;
  due_date?: string;
  event_date?: string;
  event_time?: string;
  duration_minutes?: number;
  is_completed?: boolean;
}

interface GanttChartProps {
  items: ProjectItem[];
}

export const GanttChart: React.FC<GanttChartProps> = ({ items }) => {
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

  const data = items.map(item => {
    const startDate = item.created_at ? new Date(item.created_at) : new Date();
    const endDate = item.due_date ? new Date(item.due_date) : new Date(startDate.getTime() + (item.duration_minutes || 60) * 60 * 1000);

    return [
      item.id,
      item.type === 'task' ? item.description : item.summary,
      item.type,
      startDate,
      endDate,
      null,
      item.type === 'task' ? (item.is_completed ? 100 : 0) : 0,
      null,
    ];
  });

  const chartData = [columns, ...data];

  const options = {
    height: 400,
    gantt: {
      trackHeight: 40,
      barHeight: 30,
      barCornerRadius: 4,
      palette: [
        {
          color: '#3b82f6', // blue for tasks
          dark: '#1e40af',
          light: '#93c5fd'
        },
        {
          color: '#10b981', // green for events
          dark: '#047857',
          light: '#6ee7b7'
        }
      ],
      criticalPathEnabled: false,
      innerGridHorizLine: {
        stroke: '#e5e7eb',
        strokeWidth: 1
      },
      innerGridTrack: { fill: '#f9fafb' },
      innerGridDarkTrack: { fill: '#f3f4f6' },
      labelStyle: {
        fontName: 'Inter',
        fontSize: 13,
        color: '#374151'
      }
    },
  };

  return (
    <Card className="shadow-soft border-gray-100">
      <CardHeader className="pb-3">
        <CardTitle className="text-xl font-bold text-gray-800">Diagrama de Gantt</CardTitle>
        <p className="text-sm text-gray-500 mt-1">Vista temporal del proyecto</p>
      </CardHeader>
      <CardContent>
        <div className="rounded-lg overflow-hidden border border-gray-100">
          <Chart
            chartType="Gantt"
            width="100%"
            height="400px"
            data={chartData}
            options={options}
          />
        </div>
      </CardContent>
    </Card>
  );
};