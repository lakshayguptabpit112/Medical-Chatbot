import os
import sys
import time
import json
from dotenv import load_dotenv

env_path = r"c:\Users\laksh\OneDrive\Desktop\RaGMiniProject\.env"
load_dotenv(env_path)

PINECONE_KEY = os.environ.get("PINECONE_API_KEY", "").strip(' "\t\r\n')
GOOGLE_KEY = os.environ.get("GOOGLE_API_KEY", "").strip(' "\t\r\n')

from pinecone import Pinecone
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

DOCS_DIR = r"c:\Users\laksh\OneDrive\Desktop\RaGMiniProject\medical_reference_docs"
CHECKPOINT_PATH = os.path.join(DOCS_DIR, ".ingestion_checkpoint.json")
INDEX_NAME = "rag-based-system-v3"
BATCH_SIZE = 20

DOC_METADATA = {
    "Clinical_Laboratory_Reference_Intervals_ICMR_AIIMS.md": {
        "domain": "laboratory",
        "source": "ICMR_AIIMS_Standard",
        "ui_label": "ICMR/AIIMS Laboratory Reference Intervals & Panic Values"
    },
    "Indian_Outpatient_Pharmacopeia_Brands_and_Food_Timings.md": {
        "domain": "medicines",
        "source": "Indian_Pharmacopeia",
        "ui_label": "Indian Outpatient Drug Brands & Food Timing Pharmacopeia"
    },
    "WHO_Official_Burn_Management_Guidelines.pdf": {
        "domain": "injuries",
        "source": "WHO_Burns",
        "ui_label": "WHO Burn Management Guidelines"
    },
    "WHO_Community_First_Aid_Response_PocketGuide_Official.pdf": {
        "domain": "general",
        "source": "WHO_FirstAid",
        "ui_label": "WHO Community First Aid Response Guide"
    },
    "MoHFW_National_Rabies_Prophylaxis_Guidelines_Official.pdf": {
        "domain": "injuries",
        "source": "MoHFW_Rabies",
        "ui_label": "MoHFW National Rabies Prophylaxis Guidelines"
    },
    "India_National_List_of_Essential_Medicines_2022_Official.pdf": {
        "domain": "medicines",
        "source": "MoHFW_NLEM",
        "ui_label": "National List of Essential Medicines (India)"
    },
    "USMLE_NBME_Clinical_Laboratory_Reference_Guide.pdf": {
        "domain": "laboratory",
        "source": "USMLE_NBME",
        "ui_label": "USMLE/NBME Laboratory Reference Standards"
    },
    "MoHFW_STG_Antimicrobial_Use_Official.pdf": {
        "domain": "medicines",
        "source": "MoHFW_Antimicrobial",
        "ui_label": "MoHFW Antimicrobial Stewardship & Treatment Guidelines"
    },
    "MoHFW_STG_Respiratory_Medicine_Official.pdf": {
        "domain": "diseases",
        "source": "MoHFW_Respiratory",
        "ui_label": "MoHFW Respiratory Medicine Treatment Guidelines"
    },
    "MoHFW_STG_Diabetic_Foot_Wound_Official.pdf": {
        "domain": "injuries",
        "source": "MoHFW_DiabeticFoot",
        "ui_label": "MoHFW Diabetic Foot & Wound Management Guidelines"
    },
    "MoHFW_STG_Major_Trauma_Official.pdf": {
        "domain": "injuries",
        "source": "MoHFW_Trauma",
        "ui_label": "MoHFW Major Trauma & Hemorrhage Guidelines"
    }
}

def load_checkpoint():
    if os.path.exists(CHECKPOINT_PATH):
        try:
            with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "completed_files": [],
        "current_file": None,
        "completed_batches_for_current_file": []
    }

def save_checkpoint(ckpt):
    try:
        with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
            json.dump(ckpt, f, indent=2)
    except Exception as e:
        print(f"[!] Warning: Failed to save checkpoint: {e}", flush=True)

