import json
import os

with open("scripts/test_counts.py", "r", encoding="utf-8") as f:
    text = f.read()

local_scope = {}
exec(text, {}, local_scope)
generic_lexicon = local_scope["GENERIC_ENTRIES"]

with open("scripts/merge_brands.py", "r", encoding="utf-8") as f:
    text2 = f.read()

local_scope2 = {}
exec(text2, {}, local_scope2)
brands = local_scope2["current_brands"]

intl_brands = {
    "lipitor": {"salt": "atorvastatin", "class": "hmg-coa reductase inhibitor (statin)", "typical_use": "hypercholesterolemia and cardiovascular prevention"},
    "crestor": {"salt": "rosuvastatin", "class": "statin lipid-lowering agent", "typical_use": "dyslipidemia and plaque stabilization"},
    "zocor": {"salt": "simvastatin", "class": "statin", "typical_use": "hypercholesterolemia"},
    "plavix": {"salt": "clopidogrel", "class": "antiplatelet agent", "typical_use": "atherothrombosis prevention in stroke and heart attack"},
    "norvasc": {"salt": "amlodipine", "class": "calcium channel blocker", "typical_use": "hypertension and angina"},
    "zestril": {"salt": "lisinopril", "class": "ace inhibitor", "typical_use": "hypertension and heart failure"},
    "altace": {"salt": "ramipril", "class": "ace inhibitor", "typical_use": "hypertension and heart failure"},
    "cozaar": {"salt": "losartan", "class": "angiotensin II receptor blocker", "typical_use": "hypertension and diabetic nephropathy"},
    "hyzaar": {"salt": "losartan + hydrochlorothiazide", "class": "arb + diuretic combination", "typical_use": "hypertension"},
    "diovan": {"salt": "valsartan", "class": "angiotensin II receptor blocker", "typical_use": "hypertension and heart failure"},
    "lopressor": {"salt": "metoprolol tartrate", "class": "beta-1 blocker", "typical_use": "angina and hypertension"},
    "toprolxl": {"salt": "metoprolol succinate extended release", "class": "beta-1 blocker ER", "typical_use": "hypertension and heart failure"},
    "coreg": {"salt": "carvedilol", "class": "alpha/beta blocker", "typical_use": "heart failure and post-MI left ventricular dysfunction"},
    "singulair": {"salt": "montelukast sodium", "class": "leukotriene receptor antagonist", "typical_use": "asthma maintenance and allergic rhinitis"},
    "claritin": {"salt": "loratadine", "class": "second-generation antihistamine", "typical_use": "allergic rhinitis and urticaria"},
    "zyrtec": {"salt": "cetirizine", "class": "second-generation antihistamine", "typical_use": "allergic rhinitis and hives"},
    "allegra": {"salt": "fexofenadine", "class": "non-sedating antihistamine", "typical_use": "allergies and chronic urticaria"},
    "prilosec": {"salt": "omeprazole", "class": "proton pump inhibitor", "typical_use": "GERD, heartburn, and peptic ulcer"},
    "nexium": {"salt": "esomeprazole magnesium", "class": "proton pump inhibitor", "typical_use": "erosive esophagitis and acid reflux"},
    "prevacid": {"salt": "lansoprazole", "class": "proton pump inhibitor", "typical_use": "peptic ulcer and GERD"},
    "pepcid": {"salt": "famotidine", "class": "h2 receptor antagonist", "typical_use": "heartburn and hyperacidity"},
    "zofran": {"salt": "ondansetron", "class": "5-HT3 receptor antagonist antiemetic", "typical_use": "nausea and vomiting prevention"},
    "reglan": {"salt": "metoclopramide", "class": "prokinetic dopamine antagonist", "typical_use": "diabetic gastroparesis and GERD"},
    "ambien": {"salt": "zolpidem tartrate", "class": "sedative hypnotic (z-drug)", "typical_use": "short-term treatment of insomnia"},
    "xanax": {"salt": "alprazolam", "class": "triazolobenzodiazepine", "typical_use": "panic disorder and generalized anxiety"},
    "klonopin": {"salt": "clonazepam", "class": "benzodiazepine", "typical_use": "panic attacks and seizure disorders"},
    "valium": {"salt": "diazepam", "class": "benzodiazepine", "typical_use": "anxiety, muscle spasms, and seizure emergency"},
    "ativan": {"salt": "lorazepam", "class": "benzodiazepine", "typical_use": "anxiety disorders and insomnia"},
    "prozac": {"salt": "fluoxetine", "class": "ssri antidepressant", "typical_use": "major depression, OCD, and panic disorder"},
    "zoloft": {"salt": "sertraline hydrochloride", "class": "ssri antidepressant", "typical_use": "depression, anxiety, and PTSD"},
    "lexapro": {"salt": "escitalopram", "class": "ssri antidepressant", "typical_use": "depression and generalized anxiety disorder"},
    "celexa": {"salt": "citalopram", "class": "ssri antidepressant", "typical_use": "major depressive disorder"},
    "cymbalta": {"salt": "duloxetine hydrochloride", "class": "snri antidepressant", "typical_use": "depression, generalized anxiety, and diabetic neuropathic pain"},
    "effexor": {"salt": "venlafaxine", "class": "snri antidepressant", "typical_use": "depression, panic disorder, and social anxiety"},
    "wellbutrin": {"salt": "bupropion hydrochloride", "class": "ndri antidepressant", "typical_use": "major depressive disorder and smoking cessation"},
    "neurontin": {"salt": "gabapentin", "class": "neuropathic pain agent", "typical_use": "post-herpetic neuralgia and partial seizures"},
    "lyrica": {"salt": "pregabalin", "class": "neuropathic pain and anxiolytic agent", "typical_use": "diabetic neuropathy, fibromyalgia, and spinal pain"},
    "lamictal": {"salt": "lamotrigine", "class": "antiepileptic and mood stabilizer", "typical_use": "bipolar I depression and seizure disorders"},
    "topamax": {"salt": "topiramate", "class": "carbonic anhydrase inhibitor antiepileptic", "typical_use": "epilepsy and migraine headache prophylaxis"},
    "dilantin": {"salt": "phenytoin sodium", "class": "hydantoin anticonvulsant", "typical_use": "tonic-clonic seizures and status epilepticus prophylaxis"},
    "keppra": {"salt": "levetiracetam", "class": "second-generation antiepileptic", "typical_use": "partial and generalized seizures"},
    "depakote": {"salt": "divalproex sodium", "class": "antiepileptic and mood stabilizer", "typical_use": "bipolar mania, epilepsy, and migraine prophylaxis"},
    "sinemet": {"salt": "carbidopa + levodopa", "class": "antiparkinsonian dopamine precursor", "typical_use": "Parkinson disease motor symptoms"},
    "mirapex": {"salt": "pramipexole", "class": "dopamine agonist", "typical_use": "Parkinson disease and restless legs syndrome"},
    "requip": {"salt": "ropinirole", "class": "dopamine agonist", "typical_use": "Parkinson disease and restless legs syndrome"},
    "namenda": {"salt": "memantine", "class": "NMDA receptor antagonist", "typical_use": "moderate to severe Alzheimer disease"},
    "aricept": {"salt": "donepezil", "class": "acetylcholinesterase inhibitor", "typical_use": "Alzheimer disease dementia"}
}

