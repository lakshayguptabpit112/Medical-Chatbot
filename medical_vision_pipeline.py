"""
Medical Vision Pipeline (2026) - Clinical Multimodal Intelligence Engine
--------------------------------------------------------------------------
Stage 0: Multimodal Perception (Verbatim OCR + Clinical Entities + Pharmacist Disambiguation)
Stage 2: Resilient Vector Retrieval from Pinecone (Concurrent asyncio.gather)
"""

import asyncio
import base64
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import HumanMessage
from llm_factory import get_llm
from System_Prompt import (
    UNIVERSAL_PERCEPTION_PROMPT,
    PERCEPTION_USER_CONTEXT_TEMPLATE,
)
from storage import preprocess_medical_image
from drug_lookup import resolve_brand


# ==============================================================================
# 1. UNIVERSAL MULTIMODAL EXTRACTION HELPERS
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
    Executes the pure LLM Universal Perception & Extraction step (Stage 0).
    Produces the complete structured clinical transcript without hallucinating diagnoses.
    """
    llm = get_llm(temperature=0.0)
    
    # Preprocess image if not a PDF document (90-95% compression + EXIF rotation fix)
    if mime_type != "application/pdf":
        image_bytes = preprocess_medical_image(image_bytes)
        mime_type = "image/jpeg"

    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    user_context_block = PERCEPTION_USER_CONTEXT_TEMPLATE.format(
        user_question=user_question.strip() if user_question else "Please transcribe and extract all clinical entities from this medical document completely."
    )

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



def format_full_visual_transcript(perception_data: Dict[str, Any]) -> str:
    """
    Formats the authentic multimodal perception data into a lossless clinical text document.
    Enriches handwritten brand names with deterministic drug_lookup resolution.
    Stored directly into ChatDocument.ocr_text for Stage 1 & Stage 3 context.
    """
    media_info = perception_data.get("media_classification", {})
    category = media_info.get("primary_category", "general_medical_document")
    desc = media_info.get("description", "")
    
    parts = [
        f"Document Classification: {category} ({desc})"
    ]
    
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

    # 2. Prescriptions / Medicines (enriched with drug_lookup resolver)
    raw_meds = entities.get("prescribed_medications", [])
    if raw_meds:
        enriched_meds = []
        for m in raw_meds:
            item = dict(m)
            raw_brand = item.get("brand_as_written") or item.get("raw_text") or ""
            
            disambig = item.get("disambiguation") or {}
            raw_conf = str(disambig.get("confidence") or "clear").lower()
            conf_map = {
                "high_certainty": "clear",
                "clinical_deduction": "partial",
                "unclear_scribble": "guess"
            }
            reading_flag = conf_map.get(raw_conf, raw_conf)
            candidates = disambig.get("alternative_candidates") or []
            
            lookup = resolve_brand(raw_brand, reading=reading_flag, spelling_candidates=candidates)
            if lookup.get("status") == "resolved":
                item["resolved_generic_salt"] = lookup["salt"]
                item["pharmacological_class"] = lookup["pharmacological_class"]
                item["clinical_indication"] = lookup.get("clinical_indication") or lookup.get("typical_use") or item.get("purpose")
                item["typical_use"] = lookup.get("typical_use") or lookup.get("clinical_indication") or item.get("purpose")
                if lookup.get("suffix_warning"):
                    item["suffix_warning"] = lookup["suffix_warning"]
                item["provenance"] = {
                    "status": "VERIFIED_DATABASE_MATCH",
                    "source": "Indian Pharmacopoeia Database (50k+ formulations)",
                    "matched_brand": lookup.get("brand"),
                    "database_salt": lookup.get("salt"),
                    "pharmacological_class": lookup.get("pharmacological_class")
                }
            elif lookup.get("status") == "candidates":
                item["candidate_matches"] = lookup.get("candidate_matches") or lookup.get("options", [])
                if lookup.get("suffix_warning"):
                    item["suffix_warning"] = lookup["suffix_warning"]
                if item.get("generic_name"):
                    item["resolved_generic_salt"] = item["generic_name"]
                    item["pharmacological_class"] = item.get("therapeutic_category") or "Prescription Medication"
                    item["clinical_indication"] = item.get("purpose")
                item["provenance"] = {
                    "status": "CANDIDATE_MATCHES_AVAILABLE",
                    "source": "Indian Pharmacopoeia Database (50k+ formulations)",
                    "candidate_options": lookup.get("candidate_matches") or lookup.get("options", []),
                    "model_deduced_generic": item.get("generic_name")
                }
            else:
                if item.get("generic_name"):
                    item["resolved_generic_salt"] = item["generic_name"]
                    item["pharmacological_class"] = item.get("therapeutic_category") or "Prescription Medication"
                    item["clinical_indication"] = item.get("purpose")
                    item["typical_use"] = item.get("purpose")
                    item["provenance"] = {
                        "status": "CLINICAL_MODEL_DEDUCTION",
                        "source": "Perception Model Clinical Inference",
                        "inferred_generic": item.get("generic_name"),
                        "therapeutic_category": item.get("therapeutic_category")
                    }
                else:
                    item["verification_note"] = "Unconfirmed brand name; verify composition line on physical packaging"
                    item["provenance"] = {
                        "status": "UNRESOLVED",
                        "source": "Ambiguous Handwriting",
                        "note": "Unconfirmed brand name; requires verification against physical packaging or pharmacist consultation."
                    }
            enriched_meds.append(item)
        parts.append(f"Prescribed Medications & Dosages:\n{json.dumps(enriched_meds, indent=2)}")

    # 3. Blood / Laboratory Results Table (Preserves on-page lab results from vision OCR)
    labs = entities.get("laboratory_results_table", [])
    if labs:
        parts.append(f"Laboratory Results Table:\n{json.dumps(labs, indent=2)}")
        
    # 4. Wounds / Trauma / Skin Lesions / Animal Bites / Burns
    wounds = entities.get("wound_or_skin_assessment", {})
    if wounds and (wounds.get("is_trauma_present") or wounds.get("visual_characteristics")):
        parts.append(f"Wound / Skin / Trauma Assessment:\n{json.dumps(wounds, indent=2)}")
        
    # 5. Diagnostic Scans & Investigations Ordered by Doctor
    investigations = entities.get("diagnostic_investigations_ordered", [])
    if investigations:
        parts.append(f"Diagnostic Investigations Ordered:\n{json.dumps(investigations, indent=2)}")

    # 6. Patient Context, Symptoms, and On-Examination (O/E) Findings
    if context_list:
        parts.append(f"Documented Symptoms & Clinical History:\n{json.dumps(context_list, indent=2)}")

    # 7. General Clinical, Health, Dietary, and Device Observations
    general_obs = entities.get("general_clinical_and_health_observations", {})
    if general_obs and (general_obs.get("observed_findings") or general_obs.get("key_medical_search_terms")):
        parts.append(f"General Clinical & Health Observations:\n{json.dumps(general_obs, indent=2)}")

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
    Returns: (rag_context_str, sources_list, is_quota_paused)
    """
    if not retriever or not queries:
        return "", [], False

    target_queries = [q.strip() for q in queries if q.strip()][:6]
    if not target_queries:
        return "", [], False

    async def _fetch_query_chunks(q: str):
        try:
            docs = await asyncio.to_thread(retriever.invoke, q)
            return q, docs, None
        except Exception as e:
            try:
                docs = await retriever.ainvoke(q)
                return q, docs, None
            except Exception as e2:
                return q, [], e2

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
            source_gaps.append(q)
            continue

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

    if source_gaps:
        context_blocks.append(f"<source_gaps>No verified textbook entry retrieved for: {'; '.join(source_gaps)}</source_gaps>")

    rag_context = "\n\n---\n\n".join(context_blocks)
    return rag_context, sources_list[:8], is_quota_paused
