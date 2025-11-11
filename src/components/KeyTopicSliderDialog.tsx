import React, { useState, useEffect, useCallback } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { KeyTopic } from '@/lib/models';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';

interface KeyTopicSliderDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  keyTopics: KeyTopic[];
  title: string;
}

export const KeyTopicSliderDialog: React.FC<KeyTopicSliderDialogProps> = ({ isOpen, onOpenChange, keyTopics, title }) => {
  const [currentTopicIndex, setCurrentTopicIndex] = useState(0);

  useEffect(() => {
    if (isOpen) {
      setCurrentTopicIndex(0); // Reset to first topic when dialog opens
    }
  }, [isOpen]);

  const handleNext = useCallback(() => {
    setCurrentTopicIndex((prevIndex) => Math.min(prevIndex + 1, keyTopics.length - 1));
  }, [keyTopics.length]);

  const handlePrev = useCallback(() => {
    setCurrentTopicIndex((prevIndex) => Math.max(prevIndex - 1, 0));
  }, []);

  const currentTopic = keyTopics[currentTopicIndex];

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl rounded-lg overflow-hidden">
        <DialogHeader className="p-4 border-b">
          <DialogTitle className="text-xl font-bold">{title}</DialogTitle>
          <DialogDescription>
            Explora los temas clave y sus citas asociadas.
          </DialogDescription>
        </DialogHeader>
        <ScrollArea className="h-[400px] p-4">
          {keyTopics.length > 0 ? (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">{currentTopic.topic}</h3>
              <p className="text-sm text-muted-foreground">Menciones: {currentTopic.mentions}</p>
              {currentTopic.citations && currentTopic.citations.length > 0 && (
                <div>
                  <h4 className="font-medium mb-2">Citas:</h4>
                  <ul className="list-disc pl-5 text-sm space-y-1">
                    {currentTopic.citations.map((citation, i) => (
                      <li key={i}>{citation}</li>
                    ))}
                  </ul>
                </div>
              )}
              {!currentTopic.citations || currentTopic.citations.length === 0 && (
                <p className="text-sm text-muted-foreground">No hay citas asociadas a este tema.</p>
              )}
            </div>
          ) : (
            <p className="text-center text-muted-foreground">No hay temas clave disponibles.</p>
          )}
        </ScrollArea>
        {keyTopics.length > 0 && (
          <DialogFooter className="flex justify-between items-center p-4 border-t">
            <Button
              variant="outline"
              onClick={handlePrev}
              disabled={currentTopicIndex === 0}
            >
              Anterior
            </Button>
            <span className="text-sm text-muted-foreground">
              {currentTopicIndex + 1} / {keyTopics.length}
            </span>
            <Button
              variant="outline"
              onClick={handleNext}
              disabled={currentTopicIndex === keyTopics.length - 1}
            >
              Siguiente
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
};