for k, v in intl_brands.items():
    if k not in brands:
        brands[k] = v

print(f"Total Combined Brands: {len(brands)}")
print(f"Total Combined Generics: {len(generic_lexicon)}")

with open("drug_lookup.py", "r", encoding="utf-8") as f:
    orig = f.read()

parts = orig.split("BRAND_DATABASE = {}")
if len(parts) != 2:
    raise Exception("Could not find split anchor 'BRAND_DATABASE = {}'")

tail = "BRAND_DATABASE = {}" + parts[1]

header = '''\"\"\"
Canonical Code-Side Pharmaceutical Brand-to-Salt Engine.
Provides deterministic fuzzy matching for authentic, registered Indian and International
prescription brands and generic chemical entities mapped to active generic salts and standard outpatient indications.
\"\"\"

import re
from rapidfuzz import process, fuzz

MEANINGFUL_SUFFIXES = {
    "dsr", "ds", "sr", "xr", "lc", "cv", "plus", "d", "forte",
    "mr", "er", "cr", "dt", "h", "am", "av", "duo", "susp", "gel",
    "ls", "rd", "it", "sp", "th", "nt", "ct", "trio", "p", "gp"
}

PREFIX_REGEX = re.compile(
    r'^(tab|cap|syp|inj|oint|drop|drops|cream|gel|susp|suspension|lotion|sachet|powder|r/|rx|line\\s*\\d+[:.]?)\\.?\\s*',
    re.IGNORECASE
)

# ------------------------------------------------------------------------------
# 1. CANONICAL GENERIC CHEMICAL INGREDIENT LEXICON (WHO / INN / IP)
# ------------------------------------------------------------------------------
GENERIC_LEXICON = ''' + json.dumps(generic_lexicon, indent=4) + '''

# ------------------------------------------------------------------------------
# 2. CANONICAL REGISTERED BRAND DATABASE (CDSCO / IP / PACKAGE INSERTS / FDA)
# ------------------------------------------------------------------------------
RAW_BRAND_DATABASE = ''' + json.dumps(brands, indent=4) + '''

'''

final_content = header + tail

with open("drug_lookup.py", "w", encoding="utf-8") as f:
    f.write(final_content)

print("[+] Successfully wrote expanded drug_lookup.py!")
