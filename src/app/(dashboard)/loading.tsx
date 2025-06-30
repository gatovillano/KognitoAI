import React from 'react';

export default function Loading() {
  return (
    <div className="flex items-center justify-center h-screen bg-background">
      <img 
        src="/logo-simple.png" 
        alt="Cargando Kognito AI" 
        className="w-24 h-24 animate-pulse" 
      />
    </div>
  );
}
