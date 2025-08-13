'use client';

import { DocumentCollectionDisplay } from '@/components/DocumentCollectionDisplay';
import React from 'react';
import { useParams } from 'next/navigation'; // Importar useParams

export default function CollectionDetailPage() {
  const params = useParams();
  const topic = params ? decodeURIComponent(params.topic as string) : '';

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden"> {/* Ajustado padding */}
      <DocumentCollectionDisplay
        topic={topic}
        collectionName={topic}
        backButtonText="Volver a Colecciones"
        backButtonHref="/rag/all"
      />
    </div>
  );
}