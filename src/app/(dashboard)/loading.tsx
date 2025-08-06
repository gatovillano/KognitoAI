import React from 'react';
import Image from 'next/image';

export default function Loading() {
  return (
    <div className="flex items-center justify-center h-screen bg-background">
      <Image 
        src="/logo-simple.png" 
        alt="Cargando Kognito AI" 
        width={96}
        height={96}
        className="w-24 h-24 animate-pulse" 
      />
    </div>
  );
}
