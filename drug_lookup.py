"""
Canonical Code-Side Pharmaceutical Brand-to-Salt Engine.
Provides deterministic fuzzy matching for authentic, registered Indian and International
prescription brands and generic chemical entities mapped to active generic salts and standard outpatient indications.
"""

import re
from rapidfuzz import process, fuzz

MEANINGFUL_SUFFIXES = {
    "dsr", "ds", "sr", "xr", "lc", "cv", "plus", "d", "forte",
    "mr", "er", "cr", "dt", "h", "am", "av", "duo", "susp", "gel"
}

PREFIX_REGEX = re.compile(
    r'^(tab|cap|syp|inj|oint|drop|drops|cream|gel|susp|suspension|lotion|sachet|powder|r/|rx|line\s*\d+[:.]?)\.?\s*',
    re.IGNORECASE
)

# ------------------------------------------------------------------------------
# 1. CANONICAL GENERIC CHEMICAL INGREDIENT LEXICON (WHO / INN / IP)
# ------------------------------------------------------------------------------
# Doctors often write generic chemical names directly (e.g. 'Albendazole 400', 'Tab Pantoprazole').
GENERIC_LEXICON = {
    # Antibiotics & Antimicrobials
    "amoxicillin": {"salt": "amoxicillin", "class": "penicillin antibiotic", "typical_use": "bacterial respiratory/ear/skin infection"},
    "ampicillin": {"salt": "ampicillin", "class": "aminopenicillin antibiotic", "typical_use": "bacterial infection"},
    "ciprofloxacin": {"salt": "ciprofloxacin", "class": "fluoroquinolone antibiotic", "typical_use": "bacterial/urinary/GI infection"},
    "levofloxacin": {"salt": "levofloxacin", "class": "fluoroquinolone antibiotic", "typical_use": "respiratory or systemic bacterial infection"},
    "ofloxacin": {"salt": "ofloxacin", "class": "fluoroquinolone antibiotic", "typical_use": "bacterial/urinary/enteric infection"},
    "moxifloxacin": {"salt": "moxifloxacin", "class": "fluoroquinolone antibiotic", "typical_use": "respiratory tract infection"},
    "norfloxacin": {"salt": "norfloxacin", "class": "fluoroquinolone antibiotic", "typical_use": "urinary tract or gastrointestinal infection"},
    "cefuroxime": {"salt": "cefuroxime axetil", "class": "second-generation cephalosporin antibiotic", "typical_use": "bacterial respiratory/soft tissue infection"},
    "cefixime": {"salt": "cefixime", "class": "third-generation cephalosporin antibiotic", "typical_use": "bacterial infection / typhoid fever"},
    "cefpodoxime": {"salt": "cefpodoxime proxetil", "class": "third-generation cephalosporin antibiotic", "typical_use": "acute otitis media, pharyngitis, or pneumonia"},
    "ceftriaxone": {"salt": "ceftriaxone", "class": "third-generation cephalosporin antibiotic", "typical_use": "severe bacterial infection"},
    "azithromycin": {"salt": "azithromycin", "class": "macrolide antibiotic", "typical_use": "bacterial respiratory/throat infection"},
    "clarithromycin": {"salt": "clarithromycin", "class": "macrolide antibiotic", "typical_use": "respiratory or H. pylori infection"},
    "doxycycline": {"salt": "doxycycline", "class": "tetracycline antibiotic", "typical_use": "bacterial/rickettsial infection"},
    "metronidazole": {"salt": "metronidazole", "class": "nitroimidazole antimicrobial", "typical_use": "anaerobic bacterial or amoebic infection"},
    "fluconazole": {"salt": "fluconazole", "class": "triazole antifungal", "typical_use": "candidiasis or systemic fungal infection"},
    "itraconazole": {"salt": "itraconazole", "class": "triazole antifungal", "typical_use": "dermatophyte or systemic fungal infection"},
    "terbinafine": {"salt": "terbinafine", "class": "allylamine antifungal", "typical_use": "tinea or fungal nail infection"},
    "acyclovir": {"salt": "acyclovir", "class": "antiviral agent", "typical_use": "herpes simplex or herpes zoster infection"},
    "mupirocin": {"salt": "mupirocin", "class": "topical antibacterial", "typical_use": "impetigo and superficial bacterial skin infections"},

    # Antimalarials & Anthelmintics
    "artemether": {"salt": "artemether", "class": "artemisinin derivative antimalarial", "typical_use": "malaria treatment"},
    "lumefantrine": {"salt": "lumefantrine", "class": "antimalarial aryl amino alcohol", "typical_use": "malaria combination therapy"},
    "artesunate": {"salt": "artesunate", "class": "artemisinin derivative antimalarial", "typical_use": "severe/falciparum malaria"},
    "chloroquine": {"salt": "chloroquine", "class": "4-aminoquinoline antimalarial", "typical_use": "vivax malaria prophylaxis and treatment"},
    "albendazole": {"salt": "albendazole", "class": "broad-spectrum anthelmintic", "typical_use": "intestinal worm infestation (roundworm, pinworm, hookworm)"},
    "mebendazole": {"salt": "mebendazole", "class": "anthelmintic", "typical_use": "gastrointestinal worm infestation"},
    "ivermectin": {"salt": "ivermectin", "class": "anti-parasitic", "typical_use": "scabies or strongyloidiasis"},

    # GI & Acid Reflux
    "pantoprazole": {"salt": "pantoprazole", "class": "proton pump inhibitor", "typical_use": "gastric hyperacidity, GERD, and peptic ulcer"},
    "omeprazole": {"salt": "omeprazole", "class": "proton pump inhibitor", "typical_use": "acid reflux and heartburn"},
    "rabeprazole": {"salt": "rabeprazole", "class": "proton pump inhibitor", "typical_use": "acid reflux and erosive esophagitis"},
    "esomeprazole": {"salt": "esomeprazole", "class": "proton pump inhibitor", "typical_use": "gastroesophageal reflux disease"},
    "lansoprazole": {"salt": "lansoprazole", "class": "proton pump inhibitor", "typical_use": "peptic ulcer disease and GERD"},
    "ranitidine": {"salt": "ranitidine", "class": "h2 receptor antagonist", "typical_use": "gastric acidity and heartburn"},
    "famotidine": {"salt": "famotidine", "class": "h2 receptor antagonist", "typical_use": "gastric hyperacidity and heartburn"},
    "ondansetron": {"salt": "ondansetron", "class": "5-ht3 receptor antagonist", "typical_use": "prevention and treatment of nausea and vomiting"},
    "domperidone": {"salt": "domperidone", "class": "dopamine antagonist prokinetic", "typical_use": "nausea, dyspepsia, and gastric motility"},
    "sucralfate": {"salt": "sucralfate", "class": "mucosal protective agent", "typical_use": "duodenal or gastric ulcer healing"},
    "lactulose": {"salt": "lactulose", "class": "osmotic laxative", "typical_use": "constipation and hepatic encephalopathy"},
    "dicyclomine": {"salt": "dicyclomine", "class": "antispasmodic", "typical_use": "intestinal cramp and colic pain"},

    # Diabetes & Endocrine
    "metformin": {"salt": "metformin", "class": "biguanide antidiabetic", "typical_use": "glycemic control in type 2 diabetes"},
    "glimepiride": {"salt": "glimepiride", "class": "sulfonylurea antidiabetic", "typical_use": "type 2 diabetes mellitus"},
    "gliclazide": {"salt": "gliclazide", "class": "sulfonylurea antidiabetic", "typical_use": "type 2 diabetes mellitus"},
    "glibenclamide": {"salt": "glibenclamide", "class": "sulfonylurea antidiabetic", "typical_use": "type 2 diabetes mellitus"},
    "sitagliptin": {"salt": "sitagliptin", "class": "dpp-4 inhibitor antidiabetic", "typical_use": "type 2 diabetes glycemic management"},
    "vildagliptin": {"salt": "vildagliptin", "class": "dpp-4 inhibitor antidiabetic", "typical_use": "type 2 diabetes mellitus"},
    "dapagliflozin": {"salt": "dapagliflozin", "class": "sglt2 inhibitor antidiabetic", "typical_use": "type 2 diabetes and cardio-renal protection"},
    "empagliflozin": {"salt": "empagliflozin", "class": "sglt2 inhibitor antidiabetic", "typical_use": "type 2 diabetes and cardiovascular risk reduction"},
    "levothyroxine": {"salt": "levothyroxine", "class": "synthetic thyroid hormone", "typical_use": "hypothyroidism replacement therapy"},

    # Cardiology & Hypertension
    "amlodipine": {"salt": "amlodipine", "class": "calcium channel blocker", "typical_use": "hypertension and angina pectoris"},
    "cilnidipine": {"salt": "cilnidipine", "class": "l/n-type dual calcium channel blocker", "typical_use": "hypertension with renal protection"},
    "telmisartan": {"salt": "telmisartan", "class": "angiotensin receptor blocker", "typical_use": "essential hypertension and cardiovascular protection"},
    "losartan": {"salt": "losartan", "class": "angiotensin receptor blocker", "typical_use": "hypertension and diabetic nephropathy"},
    "ramipril": {"salt": "ramipril", "class": "ace inhibitor", "typical_use": "hypertension and post-MI heart failure"},
    "enalapril": {"salt": "enalapril", "class": "ace inhibitor", "typical_use": "hypertension and heart failure"},
    "bisoprolol": {"salt": "bisoprolol", "class": "beta-1 selective blocker", "typical_use": "hypertension and angina pectoris"},
    "metoprolol": {"salt": "metoprolol", "class": "beta-blocker", "typical_use": "hypertension, angina, and rate control"},
    "nebivolol": {"salt": "nebivolol", "class": "vasodilating beta-blocker", "typical_use": "essential hypertension"},
    "atorvastatin": {"salt": "atorvastatin", "class": "statin lipid-lowering agent", "typical_use": "hypercholesterolemia and cardiovascular prevention"},
    "rosuvastatin": {"salt": "rosuvastatin", "class": "statin lipid-lowering agent", "typical_use": "hyperlipidemia management"},
    "aspirin": {"salt": "aspirin", "class": "antiplatelet agent", "typical_use": "secondary cardiovascular prevention"},
    "clopidogrel": {"salt": "clopidogrel", "class": "antiplatelet agent", "typical_use": "prevention of ischemic stroke and MI"},
    "torsemide": {"salt": "torsemide", "class": "loop diuretic", "typical_use": "edema and hypertension"},
    "furosemide": {"salt": "furosemide", "class": "loop diuretic", "typical_use": "acute and chronic edema"},
    "clonidine": {"salt": "clonidine", "class": "alpha-2 adrenergic agonist", "typical_use": "hypertension management"},

    # Pain, Anti-inflammatory & Musculoskeletal
    "paracetamol": {"salt": "paracetamol", "class": "analgesic and antipyretic", "typical_use": "fever and mild-to-moderate pain"},
    "acetaminophen": {"salt": "paracetamol", "class": "analgesic and antipyretic", "typical_use": "fever and mild-to-moderate pain"},
    "ibuprofen": {"salt": "ibuprofen", "class": "nsaid analgesic", "typical_use": "inflammatory pain, musculoskeletal swelling, and fever"},
    "diclofenac": {"salt": "diclofenac", "class": "nsaid anti-inflammatory", "typical_use": "joint pain, arthritis, and acute injury inflammation"},
    "aceclofenac": {"salt": "aceclofenac", "class": "nsaid analgesic", "typical_use": "osteoarthritis, rheumatoid arthritis, and joint pain"},
    "mefenamic acid": {"salt": "mefenamic acid", "class": "nsaid analgesic", "typical_use": "dysmenorrhea and dental/acute pain"},
    "tramadol": {"salt": "tramadol", "class": "opioid analgesic", "typical_use": "moderate to severe pain"},
    "thiocolchicoside": {"salt": "thiocolchicoside", "class": "muscle relaxant", "typical_use": "painful muscle spasms and lumbago"},

    # Allergy & Respiratory
    "cetirizine": {"salt": "cetirizine", "class": "second-generation h1 antihistamine", "typical_use": "allergic rhinitis and urticaria"},
    "levocetirizine": {"salt": "levocetirizine", "class": "active enantiomer antihistamine", "typical_use": "allergy, itching, and allergic rhinitis"},
    "fexofenadine": {"salt": "fexofenadine", "class": "non-sedating h1 antihistamine", "typical_use": "seasonal allergic rhinitis and chronic hives"},
    "montelukast": {"salt": "montelukast", "class": "leukotriene receptor antagonist", "typical_use": "bronchial asthma prophylaxis and allergic rhinitis"},
    "salbutamol": {"salt": "salbutamol", "class": "short-acting beta-2 agonist (saba)", "typical_use": "bronchospasm relief in asthma and copd"},
    "albuterol": {"salt": "salbutamol", "class": "short-acting beta-2 agonist (saba)", "typical_use": "bronchospasm relief in asthma and copd"},
    "budesonide": {"salt": "budesonide", "class": "inhaled corticosteroid", "typical_use": "airway inflammation in bronchial asthma"},
    "ketotifen": {"salt": "ketotifen", "class": "mast cell stabilizer and antihistamine", "typical_use": "prophylaxis of bronchial asthma and allergic disorders"}
}

