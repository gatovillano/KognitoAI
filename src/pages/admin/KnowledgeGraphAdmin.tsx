'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Home, Settings, Bug, BarChart3 } from 'lucide-react';
import EntityQualityDashboard from '@/components/admin/EntityQualityDashboard';

const KnowledgeGraphAdmin = () => {
  const router = useRouter();

  return (
    <div className="container mx-auto p-4 md:p-6 lg:p-8">
      {/* Breadcrumbs */}
      <div className="flex items-center space-x-2 text-sm text-muted-foreground mb-6">
        <Button variant="ghost" size="sm" onClick={() => router.push('/dashboard')}>
          <Home className="h-4 w-4 mr-1" />
          Dashboard
        </Button>
        <span>/</span>
        <span className="font-medium text-foreground">Administración del Grafo</span>
      </div>

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl md:text-4xl font-bold flex items-center gap-3">
          <Settings className="h-8 w-8 text-primary" />
          Administración del Grafo de Conocimiento
        </h1>
        <p className="text-lg text-muted-foreground mt-2 max-w-3xl">
          Herramientas avanzadas para gestionar, revisar y optimizar la calidad de las entidades y relaciones en el grafo de conocimiento.
        </p>
      </div>

      <Tabs defaultValue="quality-control" className="w-full">
        <TabsList className="grid w-full grid-cols-1 sm:grid-cols-2 md:grid-cols-4 h-auto sm:h-12">
          <TabsTrigger value="dashboard"> 
            <Bug className="h-4 w-4 mr-2" />
            Dashboard
          </TabsTrigger>
          <TabsTrigger value="quality-control"> 
            <Bug className="h-4 w-4 mr-2" />
            Control de Calidad
          </TabsTrigger>
          <TabsTrigger value="analytics">
            <BarChart3 className="h-4 w-4 mr-2" />
            Estadísticas
          </TabsTrigger>
          <TabsTrigger value="settings">
            <Settings className="h-4 w-4 mr-2" />
            Configuración
          </TabsTrigger>
        </TabsList>

        <TabsContent value="dashboard" className="mt-6">
          <EntityQualityDashboard />
        </TabsContent>

        <TabsContent value="quality-control" className="mt-6">
          <EntityQualityDashboard />
        </TabsContent>

        <TabsContent value="analytics" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Estadísticas Avanzadas</CardTitle>
              <CardDescription>Visualizaciones y métricas detalladas sobre la estructura y contenido del grafo.</CardDescription>
            </CardHeader>
            <CardContent className="h-64 flex items-center justify-center">
              <p className="text-muted-foreground">Próximamente...</p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="settings" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Configuración del Grafo</CardTitle>
              <CardDescription>Ajustes sobre el procesamiento, extracción y análisis de entidades.</CardDescription>
            </CardHeader>
            <CardContent className="h-64 flex items-center justify-center">
              <p className="text-muted-foreground">Próximamente...</p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Consejos */}
      <Card className="mt-8 bg-muted/50">
        <CardHeader>
          <CardTitle>💡 Consejos para el Control de Calidad</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-disc list-inside space-y-2 text-sm text-muted-foreground">
            <li>
              <strong>Ejecuta revisiones regulares:</strong> Realiza controles de calidad después de procesar nuevos documentos para mantener la integridad del grafo.
            </li>
            <li>
              <strong>Revisa antes de aplicar:</strong> Siempre es buena idea revisar las correcciones sugeridas antes de aplicarlas automáticamente en bloque.
            </li>
            <li>
              <strong>Monitorea las estadísticas:</strong> Una puntuación de calidad consistentemente superior al 85% indica un grafo de conocimiento saludable y confiable.
            </li>
            <li>
              <strong>Fusiona duplicados:</strong> Las entidades duplicadas pueden afectar negativamente la precisión de las consultas y los análisis.
            </li>
            <li>
              <strong>Elimina entidades inválidas:</strong> Artículos, preposiciones y otras palabras comunes no aportan valor semántico y deben ser eliminadas.
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
};

export default KnowledgeGraphAdmin;