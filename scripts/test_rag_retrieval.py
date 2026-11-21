import os
from dotenv import load_dotenv
load_dotenv()

from pinecone import Pinecone
from langchain_google_genai import GoogleGenerativeAIEmbeddings

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
idx = pc.Index("rag-based-system-v3")
emb = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")

test_queries = [
    "Can I take Atorvastatin with Clarithromycin?",
    "What should I do if I miss a dose of Levothyroxine?",
    "FAST stroke protocol and warning signs",
    "What is the blood pressure target for patients with diabetes?"
]

for q in test_queries:
    vec = emb.embed_query(q)
    results = idx.query(vector=vec, top_k=2, include_metadata=True)
    print(f"\nQUERY: {q}")
    for m in results.matches:
        score = m.score
        source = m.metadata.get("ui_label", m.metadata.get("source", "Unknown"))
        snippet = m.metadata.get("text", "")[:120].replace("\n", " ")
        print(f"  [{score:.3f}] Source: {source}")
        print(f"         Snippet: {snippet}...")
