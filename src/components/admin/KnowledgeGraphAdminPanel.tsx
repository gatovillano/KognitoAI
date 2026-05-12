'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Home, Settings, Bug, BarChart3, Network, Sparkles } from 'lucide-react';
import EntityQualityDashboard from '@/components/admin/EntityQualityDashboard';

export default function KnowledgeGraphAdminPanel() {
  return (
    <div className="container mx-auto p-4 md:p-6 lg:p-8">
      <div className="flex items-center space-x-2 text-sm text-muted-foreground mb-6">
        <Button variant="ghost" size="sm" asChild>
          <Link href="/dashboard">
            <Home className="h-4 w-4 mr-1" />
            Dashboard
          </Link>
        </Button>
        <span>/</span>
        <Button variant="ghost" size="sm" asChild>
          <Link href="/admin">Administración</Link>
        </Button>
        <span>/</span>
        <span className="font-medium text-foreground">Grafo de Conocimiento</span>
      </div>

      <div className="mb-8 space-y-4">
        <div className="flex items-center gap-3">
          <div className="rounded-2xl border border-primary/20 bg-primary/10 p-3">
            <Network className="h-7 w-7 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl md:text-4xl font-bold flex items-center gap-3">
              Administración del Grafo de Conocimiento
            </h1>
            <p className="text-lg text-muted-foreground mt-2 max-w-3xl">
              Revisa la salud del grafo, detecta entidades problemáticas y aplica correcciones sobre el conocimiento consolidado.
            </p>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <Card className="border-primary/15 bg-primary/5">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Bug className="h-4 w-4 text-primary" />
                Control de calidad
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Detecta duplicados, ruido semántico, tipos mal clasificados y fusiones sugeridas.
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-primary" />
                Estadísticas
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Consulta el volumen del grafo, la distribución por tipos y el nivel general de calidad.
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" />
                Acciones administrativas
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Usa esta vista como panel operativo antes de exponer ajustes más delicados al resto del producto.
            </CardContent>
          </Card>
        </div>
      </div>

      <Tabs defaultValue="quality-control" className="w-full">
        <TabsList className="grid w-full grid-cols-1 sm:grid-cols-2 md:grid-cols-4 h-auto sm:h-12">
          <TabsTrigger value="dashboard">
            <Network className="h-4 w-4 mr-2" />
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
              <CardDescription>
                Espacio preparado para visualizaciones más densas del grafo: crecimiento, distribución de tipos, confianza media y densidad relacional.
              </CardDescription>
            </CardHeader>
            <CardContent className="h-64 flex items-center justify-center text-center text-muted-foreground">
              Próximamente: tendencias del grafo, calidad por dataset y métricas por workspace.
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="settings" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Configuración del Grafo</CardTitle>
              <CardDescription>
                Futuro panel para reglas de extracción, thresholds y políticas de revisión antes de auto-aplicar correcciones.
              </CardDescription>
            </CardHeader>
            <CardContent className="h-64 flex items-center justify-center text-center text-muted-foreground">
              Próximamente: thresholds de confianza, reglas de merge y políticas de limpieza.
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Card className="mt-8 bg-muted/50">
        <CardHeader>
          <CardTitle>Consejos para la administración del grafo</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p><strong>Revisa antes de aplicar en lote:</strong> las fusiones y eliminaciones son más seguras si primero validas el contexto.</p>
          <p><strong>Úsalo como panel global:</strong> esta vista tiene sentido a nivel de cuenta o sistema, no como vista de documento individual.</p>
          <p><strong>Complementa, no reemplaza:</strong> el grafo por workspace puede vivir dentro del workspace; el admin debe quedar para mantenimiento y gobernanza.</p>
        </CardContent>
      </Card>
    </div>
  );
}
