"""
API endpoints for sharing conversation threads publicly.
"""
import logging
import secrets
import hashlib
import uuid
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

import json
from fastapi import APIRouter, HTTPException, Depends, Query, Body, BackgroundTasks, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_db_session
from core.database import ChatThread, SharedConversationLink
from core.config import settings
from utils.security import get_current_account_id
from utils.postgres_chat_history import get_postgres_history_connection_url
from langchain_community.chat_message_histories import PostgresChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from .chat import Message, PaginatedChatMessagesResponse, Source, create_and_run_agent_streaming

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Pydantic Models ---

class ShareChatCreateRequest(BaseModel):
    """Request to create a shared chat link."""
    thread_id: str = Field(..., description="ID of the chat thread to share")
    password: Optional[str] = Field(None, min_length=4, description="Optional password to protect the link")
    expiry_days: Optional[int] = Field(None, gt=0, le=365, description="Days until link expires (1-365)")
    allow_reply: bool = Field(False, description="Allow public replies to the shared thread")


class ShareChatResponse(BaseModel):
    """Response with shared link details."""
    id: str
    thread_id: str
    token: str
    has_password: bool
    expiry_date: Optional[str] = None
    created_at: str
    allow_reply: bool
    share_url: str

    class Config:
        from_attributes = True


class ShareChatMessagesRequest(BaseModel):
    """Request to get messages from a shared chat."""
    password: Optional[str] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)


class SharedThreadPublic(BaseModel):
    id: str
    title: str
    created_at: Optional[str] = None


class ShareMetaPublic(BaseModel):
    allow_reply: bool
    has_password: bool
    expiry_date: Optional[str] = None
    is_expired: bool


class SharedChatInfoResponse(BaseModel):
    thread: SharedThreadPublic
    share_meta: ShareMetaPublic


# --- Helper Functions ---

def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


# --- API Endpoints ---

