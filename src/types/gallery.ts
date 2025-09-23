export interface PhotoResponse {
  id: string;
  album_id: string;
  file_path: string;
  thumbnail_path?: string;
  is_favorite: boolean;
  uploaded_at: string;
  order: number;
}

export interface AlbumResponse {
  id: string;
  name: string;
  description: string | null;
  account_id: string;
  created_at: string;
  updated_at: string;
  cover_photo_id: string | null;
  cover_photo?: PhotoResponse; // Add this line
  photos: PhotoResponse[];
}