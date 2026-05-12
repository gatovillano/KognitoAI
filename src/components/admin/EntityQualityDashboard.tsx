'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { ClipboardList, Bug, Wand2, Delete, Merge, CheckCircle, AlertTriangle, Info, RefreshCw } from 'lucide-react';
import apiClient from '@/lib/api';

// Interfaces for typing
interface Correction {
  action: 'correct' | 'delete' | 'merge';
  entity: { name: string };
  reason: string;
}

interface ReviewSummary {
  quality_score: number;
  corrections_needed: number;
  deletions_needed: number;
  merges_needed: number;
  issues_found: number;
  recommendations: string[];
}

interface ReviewResults {
  summary: ReviewSummary;
  corrections: Correction[];
  deletions: Correction[];
  merges: Correction[];
}

interface Statistics {
    summary: {
        total_entities: number;
        total_relationships: number;
        entity_types_count: number;
        relationship_types_count: number;
    };
    entity_types: Array<{
        type: string;
        count: number;
        avg_confidence: number;
        methods: string[];
    }>;
}

interface CorrectionResult {
    applied: number;
    failed: number;
}

const EMPTY_STATISTICS: Statistics = {
  summary: {
    total_entities: 0,
    total_relationships: 0,
    entity_types_count: 0,
    relationship_types_count: 0,
  },
  entity_types: [],
};

const normalizeStatistics = (payload: any): Statistics => {
  const raw = payload?.data ?? payload ?? {};
  const summary = raw.summary ?? {};

  return {
    summary: {
      total_entities: Number(summary.total_entities ?? 0),
      total_relationships: Number(summary.total_relationships ?? 0),
      entity_types_count: Number(summary.entity_types_count ?? 0),
      relationship_types_count: Number(summary.relationship_types_count ?? 0),
    },
    entity_types: Array.isArray(raw.entity_types)
      ? raw.entity_types.map((item: any) => ({
          type: String(item?.type ?? 'Desconocido'),
          count: Number(item?.count ?? 0),
          avg_confidence: Number(item?.avg_confidence ?? 0),
          methods: Array.isArray(item?.methods) ? item.methods : [],
        }))
      : [],
  };
};

const normalizeReviewResults = (payload: any): ReviewResults | null => {
  const raw = payload?.data ?? payload;
  if (!raw?.summary) return null;

  return {
    summary: {
      quality_score: Number(raw.summary.quality_score ?? 0),
      corrections_needed: Number(raw.summary.corrections_needed ?? 0),
      deletions_needed: Number(raw.summary.deletions_needed ?? 0),
      merges_needed: Number(raw.summary.merges_needed ?? 0),
      issues_found: Number(raw.summary.issues_found ?? 0),
      recommendations: Array.isArray(raw.summary.recommendations) ? raw.summary.recommendations : [],
    },
    corrections: Array.isArray(raw.corrections) ? raw.corrections : [],
    deletions: Array.isArray(raw.deletions) ? raw.deletions : [],
    merges: Array.isArray(raw.merges) ? raw.merges : [],
  };
};

const normalizeCorrectionResult = (payload: any): CorrectionResult | null => {
  const raw = payload?.data ?? payload;
  if (!raw) return null;

  return {
    applied: Number(raw.applied ?? 0),
    failed: Number(raw.failed ?? 0),
  };
};


