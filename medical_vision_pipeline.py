"""
Medical Vision Pipeline (2026) - Clinical Multimodal Intelligence Engine
--------------------------------------------------------------------------
Step 1: Multi-Modal Lossless Perception (Verbatim OCR + Clinical Entities)
Step 2: Dynamic Clinical Query Generation (Targeted for RAG Vector Index)
Step 3: Resilient Vector Retrieval from Pinecone (Concurrent asyncio.gather)
"""

import asyncio
import base64
import io
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from PIL import Image, ImageOps

load_dotenv()

from langchain_core.messages import HumanMessage, SystemMessage
from llm_factory import get_llm
from System_Prompt import (
    UNIVERSAL_PERCEPTION_PROMPT,
    SYNTHESIS_SYSTEM_PROMPT
)


# ==============================================================================
# 0. IMAGE PRE-PROCESSING QUALITY GATE
# ==============================================================================

def preprocess_medical_image(image_bytes: bytes, max_dimension: int = 2048) -> bytes:
    """
    Fixes EXIF orientation from mobile phone cameras, downscales very large images
    to a medically clear ~2048px bounding box, and strips extraneous metadata.
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            # Auto-rotate based on EXIF tag (mobile portrait/landscape capture)
            img = ImageOps.exif_transpose(img)

            # Normalize palette/RGBA to RGB for safe JPEG output
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            # Downscale if wider or taller than max_dimension
            w, h = img.size
            if max(w, h) > max_dimension:
                scale = max_dimension / max(w, h)
                new_size = (int(w * scale), int(h * scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            output = io.BytesIO()
            img.save(output, format="JPEG", quality=88, optimize=True)
            return output.getvalue()
    except Exception as e:
        print(f"[IMAGE PREPROCESSING NOTICE]: {e}")
        return image_bytes  # Safely fall back to original bytes if unhandled format


# ==============================================================================
# 1. UNIVERSAL LOSSLESS MULTIMODAL EXTRACTION
# ==============================================================================

def extract_text_from_langchain_content(content: Any) -> str:
    """Safely normalizes LangChain content into a clean string."""
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


async def run_universal_medical_perception(
    image_bytes: bytes,
    mime_type: str,
    user_question: str
) -> Dict[str, Any]:
    """
    Executes the pure LLM Universal Perception & Extraction step.
    Produces the complete structured clinical transcript without hallucinating diagnoses.
    """
    llm = get_llm(temperature=0.0)
    
    # Preprocess image if not a PDF document
    if mime_type != "application/pdf":
        image_bytes = preprocess_medical_image(image_bytes)
        mime_type = "image/jpeg"

    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    user_context_block = f"""
