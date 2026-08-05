'use client';

import React from 'react';
import Image from 'next/image';

interface CircuitBrainLogoProps {
  className?: string;
  size?: number;
  glow?: boolean;
  variant?: 'brain' | 'full';
}

export function CircuitBrainLogo({ 
  className = "", 
  size = 64, 
  glow = true,
  variant = 'full'
}: CircuitBrainLogoProps) {
  return (
    <div className={`relative inline-flex items-center justify-center ${className}`}>
      {glow && (
        <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/30 via-blue-500/20 to-purple-600/30 rounded-full blur-xl animate-pulse pointer-events-none" />
      )}
      <div 
        style={{ width: size, height: variant === 'full' ? size * 1.15 : size }}
        className="relative z-10 flex items-center justify-center drop-shadow-[0_0_15px_rgba(6,182,212,0.5)] transition-transform duration-300 hover:scale-105"
      >
        <img
          src="/kognito-labs-logo.png"
          alt="Kognito AI Labs Official Logo"
          className="w-full h-full object-contain"
        />
      </div>
    </div>
  );
}
