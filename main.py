# --- Standard Library Imports ---

import json
import os
import uuid
import warnings
from datetime import datetime, timedelta, timezone

warnings.filterwarnings("ignore")

# --- Third-Party Frameworks & Authentication ---

import bcrypt

from dotenv import load_dotenv

import base64

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Response, UploadFile, status

from fastapi.responses import FileResponse

from fastapi.security import OAuth2PasswordBearer

from fastapi.staticfiles import StaticFiles

from google.auth.transport import requests as google_requests

from google.oauth2 import id_token

import jwt

from pydantic import BaseModel

import re

import edge_tts

from fastapi.responses import StreamingResponse

from enum import Enum

from pwdlib import PasswordHash

from sqlalchemy import select

from sqlalchemy.orm import Session

# --- LangChain & AI Pipeline ---

from langchain_core.documents import Document

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from langchain_core.output_parsers import StrOutputParser

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langchain_core.runnables import RunnablePassthrough

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from langchain_pinecone import PineconeVectorStore

# --- Local Application Modules ---

from database import SessionLocal, get_db

from llm_factory import get_llm

from models import Chat, Message, ChatDocument, User as UserModel

from System_Prompt import (
    system_prompt,
    system_prompt2,
    translation_prompt_hindi,
    audio_overview_prompt,
    CHAT_TITLE_PROMPT,
    LEGACY_MEDICAL_IMAGE_PROMPT,
    CLINICAL_REFINEMENT_PROMPT
)

from medical_vision_pipeline import run_universal_medical_perception, format_full_visual_transcript, retrieve_clinical_context, extract_text_from_langchain_content, preprocess_medical_image
from drug_lookup import resolve_brand

# --- CONFIGURATION ---

load_dotenv()

class TargetLanguage(str, Enum):

    AUTO = "auto"       # Speaks in whatever language the text is already in

    HINDI = "hindi"     # Always speaks in natural conversational Hindi

    ENGLISH = "english" # Always speaks in natural Indian English

# Vector Store & AI Memory

index_name = "rag-based-system-v3"

embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")

AIMemoryBufferSize = 20

# JWT & Authentication Config

SECRET_KEY = os.getenv("SECRET_KEY")

ALGORITHM = os.getenv("ALGORITHM", "HS256")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

# Password Hashing Setup

password_hash = PasswordHash.recommended()

DUMMY_HASH = password_hash.hash("dummypassword")

# --- PYDANTIC SCHEMAS ---

class Token(BaseModel):

    access_token: str

    token_type: str

class TokenData(BaseModel):

    username: str | None = None

class LoginRequest(BaseModel):

    username: str

    password: str

class RegisterRequest(LoginRequest):

    email: str

class User(BaseModel):

    id: int 

    username: str

    email: str | None = None

    full_name: str | None = None

    disabled: bool | None = None

    google_sub: str | None = None

    picture_url: str | None = None

class UserInDB(User):

    hashed_password: str | None = None

class TTSRequest(BaseModel):

    message_id: int | None = None

    text: str | None = None

    target_lang: str = "hi"

    voice: str | None = None

    rate: str | None = "+5%"

class ChatRequest(BaseModel):

    message: str

    chat_id: int

class ClarificationChoice(BaseModel):
    question: str
    selected_option: str

class MessageRefineRequest(BaseModel):
    message_id: int
    chat_id: int
    clarifications: list[ClarificationChoice]

class GoogleLoginRequest(BaseModel):

    credential: str

# --- HELPER FUNCTIONS ---

def format_docs(docs: list[Document]) -> str:

    return "\n\n".join(doc.page_content for doc in docs)

def get_ist_time(utc_dt):

    if not utc_dt: return ""

    # Convert UTC to IST (+5:30)

    ist_time = utc_dt + timedelta(hours=5, minutes=30)

    return ist_time.strftime("%b %d, %Y, %I:%M %p")

def clean_history_text(text: str) -> str:
    """Ensures raw XML tags or clarification blocks never pollute conversational memory."""
    if not text:
        return ""
    cleaned = re.sub(r'<clarification_questions>[\s\S]*?</clarification_questions>', '', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'</?clinical_response>', '', cleaned).strip()
    return cleaned

def GetChatHistory(db, BufferSize, chat_id: int):

    try:

        stmt = select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at)

        messages = db.scalars(stmt).all()

        # Filter out error messages FIRST so they don't waste LLM tokens!

        history = [{"role": msg.role, "content": msg.content} for msg in messages if msg.role != "error"]

        # THEN apply the buffer size on the clean history

        history = history[-BufferSize : ]

        chat_history = [

            HumanMessage(content=clean_history_text(m["content"])) if m["role"] == "user"

            else AIMessage(content=clean_history_text(m["content"]))

            for m in history

        ]

        return chat_history

    except Exception as e:

        return []

def generate_unique_username(db: Session, base_name: str) -> str:

    # Clean the base name (lowercase, alphanumeric only)

    clean_base = "".join(c for c in base_name.lower() if c.isalnum()) or "user"

    username = clean_base

    counter = 1

    while db.scalars(select(UserModel).where(UserModel.username == username)).first():

        username = f"{clean_base}{counter}"

        counter += 1

    return username

def verify_password(plain_password, hashed_password):

    return password_hash.verify(plain_password, hashed_password)

def get_password_hash(password):

    return password_hash.hash(password)

def create_access_token(username: str):

    # Set the token to expire 24 hours from now using UTC time

    expire = datetime.now(timezone.utc) + timedelta(hours=24)

    data = {

        "sub": username,

        "exp": expire

    }

    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def get_user(db: Session, username: str) -> UserInDB | None:

    statement = select(UserModel).where(

        UserModel.username == username

    )

    user_row = db.scalars(statement).first()

    if user_row is None:

        return None

    return UserInDB(

        id=user_row.id,

        username=user_row.username,

        email=user_row.email,

        hashed_password=user_row.hashed_password,

        google_sub=user_row.google_sub,

        picture_url=user_row.picture_url,

    )

def authenticate_user(fake_db, username: str, password: str):

    user = get_user(fake_db, username)

    if not user:

        verify_password(password, DUMMY_HASH)

        return False

    if not user.hashed_password or not verify_password(password, user.hashed_password):

        return False

    return user

def get_current_user(request: Request, db: Session = Depends(get_db)):

    # 1. Read token from the HttpOnly Cookie

    token = request.cookies.get("access_token")

    if not token:

        # 2. If not found, check the Authorization header    

        auth_header = request.headers.get("Authorization")

        if auth_header and auth_header.startswith("Bearer "):

            token = auth_header.split(" ")[1]

    if not token:

        raise HTTPException(status_code=401, detail="Missing token")

    try:

        payload = jwt.decode(

            token,

            SECRET_KEY,

            algorithms=[ALGORITHM]

        )

    except jwt.InvalidTokenError:

        raise HTTPException(status_code=401)

    username = payload.get("sub")

    user = get_user(db, username)

    if user is None:

        raise HTTPException(status_code=401)

    return user

