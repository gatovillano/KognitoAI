import logging
import logging
import uuid
import os
import aiofiles
import secrets
import hashlib
from datetime import datetime, timedelta
from PIL import Image, ImageOps # Added
import io # Added
import zipfile
from fastapi.responses import StreamingResponse, FileResponse

from fastapi import APIRouter, Depends, HTTPException, Response, File, UploadFile, status, Query, Security # Added Query
from fastapi.concurrency import run_in_threadpool # Added
import shutil # Added
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List, Optional, Tuple # Added Tuple

from core.dependencies import get_db_session
from core.database import Album, Account, Photo, SharedAlbumLink, ContactProfile
from core.config import settings
from api.auth import get_current_account_id
from utils.security import get_optional_current_active_account
from sqlalchemy.future import select
from sqlalchemy import func # Added func

logger = logging.getLogger(__name__)

# Helper function to get the current account (similar to other api files)
async def get_current_account(account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db_session)) -> Account:
    account = await db.get(Account, uuid.UUID(account_id))
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")
    return account

router = APIRouter()

# --- Pydantic Models for Gallery Feature ---

class ContactProfileResponse(BaseModel):
    id: uuid.UUID
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    # Add other fields as necessary from ContactProfile model

    class Config:
        from_attributes = True

class PhotoResponse(BaseModel):
    id: uuid.UUID
    album_id: uuid.UUID
    file_path: str
    thumbnail_path: Optional[str] = None # NEW FIELD
    is_favorite: bool
    uploaded_at: datetime
    order: Optional[int] = None # Modificado para ser opcional

    class Config:
        from_attributes = True

from api.schemas import ProfileLinkRequest

class AlbumBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Nombre del álbum.")
    description: Optional[str] = Field(None, max_length=500, description="Descripción opcional del álbum.")
    workspace_id: Optional[uuid.UUID] = Field(None, description="Workspace al que pertenece el álbum.")

class AlbumCreate(AlbumBase):
    pass

class AlbumUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Nuevo nombre del álbum.")
    description: Optional[str] = Field(None, max_length=500, description="Nueva descripción opcional del álbum.")
    workspace_id: Optional[uuid.UUID] = Field(None, description="Nuevo workspace asociado al álbum.")

class SetCoverRequest(BaseModel):
    photo_id: uuid.UUID

class AlbumResponse(AlbumBase):
    id: uuid.UUID
    account_id: uuid.UUID
    workspace_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    cover_photo_id: Optional[uuid.UUID] = None
    cover_photo: Optional[PhotoResponse] = None # NEW FIELD for album cover
    photos: List[PhotoResponse] = []
    total_photos: int # NEW FIELD
    allow_download: Optional[bool] = None # NEW FIELD for shared album download permission

    class Config:
        from_attributes = True

# --- Pydantic Models for Shared Links ---
class SharedLinkCreate(BaseModel):
    password: Optional[str] = Field(None, min_length=4, description="Contraseña para proteger el enlace (opcional).")
    expiry_days: Optional[int] = Field(None, gt=0, description="Días hasta que el enlace expire (opcional).")
    allow_download: Optional[bool] = Field(True, description="Permitir la descarga de fotos desde este enlace.")

class SharedLinkResponse(BaseModel):
    id: uuid.UUID
    album_id: uuid.UUID
    token: str
    has_password: bool
    expiry_date: Optional[datetime]
    created_at: datetime
    allow_download: bool

    class Config:
        from_attributes = True

class SharedLinkAccess(BaseModel):
    password: Optional[str] = None

# --- Constants ---
MEDIA_ROOT = settings.media_root
THUMBNAIL_ROOT = settings.thumbnails_root

def get_account_media_root(account: Optional[Account]) -> str:
    if account and getattr(account, "cloud_storage_path", None):
        path = os.path.join(account.cloud_storage_path, "photos")
        os.makedirs(path, exist_ok=True)
        return path
    return MEDIA_ROOT

# --- Helper Functions ---
async def get_photo_and_verify_ownership(photo_id: uuid.UUID, current_account: Account, db: AsyncSession) -> Photo:
    stmt = (
        select(Photo)
        .join(Album, Photo.album_id == Album.id) # Explicit join condition
        .where(Photo.id == photo_id, Album.account_id == current_account.id)
    )
    result = await db.execute(stmt)
    photo = result.scalars().first()
    if not photo:
        raise HTTPException(status_code=404, detail="Foto no encontrada o no autorizada.")
    return photo

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

async def get_account_for_media(
    token: Optional[str] = Query(
        None,
        description="JWT alternativo. Necesario porque <img src> y el visor de "
                    "lightbox no pueden enviar el header Authorization.",
    ),
    bearer_account: Optional[Account] = Security(get_optional_current_active_account),
    db: AsyncSession = Depends(get_db_session),
) -> Account:
    """Autenticación para servir/binario de fotos: acepta Bearer o ?token=."""
    if bearer_account is not None:
        return bearer_account

    if token:
        from utils.security import decode_access_token
        payload = decode_access_token(token)
        if payload and payload.get("sub"):
            account = (
                await db.execute(
                    select(Account).where(
                        Account.id == payload["sub"], Account.is_active == True
                    )
                )
            ).scalars().first()
            if account:
                return account

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autorizado.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def resolve_photo_path(account: Optional[Account], file_path: str) -> str:
    """Resolves a Photo.file_path (stored relative to the account media root).

    Photo.file_path is relative on purpose, but the account media root can live
    outside MEDIA_ROOT when the account has cloud_storage_path configured.
    """
    return os.path.join(get_account_media_root(account), file_path)

