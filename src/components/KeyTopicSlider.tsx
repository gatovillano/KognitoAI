import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowLeft, ArrowRight, LibraryBig } from 'lucide-react';
import { KeyTopic } from '@/lib/models';
import { ScrollArea } from '@/components/ui/scroll-area';

interface KeyTopicSliderProps {
  title: string;
  keyTopics: KeyTopic[];
  icon?: React.ReactNode;
  emptyMessage?: string;
  autoSlide?: boolean;
  slideInterval?: number;
  onKeyTopicClick?: (topic: KeyTopic) => void; // Nueva prop
}

export const KeyTopicSlider: React.FC<KeyTopicSliderProps> = ({
  title,
  keyTopics,
  icon,
  emptyMessage = "No hay temas clave disponibles.",
  autoSlide = false,
  slideInterval = 5000,
  onKeyTopicClick, // Usar la nueva prop
}) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isHovered, setIsHovered] = useState(false);

  const handleNext = useCallback(() => {
    setCurrentIndex((prevIndex) => (prevIndex + 1) % keyTopics.length);
  }, [keyTopics.length]);

  const handlePrev = useCallback(() => {
    setCurrentIndex((prevIndex) => (prevIndex - 1 + keyTopics.length) % keyTopics.length);
  }, [keyTopics.length]);

  useEffect(() => {
    if (autoSlide && keyTopics.length > 1) {
      const timer = setInterval(handleNext, slideInterval);
      return () => clearInterval(timer);
    }
  }, [autoSlide, slideInterval, keyTopics.length, handleNext]);

  if (keyTopics.length === 0) {
    return (
      <Card className="modern-card h-full relative overflow-hidden group hover-lift transition-all duration-300">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            {icon || <LibraryBig className="h-5 w-5 text-primary" />}
            {title}
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col justify-center items-center h-48">
          <p className="text-sm text-muted-foreground mb-4 text-center">
            {emptyMessage}
          </p>
        </CardContent>
      </Card>
    );
  }

  const currentTopic = keyTopics[currentIndex];

  return (
    <>
      <Card
        className="modern-card h-full relative overflow-hidden group hover-lift cursor-pointer transition-all duration-300 hover:scale-105"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onClick={() => onKeyTopicClick && onKeyTopicClick(currentTopic)}
      >
      <CardHeader className="pb-3">
        <div className="flex items-center gap-3">
          {icon || <LibraryBig className="h-5 w-5 text-primary" />}
          <CardTitle className="text-lg font-semibold">{title}</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="flex-grow flex flex-col justify-between">
        <ScrollArea className="h-[150px] pr-4">
          <h3 className="text-md font-bold mb-2">{currentTopic.topic}</h3>
          <p className="text-sm text-muted-foreground mb-3">Menciones: {currentTopic.mentions}</p>
          {currentTopic.citations && currentTopic.citations.length > 0 && (
            <div>
              <h4 className="font-medium text-sm mb-1">Citas:</h4>
              <ul className="list-disc pl-5 text-xs space-y-1">
                {currentTopic.citations.map((citation, i) => (
                  <li key={i}>{citation.quote} (Fuente: {citation.document_title})</li>
                ))}
              </ul>
            </div>
          )}
          {!currentTopic.citations || currentTopic.citations.length === 0 && (
            <p className="text-xs text-muted-foreground mt-2">No hay citas asociadas a este tema.</p>
          )}
        </ScrollArea>
        <div className="flex justify-between items-center mt-4 pt-4 border-t">
          <Button variant="outline" size="sm" onClick={handlePrev} disabled={keyTopics.length <= 1}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm text-muted-foreground">
            {currentIndex + 1} / {keyTopics.length}
          </span>
          <Button variant="outline" size="sm" onClick={handleNext} disabled={keyTopics.length <= 1}>
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
      </Card>
    </>
  );
};