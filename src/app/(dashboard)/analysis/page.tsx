'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { AnalysisDetailDialog } from './analysis-detail-dialog';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { 
  BarChart3, 
  FileText, 
  FolderKanban, 
  Brain, 
  Lightbulb, 
  Code, 
  Search, 
  Filter, 
  ChevronDown,
  Calendar,
  Eye,
  Loader2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Analysis {
  id: string;
  type: string;
  title: string;
  summary: string;
  created_at: string;
  updated_at: string;
  source_table: string;
  tool_used?: string;
  confidence_score?: number;
  action_suggestion?: string;
  related_items?: any[];
  full_data: any;
}

interface AnalysisResponse {
  analysis: Analysis[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

const getAnalysisIcon = (type: string) => {
  switch (type) {
    case 'document':
      return <FileText className="h-5 w-5 text-blue-500" />;
    case 'collection':
      return <FolderKanban className="h-5 w-5 text-green-500" />;
    case 'mindmap':
      return <Brain className="h-5 w-5 text-purple-500" />;
    case 'insight':
      return <Lightbulb className="h-5 w-5 text-yellow-500" />;
    case 'code':
      return <Code className="h-5 w-5 text-orange-500" />;
    case 'semantic':
      return <BarChart3 className="h-5 w-5 text-indigo-500" />;
    default:
      return <FileText className="h-5 w-5 text-gray-500" />;
  }
};

const getAnalysisTypeLabel = (type: string) => {
  switch (type) {
    case 'document':
      return 'Documento';
    case 'collection':
      return 'Colección';
    case 'mindmap':
      return 'Mapa Mental';
    case 'insight':
      return 'Insight';
    case 'code':
      return 'Código';
    case 'semantic':
      return 'Semántico';
    default:
      return 'Análisis';
  }
};

const getAnalysisTypeBadgeColor = (type: string) => {
  switch (type) {
    case 'document':
      return 'bg-blue-100 text-blue-800 border-blue-200';
    case 'collection':
      return 'bg-green-100 text-green-800 border-green-200';
    case 'mindmap':
      return 'bg-purple-100 text-purple-800 border-purple-200';
    case 'insight':
      return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    case 'code':
      return 'bg-orange-100 text-orange-800 border-orange-200';
    case 'semantic':
      return 'bg-indigo-100 text-indigo-800 border-indigo-200';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200';
  }
};

export default function AnalysisPage() {
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [selectedAnalysis, setSelectedAnalysis] = useState<Analysis | null>(null);
  const [isDetailDialogOpen, setIsDetailDialogOpen] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [offset, setOffset] = useState(0);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  const fetchAnalyses = async (reset = false) => {
    if (reset) {
      setIsLoading(true);
      setOffset(0);
    } else {
      setIsLoadingMore(true);
    }

    try {
      const currentOffset = reset ? 0 : offset;
      const response = await apiClient.post('/api/get-all-analysis', {
        limit: 20,
        offset: currentOffset,
        analysis_type: selectedType,
        search_query: searchQuery || undefined
      });

      const data: AnalysisResponse = response.data;
      
      if (reset) {
        setAnalyses(data.analysis);
      } else {
        setAnalyses(prev => [...prev, ...data.analysis]);
      }
      
      setHasMore(data.has_more);
      setOffset(currentOffset + data.analysis.length);
    } catch (error) {
      toast.error('Error al cargar los análisis');
      console.error('Error fetching analyses:', error);
    } finally {
      setIsLoading(false);
      setIsLoadingMore(false);
    }
  };

  useEffect(() => {
    fetchAnalyses(true);
  }, [selectedType, searchQuery]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchAnalyses(true);
  };

  const handleViewDetails = (analysis: Analysis) => {
    setSelectedAnalysis(analysis);
    setIsDetailDialogOpen(true);
  };

  const handleLoadMore = () => {
    if (!isLoadingMore && hasMore) {
      fetchAnalyses(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const analysisTypes = [
    { value: null, label: 'Todos los tipos' },
    { value: 'document', label: 'Documentos' },
    { value: 'collection', label: 'Colecciones' },
    { value: 'mindmap', label: 'Mapas Mentales' },
    { value: 'insight', label: 'Insights' },
    { value: 'code', label: 'Código' },
    { value: 'semantic', label: 'Semántico' }
  ];

  if (isLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center">
        <div className="flex flex-col items-center gap-2">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-muted-foreground">Cargando análisis...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 mx-4 space-y-8">
      {/* Header */}
      <div className="spacing-component">
        <h1 className="text-5xl font-bold tracking-tight bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent spacing-tight">
          Centro de Análisis
        </h1>
        <p className="typography-body-large text-muted-foreground max-w-2xl">
          Explora todos tus análisis de documentos, colecciones, mapas mentales e insights proactivos en un solo lugar.
        </p>
      </div>

      {/* Filtros y búsqueda */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
        <form onSubmit={handleSearch} className="flex gap-2 flex-1">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Buscar en análisis..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <Button type="submit" variant="outline">
            Buscar
          </Button>
        </form>
        
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" className="gap-2">
              <Filter className="h-4 w-4" />
              {selectedType ? getAnalysisTypeLabel(selectedType) : 'Filtrar por tipo'}
              <ChevronDown className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {analysisTypes.map((type) => (
              <DropdownMenuItem
                key={type.value || 'all'}
                onClick={() => setSelectedType(type.value)}
              >
                {type.label}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Lista de análisis */}
      {analyses.length === 0 ? (
        <div className="text-center py-20 px-8">
          <BarChart3 className="mx-auto h-16 w-16 text-muted-foreground/50 mb-6" />
          <h3 className="text-xl font-semibold mb-4">No se encontraron análisis</h3>
          <p className="text-muted-foreground mb-8 max-w-md mx-auto">
            {searchQuery || selectedType 
              ? 'No hay análisis que coincidan con tus filtros. Intenta ajustar la búsqueda.'
              : 'Aún no tienes análisis. ¡Comienza analizando documentos o colecciones para ver resultados aquí!'
            }
          </p>
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <AnimatePresence>
            {analyses.map((analysis, index) => (
              <motion.div
                key={analysis.id}
                layout
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                transition={{ type: "spring", stiffness: 300, damping: 30, delay: index * 0.05 }}
                className="h-full"
              >
                <Card className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20 flex flex-col h-full">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                        {getAnalysisIcon(analysis.type)}
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleViewDetails(analysis)}
                        className="opacity-0 group-hover:opacity-100 transition-opacity gap-1 h-8 px-2"
                      >
                        <Eye className="h-3 w-3" />
                        <span className="text-xs">Ver</span>
                      </Button>
                    </div>
                    <div className="space-y-3">
                      <CardTitle className="text-lg leading-tight line-clamp-2">{analysis.title}</CardTitle>
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge className={`text-xs ${getAnalysisTypeBadgeColor(analysis.type)}`}>
                          {getAnalysisTypeLabel(analysis.type)}
                        </Badge>
                        {analysis.confidence_score && (
                          <Badge variant="outline" className="text-xs">
                            Confianza: {(analysis.confidence_score * 100).toFixed(0)}%
                          </Badge>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="pt-0 flex-grow flex flex-col">
                    <p className="text-sm text-muted-foreground line-clamp-6 mb-4 flex-grow leading-relaxed">
                      {analysis.summary}
                    </p>

                    {analysis.action_suggestion && (
                      <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                        <p className="text-xs font-medium text-yellow-800 mb-1">Sugerencia:</p>
                        <p className="text-xs text-yellow-700 line-clamp-2">{analysis.action_suggestion}</p>
                      </div>
                    )}

                    {analysis.related_items && analysis.related_items.length > 0 && (
                      <div className="mb-4">
                        <p className="text-xs font-medium text-muted-foreground mb-2">
                          Elementos relacionados ({analysis.related_items.length})
                        </p>
                        <div className="flex flex-wrap gap-1">
                          {analysis.related_items.slice(0, 3).map((item, idx) => (
                            <Badge key={idx} variant="secondary" className="text-xs">
                              {item.title || item.name || `Item ${idx + 1}`}
                            </Badge>
                          ))}
                          {analysis.related_items.length > 3 && (
                            <Badge variant="outline" className="text-xs">
                              +{analysis.related_items.length - 3} más
                            </Badge>
                          )}
                        </div>
                      </div>
                    )}
                    <div className="space-y-2 text-xs text-muted-foreground mt-auto pt-3 border-t border-border/50">
                      {analysis.tool_used && (
                        <div className="mb-2">
                          <Badge variant="outline" className="text-xs font-mono bg-slate-50 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700">
                            {analysis.tool_used}
                          </Badge>
                        </div>
                      )}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          <span className="truncate">Creado: {formatDate(analysis.created_at)}</span>
                        </div>
                      </div>
                      {analysis.updated_at !== analysis.created_at && (
                        <div className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          <span className="truncate">Actualizado: {formatDate(analysis.updated_at)}</span>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Botón cargar más */}
          {hasMore && (
            <div className="text-center pt-6">
              <Button
                onClick={handleLoadMore}
                disabled={isLoadingMore}
                variant="outline"
                className="gap-2"
              >
                {isLoadingMore ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Cargando...
                  </>
                ) : (
                  'Cargar más análisis'
                )}
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Dialog de detalles especializado */}
      <AnalysisDetailDialog
        analysis={selectedAnalysis}
        isOpen={isDetailDialogOpen}
        onOpenChange={setIsDetailDialogOpen}
      />
    </div>
  );
}
