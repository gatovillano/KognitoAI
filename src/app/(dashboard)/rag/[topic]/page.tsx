'use client';

import { DocumentCollectionDisplay } from '@/components/DocumentCollectionDisplay';
import React from 'react';
import { useParams, useSearchParams } from 'next/navigation';

export default function CollectionDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const topic = params ? decodeURIComponent(params.topic as string) : '';
  const workspaceId = searchParams ? searchParams.get('workspace_id') : null;


  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto">
      <DocumentCollectionDisplay
        topic={topic}
        collectionName={topic}
        workspaceId={workspaceId || undefined}
        backButtonText={workspaceId ? "Volver al Workspace" : "Volver a Colecciones"}
        backButtonHref={workspaceId ? `/workspaces/${workspaceId}` : "/rag/all"}
      />
    </div>
  );
}
