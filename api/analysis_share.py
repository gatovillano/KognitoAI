"""
API endpoints for sharing analysis reports.
"""
import logging
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_db_session
from core.config import settings
from utils.security import get_current_account_id

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Pydantic Models ---

class ShareAnalysisCreateRequest(BaseModel):
    """Request model for creating a shared analysis link."""
    analysis_id: str = Field(..., description="ID of the analysis to share")
    password: Optional[str] = Field(None, min_length=4, description="Optional password to protect the link")
    expiry_days: Optional[int] = Field(None, gt=0, le=365, description="Days until the link expires (1-365)")
    allow_download: bool = Field(True, description="Allow downloading PDF from the shared link")


class ShareAnalysisResponse(BaseModel):
    """Response model for a shared analysis link."""
    id: str
    analysis_id: str
    token: str
    has_password: bool
    expiry_date: Optional[str]
    created_at: str
    allow_download: bool

    class Config:
        from_attributes = True


class ShareAnalysisAccessRequest(BaseModel):
    """Request model for accessing a protected shared analysis."""
    password: Optional[str] = None


class SharedAnalysisDetailResponse(BaseModel):
    """Response model for shared analysis details (without sensitive data)."""
    id: str
    analysis_id: str
    title: str
    type: str
    summary: str
    created_at: str
    allow_download: bool
    has_password: bool
    is_expired: bool

    class Config:
        from_attributes = True


# --- Helper Functions ---

def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


# --- API Endpoints ---

@router.post("/create", response_model=ShareAnalysisResponse, summary="Create a shared analysis link")
async def create_share_analysis_link(
    request: ShareAnalysisCreateRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create a unique shareable link for an analysis report.
    The link can be protected with a password and/or have an expiry date.
    """
    try:
        # Verify the analysis exists and belongs to the current user
        import uuid
        analysis_uuid = uuid.UUID(request.analysis_id)
        account_uuid = uuid.UUID(current_account_id)
        
        stmt = select(AnalysisTask).where(
            AnalysisTask.id == analysis_uuid,
            AnalysisTask.account_id == account_uuid
        )
        result = await db.execute(stmt)
        analysis = result.scalars().first()
        
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found or you don't have permission to share it."
            )
        
        # Check if analysis is completed
        if analysis.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only completed analyses can be shared."
            )
        
        # Generate unique token
        token = secrets.token_urlsafe(32)
        
        # Hash password if provided
        password_hash = hash_password(request.password) if request.password else None
        
        # Calculate expiry date
        expiry_date = None
        if request.expiry_days:
            expiry_date = datetime.utcnow() + timedelta(days=request.expiry_days)
        
        # Create shared link
        shared_link = SharedAnalysisLink(
            analysis_id=request.analysis_id,
            token=token,
            password_hash=password_hash,
            expiry_date=expiry_date,
            allow_download=request.allow_download
        )
        db.add(shared_link)
        await db.commit()
        await db.refresh(shared_link)
        
        return ShareAnalysisResponse(
            id=str(shared_link.id),
            analysis_id=str(shared_link.analysis_id),
            token=shared_link.token,
            has_password=bool(shared_link.password_hash),
            expiry_date=shared_link.expiry_date.isoformat() if shared_link.expiry_date else None,
            created_at=shared_link.created_at.isoformat(),
            allow_download=shared_link.allow_download
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating share analysis link: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create share link."
        )


@router.get("/list", response_model=list[ShareAnalysisResponse], summary="List shared analysis links")
async def list_share_analysis_links(
    analysis_id: str = Query(..., description="ID of the analysis"),
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    List all shared links for a specific analysis.
    """
    try:
        import uuid
        analysis_uuid = uuid.UUID(analysis_id)
        account_uuid = uuid.UUID(current_account_id)
        
        # Verify the analysis exists and belongs to the current user
        stmt = select(AnalysisTask).where(
            AnalysisTask.id == analysis_uuid,
            AnalysisTask.account_id == account_uuid
        )
        result = await db.execute(stmt)
        analysis = result.scalars().first()
        
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found or you don't have permission to access it."
            )
        
        # Get all shared links for this analysis
        stmt = select(SharedAnalysisLink).where(
            SharedAnalysisLink.analysis_id == analysis_id
        ).order_by(SharedAnalysisLink.created_at.desc())
        
        result = await db.execute(stmt)
        links = result.scalars().all()
        
        return [
            ShareAnalysisResponse(
                id=str(link.id),
                analysis_id=str(link.analysis_id),
                token=link.token,
                has_password=bool(link.password_hash),
                expiry_date=link.expiry_date.isoformat() if link.expiry_date else None,
                created_at=link.created_at.isoformat(),
                allow_download=link.allow_download
            )
            for link in links
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing share analysis links: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list share links."
        )