const EntityQualityDashboard = () => {
  const [statistics, setStatistics] = useState<Statistics>(EMPTY_STATISTICS);
  const [reviewResults, setReviewResults] = useState<ReviewResults | null>(null);
  const [loading, setLoading] = useState(false);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [applyLoading, setApplyLoading] = useState(false);
  const [selectedCorrections, setSelectedCorrections] = useState<Correction[]>([]);
  const [showCorrectionDialog, setShowCorrectionDialog] = useState(false);
  const [correctionResults, setCorrectionResults] = useState<CorrectionResult | null>(null);

  useEffect(() => {
    loadStatistics();
  }, []);

  const loadStatistics = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/api/knowledge-graph/entity-statistics');
      if (response.data?.success === false) {
        throw new Error(response.data.error || 'No se pudieron cargar las estadísticas');
      }
      setStatistics(normalizeStatistics(response.data));
    } catch (error) {
      console.error('Error loading statistics:', error);
      setStatistics(EMPTY_STATISTICS);
    } finally {
      setLoading(false);
    }
  };

  const runQualityReview = async () => {
    setReviewLoading(true);
    try {
      const response = await apiClient.post('/api/knowledge-graph/review-entities', {});
      if (response.data?.success === false) {
        throw new Error(response.data.error || 'No se pudo ejecutar la revisión');
      }
      setReviewResults(normalizeReviewResults(response.data));
    } catch (error) {
      console.error('Error running quality review:', error);
      setReviewResults(null);
    } finally {
      setReviewLoading(false);
    }
  };

  const applyCorrections = async (corrections: Correction[], autoApply = false) => {
    setApplyLoading(true);
    try {
      const response = await apiClient.post('/api/knowledge-graph/apply-corrections', {
        corrections,
        auto_apply: autoApply
      });
      if (response.data?.success === false) {
        throw new Error(response.data.error || 'No se pudieron aplicar las correcciones');
      }
      setCorrectionResults(normalizeCorrectionResult(response.data));
      await loadStatistics();
      setReviewResults(null);
    } catch (error) {
      console.error('Error applying corrections:', error);
      setCorrectionResults(null);
    } finally {
      setApplyLoading(false);
    }
  };

  const getQualityColor = (score: number) => {
    if (score >= 90) return 'bg-green-500';
    if (score >= 70) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getActionIcon = (action: string) => {
    switch (action) {
      case 'correct': return <Wand2 className="h-4 w-4 text-yellow-500" />;
      case 'delete': return <Delete className="h-4 w-4 text-red-500" />;
      case 'merge': return <Merge className="h-4 w-4 text-blue-500" />;
      default: return <Info className="h-4 w-4" />;
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <RefreshCw className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Entidades</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{statistics.summary.total_entities.toLocaleString()}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Relaciones</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{statistics.summary.total_relationships.toLocaleString()}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Tipos de Entidades</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{statistics.summary.entity_types_count}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Tipos de Relaciones</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{statistics.summary.relationship_types_count}</div>
          </CardContent>
        </Card>
      </div>

      {/* Botones de Acción */}
      <div className="flex gap-2">
        <Button onClick={loadStatistics} disabled={loading}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Actualizar Estadísticas
        </Button>
        <Button onClick={runQualityReview} disabled={reviewLoading} variant="outline">
          {reviewLoading ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <ClipboardList className="mr-2 h-4 w-4" />}
          {reviewLoading ? 'Analizando...' : 'Ejecutar Revisión de Calidad'}
        </Button>
      </div>

      {/* Resultados de Revisión */}
      {reviewResults && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ClipboardList />
              Resultados de Revisión de Calidad
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm font-medium mb-2">Puntuación de Calidad: {reviewResults.summary.quality_score.toFixed(1)}%</p>
              <Progress value={reviewResults.summary.quality_score} className={getQualityColor(reviewResults.summary.quality_score)} />
            </div>
            <div className="grid gap-4 md:grid-cols-3">
              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>{reviewResults.summary.corrections_needed}</AlertTitle>
                <AlertDescription>Correcciones Necesarias</AlertDescription>
              </Alert>
              <Alert variant="destructive">
                <Delete className="h-4 w-4" />
                <AlertTitle>{reviewResults.summary.deletions_needed}</AlertTitle>
                <AlertDescription>Eliminaciones Necesarias</AlertDescription>
              </Alert>
              <Alert>
                <Merge className="h-4 w-4" />
                <AlertTitle>{reviewResults.summary.merges_needed}</AlertTitle>
                <AlertDescription>Fusiones Necesarias</AlertDescription>
              </Alert>
            </div>
            {reviewResults.summary.recommendations.length > 0 && (
              <div>
                <h4 className="font-semibold mb-2">Recomendaciones:</h4>
                <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                  {reviewResults.summary.recommendations.map((rec, index) => (
                    <li key={index}>{rec}</li>
                  ))}
                </ul>
              </div>
            )}
            <div className="flex gap-2">
              <Button
                onClick={() => {
                  const allCorrections = [
                    ...reviewResults.corrections,
                    ...reviewResults.deletions,
                    ...reviewResults.merges
                  ];
                  setSelectedCorrections(allCorrections);
                  setShowCorrectionDialog(true);
                }}
                disabled={reviewResults.summary.issues_found === 0}
              >
                <Wand2 className="mr-2 h-4 w-4" />
                Aplicar Todas las Correcciones ({reviewResults.summary.issues_found})
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setSelectedCorrections(reviewResults.corrections);
                  setShowCorrectionDialog(true);
                }}
                disabled={reviewResults.corrections.length === 0}
              >
                Solo Correcciones de Tipo ({reviewResults.corrections.length})
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Distribución de Entidades por Tipo</CardTitle>
        </CardHeader>
        <CardContent>
          {statistics.entity_types.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Aún no hay estadísticas detalladas disponibles para mostrar.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tipo</TableHead>
                  <TableHead className="text-right">Cantidad</TableHead>
                  <TableHead className="text-right">Confianza Promedio</TableHead>
                  <TableHead>Métodos de Extracción</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {statistics.entity_types.map((type) => (
                  <TableRow key={type.type}>
                    <TableCell><Badge variant="outline">{type.type}</Badge></TableCell>
                    <TableCell className="text-right">{type.count.toLocaleString()}</TableCell>
                    <TableCell className="text-right">{(type.avg_confidence * 100).toFixed(1)}%</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {type.methods.map((method, index) => (
                          <Badge key={index} variant="secondary">{method}</Badge>
                        ))}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Dialog de Confirmación de Correcciones */}
      <Dialog open={showCorrectionDialog} onOpenChange={setShowCorrectionDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirmar Aplicación de Correcciones</DialogTitle>
            <DialogDescription>
              Se aplicarán {selectedCorrections.length} correcciones.
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-60 overflow-y-auto space-y-2 p-1">
            {selectedCorrections.slice(0, 10).map((correction, index) => (
              <div key={index} className="flex items-center gap-2 text-sm">
                {getActionIcon(correction.action)}
                <Badge variant="outline">{correction.action.toUpperCase()}</Badge>
                <span className="font-medium">{correction.entity?.name || 'Entidad desconocida'}</span>
                <span className="text-muted-foreground truncate">{correction.reason}</span>
              </div>
            ))}
            {selectedCorrections.length > 10 && (
              <p className="text-sm text-muted-foreground">... y {selectedCorrections.length - 10} más.</p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCorrectionDialog(false)}>Cancelar</Button>
            <Button
              onClick={() => {
                applyCorrections(selectedCorrections, true);
                setShowCorrectionDialog(false);
              }}
              disabled={applyLoading}
            >
              {applyLoading ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : null}
              {applyLoading ? 'Aplicando...' : 'Aplicar Correcciones'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Resultados de Corrección */}
      {correctionResults && (
        <Alert variant={correctionResults.failed === 0 ? 'default' : 'destructive'} className="mt-4">
          <CheckCircle className="h-4 w-4" />
          <AlertTitle>Resultados de la Corrección</AlertTitle>
          <AlertDescription>
            Correcciones Aplicadas: {correctionResults.applied} exitosas, {correctionResults.failed} fallidas
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
};

export default EntityQualityDashboard;
