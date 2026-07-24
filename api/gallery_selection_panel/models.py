import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.database import Base

class SelectionShareLink(Base):
    __tablename__ = 'selection_share_links'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    album_id = Column(UUID(as_uuid=True), ForeignKey('albums.id', ondelete='CASCADE'), nullable=False, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    allow_comments = Column(Boolean, default=True, nullable=False)
    max_selections = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    album = relationship("Album")
    submissions = relationship("SelectionSubmission", back_populates="share_link", cascade="all, delete-orphan")


class SelectionSubmission(Base):
    __tablename__ = 'selection_submissions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    share_link_id = Column(UUID(as_uuid=True), ForeignKey('selection_share_links.id', ondelete='CASCADE'), nullable=False, index=True)
    album_id = Column(UUID(as_uuid=True), ForeignKey('albums.id', ondelete='CASCADE'), nullable=False, index=True)
    client_name = Column(String(255), nullable=False)
    client_email = Column(String(255), nullable=True)
    general_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    share_link = relationship("SelectionShareLink", back_populates="submissions")
    album = relationship("Album")
    items = relationship("SelectionItem", back_populates="submission", cascade="all, delete-orphan")


class SelectionItem(Base):
    __tablename__ = 'selection_items'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(UUID(as_uuid=True), ForeignKey('selection_submissions.id', ondelete='CASCADE'), nullable=False, index=True)
    photo_id = Column(UUID(as_uuid=True), ForeignKey('photos.id', ondelete='CASCADE'), nullable=False, index=True)
    comment = Column(Text, nullable=True)

    submission = relationship("SelectionSubmission", back_populates="items")
    photo = relationship("Photo")