@router.delete("/{token}", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke a shared analysis link")
async def revoke_share_analysis_link(
    token: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Revoke (delete) a shared analysis link.
    """
    try:
        # Find the shared link
        stmt = select(SharedAnalysisLink).where(SharedAnalysisLink.token == token)
        result = await db.execute(stmt)
        shared_link = result.scalars().first()
        
        if not shared_link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shared link not found."
            )
        
        # Verify the analysis belongs to the current user
        import uuid
        analysis_uuid = uuid.UUID(shared_link.analysis_id)
        account_uuid = uuid.UUID(current_account_id)
        
        stmt = select(AnalysisTask).where(
            AnalysisTask.id == analysis_uuid,
            AnalysisTask.account_id == account_uuid
        )
        result = await db.execute(stmt)
        analysis = result.scalars().first()
        
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to revoke this link."
            )
        
        # Delete the shared link
        await db.delete(shared_link)
        await db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking share analysis link: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke share link."
        )


@router.post("/access/{token}", response_model=Dict[str, Any], summary="Access a shared analysis")
async def access_shared_analysis(
    token: str,
    request: Optional[ShareAnalysisAccessRequest] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Access a shared analysis report.
    If the link is password-protected, the password must be provided.
    Returns the analysis data if access is granted.
    """
    try:
        # Find the shared link
        stmt = select(SharedAnalysisLink).where(SharedAnalysisLink.token == token)
        result = await db.execute(stmt)
        shared_link = result.scalars().first()
        
        if not shared_link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shared link not found."
            )
        
        # Check if link has expired
        if shared_link.expiry_date and shared_link.expiry_date < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This shared link has expired."
            )
        
        # Check password if required
        if shared_link.password_hash:
            if not request or not request.password:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Password required to access this analysis.",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            if hash_password(request.password) != shared_link.password_hash:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect password."
                )
        
        # Get the analysis
        import uuid
        # shared_link.analysis_id is already a UUID from the database
        analysis_uuid = shared_link.analysis_id if isinstance(shared_link.analysis_id, uuid.UUID) else uuid.UUID(shared_link.analysis_id)
        
        stmt = select(AnalysisTask).where(AnalysisTask.id == analysis_uuid)
        result = await db.execute(stmt)
        analysis = result.scalars().first()
        
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found."
            )
        
        if analysis.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This analysis is not yet completed."
            )
        
        # Return the analysis data
        return {
            "analysis": {
                "id": str(analysis.id),
                "title": analysis.result_payload.get("title", "Análisis") if analysis.result_payload else "Análisis",
                "type": analysis.analysis_type,
                "summary": analysis.result_payload.get("summary", "") if analysis.result_payload else "",
                "result_payload": analysis.result_payload,
                "full_data": {
                    # For gap_development, check if we have report in result_payload
                    "report": analysis.result_payload.get("report") if analysis.analysis_type == "gap_development" and analysis.result_payload else None
                },
                "created_at": analysis.created_at.isoformat(),
                "file_name": analysis.file_name
            },
            "share_link": {
                "allow_download": shared_link.allow_download,
                "expiry_date": shared_link.expiry_date.isoformat() if shared_link.expiry_date else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accessing shared analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to access shared analysis."
        )


@router.get("/info/{token}", response_model=SharedAnalysisDetailResponse, summary="Get shared analysis info (without full data)")
async def get_shared_analysis_info(
    token: str,
    request: Optional[ShareAnalysisAccessRequest] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get basic info about a shared analysis (title, type, etc.).
    Used to show a preview before requiring password.
    """
    try:
        # Find the shared link
        stmt = select(SharedAnalysisLink).where(SharedAnalysisLink.token == token)
        result = await db.execute(stmt)
        shared_link = result.scalars().first()
        
        if not shared_link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shared link not found."
            )
        
        # Check if link has expired
        is_expired = False
        if shared_link.expiry_date and shared_link.expiry_date < datetime.utcnow():
            is_expired = True
        
        # Check password if required
        if shared_link.password_hash and not is_expired:
            if not request or not request.password:
                # Return info indicating password is required
                return SharedAnalysisDetailResponse(
                    id=str(shared_link.id),
                    analysis_id=str(shared_link.analysis_id),
                    title="",  # Don't reveal title without password
                    type="",
                    summary="",
                    created_at="",
                    allow_download=shared_link.allow_download,
                    has_password=True,
                    is_expired=is_expired
                )
            
            if hash_password(request.password) != shared_link.password_hash:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect password."
                )
        
        # Get the analysis
        import uuid
        # shared_link.analysis_id is already a UUID from the database
        analysis_uuid = shared_link.analysis_id if isinstance(shared_link.analysis_id, uuid.UUID) else uuid.UUID(shared_link.analysis_id)
        
        stmt = select(AnalysisTask).where(AnalysisTask.id == analysis_uuid)
        result = await db.execute(stmt)
        analysis = result.scalars().first()
        
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found."
            )
        
        return SharedAnalysisDetailResponse(
            id=str(shared_link.id),
            analysis_id=str(shared_link.analysis_id),
            title=analysis.result_payload.get("title", "Análisis") if analysis.result_payload else "Análisis",
            type=analysis.analysis_type,
            summary=analysis.result_payload.get("summary", "") if analysis.result_payload else "",
            created_at=analysis.created_at.isoformat(),
            allow_download=shared_link.allow_download,
            has_password=bool(shared_link.password_hash),
            is_expired=is_expired
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting shared analysis info: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get analysis info."
        )
