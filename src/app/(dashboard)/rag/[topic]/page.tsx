'use client';

import { DocumentCollectionDisplay } from '@/components/DocumentCollectionDisplay';
import React from 'react';
import { useParams, useSearchParams } from 'next/navigation';

export default function CollectionDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const topic = params ? decodeURIComponent(params.topic as string) : '';
  const workspaceId = searchParams.get('workspace_id');

  console.log("[topic] page - workspaceId from URL:", workspaceId); // DEBUG

  return (
    <div className="p-4 sm:p-8 mx-auto overflow-x-hidden">
      <DocumentCollectionDisplay
        topic={topic}
        collectionName={topic}
        workspaceId={workspaceId || undefined}
        backButtonText="Volver a Colecciones"
        backButtonHref="/rag"
      />
    </div>
  );
}
