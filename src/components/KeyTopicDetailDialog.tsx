import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { KeyTopic } from '@/lib/models';
import { KeyTopicQuotesDialog } from './KeyTopicQuotesDialog'; // Importar el segundo diálogo

interface KeyTopicDetailDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  keyTopic: KeyTopic | null;
}

export const KeyTopicDetailDialog: React.FC<KeyTopicDetailDialogProps> = ({ isOpen, onOpenChange, keyTopic }) => {
  const [isQuotesDialogOpen, setIsQuotesDialogOpen] = useState(false);
  const [selectedSubTopic, setSelectedSubTopic] = useState<string | null>(null);
  const [selectedQuotes, setSelectedQuotes] = useState<any[]>([]); // Aquí almacenaremos las citas del sub-tema

  // Función para simular la obtención de citas por sub-tema
  // En un caso real, esto podría implicar una llamada a la API o una búsqueda en los datos existentes
  const getQuotesForSubTopic = (subTopic: string): any[] => {
    if (keyTopic?.quotes && keyTopic.quotes.length > 0) {
      return keyTopic.quotes;
    }
    return [];
  };

  const handleSubTopicClick = (subTopic: string) => {
    setSelectedSubTopic(subTopic);
    setSelectedQuotes(getQuotesForSubTopic(subTopic)); // Obtener citas para el sub-tema
    setIsQuotesDialogOpen(true);
  };

  if (!keyTopic) return null;

  return (
    <>
      <Dialog open={isOpen} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-2xl w-full max-h-[90vh] rounded-3xl backdrop-blur-xl bg-card/95 border-0 shadow-2xl flex flex-col p-0">
          <DialogHeader className="p-6 pb-4 border-b">
            <DialogTitle className="text-xl font-bold text-foreground">Detalles del Tema Clave: {keyTopic.topic}</DialogTitle>
          </DialogHeader>
          <ScrollArea className="flex-1 p-6">
            <div className="space-y-4">
              {keyTopic.description && (
                <div>
                  <h4 className="font-semibold text-lg">Descripción:</h4>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">{keyTopic.description}</p>
                </div>
              )}

              {keyTopic.topics && keyTopic.topics.length > 0 && (
                <div>
                  <h4 className="font-semibold text-lg mb-2">Temas Agrupados:</h4>
                  <div className="flex flex-wrap gap-2">
                    {keyTopic.topics.map((subTopic, index) => (
                      <Badge
                        key={index}
                        className="cursor-pointer bg-purple-100 text-purple-800 border border-purple-200 hover:bg-purple-200 transition-colors"
                        onClick={() => handleSubTopicClick(subTopic)}
                      >
                        {subTopic}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {!keyTopic.description && (!keyTopic.topics || keyTopic.topics.length === 0) && (
                <p className="text-sm text-muted-foreground">No hay detalles adicionales para este tema clave.</p>
              )}
            </div>
          </ScrollArea>
          <DialogFooter className="p-6 pt-4 border-t">
            <Button variant="outline" onClick={() => onOpenChange(false)}>Cerrar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Segundo Diálogo para mostrar citas del sub-tema */}
      <KeyTopicQuotesDialog
        isOpen={isQuotesDialogOpen}
        onOpenChange={setIsQuotesDialogOpen}
        subTopic={selectedSubTopic}
        quotes={selectedQuotes}
      />
    </>
  );
};