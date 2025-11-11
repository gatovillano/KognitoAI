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
      <input
        type="text"
        placeholder="Buscar en todo..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        className="pl-8 pr-4 py-2 border border-border rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 w-64 bg-background text-foreground placeholder:text-muted-foreground transition-all"
      />
      <Search className="h-4 w-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" />

      <UniversalSearchDialog
        isOpen={isUniversalSearchDialogOpen}
        onOpenChange={setIsUniversalSearchDialogOpen}
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
      />
    </div>
  );
}