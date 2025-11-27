import uuid
import json
from typing import List, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, Column, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declarative_base

# Importaciones del proyecto
from core.database import SessionLocal, ChatThread
from core.dependencies import get_db_session

# --- Base y Modelo ORM para LangChain History ---
# Se necesita una Base local porque la tabla de LangChain no está en nuestro Base de core.database
Base = declarative_base()

class LangchainChatMessage(Base):
    __tablename__ = 'langchain_chat_history'
    # Esto permite que SQLAlchemy use la definición de la tabla aunque ya exista
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String, nullable=False)
    message = Column(JSONB, nullable=False)

# --- Dependencia de FastAPI ---
# get_db eliminado en favor de core.dependencies.get_db_session

router = APIRouter()

# --- Esquemas Pydantic para la Respuesta ---
class SearchChatMessage(BaseModel):
    text: str
    sender: str
    created_at: str
    thread_id: str
    thread_title: str

class MessageSearchResult(BaseModel):
    message: SearchChatMessage
    context: str

class SearchChatThread(BaseModel):
    id: str
    title: str
    created_at: str

class SearchResponse(BaseModel):
    threads: List[SearchChatThread]
    messages: List[MessageSearchResult]

@router.get("/search/all", response_model=SearchResponse)
async def search_all(query: str = Query(..., min_length=3), db: AsyncSession = Depends(get_db_session)):
    """
    Busca en todos los hilos de chat y mensajes.
    """
    try:
        # 1. Buscar en los títulos de los hilos de chat
        threads_query = select(ChatThread).filter(ChatThread.title.ilike(f"%{query}%"))
        threads_result = await db.execute(threads_query)
        threads = threads_result.scalars().all()

        # 2. Buscar en el contenido de los mensajes (en el campo JSONB)
        messages_query = select(LangchainChatMessage).filter(
            LangchainChatMessage.message['data']['content'].astext.ilike(f"%{query}%")
        ).limit(50)
        messages_result = await db.execute(messages_query)
        messages_results = messages_result.scalars().all()

        # 3. Formatear los resultados de los hilos
        formatted_threads = [
            SearchChatThread(
                id=str(t.id),
                title=str(t.title),
                created_at=t.created_at.isoformat()
            ) for t in threads
        ]

        # 4. Formatear los resultados de los mensajes
        formatted_messages = []
        for msg in messages_results:
            thread_id_str = str(msg.session_id)
            try:
                thread_uuid = uuid.UUID(thread_id_str)
                thread = await db.get(ChatThread, thread_uuid)
                if thread:
                    message_data = msg.message.get('data', {})
                    content = message_data.get('content', '')
                    # Asegurarse de que el contenido sea un string
                    if not isinstance(content, str):
                        content = json.dumps(content)
                    
                    sender = 'user' if message_data.get('type') == 'human' else 'ai'

                    formatted_messages.append(
                        MessageSearchResult(
                            message=SearchChatMessage(
                                text=content,
                                sender=sender,
                                created_at="", # El timestamp no está fácilmente disponible aquí
                                thread_id=thread_id_str,
                                thread_title=str(thread.title),
                            ),
                            context=content,
                        )
                    )
            except (ValueError, TypeError):
                # Ignorar si el session_id no es un UUID válido
                continue

        return SearchResponse(threads=formatted_threads, messages=formatted_messages)
    except Exception as e:
        print(f"Error durante la búsqueda: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor durante la búsqueda.")