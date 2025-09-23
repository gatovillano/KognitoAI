'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Image from 'next/image';
import { Button } from '@/components/ui/button';
import { Download } from 'lucide-react';
import Lightbox from "yet-another-react-lightbox";
import "yet-another-react-lightbox/styles.css";
import Masonry from 'react-masonry-css';

// Define types (mirroring backend Pydantic models)
interface PhotoResponse {
  id: string;
  album_id: string;
  file_path: string;
  is_favorite: boolean;
  uploaded_at: string;
}

interface AlbumResponse {
  id: string;
  name: string;
  description: string | null;
  account_id: string;
  created_at: string;
  updated_at: string;
  cover_photo_id: string | null;
  photos: PhotoResponse[];
  allow_download?: boolean; // NEW FIELD
}

const SharedAlbumPage: React.FC = () => {
  const params = useParams();
  const token = (params?.token || '') as string;

  const [album, setAlbum] = useState<AlbumResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [password, setPassword] = useState('');
  const [passwordRequired, setPasswordRequired] = useState(false);
  const [open, setOpen] = React.useState(false); // Corregido a 'false'
  const [currentIndex, setCurrentIndex] = React.useState(0);

  const fetchSharedAlbum = useCallback(async (submitPassword?: string) => {
    setLoading(true);
    setError(null);
    setPasswordRequired(false);

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 segundos de timeout

      const payload: { password?: string } = {};
      if (submitPassword) {
        payload.password = submitPassword;
      }

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/galleries/share/${token}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: controller.signal, // Pasa la señal al fetch
      });

      clearTimeout(timeoutId); // Limpia el timeout si la solicitud se completa a tiempo

      if (response.status === 401) {
        setPasswordRequired(true);
        setLoading(false);
        return;
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const data: AlbumResponse = await response.json();
      setAlbum(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (token) {
      fetchSharedAlbum();
    }
  }, [token, fetchSharedAlbum]);

  const handlePasswordSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchSharedAlbum(password);
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8 text-center text-gray-600 dark:text-gray-300">
        Cargando álbum compartido...
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8 text-center text-red-600 dark:text-red-400">
        Error al cargar el álbum: {error}
      </div>
    );
  }

  if (passwordRequired) {
    return (
      <div className="container mx-auto px-4 py-8 flex flex-col items-center justify-center min-h-screen">
        <div className="bg-white dark:bg-gray-800 p-8 rounded-lg shadow-md w-full max-w-sm text-center">
          <h2 className="text-2xl font-bold mb-4 text-gray-800 dark:text-white">Álbum Protegido</h2>
          <p className="text-gray-600 dark:text-gray-300 mb-4">Introduce la contraseña para acceder a este álbum.</p>
          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white"
              placeholder="Contraseña"
              required
            />
            <button
              type="submit"
              className="w-full bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded-lg shadow-md transition-colors duration-300"
            >
              Acceder
            </button>
          </form>
          {error && <p className="text-red-500 text-sm mt-4">Error: {error}</p>}
        </div>
      </div>
    );
  }

  if (!album) {
    return (
      <div className="container mx-auto px-4 py-8 text-center text-gray-600 dark:text-gray-300">
        Álbum no encontrado o no disponible.
      </div>
    );
  }

  const slides = album.photos.map((photo) => ({
      src: `${process.env.NEXT_PUBLIC_API_URL}/media/${photo.file_path}`,
  }));

  const breakpointColumnsObj = {
    default: 3,
    1100: 3,
    700: 3,
    500: 3
  };

  const handleDownload = async () => {
    if (!album) return;
    try {
      console.log('Attempting to download album:', album.name, 'ID:', album.id);
      const downloadUrl = `${process.env.NEXT_PUBLIC_API_URL}/api/galleries/albums/${album.id}/download`;
      console.log('Download URL:', downloadUrl);
      const response = await fetch(downloadUrl);
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response from server:', response.status, errorText);
        throw new Error(`Error al descargar el álbum: ${response.status} - ${errorText}`);
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${album.name}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      console.log('Album download initiated successfully.');
    } catch (error) {
      console.error('Error downloading album:', error);
    }
  };

  return (
    <div className="bg-black min-h-screen" onContextMenu={(e) => e.preventDefault()}>
      <div className="p-6 sm:p-12 max-w-7xl mx-auto overflow-x-hidden">
        {album.allow_download && (
          <div className="absolute top-6 right-6">
            <Button onClick={handleDownload} variant="outline" size="icon" className="text-white border-white">
              <Download className="h-4 w-4" />
            </Button>
          </div>
        )}
        <header className="mb-12 text-center">
          <Image src="/logocl.png" alt="Cuerpo Libre Fotografía" width={200} height={100} className="mx-auto mb-4" />
          <h1 className="text-4xl font-bold text-white mb-2">{album.name}</h1>
          <p className="text-gray-300">{album.description || 'Sin descripción.'}</p>
        </header>

        <section>
          {album.photos.length === 0 ? (
            <p className="text-center text-gray-300">Este álbum no tiene fotos aún.</p>
          ) : (
            <Masonry
              breakpointCols={breakpointColumnsObj}
              className="my-masonry-grid"
              columnClassName="my-masonry-grid_column">
              {album.photos.map((photo, index) => (
                <div key={photo.id} className="relative bg-white dark:bg-gray-700 shadow-md overflow-hidden cursor-pointer mb-3" onClick={() => {
                  setCurrentIndex(index);
                  setOpen(true);
                }}>
                  <Image src={`${process.env.NEXT_PUBLIC_API_URL}/media/${photo.file_path}`} alt="Album Photo" width={500} height={500} className="w-full object-cover" />

                </div>
              ))}
            </Masonry>
          )}
        </section>

        <Lightbox
          open={open}
          close={() => setOpen(false)}
          slides={slides}
          index={currentIndex}
        />

        <footer className="text-center text-gray-500 text-sm mt-12">
          <Image src="/logo transparente.png" alt="Gatovillano Foto" width={150} height={75} className="mx-auto" />
        </footer>
      </div>
    </div>
  );
};

export default SharedAlbumPage;
