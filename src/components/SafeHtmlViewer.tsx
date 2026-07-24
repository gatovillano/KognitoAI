'use client';
import React from 'react';

interface SafeHtmlViewerProps {
  htmlContent: string;
}

export function SafeHtmlViewer({ htmlContent }: SafeHtmlViewerProps) {
  return (
    <iframe
      srcDoc={htmlContent}
      sandbox="allow-popups allow-popups-to-escape-sandbox"
      className="w-full h-full border-none bg-white rounded-2xl min-h-[400px] shadow-inner"
      title="Contenido del Email"
    />
  );
}