# ------------------------------------------------------------------------------
# 2. CANONICAL REGISTERED BRAND DATABASE (CDSCO / IP / PACKAGE INSERTS)
# ------------------------------------------------------------------------------
RAW_BRAND_DATABASE = {
    # --- Antibiotics, Antifungals & Antivirals ---
    "augmentin": {"salt": "amoxicillin + clavulanic acid", "class": "penicillin antibiotic with beta-lactamase inhibitor", "typical_use": "bacterial respiratory/skin infection"},
    "clavam": {"salt": "amoxicillin + clavulanic acid", "class": "penicillin antibiotic with beta-lactamase inhibitor", "typical_use": "bacterial infection"},
    "moxikind": {"salt": "amoxicillin + clavulanic acid", "class": "penicillin antibiotic with beta-lactamase inhibitor", "typical_use": "bacterial infection"},
    "novamox": {"salt": "amoxicillin", "class": "penicillin antibiotic", "typical_use": "bacterial infection"},
    "mox": {"salt": "amoxicillin", "class": "penicillin antibiotic", "typical_use": "bacterial infection"},
    "ciplox": {"salt": "ciprofloxacin", "class": "fluoroquinolone antibiotic", "typical_use": "bacterial infection"},
    "cifran": {"salt": "ciprofloxacin", "class": "fluoroquinolone antibiotic", "typical_use": "bacterial infection"},
    "ciprobid": {"salt": "ciprofloxacin", "class": "fluoroquinolone antibiotic", "typical_use": "bacterial infection"},
    "zoxan": {"salt": "ciprofloxacin", "class": "fluoroquinolone antibiotic", "typical_use": "bacterial eye/systemic infection"},
    "alcipro": {"salt": "ciprofloxacin", "class": "fluoroquinolone antibiotic", "typical_use": "bacterial infection"},
    "levomac": {"salt": "levofloxacin", "class": "fluoroquinolone antibiotic", "typical_use": "respiratory or systemic bacterial infection"},
    "tavanic": {"salt": "levofloxacin", "class": "fluoroquinolone antibiotic", "typical_use": "bacterial respiratory infection"},
    "lquin": {"salt": "levofloxacin", "class": "fluoroquinolone antibiotic", "typical_use": "bacterial infection"},
    "avelox": {"salt": "moxifloxacin", "class": "fluoroquinolone antibiotic", "typical_use": "respiratory tract infection"},
    "moxicip": {"salt": "moxifloxacin", "class": "fluoroquinolone antibiotic", "typical_use": "bacterial infection"},
    "zenflox": {"salt": "ofloxacin", "class": "fluoroquinolone antibiotic", "typical_use": "bacterial infection"},
    "oflox": {"salt": "ofloxacin", "class": "fluoroquinolone antibiotic", "typical_use": "bacterial/urinary/GI infection"},
    "norflox": {"salt": "norfloxacin", "class": "fluoroquinolone antibiotic", "typical_use": "urinary tract or gastrointestinal infection"},
    "ceftum": {"salt": "cefuroxime axetil", "class": "second-generation cephalosporin antibiotic", "typical_use": "bacterial respiratory/soft tissue infection"},
    "cetil": {"salt": "cefuroxime axetil", "class": "second-generation cephalosporin antibiotic", "typical_use": "bacterial infection"},
    "zinacef": {"salt": "cefuroxime", "class": "second-generation cephalosporin antibiotic", "typical_use": "bacterial infection"},
    "taxim": {"salt": "cefixime", "class": "third-generation cephalosporin", "typical_use": "bacterial infection / typhoid fever"},
    "zifi": {"salt": "cefixime", "class": "third-generation cephalosporin", "typical_use": "bacterial infection"},
    "mahacef": {"salt": "cefixime", "class": "third-generation cephalosporin", "typical_use": "bacterial infection"},
    "cefspan": {"salt": "cefixime", "class": "third-generation cephalosporin", "typical_use": "bacterial infection"},
    "cepodem": {"salt": "cefpodoxime proxetil", "class": "third-generation cephalosporin antibiotic", "typical_use": "acute otitis media, pharyngitis, or pneumonia"},
    "doxcef": {"salt": "cefpodoxime proxetil", "class": "third-generation cephalosporin antibiotic", "typical_use": "bacterial infection"},
    "monocef": {"salt": "ceftriaxone", "class": "third-generation cephalosporin", "typical_use": "severe bacterial infection"},
    "rocephin": {"salt": "ceftriaxone", "class": "third-generation cephalosporin", "typical_use": "severe bacterial infection"},
    "meronem": {"salt": "meropenem", "class": "carbapenem antibiotic", "typical_use": "severe hospital-acquired infection"},
    "invanz": {"salt": "ertapenem", "class": "carbapenem antibiotic", "typical_use": "complicated intra-abdominal or skin infection"},
    "azithral": {"salt": "azithromycin", "class": "macrolide antibiotic", "typical_use": "bacterial respiratory/throat infection"},
    "azee": {"salt": "azithromycin", "class": "macrolide antibiotic", "typical_use": "bacterial infection"},
    "zady": {"salt": "azithromycin", "class": "macrolide antibiotic", "typical_use": "respiratory tract infection"},
    "zithromax": {"salt": "azithromycin", "class": "macrolide antibiotic", "typical_use": "bacterial infection"},
    "klacid": {"salt": "clarithromycin", "class": "macrolide antibiotic", "typical_use": "respiratory or H. pylori infection"},
    "claribid": {"salt": "clarithromycin", "class": "macrolide antibiotic", "typical_use": "bacterial respiratory infection"},
    "rulide": {"salt": "roxithromycin", "class": "macrolide antibiotic", "typical_use": "respiratory tract infection"},
    "doxy": {"salt": "doxycycline", "class": "tetracycline antibiotic", "typical_use": "bacterial/rickettsial infection"},
    "doxt": {"salt": "doxycycline", "class": "tetracycline antibiotic", "typical_use": "bacterial infection"},
    "metrogyl": {"salt": "metronidazole", "class": "nitroimidazole antimicrobial", "typical_use": "amoebiasis or anaerobic infection"},
    "flagyl": {"salt": "metronidazole", "class": "nitroimidazole antimicrobial", "typical_use": "anaerobic bacterial/protozoal infection"},
    "bactrim": {"salt": "sulfamethoxazole + trimethoprim", "class": "sulfonamide combination antibacterial", "typical_use": "urinary tract or respiratory infection"},
    "septra": {"salt": "sulfamethoxazole + trimethoprim", "class": "antibacterial combination", "typical_use": "bacterial infection"},
    "diflucan": {"salt": "fluconazole", "class": "triazole antifungal", "typical_use": "candidiasis or systemic fungal infection"},
    "forcan": {"salt": "fluconazole", "class": "triazole antifungal", "typical_use": "fungal infection"},
    "itaspor": {"salt": "itraconazole", "class": "triazole antifungal", "typical_use": "systemic fungal or dermatophyte infection"},
    "canditral": {"salt": "itraconazole", "class": "triazole antifungal", "typical_use": "fungal infection"},
    "sporanox": {"salt": "itraconazole", "class": "triazole antifungal", "typical_use": "fungal infection"},
    "terbinaforce": {"salt": "terbinafine", "class": "allylamine antifungal", "typical_use": "onychomycosis or tinea fungal infection"},
    "acyclovir": {"salt": "acyclovir", "class": "antiviral agent", "typical_use": "herpes simplex or herpes zoster infection"},
    "zovirax": {"salt": "acyclovir", "class": "antiviral agent", "typical_use": "herpes viral infection"},
    "valcivir": {"salt": "valacyclovir", "class": "antiviral prodrug", "typical_use": "herpes zoster and genital herpes"},
    "tbact": {"salt": "mupirocin", "class": "topical antibacterial", "typical_use": "impetigo and superficial bacterial skin infections"},

    # --- Antimalarials & Anthelmintics ---
    "coartem": {"salt": "artemether + lumefantrine", "class": "artemisinin-based combination (antimalarial)", "typical_use": "uncomplicated falciparum malaria"},
    "lumerax": {"salt": "artemether + lumefantrine", "class": "artemisinin-based combination (antimalarial)", "typical_use": "falciparum malaria"},
    "falcinil": {"salt": "artesunate", "class": "antimalarial", "typical_use": "malaria treatment"},
    "combither": {"salt": "artemether + lumefantrine", "class": "antimalarial combination", "typical_use": "malaria"},
    "larinate": {"salt": "artesunate + sulfadoxine-pyrimethamine", "class": "antimalarial", "typical_use": "malaria"},
    "zentel": {"salt": "albendazole", "class": "anthelmintic (anti-parasitic)", "typical_use": "intestinal worm infection (roundworm, pinworm, hookworm)"},
    "bandy": {"salt": "albendazole", "class": "anthelmintic (anti-parasitic)", "typical_use": "intestinal helminthic infection"},
    "noworm": {"salt": "albendazole", "class": "anthelmintic (anti-parasitic)", "typical_use": "intestinal worm infestation"},
    "bendex": {"salt": "albendazole", "class": "anthelmintic (anti-parasitic)", "typical_use": "parasitic worm infection"},
    "alminth": {"salt": "albendazole", "class": "anthelmintic (anti-parasitic)", "typical_use": "worm infestation"},
    "vermox": {"salt": "mebendazole", "class": "anthelmintic", "typical_use": "gastrointestinal worm infection"},
    "ivecop": {"salt": "ivermectin", "class": "anti-parasitic", "typical_use": "scabies or strongyloidiasis infection"},
    "ivermectol": {"salt": "ivermectin", "class": "anti-parasitic", "typical_use": "parasitic infection or scabies"},

    # --- Gastrointestinal, Antacids & Acid Reflux ---
    "pan": {"salt": "pantoprazole", "class": "proton pump inhibitor", "typical_use": "gastric hyperacidity, GERD, and peptic ulcer"},
    "pantocid": {"salt": "pantoprazole", "class": "proton pump inhibitor", "typical_use": "gastroesophageal reflux and ulcer healing"},
    "pantodac": {"salt": "pantoprazole", "class": "proton pump inhibitor", "typical_use": "acid peptic disease"},
    "pantop": {"salt": "pantoprazole", "class": "proton pump inhibitor", "typical_use": "gastric acidity / GERD"},
    "omez": {"salt": "omeprazole", "class": "proton pump inhibitor", "typical_use": "acid peptic disease and heartburn"},
    "omee": {"salt": "omeprazole", "class": "proton pump inhibitor", "typical_use": "gastric acidity"},
    "razo": {"salt": "rabeprazole", "class": "proton pump inhibitor", "typical_use": "acid reflux and erosive esophagitis"},
    "rabicip": {"salt": "rabeprazole", "class": "proton pump inhibitor", "typical_use": "acid peptic disease"},
    "happi": {"salt": "rabeprazole", "class": "proton pump inhibitor", "typical_use": "gastroesophageal reflux disease"},
    "rablet": {"salt": "rabeprazole", "class": "proton pump inhibitor", "typical_use": "acid reflux and peptic ulcers"},
    "cyra": {"salt": "rabeprazole", "class": "proton pump inhibitor", "typical_use": "gastric acidity"},
    "veloz": {"salt": "rabeprazole", "class": "proton pump inhibitor", "typical_use": "acid reflux and heartburn"},
    "parit": {"salt": "rabeprazole", "class": "proton pump inhibitor", "typical_use": "acid peptic disorder"},
    "nexpro": {"salt": "esomeprazole", "class": "proton pump inhibitor", "typical_use": "severe GERD and reflux esophagitis"},
    "esomac": {"salt": "esomeprazole", "class": "proton pump inhibitor", "typical_use": "gastroesophageal reflux disease"},
    "lanzol": {"salt": "lansoprazole", "class": "proton pump inhibitor", "typical_use": "gastric and duodenal ulcers"},
    "rantac": {"salt": "ranitidine", "class": "h2 receptor antagonist", "typical_use": "gastric acidity and heartburn"},
    "aciloc": {"salt": "ranitidine", "class": "h2 receptor antagonist", "typical_use": "gastric acidity and ulcer disease"},
    "zinetac": {"salt": "ranitidine", "class": "h2 receptor antagonist", "typical_use": "acid dyspepsia"},
    "gelusil": {"salt": "aluminium hydroxide + magnesium hydroxide + simethicone", "class": "antacid and antiflatulent suspension", "typical_use": "gastric acidity, heartburn, and gas"},
    "digene": {"salt": "magnesium hydroxide + aluminium hydroxide + simethicone", "class": "antacid suspension", "typical_use": "acidity, flatulence, and heartburn"},
    "mucaine": {"salt": "oxethazaine + aluminium hydroxide + magnesium hydroxide", "class": "local anesthetic antacid gel", "typical_use": "severe esophagitis and gastritis pain"},
    "sucrafil": {"salt": "sucralfate", "class": "mucosal protective agent", "typical_use": "gastric or duodenal ulcer protection"},
    "cremaffin": {"salt": "liquid paraffin + milk of magnesia", "class": "laxative emulsion", "typical_use": "constipation relief"},
    "duphalac": {"salt": "lactulose", "class": "osmotic laxative", "typical_use": "chronic constipation and hepatic encephalopathy"},
    "ondem": {"salt": "ondansetron", "class": "5-ht3 antagonist antiemetic", "typical_use": "nausea and vomiting prevention"},
    "vomikind": {"salt": "ondansetron", "class": "antiemetic", "typical_use": "nausea and vomiting"},
    "domstal": {"salt": "domperidone", "class": "prokinetic and antiemetic", "typical_use": "dyspepsia, gastric fullness, and nausea"},
    "motilium": {"salt": "domperidone", "class": "prokinetic", "typical_use": "nausea and upper GI motility disorder"},
    "colimex": {"salt": "dicyclomine + paracetamol", "class": "antispasmodic and analgesic", "typical_use": "abdominal cramp and colic pain"},
    "cyclopam": {"salt": "dicyclomine + paracetamol", "class": "antispasmodic and analgesic", "typical_use": "intestinal colic and abdominal pain"},
    "colospa": {"salt": "mebeverine", "class": "musculotropic antispasmodic", "typical_use": "irritable bowel syndrome (IBS)"},

    # --- Diabetes & Endocrine ---
    "glycomet": {"salt": "metformin", "class": "biguanide antidiabetic", "typical_use": "type 2 diabetes mellitus glycemic control"},
    "glucophage": {"salt": "metformin", "class": "biguanide antidiabetic", "typical_use": "type 2 diabetes mellitus glycemic control"},
    "gluconorm": {"salt": "metformin", "class": "biguanide antidiabetic", "typical_use": "type 2 diabetes mellitus"},
    "obimet": {"salt": "metformin", "class": "biguanide antidiabetic", "typical_use": "type 2 diabetes mellitus"},
    "formin": {"salt": "metformin", "class": "biguanide antidiabetic", "typical_use": "type 2 diabetes mellitus"},
    "amaryl": {"salt": "glimepiride", "class": "sulfonylurea antidiabetic", "typical_use": "type 2 diabetes mellitus"},
    "glador": {"salt": "glimepiride", "class": "sulfonylurea antidiabetic", "typical_use": "type 2 diabetes mellitus"},
    "zoryl": {"salt": "glimepiride", "class": "sulfonylurea antidiabetic", "typical_use": "type 2 diabetes mellitus"},
    "glimi": {"salt": "glimepiride", "class": "sulfonylurea antidiabetic", "typical_use": "type 2 diabetes mellitus"},
    "diamicron": {"salt": "gliclazide", "class": "sulfonylurea antidiabetic", "typical_use": "type 2 diabetes mellitus"},
    "daonil": {"salt": "glibenclamide", "class": "sulfonylurea antidiabetic", "typical_use": "type 2 diabetes mellitus"},
    "januvia": {"salt": "sitagliptin", "class": "dpp-4 inhibitor antidiabetic", "typical_use": "type 2 diabetes mellitus"},
    "galvus": {"salt": "vildagliptin", "class": "dpp-4 inhibitor antidiabetic", "typical_use": "type 2 diabetes mellitus"},
    "trajenta": {"salt": "linagliptin", "class": "dpp-4 inhibitor antidiabetic", "typical_use": "type 2 diabetes mellitus"},
    "forxiga": {"salt": "dapagliflozin", "class": "sglt2 inhibitor antidiabetic", "typical_use": "type 2 diabetes and renal/cardiac protection"},
    "jardiance": {"salt": "empagliflozin", "class": "sglt2 inhibitor antidiabetic", "typical_use": "type 2 diabetes and cardiovascular risk reduction"},
    "rybelsus": {"salt": "semaglutide", "class": "glp-1 receptor agonist", "typical_use": "type 2 diabetes glycemic control and weight management"},
    "mixtard": {"salt": "biphasic isophane human insulin", "class": "human insulin preparation", "typical_use": "insulin-dependent diabetes mellitus"},
    "lantus": {"salt": "insulin glargine", "class": "long-acting basal insulin analog", "typical_use": "basal glycemic control in diabetes"},
    "thyronorm": {"salt": "levothyroxine sodium", "class": "synthetic thyroid hormone", "typical_use": "hypothyroidism replacement therapy"},
    "eltroxin": {"salt": "levothyroxine sodium", "class": "thyroid hormone replacement", "typical_use": "hypothyroidism"},

    # --- Hypertension, Cardiology & Lipid Lowering ---
    "concor": {"salt": "bisoprolol", "class": "cardioselective beta-1 blocker", "typical_use": "hypertension and angina pectoris"},
    "betaloc": {"salt": "metoprolol", "class": "beta-blocker", "typical_use": "hypertension, angina, and heart rate control"},
    "metolar": {"salt": "metoprolol", "class": "beta-blocker", "typical_use": "hypertension and angina"},
    "nebicard": {"salt": "nebivolol", "class": "vasodilating beta-blocker", "typical_use": "essential hypertension"},
    "telma": {"salt": "telmisartan", "class": "angiotensin receptor blocker (arb)", "typical_use": "essential hypertension"},
    "telmikind": {"salt": "telmisartan", "class": "angiotensin receptor blocker (arb)", "typical_use": "hypertension"},
    "telsar": {"salt": "telmisartan", "class": "angiotensin receptor blocker (arb)", "typical_use": "essential hypertension"},
    "losar": {"salt": "losartan", "class": "angiotensin receptor blocker (arb)", "typical_use": "hypertension and diabetic nephropathy"},
    "repace": {"salt": "losartan", "class": "angiotensin receptor blocker", "typical_use": "hypertension"},
    "amlong": {"salt": "amlodipine", "class": "dihydropyridine calcium channel blocker", "typical_use": "hypertension and chronic stable angina"},
    "stamlo": {"salt": "amlodipine", "class": "calcium channel blocker", "typical_use": "hypertension"},
    "cilacar": {"salt": "cilnidipine", "class": "l/n-type dual calcium channel blocker", "typical_use": "hypertension with kidney protection"},
    "cardace": {"salt": "ramipril", "class": "ace inhibitor", "typical_use": "hypertension and post-myocardial infarction care"},
    "envas": {"salt": "enalapril", "class": "ace inhibitor", "typical_use": "hypertension and heart failure"},
    "atorva": {"salt": "atorvastatin", "class": "hmg-coa reductase inhibitor (statin)", "typical_use": "hypercholesterolemia and cardiovascular prevention"},
    "lipitor": {"salt": "atorvastatin", "class": "hmg-coa reductase inhibitor (statin)", "typical_use": "dyslipidemia"},
    "rosuvas": {"salt": "rosuvastatin", "class": "statin lipid-lowering agent", "typical_use": "hyperlipidemia"},
    "rozucor": {"salt": "rosuvastatin", "class": "statin lipid-lowering agent", "typical_use": "hypercholesterolemia"},
    "ecosprin": {"salt": "aspirin", "class": "antiplatelet agent", "typical_use": "cardiovascular event prevention and antiplatelet therapy"},
    "clopilet": {"salt": "clopidogrel", "class": "antiplatelet agent", "typical_use": "prevention of ischemic stroke and myocardial infarction"},
    "deplatt": {"salt": "clopidogrel", "class": "antiplatelet agent", "typical_use": "atherothrombosis prevention"},
    "dytor": {"salt": "torsemide", "class": "loop diuretic", "typical_use": "edema and hypertension"},
    "lasix": {"salt": "furosemide", "class": "loop diuretic", "typical_use": "edema due to cardiac, hepatic, or renal disease"},
    "catapres": {"salt": "clonidine", "class": "centrally acting alpha-2 agonist", "typical_use": "hypertension"},

    # --- Pain, Fever, Orthopedics & Anti-inflammatory ---
    "dolo": {"salt": "paracetamol", "class": "analgesic and antipyretic", "typical_use": "fever and mild-to-moderate pain"},
    "calpol": {"salt": "paracetamol", "class": "analgesic and antipyretic", "typical_use": "fever and pain"},
    "crocin": {"salt": "paracetamol", "class": "analgesic and antipyretic", "typical_use": "fever and body ache"},
    "pacimol": {"salt": "paracetamol", "class": "analgesic and antipyretic", "typical_use": "fever and pain relief"},
    "combiflam": {"salt": "ibuprofen + paracetamol", "class": "nsaid + analgesic combination", "typical_use": "inflammatory musculoskeletal pain and fever"},
    "ibugesic": {"salt": "ibuprofen + paracetamol", "class": "nsaid analgesic combination", "typical_use": "pain and swelling"},
    "brufen": {"salt": "ibuprofen", "class": "nsaid analgesic", "typical_use": "inflammatory arthritis and pain"},
    "voveran": {"salt": "diclofenac", "class": "nsaid anti-inflammatory", "typical_use": "orthopedic pain, arthritis, or post-traumatic swelling"},
    "voltaren": {"salt": "diclofenac", "class": "nsaid anti-inflammatory", "typical_use": "joint and musculoskeletal pain"},
    "zerodol": {"salt": "aceclofenac", "class": "nsaid analgesic", "typical_use": "joint pain, osteoarthritis, and inflammation"},
    "hifenac": {"salt": "aceclofenac", "class": "nsaid analgesic", "typical_use": "rheumatoid arthritis and osteoarthritis pain"},
    "meftal": {"salt": "mefenamic acid", "class": "nsaid analgesic", "typical_use": "dysmenorrhea, menstrual colic, or dental pain"},
    "chymooral": {"salt": "trypsin + chymotrypsin", "class": "proteolytic enzyme anti-inflammatory", "typical_use": "post-operative and post-traumatic edema"},
    "enzomac": {"salt": "trypsin + bromelain + rutoside", "class": "anti-inflammatory enzyme combination", "typical_use": "soft tissue swelling and inflammation"},
    "ultracet": {"salt": "tramadol + paracetamol", "class": "opioid analgesic combination", "typical_use": "moderate to severe acute pain"},
    "myoril": {"salt": "thiocolchicoside", "class": "muscle relaxant", "typical_use": "painful muscle spasms and lumbago"},

    # --- Allergy, Cough, Cold & Respiratory ---
    "allegra": {"salt": "fexofenadine", "class": "non-sedating second-generation h1-antihistamine", "typical_use": "seasonal allergic rhinitis and chronic urticaria"},
    "cetzine": {"salt": "cetirizine", "class": "second-generation h1 antihistamine", "typical_use": "allergic rhinitis and urticaria"},
    "alerid": {"salt": "cetirizine", "class": "antihistamine", "typical_use": "allergy symptoms"},
    "zyrtec": {"salt": "cetirizine", "class": "antihistamine", "typical_use": "allergic rhinitis and hives"},
    "xyzal": {"salt": "levocetirizine", "class": "active enantiomer antihistamine", "typical_use": "allergy, runny nose, and itching"},
    "teczine": {"salt": "levocetirizine", "class": "antihistamine", "typical_use": "allergic rhinitis and skin allergy"},
    "montair": {"salt": "montelukast", "class": "leukotriene receptor antagonist", "typical_use": "bronchial asthma prophylaxis and allergic rhinitis"},
    "montek": {"salt": "montelukast", "class": "leukotriene receptor antagonist", "typical_use": "bronchial asthma and allergic rhinitis"},
    "asthalin": {"salt": "salbutamol", "class": "short-acting beta-2 agonist (saba) bronchodilator", "typical_use": "acute bronchospasm and asthma relief"},
    "ventolin": {"salt": "salbutamol", "class": "bronchodilator", "typical_use": "asthma and copd wheezing"},
    "duolin": {"salt": "ipratropium + levosalbutamol", "class": "anticholinergic + bronchodilator", "typical_use": "bronchospasm in asthma and copd"},
    "budecort": {"salt": "budesonide", "class": "corticosteroid inhaler/respules", "typical_use": "airway inflammation in bronchial asthma"},
    "foracort": {"salt": "formoterol + budesonide", "class": "laba + inhaled corticosteroid", "typical_use": "maintenance therapy for asthma and copd"},
    "seretide": {"salt": "salmeterol + fluticasone", "class": "laba + inhaled corticosteroid", "typical_use": "asthma and copd maintenance"},
    "ascoril": {"salt": "terbutaline + bromhexine + guaiphenesin", "class": "bronchodilator and expectorant", "typical_use": "productive cough and chest congestion"},
    "grilinctus": {"salt": "dextromethorphan + chlorpheniramine", "class": "antitussive cough syrup", "typical_use": "dry non-productive cough"},
    "alex": {"salt": "dextromethorphan + chlorpheniramine + phenylephrine", "class": "cough suppressant and decongestant", "typical_use": "cough and common cold symptoms"},
    "cheston": {"salt": "cetirizine + paracetamol + phenylephrine", "class": "cold preparation", "typical_use": "nasal congestion, cold, and fever"},
    "sinarest": {"salt": "paracetamol + phenylephrine + chlorpheniramine", "class": "cold and sinus relief preparation", "typical_use": "nasal congestion, fever, and common cold"},
    "nasivion": {"salt": "oxymetazoline", "class": "nasal decongestant spray/drops", "typical_use": "blocked nose and nasal congestion"},
    "otrivin": {"salt": "xylometazoline", "class": "topical nasal decongestant", "typical_use": "nasal congestion from colds or sinusitis"},
    "asthafen": {"salt": "ketotifen", "class": "mast cell stabilizer and h1-antihistamine", "typical_use": "prophylaxis of bronchial asthma and allergic disorders"},
    "zaditen": {"salt": "ketotifen", "class": "mast cell stabilizer", "typical_use": "allergic rhinitis and conjunctivitis"},

    # --- Neurology & Psychiatry ---
    "tegretol": {"salt": "carbamazepine", "class": "sodium channel blocker anticonvulsant", "typical_use": "epilepsy and trigeminal neuralgia"},
    "encorate": {"salt": "sodium valproate", "class": "broad-spectrum antiepileptic", "typical_use": "epilepsy and bipolar disorder prophylaxis"},
    "depakote": {"salt": "divalproex sodium", "class": "antiepileptic and mood stabilizer", "typical_use": "seizures, bipolar mania, and migraine prophylaxis"},
    "levipil": {"salt": "levetiracetam", "class": "second-generation antiepileptic", "typical_use": "partial onset and generalized seizures"},
    "keppra": {"salt": "levetiracetam", "class": "antiepileptic", "typical_use": "epileptic seizure control"},
    "gabapin": {"salt": "gabapentin", "class": "gaba analog", "typical_use": "neuropathic pain and partial seizures"},
    "neurontin": {"salt": "gabapentin", "class": "neuropathic pain agent", "typical_use": "post-herpetic neuralgia and neuropathic pain"},
    "pregabalin": {"salt": "pregabalin", "class": "calcium channel subunit modulator", "typical_use": "peripheral neuropathic pain and generalized anxiety"},
    "lyrica": {"salt": "pregabalin", "class": "neuropathic pain agent", "typical_use": "diabetic neuropathy, fibromyalgia, and neuralgia"},
    "nexito": {"salt": "escitalopram", "class": "selective serotonin reuptake inhibitor (ssri)", "typical_use": "major depressive disorder and generalized anxiety"},
    "cipralex": {"salt": "escitalopram", "class": "ssri antidepressant", "typical_use": "depression and anxiety disorders"},
    "alprax": {"salt": "alprazolam", "class": "triazolobenzodiazepine anxiolytic", "typical_use": "panic disorder and acute anxiety"},
    "ativan": {"salt": "lorazepam", "class": "benzodiazepine", "typical_use": "short-term anxiety and insomnia relief"},

    # --- Dermatology & Topical Care ---
    "betnovate": {"salt": "betamethasone valerate", "class": "topical corticosteroid", "typical_use": "inflammatory dermatoses, eczema, and psoriasis"},
    "diprovate": {"salt": "betamethasone dipropionate", "class": "potent topical corticosteroid", "typical_use": "inflammatory skin conditions"},
    "clobetamil": {"salt": "clobetasol propionate", "class": "very potent topical corticosteroid", "typical_use": "recalcitrant dermatoses and severe eczema"},
    "tenovate": {"salt": "clobetasol propionate", "class": "high-potency topical steroid", "typical_use": "plaque psoriasis and severe lichen planus"},
    "panderm": {"salt": "clobetasol + neomycin + miconazole", "class": "corticosteroid + antibiotic + antifungal cream", "typical_use": "mixed bacterial and fungal skin infections"},
    "quadriderm": {"salt": "betamethasone + gentamicin + tolnaftate + iodochlorhydroxyquin", "class": "multi-ingredient topical cream", "typical_use": "superficial mixed skin infections"}
}