def main():
    pc = Pinecone(api_key=PINECONE_KEY)
    index = pc.Index(INDEX_NAME)
    initial_count = index.describe_index_stats().total_vector_count
    print(f"[*] Resilient Ingestion Engine. Pinecone vectors currently: {initial_count}", flush=True)

    ckpt = load_checkpoint()
    completed_files = set(ckpt.get("completed_files", []))
    print(f"[*] Found checkpoint: {len(completed_files)} files already completed.", flush=True)

    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-2",
        google_api_key=GOOGLE_KEY,
        request_timeout=30.0
    )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""]
    )

    priority_order = [
        "Clinical_Laboratory_Reference_Intervals_ICMR_AIIMS.md",
        "Indian_Outpatient_Pharmacopeia_Brands_and_Food_Timings.md",
        "WHO_Official_Burn_Management_Guidelines.pdf",
        "WHO_Community_First_Aid_Response_PocketGuide_Official.pdf",
        "MoHFW_National_Rabies_Prophylaxis_Guidelines_Official.pdf",
        "India_National_List_of_Essential_Medicines_2022_Official.pdf",
        "USMLE_NBME_Clinical_Laboratory_Reference_Guide.pdf",
        "MoHFW_STG_Antimicrobial_Use_Official.pdf",
        "MoHFW_STG_Respiratory_Medicine_Official.pdf",
        "MoHFW_STG_Diabetic_Foot_Wound_Official.pdf",
        "MoHFW_STG_Major_Trauma_Official.pdf"
    ]

    for filename in priority_order:
        if filename in completed_files:
            print(f"[DONE] {filename} is already fully ingested. Skipping.", flush=True)
            continue

        filepath = os.path.join(DOCS_DIR, filename)
        if not os.path.exists(filepath):
            continue

        meta_info = DOC_METADATA.get(filename, {"domain": "general", "source": filename, "ui_label": filename})
        doc_chunks = []

        if filename.endswith(".pdf"):
            reader = PdfReader(filepath)
            for page_num, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                if len(page_text.strip()) < 40:
                    continue
                chunks = splitter.split_text(page_text)
                for c_idx, c_text in enumerate(chunks):
                    chunk_id = f"{filename}_p{page_num}_c{c_idx}"
                    doc_chunks.append({
                        "id": chunk_id,
                        "text": c_text,
                        "metadata": {
                            "text": c_text,
                            "domain": meta_info["domain"],
                            "source": meta_info["source"],
                            "document": filename,
                            "ui_label": meta_info["ui_label"],
                            "page": page_num
                        }
                    })
        elif filename.endswith(".md"):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            chunks = splitter.split_text(content)
            for c_idx, c_text in enumerate(chunks):
                chunk_id = f"{filename}_c{c_idx}"
                doc_chunks.append({
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

        print(f"\n[+] Ingesting {filename} ({len(doc_chunks)} chunks, domain: {meta_info['domain']})...", flush=True)
        ckpt["current_file"] = filename
        completed_batches = set(ckpt.get("completed_batches_for_current_file", [])) if ckpt.get("current_file") == filename else set()

        file_fully_done = True
        batch_idx = 0
        for i in range(0, len(doc_chunks), BATCH_SIZE):
            batch_idx += 1
            if batch_idx in completed_batches:
                print(f"  [DONE] Batch {batch_idx} previously ingested. Skipping.", flush=True)
                continue

            batch = doc_chunks[i:i + BATCH_SIZE]
            texts = [b["text"] for b in batch]
            ids = [b["id"] for b in batch]
            metadatas = [b["metadata"] for b in batch]

            vectors = None
            daily_quota_hit = False
            for attempt in range(6):
                try:
                    vectors = embeddings.embed_documents(texts)
                    break
                except Exception as e:
                    err_msg = str(e)
                    if "per day" in err_msg.lower() or "requestsperday" in err_msg.lower():
                        print(f"  [!] Daily quota reached: {err_msg[:140]}...", flush=True)
                        daily_quota_hit = True
                        break
                    elif "429" in err_msg or "resource_exhausted" in err_msg.lower():
                        wait_sec = 42 + (attempt * 10)
                        print(f"  [!] Per-minute rate limit hit. Sleeping {wait_sec}s for window reset (attempt {attempt+1}/6)...", flush=True)
                        time.sleep(wait_sec)
                    else:
                        print(f"  [!] Embedding error: {err_msg[:140]}... retrying in 10s...", flush=True)
                        time.sleep(10)

            if daily_quota_hit or not vectors:
                print(f"\n[!] Quota paused at {filename} (Batch {batch_idx}). Saving checkpoint...", flush=True)
                save_checkpoint(ckpt)
                file_fully_done = False
                print("[*] State cleanly saved. Run this script again after quota reset to resume seamlessly from this exact batch.", flush=True)
                return

            upserts = []
            for vid, vec, meta in zip(ids, vectors, metadatas):
                upserts.append({"id": vid, "values": vec, "metadata": meta})

            for _ in range(3):
                try:
                    index.upsert(vectors=upserts)
                    break
                except Exception:
                    time.sleep(3)

            completed_batches.add(batch_idx)
            ckpt["completed_batches_for_current_file"] = list(completed_batches)
            save_checkpoint(ckpt)

            print(f"  -> Upserted batch {batch_idx} ({min(i + BATCH_SIZE, len(doc_chunks))}/{len(doc_chunks)} chunks)", flush=True)
            time.sleep(2.5)  # Safe free tier pacing

        if file_fully_done:
            completed_files.add(filename)
            ckpt["completed_files"] = list(completed_files)
            ckpt["current_file"] = None
            ckpt["completed_batches_for_current_file"] = []
            save_checkpoint(ckpt)
            print(f"[DONE] Completed {filename}!", flush=True)

    final_count = index.describe_index_stats().total_vector_count
    print(f"\n[+] ALL CURATED REFERENCE DOCS INGESTED! Pinecone total vectors: {final_count}", flush=True)

if __name__ == "__main__":
    main()
