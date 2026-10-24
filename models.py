from __future__ import annotations
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, inspect, text
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
    messages: Mapped[list[Message]] = relationship(back_populates="chat")

class Message(Base):
    __tablename__ = "messages"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    chat_id : Mapped[int] = mapped_column(Integer, ForeignKey("chats.id"))
    role : Mapped[str] = mapped_column(String)  # 'user', 'ai', or 'error'
    content : Mapped[str] = mapped_column(String)
    sources : Mapped[str] = mapped_column(String, nullable=True)
    created_at : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationship to the Chat model
    chat: Mapped[Chat] = relationship(back_populates="messages")

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

# --- ENABLE ROW LEVEL SECURITY (RLS) ON POSTGRES ---
if not DATABASE_URL.startswith("sqlite"):
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE users ENABLE ROW LEVEL SECURITY;"))
        conn.execute(text("ALTER TABLE chats ENABLE ROW LEVEL SECURITY;"))
        conn.execute(text("ALTER TABLE messages ENABLE ROW LEVEL SECURITY;"))
        conn.commit()