def background_generate_title(chat_id: int, chat_history_list: list):

    try:

        # Create a fresh database connection for the background task

        db_gen = get_db()

        db = next(db_gen)

        # Format the last 5 messages for the LLM

        prompt_text = CHAT_TITLE_PROMPT

        for msg in chat_history_list[-AIMemoryBufferSize:]:

            prompt_text += f"{msg.type}: {msg.content}\n"

        # Use our existing Gemini model with a StrOutputParser to guarantee a string!

        title_chain = llm | StrOutputParser()

        raw_title = title_chain.invoke(prompt_text)

        # Clean up any quotes the AI might have added

        new_title = raw_title.replace('"', '').strip()

        # Update the database

        stmt = select(Chat).where(Chat.id == chat_id)

        chat = db.scalars(stmt).first()

        if chat:

            chat.title = new_title

            db.commit()

        db.close()

    except Exception as e:

        print("Background Title Error:", e)

# --- APP & PIPELINE SETUP ---

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# Persistent Uploads Directory for Images & PDFs
if not os.path.exists("uploads"):
    os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

def generate_pdf_thumbnail(pdf_path: str, thumb_path: str) -> bool:
    """Renders page 1 of a PDF document into a high-resolution PNG thumbnail."""
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(pdf_path)
        if len(pdf) > 0:
            page = pdf[0]
            image = page.render(scale=1.5).to_pil()
            image.save(thumb_path, format="PNG")
            return True
    except Exception as e:
        print(f"[PDF THUMBNAIL NOTICE]: {e}")
    return False

print("Connecting to Pinecone database...")

vector_db = PineconeVectorStore(index_name=index_name, embedding=embeddings)

print("Setting Up The Retriever...")

retriever = vector_db.as_retriever(

    search_type="similarity_score_threshold",

    search_kwargs={"k": 5, "score_threshold": 0.68}

)

print("Setting up the active LLM...")

llm = get_llm(temperature=0.2)

print("Setting up the translator LLM...")

translator_llm = get_llm(temperature=0.1)

print("Building the pure LCEL Chat Pipeline...")

# A. The Rephraser Pipe (Pure LCEL)

context_prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt2 + "\n\n{media_context}"),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}")
])

rephraser_chain = context_prompt | llm | StrOutputParser()

async def analyze_stage1_query(
    user_msg: str,
    chat_history: list,
    media_documents: list[ChatDocument],
    current_upload_doc_no: int | None = None
) -> dict:
    """
    Executes unified Stage 1 using the upgraded system_prompt2.
    Analyzes medical intent, inspects all session media transcripts with timestamps,
    determines RAG necessity, formulates a standalone search query, and identifies referenced docs.
    Returns:
    {
        "is_medical_query": bool,
        "requires_rag": bool,
        "standalone_search_query": str or None,
        "referenced_doc_ids": list[int]
    }
    """
    if media_documents:
        lines = ["### SESSION ATTACHED DOCUMENTS (Capped to last 20):"]
        for doc in media_documents:
            time_str = get_ist_time(doc.created_at)
            is_current = " [CURRENT TURN ATTACHMENT]" if doc.doc_no == current_upload_doc_no else ""
            type_label = doc.doc_type.replace('_', ' ').title() if doc.doc_type else "Medical Document"
            lines.append(f"--- Document {doc.doc_no}: {type_label} (Uploaded: {time_str}){is_current} ---")
            lines.append(doc.raw_visual_transcript)
        media_context_text = "\n\n".join(lines)
    else:
        media_context_text = "No attached documents in this consultation."

    try:
        raw_output = await rephraser_chain.ainvoke({
            "input": user_msg,
            "chat_history": chat_history,
            "media_context": media_context_text
        })
        text = str(raw_output).strip()
        if text.startswith("```"):
            parts = text.split("```")
            if len(parts) > 1:
                text = parts[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()
        data = json.loads(text)

        referenced = data.get("referenced_doc_ids", [])
        if not isinstance(referenced, list):
            referenced = []

        # Deterministic Guardrail for Currently Attached File:
        if current_upload_doc_no and current_upload_doc_no not in referenced:
            referenced.append(current_upload_doc_no)

        suspected_topics = data.get("suspected_clinical_topics", [])
        if not isinstance(suspected_topics, list):
            suspected_topics = []

        clean_topics = [str(t).strip() for t in suspected_topics if str(t).strip()]

        return {
            "is_medical_query": bool(data.get("is_medical_query", True)),
            "requires_rag": bool(data.get("requires_rag", True)),
            "standalone_search_query": data.get("standalone_search_query"),
            "suspected_clinical_topics": clean_topics,
            "referenced_doc_ids": referenced
        }
    except Exception as e:
        print(f"[STAGE 1 INTENT NOTICE]: {e}")
        # Safe fallback: treat as medical query requiring RAG with user's raw message
        default_referenced = [current_upload_doc_no] if current_upload_doc_no else []
        return {
            "is_medical_query": True,
            "requires_rag": True,
            "standalone_search_query": user_msg,
            "suspected_clinical_topics": [],
            "referenced_doc_ids": default_referenced
        }

history_aware_retriever = (

    context_prompt 

    | llm 

    | StrOutputParser() 

    | retriever 

)

# Note: Stage 3 directly invokes llm.ainvoke(stage3_messages) multimodally below.

# C. The Post-Clarification Refinement Pipe
refiner_prompt = ChatPromptTemplate.from_messages([
    ("system", CLINICAL_REFINEMENT_PROMPT),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}")
])

refiner_chain = refiner_prompt | llm | StrOutputParser()

def parse_stage3_output(raw_output: str, referenced_docs: list = None) -> tuple[str, dict | None]:
    """
    Parses Stage 3 Doctor Persona Synthesizer output.
    Extracts the clinical response and any targeted clarification questions.
    Returns: (clinical_response_str, clarification_dict_or_None)
    """
    if not raw_output:
        return "", None

    clinical_resp = raw_output
    clarification_data = None

    # Check for root JSON structure first
    stripped = raw_output.strip()
    if stripped.startswith("```"):
        parts = stripped.split("```")
        if len(parts) > 1:
            stripped = parts[1]
            if stripped.startswith("json"):
                stripped = stripped[4:]
        stripped = stripped.strip()

    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            data = json.loads(stripped, strict=False)
            if "main_answer" in data or "clinical_response" in data:
                clinical_resp = data.get("main_answer") or data.get("clinical_response") or ""
                qs = data.get("clarification_questions") or []
                if qs and isinstance(qs, list):
                    valid_qs = []
                    for idx, q in enumerate(qs[:2]):
                        if isinstance(q, dict) and "question" in q and "options" in q:
                            opts = [str(o).strip() for o in q["options"] if str(o).strip()]
                            if opts:
                                valid_qs.append({"id": q.get("id") or f"q{idx+1}", "question": str(q["question"]).strip(), "options": opts})
                    if valid_qs:
                        clarification_data = {"needed": True, "questions": valid_qs, "resolved": False}
                return clinical_resp, clarification_data
        except Exception:
            pass

    # 1. Extract <clarification_questions> if present
    q_match = re.search(r'<clarification_questions>([\s\S]*?)</clarification_questions>', raw_output, re.IGNORECASE)
    if q_match:
        raw_json = q_match.group(1).strip()
        if raw_json.startswith("```"):
            parts = raw_json.split("```")
            if len(parts) > 1:
                raw_json = parts[1]
                if raw_json.startswith("json"):
                    raw_json = raw_json[4:]
            raw_json = raw_json.strip()
        try:
            parsed_questions = json.loads(raw_json, strict=False)
            if isinstance(parsed_questions, list) and len(parsed_questions) > 0:
                valid_questions = []
                for idx, q in enumerate(parsed_questions[:2]):  # Cap at max 2 high-yield questions
                    if isinstance(q, dict) and "question" in q and "options" in q:
                        opts = [str(o).strip() for o in q["options"] if str(o).strip()]
                        if opts:
                            valid_questions.append({
                                "id": q.get("id") or f"q{idx+1}",
                                "question": str(q["question"]).strip(),
                                "options": opts
                            })
                if valid_questions:
                    clarification_data = {
                        "needed": True,
                        "questions": valid_questions,
                        "resolved": False
                    }
        except Exception as e:
            print(f"[STAGE 3 CLARIFICATION PARSE WARNING]: {e}")

    # 2. Extract <clinical_response> if present
    resp_match = re.search(r'<clinical_response>([\s\S]*?)</clinical_response>', raw_output, re.IGNORECASE)
    if resp_match:
        clinical_resp = resp_match.group(1).strip()
    else:
        clinical_resp = re.sub(r'<clarification_questions>([\s\S]*?)</clarification_questions>', '', raw_output, flags=re.IGNORECASE).strip()
        clinical_resp = re.sub(r'</?clinical_response>', '', clinical_resp).strip()

    # 3. Clean any trailing conversational questions if clarification card is active
    if clarification_data:
        trailing_q_match = re.search(
            r'\n*(?:To help me|Please let me know|Could you let me know|Let me know|Can you confirm|Could you confirm)[^\n?]+\?\s*$',
            clinical_resp,
            re.IGNORECASE
        )
        if trailing_q_match:
            clinical_resp = clinical_resp[:trailing_q_match.start()].strip()

    return clinical_resp, clarification_data

