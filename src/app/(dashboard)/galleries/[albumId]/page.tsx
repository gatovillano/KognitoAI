import AlbumDetailPageClient from './client';

interface AlbumDetailPageProps {
  params: Promise<{
    albumId: string;
  }>;
}

export default async function AlbumDetailPage({ params }: AlbumDetailPageProps) {
  const { albumId } = await params;

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden">
      <AlbumDetailPageClient albumId={albumId} />
    </div>
  );}
