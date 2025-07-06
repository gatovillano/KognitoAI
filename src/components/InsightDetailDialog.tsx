'use client';

import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ThumbsUp, ThumbsDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import apiClient from '@/lib/api';
import { toast } from 'sonner';

interface Insight {
  id: string; // Este ID es numérico en el backend (ProactiveInsight.id), pero la UI lo trata como string.
  type: string;
  summary: string;
  created_at: string;
  related_items: any[];
  action_suggestion?: string;
  synthetic_name?: string; // Asegúrate de que coincida con la interfaz en page.tsx
}

interface Feedback {
  id: string;
  insight_id: number;
  is_useful: boolean;
  feedback_category?: string;
  comment?: string;
  created_at: string;
  updated_at: string;
  account_id: string;
}

const feedbackCategories = [
  { value: 'IRRELEVANT', label: 'Irrelevante' },
  { value: 'ALREADY_KNOWN', label: 'Ya lo sabía' },
  { value: 'INCORRECT', label: 'Incorrecto' },
  { value: 'UNCLEAR', label: 'Poco claro' },
  { value: 'OTHER', label: 'Otro' },
];

export function InsightDetailDialog({ insight, isOpen, onOpenChange }: { insight: Insight | null; isOpen: boolean; onOpenChange: (open: boolean) => void }) {
  const [selectedFeedback, setSelectedFeedback] = useState<'useful' | 'not_useful' | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string | undefined>(undefined);
  const [comment, setComment] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [existingFeedback, setExistingFeedback] = useState<Feedback | null>(null);

  useEffect(() => {
    if (isOpen && insight) {
      // Reset state for new insight
      setSelectedFeedback(null);
      setSelectedCategory(undefined);
      setComment('');
      setExistingFeedback(null);
      setIsLoading(false);

      // Fetch existing feedback
      const fetchFeedback = async () => {
        try {
          // Assuming current user's feedback is the first one if multiple, or API filters by user.
          // The backend GET /proactive-insights/{insight_id}/feedback returns a list.
          // We need to find feedback by the current user. For now, we'll take the first one.
          // A better approach would be for the API to allow fetching feedback for current user only or include user info.
          const response = await apiClient.get(`/api/proactive-insights/${insight.id}/feedback`);
          if (response.data && response.data.length > 0) {
            // Heurística: tomar el feedback más reciente como el "existente" para este usuario.
            // En un sistema multiusuario real, filtraríamos por account_id del usuario actual.
            const feedback = response.data[0] as Feedback; // Tomamos el primero, idealmente filtraríamos por usuario
            setExistingFeedback(feedback);
            setSelectedFeedback(feedback.is_useful ? 'useful' : 'not_useful');
            setSelectedCategory(feedback.feedback_category);
            setComment(feedback.comment || '');
          }
        } catch (error) {
          // No es crítico si no se carga el feedback existente, no mostramos toast.
          console.error('Error fetching existing feedback:', error);
        }
      };
      fetchFeedback();
    }
  }, [isOpen, insight]);

  const handleSubmitFeedback = async () => {
    if (!insight || selectedFeedback === null) {
      toast.error('Por favor, selecciona si el insight fue útil o no.');
      return;
    }
    setIsLoading(true);
    try {
      const payload = {
        insight_id: parseInt(insight.id, 10), // Backend espera int
        is_useful: selectedFeedback === 'useful',
        feedback_category: selectedFeedback === 'not_useful' ? selectedCategory : undefined,
        comment: comment,
      };
      const response = await apiClient.post('/api/proactive-insights/feedback', payload);
      setExistingFeedback(response.data); // Update with submitted feedback
      toast.success('Feedback enviado con éxito.');
      // Optionally close dialog or give other indication:
      // onOpenChange(false);
    } catch (error: any) {
      toast.error('Error al enviar feedback.', { description: error?.response?.data?.detail || error.message });
    } finally {
      setIsLoading(false);
    }
  };

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
                  <Badge variant={insight.type === 'synergy' || insight.type === 'evolucion' || insight.type === 'sinergia' ? 'default' : 'destructive'} className="rounded-full">
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
                <Separator />
                {/* Feedback Section */}
                <motion.div
                  initial={{ opacity: 0, y:10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4, duration: 0.3 }}
                  className="space-y-3 pt-2"
                >
                  <h4 className="font-semibold">¿Te resultó útil este insight?</h4>
                  <div className="flex space-x-2">
                    <Button
                      variant={selectedFeedback === 'useful' ? 'default' : 'outline'}
                      onClick={() => setSelectedFeedback('useful')}
                      size="sm"
                      className="rounded-full"
                    >
                      <ThumbsUp className="mr-2 h-4 w-4" /> Útil
                    </Button>
                    <Button
                      variant={selectedFeedback === 'not_useful' ? 'destructive' : 'outline'}
                      onClick={() => setSelectedFeedback('not_useful')}
                      size="sm"
                      className="rounded-full"
                    >
                      <ThumbsDown className="mr-2 h-4 w-4" /> No útil
                    </Button>
                  </div>

                  {selectedFeedback === 'not_useful' && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      transition={{ duration: 0.3 }}
                      className="space-y-2 pt-2"
                    >
                      <Select value={selectedCategory} onValueChange={setSelectedCategory}>
                        <SelectTrigger className="w-full rounded-xl">
                          <SelectValue placeholder="¿Por qué no fue útil? (Opcional)" />
                        </SelectTrigger>
                        <SelectContent className="rounded-xl">
                          {feedbackCategories.map(cat => (
                            <SelectItem key={cat.value} value={cat.value} className="rounded-lg">{cat.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </motion.div>
                  )}
                  <Textarea
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    placeholder="Comentarios adicionales (Opcional)"
                    className="rounded-xl min-h-[80px]"
                  />
                </motion.div>
              </motion.div>
              <DialogFooter className="pt-4">
                <Button
                  onClick={handleSubmitFeedback}
                  disabled={isLoading || selectedFeedback === null}
                  className="rounded-xl gradient-primary text-white shadow-medium hover:shadow-strong transition-all duration-300"
                >
                  {isLoading ? 'Enviando...' : 'Enviar Feedback'}
                </Button>
              </DialogFooter>
            </motion.div>
          </DialogContent>
        </Dialog>
      )}
    </AnimatePresence>
  );
}