def clean_markdown_for_speech(text: str) -> str:

    """Strips markdown syntax and URLs so Edge-TTS doesn't read punctuation/links."""

    clean = re.sub(r'[*_#`~>\[\]]', '', text)

    clean = re.sub(r'\(https?://\S+\)', '', clean)

    clean = re.sub(r'https?://\S+', '', clean)

    clean = re.sub(r'[,]{2,}', ',', clean)

    clean = re.sub(r'[—\-–]{2,}', ' ', clean)

    return clean.strip()

def extract_text_from_content(content) -> str:

    """Extracts raw string text from diverse LangChain message content formats."""

    if isinstance(content, str):

        return content

    if isinstance(content, list):

        parts = []

        for p in content:

            if isinstance(p, dict) and "text" in p:

                parts.append(p["text"])

            elif isinstance(p, str):

                parts.append(p)

            else:

                parts.append(str(p))

        return "".join(parts)

    return str(content)

async def generate_and_save_audio_overview(message_id: int, text: str) -> dict:

    """

    Background worker: Translates medical advice into natural spoken

    Hindi (Devanagari) and Indian English overviews, caching them in message.translations.

    """

    clean_text = clean_markdown_for_speech(text)

    if not clean_text or len(clean_text) < 2:

        return {}

    try:

        formatted_prompt = audio_overview_prompt.format(text=clean_text)

        response = await translator_llm.ainvoke(formatted_prompt)

        raw = extract_text_from_content(response.content).strip()

        # Clean any markdown code fences if outputted by LLM

        if raw.startswith("```"):

            raw = re.sub(r'^```(?:json)?\s*', '', raw)

            raw = re.sub(r'\s*```$', '', raw)

        try:

            translations = json.loads(raw)

        except Exception:

            translations = {}

            hi_match = re.search(r'"hi"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', raw)

            en_match = re.search(r'"en"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', raw)

            if hi_match:

                try:

                    translations["hi"] = hi_match.group(1).encode('utf-8').decode('unicode_escape')

                except Exception:

                    translations["hi"] = hi_match.group(1)

            if en_match:

                try:

                    translations["en"] = en_match.group(1).encode('utf-8').decode('unicode_escape')

                except Exception:

                    translations["en"] = en_match.group(1)

        # Fallback to cleaned text if any key is missing

        if not translations.get("hi"):

            translations["hi"] = clean_text

        if not translations.get("en"):

            translations["en"] = clean_text

        # Persist to database in its own isolated session

        with SessionLocal() as db:

            msg = db.query(Message).filter(Message.id == message_id).first()

            if msg:

                current = dict(msg.translations or {})

                current.update(translations)

                msg.translations = current

                db.commit()

        return translations

    except Exception as e:

        print(f"[BACKGROUND AUDIO OVERVIEW ERROR for message {message_id}]: {e}")

        return {"hi": clean_text, "en": clean_text}

async def analyze_medical_image_with_gemini(image_bytes: bytes, mime_type: str, user_question: str) -> str:

    """

    Sends the medical image/report to Gemini Flash Vision with a structured clinical prompt.

    """

    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    if not mime_type or mime_type == "application/octet-stream":

        mime_type = "image/jpeg"

    user_q = user_question if user_question else 'Please provide a structured, complete, and clinically accurate explanation of this medical image.'
    prompt = LEGACY_MEDICAL_IMAGE_PROMPT.format(user_question=user_q)

    message = HumanMessage(

        content=[

            {"type": "text", "text": prompt},

            {

                "type": "image_url",

                "image_url": f"data:{mime_type};base64,{b64_image}"

            }

        ]

    )

    response = await llm.ainvoke([message])

    return extract_text_from_content(response.content).strip()

# --- ROUTES ---

@app.get("/")

def home():

    return FileResponse("frontend/index.html")

@app.get("/users/me")

def read_users_me(current_user: UserInDB = Depends(get_current_user)):

    return {

        "username": current_user.username,

        "email": current_user.email,

        "picture_url": current_user.picture_url

    }

@app.post("/login")

def login(

    data: LoginRequest,

    response: Response,

    db: Session = Depends(get_db),

):

    user = authenticate_user(db, data.username, data.password)

    if not user:

        raise HTTPException(

            status_code=status.HTTP_401_UNAUTHORIZED,

            detail="Incorrect username or password",

        )

    token = create_access_token(user.username)

    # Set the HttpOnly cookie!

    response.set_cookie(

        key="access_token",

        value=token,

        httponly=True,       # JavaScript cannot touch or steal it!

        max_age=86400,       # 24 hours in seconds

        samesite="lax",      # Protects against CSRF

        secure=False         # Set to True when deploying to HTTPS

    )

    return {

        "message": "Login successful"

    }

@app.post("/logout")

def logout(response: Response):

    response.delete_cookie(key="access_token")

    return {"message": "Logged out successfully"}

@app.post("/register", status_code=status.HTTP_201_CREATED)

def register(

    data: RegisterRequest,

    db: Session = Depends(get_db),

):

    username = data.username.strip()

    email = data.email.strip().lower()

    if len(username) < 3:

        raise HTTPException(

            status_code=400,

            detail="Username must be at least 3 characters.",

        )

    if len(data.password) < 8:

        raise HTTPException(

            status_code=400,

            detail="Password must be at least 8 characters.",

        )

    username_exists = db.scalars(

        select(UserModel).where(

            UserModel.username == username

        )

    ).first()

    if username_exists:

        raise HTTPException(

            status_code=400,

            detail="This username is already taken.",

        )

    email_exists = db.scalars(

        select(UserModel).where(

            UserModel.email == email

        )

    ).first()

    if email_exists:

        raise HTTPException(

            status_code=400,

            detail="An account already uses this email.",

        )

    new_user = UserModel(

        username=username,

        email=email,

        hashed_password=get_password_hash(data.password),

    )

    db.add(new_user)

    db.commit()

    return {

        "message": "Account created. You can now sign in."

    }

