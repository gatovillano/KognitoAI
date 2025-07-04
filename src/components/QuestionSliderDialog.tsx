'use client';

import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface QuestionSliderDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  questions: string[];
  title: string;
}

export function QuestionSliderDialog({ isOpen, onOpenChange, questions, title }: QuestionSliderDialogProps) {
  const [currentIndex, setCurrentIndex] = useState(0);

  const handleNext = () => {
    setCurrentIndex((prev) => (prev + 1) % questions.length);
  };

  const handlePrev = () => {
    setCurrentIndex((prev) => (prev - 1 + questions.length) % questions.length);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
          <DialogContent className="max-w-5xl rounded-2xl backdrop-blur-xl bg-card/95 border-0 shadow-2xl">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
            >
              <DialogHeader className="mb-10 mt-4">
                <DialogTitle className="text-3xl font-bold text-center mb-4">{title}</DialogTitle>
                {questions.length > 1 && (
                  <p className="text-lg text-muted-foreground text-center">
                    Pregunta {currentIndex + 1} de {questions.length}
                  </p>
                )}
              </DialogHeader>
              <div className="relative min-h-[400px] flex items-center justify-center px-8 py-6">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={currentIndex}
                    initial={{ opacity: 0, x: 100 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -100 }}
                    transition={{ duration: 0.3, ease: "easeInOut" }}
                    className="absolute text-center p-8 max-w-4xl"
                  >
                    <p className="text-3xl font-medium leading-relaxed text-foreground">
                      {questions[currentIndex]}
                    </p>
                  </motion.div>
                </AnimatePresence>
              </div>

              {questions.length > 1 && (
                <>
                  <div className="flex justify-between items-center mt-12 px-4">
                    <Button
                      variant="outline"
                      onClick={handlePrev}
                      className="rounded-full px-8 py-4 text-lg font-medium"
                    >
                      <ChevronLeft className="h-6 w-6 mr-3" />
                      Anterior
                    </Button>
                    <div className="flex gap-3">
                      {questions.map((_, index) => (
                        <button
                          key={index}
                          onClick={() => setCurrentIndex(index)}
                          className={`w-4 h-4 rounded-full transition-all duration-200 ${
                            index === currentIndex
                              ? 'bg-primary scale-125'
                              : 'bg-muted-foreground/30 hover:bg-muted-foreground/50'
                          }`}
                        />
                      ))}
                    </div>
                    <Button
                      variant="outline"
                      onClick={handleNext}
                      className="rounded-full px-8 py-4 text-lg font-medium"
                    >
                      Siguiente
                      <ChevronRight className="h-6 w-6 ml-3" />
                    </Button>
                  </div>
                </>
              )}
            </motion.div>
          </DialogContent>
        </Dialog>
      )}
    </AnimatePresence>
  );
}
