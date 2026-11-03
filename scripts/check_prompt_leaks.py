"""
Continuous Integration Leak Checker.
Fails the build if System_Prompt.py, main.py, or medical_vision_pipeline.py contain
any leaked drug names or prompt illustration phrases from test prescription images.
Also asserts that drug_lookup.py contains zero hand-fitted test case entries.
"""

import sys
import os
import re

FORBIDDEN_PROMPT_PHRASES = [
    "sitex",
    "act ds",
    "actas",
    "porbloc",
    "prolere",
    "recel",
    "phylax",
    "glusphase",
    "gluophage",
    "catoflon",
    "cotufer",
    "zehil",
    "zedil",
    "thick white liquid suspension",
    "dry powder bottle you mix with water",
    "malaria vs typhoid",
    "liquid gel vs powder syrup",
    "line 4 is a 10ml liquid"
]

FORBIDDEN_DATABASE_KEYS = [
    "sitex",
    "actas",
    "albenda",
    "porbloc",
    "prolere",
    "recel",
    "phylax",
    "glusphase",
    "catoflon"
]

FILES_TO_CHECK = [
    "System_Prompt.py",
    "main.py",
    "medical_vision_pipeline.py"
]

def run_leak_check() -> int:
    leaks_found = 0
    print("=" * 60)
    print("RUNNING PROMPT & CODEBASE LEAK VERIFICATION")
    print("=" * 60)

    # 1. Check prompt & pipeline files for leaked phrases
    for filepath in FILES_TO_CHECK:
        if not os.path.exists(filepath):
            print(f"Warning: File {filepath} not found.")
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, start=1):
            line_lower = line.lower()
            for phrase in FORBIDDEN_PROMPT_PHRASES:
                if phrase in line_lower:
                    print(f"❌ LEAK DETECTED in {filepath}:{line_num}")
                    print(f"   Offending text: '{phrase}'")
                    print(f"   Line content  : {line.strip()[:100]}")
                    leaks_found += 1

    # 2. Check drug_lookup.py for hand-fitted test brands
    try:
        sys.path.insert(0, ".")
        from drug_lookup import BRAND_DATABASE
        for key in FORBIDDEN_DATABASE_KEYS:
            if key in BRAND_DATABASE:
                print(f"❌ HAND-FITTED TEST ENTRY IN BRAND_DATABASE: '{key}' -> {BRAND_DATABASE[key]}")
                leaks_found += 1
        print(f"Verified BRAND_DATABASE: {len(BRAND_DATABASE)} canonical registered brands.")
    except Exception as e:
        print(f"❌ Error loading BRAND_DATABASE: {e}")
        leaks_found += 1

    print("-" * 60)
    if leaks_found > 0:
        print(f"FAILED: {leaks_found} leak(s) found across prompt and codebase files!")
        return 1
    else:
        print("PASSED: 0 leaks found. All prompts, code, and drug databases are 100% clean and non-fitted.")
        return 0

if __name__ == "__main__":
    sys.exit(run_leak_check())
