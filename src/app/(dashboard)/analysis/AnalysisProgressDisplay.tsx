'use client';

import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Loader2, CheckCircle, XCircle, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AnalysisProgressDisplayProps {
  progressInfo: {
    status: string;
    current_step?: string;
    progress_percentage?: number;
    details?: Array<{
      step: string;
      status: string;
      progress?: string;
      timestamp?: string;
    }>;
    estimated_time_remaining?: string;
  };
  className?: string;
}

const getStepIcon = (status: string) => {
  switch (status) {
    case 'completed':
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case 'failed':
      return <XCircle className="h-4 w-4 text-red-500" />;
    case 'processing':
      return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
    default:
      return <Clock className="h-4 w-4 text-gray-400" />;
  }
};

const getStatusBadge = (status: string) => {
  switch (status) {
    case 'completed':
      return <Badge variant="default">Completado</Badge>;
    case 'failed':
      return <Badge variant="destructive">Fallido</Badge>;
    case 'processing':
      return <Badge variant="secondary" className="animate-pulse">Procesando</Badge>;
    default:
      return <Badge variant="outline">Pendiente</Badge>;
  }
};

export function AnalysisProgressDisplay({ progressInfo, className }: AnalysisProgressDisplayProps) {
  const { status, current_step, progress_percentage, details, estimated_time_remaining } = progressInfo;

  return (
    <div className={cn('space-y-4', className)}>
      {/* Estado general y barra de progreso */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {status === 'processing' && <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />}
          {status === 'completed' && <CheckCircle className="h-4 w-4 text-green-500" />}
          {status === 'failed' && <XCircle className="h-4 w-4 text-red-500" />}
          {status === 'pending' && <Clock className="h-4 w-4 text-gray-400" />}
          <span className="font-medium">{status === 'processing' ? 'En progreso' : status}</span>
        </div>
        {getStatusBadge(status)}
      </div>

      {/* Paso actual */}
      {current_step && (
        <div className="text-sm text-muted-foreground">
          <span className="font-medium">Paso actual:</span> {current_step}
        </div>
      )}

      {/* Barra de progreso */}
      {progress_percentage !== undefined && (
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span>Progreso</span>
            <span>{progress_percentage}%</span>
          </div>
          <Progress value={progress_percentage} className="w-full" />
        </div>
      )}

      {/* Tiempo estimado restante */}
      {estimated_time_remaining && (
        <div className="text-sm text-muted-foreground">
          <span className="font-medium">Tiempo estimado restante:</span> {estimated_time_remaining}
        </div>
      )}

      {/* Detalles de pasos */}
      {details && details.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium">Detalles del proceso:</h4>
          <div className="space-y-1">
            {details.map((detail, index) => (
              <div key={index} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  {getStepIcon(detail.status)}
                  <span>{detail.step}</span>
                </div>
                <div className="flex items-center gap-2">
                  {detail.progress && <span className="text-xs text-muted-foreground">{detail.progress}</span>}
                  {getStatusBadge(detail.status)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}