'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { motion, AnimatePresence } from 'framer-motion';

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
    <AnimatePresence>
      {isOpen && (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
          <DialogContent className="max-w-2xl rounded-3xl backdrop-blur-xl bg-card/95 border-0 shadow-2xl">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
            >
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <Badge variant={insight.type === 'synergy' ? 'default' : 'destructive'} className="rounded-full">
                    {insight.type.toUpperCase()}
                  </Badge>
                  <span>Detalle del Insight</span>
                </DialogTitle>
                <DialogDescription>
                  Generado el: {new Date(insight.created_at).toLocaleString('es-ES')}
                </DialogDescription>
              </DialogHeader>
              <motion.div 
                className="space-y-4 py-4"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1, duration: 0.3 }}
              >
                <div>
                  <h4 className="font-semibold mb-1">Resumen del Hallazgo:</h4>
                  <p className="text-sm text-muted-foreground">{insight.summary}</p>
                </div>
                <Separator />
                <div>
                  <h4 className="font-semibold mb-1">Ítems Relacionados:</h4>
                  <div className="space-y-2 text-sm">
                    {insight.related_items?.map((item, index) => (
                      <motion.div 
                        key={index} 
                        className="p-3 bg-muted/30 rounded-2xl border border-border/50"
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.2 + index * 0.05, duration: 0.2 }}
                      >
                        <p className="font-medium">{item.title || item.reference || 'Ítem sin título'}</p>
                        <p className="text-xs text-muted-foreground">Tipo: {item.type || 'N/A'}</p>
                      </motion.div>
                    ))}
                  </div>
                </div>
                {insight.action_suggestion && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3, duration: 0.2 }}
                  >
                    <h4 className="font-semibold mb-1">Sugerencia de Acción:</h4>
                    <p className="text-sm text-muted-foreground">{insight.action_suggestion}</p>
                  </motion.div>
                )}
              </motion.div>
            </motion.div>
          </DialogContent>
        </Dialog>
      )}
    </AnimatePresence>
  );
}