# Thumbnail geometry is intentionally generous: the grid renders these at
# device-pixel sizes well above 256px, and a too-small thumbnail is what makes
# a gallery look "soft" even though the originals are pristine.
THUMBNAIL_SIZE = (1024, 1024)
THUMBNAIL_QUALITY = 90

def _srgb_convert(img, icc_bytes):
    """Convierte un thumbnail a sRGB (estándar web) preservando la apariencia.

    - Si el original ya es sRGB, devuelve la imagen y los bytes del perfil para
      re-incrustarlos tal cual (round-trip seguro, sin conversión).
    - Si es un perfil amplio (Adobe RGB, Display P3...), convierte los píxeles
      a sRGB con intent perceptual y devuelve (imagen, None): sRGB es el
      valor asumido por defecto en la web, así el thumbnail se ve correcto
      incluso donde no hay gestión de color.
    - Si algo falla (perfil corrupto, LCMS ausente), devuelve (imagen, None)
      y el llamador incrusta el perfil original como red de seguridad para
      navegadores con gestión de color.
    """
    try:
        import io as _io
        from PIL import ImageCms as _ImageCms

        src_profile = _ImageCms.getOpenProfile(_io.BytesIO(icc_bytes))
        desc = _ImageCms.getProfileDescription(src_profile).strip().lower()
        if "srgb" in desc:
            return img, icc_bytes
        srgb_profile = _ImageCms.createProfile("sRGB")
        converted = _ImageCms.profileToProfile(
            img, src_profile, srgb_profile, outputMode="RGB"
        )
        return converted, None
    except Exception as e:
        logger.warning(f"No se pudo convertir a sRGB ({e}); se conserva el perfil original.")
        return img, icc_bytes


