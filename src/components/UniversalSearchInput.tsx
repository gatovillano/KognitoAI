'use client';

import React, { useState, useEffect } from 'react';
import { Search } from 'lucide-react';
import { useSearch } from '@/contexts/SearchContext';
import { UniversalSearchDialog } from './UniversalSearchDialog';

export function UniversalSearchInput() {
  const { searchTerm, setSearchTerm } = useSearch();
  const [isUniversalSearchDialogOpen, setIsUniversalSearchDialogOpen] = useState(false);

  useEffect(() => {
    if (searchTerm) {
      setIsUniversalSearchDialogOpen(true);
    } else {
      setIsUniversalSearchDialogOpen(false);
    }
  }, [searchTerm]);

  return (
    <div className="relative">
      {/* Input para escritorio */}
      <div className="hidden md:block relative">
        <input
          type="text"
          placeholder="Buscar en todo..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-8 pr-4 py-2 border border-border rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 w-64 bg-background text-foreground placeholder:text-muted-foreground transition-all"
        />
        <Search className="h-4 w-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" />
      </div>

      {/* Botón de icono para móvil */}
      <button
        type="button"
        onClick={() => setIsUniversalSearchDialogOpen(true)}
        className="md:hidden flex items-center justify-center h-9 w-9 rounded-full border border-border bg-background text-muted-foreground hover:text-primary hover:border-primary/50 transition-all"
        title="Buscar"
      >
        <Search className="h-5 w-5" />
      </button>

      <UniversalSearchDialog
        isOpen={isUniversalSearchDialogOpen}
        onOpenChange={setIsUniversalSearchDialogOpen}
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
      />
    </div>
  );
}