@app.get("/auth/google/client-id")

def get_google_client_id():

    return {"client_id": GOOGLE_CLIENT_ID}

@app.post("/auth/google")

def google_auth(

    data: GoogleLoginRequest,

    response: Response,

    db: Session = Depends(get_db)

):

    try:

        id_info = id_token.verify_oauth2_token(

            data.credential,

            google_requests.Request(),

            GOOGLE_CLIENT_ID

        )

    except ValueError:

        raise HTTPException(

            status_code=status.HTTP_401_UNAUTHORIZED,

            detail="Invalid or expired Google token"

        )

    google_sub = id_info.get("sub")

    email = id_info.get("email", "").lower()

    name = id_info.get("name") or email.split("@")[0]

    picture_url = id_info.get("picture")

    if not google_sub or not email:

        raise HTTPException(

            status_code=status.HTTP_400_BAD_REQUEST,

            detail="Could not retrieve account details from Google"

        )

    # 3. Account Resolution:

    # A) Existing Google user -> update picture and use

    user = db.scalars(select(UserModel).where(UserModel.google_sub == google_sub)).first()

    if user:

        if picture_url:

            user.picture_url = picture_url

            db.commit()

    # B) Existing email user -> link google_sub & picture

    if not user:

        user = db.scalars(select(UserModel).where(UserModel.email == email)).first()

        if user:

            user.google_sub = google_sub

            if picture_url:

                user.picture_url = picture_url

            db.commit()

    # C) Brand new user -> create account

    if not user:

        unique_username = generate_unique_username(db, name)

        user = UserModel(

            username=unique_username,

            email=email,

            google_sub=google_sub,

            picture_url=picture_url,

            hashed_password="!OAUTH_GOOGLE_ACCOUNT!"

        )

        db.add(user)

        db.commit()

    token = create_access_token(user.username)

    response.set_cookie(

        key="access_token",

        value=token,

        httponly=True,

        max_age=86400,

        samesite="lax",

        secure=False

    )

    return {

        "message": "Google login successful",

        "username": user.username

    }

@app.get("/chats")

def get_all_chats(current_user: UserInDB = Depends(get_current_user), db: Session = Depends(get_db)):

    try:

        stmt = select(Chat).where(Chat.user_id == current_user.id).order_by(Chat.created_at)

        chats = list(db.scalars(stmt).all())

        # Convert to JSON for Javascript using IST — now includes is_generating!

        history = [{"id": chat.id, "title": chat.title, "time": get_ist_time(chat.created_at), "is_generating": chat.is_generating} for chat in chats]

        return history

    except Exception as e:

        return {"error": f"Failed to retrieve chats due to: {e}"}

@app.post("/chats/new")

def create_new_chat(user_prompt: str, current_user: UserInDB = Depends(get_current_user), db: Session = Depends(get_db)):

    endingstring = "..." if len(user_prompt) > 20 else ""

    title = f"{user_prompt[:20]}{endingstring}"

    # One single insert with the real title, 1 commit, done!

    new_chat = Chat(user_id=current_user.id, title=title)

    db.add(new_chat)

    db.commit()

    return {"id": new_chat.id}

@app.delete("/chats/{chat_id}")

def delete_chat(chat_id: int, current_user: UserInDB = Depends(get_current_user), db: Session = Depends(get_db)):

    # 1. Verify the chat exists AND belongs to the user

    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()

    if not chat:

        raise HTTPException(status_code=404, detail="Chat not found or access denied")

    try:

        # Delete messages first

        stmt = select(Message).where(Message.chat_id == chat_id)

        for msg in db.scalars(stmt).all():

            db.delete(msg)

        # Delete attached documents and clean up files from disk
        stmt_docs = select(ChatDocument).where(ChatDocument.chat_id == chat_id)
        for doc in db.scalars(stmt_docs).all():
            if doc.file_url:
                local_f = doc.file_url.lstrip("/")
                if os.path.exists(local_f):
                    try:
                        os.remove(local_f)
                    except Exception:
                        pass
            if doc.thumbnail_url and doc.thumbnail_url != doc.file_url:
                local_t = doc.thumbnail_url.lstrip("/")
                if os.path.exists(local_t):
                    try:
                        os.remove(local_t)
                    except Exception:
                        pass
            db.delete(doc)

        # Delete chat

        stmt2 = select(Chat).where(Chat.id == chat_id)

        for c in db.scalars(stmt2).all():

            db.delete(c)

        db.commit()

        return {"success": True}

    except Exception as e:

        db.rollback()

        raise HTTPException(status_code=500, detail=f"Failed to delete chat: {e}")

@app.get("/history/{chat_id}")

def get_chat_history(chat_id: int, current_user: UserInDB = Depends(get_current_user), db: Session = Depends(get_db)):

    # 1. Verify the chat exists AND belongs to the user

    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()

    if not chat:

        raise HTTPException(status_code=404, detail="Chat not found or access denied")

    try:

        stmt = select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at)

        messages = db.scalars(stmt).all()

        history = []

        for msg in messages:

            parsed_sources = json.loads(msg.sources) if msg.sources else None

            history.append({
                "id": msg.id,
                "role": msg.role, 
                "content": msg.content, 
                "translations": msg.translations or {},
                "time": get_ist_time(msg.created_at),
                "sources": parsed_sources,
                "file_url": getattr(msg, 'file_url', None),
                "thumbnail_url": getattr(msg, 'thumbnail_url', None),
                "file_name": getattr(msg, 'file_name', None),
                "file_type": getattr(msg, 'file_type', None)
            })

        return history

    except Exception as e:

        raise HTTPException(status_code=500, detail=f"Failed to retrieve chat history: {e}")