def generate_thumbnail_sync(image_path: str, output_path: str, size: Tuple[int, int] = THUMBNAIL_SIZE) -> bool:
    """Generates a JPEG thumbnail for an image synchronously.

    The original file is never modified. Returns False when the image cannot be
    processed (unsupported or corrupt format) so the caller can continue instead
    of failing the whole upload batch.

    Color: el thumbnail se normaliza a sRGB (o conserva el ICC si ya es sRGB).
    Sin esto, un original Adobe RGB pierde su perfil al re-guardar, el navegador
    asume sRGB y los negros se lavan / los colores se desaturan.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    try:
        img = Image.open(image_path)
        # Capturar el ICC antes de transformar: convert()/transpose pueden
        # crear objetos nuevos sin .info.
        icc_bytes = img.info.get("icc_profile") if hasattr(img, "info") else None
        # Honour EXIF orientation, otherwise portrait phone photos render sideways.
        img = ImageOps.exif_transpose(img) or img
        img.thumbnail(size, Image.Resampling.LANCZOS)
        if img.mode not in ("RGB", "L"):
            # CMYK / palette / alpha cannot be written as JPEG.
            img = img.convert("RGB")
        save_kwargs = {"quality": THUMBNAIL_QUALITY, "optimize": True, "progressive": True}
        if icc_bytes:
            img, out_icc = _srgb_convert(img, icc_bytes)
            if out_icc:
                # Solo cuando el original ya era sRGB (o la conversión falló y
                # devolvimos los píxeles intactos): píxeles y perfil emparejados.
                # Un thumbnail convertido a sRGB se guarda SIN perfil porque
                # sRGB es el asumido por defecto en la web; incrustar el perfil
                # Adobe original sobre píxeles ya convertidos duplicaría el cambio.
                save_kwargs["icc_profile"] = out_icc
        img.save(output_path, "JPEG", **save_kwargs)
        return True
    except Exception as e:
        logger.warning(f"No se pudo generar thumbnail para {os.path.basename(image_path)}: {e}")
        return False

# --- Album Endpoints ---

@router.post("/albums", response_model=AlbumResponse, summary="Crear un nuevo álbum")
async def create_album(
    album_data: AlbumCreate,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Crea un nuevo álbum de fotos para la cuenta del usuario actual.
    """
    try:
        new_album = Album(
            account_id=current_account.id,
            workspace_id=album_data.workspace_id,
            name=album_data.name,
            description=album_data.description
        )
        db.add(new_album)
        await db.commit()
        await db.refresh(new_album)

        # For a new album, total_photos is 0
        total_photos = 0

        return AlbumResponse(
            id=new_album.id,
            account_id=new_album.account_id,
            workspace_id=new_album.workspace_id,
            name=new_album.name,
            description=new_album.description,
            created_at=new_album.created_at,
            updated_at=new_album.updated_at,
            cover_photo_id=new_album.cover_photo_id,
            cover_photo=None, # New album has no cover photo initially
            photos=[], # New album has no photos initially
            total_photos=total_photos
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al crear el álbum: {e}")

@router.get("/albums", response_model=List[AlbumResponse], summary="Listar todos los álbumes")
async def get_albums(
    workspace_id: Optional[str] = Query(None),
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Obtiene una lista de todos los álbumes pertenecientes a la cuenta del usuario actual.
    """
    try:
        # Fetch albums
        stmt = select(Album).where(Album.account_id == current_account.id)
        if workspace_id and workspace_id != "all":
            try:
                ws_uuid = uuid.UUID(workspace_id)
                stmt = stmt.where(Album.workspace_id == ws_uuid)
            except ValueError:
                pass
        stmt = stmt.order_by(Album.created_at.desc())
        
        result = await db.execute(stmt)
        albums = result.scalars().all()

        # For each album, get the total photo count and construct AlbumResponse
        albums_response = []
        for album in albums:
            total_photos_stmt = select(func.count(Photo.id)).where(Photo.album_id == album.id)
            total_photos_result = await db.execute(total_photos_stmt)
            total_photos = total_photos_result.scalar_one()

            cover_photo_obj: Optional[PhotoResponse] = None
            if album.cover_photo_id:
                cover_photo_stmt = select(Photo).where(Photo.id == album.cover_photo_id)
                cover_photo_result = await db.execute(cover_photo_stmt)
                photo = cover_photo_result.scalars().first()
                if photo:
                    cover_photo_obj = PhotoResponse(
                        id=photo.id,
                        album_id=photo.album_id,
                        file_path=photo.file_path,
                        thumbnail_path=photo.thumbnail_path,
                        is_favorite=photo.is_favorite,
                        uploaded_at=photo.uploaded_at,
                        order=photo.order # Assign the new 'order' field
                    )

            albums_response.append(AlbumResponse(
                id=album.id,
                account_id=album.account_id,
                workspace_id=album.workspace_id,
                name=album.name,
                description=album.description,
                created_at=album.created_at,
                updated_at=album.updated_at,
                cover_photo_id=album.cover_photo_id,
                cover_photo=cover_photo_obj, # Assign the fetched cover photo object
                photos=[], # No need to load all photos for the list view
                total_photos=total_photos
            ))
        return albums_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al listar los álbumes: {e}")

@router.get("/albums/{album_id}", response_model=AlbumResponse, summary="Obtener un álbum por ID")
async def get_album(
    album_id: uuid.UUID,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    
    logger.warning(f"Attempting to fetch album with ID: {album_id}")
    logger.warning(f"Current account ID: {current_account.id}")
    try:
        # First, get the album itself
        album_stmt = select(Album).where(Album.id == album_id, Album.account_id == current_account.id)
        album_result = await db.execute(album_stmt)
        album = album_result.scalars().first()

        if not album:
            logger.warning("Album not found or user not authorized.")
            raise HTTPException(status_code=404, detail="Álbum no encontrado o no autorizado.")

        # Get total count of photos in the album
        total_photos = 0 # Initialize total_photos
        total_photos_stmt = select(func.count(Photo.id)).where(Photo.album_id == album.id)
        total_photos_result = await db.execute(total_photos_stmt)
        total_photos = total_photos_result.scalar_one()

        # Get paginated photos
        photos_stmt = (
            select(Photo)
            .where(Photo.album_id == album.id)
            .order_by(Photo.order) # Order by the new 'order' column
        )
        photos_result = await db.execute(photos_stmt)
        paginated_photos = photos_result.scalars().all()

        photos_response = [
            PhotoResponse(
                id=photo.id,
                album_id=photo.album_id,
                file_path=photo.file_path,
                thumbnail_path=photo.thumbnail_path,
                is_favorite=photo.is_favorite,
                uploaded_at=photo.uploaded_at,
                order=photo.order # Assign the new 'order' field
            ) for photo in paginated_photos
        ]

        logger.error(f"[DEBUG] === ENVIANDO {len(photos_response)} FOTOS PARA EL ÁLBUM {album.id} ===")
        print(f"[DEBUG] === ENVIANDO {len(photos_response)} FOTOS PARA EL ÁLBUM {album.id} ===")
        return AlbumResponse(
            id=album.id,
            account_id=album.account_id,
            name=album.name,
            description=album.description,
            created_at=album.created_at,
            updated_at=album.updated_at,
            cover_photo_id=album.cover_photo_id,
            photos=photos_response,
            total_photos=total_photos # Include total_photos
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al obtener el álbum: {e}")

@router.put("/albums/{album_id}", response_model=AlbumResponse, summary="Actualizar un álbum")
async def update_album(
    album_id: uuid.UUID,
    album_data: AlbumUpdate,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Actualiza el nombre y/o la descripción de un álbum existente.
    """
    try:
        stmt = (
            select(Album)
            .options(selectinload(Album.photos))
            .where(Album.id == album_id, Album.account_id == current_account.id)
        )
        result = await db.execute(stmt)
        album = result.scalars().first()

        if not album:
            raise HTTPException(status_code=404, detail="Álbum no encontrado o no autorizado.")

        update_data = album_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(album, key, value)

        await db.commit()
        await db.refresh(album)

        # Get total count of photos in the album
        total_photos_stmt = select(func.count(Photo.id)).where(Photo.album_id == album.id)
        total_photos_result = await db.execute(total_photos_stmt)
        total_photos = total_photos_result.scalar_one()

        return AlbumResponse(
            id=album.id,
            account_id=album.account_id,
            name=album.name,
            description=album.description,
            created_at=album.created_at,
            updated_at=album.updated_at,
            cover_photo_id=album.cover_photo_id,
            photos=[], # No need to load all photos for the list view
            total_photos=total_photos
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al actualizar el álbum: {e}")

@router.delete("/albums/{album_id}", status_code=204, summary="Eliminar un álbum")
async def delete_album(
    album_id: uuid.UUID,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Elimina un álbum y todas las fotos contenidas en él.
    """
    try:
        stmt = select(Album).where(Album.id == album_id, Album.account_id == current_account.id)
        result = await db.execute(stmt)
        album = result.scalars().first()

        if not album:
            raise HTTPException(status_code=404, detail="Álbum no encontrado o no autorizado.")

        # Delete associated shared links first
        shared_links_stmt = select(SharedAlbumLink).where(SharedAlbumLink.album_id == album_id)
        shared_links_result = await db.execute(shared_links_stmt)
        shared_links = shared_links_result.scalars().all()
        for link in shared_links:
            await db.delete(link)

        # Delete the physical album directory if it exists
        account_media_root = get_account_media_root(current_account)
        album_dir = os.path.join(account_media_root, str(album_id))
        if os.path.isdir(album_dir):
            import shutil
            shutil.rmtree(album_dir)

        # Delete the album from the database
        await db.delete(album)
        await db.commit()
        
        return Response(status_code=204)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al eliminar el álbum: {e}")

@router.put("/albums/{album_id}/cover", response_model=AlbumResponse, summary="Establecer foto de portada del álbum")
async def set_album_cover(
    album_id: uuid.UUID,
    request: SetCoverRequest,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Establece una foto como la portada de un álbum.
    """
    stmt = select(Album).where(Album.id == album_id, Album.account_id == current_account.id)
    result = await db.execute(stmt)
    album = result.scalars().first()
    if not album:
        raise HTTPException(status_code=404, detail="Álbum no encontrado o no autorizado.")

    photo = await get_photo_and_verify_ownership(request.photo_id, current_account, db)
    if photo.album_id != album_id:
        raise HTTPException(status_code=400, detail="La foto no pertenece a este álbum.")

    album.cover_photo_id = request.photo_id
    await db.commit()
    await db.refresh(album)

    # Get total count of photos in the album
    total_photos_stmt = select(func.count(Photo.id)).where(Photo.album_id == album.id)
    total_photos_result = await db.execute(total_photos_stmt)
    total_photos = total_photos_result.scalar_one()

    return AlbumResponse(
        id=album.id,
        account_id=album.account_id,
        name=album.name,
        description=album.description,
        created_at=album.created_at,
        updated_at=album.updated_at,
        cover_photo_id=album.cover_photo_id,
        photos=[], # No need to load all photos for the list view
        total_photos=total_photos
    )

@router.get("/albums/{album_id}/linked-profiles", response_model=List[ContactProfileResponse], summary="Obtener perfiles vinculados a un álbum")
async def get_linked_profiles_for_album(
    album_id: uuid.UUID,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Obtiene la lista de perfiles de contacto vinculados a un álbum específico.
    """
    album_stmt = select(Album).options(selectinload(Album.contact_profiles)).where(
        Album.id == album_id,
        Album.account_id == current_account.id
    )
    album_result = await db.execute(album_stmt)
    album = album_result.scalars().first()

    if not album:
        raise HTTPException(status_code=404, detail="Álbum no encontrado o no autorizado.")

    return [ContactProfileResponse.model_validate(profile) for profile in album.contact_profiles]


@router.post("/albums/{album_id}/link-profile", status_code=200, summary="Vincular un perfil a un álbum")
async def link_profile_to_album(
    album_id: uuid.UUID,
    profile_link_request: ProfileLinkRequest,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Vincula un perfil de contacto a un álbum.
    """
    album_stmt = select(Album).options(selectinload(Album.contact_profiles)).where(
        Album.id == album_id,
        Album.account_id == current_account.id
    )
    album_result = await db.execute(album_stmt)
    album = album_result.scalars().first()

    if not album:
        raise HTTPException(status_code=404, detail="Álbum no encontrado o no autorizado.")

    profile_stmt = select(ContactProfile).where(
        ContactProfile.id == profile_link_request.profile_id,
        ContactProfile.account_id == current_account.id
    )
    profile_result = await db.execute(profile_stmt)
    profile = profile_result.scalars().first()

    if not profile:
        raise HTTPException(status_code=404, detail="Perfil de contacto no encontrado o no autorizado.")

    if profile not in album.contact_profiles:
        album.contact_profiles.append(profile)
        await db.commit()
        await db.refresh(album)

    return {"message": "Perfil vinculado exitosamente al álbum."}


@router.post("/albums/{album_id}/unlink-profile", status_code=200, summary="Desvincular un perfil de un álbum")
async def unlink_profile_from_album(
    album_id: uuid.UUID,
    profile_link_request: ProfileLinkRequest,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Desvincula un perfil de contacto de un álbum.
    """
    album_stmt = select(Album).options(selectinload(Album.contact_profiles)).where(
        Album.id == album_id,
        Album.account_id == current_account.id
    )
    album_result = await db.execute(album_stmt)
    album = album_result.scalars().first()

    if not album:
        raise HTTPException(status_code=404, detail="Álbum no encontrado o no autorizado.")

    profile_stmt = select(ContactProfile).where(
        ContactProfile.id == profile_link_request.profile_id,
        ContactProfile.account_id == current_account.id
    )
    profile_result = await db.execute(profile_stmt)
    profile = profile_result.scalars().first()

    if not profile:
        raise HTTPException(status_code=404, detail="Perfil de contacto no encontrado o no autorizado.")

    if profile in album.contact_profiles:
        album.contact_profiles.remove(profile)
        await db.commit()
        await db.refresh(album)

    return {"message": "Perfil desvinculado exitosamente del álbum."}


# --- Photo Endpoints ---

@router.post("/albums/{album_id}/photos", response_model=List[PhotoResponse], summary="Subir fotos a un álbum")
async def upload_photos(
    album_id: uuid.UUID,
    files: List[UploadFile] = File(...),
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Sube una o más fotos a un álbum específico.
    """
    album = await db.get(Album, album_id)
    if not album or album.account_id != current_account.id:
        raise HTTPException(status_code=404, detail="Álbum no encontrado o no autorizado.")

    account_media_root = get_account_media_root(current_account)
    album_dir = os.path.join(account_media_root, str(album_id))
    os.makedirs(album_dir, exist_ok=True)

    # Get the current total number of photos in the album to set the starting order
    total_photos_stmt = select(func.count(Photo.id)).where(Photo.album_id == album_id)
    total_photos_result = await db.execute(total_photos_stmt)
    current_total_photos = total_photos_result.scalar_one()

    created_photos = []
    for idx, file in enumerate(files):
        unique_filename = f"{uuid.uuid4()}-{file.filename}"
        file_path = os.path.join(album_dir, unique_filename)

        # Save the original file verbatim, using shutil.copyfileobj in a threadpool.
        # This is a raw byte copy: no re-encoding, so quality is preserved exactly.
        with open(file_path, 'wb') as buffer:
            await run_in_threadpool(shutil.copyfileobj, file.file, buffer)

        db_file_path = os.path.join(str(album_id), unique_filename)

        # Generate thumbnail in a threadpool. Thumbnails are always JPEG so the
        # Content-Type served by StaticFiles matches the actual bytes.
        thumbnail_dir = os.path.join(THUMBNAIL_ROOT, str(album_id))
        os.makedirs(thumbnail_dir, exist_ok=True)
        thumbnail_filename = f"thumb-{uuid.uuid4()}.jpg"
        thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)
        thumbnail_ok = await run_in_threadpool(generate_thumbnail_sync, file_path, thumbnail_path)
        db_thumbnail_path = os.path.join(str(album_id), thumbnail_filename) if thumbnail_ok else None

        new_photo = Photo(
            album_id=album_id,
            file_path=db_file_path,
            thumbnail_path=db_thumbnail_path,
            order=current_total_photos + idx
        )
        db.add(new_photo)
        created_photos.append(new_photo)

    await db.commit()
    for photo in created_photos:
        await db.refresh(photo)

    return created_photos

@router.get("/photos/{photo_id}/file", summary="Obtener el archivo original de una foto")
async def get_photo_file(
    photo_id: uuid.UUID,
    current_account: Account = Depends(get_account_for_media),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Sirve el archivo ORIGINAL de la foto, sin recomprimir, resolviendo la raíz
    de medios de la cuenta. Es la vía correcta para el visor y las descargas:
    el mount estático /media solo expone MEDIA_ROOT y no alcanza las cuentas
    que tienen cloud_storage_path configurado.
    """
    photo = await get_photo_and_verify_ownership(photo_id, current_account, db)

    full_file_path = resolve_photo_path(current_account, photo.file_path)
    if not os.path.isfile(full_file_path):
        raise HTTPException(status_code=404, detail="Archivo original no encontrado en disco.")

    return FileResponse(
        full_file_path,
        filename=os.path.basename(photo.file_path),
        media_type="application/octet-stream",
    )

@router.put("/photos/{photo_id}/favorite", response_model=PhotoResponse, summary="Marcar/desmarcar foto como favorita")
async def toggle_favorite_photo(
    photo_id: uuid.UUID,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Alterna el estado de 'favorita' de una foto.
    """
    photo = await get_photo_and_verify_ownership(photo_id, current_account, db)
    photo.is_favorite = not photo.is_favorite
    await db.commit()
    await db.refresh(photo)
    return photo

@router.delete("/photos/{photo_id}", status_code=204, summary="Eliminar una foto")
async def delete_photo(
    photo_id: uuid.UUID,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Elimina una foto de un álbum y del disco.
    """
    photo = await get_photo_and_verify_ownership(photo_id, current_account, db)

    # Delete the physical file
    full_file_path = resolve_photo_path(current_account, photo.file_path)
    if os.path.exists(full_file_path):
        os.remove(full_file_path)
    else:
        logger.warning(f"Archivo no encontrado en {full_file_path}; se procede a eliminar la fila.")

    # Best-effort cleanup of the generated thumbnail.
    if photo.thumbnail_path:
        thumbnail_path = os.path.join(THUMBNAIL_ROOT, photo.thumbnail_path)
        if os.path.isfile(thumbnail_path):
            try:
                os.remove(thumbnail_path)
            except OSError as e:
                logger.warning(f"No se pudo eliminar el thumbnail {thumbnail_path}: {e}")

    await db.delete(photo)
    await db.commit()

    return Response(status_code=204)

# --- Shared Link Endpoints ---

@router.post("/albums/{album_id}/share-link", response_model=SharedLinkResponse, summary="Generar un enlace para compartir un álbum")
async def generate_share_link(
    album_id: uuid.UUID,
    link_data: SharedLinkCreate,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Genera un enlace único y compartible para un álbum. Puede ser protegido con contraseña y tener una fecha de caducidad.
    """
    album = await db.get(Album, album_id)
    if not album or album.account_id != current_account.id:
        raise HTTPException(status_code=404, detail="Álbum no encontrado o no autorizado.")

    token = secrets.token_urlsafe(16) # Generate a URL-safe token
    password_hash = hash_password(link_data.password) if link_data.password else None
    expiry_date = datetime.utcnow() + timedelta(days=link_data.expiry_days) if link_data.expiry_days else None

    new_link = SharedAlbumLink(
        album_id=album_id,
        token=token,
        password_hash=password_hash,
        expiry_date=expiry_date,
        allow_download=link_data.allow_download # NEW FIELD
    )
    db.add(new_link)
    await db.commit()
    await db.refresh(new_link)

    return SharedLinkResponse(
        id=new_link.id,
        album_id=new_link.album_id,
        token=new_link.token,
        has_password=bool(new_link.password_hash),
        expiry_date=new_link.expiry_date,
        created_at=new_link.created_at,
        allow_download=new_link.allow_download # NEW FIELD
    )

@router.get("/albums/{album_id}/share-links", response_model=List[SharedLinkResponse], summary="Listar enlaces compartidos de un álbum")
async def get_album_share_links(
    album_id: uuid.UUID,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Lista todos los enlaces compartidos activos para un álbum específico.
    """
    album = await db.get(Album, album_id)
    if not album or album.account_id != current_account.id:
        raise HTTPException(status_code=404, detail="Álbum no encontrado o no autorizado.")

    stmt = select(SharedAlbumLink).where(SharedAlbumLink.album_id == album_id)
    result = await db.execute(stmt)
    links = result.scalars().all()
    return [
        SharedLinkResponse(
            id=link.id,
            album_id=link.album_id,
            token=link.token,
            has_password=bool(link.password_hash),
            expiry_date=link.expiry_date,
            created_at=link.created_at,
            allow_download=link.allow_download # NEW FIELD
        )
        for link in links
    ]

@router.post("/share/{token}", response_model=AlbumResponse, summary="Acceder a un álbum compartido")
async def get_shared_album(
    token: str,
    access_data: Optional[SharedLinkAccess] = None, # Password for protected links
    db: AsyncSession = Depends(get_db_session)
):
    """
    Accede a un álbum a través de un enlace compartido. Requiere contraseña si el enlace está protegido.
    """
    stmt = select(SharedAlbumLink).where(SharedAlbumLink.token == token)
    result = await db.execute(stmt)
    shared_link = result.scalars().first()

    if not shared_link:
        raise HTTPException(status_code=404, detail="Enlace compartido no encontrado.")

    if shared_link.expiry_date and shared_link.expiry_date < datetime.utcnow():
        raise HTTPException(status_code=403, detail="Enlace compartido caducado.")

    if shared_link.password_hash:
        if not access_data or not access_data.password:
            raise HTTPException(status_code=401, detail="Contraseña requerida para acceder a este álbum.")
        if hash_password(access_data.password) != shared_link.password_hash:
            raise HTTPException(status_code=401, detail="Contraseña incorrecta.")

    stmt = (
        select(Album)
        .options(selectinload(Album.photos))
        .where(Album.id == shared_link.album_id)
    )
    result = await db.execute(stmt)
    album = result.scalars().first()

    if not album:
        raise HTTPException(status_code=404, detail="Álbum asociado no encontrado.")

    # Calculate total_photos for the album
    total_photos_stmt = select(func.count(Photo.id)).where(Photo.album_id == album.id)
    total_photos_result = await db.execute(total_photos_stmt)
    total_photos = total_photos_result.scalar_one()

    # Get paginated photos
    photos_stmt = (
        select(Photo)
        .where(Photo.album_id == album.id)
        .order_by(Photo.order) # Order by the new 'order' column
    )
    photos_result = await db.execute(photos_stmt)
    album_photos = photos_result.scalars().all()

    photos_response = [
        PhotoResponse(
            id=photo.id,
            album_id=photo.album_id,
            file_path=photo.file_path,
            thumbnail_path=photo.thumbnail_path,
            is_favorite=photo.is_favorite,
            uploaded_at=photo.uploaded_at,
            order=photo.order # Assign the new 'order' field
        ) for photo in album_photos
    ]

    logger.error(f"[DEBUG] === ENVIANDO {len(photos_response)} FOTOS PARA EL ÁLBUM COMPARTIDO {album.id} ===")
    print(f"[DEBUG] === ENVIANDO {len(photos_response)} FOTOS PARA EL ÁLBUM COMPARTIDO {album.id} ===")
    return AlbumResponse(
        id=album.id,
        account_id=album.account_id,
        name=album.name,
        description=album.description,
        created_at=album.created_at,
        updated_at=album.updated_at,
                    cover_photo_id=album.cover_photo_id,
                    photos=photos_response,
                    total_photos=total_photos,
                    allow_download=shared_link.allow_download # NEW FIELD
                )
@router.delete("/share/{token}", status_code=204, summary="Revocar un enlace compartido")
async def revoke_share_link(
    token: str,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Revoca un enlace compartido, haciéndolo inaccesible.
    """
    stmt = select(SharedAlbumLink).where(SharedAlbumLink.token == token)
    result = await db.execute(stmt)
    shared_link = result.scalars().first()

    if not shared_link:
        raise HTTPException(status_code=404, detail="Enlace compartido no encontrado.")

    album = await db.get(Album, shared_link.album_id)
    if not album or album.account_id != current_account.id:
        raise HTTPException(status_code=403, detail="No autorizado para revocar este enlace.")

    await db.delete(shared_link)
    await db.commit()

    return Response(status_code=204)

@router.get("/albums/{album_id}/download", summary="Descargar un álbum como archivo ZIP")
async def download_album_as_zip(
    album_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Descarga todas las fotos de un álbum en un único archivo ZIP.
    """
    album_stmt = select(Album).options(selectinload(Album.photos)).where(
        Album.id == album_id
    )
    album_result = await db.execute(album_stmt)
    album = album_result.scalars().first()

    if not album:
        raise HTTPException(status_code=404, detail="Álbum no encontrado.")

    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, 'w', zipfile.ZIP_DEFLATED) as zipf:
        album_account = await db.get(Account, album.account_id)
        for photo in album.photos:
            file_path = resolve_photo_path(album_account, photo.file_path)
            if os.path.exists(file_path):
                zipf.write(file_path, os.path.basename(file_path))

    zip_io.seek(0)
    return StreamingResponse(zip_io, media_type="application/zip", headers={"Content-Disposition": f"attachment; filename={album.name}.zip"})


class PhotoReorderRequest(BaseModel):
    photo_id: uuid.UUID
    order: int

@router.post("/albums/{album_id}/reorder-photos", status_code=204, summary="Reordenar fotos en un álbum")
async def reorder_photos(
    album_id: uuid.UUID,
    reorder_data: List[PhotoReorderRequest],
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Actualiza el orden de las fotos en un álbum.
    """
    album = await db.get(Album, album_id)
    if not album or album.account_id != current_account.id:
        raise HTTPException(status_code=404, detail="Álbum no encontrado o no autorizado.")

    for item in reorder_data:
        photo = await db.get(Photo, item.photo_id)
        if not photo or photo.album_id != album_id:
            raise HTTPException(status_code=404, detail=f"Foto {item.photo_id} no encontrada en este álbum.")
        photo.order = item.order
        db.add(photo) # Marcar la foto como modificada

    await db.commit()
    return Response(status_code=204)

@router.put("/photos/{photo_id}/favorite", response_model=PhotoResponse, summary="Marcar/desmarcar foto como favorita")
async def toggle_favorite_photo(
    photo_id: uuid.UUID,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Alterna el estado de 'favorita' de una foto.
    """
    photo = await get_photo_and_verify_ownership(photo_id, current_account, db)
    photo.is_favorite = not photo.is_favorite
    await db.commit()
    await db.refresh(photo)
    return photo

@router.delete("/photos/{photo_id}", status_code=204, summary="Eliminar una foto")
async def delete_photo(
    photo_id: uuid.UUID,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Elimina una foto de un álbum y del disco.
    """
    photo = await get_photo_and_verify_ownership(photo_id, current_account, db)

    # Delete the physical file
    full_file_path = resolve_photo_path(current_account, photo.file_path)
    if os.path.exists(full_file_path):
        os.remove(full_file_path)
    else:
        logger.warning(f"Archivo no encontrado en {full_file_path}; se procede a eliminar la fila.")

    # Best-effort cleanup of the generated thumbnail.
    if photo.thumbnail_path:
        thumbnail_path = os.path.join(THUMBNAIL_ROOT, photo.thumbnail_path)
        if os.path.isfile(thumbnail_path):
            try:
                os.remove(thumbnail_path)
            except OSError as e:
                logger.warning(f"No se pudo eliminar el thumbnail {thumbnail_path}: {e}")

    await db.delete(photo)
    await db.commit()

    return Response(status_code=204)

# --- Shared Link Endpoints ---

@router.post("/albums/{album_id}/share-link", response_model=SharedLinkResponse, summary="Generar un enlace para compartir un álbum")
async def generate_share_link(
    album_id: uuid.UUID,
    link_data: SharedLinkCreate,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Genera un enlace único y compartible para un álbum. Puede ser protegido con contraseña y tener una fecha de caducidad.
    """
    album = await db.get(Album, album_id)
    if not album or album.account_id != current_account.id:
        raise HTTPException(status_code=404, detail="Álbum no encontrado o no autorizado.")

    token = secrets.token_urlsafe(16) # Generate a URL-safe token
    password_hash = hash_password(link_data.password) if link_data.password else None
    expiry_date = datetime.utcnow() + timedelta(days=link_data.expiry_days) if link_data.expiry_days else None

    new_link = SharedAlbumLink(
        album_id=album_id,
        token=token,
        password_hash=password_hash,
        expiry_date=expiry_date,
        allow_download=link_data.allow_download # NEW FIELD
    )
    db.add(new_link)
    await db.commit()
    await db.refresh(new_link)

    return SharedLinkResponse(
        id=new_link.id,
        album_id=new_link.album_id,
        token=new_link.token,
        has_password=bool(new_link.password_hash),
        expiry_date=new_link.expiry_date,
        created_at=new_link.created_at,
        allow_download=new_link.allow_download # NEW FIELD
    )

@router.get("/albums/{album_id}/share-links", response_model=List[SharedLinkResponse], summary="Listar enlaces compartidos de un álbum")
async def get_album_share_links(
    album_id: uuid.UUID,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Lista todos los enlaces compartidos activos para un álbum específico.
    """
    album = await db.get(Album, album_id)
    if not album or album.account_id != current_account.id:
        raise HTTPException(status_code=404, detail="Álbum no encontrado o no autorizado.")

    stmt = select(SharedAlbumLink).where(SharedAlbumLink.album_id == album_id)
    result = await db.execute(stmt)
    links = result.scalars().all()
    return [
        SharedLinkResponse(
            id=link.id,
            album_id=link.album_id,
            token=link.token,
            has_password=bool(link.password_hash),
            expiry_date=link.expiry_date,
            created_at=link.created_at,
            allow_download=link.allow_download # NEW FIELD
        )
        for link in links
    ]

@router.post("/share/{token}", response_model=AlbumResponse, summary="Acceder a un álbum compartido")
async def get_shared_album(
    token: str,
    access_data: Optional[SharedLinkAccess] = None, # Password for protected links
    db: AsyncSession = Depends(get_db_session)
):
    """
    Accede a un álbum a través de un enlace compartido. Requiere contraseña si el enlace está protegido.
    """
    stmt = select(SharedAlbumLink).where(SharedAlbumLink.token == token)
    result = await db.execute(stmt)
    shared_link = result.scalars().first()

    if not shared_link:
        raise HTTPException(status_code=404, detail="Enlace compartido no encontrado.")

    if shared_link.expiry_date and shared_link.expiry_date < datetime.utcnow():
        raise HTTPException(status_code=403, detail="Enlace compartido caducado.")

    if shared_link.password_hash:
        if not access_data or not access_data.password:
            raise HTTPException(status_code=401, detail="Contraseña requerida para acceder a este álbum.")
        if hash_password(access_data.password) != shared_link.password_hash:
            raise HTTPException(status_code=401, detail="Contraseña incorrecta.")

    stmt = (
        select(Album)
        .options(selectinload(Album.photos))
        .where(Album.id == shared_link.album_id)
    )
    result = await db.execute(stmt)
    album = result.scalars().first()

    if not album:
        raise HTTPException(status_code=404, detail="Álbum asociado no encontrado.")

    # Calculate total_photos for the album
    total_photos_stmt = select(func.count(Photo.id)).where(Photo.album_id == album.id)
    total_photos_result = await db.execute(total_photos_stmt)
    total_photos = total_photos_result.scalar_one()

    # Get paginated photos
    photos_stmt = (
        select(Photo)
        .where(Photo.album_id == album.id)
        .order_by(Photo.order) # Order by the new 'order' column
    )
    photos_result = await db.execute(photos_stmt)
    album_photos = photos_result.scalars().all()

    photos_response = [
        PhotoResponse(
            id=photo.id,
            album_id=photo.album_id,
            file_path=photo.file_path,
            thumbnail_path=photo.thumbnail_path,
            is_favorite=photo.is_favorite,
            uploaded_at=photo.uploaded_at,
            order=photo.order # Assign the new 'order' field
        ) for photo in album_photos
    ]

    logger.error(f"[DEBUG] === ENVIANDO {len(photos_response)} FOTOS PARA EL ÁLBUM COMPARTIDO {album.id} ===")
    print(f"[DEBUG] === ENVIANDO {len(photos_response)} FOTOS PARA EL ÁLBUM COMPARTIDO {album.id} ===")
    return AlbumResponse(
        id=album.id,
        account_id=album.account_id,
        name=album.name,
        description=album.description,
        created_at=album.created_at,
        updated_at=album.updated_at,
                    cover_photo_id=album.cover_photo_id,
                    photos=photos_response,
                    total_photos=total_photos,
                    allow_download=shared_link.allow_download # NEW FIELD
                )
@router.delete("/share/{token}", status_code=204, summary="Revocar un enlace compartido")
async def revoke_share_link(
    token: str,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Revoca un enlace compartido, haciéndolo inaccesible.
    """
    stmt = select(SharedAlbumLink).where(SharedAlbumLink.token == token)
    result = await db.execute(stmt)
    shared_link = result.scalars().first()

    if not shared_link:
        raise HTTPException(status_code=404, detail="Enlace compartido no encontrado.")

    album = await db.get(Album, shared_link.album_id)
    if not album or album.account_id != current_account.id:
        raise HTTPException(status_code=403, detail="No autorizado para revocar este enlace.")

    await db.delete(shared_link)
    await db.commit()

    return Response(status_code=204)

@router.get("/albums/{album_id}/download", summary="Descargar un álbum como archivo ZIP")
async def download_album_as_zip(
    album_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Descarga todas las fotos de un álbum en un único archivo ZIP.
    """
    album_stmt = select(Album).options(selectinload(Album.photos)).where(
        Album.id == album_id
    )
    album_result = await db.execute(album_stmt)
    album = album_result.scalars().first()

    if not album:
        raise HTTPException(status_code=404, detail="Álbum no encontrado.")

    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, 'w', zipfile.ZIP_DEFLATED) as zipf:
        album_account = await db.get(Account, album.account_id)
        for photo in album.photos:
            file_path = resolve_photo_path(album_account, photo.file_path)
            if os.path.exists(file_path):
                zipf.write(file_path, os.path.basename(file_path))

    zip_io.seek(0)
    return StreamingResponse(zip_io, media_type="application/zip", headers={"Content-Disposition": f"attachment; filename={album.name}.zip"})


class PhotoReorderRequest(BaseModel):
    photo_id: uuid.UUID
    order: int

@router.post("/albums/{album_id}/reorder-photos", status_code=204, summary="Reordenar fotos en un álbum")
async def reorder_photos(
    album_id: uuid.UUID,
    reorder_data: List[PhotoReorderRequest],
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Actualiza el orden de las fotos en un álbum.
    """
    album = await db.get(Album, album_id)
    if not album or album.account_id != current_account.id:
        raise HTTPException(status_code=404, detail="Álbum no encontrado o no autorizado.")

    for item in reorder_data:
        photo = await db.get(Photo, item.photo_id)
        if not photo or photo.album_id != album_id:
            raise HTTPException(status_code=404, detail=f"Foto {item.photo_id} no encontrada en este álbum.")
        photo.order = item.order
        db.add(photo) # Marcar la foto como modificada

    await db.commit()
    return Response(status_code=204)

@router.get("/share/{token}/photos/{photo_id}/file", summary="Original de una foto en un álbum compartido")
async def get_shared_photo_file(
    token: str,
    photo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Sirve el original de una foto a traves de un enlace compartido, resolviendo
    la raiz de medios de la cuenta propietaria del album. Sin esto, la pagina
    publica seguiria leyendo /media y devolveria 404 en cuentas con
    cloud_storage_path configurado.

    Los enlaces protegidos por contrasena NO sirven el original: siguen
    mostrando el thumbnail desde /thumbnails.
    """
    link_stmt = select(SharedAlbumLink).where(SharedAlbumLink.token == token)
    shared_link = (await db.execute(link_stmt)).scalars().first()
    if not shared_link:
        raise HTTPException(status_code=404, detail="Enlace compartido no encontrado.")
    if shared_link.expiry_date and shared_link.expiry_date < datetime.utcnow():
        raise HTTPException(status_code=403, detail="Enlace compartido caducado.")
    if shared_link.password_hash:
        raise HTTPException(
            status_code=401,
            detail="Este album esta protegido por contrasena.",
        )

    photo_stmt = (
        select(Photo)
        .join(Album, Photo.album_id == Album.id)
        .where(Photo.id == photo_id, Album.id == shared_link.album_id)
    )
    photo = (await db.execute(photo_stmt)).scalars().first()
    if not photo:
        raise HTTPException(status_code=404, detail="Foto no encontrada en este album.")

    album = await db.get(Album, shared_link.album_id)
    owner = await db.get(Account, album.account_id)

    full_file_path = resolve_photo_path(owner, photo.file_path)
    if not os.path.isfile(full_file_path):
        raise HTTPException(status_code=404, detail="Archivo original no encontrado en disco.")

    return FileResponse(
        full_file_path,
        filename=os.path.basename(photo.file_path),
        media_type="application/octet-stream",
    )