# Normalize BRAND_DATABASE keys at load time and guarantee backwards compatibility
BRAND_DATABASE = {}
for k, v in RAW_BRAND_DATABASE.items():
    clean_k = k.lower().replace("-", "").strip()
    data = dict(v)
    data["clinical_indication"] = data.get("typical_use") or data.get("indication", "")
    data["typical_use"] = data["clinical_indication"]
    BRAND_DATABASE[clean_k] = data


def clean_brand_key(raw: str) -> tuple[str, list[str]]:
    """
    Cleans raw handwritten or OCR text:
    - Strips prescription prefixes (Tab, Cap, Syp, R/)
    - Normalizes hyphens (e.g. T-Bact -> tbact)
    - Strips strengths/dosages (500mg, 10ml, 650)
    - Extracts meaningful pharmaceutical suffixes (DSR, LC, CV, Plus, D, Forte)
    Returns: (base_token, detected_suffixes)
    """
    if not raw:
        return "", []
    s = PREFIX_REGEX.sub("", str(raw)).strip().lower()
    s = s.replace("-", "")
    s = re.sub(r'\b\d+(\.\d+)?\s*(mg|ml|mcg|g|iu)?\b', '', s)
    toks = re.sub(r'[^a-z0-9\s]', ' ', s).split()
    base_tok = toks[0] if toks else ""
    suffixes = [t for t in toks[1:] if t in MEANINGFUL_SUFFIXES]
    return base_tok, suffixes


