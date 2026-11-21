import os
import sys
import time
from dotenv import load_dotenv

# 1. Environment Loading
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
from pypdf import PdfReader

DOCS_DIR = r"c:\Users\laksh\OneDrive\Desktop\RaGMiniProject\medical_reference_docs"
INDEX_NAME = "rag-based-system-v3"
BATCH_SIZE = 25  # Paced for Google Free Tier (100 RPM limit)

DOC_METADATA = {
    "AIIMS_Standard_Treatment_Guidelines_Official.pdf": {
        "domain": "diseases",
        "source": "AIIMS_STG",
        "ui_label": "AIIMS Standard Treatment Guidelines"
    },
    "India_National_List_of_Essential_Medicines_2022_Official.pdf": {
        "domain": "medicines",
        "source": "MoHFW_NLEM",
        "ui_label": "National List of Essential Medicines (India)"
    },
    "MoHFW_National_Rabies_Prophylaxis_Guidelines_Official.pdf": {
        "domain": "injuries",
        "source": "MoHFW_Rabies",
        "ui_label": "MoHFW National Rabies Prophylaxis Guidelines"
    },
    "MoHFW_STG_Antimicrobial_Use_Official.pdf": {
        "domain": "medicines",
        "source": "MoHFW_Antimicrobial",
        "ui_label": "MoHFW Antimicrobial Stewardship & Treatment Guidelines"
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
    },
    "MoHFW_STG_Respiratory_Medicine_Official.pdf": {
        "domain": "diseases",
        "source": "MoHFW_Respiratory",
        "ui_label": "MoHFW Respiratory Medicine Treatment Guidelines"
    },
    "USMLE_NBME_Clinical_Laboratory_Reference_Guide.pdf": {
        "domain": "laboratory",
        "source": "USMLE_NBME",
        "ui_label": "USMLE/NBME Laboratory Reference Standards"
    },
    "WHO_Community_First_Aid_Response_PocketGuide_Official.pdf": {
        "domain": "general",
        "source": "WHO_FirstAid",
        "ui_label": "WHO Community First Aid Response Guide"
    },
    "WHO_Official_Burn_Management_Guidelines.pdf": {
        "domain": "injuries",
        "source": "WHO_Burns",
        "ui_label": "WHO Burn Management Guidelines"
    },
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

def main():
    print("=" * 60)
    print("  PRODUCTION CLINICAL KNOWLEDGE INGESTION (RATE-PACED)")
    print(f"  Target Pinecone Index: {INDEX_NAME}")
    print(f"  Source Documents Folder: {DOCS_DIR}")
    print("=" * 60)

    pc = Pinecone(api_key=PINECONE_KEY)
    index = pc.Index(INDEX_NAME)
    stats = index.describe_index_stats()
    print(f"[*] Connected to Pinecone. Existing vectors in index: {stats.total_vector_count}")

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
    files = sorted(os.listdir(DOCS_DIR))

    print(f"\n[*] Parsing {len(files)} curated files...")
    for filename in files:
        filepath = os.path.join(DOCS_DIR, filename)
        if not os.path.isfile(filepath):
            continue

        meta_info = DOC_METADATA.get(filename, {
            "domain": "general",
            "source": filename,
            "ui_label": filename.replace("_", " ").replace(".pdf", "").replace(".md", "")
        })

        if filename.endswith(".pdf"):
            reader = PdfReader(filepath)
            for page_num, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                if len(page_text.strip()) < 40:
                    continue
                page_chunks = splitter.split_text(page_text)
                for c_idx, c_text in enumerate(page_chunks):
                    chunk_id = f"{filename}_p{page_num}_c{c_idx}"
                    all_chunks.append({
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
            doc_chunks = splitter.split_text(content)
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
    print(f"[+] Total chunks prepared: {total_chunks}")

    start_time = time.time()
    upserted_count = 0

    print(f"\n[*] Starting paced ingestion (Batch Size: {BATCH_SIZE})...")
    for i in range(0, total_chunks, BATCH_SIZE):
        batch = all_chunks[i:i + BATCH_SIZE]
        texts = [item["text"] for item in batch]
        ids = [item["id"] for item in batch]
        metadatas = [item["metadata"] for item in batch]

        # Generate Embeddings with 429 adaptive backoff
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
                    print(f"\n[!] Embedding error: {e}. Retrying in 5s...")
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
                time.sleep(3)

        elapsed = time.time() - start_time
        pct = (upserted_count / total_chunks) * 100
        print(f"[->] Ingested {upserted_count}/{total_chunks} ({pct:.1f}%) | Time: {int(elapsed)}s")

        # Free tier pacing: 1.2s delay between batches keeps us safely under 100 RPM
        time.sleep(1.2)

    print("\n" + "=" * 60)
    final_stats = index.describe_index_stats()
    print(f"[+] INGESTION COMPLETE! Total vectors in Pinecone: {final_stats.total_vector_count}")
    print(f"[+] Total Time: {int(time.time() - start_time)} seconds")
    print("=" * 60)

if __name__ == "__main__":
    main()