@router.post("/create", response_model=ShareChatResponse, summary="Create a shared chat link")
async def create_share_chat_link(
    request: ShareChatCreateRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a unique shareable link for a chat thread."""
    try:
        # Verify the thread exists and belongs to the current user
        thread_uuid = uuid.UUID(request.thread_id)
        account_uuid = uuid.UUID(current_account_id)

        stmt = select(ChatThread).where(
            ChatThread.id == thread_uuid,
            ChatThread.account_id == account_uuid
        )
        result = await db.execute(stmt)
        thread = result.scalars().first()
        if not thread:
            raise HTTPException(status_code=404, detail="Chat thread not found.")

        # Generate a unique token
        token = secrets.token_urlsafe(32)
        password_hash = hash_password(request.password) if request.password else None
        expiry_date = datetime.now(timezone.utc) + timedelta(days=request.expiry_days) if request.expiry_days else None

        shared_link = SharedConversationLink(
            thread_id=thread_uuid,
            token=token,
            password_hash=password_hash,
            expiry_date=expiry_date,
            allow_reply=request.allow_reply
        )
        db.add(shared_link)
        await db.commit()
        await db.refresh(shared_link)

        share_url = f"/share/chat/{token}"

        return ShareChatResponse(
            id=str(shared_link.id),
            thread_id=str(shared_link.thread_id),
            token=shared_link.token,
            has_password=bool(shared_link.password_hash),
            expiry_date=shared_link.expiry_date.isoformat() if shared_link.expiry_date else None,
            created_at=shared_link.created_at.isoformat(),
            allow_reply=shared_link.allow_reply,
            share_url=share_url
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid thread_id format.")
    except Exception as e:
        logger.error(f"Error creating share link for thread {request.thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create share link.")


@router.get("/list", response_model=List[ShareChatResponse], summary="List share links for a thread")
async def list_share_chat_links(
    thread_id: str = Query(..., description="ID of the thread"),
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """List all share links for a specific chat thread."""
    try:
        thread_uuid = uuid.UUID(thread_id)
        account_uuid = uuid.UUID(current_account_id)

        # Verify ownership of thread
        stmt = select(ChatThread).where(
            ChatThread.id == thread_uuid,
            ChatThread.account_id == account_uuid
        )
        result = await db.execute(stmt)
        thread = result.scalars().first()
        if not thread:
            raise HTTPException(status_code=404, detail="Chat thread not found.")

        # Fetch share links
        stmt = select(SharedConversationLink).where(
            SharedConversationLink.thread_id == thread_uuid
        ).order_by(SharedConversationLink.created_at.desc())
        result = await db.execute(stmt)
        links = result.scalars().all()

        response_list = []
        for link in links:
            response_list.append(ShareChatResponse(
                id=str(link.id),
                thread_id=str(link.thread_id),
                token=link.token,
                has_password=bool(link.password_hash),
                expiry_date=link.expiry_date.isoformat() if link.expiry_date else None,
                created_at=link.created_at.isoformat(),
                allow_reply=link.allow_reply,
                share_url=f"/share/chat/{link.token}"
            ))
        return response_list
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid thread_id format.")
    except Exception as e:
        logger.error(f"Error listing share links for thread {thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list share links.")


@router.delete("/{token}", status_code=204, summary="Revoke a shared chat link")
async def revoke_share_chat_link(
    token: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Revoke a shared chat link."""
    try:
        # Find the share link
        stmt = select(SharedConversationLink).where(SharedConversationLink.token == token)
        result = await db.execute(stmt)
        shared_link = result.scalars().first()
        if not shared_link:
            raise HTTPException(status_code=404, detail="Share link not found.")

        # Verify ownership of the associated thread
        stmt = select(ChatThread).where(
            ChatThread.id == shared_link.thread_id,
            ChatThread.account_id == uuid.UUID(current_account_id)
        )
        result = await db.execute(stmt)
        thread = result.scalars().first()
        if not thread:
            raise HTTPException(status_code=403, detail="Not authorized to revoke this link.")

        await db.delete(shared_link)
        await db.commit()
        return None
    except Exception as e:
        logger.error(f"Error revoking share link {token}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to revoke share link.")


@router.get("/{token}/info", response_model=SharedChatInfoResponse, summary="Get public info about a shared chat")
async def get_shared_chat_info(
    token: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get metadata about a shared chat thread (does not require password)."""
    try:
        stmt = select(SharedConversationLink).where(SharedConversationLink.token == token)
        result = await db.execute(stmt)
        shared_link = result.scalars().first()
        if not shared_link:
            raise HTTPException(status_code=404, detail="Share link not found.")

        # Check expiry
        now = datetime.now(timezone.utc)
        is_expired = bool(shared_link.expiry_date and shared_link.expiry_date < now)
        if is_expired:
            raise HTTPException(status_code=403, detail="Share link has expired.")

        # Get the thread
        thread = await db.get(ChatThread, shared_link.thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Chat thread not found.")

        thread_data = SharedThreadPublic(
            id=str(thread.id),
            title=thread.title,
            created_at=thread.created_at.isoformat() if thread.created_at else None
        )

        share_meta = ShareMetaPublic(
            allow_reply=shared_link.allow_reply,
            has_password=bool(shared_link.password_hash),
            expiry_date=shared_link.expiry_date.isoformat() if shared_link.expiry_date else None,
            is_expired=is_expired
        )

        return SharedChatInfoResponse(thread=thread_data, share_meta=share_meta)
    except Exception as e:
        logger.error(f"Error getting shared chat info for token {token}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get share info.")


@router.post("/{token}/messages", response_model=PaginatedChatMessagesResponse, summary="Get messages from a shared chat")
async def get_shared_chat_messages(
    token: str,
    request: ShareChatMessagesRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Get paginated messages from a shared chat thread. Password required if the link is protected."""
    try:
        # Validate token and get share link
        stmt = select(SharedConversationLink).where(SharedConversationLink.token == token)
        result = await db.execute(stmt)
        shared_link = result.scalars().first()
        if not shared_link:
            raise HTTPException(status_code=404, detail="Share link not found.")

        # Check expiry
        now = datetime.now(timezone.utc)
        if shared_link.expiry_date and shared_link.expiry_date < now:
            raise HTTPException(status_code=403, detail="Share link has expired.")

        # Verify password if required
        if shared_link.password_hash:
            if not request.password:
                raise HTTPException(status_code=401, detail="Password required.")
            if hash_password(request.password) != shared_link.password_hash:
                raise HTTPException(status_code=401, detail="Incorrect password.")

        # Get the thread
        thread = await db.get(ChatThread, shared_link.thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Chat thread not found.")

        # Fetch messages from LangChain history
        db_sync_url = get_postgres_history_connection_url(settings.database_url)
        chat_message_history = None
        for attempt in range(3):
            try:
                chat_message_history = PostgresChatMessageHistory(
                    connection_string=db_sync_url,
                    session_id=str(shared_link.thread_id),
                    table_name="langchain_chat_history",
                )
                all_messages = await chat_message_history.aget_messages()
                break
            except Exception as e:
                logger.warning(f"⚠️ Attempt {attempt+1} failed to fetch messages for thread {shared_link.thread_id}: {e}")
                if attempt == 2:
                    logger.error(f"❌ Failed to fetch messages after retries: {e}")
                    raise HTTPException(status_code=500, detail="Error retrieving chat history.")
                await asyncio.sleep(1)

        # Format messages (filter summaries, etc.)
        real_messages = []
        for msg in all_messages:
            if not (hasattr(msg, 'additional_kwargs') and msg.additional_kwargs.get("role") == "summary"):
                text_content = ""
                image_contents = []

                if isinstance(msg.content, list):
                    for part in msg.content:
                        if isinstance(part, dict):
                            if part.get("type") == "text":
                                text_content += part.get("text", "")
                            elif part.get("type") == "image_url":
                                image_url_data = part.get("image_url")
                                if isinstance(image_url_data, dict):
                                    image_contents.append(image_url_data.get("url"))
                        else:
                            text_content += str(part)
                else:
                    text_content = str(msg.content)

                message_sources = msg.additional_kwargs.get("sources", [])
                reasoning = msg.additional_kwargs.get("reasoning") or msg.additional_kwargs.get("think")

                real_messages.append(Message(
                    text=text_content,
                    sender="user" if isinstance(msg, HumanMessage) else "ai",
                    created_at=msg.additional_kwargs.get("created_at", datetime.now(timezone.utc)),
                    image_base64=image_contents[0] if image_contents else None,
                    images_base64=image_contents if len(image_contents) > 1 else None,
                    sources=message_sources,
                    reasoning=reasoning
                ))

        # Sort by created_at ascending
        real_messages.sort(key=lambda m: m.created_at)

        total = len(real_messages)
        paginated = real_messages[request.skip : request.skip + request.limit]

        return PaginatedChatMessagesResponse(total=total, messages=paginated)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request parameters.")
    except Exception as e:
        logger.error(f"Error getting shared messages for token {token}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get messages.")


class ShareChatReplyRequest(BaseModel):
    """Request to send a reply to a shared chat thread."""
    message: str = Field(..., min_length=1, description="The reply message")
    password: Optional[str] = None


class ShareChatReplyResponse(BaseModel):
    """Response after sending a reply."""
    task_id: str
    thread_id: str
    status: str = "processing"


# In-memory task status tracker for shared replies
_shared_reply_tasks: Dict[str, Dict[str, Any]] = {}


@router.post("/{token}/reply", response_model=ShareChatReplyResponse, summary="Send a reply to a shared chat thread")
async def reply_to_shared_chat(
    token: str,
    request: ShareChatReplyRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """Send a reply to a shared conversation thread. Requires allow_reply=True on the share link."""
    try:
        # Validate token
        stmt = select(SharedConversationLink).where(SharedConversationLink.token == token)
        result = await db.execute(stmt)
        shared_link = result.scalars().first()
        if not shared_link:
            raise HTTPException(status_code=404, detail="Share link not found.")

        # Check expiry
        now = datetime.now(timezone.utc)
        if shared_link.expiry_date and shared_link.expiry_date < now:
            raise HTTPException(status_code=403, detail="Share link has expired.")

        # Check allow_reply
        if not shared_link.allow_reply:
            raise HTTPException(status_code=403, detail="Replies are not allowed for this shared link.")

        # Verify password if required
        if shared_link.password_hash:
            if not request.password:
                raise HTTPException(status_code=401, detail="Password required.")
            if hash_password(request.password) != shared_link.password_hash:
                raise HTTPException(status_code=401, detail="Incorrect password.")

        # Get the thread to find the owner's account_id
        thread = await db.get(ChatThread, shared_link.thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Chat thread not found.")

        account_id = str(thread.account_id)
        thread_id = str(thread.id)
        task_id = str(uuid.uuid4())

        # Track the task
        _shared_reply_tasks[token] = {
            "task_id": task_id,
            "thread_id": thread_id,
            "status": "processing",
            "created_at": now.isoformat(),
        }

        # Run the agent as a background task
        background_tasks.add_task(
            _run_shared_reply,
            account_id=account_id,
            thread_id=thread_id,
            task_id=task_id,
            user_message=request.message,
            token=token,
        )

        logger.info(f"Shared reply initiated for thread {thread_id} via token {token[:8]}... Task: {task_id}")

        return ShareChatReplyResponse(
            task_id=task_id,
            thread_id=thread_id,
            status="processing"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing reply for token {token}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process reply.")


async def _run_shared_reply(
    account_id: str,
    thread_id: str,
    task_id: str,
    user_message: str,
    token: str,
):
    """Run the agent for a shared reply and update task status."""
    try:
        await create_and_run_agent_streaming(
            account_id=account_id,
            thread_id=thread_id,
            task_id=task_id,
            telegram_id=None,
            user_message=user_message,
        )
        # Mark as complete
        if token in _shared_reply_tasks:
            _shared_reply_tasks[token]["status"] = "completed"
    except Exception as e:
        logger.error(f"Error in shared reply task {task_id}: {e}", exc_info=True)
        if token in _shared_reply_tasks:
            _shared_reply_tasks[token]["status"] = "error"
            _shared_reply_tasks[token]["error"] = str(e)


@router.get("/{token}/reply-status", summary="Check the status of a reply task")
async def get_reply_status(token: str):
    """Check if a reply task has completed processing."""
    task_info = _shared_reply_tasks.get(token)
    if not task_info:
        raise HTTPException(status_code=404, detail="No reply task found for this token.")
    return task_info