@app.get("/message/translations/{message_id}")
def get_message_translations(
    message_id: int,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Checks whether speech translations are ready for a specific message."""
    msg = db.query(Message).filter(Message.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    chat = db.query(Chat).filter(Chat.id == msg.chat_id, Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=403, detail="Access denied")

    translations = msg.translations if isinstance(msg.translations, dict) else {}
    is_ready = bool(translations and ("hi" in translations or "en" in translations))

    return {
        "message_id": msg.id,
        "is_ready": is_ready,
        "translations": translations
    }

@app.post("/chat/stop/{chat_id}")

def stop_generating(chat_id: int, current_user: UserInDB = Depends(get_current_user), db: Session = Depends(get_db)):

    # 1. Verify the chat exists AND belongs to the user

    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()

    if not chat:

        raise HTTPException(status_code=404, detail="Chat not found or access denied")

    try:

        # 1. Set the flag to False (unlocks the chat)

        if chat:

            chat.is_generating = False

        # 2. Save a cancellation error message

        error_message = Message(chat_id=chat_id, role="error", content="Generation was cancelled.")

        db.add(error_message)

        db.commit()

        return {"success": True}

    except Exception as e:

        db.rollback()

        raise HTTPException(status_code=500, detail=f"Failed to stop generation: {e}")

@app.delete("/messages/last/{chat_id}")

def delete_last_message(chat_id: int, current_user: UserInDB = Depends(get_current_user), db: Session = Depends(get_db)):

    # 1. Verify the chat exists AND belongs to the user

    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()

    if not chat:

        raise HTTPException(status_code=404, detail="Chat not found or access denied")

    try:

        stmt = select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at.desc())

        last_msg = db.scalars(stmt).first()

        if last_msg:

            db.delete(last_msg)

            db.commit()

        return {"success": True}

    except Exception as e:

        db.rollback()

        raise HTTPException(status_code=500, detail=f"Failed to delete last message: {e}")

@app.post("/chat")

async def chat_with_bot(

    request: Request,

    background_tasks: BackgroundTasks,

    current_user: UserInDB = Depends(get_current_user),

    db: Session = Depends(get_db)

):

    # 1. Parse both JSON and multipart/form-data dynamically

    content_type = request.headers.get("content-type", "")

    uploaded_file: UploadFile | None = None

    if "multipart/form-data" in content_type:

        form = await request.form()

        user_message = str(form.get("message", "")).strip()

        chat_id = int(form.get("chat_id"))

        file_field = form.get("file")

        if file_field and hasattr(file_field, "filename") and file_field.filename:

            uploaded_file = file_field

    else:

        body = await request.json()

        user_message = str(body.get("message", "")).strip()

        chat_id = int(body.get("chat_id"))

    # 2. Verify chat exists and belongs to the user

    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()

    if not chat:

        raise HTTPException(status_code=404, detail="Chat not found or access denied")

    # 3. Verify character limit (max 500 characters)

    char_count = len(user_message)

    if char_count > 500:

        raise HTTPException(

            status_code=status.HTTP_400_BAD_REQUEST,

            detail=f"Message exceeds the 500-character limit ({char_count}/500)."

        )

    try:

        chat.is_generating = True

        msg_count = db.query(Message).filter(Message.chat_id == chat_id).count()

        old_history = GetChatHistory(db, AIMemoryBufferSize, chat_id)

        # Record user message in DB

        recorded_user_msg = user_message if user_message else "[Uploaded Medical Attachment]"

        db_message = Message(chat_id=chat_id, role="user", content=recorded_user_msg)  

        db.add(db_message)

        db.commit()

        current_upload_doc_no = None

        if uploaded_file:
            # Stage 0: Perception & Extraction of newly attached media
            image_bytes = await uploaded_file.read()
            
            # 1. Strict Upload Size Limit (10 MB)
            MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB limit
            if len(image_bytes) > MAX_UPLOAD_SIZE:
                chat.is_generating = False
                db.commit()
                friendly_err = "The uploaded file exceeds the 10 MB limit. Please upload a smaller or compressed document."
                err_msg = Message(chat_id=chat_id, role="error", content=friendly_err)
                db.add(err_msg)
                db.commit()
                return {"error": True, "message": friendly_err}

            mime_type = uploaded_file.content_type or "image/jpeg"
            orig_filename = uploaded_file.filename or "medical_document"
            is_pdf = (mime_type == "application/pdf" or orig_filename.lower().endswith(".pdf"))

            # 2. Pre-compress photos before saving to disk (slashes disk usage by ~95% from 8MB to ~250KB)
            if not is_pdf:
                image_bytes = preprocess_medical_image(image_bytes)
                mime_type = "image/jpeg"
                ext = ".jpg"
            else:
                ext = ".pdf"
            
            # 3. Rolling Document Quota per Chat (Keeps at most 3 active documents per consultation)
            # Evicts oldest physical files from disk so users never exhaust server storage
            MAX_DOCS_PER_CHAT = 3
            existing_docs = db.query(ChatDocument).filter(ChatDocument.chat_id == chat_id).order_by(ChatDocument.doc_no.asc()).all()
            max_existing_no = max([d.doc_no for d in existing_docs], default=0)
            while len(existing_docs) >= MAX_DOCS_PER_CHAT:
                old_doc = existing_docs.pop(0)
                if old_doc.file_url:
                    local_f = old_doc.file_url.lstrip("/")
                    if os.path.exists(local_f):
                        try:
                            os.remove(local_f)
                        except Exception:
                            pass
                if old_doc.thumbnail_url and old_doc.thumbnail_url != old_doc.file_url:
                    local_t = old_doc.thumbnail_url.lstrip("/")
                    if os.path.exists(local_t):
                        try:
                            os.remove(local_t)
                        except Exception:
                            pass
                db.delete(old_doc)
            db.commit()

            current_upload_doc_no = max_existing_no + 1

            # Save uploaded document to persistent /uploads directory
            safe_token = f"chat_{chat_id}_doc_{current_upload_doc_no}_{int(datetime.utcnow().timestamp())}_{uuid.uuid4().hex[:6]}"
            saved_filename = f"{safe_token}{ext}"
            saved_path = os.path.join("uploads", saved_filename)
            
            with open(saved_path, "wb") as f:
                f.write(image_bytes)
                
            file_url = f"/uploads/{saved_filename}"
            thumbnail_url = file_url
            thumb_path = None
            
            if is_pdf:
                thumb_filename = f"{safe_token}_thumb.png"
                thumb_path = os.path.join("uploads", thumb_filename)
                if generate_pdf_thumbnail(saved_path, thumb_path):
                    thumbnail_url = f"/uploads/{thumb_filename}"
                else:
                    thumbnail_url = None
            
            # Run Multimodal AI Perception
            perception_data = await run_universal_medical_perception(
                image_bytes=image_bytes,
                mime_type=mime_type,
                user_question=user_message
            )

            # Defensive Check: If both perception attempts fail, do not save fake document
            if perception_data.get("error_fallback"):
                try:
                    if os.path.exists(saved_path):
                        os.remove(saved_path)
                    if thumb_path and os.path.exists(thumb_path):
                        os.remove(thumb_path)
                except Exception:
                    pass
                chat.is_generating = False
                db.commit()
                friendly_err = "I was unable to read this medical document clearly. Please upload a clearer, well-lit photo taken flat and fully in frame so I can analyze it safely."
                err_msg = Message(chat_id=chat_id, role="error", content=friendly_err)
                db.add(err_msg)
                db.commit()
                return {"error": True, "message": friendly_err}

            raw_transcript = format_full_visual_transcript(perception_data)
            category = perception_data.get("media_classification", {}).get("primary_category", "medical_document")
            
            doc_meta = perception_data.get("document_metadata", {})
            doc_date = doc_meta.get("document_date") or perception_data.get("syntactic_clinical_entities", {}).get("document_date")
            doc_issuer = doc_meta.get("issuer") or perception_data.get("syntactic_clinical_entities", {}).get("issuer")
            doc_summary = perception_data.get("media_classification", {}).get("description") or "Uploaded Medical Document"

            new_doc = ChatDocument(
                chat_id=chat_id,
                doc_no=current_upload_doc_no,
                doc_type=category,
                raw_visual_transcript=raw_transcript,
                file_url=file_url,
                thumbnail_url=thumbnail_url,
                file_name=orig_filename,
                mime_type="application/pdf" if is_pdf else mime_type,
                document_date=doc_date,
                issuer=doc_issuer,
                summary=doc_summary,
                perception_json=perception_data
            )
            db.add(new_doc)
            
            # Attach media to user's db_message so it survives page reloads!
            db_message.file_url = file_url
            db_message.thumbnail_url = thumbnail_url
            db_message.file_name = orig_filename
            db_message.file_type = "pdf" if is_pdf else "image"
            db.commit()

        # Retrieve session documents (last 20 for this chat, ordered by doc_no)
        doc_stmt = select(ChatDocument).where(ChatDocument.chat_id == chat_id).order_by(ChatDocument.doc_no)
        session_docs = list(db.scalars(doc_stmt).all())[-20:]

        # --- UNIFIED 4-STAGE PIPELINE ---
        cleaned_msg = user_message.strip()
        if uploaded_file and (not cleaned_msg or re.fullmatch(r'[\s.,;:!?\-_~]+', cleaned_msg)):
            effective_query_input = "Please evaluate my attached medical document completely."
        else:
            effective_query_input = user_message if user_message else "Please evaluate my attached medical document completely."
        
        # Stage 1: LLM Clinical Intent, Rephrasing & Document Selection (system_prompt2)
        query_intent = await analyze_stage1_query(
            user_msg=effective_query_input,
            chat_history=old_history,
            media_documents=session_docs,
            current_upload_doc_no=current_upload_doc_no
        )
        requires_rag = query_intent.get("requires_rag", False)
        standalone_query = query_intent.get("standalone_search_query")
        referenced_doc_ids = query_intent.get("referenced_doc_ids", [])
        referenced_docs = [doc for doc in session_docs if doc.doc_no in referenced_doc_ids]
        unreferenced_docs = [doc for doc in session_docs if doc.doc_no not in referenced_doc_ids]

        # Stage 2: Shared Safe Retrieval from Pinecone (Multi-Topic Decomposed Clinical Retrieval)
        rag_context = ""
        sources_list = []
        is_quota_paused = False
        if requires_rag:
            search_term = standalone_query if standalone_query else effective_query_input
            rag_queries = []
            seen_queries_lower = set()

            def _add_query(q_str: str):
                cleaned = q_str.strip()
                if cleaned and cleaned.lower() not in seen_queries_lower and len(rag_queries) < 6:
                    seen_queries_lower.add(cleaned.lower())
                    rag_queries.append(cleaned)

            def resolve_med(m: dict) -> dict:
                return resolve_brand(
                    m.get("brand_as_written") or m.get("raw_text") or "",
                    reading=str(m.get("reading") or "clear").lower(),
                    spelling_candidates=m.get("spelling_candidates") or []
                )

            # 1. RESOLVED MEDICINE SALTS FIRST (Guaranteed query budget, up to 3 distinct salts)
            # NEVER query unresolved brand names to prevent nearest-neighbor textbook hallucinations
            salts = []
            if referenced_docs:
                for doc in referenced_docs[:3]:
                    p_data = getattr(doc, 'perception_json', None) or {}
                    meds = p_data.get("syntactic_clinical_entities", {}).get("prescribed_medications", [])
                    for m in meds:
                        res = resolve_med(m)
                        salt_name = res.get("salt") or m.get("generic_name") or m.get("resolved_generic_salt")
                        if salt_name and salt_name not in salts:
                            salts.append(salt_name)

            for s in salts[:3]:
                _add_query(f"{s} indication dosage timing pharmacopeia")

            # 2. STAGE 1 CLINICAL TOPICS (Up to 2 clean synthesized topics - no raw OCR handwriting)
            stage1_topics = query_intent.get("suspected_clinical_topics", [])
            for topic in stage1_topics[:2]:
                _add_query(topic)

            # 3. USER CLINICAL QUERY / STANDALONE SEARCH (If specific)
            if search_term and search_term != "Please evaluate my attached medical document completely.":
                _add_query(search_term)

            # 4. OUT-OF-RANGE LAB FINDINGS (At most 2 abnormal tests)
            if referenced_docs and len(rag_queries) < 6:
                for doc in referenced_docs[:2]:
                    p_data = getattr(doc, 'perception_json', None) or {}
                    lab_results = p_data.get("syntactic_clinical_entities", {}).get("laboratory_results_table", [])
                    for row in lab_results:
                        status = (row.get("status") or "").strip().lower()
                        test_name = (row.get("test_name") or "").strip()
                        if test_name and status in ["high", "low", "critical"]:
                            _add_query(f"{test_name} {status} reference interval panic values ICMR USMLE")
                            if len(rag_queries) >= 6:
                                break

            # Fallback if no specific entity was extracted
            if not rag_queries:
                rag_queries.append(search_term if search_term else "AIIMS standard clinical guidelines")

            rag_context, sources_list, is_quota_paused = await retrieve_clinical_context(
                rag_queries,
                retriever
            )

        # Stage 3: Doctor Synthesis (Filtered Media Injection & Clean Semantic Ordering)
        patient_documents_section = ""
        if referenced_docs or unreferenced_docs:
            doc_blocks = ["### SECTION 1: PATIENT CONSULTATION DOCUMENTS"]
            
            # Separate the Newly Attached Document from Previous Consultation Documents:
            current_turn_docs = [d for d in referenced_docs if current_upload_doc_no and d.doc_no == current_upload_doc_no]
            past_consultation_docs = [d for d in referenced_docs if not (current_upload_doc_no and d.doc_no == current_upload_doc_no)]
            
            if current_turn_docs:
                doc_blocks.append("[CURRENT TURN ATTACHMENT - UPLOADED WITH THIS MESSAGE]:")
                for doc in current_turn_docs:
                    time_str = get_ist_time(doc.created_at)
                    date_info = f", Document Date: {doc.document_date}" if getattr(doc, 'document_date', None) else ""
                    type_label = doc.doc_type.replace('_', ' ').title() if doc.doc_type else "Medical Document"
                    # Defend against prompt injection by escaping document tags in raw transcript:
                    safe_transcript = (doc.raw_visual_transcript or "").replace("</document>", "").replace("<document", "")
                    doc_blocks.append(f'<document type="{type_label}" uploaded="{time_str}"{date_info}>\n{safe_transcript}\n</document>')
                    
            if past_consultation_docs:
                doc_blocks.append("[PREVIOUS CONSULTATION RECORDS - RELEVANT TO THIS QUESTION]:")
                for doc in past_consultation_docs:
                    time_str = get_ist_time(doc.created_at)
                    date_info = f", Document Date: {doc.document_date}" if getattr(doc, 'document_date', None) else ""
                    type_label = doc.doc_type.replace('_', ' ').title() if doc.doc_type else "Medical Document"
                    safe_transcript = (doc.raw_visual_transcript or "").replace("</document>", "").replace("<document", "")
                    doc_blocks.append(f'<document type="{type_label}" uploaded="{time_str}"{date_info}>\n{safe_transcript}\n</document>')
                    
            if unreferenced_docs:
                other_summaries = []
                for d in unreferenced_docs:
                    t_label = d.doc_type.replace('_', ' ').title() if d.doc_type else "Medical Document"
                    t_time = get_ist_time(d.created_at)
                    other_summaries.append(f"{t_label} (uploaded: {t_time})")
                doc_blocks.append(f"<other_records>Other past records in this consultation: {'; '.join(other_summaries)}</other_records>")
                
            patient_documents_section = "\n\n".join(doc_blocks)

        factual_literature_section = ""
        if rag_context:
            factual_literature_section = (
                "### SECTION 2: RETRIEVED CLINICAL REFERENCE EXCERPTS (AIIMS & PHARMACOPEIA)\n"
                "(Authoritative clinical knowledge and outpatient pharmacopeia. "
                "These excerpts were retrieved based on the clinical queries above. "
                "Use an excerpt only if it directly addresses the specific medication, test, or condition being discussed. "
                "Never force an excerpt onto an unrelated item, never swap a medication name on literature alone, "
                "and clearly state which readings are uncertain or unverified.)\n\n"
                + rag_context
            )

        # Assemble Context: Current Date, Patient Documents FIRST, then Supporting Factual Literature
        current_time_str = get_ist_time(datetime.utcnow())
        context_parts = [f"<today>{current_time_str}</today>"]
        if patient_documents_section:
            context_parts.append(patient_documents_section)
        if factual_literature_section:
            context_parts.append(factual_literature_section)
            
        combined_context = "\n\n======================================================================\n\n".join(context_parts).strip()

        # Check if media is available for Stage 3 multimodal perception (supports multiple images/PDFs)
        stage3_media_items = []
        if uploaded_file and 'image_bytes' in locals() and image_bytes:
            m_type = "application/pdf" if is_pdf else "image/jpeg"
            b64_data = base64.b64encode(image_bytes).decode("utf-8")
            stage3_media_items.append({"mime_type": m_type, "b64": b64_data})

        # Also inspect referenced past documents (e.g. comparing past prescriptions/reports)
        if referenced_docs:
            for d in referenced_docs:
                if current_upload_doc_no and d.doc_no == current_upload_doc_no:
                    continue  # already added as current upload
                if len(stage3_media_items) >= 2:  # cap at 2 media attachments to stay safe on tokens and latency
                    break
                if d.file_url:
                    local_doc_path = d.file_url.lstrip("/")
                    if os.path.exists(local_doc_path):
                        try:
                            ext = os.path.splitext(local_doc_path)[1].lower()
                            if ext == ".pdf":
                                with open(local_doc_path, "rb") as pf:
                                    stage3_media_items.append({
                                        "mime_type": "application/pdf",
                                        "b64": base64.b64encode(pf.read()).decode("utf-8")
                                    })
                            elif ext in [".jpg", ".jpeg", ".png", ".webp"]:
                                with open(local_doc_path, "rb") as imf:
                                    prep_bytes = preprocess_medical_image(imf.read())
                                    stage3_media_items.append({
                                        "mime_type": "image/jpeg",
                                        "b64": base64.b64encode(prep_bytes).decode("utf-8")
                                    })
                        except Exception:
                            pass

        # Stage 3: Multimodal Doctor Persona Synthesizer
        stage3_system_text = system_prompt.format(context=combined_context)

        stage3_instruction_parts = [effective_query_input]
        if stage3_media_items:
            stage3_instruction_parts.append(
                "[SECOND-PASS CLINICAL RE-EVALUATION & COHERENCE DIRECTIVE: You have direct visual access to the attached document image(s). "
                "Re-examine every medication line and clinical reading against the overall clinical diagnosis, organ system, and specialty context. "
                "If any extracted reading seems out-of-place (e.g. an eye prescription containing what looks like a lung drug, or an unusual cursive name), "
                "re-inspect the physical visual ink strokes for alternative candidate spellings that clinically fit the therapeutic environment. "
                "Confidently deduce the most accurate clinical medication and explain it clearly, noting your clinical reasoning transparently.]\n\n"
                "[IMAGE GROUNDING & CONFLICT DIRECTIVE: If the visual image and the extracted document text disagree on any line, drug name, or dosage, trust the visual image and explicitly state the discrepancy.]"
            )

        stage3_instruction_parts.append(
            "[RESPONSE STRUCTURE DIRECTIVE: Wrap your clinical response inside <clinical_response>...</clinical_response>. If and only if a specific line is unreadable or ambiguous and an observable discriminator exists (e.g. medicine physical form: liquid suspension vs dry powder bottle, patient's doctor-stated condition, or packaging composition photo), append 1 targeted MCQ inside <clarification_questions>[{\"id\": \"q1\", \"question\": \"<observable discriminator>\", \"options\": [\"<Option A>\", \"<Option B>\", \"Not sure / Don't remember / Check with pharmacist\"]}]</clarification_questions>. If an ambiguous line has no observable discriminator, state the uncertainty honestly in prose and advise pharmacist verification—do NOT generate questions. If any medication contains a suffix warning regarding combination or release form, caution the patient to verify the composition line on the pack. Options must be observable facts or candidate drug spellings from lookup, NEVER invented clinical indications. Do NOT write conversational questions at the end of your text response.]"
        )
        stage3_instruction = "\n\n".join(stage3_instruction_parts)

        if stage3_media_items:
            stage3_human_content = [{"type": "text", "text": stage3_instruction}]
            for m_item in stage3_media_items:
                stage3_human_content.append({
                    "type": "image_url",
                    "image_url": f"data:{m_item['mime_type']};base64,{m_item['b64']}"
                })
        else:
            stage3_human_content = stage3_instruction

        stage3_messages = [
            SystemMessage(content=stage3_system_text),
            *old_history,
            HumanMessage(content=stage3_human_content)
        ]

        raw_response = await llm.ainvoke(stage3_messages)
        raw_result = extract_text_from_langchain_content(raw_response.content)

        clinical_answer, clarification_data = parse_stage3_output(raw_result, referenced_docs=referenced_docs)

        if is_quota_paused and not sources_list and requires_rag:
            result = f"> ⚠️ *Live medical textbook verification is temporarily paused. This response is based on general clinical AI knowledge.*\n\n{clinical_answer}"
        else:
            result = clinical_answer

        # Track referenced documents in sources list for complete clinical traceability!
        if referenced_docs:
            for doc in referenced_docs:
                type_label = doc.doc_type.replace('_', ' ').title() if doc.doc_type else "Medical Record"
                sources_list.append({
                    "kind": "patient_record",
                    "doc_no": doc.doc_no,
                    "title": type_label,
                    "page": type_label,
                    "file_name": getattr(doc, 'file_name', None) or type_label,
                    "file_url": getattr(doc, 'file_url', None),
                    "thumbnail_url": getattr(doc, 'thumbnail_url', None),
                    "doc_type": doc.doc_type,
                    "text": f"Uploaded {type_label.lower()}"
                })
        sources_json = json.dumps(sources_list) if sources_list else None

        # CHECK: Did the user cancel while Gemini was thinking?

        db.refresh(chat)

        if not chat.is_generating:

            return {"cancelled": True}

        # 4. Save to the database

        db_response = Message(chat_id=chat_id, role="ai", content=result, sources=sources_json)

        db.add(db_response)

        chat.is_generating = False

        db.commit()

        # TRIGGER BACKGROUND AUDIO OVERVIEW GENERATION

        background_tasks.add_task(generate_and_save_audio_overview, db_response.id, result)

        # TRIGGER BACKGROUND TITLE GENERATION

        if msg_count == 0 or msg_count % 10 == 0:

            full_history = old_history + [HumanMessage(content=recorded_user_msg), AIMessage(content=result)]

            background_tasks.add_task(background_generate_title, chat_id, full_history)

        user_attachment_info = None
        if uploaded_file and 'file_url' in locals():
            user_attachment_info = {
                "file_url": file_url,
                "thumbnail_url": thumbnail_url,
                "file_name": orig_filename,
                "file_type": "pdf" if is_pdf else "image"
            }

        return {
            "response": result,
            "sources": sources_list,
            "message_id": db_response.id,
            "clarification": clarification_data,
            "user_attachment": user_attachment_info
        }

    except Exception as e:

        error_str = str(e)

        print(f"\n[AI PIPELINE ERROR]: {error_str}\n")

        if "503" in error_str or "high demand" in error_str:

            friendly_msg = "I'm sorry, my servers are currently experiencing extremely high demand. Please wait a few seconds and try again!"

        else:

            friendly_msg = "I'm sorry, I ran into an unexpected system error. Please try again later."

        try:

            error_message = Message(chat_id=chat_id, role="error", content=friendly_msg)

            db.add(error_message)

            chat.is_generating = False

            db.commit()

        except Exception as db_err:

            db.rollback()

            print(f"[CRITICAL: FAILED TO SAVE ERROR TO DB]: {db_err}")

        return {"error": True, "message": friendly_msg}

@app.post("/message/refine")
async def refine_message(
    req: MessageRefineRequest,
    background_tasks: BackgroundTasks,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Refines an existing AI message in-place based on patient-confirmed clarifications.
    Strictly preserves the single AI message in database and chat history.
    """
    chat = db.query(Chat).filter(Chat.id == req.chat_id, Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found or access denied")

    msg = db.query(Message).filter(Message.id == req.message_id, Message.chat_id == req.chat_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    meaningful_clarifications = [
        c for c in req.clarifications
        if c.selected_option and not any(skip_term in c.selected_option.lower() for skip_term in ["skip", "not sure", "don't know", "none of these"])
    ]

    if not meaningful_clarifications:
        return {"status": "unchanged", "refined_content": msg.content}

    try:
        # A. Patient documents for this chat
        doc_stmt = select(ChatDocument).where(ChatDocument.chat_id == req.chat_id).order_by(ChatDocument.doc_no)
        session_docs = list(db.scalars(doc_stmt).all())[-20:]
        doc_texts = []
        for d in session_docs:
            type_label = d.doc_type.replace('_', ' ').title() if d.doc_type else "Medical Document"
            time_str = get_ist_time(d.created_at)
            safe_transcript = (d.raw_visual_transcript or "").replace("</document>", "").replace("<document", "")
            doc_texts.append(f'<document type="{type_label}" uploaded="{time_str}">\n{safe_transcript}\n</document>')
        patient_docs_block = "\n\n".join(doc_texts) if doc_texts else "No attached documents in this consultation."

        # B. Clarification answers summary & targeted queries
        clarification_lines = []
        search_terms = []
        for c in req.clarifications:
            clarification_lines.append(f"- Question: {c.question}\n  Patient response (unverified): {c.selected_option}")
            search_terms.append(f"{c.question} {c.selected_option}")
        clarifications_block = "\n".join(clarification_lines)

        # C. Retrieve relevant literature using confirmed options
        literature_block = ""
        if search_terms:
            rag_ctx, _, _ = await retrieve_clinical_context(search_terms[:2], retriever)
            if rag_ctx:
                literature_block = f"### VERIFIED CLINICAL LITERATURE (AIIMS & PHARMACOPEIA):\n{rag_ctx}"

        # D. Assemble combined context for the Refiner
        combined_context = (
            f"### PATIENT CLARIFICATION (UNVERIFIED OUTPATIENT RESPONSE):\n{clarifications_block}\n\n"
            f"### INITIAL DRAFT RESPONSE (TO BE REFINED):\n{msg.content}\n\n"
            f"### PATIENT CONSULTATION DOCUMENTS:\n{patient_docs_block}\n\n"
            f"{literature_block}"
        ).strip()

        old_history = GetChatHistory(db, 6, req.chat_id)

        # E. Execute Refiner LLM
        refined_raw = await refiner_chain.ainvoke({
            "context": combined_context,
            "input": (
                "Elevate and refine the initial draft clinical response using the newly confirmed patient facts. "
                "Resolve any candidate medications or ambiguous clinical pathways against the verified literature. "
                "Maintain document attribution ('According to your prescription...'). Output the finalized clinical consultation response."
            ),
            "chat_history": old_history
        })

        # Clean tags if any
        cleaned_refined = re.sub(r'<clarification_questions>[\s\S]*?</clarification_questions>', '', refined_raw, flags=re.IGNORECASE)
        resp_match = re.search(r'<clinical_response>([\s\S]*?)</clinical_response>', cleaned_refined, re.IGNORECASE)
        if resp_match:
            cleaned_refined = resp_match.group(1).strip()
        else:
            cleaned_refined = re.sub(r'</?clinical_response>', '', cleaned_refined).strip()

        # F. Update database in-place (strictly preserving 1 AI message in history, saving draft as audit record)
        if not getattr(msg, 'draft_content', None):
            msg.draft_content = msg.content
        msg.content = cleaned_refined
        db.commit()

        # G. Re-trigger background audio overview with refined text
        background_tasks.add_task(generate_and_save_audio_overview, msg.id, cleaned_refined)

        return {"status": "success", "refined_content": cleaned_refined}

    except Exception as e:
        print(f"[REFINER LLM ERROR]: {e}")
        return {"status": "fallback", "refined_content": msg.content}

@app.post("/tts")

async def text_to_speech(req: TTSRequest):

    target_lang = (req.target_lang or "hi").strip().lower()

    speech_text = None

    # 1. Check if cached in database

    if req.message_id:

        with SessionLocal() as db:

            msg = db.query(Message).filter(Message.id == req.message_id).first()

            if msg and msg.translations and target_lang in msg.translations:

                speech_text = msg.translations[target_lang]

            elif msg and msg.content:

                # Not yet cached or older message: generate now and cache it!

                overviews = await generate_and_save_audio_overview(msg.id, msg.content)

                speech_text = overviews.get(target_lang)

    # 2. Fallback to clean raw text if message_id wasn't provided or found

    if not speech_text:

        if req.text:

            speech_text = clean_markdown_for_speech(req.text)

        else:

            speech_text = "No audio overview available."

    # 3. Select natural human-like voice

    # Default Hindi: hi-IN-SwaraNeural (Warm, empathetic female doctor)

    # Default English: en-IN-NeerjaNeural (Natural female doctor)

    if req.voice:

        selected_voice = req.voice

    elif target_lang == "hi" or any('\u0900' <= char <= '\u097F' for char in speech_text):

        selected_voice = "hi-IN-SwaraNeural"

    else:

        selected_voice = "en-IN-NeerjaNeural"

    selected_rate = req.rate if req.rate else "+5%"

    # 4. Stream audio directly as MP3 chunks via Edge-TTS (+5% natural pace)

    try:

        communicate = edge_tts.Communicate(text=speech_text, voice=selected_voice, rate=selected_rate)

        async def audio_stream():

            async for chunk in communicate.stream():

                if chunk["type"] == "audio":

                    yield chunk["data"]

        return StreamingResponse(audio_stream(), media_type="audio/mpeg")

    except Exception as e:

        print(f"[TTS STREAM ERROR]: {e}")

        raise HTTPException(status_code=500, detail=f"TTS generation error: {e}")

if __name__ == "__main__":

    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True)

