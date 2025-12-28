'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight, HelpCircle, Expand } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { QuestionSliderDialog } from './QuestionSliderDialog';

interface QuestionSliderProps {
  title: string;
  questions: string[];
  icon?: React.ReactNode;
  emptyMessage: string;
  onReload?: () => void;
  isLoading?: boolean;
  autoSlide?: boolean;
  slideInterval?: number;
  showCounter?: boolean;
  onDevelopClick?: () => void;
}

export function QuestionSlider({
  title,
  questions,
  icon = <HelpCircle className="h-5 w-5 text-primary" />,
  emptyMessage,
  onReload,
  isLoading = false,
  autoSlide = true,
  slideInterval = 4000,
  showCounter = true,
  onDevelopClick
}: QuestionSliderProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isHovered, setIsHovered] = useState(false);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  // Auto-slide functionality
  useEffect(() => {
    if (!autoSlide || questions.length <= 1 || isHovered) return;

    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % questions.length);
    }, slideInterval);

    return () => clearInterval(interval);
  }, [autoSlide, questions.length, slideInterval, isHovered]);

  const nextSlide = () => {
    setCurrentIndex((prev) => (prev + 1) % questions.length);
  };

  const prevSlide = () => {
    setCurrentIndex((prev) => (prev - 1 + questions.length) % questions.length);
  };

  const goToSlide = (index: number) => {
    setCurrentIndex(index);
  };

  if (questions.length === 0) {
    return (
      <Card className="modern-card h-full relative overflow-hidden group hover-lift transition-all duration-300">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            {icon}
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

  return (
    <>
      <Card
        className="modern-card h-full relative overflow-hidden group hover-lift cursor-pointer transition-all duration-300 hover:scale-105"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onClick={() => setIsDialogOpen(true)}
      >
        <CardHeader>
          <CardTitle className="flex items-center justify-between text-lg">
            <div className="flex items-center gap-2">
              {icon}
              {title}
            </div>
            <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-200">
              <Expand className="h-4 w-4 text-muted-foreground" />
            </div>
          </CardTitle>
        </CardHeader>
      
      <CardContent className="relative h-48">
        {/* Slide Content */}
        <div className="relative h-full">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentIndex}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3, ease: "easeInOut" }}
              className="absolute inset-0 flex items-center"
            >
              <div>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {questions[currentIndex]}
                </p>
              </div>
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Navigation Controls */}
        {questions.length > 1 && (
          <>
            {/* Navigation Buttons */}
            <div className="absolute top-4 right-4 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity z-10">
              <Button
                variant="ghost"
                size="icon"
                onClick={(e) => {
                  e.stopPropagation();
                  prevSlide();
                }}
                className="h-8 w-8 rounded-full bg-background/80 hover:bg-background"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={(e) => {
                  e.stopPropagation();
                  nextSlide();
                }}
                className="h-8 w-8 rounded-full bg-background/80 hover:bg-background"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>

            {/* Dots Indicator */}
            <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 flex gap-2">
              {questions.map((_, index) => (
                <button
                  key={index}
                  onClick={(e) => {
                    e.stopPropagation();
                    goToSlide(index);
                  }}
                  className={`w-2 h-2 rounded-full transition-all duration-200 ${
                    index === currentIndex
                      ? 'bg-primary scale-125'
                      : 'bg-muted-foreground/30 hover:bg-muted-foreground/50'
                  }`}
                />
              ))}
            </div>

            {/* Progress Bar */}
            {autoSlide && !isHovered && (
              <div className="absolute bottom-0 left-0 w-full h-1 bg-muted/30">
                <motion.div
                  className="h-full bg-primary"
                  initial={{ width: "0%" }}
                  animate={{ width: "100%" }}
                  transition={{ 
                    duration: slideInterval / 1000, 
                    ease: "linear",
                    repeat: Infinity 
                  }}
                  key={currentIndex}
                />
              </div>
            )}
          </>
        )}

        {/* Question Counter */}
        {showCounter && questions.length > 1 && (
          <div className="absolute top-4 left-4 text-xs text-muted-foreground bg-muted/20 px-2 py-1 rounded-full">
            {currentIndex + 1} de {questions.length}
          </div>
        )}
      </CardContent>
    </Card>

    <QuestionSliderDialog
      isOpen={isDialogOpen}
      onOpenChange={setIsDialogOpen}
      questions={questions}
      title={title}
      onDevelopClick={onDevelopClick}
    />
  </>
  );
}