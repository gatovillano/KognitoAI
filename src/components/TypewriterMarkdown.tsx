// src/components/TypewriterMarkdown.tsx
import React, { useState, useEffect } from 'react';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';

interface TypewriterMarkdownProps {
  content: string;
  speed?: number;
  shouldAnimate?: boolean; // Nueva prop para controlar la animación
}

const TypewriterMarkdown: React.FC<TypewriterMarkdownProps> = ({ content, speed = 20, shouldAnimate = true }) => {
  const [displayedContent, setDisplayedContent] = useState('');
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    if (!shouldAnimate) {
      setDisplayedContent(content);
      setIsComplete(true);
      return;
    }

    // Reinicia la animación si el contenido cambia
    setDisplayedContent('');
    setIsComplete(false);
    let i = 0;
    const intervalId = setInterval(() => {
      if (i < content.length) {
        setDisplayedContent((prev) => prev + content.charAt(i));
        i++;
      } else {
        clearInterval(intervalId);
        setIsComplete(true);
      }
    }, speed);

    return () => clearInterval(intervalId);
  }, [content, speed, shouldAnimate]);

  // Añade un cursor parpadeante mientras se escribe para una mejor UX
  const contentToRender = isComplete ? displayedContent : displayedContent + '▋';

  return <MarkdownRenderer content={contentToRender} />;
};

export default TypewriterMarkdown;
