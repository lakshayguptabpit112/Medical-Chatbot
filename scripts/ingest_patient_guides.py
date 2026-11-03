import os
import sys
import time
from dotenv import load_dotenv

ENV_PATH = r"c:\Users\laksh\OneDrive\Desktop\RaGMiniProject\.env"
load_dotenv(ENV_PATH)

PINECONE_KEY = os.environ.get("PINECONE_API_KEY", "").strip(' "\t\r\n')
GOOGLE_KEY = os.environ.get("GOOGLE_API_KEY", "").strip(' "\t\r\n')

if not PINECONE_KEY or not GOOGLE_KEY:
    print("[-] Error: PINECONE_API_KEY or GOOGLE_API_KEY missing in .env")
    sys.exit(1)

from pinecone import Pinecone
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

DOCS_DIR = r"c:\Users\laksh\OneDrive\Desktop\RaGMiniProject\medical_reference_docs"
INDEX_NAME = "rag-based-system-v3"
BATCH_SIZE = 25

NEW_DOCS_METADATA = {
    "Patient_Guide_to_Diagnostic_Scans_and_Lab_Preparation.md": {
        "domain": "diagnostic_imaging_and_tests",
        "source": "ICMR_AIIMS_AERB",
        "ui_label": "Patient Diagnostic Scans & Lab Prep Guide"
    },
    "ICMR_Patient_Diet_and_Lifestyle_Management_Guidelines.md": {
        "domain": "patient_diet_and_lifestyle",
        "source": "ICMR_NIN_RSSDI",
        "ui_label": "ICMR & NIN Patient Diet & Lifestyle Guidelines"
    },
    "Practical_Medicine_Administration_and_Pregnancy_Safety_Guide.md": {
        "domain": "medication_administration_and_safety",
        "source": "CDSCO_Indian_Pharmacopeia",
        "ui_label": "Practical Medicine Administration & Pregnancy Safety Guide"
    },
    "Outpatient_First_Aid_Pediatric_Care_and_Red_Flags_Guide.md": {
        "domain": "first_aid_and_emergency_triage",
        "source": "WHO_IAP_AIIMS",
        "ui_label": "Outpatient First Aid, Pediatric Care & Red Flags Guide"
    }
}

def main():
    print("=" * 60)
    print("  INGESTING PATIENT-CENTRIC CLINICAL REFERENCE GUIDES")
    print(f"  Target Pinecone Index: {INDEX_NAME}")
    print("=" * 60)

    pc = Pinecone(api_key=PINECONE_KEY)
    index = pc.Index(INDEX_NAME)
    stats = index.describe_index_stats()
    initial_count = stats.total_vector_count
    print(f"[*] Initial vector count in Pinecone: {initial_count}")

    print("[*] Initializing Google Generative AI Embeddings (models/gemini-embedding-2)...")
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-2",
        google_api_key=GOOGLE_KEY
    )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""]
    )

    all_chunks = []
    for filename, meta_info in NEW_DOCS_METADATA.items():
        filepath = os.path.join(DOCS_DIR, filename)
        if not os.path.exists(filepath):
            print(f"[-] File not found: {filepath}")
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        doc_chunks = splitter.split_text(content)
        print(f"[+] {filename}: {len(doc_chunks)} chunks generated.")
        for c_idx, c_text in enumerate(doc_chunks):
            chunk_id = f"{filename}_c{c_idx}"
            all_chunks.append({
                "id": chunk_id,
                "text": c_text,
                "metadata": {
                    "text": c_text,
                    "domain": meta_info["domain"],
                    "source": meta_info["source"],
                    "document": filename,
                    "ui_label": meta_info["ui_label"],
                    "page": 1
                }
            })

    total_chunks = len(all_chunks)
    print(f"\n[*] Total new chunks to embed and upsert: {total_chunks}")

    upserted_count = 0
    start_time = time.time()

    for i in range(0, total_chunks, BATCH_SIZE):
        batch = all_chunks[i:i + BATCH_SIZE]
        texts = [item["text"] for item in batch]
        ids = [item["id"] for item in batch]
        metadatas = [item["metadata"] for item in batch]

        print(f"[*] Embedding batch {i // BATCH_SIZE + 1}/{(total_chunks + BATCH_SIZE - 1) // BATCH_SIZE} ({len(texts)} chunks)...")
        embedded_vectors = None
        for attempt in range(5):
            try:
                embedded_vectors = embeddings.embed_documents(texts)
                break
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    wait_time = 15 + (attempt * 5)
                    print(f"[!] Rate limit (429) hit. Pacing pause for {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"[!] Embedding error: {e}. Retrying in 5s...")
                    time.sleep(5)

        if not embedded_vectors:
            print(f"[-] Failed to embed batch {i}, skipping.")
            continue

        vectors_to_upsert = []
        for vid, vec, meta in zip(ids, embedded_vectors, metadatas):
            vectors_to_upsert.append({
                "id": vid,
                "values": vec,
                "metadata": meta
            })

        for attempt in range(3):
            try:
                index.upsert(vectors=vectors_to_upsert)
                upserted_count += len(vectors_to_upsert)
                print(f"[+] Upserted {len(vectors_to_upsert)} chunks to Pinecone.")
                break
            except Exception as e:
                print(f"[!] Upsert retry ({attempt+1}/3): {e}")
                time.sleep(3)

        # Gentle pacing between batches
        time.sleep(2)

    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"[+] Ingestion complete in {elapsed:.1f}s.")
    print(f"[+] Total new chunks successfully indexed: {upserted_count}/{total_chunks}")

    new_stats = index.describe_index_stats()
    print(f"[*] Final Pinecone total vector count: {new_stats.total_vector_count}")
    print("=" * 60)

if __name__ == "__main__":
    main()
