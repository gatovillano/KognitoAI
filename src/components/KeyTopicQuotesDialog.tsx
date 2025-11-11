import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';

interface KeyTopicQuotesDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  subTopic: string | null;
  quotes: any[]; // Las citas tendrán la estructura { document_title: string, quote: string }
}

export const KeyTopicQuotesDialog: React.FC<KeyTopicQuotesDialogProps> = ({ isOpen, onOpenChange, subTopic, quotes }) => {
  if (!subTopic) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl w-full max-h-[90vh] rounded-3xl backdrop-blur-xl bg-card/95 border-0 shadow-2xl flex flex-col p-0">
        <DialogHeader className="p-6 pb-4 border-b">
          <DialogTitle className="text-xl font-bold text-foreground">Citas para: {subTopic}</DialogTitle>
        </DialogHeader>
        <ScrollArea className="flex-1 p-6">
          <div className="space-y-4">
            {quotes.length > 0 ? (
              <ul className="list-disc list-inside text-sm text-muted-foreground space-y-2">
                {quotes.map((quote: any, i: number) => (
                  <li key={i}>
                    <strong>{quote.document_title || 'Documento desconocido'}</strong>: {quote.quote || quote}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">No hay citas disponibles para este sub-tema.</p>
            )}
          </div>
        </ScrollArea>
        <DialogFooter className="p-6 pt-4 border-t">
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cerrar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};