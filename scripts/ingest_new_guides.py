import os
import sys
import time
from dotenv import load_dotenv

ENV_PATH = r"c:\Users\laksh\OneDrive\Desktop\RaGMiniProject\.env"
load_dotenv(ENV_PATH)

PINECONE_KEY = os.environ.get("PINECONE_API_KEY", "").strip(' "\t\r\n')
GOOGLE_KEY = os.environ.get("GOOGLE_API_KEY", "").strip(' "\t\r\n')

if not PINECONE_KEY or not GOOGLE_KEY:
    print("[-] Error: Missing PINECONE_API_KEY or GOOGLE_API_KEY in .env")
    sys.exit(1)

from pinecone import Pinecone
from langchain_google_genai import GoogleGenerativeAIEmbeddings

DOCS_DIR = r"c:\Users\laksh\OneDrive\Desktop\RaGMiniProject\medical_reference_docs"
INDEX_NAME = "rag-based-system-v3"
BATCH_SIZE = 15

TARGET_FILES = {
    "Clinical_Drug_Interactions_and_Contraindications_Guide.md": {
        "domain": "medicines",
        "source": "Clinical_Drug_Interactions_Guide",
        "ui_label": "Clinical Drug-Drug & Food Interactions Guide (WHO/BNF)"
    },
    "Outpatient_Disease_Protocols_and_Treatment_Targets_Guide.md": {
        "domain": "diseases",
        "source": "Outpatient_Disease_Protocols_Guide",
        "ui_label": "Outpatient Chronic Disease Protocols (ACC/ADA/GINA/GOLD)"
    },
    "Emergency_Clinical_Red_Flags_and_Hospital_Triage_Protocols.md": {
        "domain": "general",
        "source": "Emergency_Red_Flags_Triage_Protocols",
        "ui_label": "Emergency Red Flags & Hospital Triage Protocols (AHA/IMCI/ACEP)"
    },
    "Patient_Medicine_Administration_Food_Timings_and_Missed_Dose_Guide.md": {
        "domain": "medicines",
        "source": "Medicine_Administration_and_Missed_Dose_Guide",
        "ui_label": "Patient Medication Administration & Missed Dose Protocols (IPC/NHS)"
    },
    "ICMR_Patient_Diet_and_Lifestyle_Management_Guidelines.md": {
        "domain": "general",
        "source": "ICMR_Diet_Guidelines",
        "ui_label": "ICMR Patient Diet & Lifestyle Management Guidelines"
    },
    "Outpatient_First_Aid_Pediatric_Care_and_Red_Flags_Guide.md": {
        "domain": "general",
        "source": "Pediatric_First_Aid_Guide",
        "ui_label": "Outpatient First Aid & Pediatric Care Guide"
    },
    "Patient_Guide_to_Diagnostic_Scans_and_Lab_Preparation.md": {
        "domain": "laboratory",
        "source": "Diagnostic_Scans_Prep_Guide",
        "ui_label": "Diagnostic Scans & Lab Test Preparation Guide"
    },
    "Practical_Medicine_Administration_and_Pregnancy_Safety_Guide.md": {
        "domain": "medicines",
        "source": "Pregnancy_Safety_Guide",
        "ui_label": "Medication Administration & Pregnancy Safety Guide"
    }
}


def split_markdown_into_chunks(text: str, max_chunk_size: int = 850) -> list[str]:
    """
    Intelligent Markdown chunker that preserves clinical headers, tables, and bullet points.
    """
    chunks = []
    sections = text.split("\n## ")
    for s_idx, sec in enumerate(sections):
        if not sec.strip():
            continue
        if s_idx > 0:
            sec = "## " + sec

        if len(sec) <= max_chunk_size:
            if len(sec.strip()) > 30:
                chunks.append(sec.strip())
        else:
            paragraphs = sec.split("\n\n")
            current_chunk = ""
            for p in paragraphs:
                p_clean = p.strip()
                if not p_clean:
                    continue
                if len(current_chunk) + len(p_clean) + 2 <= max_chunk_size:
                    current_chunk = (current_chunk + "\n\n" + p_clean).strip()
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    if len(p_clean) > max_chunk_size:
                        lines = p_clean.split("\n")
                        sub = ""
                        for l in lines:
                            if len(sub) + len(l) + 1 <= max_chunk_size:
                                sub = (sub + "\n" + l).strip()
                            else:
                                if sub:
                                    chunks.append(sub)
                                sub = l
                        if sub:
                            chunks.append(sub)
                        current_chunk = ""
                    else:
                        current_chunk = p_clean
            if current_chunk:
                chunks.append(current_chunk)
    return chunks


