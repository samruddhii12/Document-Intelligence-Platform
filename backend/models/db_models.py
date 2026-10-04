import uuid
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from backend.database import Base



class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        nullable=False,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    workspaces: Mapped[list["Workspace"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    documents: Mapped[list["Document"]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )

    chat_sessions: Mapped[list["ChatSession"]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )

    # ------------------------------------------------------------------
    # Ownership (Phase 3.2)
    #
    # A workspace belongs to EITHER a registered user OR a guest:
    #
    #   registered workspace: user_id = <uuid>, guest_id = NULL
    #   guest workspace:      user_id = NULL,   guest_id = <token>
    #
    # Both columns are nullable so guests can use the app without an
    # account. chk_workspaces_single_owner enforces that a NEW workspace
    # has exactly one owner. In the database this constraint is added
    # NOT VALID so workspaces created before Phase 3 (which have no
    # owner) are preserved - see migrations/001_workspace_ownership.sql
    # ------------------------------------------------------------------
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    guest_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    user: Mapped[Optional["User"]] = relationship(
        back_populates="workspaces",
    )

    __table_args__ = (
        CheckConstraint(
            "(user_id IS NOT NULL) <> (guest_id IS NOT NULL)",
            name="chk_workspaces_single_owner",
        ),
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    file_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    storage_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="uploaded",
        server_default="uploaded",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    workspace: Mapped["Workspace"] = relationship(
        back_populates="documents",
    )

    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "file_type IN ('pdf', 'docx')",
            name="chk_documents_file_type",
        ),
        CheckConstraint(
            "status IN ('uploaded', 'processing', 'indexed', 'failed')",
            name="chk_documents_status",
        ),
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    section_title: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(768),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    document: Mapped["Document"] = relationship(
        back_populates="chunks",
    )

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_chunks_document_index",
        ),
        CheckConstraint(
            "chunk_index >= 0",
            name="chk_chunks_chunk_index",
        ),
        CheckConstraint(
            "page_number IS NULL OR page_number > 0",
            name="chk_chunks_page_number",
        ),
    )


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    workspace: Mapped["Workspace"] = relationship(
        back_populates="chat_sessions",
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="chat_session",
        cascade="all, delete-orphan",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    chat_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    sources: Mapped[list[dict] | None] = mapped_column(
    JSONB,
    nullable=True,
)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    chat_session: Mapped["ChatSession"] = relationship(
        back_populates="messages",
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant', 'system')",
            name="chk_messages_role",
        ),
    )