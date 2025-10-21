// En: src/app/(dashboard)/workspaces/[id]/collections/[collectionId]/page.tsx

'use client';

import { useEffect, useState, useCallback, use } from 'react';
import { useParams } from 'next/navigation';
import { toast } from 'sonner';

import apiClient from '@/lib/api';
import { DocumentCollectionDisplay } from '@/components/DocumentCollectionDisplay';

interface Collection {
  topic: string;
  document_count: number;
  description?: string;
  team_shared?: boolean;
  has_knowledge_graph?: boolean;
}

interface PageProps {
  params: Promise<{ id: string; collectionId: string }>;
}

export default function WorkspaceCollectionDetailPage({ params }: PageProps) {
  const { id: workspaceId, collectionId } = use(params);
  
  const [collectionData, setCollectionData] = useState<Collection | null>(null);
  const [isLoadingCollection, setIsLoadingCollection] = useState(true);

  console.log('Workspace ID:', workspaceId);
  console.log('Collection ID (from URL):', collectionId);

  const fetchCollectionData = useCallback(async () => {
    if (!workspaceId || !collectionId) return;
    setIsLoadingCollection(true);
    try {
      const collectionRes = await apiClient.get(`/api/documents/collections/${collectionId}/details?workspace_id=${workspaceId}`);
      setCollectionData(collectionRes.data);
    } catch (error) {
      toast.error('Error al cargar los datos de la colección.');
      console.error(error);
    } finally {
      setIsLoadingCollection(false);
    }
  }, [workspaceId, collectionId]);

  useEffect(() => {
    fetchCollectionData();
  }, [fetchCollectionData]);

  if (isLoadingCollection) {
    return <div className="flex justify-center items-center h-full">Cargando colección...</div>;
  }

  if (!collectionData) {
    return <div className="flex justify-center items-center h-full">No se pudo cargar la colección.</div>;
  }

  return (
    <div className="h-full">
      <DocumentCollectionDisplay
        topic={collectionId}
        workspaceId={workspaceId}
        collectionName={collectionData.topic}
        backButtonText="Volver al Workspace"
        backButtonHref={`/workspaces/${workspaceId}`}
      />
    </div>
  );
}