def main():
    print("=" * 65)
    print("  INGESTING NEW CLINICAL KNOWLEDGE GUIDES INTO PINECONE")
    print(f"  Target Index: {INDEX_NAME}")
    print(f"  Target Files Count: {len(TARGET_FILES)}")
    print("=" * 65)

    pc = Pinecone(api_key=PINECONE_KEY)
    index = pc.Index(INDEX_NAME)
    stats_before = index.describe_index_stats()
    print(f"[*] Current vectors in Pinecone index: {stats_before.total_vector_count}")

    print("[*] Initializing Google Generative AI Embeddings (models/gemini-embedding-2)...")
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-2",
        google_api_key=GOOGLE_KEY
    )

    all_chunks = []
    for filename, meta in TARGET_FILES.items():
        filepath = os.path.join(DOCS_DIR, filename)
        if not os.path.exists(filepath):
            print(f"[-] File not found: {filename}")
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        doc_chunks = split_markdown_into_chunks(content)
        print(f"[+] Chunked {filename}: {len(doc_chunks)} clinical chunks")
        for c_idx, c_text in enumerate(doc_chunks):
            chunk_id = f"{filename}_c{c_idx}"
            all_chunks.append({
                "id": chunk_id,
                "text": c_text,
                "metadata": {
                    "text": c_text,
                    "domain": meta["domain"],
                    "source": meta["source"],
                    "document": filename,
                    "ui_label": meta["ui_label"],
                    "page": 1
                }
            })

    total_chunks = len(all_chunks)
    print(f"\n[*] Total new chunks to ingest: {total_chunks}")

    start_time = time.time()
    upserted_count = 0

    for i in range(0, total_chunks, BATCH_SIZE):
        batch = all_chunks[i:i + BATCH_SIZE]
        texts = [item["text"] for item in batch]
        ids = [item["id"] for item in batch]
        metadatas = [item["metadata"] for item in batch]

        embedded_vectors = None
        for attempt in range(5):
            try:
                embedded_vectors = embeddings.embed_documents(texts)
                break
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    wait_time = 18 + (attempt * 5)
                    print(f"\n[!] Rate limit (429) hit. Pacing pause for {wait_time}s (attempt {attempt+1}/5)...")
                    time.sleep(wait_time)
                else:
                    print(f"\n[!] Embedding notice: {e}. Retrying in 5s...")
                    time.sleep(5)

        if not embedded_vectors:
            print(f"\n[-] Skipping batch {i} due to unrecoverable embedding error.")
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
                break
            except Exception as e:
                print(f"[!] Upsert retry {attempt+1}: {e}")
                time.sleep(3)

        elapsed = time.time() - start_time
        pct = (upserted_count / total_chunks) * 100
        print(f"[->] Upserted {upserted_count}/{total_chunks} ({pct:.1f}%) | Time: {int(elapsed)}s")
        time.sleep(1.2)

    print("\n" + "=" * 65)
    stats_after = index.describe_index_stats()
    print(f"[+] INGESTION COMPLETE! Vectors in Pinecone: {stats_after.total_vector_count} (New vectors added: {stats_after.total_vector_count - stats_before.total_vector_count})")
    print(f"[+] Total Time: {int(time.time() - start_time)} seconds")
    print("=" * 65)

if __name__ == "__main__":
    main()
