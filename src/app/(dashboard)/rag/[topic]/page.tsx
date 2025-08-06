'use client';

import { DocumentCollectionDisplay } from '@/components/DocumentCollectionDisplay';
import React from 'react';

interface PageProps {
  params: { topic: string };
}

export default function CollectionDetailPage({ params }: PageProps) {
  const topic = decodeURIComponent(params.topic || '');

  return (
    <div className="h-full">
      <DocumentCollectionDisplay
        topic={topic}
        collectionName={topic}
        backButtonText="Volver a Colecciones"
        backButtonHref="/rag/all"
      />
    </div>
  );
}