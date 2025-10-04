'use client';

import React from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { motion } from 'framer-motion';
import { Image as ImageIcon, MoreHorizontal, Edit, Trash2, Link as LinkIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { AlbumResponse } from '@/types/gallery'; // Assuming a common type definition

// A more generic album type to be compatible with different API responses
interface GenericAlbum extends Omit<AlbumResponse, 'photos'> {
  photos?: AlbumResponse['photos'];
}

interface AlbumCardProps {
  album: GenericAlbum;
  onEditClick?: (album: GenericAlbum) => void;
  onDeleteClick?: (albumId: string) => void;
  onLinkProfileClick?: (album: { id: string; name: string; }) => void;
}

export const AlbumCard = ({ album, onEditClick, onDeleteClick, onLinkProfileClick }: AlbumCardProps) => {
  const coverPhoto = album.cover_photo || (album.photos && album.photos.find(p => p.id === album.cover_photo_id));

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className="h-full"
    >
      <Link href={`/galleries/${album.id}`} passHref>
        <Card className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/30 flex flex-col h-full min-h-[320px]">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <ImageIcon className="h-5 w-5 text-primary" />
                </div>
                <span className="font-semibold text-lg truncate">{album.name}</span>
              </div>
              {(onEditClick || onDeleteClick || onLinkProfileClick) && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                      }}
                    >
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-[180px]">
                    {onEditClick && (
                      <DropdownMenuItem onClick={(e) => { e.preventDefault(); e.stopPropagation(); onEditClick(album); }}>
                        <Edit className="mr-2 h-4 w-4" />
                        Editar Álbum
                      </DropdownMenuItem>
                    )}
                    {onLinkProfileClick && (
                      <DropdownMenuItem onClick={(e) => { e.preventDefault(); e.stopPropagation(); onLinkProfileClick({ id: album.id, name: album.name }); }}>
                        <LinkIcon className="mr-2 h-4 w-4" />
                        Vincular a Perfil
                      </DropdownMenuItem>
                    )}
                    {onDeleteClick && (
                      <DropdownMenuItem onClick={(e) => { e.preventDefault(); e.stopPropagation(); onDeleteClick(album.id); }} className="text-destructive focus:text-destructive">
                        <Trash2 className="mr-2 h-4 w-4" />
                        Eliminar Álbum
                      </DropdownMenuItem>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 flex-grow flex flex-col">
            <div className="relative w-full aspect-square bg-muted rounded-md overflow-hidden mb-3">
              {coverPhoto ? (
                <Image
                  src={`${process.env.NEXT_PUBLIC_API_URL}/media/${coverPhoto.file_path}`}
                  alt={album.name || 'cover photo'}
                  width={500}
                  height={500}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-muted-foreground">
                  <ImageIcon className="h-10 w-10 opacity-50" />
                </div>
              )}
            </div>
            <p className="text-sm text-muted-foreground line-clamp-2">
              {album.description || 'Sin descripción'}
            </p>
          </CardContent>
          <CardFooter className="flex justify-between items-center text-xs text-muted-foreground pt-3 mt-auto border-t border-border/50">
            <span>{album.photos ? album.photos.length : 0} foto(s)</span>
            <span>{new Date(album.created_at).toLocaleDateString()}</span>
          </CardFooter>
        </Card>
      </Link>
    </motion.div>
  );
};
