import os
from langchain_google_genai import ChatGoogleGenerativeAI

def get_llm(temperature: float = 0.2):
    """
    Builds a high-speed fallback chain using Google Gemini flash models.
    Primary: gemini-flash-lite-latest (~1.3s response time)
    Backup 1: gemini-3.5-flash (~2.9s)
    Backup 2: gemini-3.5-flash-lite (~2.2s)
    """
    if not os.getenv("GOOGLE_API_KEY"):
        raise ValueError("GOOGLE_API_KEY is missing from .env")
        
    # Primary: Fastest flash-lite model (1-2s response)
    gemini_primary = ChatGoogleGenerativeAI(
        model="gemini-flash-lite-latest", 
        temperature=temperature, 
        max_retries=1
    )
    
    # Backup 1: Highly reliable 3.5 flash
    gemini_backup_1 = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash", 
        temperature=temperature, 
        max_retries=1
    )
    
    # Backup 2: Lightweight 3.5 flash-lite
    gemini_backup_2 = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite", 
        temperature=temperature, 
        max_retries=1
    )

    # ASSEMBLE THE CHAIN
    # If primary has a momentary 503 spike, it instantly falls back to 3.5-flash, then 3.5-flash-lite
    robust_llm = gemini_primary.with_fallbacks([
        gemini_backup_1,
        gemini_backup_2
    ])
    
    return robust_llm
