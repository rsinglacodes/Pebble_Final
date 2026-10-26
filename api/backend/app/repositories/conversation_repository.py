"""Conversation and Message repository for database access."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Union
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from backend.app.models.conversation import Conversation, Message


class ConversationRepository:
    """Repository handling database operations for conversations and chat messages."""

    @staticmethod
    def _to_uuid(val: Union[uuid.UUID, str]) -> uuid.UUID:
        if isinstance(val, str):
            return uuid.UUID(val)
        return val

    @classmethod
    def create(
        cls,
        db: Session,
        user_id: Union[uuid.UUID, str],
        title: str = "New conversation",
    ) -> Conversation:
        """Create and persist a new conversation for a user."""
        u_id = cls._to_uuid(user_id)
        conv = Conversation(
            user_id=u_id,
            title=title.strip() if title else "New conversation",
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        return conv

    @classmethod
    def list_by_user(
        cls,
        db: Session,
        user_id: Union[uuid.UUID, str],
        limit: int = 50,
        offset: int = 0,
    ) -> List[Conversation]:
        """List conversations belonging to user, newest updated first, paginated."""
        u_id = cls._to_uuid(user_id)
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == u_id)
            .order_by(Conversation.updated_at.desc(), Conversation.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(db.scalars(stmt).all())

    @classmethod
    def get_by_id(
        cls,
        db: Session,
        conversation_id: Union[uuid.UUID, str],
        user_id: Union[uuid.UUID, str],
    ) -> Optional[Conversation]:
        """Fetch conversation by ID with loaded messages, ensuring user ownership."""
        c_id = cls._to_uuid(conversation_id)
        u_id = cls._to_uuid(user_id)
        stmt = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == c_id, Conversation.user_id == u_id)
        )
        conv = db.scalars(stmt).first()
        if conv and conv.messages:
            conv.messages.sort(key=lambda m: m.created_at)
        return conv

    @classmethod
    def add_message(
        cls,
        db: Session,
        conversation_id: Union[uuid.UUID, str],
        user_id: Union[uuid.UUID, str],
        role: str,
        content: str,
        mode: Optional[str] = None,
        meta: Optional[dict] = None,
    ) -> Optional[Message]:
        """Add a message to a conversation owned by the user, updating title and timestamps."""
        conv = cls.get_by_id(db, conversation_id, user_id)
        if not conv:
            return None

        # Auto-title: if title is "New conversation", set it from the first user message (max 40 chars)
        if conv.title == "New conversation" and role.lower() == "user":
            cleaned = content.strip().replace("\r\n", " ").replace("\n", " ")
            if len(cleaned) > 40:
                cleaned = cleaned[:40].rstrip()
            if cleaned:
                conv.title = cleaned

        msg = Message(
            conversation_id=conv.id,
            role=role,
            content=content,
            mode=mode,
            meta=meta,
        )
        conv.updated_at = datetime.now(timezone.utc)
        db.add(msg)
        db.add(conv)
        db.commit()
        db.refresh(msg)
        return msg

    @classmethod
    def update_title(
        cls,
        db: Session,
        conversation_id: Union[uuid.UUID, str],
        user_id: Union[uuid.UUID, str],
        title: str,
    ) -> Optional[Conversation]:
        """Update/rename a conversation title, ensuring ownership."""
        conv = cls.get_by_id(db, conversation_id, user_id)
        if not conv:
            return None

        conv.title = title.strip()
        conv.updated_at = datetime.now(timezone.utc)
        db.add(conv)
        db.commit()
        db.refresh(conv)
        return conv

    @classmethod
    def rename(
        cls,
        db: Session,
        conversation_id: Union[uuid.UUID, str],
        user_id: Union[uuid.UUID, str],
        title: str,
    ) -> Optional[Conversation]:
        """Alias for update_title."""
        return cls.update_title(db, conversation_id, user_id, title)

    @classmethod
    def delete(
        cls,
        db: Session,
        conversation_id: Union[uuid.UUID, str],
        user_id: Union[uuid.UUID, str],
    ) -> bool:
        """Delete conversation and cascade delete messages, ensuring user ownership."""
        conv = cls.get_by_id(db, conversation_id, user_id)
        if not conv:
            return False

        db.delete(conv)
        db.commit()
        return True

    @classmethod
    def update_message_meta(
        cls,
        db: Session,
        conversation_id: Union[uuid.UUID, str],
        message_id: Union[uuid.UUID, str],
        user_id: Union[uuid.UUID, str],
        meta: dict,
    ) -> Optional[Message]:
        """Update or merge metadata on a specific message owned by the user."""
        conv = cls.get_by_id(db, conversation_id, user_id)
        if not conv:
            return None

        m_id = cls._to_uuid(message_id)
        stmt = select(Message).where(Message.id == m_id, Message.conversation_id == conv.id)
        msg = db.scalars(stmt).first()
        if not msg:
            return None

        existing_meta = dict(msg.meta) if msg.meta else {}
        existing_meta.update(meta)
        msg.meta = existing_meta
        conv.updated_at = datetime.now(timezone.utc)
        db.add(msg)
        db.add(conv)
        db.commit()
        db.refresh(msg)
        return msg
