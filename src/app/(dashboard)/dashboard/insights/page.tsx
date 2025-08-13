// En: src/app/(dashboard)/dashboard/insights/page.tsx

'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { InsightDetailDialog } from '@/components/InsightDetailDialog';
import { Bot, Library, FileText, FolderKanban } from 'lucide-react';
import Link from 'next/link';

// Tipos
interface Insight {
  id: string;
  type: string;
  summary: string;
  created_at: string;
  related_items: any[];
  action_suggestion?: string;
}

export default function AllInsightsPage() {
  const [insights, setInsights] = useState<Insight[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [viewingInsight, setViewingInsight] = useState<Insight | null>(null);

  useEffect(() => {
    const fetchAllInsights = async () => {
      setIsLoading(true);
      try {
        // Asumimos que la API puede devolver todos los insights con un parámetro
        const response = await apiClient.post('/api/dashboard-insights', { all: true });
        setInsights(response.data.proactive_insights || []);
      } catch (error) {
        toast.error('No se pudieron cargar los insights.');
        console.error("Fetch all insights error:", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchAllInsights();
  }, []);

  const getInsightIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'pattern':
        return <Bot className="h-5 w-5 text-primary" />;
      case 'connection':
        return <Library className="h-5 w-5 text-primary" />;
      case 'project':
        return <FolderKanban className="h-5 w-5 text-primary" />;
      default:
        return <FileText className="h-5 w-5 text-primary" />;
    }
  };

  if (isLoading) {
    return <div className="p-6 text-center">Cargando todos los descubrimientos...</div>;
  }

  return (
    <>
      <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden space-y-6">
        <div>
          <Link href="/dashboard" className="text-sm text-primary hover:underline mb-2 inline-block">
            &larr; Volver al Dashboard
          </Link>
          <h1 className="text-3xl font-bold">Todos los Descubrimientos Proactivos</h1>
          <p className="text-muted-foreground">Explora todos los patrones y conexiones que Kognito ha encontrado en tu conocimiento.</p>
        </div>

        {insights.length > 0 ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
            {insights.map(insight => (
              <Card key={insight.id} className="rounded-2xl hover:border-primary/80 transition-colors cursor-pointer flex flex-col" onClick={() => setViewingInsight(insight)}>
                <CardHeader>
                  <div className="flex items-center gap-2">
                     {getInsightIcon(insight.type)}
                     <CardTitle className="text-base">{insight.type.charAt(0).toUpperCase() + insight.type.slice(1)}</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="flex-grow flex flex-col justify-between">
                  <p className="text-sm text-muted-foreground line-clamp-4 mb-3">{insight.summary}</p>
                  <div className="text-xs space-y-1 mt-auto">
                    <p className="font-semibold">Ítems Relacionados:</p>
                    {insight.related_items.slice(0, 3).map((item, idx) => (
                      <p key={idx} className="flex items-center gap-1.5 text-muted-foreground truncate">
                        <FileText className="h-3 w-3" />
                        {item.title || item.reference}
                      </p>
                    ))}
                     {insight.related_items.length > 3 && (
                      <p className="text-muted-foreground text-xs">y {insight.related_items.length - 3} más...</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="text-center py-10 col-span-full">
            <p className="text-muted-foreground">No se encontraron descubrimientos proactivos.</p>
          </div>
        )}
      </div>
      
      <InsightDetailDialog 
        isOpen={!!viewingInsight} 
        onOpenChange={(open: boolean) => !open && setViewingInsight(null)}
        insight={viewingInsight}
      />
    </>
  );
}
