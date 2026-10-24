# --- Standard Library Imports ---
import json
import os
import warnings
from datetime import datetime, timedelta, timezone

warnings.filterwarnings("ignore")

# --- Third-Party Frameworks & Authentication ---
import bcrypt
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
import jwt
from pydantic import BaseModel
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

# --- LangChain & AI Pipeline ---
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore

# --- Local Application Modules ---
from database import SessionLocal, get_db
from llm_factory import get_llm
from models import Chat, Message, User as UserModel
from System_Prompt import system_prompt, system_prompt2


# --- CONFIGURATION ---

load_dotenv()

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


class ChatRequest(BaseModel):
    message: str
    chat_id: int


class GoogleLoginRequest(BaseModel):
    credential: str


# --- HELPER FUNCTIONS ---

def format_docs(docs: list[Document]) -> str:
    return "\n\n".join(doc.page_content for doc in docs)


def get_ist_time(utc_dt):
    if not utc_dt: return ""
    # Convert UTC to IST (+5:30)
    ist_time = utc_dt + timedelta(hours=5, minutes=30)
    return ist_time.strftime("%b %d, %I:%M %p")


def GetChatHistory(db, BufferSize, chat_id: int):
    try:
        stmt = select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at)
        messages = db.scalars(stmt).all()
        # Filter out error messages FIRST so they don't waste LLM tokens!
        history = [{"role": msg.role, "content": msg.content} for msg in messages if msg.role != "error"]
        # THEN apply the buffer size on the clean history
        history = history[-BufferSize : ]
        chat_history = [
            HumanMessage(content=m["content"]) if m["role"] == "user"
            else AIMessage(content=m["content"])
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
        prompt_text = "Generate a concise, professional 3-word title summarizing this medical conversation:\n\n"
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

print("Connecting to Pinecone database...")
vector_db = PineconeVectorStore(index_name=index_name, embedding=embeddings)
    
print("Setting Up The Retriever...")
retriever = vector_db.as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={"k": 5, "score_threshold": 0.80}
)

print("Setting up the active LLM...")
llm = get_llm(temperature=0.2)

print("Building the pure LCEL Chat Pipeline...")

# A. The Rephraser Pipe (Pure LCEL)
context_prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt2),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}")
])
history_aware_retriever = (
    context_prompt 
    | llm 
    | StrOutputParser() 
    | retriever 
)

# B. The Final Answer Pipe (Pure LCEL)
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}")
])

rag_chain = prompt | llm | StrOutputParser()


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
    new_chat = Chat(user_id=current_user.id, title="New Chat")
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    
    max_size = 20
    endingstring = ""
    if len(user_prompt) > 20:
        endingstring = "..."

    new_chat.title = f"{user_prompt[:20]+endingstring}"
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
                "role": msg.role, 
                "content": msg.content, 
                "time": get_ist_time(msg.created_at),
                "sources": parsed_sources
            })
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chat history: {e}")


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
async def chat_with_bot(request: ChatRequest, background_tasks: BackgroundTasks, current_user: UserInDB = Depends(get_current_user), db: Session = Depends(get_db)):
    # 1. Verify the chat exists AND belongs to the user
    chat = db.query(Chat).filter(Chat.id == request.chat_id, Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found or access denied")

    # 2. Verify character limit (max 500 characters)
    char_count = len(request.message.strip())
    if char_count > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Message exceeds the 500-character limit ({char_count}/500)."
        )
        
    try:
        user_message = request.message
    
        # Get the chat object and set the generating flag!
        chat.is_generating = True
    
        # Count how many messages are in this chat BEFORE we add the new one
        msg_count = db.query(Message).filter(Message.chat_id == request.chat_id).count()
    
        old_history = GetChatHistory(db, AIMemoryBufferSize, request.chat_id)

        db_message = Message(chat_id=request.chat_id, role="user", content=user_message)  
        db.add(db_message)
        db.commit()

        docs = await history_aware_retriever.ainvoke({
            "input": user_message,
            "chat_history": old_history
        })

        sources_list = []
        for doc in docs:
            sources_list.append({
                "page": doc.metadata.get("ui_label", "Unknown"), 
                "text": doc.page_content[:250] + "..." 
            })

        sources_json = json.dumps(sources_list) if sources_list else None

        # 2. Crush the docs into a string
        context_string = format_docs(docs)
        # 3. Feed the string into your rag_chain!
        result = await rag_chain.ainvoke({
            "context": context_string,
            "input": user_message,
            "chat_history": old_history
        })
        
        # CHECK: Did the user cancel while Gemini was thinking?
        # If they clicked Stop, the stop endpoint already set is_generating = False.
        # We refresh to get the latest value from the database.
        db.refresh(chat)
        if not chat.is_generating:
            # User cancelled! Don't save the AI response, just quietly exit.
            return {"cancelled": True}
        
        # 4. Save to the database
        db_response = Message(chat_id=request.chat_id, role="ai", content=result, sources=sources_json)
        db.add(db_response)
        chat.is_generating = False
        db.commit()
        
        # TRIGGER BACKGROUND TITLE GENERATION
        # If msg_count == 0 (first message) or msg_count == 10, 20, 30...
        if msg_count == 0 or msg_count % 10 == 0:
            full_history = old_history + [HumanMessage(content=user_message), AIMessage(content=result)]
            background_tasks.add_task(background_generate_title, request.chat_id, full_history)
            
        return {"response": result, "sources": sources_list}
    except Exception as e:
        error_str = str(e)
        
        # ---> ADD THIS LINE TO SEE THE REAL ERROR IN YOUR TERMINAL <---
        print(f"\n[AI PIPELINE ERROR]: {error_str}\n")
        
        # Checks For KeyWord In Gemini Error and Frame it nicely!
        if "503" in error_str or "high demand" in error_str:
            friendly_msg = "I'm sorry, my servers are currently experiencing extremely high demand. Please wait a few seconds and try again!"
        else:
            friendly_msg = "I'm sorry, I ran into an unexpected system error. Please try again later."
        
        # Save the error as a message in the database
        try:
            error_message = Message(chat_id=request.chat_id, role="error", content=friendly_msg)
            db.add(error_message)
        
            chat.is_generating = False
            db.commit()
        except Exception as db_err:
            db.rollback()  # <--- Cleans the transaction so the connection isn't corrupted
            print(f"[CRITICAL: FAILED TO SAVE ERROR TO DB]: {db_err}")
        
        return {"error": True, "message": friendly_msg}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True)