USER'S REQUEST OR CLINICAL INQUIRY:
"{user_question.strip() if user_question else 'Please transcribe and extract all clinical entities from this medical document completely.'}"
(CRITICAL EXTRACTION DIRECTIVE: Transcribe ONLY what is objectively visible on the page. Do NOT let user guesses or questions bias your verbatim reading.)
"""

    prompt = f"{UNIVERSAL_PERCEPTION_PROMPT}\n\n{user_context_block}"

    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": f"data:{mime_type};base64,{b64_image}"
            }
        ]
    )

    for attempt in range(2):
        try:
            response = await llm.ainvoke([message])
            raw_text = extract_text_from_langchain_content(response.content)

            # Robust JSON block extraction (handles markdown fences, preamble, or trailing prose)
            match = re.search(r'\{[\s\S]*\}', raw_text)
            clean_json_str = match.group(0) if match else raw_text.strip()

            parsed_data = json.loads(clean_json_str)
            return parsed_data
        except Exception as e:
            print(f"[UNIVERSAL PERCEPTION EXTRACTION ATTEMPT {attempt + 1} NOTICE]: {e}")
            if attempt == 0:
                await asyncio.sleep(1.0)
                continue

    # Graceful fallback ONLY if both attempts fail
    return {
        "media_classification": {"primary_category": "unreadable_document", "description": "Unclear medical file"},
        "document_metadata": {"document_date": None, "issuer": None, "patient_demographics": None},
        "lossless_verbatim_transcription": {
            "full_raw_text": "",
            "ambiguous_or_unclear_scribbles": []
        },
        "syntactic_clinical_entities": {
            "patient_context_and_history": [],
            "diagnostic_investigations_ordered": [],
            "prescribed_medications": [],
            "wound_or_skin_assessment": {"is_trauma_present": False},
            "laboratory_results_table": []
        },
        "error_fallback": True
    }


TIERED_LAB_REGEX = re.compile(
    r'borderline|desirable|optimal|deficien|insufficien|prediab|\b(male|female|men|women|child|adult)\b|\b[MF]\s*[:\-]',
    re.IGNORECASE
)

def compute_lab_status(observed_val_str: Any, ref_range_str: Any) -> str | None:
    """
    Computes High / Low / Normal status deterministically from numeric values and reference intervals.
    Prevents the LLM from hallucinating or inverting laboratory test results.
    Returns None if the range is complex, tiered, sex/age-dependent, or cannot be parsed unambiguously.
    """
    if not observed_val_str or not ref_range_str:
        return None
    try:
        val_clean = str(observed_val_str).strip().replace(",", "")
        val_match = re.search(r"[-+]?\d*\.?\d+", val_clean)
        if not val_match:
            return None
        val = float(val_match.group(0))

        range_clean = str(ref_range_str).strip().replace("≥", ">=").replace("≤", "<=").replace(",", "")
        
        # Guard against tiered, demographic, or multi-interval ranges
        if TIERED_LAB_REGEX.search(range_clean) or len(re.findall(r'\d+\.?\d*', range_clean)) > 2:
            return None

        # 1. Low - High interval (e.g. '11.5 - 15.0', '70 to 110', '135-145')
        interval_match = re.search(r"([-+]?\d*\.?\d+)\s*(?:-|to|–|—)\s*([-+]?\d*\.?\d+)", range_clean)
        if interval_match:
            low = float(interval_match.group(1))
            high = float(interval_match.group(2))
            if val < low:
                return "Low"
            elif val > high:
                return "High"
            else:
                return "Normal"

        # 2. Upper bound only (e.g. '< 100', '<= 200', 'less than 150')
        upper_match = re.search(r"(?:<=|<|less than|up to)\s*([-+]?\d*\.?\d+)", range_clean, re.IGNORECASE)
        if upper_match:
            high = float(upper_match.group(1))
            return "High" if val > high else "Normal"

        # 3. Lower bound only (e.g. '> 60', '>= 50', 'greater than 40')
        lower_match = re.search(r"(?:>=|>|greater than|more than)\s*([-+]?\d*\.?\d+)", range_clean, re.IGNORECASE)
        if lower_match:
            low = float(lower_match.group(1))
            return "Low" if val < low else "Normal"

    except Exception:
        pass
    return None


def format_full_visual_transcript(perception_data: Dict[str, Any]) -> str:
    """
    Formats the authentic multimodal perception data into a lossless clinical text document.
    CRITICAL: Preserves strictly on-page facts (OCR, medications, dosages, lab values, wound features).
    Enriches handwritten brand names with deterministic code-side brand-to-salt resolution.
    Excludes model-guessed diagnoses or ungrounded inferences.
    """
    from drug_lookup import resolve_brand

    media_info = perception_data.get("media_classification", {})
    category = media_info.get("primary_category", "general_medical_document")
    desc = media_info.get("description", "")
    
    parts = [
        f"Document Classification: {category} ({desc})"
    ]
    
    # Document Date & Issuer if visible
    doc_meta = perception_data.get("document_metadata", {})
    doc_date = doc_meta.get("document_date")
    issuer = doc_meta.get("issuer")
    if doc_date:
        parts.append(f"Document Date: {doc_date}")
    if issuer:
        parts.append(f"Issuing Doctor / Clinic: {issuer}")

    entities = perception_data.get("syntactic_clinical_entities", {})
    context_list = entities.get("patient_context_and_history", [])
    
    # 1. Lossless Verbatim Text & Handwriting Ambiguities
    verbatim_info = perception_data.get("lossless_verbatim_transcription", {})
    raw_ocr = verbatim_info.get("full_raw_text", "")
    if raw_ocr:
        parts.append(f"Verbatim Document Text:\n{raw_ocr}")
        
    ambiguous_scribbles = verbatim_info.get("ambiguous_or_unclear_scribbles", [])
    if ambiguous_scribbles:
        parts.append(f"Ambiguous Handwriting & Unclear Notes:\n{json.dumps(ambiguous_scribbles, indent=2)}")

    # 2. Syntactic Clinical Entities (Prescriptions, Labs, Wounds, Tests, Symptoms)
    # Prescriptions / Medicines (enriched with deterministic code lookup)
    raw_meds = entities.get("prescribed_medications", [])
    if raw_meds:
        enriched_meds = []
        for m in raw_meds:
            item = dict(m)
            raw_brand = item.get("brand_as_written") or item.get("raw_text") or ""
            reading_flag = str(item.get("reading") or "clear").lower()
            candidates = item.get("spelling_candidates") or []
            lookup = resolve_brand(raw_brand, reading=reading_flag, spelling_candidates=candidates)
            if lookup.get("status") == "resolved":
                item["resolved_generic_salt"] = lookup["salt"]
                item["pharmacological_class"] = lookup["pharmacological_class"]
                item["clinical_indication"] = lookup.get("clinical_indication") or lookup.get("typical_use") or item.get("purpose")
                item["typical_use"] = lookup.get("typical_use") or lookup.get("clinical_indication") or item.get("purpose")
                if lookup.get("suffix_warning"):
                    item["suffix_warning"] = lookup["suffix_warning"]
            elif lookup.get("status") == "candidates":
                item["candidate_matches"] = lookup.get("candidate_matches") or lookup.get("options", [])
                if lookup.get("suffix_warning"):
                    item["suffix_warning"] = lookup["suffix_warning"]
                if item.get("generic_name"):
                    item["resolved_generic_salt"] = item["generic_name"]
                    item["pharmacological_class"] = item.get("therapeutic_category") or "Prescription Medication"
                    item["clinical_indication"] = item.get("purpose")
            else:
                # Top-Tier Clinical Pharmacist Vision decoding
                if item.get("generic_name"):
                    item["resolved_generic_salt"] = item["generic_name"]
                    item["pharmacological_class"] = item.get("therapeutic_category") or "Prescription Medication"
                    item["clinical_indication"] = item.get("purpose")
                    item["typical_use"] = item.get("purpose")
                else:
                    item["verification_note"] = "Unconfirmed brand name; verify composition line on physical packaging"
            enriched_meds.append(item)
        parts.append(f"Prescribed Medications & Dosages:\n{json.dumps(enriched_meds, indent=2)}")

    # Blood / Lab Results with deterministic status calculation
    labs = entities.get("laboratory_results_table", [])
    if labs:
        computed_labs = []
        for lab in labs:
            if isinstance(lab, dict):
                lab_copy = dict(lab)
                obs = lab_copy.get("observed_value")
                ref = lab_copy.get("printed_reference_range")
                existing_status = str(lab_copy.get("status") or "").strip().lower()
                # Do NOT overwrite Critical / Panic values with standard Normal/High/Low math
                if "critical" not in existing_status and "panic" not in existing_status:
                    computed_status = compute_lab_status(obs, ref)
                    if computed_status:
                        lab_copy["status"] = computed_status
                        lab_copy["status_determination"] = "Computed deterministically from printed reference range"
                computed_labs.append(lab_copy)
            else:
                computed_labs.append(lab)
        parts.append(f"Laboratory Results Table:\n{json.dumps(computed_labs, indent=2)}")
        
    # Wounds / Trauma / Skin Lesions / Animal Bites / Burns
    wounds = entities.get("wound_or_skin_assessment", {})
    if wounds and (wounds.get("is_trauma_present") or wounds.get("visual_characteristics")):
        parts.append(f"Wound / Skin / Trauma Assessment:\n{json.dumps(wounds, indent=2)}")
        
    # Diagnostic Scans & Investigations Ordered by Doctor
    investigations = entities.get("diagnostic_investigations_ordered", [])
    if investigations:
        parts.append(f"Diagnostic Investigations Ordered:\n{json.dumps(investigations, indent=2)}")

    # Patient Context, Symptoms, and On-Examination (O/E) Findings explicitly noted on document
    if context_list:
        parts.append(f"Documented Symptoms & Clinical History:\n{json.dumps(context_list, indent=2)}")

    return "\n\n".join(parts)


# ==============================================================================
# 2. CONCURRENT RESILIENT RAG RETRIEVAL WITH SOURCE GAP DETECTION
# ==============================================================================

async def retrieve_clinical_context(
    queries: List[str],
    retriever: Any
) -> Tuple[str, List[Dict[str, Any]], bool]:
    """
    Executes targeted RAG retrieval from the Pinecone vector index concurrently via asyncio.gather.
    Includes safe error-handling for rate limits, quota exhaustion (429), or network timeouts.
    Maintains balanced retrieval (top 2 chunks per entity) and outputs <source_gaps> for missing items.
    Returns: (rag_context_str, sources_list, is_quota_paused)
    """
    if not retriever or not queries:
        return "", [], False

    # Cap to maximum 6 high-yield queries for multi-topic clinical coverage
    target_queries = [q.strip() for q in queries if q.strip()][:6]
    if not target_queries:
        return "", [], False

    async def _fetch_query_chunks(q: str):
        try:
            docs = await retriever.ainvoke(q)
            return q, docs, None
        except Exception as e:
            return q, [], e

    # Concurrently execute all queries in parallel
    results = await asyncio.gather(*[_fetch_query_chunks(q) for q in target_queries])

    retrieved_docs = []
    seen_texts = set()
    sources_list: List[Dict[str, Any]] = []
    is_quota_paused = False
    source_gaps: List[str] = []

    for q, docs, err in results:
        if err:
            err_str = str(err).lower()
            if "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str:
                is_quota_paused = True
            print(f"[RAG RETRIEVAL NOTICE]: Quota/Retrieval pause for query '{q}': {err}")
            continue

        if not docs:
            # Note when no verified literature was found for this specific query target
            source_gaps.append(q)
            continue

        # Keep top 2 chunks per target query for balanced coverage
        for d in docs[:2]:
            text_snippet = d.page_content.strip()[:150]
            if text_snippet not in seen_texts:
                seen_texts.add(text_snippet)
                retrieved_docs.append((q, d))

                label = d.metadata.get("ui_label") or d.metadata.get("source") or "Clinical Reference"
                page = d.metadata.get("page")
                page_str = f" (Page {page})" if page else ""
                sources_list.append({
                    "kind": "medical_literature",
                    "page": f"{label}{page_str}",
                    "title": f"{label}{page_str}",
                    "text": d.page_content[:250] + "..."
                })

    if not retrieved_docs:
        return "", [], is_quota_paused

    context_blocks = []
    for idx, (query_target, doc) in enumerate(retrieved_docs[:8], 1):
        source_name = doc.metadata.get("ui_label") or doc.metadata.get("source") or "Clinical Reference"
        page = doc.metadata.get("page")
        page_info = f", Page {page}" if page else ""
        context_blocks.append(f"[Reference {idx} (Retrieved for: {query_target}) - {source_name}{page_info}]\n{doc.page_content.strip()}")

    # Append source gaps notice so Stage 3 knows which drugs/topics had no database monograph
    if source_gaps:
        context_blocks.append(f"<source_gaps>No verified textbook entry retrieved for: {'; '.join(source_gaps)}</source_gaps>")

    rag_context = "\n\n---\n\n".join(context_blocks)
    return rag_context, sources_list[:8], is_quota_paused
