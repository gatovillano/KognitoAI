import uuid
import secrets
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from core.database import get_db_session, Album, Account, Photo
from api.auth import get_current_account_id
from api.galleries import hash_password, PhotoResponse, AlbumResponse
from .models import SelectionShareLink, SelectionSubmission, SelectionItem
from .schemas import (
    SelectionShareLinkCreate,
    SelectionShareLinkResponse,
    SelectionSubmitRequest,
    SelectionSubmissionResponse,
    SelectionItemResponse,
    PublicSelectionPanelResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/galleries/extension/selection", tags=["gallery-selection-extension"])


async def get_current_account(account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db_session)) -> Account:
    account = await db.get(Account, uuid.UUID(account_id))
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")
    return account


@router.post("/albums/{album_id}/share-link", response_model=SelectionShareLinkResponse, summary="Generar enlace de Panel de Selección")
async def generate_selection_share_link(
    album_id: uuid.UUID,
    link_data: SelectionShareLinkCreate,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    album = await db.get(Album, album_id)
    if not album or album.account_id != current_account.id:
        raise HTTPException(status_code=404, detail="Álbum no encontrado o no autorizado.")

    token = secrets.token_urlsafe(16)
    password_hash = hash_password(link_data.password) if link_data.password else None
    expiry_date = datetime.utcnow() + timedelta(days=link_data.expiry_days) if link_data.expiry_days else None

    new_link = SelectionShareLink(
        album_id=album_id,
        token=token,
        password_hash=password_hash,
        expiry_date=expiry_date,
        allow_comments=link_data.allow_comments,
        max_selections=link_data.max_selections
    )
    db.add(new_link)
    await db.commit()
    await db.refresh(new_link)

    return SelectionShareLinkResponse(
        id=new_link.id,
        album_id=new_link.album_id,
        token=new_link.token,
        has_password=bool(new_link.password_hash),
        expiry_date=new_link.expiry_date,
        allow_comments=new_link.allow_comments,
        max_selections=new_link.max_selections,
        created_at=new_link.created_at
    )


@router.get("/albums/{album_id}/share-links", response_model=List[SelectionShareLinkResponse], summary="Listar enlaces de Panel de Selección de un álbum")
async def get_selection_share_links(
    album_id: uuid.UUID,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    album = await db.get(Album, album_id)
    if not album or album.account_id != current_account.id:
        raise HTTPException(status_code=404, detail="Álbum no encontrado o no autorizado.")

    stmt = select(SelectionShareLink).where(SelectionShareLink.album_id == album_id).order_by(SelectionShareLink.created_at.desc())
    result = await db.execute(stmt)
    links = result.scalars().all()

    return [
        SelectionShareLinkResponse(
            id=link.id,
            album_id=link.album_id,
            token=link.token,
            has_password=bool(link.password_hash),
            expiry_date=link.expiry_date,
            allow_comments=link.allow_comments,
            max_selections=link.max_selections,
            created_at=link.created_at
        )
        for link in links
    ]


@router.delete("/share-link/{token}", status_code=204, summary="Revocar enlace de Panel de Selección")
async def revoke_selection_share_link(
    token: str,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(SelectionShareLink).where(SelectionShareLink.token == token)
    result = await db.execute(stmt)
    link = result.scalars().first()

    if not link:
        raise HTTPException(status_code=404, detail="Enlace no encontrado.")

    album = await db.get(Album, link.album_id)
    if not album or album.account_id != current_account.id:
        raise HTTPException(status_code=403, detail="No autorizado.")

    await db.delete(link)
    await db.commit()
    return Response(status_code=204)


@router.post("/public/{token}", response_model=PublicSelectionPanelResponse, summary="Acceso público a Panel de Selección")
async def get_public_selection_panel(
    token: str,
    access_data: Optional[dict] = None,
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(SelectionShareLink).where(SelectionShareLink.token == token)
    result = await db.execute(stmt)
    share_link = result.scalars().first()

    if not share_link:
        raise HTTPException(status_code=404, detail="Enlace de selección no encontrado.")

    if share_link.expiry_date and share_link.expiry_date < datetime.utcnow():
        raise HTTPException(status_code=403, detail="El enlace ha expirado.")

    if share_link.password_hash:
        password = access_data.get("password") if access_data else None
        if not password or hash_password(password) != share_link.password_hash:
            raise HTTPException(status_code=401, detail="Contraseña incorrecta o requerida.")

    stmt_album = select(Album).options(selectinload(Album.photos)).where(Album.id == share_link.album_id)
    album_res = await db.execute(stmt_album)
    album = album_res.scalars().first()

    if not album:
        raise HTTPException(status_code=404, detail="Álbum no encontrado.")

    photos_stmt = select(Photo).where(Photo.album_id == album.id).order_by(Photo.order)
    photos_res = await db.execute(photos_stmt)
    photos = photos_res.scalars().all()

    photos_response = [
        PhotoResponse(
            id=p.id,
            album_id=p.album_id,
            file_path=p.file_path,
            thumbnail_path=p.thumbnail_path,
            is_favorite=p.is_favorite,
            uploaded_at=p.uploaded_at,
            order=p.order
        ) for p in photos
    ]

    album_response = AlbumResponse(
        id=album.id,
        account_id=album.account_id,
        name=album.name,
        description=album.description,
        created_at=album.created_at,
        updated_at=album.updated_at,
        cover_photo_id=album.cover_photo_id,
        photos=photos_response,
        total_photos=len(photos_response)
    )

    return PublicSelectionPanelResponse(
        album=album_response,
        allow_comments=share_link.allow_comments,
        max_selections=share_link.max_selections,
        token=token
    )


@router.post("/public/{token}/submit", status_code=201, response_model=SelectionSubmissionResponse, summary="Enviar selección de fotos")
async def submit_photo_selection(
    token: str,
    submit_data: SelectionSubmitRequest,
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(SelectionShareLink).where(SelectionShareLink.token == token)
    result = await db.execute(stmt)
    share_link = result.scalars().first()

    if not share_link:
        raise HTTPException(status_code=404, detail="Enlace de selección no encontrado.")

    if share_link.expiry_date and share_link.expiry_date < datetime.utcnow():
        raise HTTPException(status_code=403, detail="El enlace ha expirado.")

    if share_link.max_selections and len(submit_data.items) > share_link.max_selections:
        raise HTTPException(status_code=400, detail=f"Has superado el número máximo de elecciones ({share_link.max_selections}).")

    submission = SelectionSubmission(
        share_link_id=share_link.id,
        album_id=share_link.album_id,
        client_name=submit_data.client_name,
        client_email=submit_data.client_email,
        general_comment=submit_data.general_comment
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    created_items = []
    for item in submit_data.items:
        s_item = SelectionItem(
            submission_id=submission.id,
            photo_id=item.photo_id,
            comment=item.comment if share_link.allow_comments else None
        )
        db.add(s_item)
        created_items.append(s_item)

    await db.commit()

    # Load items with photo data for response
    stmt_loaded = select(SelectionSubmission).options(
        selectinload(SelectionSubmission.items).selectinload(SelectionItem.photo)
    ).where(SelectionSubmission.id == submission.id)
    res_loaded = await db.execute(stmt_loaded)
    submission_loaded = res_loaded.scalars().first()

    items_resp = []
    for it in submission_loaded.items:
        p_resp = PhotoResponse(
            id=it.photo.id,
            album_id=it.photo.album_id,
            file_path=it.photo.file_path,
            thumbnail_path=it.photo.thumbnail_path,
            is_favorite=it.photo.is_favorite,
            uploaded_at=it.photo.uploaded_at,
            order=it.photo.order
        ) if it.photo else None

        items_resp.append(SelectionItemResponse(
            id=it.id,
            photo_id=it.photo_id,
            comment=it.comment,
            photo=p_resp
        ))

    return SelectionSubmissionResponse(
        id=submission.id,
        share_link_id=submission.share_link_id,
        album_id=submission.album_id,
        client_name=submission.client_name,
        client_email=submission.client_email,
        general_comment=submission.general_comment,
        created_at=submission.created_at,
        items=items_resp
    )


@router.get("/albums/{album_id}/submissions", response_model=List[SelectionSubmissionResponse], summary="Obtener selecciones recibidas de un álbum")
async def get_album_submissions(
    album_id: uuid.UUID,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    album = await db.get(Album, album_id)
    if not album or album.account_id != current_account.id:
        raise HTTPException(status_code=404, detail="Álbum no encontrado o no autorizado.")

    stmt = select(SelectionSubmission).options(
        selectinload(SelectionSubmission.items).selectinload(SelectionItem.photo)
    ).where(SelectionSubmission.album_id == album_id).order_by(SelectionSubmission.created_at.desc())
    
    result = await db.execute(stmt)
    submissions = result.scalars().all()

    response = []
    for sub in submissions:
        items_resp = []
        for it in sub.items:
            p_resp = PhotoResponse(
                id=it.photo.id,
                album_id=it.photo.album_id,
                file_path=it.photo.file_path,
                thumbnail_path=it.photo.thumbnail_path,
                is_favorite=it.photo.is_favorite,
                uploaded_at=it.photo.uploaded_at,
                order=it.photo.order
            ) if it.photo else None

            items_resp.append(SelectionItemResponse(
                id=it.id,
                photo_id=it.photo_id,
                comment=it.comment,
                photo=p_resp
            ))

        response.append(SelectionSubmissionResponse(
            id=sub.id,
            share_link_id=sub.share_link_id,
            album_id=sub.album_id,
            client_name=sub.client_name,
            client_email=sub.client_email,
            general_comment=sub.general_comment,
            created_at=sub.created_at,
            items=items_resp
        ))

    return response


@router.delete("/submissions/{submission_id}", status_code=204, summary="Eliminar una selección recibida")
async def delete_submission(
    submission_id: uuid.UUID,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(SelectionSubmission).where(SelectionSubmission.id == submission_id)
    res = await db.execute(stmt)
    sub = res.scalars().first()

    if not sub:
        raise HTTPException(status_code=404, detail="Selección no encontrada.")

    album = await db.get(Album, sub.album_id)
    if not album or album.account_id != current_account.id:
        raise HTTPException(status_code=403, detail="No autorizado.")

    await db.delete(sub)
    await db.commit()
    return Response(status_code=204)
