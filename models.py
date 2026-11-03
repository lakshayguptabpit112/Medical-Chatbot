from __future__ import annotations
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON, inspect, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base, engine, DATABASE_URL

class User(Base):
    __tablename__ = "users"
    
    id : Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username : Mapped[str] = mapped_column(String, unique=True, index=True)
    email : Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password : Mapped[str | None] = mapped_column(String, nullable=True)
    google_sub : Mapped[str | None] = mapped_column(String, unique=True, nullable=True, index=True)
    picture_url : Mapped[str | None] = mapped_column(String, nullable=True)
    created_at : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationship to the Document model
    chats: Mapped[list[Chat]] = relationship(back_populates="owner")

class Chat(Base):
    __tablename__ = "chats"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id : Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title : Mapped[str] = mapped_column(String)
    is_generating : Mapped[bool] = mapped_column(Boolean, default=False)
    created_at : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationship to the User model
    owner: Mapped[User] = relationship(back_populates="chats")
    messages: Mapped[list[Message]] = relationship(back_populates="chat", cascade="all, delete-orphan")
    documents: Mapped[list[ChatDocument]] = relationship(back_populates="chat", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    chat_id : Mapped[int] = mapped_column(Integer, ForeignKey("chats.id"), index=True)
    role : Mapped[str] = mapped_column(String)  # 'user', 'ai', or 'error'
    content : Mapped[str] = mapped_column(String)
    sources : Mapped[str] = mapped_column(String, nullable=True)
    translations : Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    file_url : Mapped[str | None] = mapped_column(String, nullable=True)
    thumbnail_url : Mapped[str | None] = mapped_column(String, nullable=True)
    file_name : Mapped[str | None] = mapped_column(String, nullable=True)
    file_type : Mapped[str | None] = mapped_column(String, nullable=True)  # 'image' or 'pdf'
    draft_content : Mapped[str | None] = mapped_column(String, nullable=True)  # Preserves initial unrefined consultation
    created_at : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationship to the Chat model
    chat: Mapped[Chat] = relationship(back_populates="messages")

class ChatDocument(Base):
    __tablename__ = "chat_documents"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    chat_id: Mapped[int] = mapped_column(Integer, ForeignKey("chats.id"), index=True)
    doc_no: Mapped[int] = mapped_column(Integer, index=True)
    doc_type: Mapped[str] = mapped_column(String, default="medical_document")
    raw_visual_transcript: Mapped[str] = mapped_column(String)
    file_url: Mapped[str | None] = mapped_column(String, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String, nullable=True)
    file_name: Mapped[str | None] = mapped_column(String, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String, nullable=True)
    document_date: Mapped[str | None] = mapped_column(String, nullable=True)
    issuer: Mapped[str | None] = mapped_column(String, nullable=True)
    summary: Mapped[str | None] = mapped_column(String, nullable=True)
    perception_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationship to the Chat model
    chat: Mapped[Chat] = relationship(back_populates="documents")

# --- CREATE THE TABLES ---
Base.metadata.create_all(bind=engine)

# --- MIGRATIONS for existing databases ---
inspector = inspect(engine)
if inspector.has_table('chats'):
    chat_columns = [c['name'] for c in inspector.get_columns('chats')]
    if 'is_generating' not in chat_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE chats ADD COLUMN is_generating BOOLEAN DEFAULT false"))
            conn.commit()

if inspector.has_table('users'):
    user_columns = [c['name'] for c in inspector.get_columns('users')]
    if 'google_sub' not in user_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN google_sub VARCHAR"))
            conn.commit()

    if 'picture_url' not in user_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN picture_url VARCHAR"))
            conn.commit()

if inspector.has_table('messages'):
    msg_columns = [c['name'] for c in inspector.get_columns('messages')]
    with engine.connect() as conn:
        if 'translations' not in msg_columns:
            col_type = "JSONB" if not DATABASE_URL.startswith("sqlite") else "JSON"
            conn.execute(text(f"ALTER TABLE messages ADD COLUMN translations {col_type} DEFAULT '{{}}'::jsonb" if not DATABASE_URL.startswith("sqlite") else f"ALTER TABLE messages ADD COLUMN translations JSON DEFAULT '{{}}'"))
        if 'file_url' not in msg_columns:
            conn.execute(text("ALTER TABLE messages ADD COLUMN file_url VARCHAR"))
        if 'thumbnail_url' not in msg_columns:
            conn.execute(text("ALTER TABLE messages ADD COLUMN thumbnail_url VARCHAR"))
        if 'file_name' not in msg_columns:
            conn.execute(text("ALTER TABLE messages ADD COLUMN file_name VARCHAR"))
        if 'file_type' not in msg_columns:
            conn.execute(text("ALTER TABLE messages ADD COLUMN file_type VARCHAR"))
        if 'draft_content' not in msg_columns:
            conn.execute(text("ALTER TABLE messages ADD COLUMN draft_content TEXT"))
        conn.commit()

if inspector.has_table('chat_documents'):
    doc_columns = [c['name'] for c in inspector.get_columns('chat_documents')]
    with engine.connect() as conn:
        if 'file_url' not in doc_columns:
            conn.execute(text("ALTER TABLE chat_documents ADD COLUMN file_url VARCHAR"))
        if 'thumbnail_url' not in doc_columns:
            conn.execute(text("ALTER TABLE chat_documents ADD COLUMN thumbnail_url VARCHAR"))
        if 'file_name' not in doc_columns:
            conn.execute(text("ALTER TABLE chat_documents ADD COLUMN file_name VARCHAR"))
        if 'mime_type' not in doc_columns:
            conn.execute(text("ALTER TABLE chat_documents ADD COLUMN mime_type VARCHAR"))
        if 'document_date' not in doc_columns:
            conn.execute(text("ALTER TABLE chat_documents ADD COLUMN document_date VARCHAR"))
        if 'issuer' not in doc_columns:
            conn.execute(text("ALTER TABLE chat_documents ADD COLUMN issuer VARCHAR"))
        if 'summary' not in doc_columns:
            conn.execute(text("ALTER TABLE chat_documents ADD COLUMN summary VARCHAR"))
        if 'perception_json' not in doc_columns:
            col_type = "JSONB" if not DATABASE_URL.startswith("sqlite") else "JSON"
            conn.execute(text(f"ALTER TABLE chat_documents ADD COLUMN perception_json {col_type}"))
        conn.commit()

# --- ENABLE ROW LEVEL SECURITY (RLS) ON POSTGRES ---
if not DATABASE_URL.startswith("sqlite"):
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE users ENABLE ROW LEVEL SECURITY;"))
        conn.execute(text("ALTER TABLE chats ENABLE ROW LEVEL SECURITY;"))
        conn.execute(text("ALTER TABLE messages ENABLE ROW LEVEL SECURITY;"))
        conn.execute(text("ALTER TABLE chat_documents ENABLE ROW LEVEL SECURITY;"))
        conn.commit()
