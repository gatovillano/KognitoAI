'use client';

import React, { useState, useCallback } from 'react';
import apiClient from '@/lib/api'; // Importar apiClient
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { useToast } from '@/hooks/use-toast'; // Importación corregida

interface InsightGeneratorFormProps {
  accountId: string; // El accountId se pasará como prop
}

const InsightGeneratorForm: React.FC<InsightGeneratorFormProps> = ({ accountId }) => {
  const [sinceDaysAgo, setSinceDaysAgo] = useState<string>('');
  const [topicKeywords, setTopicKeywords] = useState<string>('');
  const [topK, setTopK] = useState<string>('20');
  const [includeNotes, setIncludeNotes] = useState<boolean>(true);
  const [includeDocuments, setIncludeDocuments] = useState<boolean>(true);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const { toast } = useToast(); // Hook para mostrar notificaciones

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setTaskId(null);

    const payload = {
      account_id: accountId,
      since_days_ago: sinceDaysAgo ? parseInt(sinceDaysAgo, 10) : undefined,
      topic_keywords: topicKeywords ? topicKeywords.split(',').map(kw => kw.trim()).filter(kw => kw.length > 0) : undefined,
      top_k: topK ? parseInt(topK, 10) : 20,
      include_notes: includeNotes,
      include_documents: includeDocuments,
      // thread_id no se incluye aquí, ya que es para integración con chat y no es relevante para el frontend web
    };

              try {

                const response = await apiClient.post('/api/start-proactive-insight-generation', payload);



                setTaskId(response.data.task_id);

                toast({

                  title: 'Generación de Insights Iniciada',

                  description: `La tarea de insights ha sido iniciada con ID: ${response.data.task_id}. Puedes consultar su estado.`,

                  variant: 'default',

                });

              } catch (error: any) {

                console.error('Error al generar insights:', error);

                toast({

                  title: 'Error',

                  description: error.response?.data?.detail || error.message || 'Hubo un problema al iniciar la generación de insights.',

                  variant: 'destructive',

                });

              } finally {

                setIsLoading(false);

              }
  }, [accountId, sinceDaysAgo, topicKeywords, topK, includeNotes, includeDocuments, toast]);

  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader>
        <CardTitle>Generar Insights Proactivos</CardTitle>
        <CardDescription>
          Inicia un análisis profundo de tu conocimiento para descubrir nuevas conexiones y oportunidades.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="sinceDaysAgo">Analizar desde hace (días):</Label>
            <Input
              id="sinceDaysAgo"
              type="number"
              placeholder="Ej: 7 (para los últimos 7 días)"
              value={sinceDaysAgo}
              onChange={(e) => setSinceDaysAgo(e.target.value)}
              disabled={isLoading}
            />
            <p className="text-sm text-gray-500 mt-1">Deja en blanco para analizar todo el conocimiento.</p>
          </div>
          <div>
            <Label htmlFor="topicKeywords">Palabras clave (separadas por coma):</Label>
            <Input
              id="topicKeywords"
              type="text"
              placeholder="Ej: marketing digital, nuevas tendencias"
              value={topicKeywords}
              onChange={(e) => setTopicKeywords(e.target.value)}
              disabled={isLoading}
            />
            <p className="text-sm text-gray-500 mt-1">Opcional. Enfoca el análisis en temas específicos.</p>
          </div>
          <div>
            <Label htmlFor="topK">Número de Documentos Similares a Analizar:</Label>
            <Input
              id="topK"
              type="number"
              placeholder="Ej: 20"
              value={topK}
              onChange={(e) => setTopK(e.target.value)}
              disabled={isLoading}
              min="1"
              max="100"
            />
            <p className="text-sm text-gray-500 mt-1">Cuántos documentos similares analizar (1-100). Más documentos = análisis más profundo pero más costoso.</p>
          </div>
          <div>
            <Label>Tipos de contenido a incluir:</Label>
            <div className="space-y-2 mt-2">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="includeNotes"
                  checked={includeNotes}
                  onCheckedChange={(checked) => setIncludeNotes(checked as boolean)}
                  disabled={isLoading}
                />
                <Label htmlFor="includeNotes" className="text-sm">Incluir Notas</Label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="includeDocuments"
                  checked={includeDocuments}
                  onCheckedChange={(checked) => setIncludeDocuments(checked as boolean)}
                  disabled={isLoading}
                />
                <Label htmlFor="includeDocuments" className="text-sm">Incluir Documentos</Label>
              </div>
            </div>
            <p className="text-sm text-gray-500 mt-1">Selecciona qué tipos de contenido analizar.</p>
          </div>
          <Button type="submit" className="w-full" disabled={isLoading || (!includeNotes && !includeDocuments)}>
            {isLoading ? 'Generando Insights...' : 'Generar Insights'}
          </Button>
        </form>
        {taskId && (
          <div className="mt-4 p-3 bg-gray-100 dark:bg-gray-800 rounded-md text-sm">
            <p>Tarea de análisis iniciada. ID: <span className="font-mono">{taskId}</span></p>
            <p>Puedes consultar el estado en la sección de tareas o análisis.</p>
          </div>
        )}
      </CardContent>
      <CardFooter>
        <p className="text-xs text-gray-500">
          El análisis se ejecutará en segundo plano. Recibirás una notificación cuando esté completo.
        </p>
      </CardFooter>
    </Card>
  );
};

export default InsightGeneratorForm;