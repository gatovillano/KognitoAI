'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';

interface Insight {
  id: string;
  type: string;
  summary: string;
  created_at: string;
  related_items: any[];
  action_suggestion?: string;
}

export function InsightDetailDialog({ insight, isOpen, onOpenChange }: { insight: Insight | null; isOpen: boolean; onOpenChange: (open: boolean) => void }) {
  if (!insight) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Badge variant={insight.type === 'synergy' ? 'default' : 'destructive'}>{insight.type.toUpperCase()}</Badge>
            <span>Detalle del Insight</span>
          </DialogTitle>
          <DialogDescription>
            Generado el: {new Date(insight.created_at).toLocaleString('es-ES')}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div>
            <h4 className="font-semibold mb-1">Resumen del Hallazgo:</h4>
            <p className="text-sm text-muted-foreground">{insight.summary}</p>
          </div>
          <Separator />
          <div>
            <h4 className="font-semibold mb-1">Ítems Relacionados:</h4>
            <div className="space-y-2 text-sm">
              {insight.related_items?.map((item, index) => (
                <div key={index} className="p-2 bg-muted/50 rounded-md">
                  <p className="font-medium">{item.title || item.reference || 'Ítem sin título'}</p>
                  <p className="text-xs text-muted-foreground">Tipo: {item.type || 'N/A'}</p>
                </div>
              ))}
            </div>
          </div>
          {insight.action_suggestion && (
            <div>
                <h4 className="font-semibold mb-1">Sugerencia de Acción:</h4>
                <p className="text-sm text-muted-foreground">{insight.action_suggestion}</p>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
