'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { motion, AnimatePresence } from 'framer-motion';

interface Insight {
  id: string;
  type: string;
  summary: string;
  created_at: string;
  related_items: any[];
  action_suggestion?: string;
  synthetic_name?: string; // Asegúrate de que coincida con la interfaz en page.tsx
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
                className="space-y-6 py-4"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1, duration: 0.3 }}
              >
                {/* Card principal del insight */}
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1, duration: 0.3 }}
                  className="border border-slate-200 bg-slate-50/50 dark:border-slate-700 dark:bg-slate-800/30 rounded-2xl p-4"
                >
                  <h4 className="font-semibold mb-3 text-foreground flex items-center gap-2">
                    <span className="h-2 w-2 bg-yellow-500 rounded-full"></span>
                    Resumen del Hallazgo
                  </h4>
                  <p className="text-sm text-muted-foreground leading-relaxed">{insight.summary}</p>
                </motion.div>

                {/* Sugerencia de acción */}
                {insight.action_suggestion && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2, duration: 0.2 }}
                    className="border border-slate-200 bg-slate-50/50 dark:border-slate-700 dark:bg-slate-800/30 rounded-2xl p-4"
                  >
                    <h4 className="font-semibold mb-3 text-foreground flex items-center gap-2">
                      <span className="h-2 w-2 bg-blue-500 rounded-full"></span>
                      Sugerencia de Acción
                    </h4>
                    <p className="text-sm text-muted-foreground leading-relaxed">{insight.action_suggestion}</p>
                  </motion.div>
                )}

                {/* Ítems relacionados */}
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3, duration: 0.2 }}
                  className="border border-slate-200 bg-slate-50/50 dark:border-slate-700 dark:bg-slate-800/30 rounded-2xl p-4"
                >
                  <h4 className="font-semibold mb-4 text-foreground flex items-center gap-2">
                    <span className="h-2 w-2 bg-primary rounded-full"></span>
                    Ítems Relacionados
                  </h4>
                  <div className="space-y-3 text-sm">
                    {(() => {
                      // Handle different possible structures of related_items
                      let items: any = insight.related_items || [];

                      // If related_items is an object with an 'items' property, use that
                      if (typeof items === 'object' && !Array.isArray(items) && (items as any).items) {
                        items = (items as any).items;
                      }

                      // Ensure we have an array
                      if (!Array.isArray(items)) {
                        items = [];
                      }

                      return items.map((item: any, index: number) => (
                        <motion.div
                          key={index}
                          className="p-4 bg-white/60 dark:bg-slate-900/40 rounded-2xl border border-slate-200/50 dark:border-slate-600/50 hover:bg-white/80 dark:hover:bg-slate-900/60 transition-colors duration-200"
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: 0.4 + index * 0.05, duration: 0.2 }}
                        >
                          <p className="font-medium text-foreground">{item.title || item.reference || 'Ítem sin título'}</p>
                          <div className="mt-2">
                            <Badge variant="secondary" className="text-xs">
                              {item.type || 'N/A'}
                            </Badge>
                          </div>
                        </motion.div>
                      ));
                    })()}
                  </div>
                </motion.div>
              </motion.div>
            </motion.div>
          </DialogContent>
        </Dialog>
      )}
    </AnimatePresence>
  );
}
