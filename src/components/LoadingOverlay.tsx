'use client';

import React from 'react';
import Image from 'next/image';

interface LoadingOverlayProps {
  isLoading: boolean;
}

export function LoadingOverlay({ isLoading }: LoadingOverlayProps) {
  if (!isLoading) return null;

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-background/80 backdrop-blur-sm transition-opacity duration-300 animate-fade-in">
      <Image
        src="/logo-simple.png"
        alt="Loading"
        width={100}
        height={100}
        className="animate-pulse-fade"
      />
    </div>
  );
}
