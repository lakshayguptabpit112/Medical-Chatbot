import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace

def get_llm(temperature: float = 0.2):
    """
    Builds a fallback chain using ONLY Gemini models.
    This guarantees fallbacks work using just your one GOOGLE_API_KEY.
    Flow: 3.8 Flash -> 3.6 Flash -> 3.5 Flash-Lite
    """
    if not os.getenv("GOOGLE_API_KEY"):
        raise ValueError("GOOGLE_API_KEY is missing from .env")
        
    # Primary: Latest 3.8 generation
    gemini_3_8 = ChatGoogleGenerativeAI(
        model="gemini-3.8-flash", 
        temperature=temperature, 
        max_retries=1
    )
    
    # Backup 1: Previous 3.6 stable generation
    gemini_3_6 = ChatGoogleGenerativeAI(
        model="gemini-3.6-flash", 
        temperature=temperature, 
        max_retries=1
    )
    
    # Backup 2: The lightweight 3.5 model (fastest, least likely to be overloaded)
    gemini_3_5_lite = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite", 
        temperature=temperature, 
        max_retries=1
    )

    # ASSEMBLE THE CHAIN
    # If 3.8 is busy (503 error), it instantly tries 3.6. If 3.6 is busy, it tries 3.5-lite.
    robust_llm = gemini_3_8.with_fallbacks([
        gemini_3_6,
        gemini_3_5_lite
    ])
    
    return robust_llm