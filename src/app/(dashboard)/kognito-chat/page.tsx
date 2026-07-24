'use client';

import React from 'react';
import KognitoChatPanel from '@/components/KognitoChatPanel';

export default function KognitoChatPage() {
  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto h-[calc(100vh-3.5rem)]">
      <KognitoChatPanel />
    </div>
  );
}