def resolve_brand(
    raw_name: str,
    reading: str = "clear",
    spelling_candidates: list[str] | None = None
) -> dict:
    """
    Deterministically resolves a prescription medication name against authentic pharmacopeia.
    Supports:
      1. Canonical brand names & generic chemical ingredients.
      2. Meaningful suffix warnings (e.g. Pan D -> warned that 'D' indicates added domperidone).
      3. Reading-aware confidence gate: partial or guess readings are capped at 'candidates'.
      4. Margin rule for 7+ letter words: lookalike drug names must have >= 8 point lead over #2.
    """
    if not raw_name:
        return {"status": "unknown", "brand_as_written": raw_name, "is_known": False}

    base_tok, suffixes = clean_brand_key(raw_name)
    if not base_tok or len(base_tok) < 2:
        return {"status": "unknown", "brand_as_written": raw_name, "is_known": False}

    suffix_warn = None
    if suffixes:
        suffix_str = " ".join(suffixes).upper()
        suffix_warn = (
            f"Suffix '{suffix_str}' usually indicates an added active ingredient or modified-release formulation "
            f"(e.g. domperidone, clavulanate, levocetirizine, or sustained-release); "
            f"confirm full composition line on the physical packaging."
        )

    reading_norm = str(reading or "clear").lower().strip()

    # --- 1. Check GENERIC_LEXICON (Chemical entities written directly) ---
    if base_tok in GENERIC_LEXICON:
        info = GENERIC_LEXICON[base_tok]
        res = {
            "status": "resolved" if reading_norm == "clear" else "candidates",
            "is_generic": True,
            "brand_as_written": raw_name,
            "matched_brand": base_tok.title(),
            "salt": info["salt"],
            "pharmacological_class": info["class"],
            "typical_use": info["typical_use"],
            "clinical_indication": info["typical_use"],
            "is_known": (reading_norm == "clear")
        }
        if suffix_warn:
            res["suffix_warning"] = suffix_warn
        if res["status"] == "candidates":
            res["candidate_matches"] = [{
                "brand": base_tok.title(),
                "salt": info["salt"],
                "class": info["class"],
                "typical_use": info["typical_use"],
                "score": 100.0,
                "note": f"Visual reading was marked '{reading_norm}'"
            }]
        return res

    # --- 2. Check BRAND_DATABASE (Direct Exact Match) ---
    if base_tok in BRAND_DATABASE:
        info = BRAND_DATABASE[base_tok]
        res = {
            "status": "resolved" if reading_norm == "clear" else "candidates",
            "is_generic": False,
            "brand_as_written": raw_name,
            "matched_brand": base_tok.title(),
            "salt": info["salt"],
            "pharmacological_class": info["class"],
            "typical_use": info["typical_use"],
            "clinical_indication": info["clinical_indication"],
            "is_known": (reading_norm == "clear")
        }
        if suffix_warn:
            res["suffix_warning"] = suffix_warn
        if res["status"] == "candidates":
            res["candidate_matches"] = [{
                "brand": base_tok.title(),
                "salt": info["salt"],
                "class": info["class"],
                "typical_use": info["typical_use"],
                "score": 100.0,
                "note": f"Visual reading was marked '{reading_norm}'"
            }]
        return res

    # --- 3. Fuzzy Matching against BRAND_DATABASE with Margin & Reading Rules ---
    top_matches = process.extract(base_tok, BRAND_DATABASE.keys(), scorer=fuzz.ratio, limit=2)
    if top_matches:
        best_name, best_score, _ = top_matches[0]
        second_score = top_matches[1][1] if len(top_matches) > 1 else 0

        # Strict Threshold: >= 85 required for automated resolution
        if best_score >= 85:
            # Margin Rule: For words with 7+ letters, best match must beat second by at least 8 points
            margin_violation = (len(base_tok) >= 7 and (best_score - second_score < 8))
            is_clear_read = (reading_norm == "clear")

            info = BRAND_DATABASE[best_name]
            if is_clear_read and not margin_violation:
                res = {
                    "status": "resolved",
                    "is_generic": False,
                    "brand_as_written": raw_name,
                    "matched_brand": best_name.title(),
                    "salt": info["salt"],
                    "pharmacological_class": info["class"],
                    "typical_use": info["typical_use"],
                    "clinical_indication": info["clinical_indication"],
                    "match_score": round(best_score, 1),
                    "is_known": True
                }
                if suffix_warn:
                    res["suffix_warning"] = suffix_warn
                return res
            else:
                # Demote to candidates due to margin violation or partial/guess reading
                cands = []
                for b_name, sc, _ in top_matches:
                    if sc >= 70:
                        b_info = BRAND_DATABASE[b_name]
                        cands.append({
                            "brand": b_name.title(),
                            "salt": b_info["salt"],
                            "class": b_info["class"],
                            "typical_use": b_info["typical_use"],
                            "score": round(sc, 1)
                        })
                res = {
                    "status": "candidates",
                    "is_generic": False,
                    "brand_as_written": raw_name,
                    "candidate_matches": cands,
                    "is_known": False
                }
                if margin_violation:
                    res["note"] = f"Margin ambiguity between '{best_name.title()}' and '{top_matches[1][0].title()}'"
                if not is_clear_read:
                    res["reading_note"] = f"Visual handwriting reading was marked '{reading_norm}'"
                if suffix_warn:
                    res["suffix_warning"] = suffix_warn
                return res

        elif best_score >= 70:
            cands = []
            for b_name, sc, _ in top_matches:
                if sc >= 70:
                    b_info = BRAND_DATABASE[b_name]
                    cands.append({
                        "brand": b_name.title(),
                        "salt": b_info["salt"],
                        "class": b_info["class"],
                        "typical_use": b_info["typical_use"],
                        "score": round(sc, 1)
                    })
            res = {
                "status": "candidates",
                "is_generic": False,
                "brand_as_written": raw_name,
                "candidate_matches": cands,
                "is_known": False
            }
            if suffix_warn:
                res["suffix_warning"] = suffix_warn
            return res

    # --- 4. Fuzzy Check against GENERIC_LEXICON ---
    gen_matches = process.extract(base_tok, GENERIC_LEXICON.keys(), scorer=fuzz.ratio, limit=2)
    if gen_matches:
        g_name, g_score, _ = gen_matches[0]
        if g_score >= 85 and reading_norm == "clear":
            info = GENERIC_LEXICON[g_name]
            res = {
                "status": "resolved",
                "is_generic": True,
                "brand_as_written": raw_name,
                "matched_brand": g_name.title(),
                "salt": info["salt"],
                "pharmacological_class": info["class"],
                "typical_use": info["typical_use"],
                "clinical_indication": info["typical_use"],
                "match_score": round(g_score, 1),
                "is_known": True
            }
            if suffix_warn:
                res["suffix_warning"] = suffix_warn
            return res
        elif g_score >= 70:
            info = GENERIC_LEXICON[g_name]
            res = {
                "status": "candidates",
                "is_generic": True,
                "brand_as_written": raw_name,
                "candidate_matches": [{
                    "brand": g_name.title(),
                    "salt": info["salt"],
                    "class": info["class"],
                    "typical_use": info["typical_use"],
                    "score": round(g_score, 1)
                }],
                "is_known": False
            }
            if suffix_warn:
                res["suffix_warning"] = suffix_warn
            return res

    # --- 5. Test Extra Spelling Candidates if provided ---
    if spelling_candidates:
        candidate_results = []
        for cand in spelling_candidates:
            if not cand or cand.strip().lower() == raw_name.strip().lower():
                continue
            cand_res = resolve_brand(cand, reading="partial")
            if cand_res.get("status") in ("resolved", "candidates"):
                c_matches = cand_res.get("candidate_matches") or [{
                    "brand": cand_res.get("matched_brand"),
                    "salt": cand_res.get("salt"),
                    "class": cand_res.get("pharmacological_class"),
                    "typical_use": cand_res.get("typical_use")
                }]
                candidate_results.extend(c_matches)
        if candidate_results:
            return {
                "status": "candidates",
                "brand_as_written": raw_name,
                "candidate_matches": candidate_results[:3],
                "is_known": False
            }

    # --- 6. Honestly Return Unknown ---
    res = {
        "status": "unknown",
        "brand_as_written": raw_name,
        "is_known": False
    }
    if suffix_warn:
        res["suffix_warning"] = suffix_warn
    return res
