"""
Canonical Code-Side Pharmaceutical Brand-to-Salt Engine.
Provides deterministic fuzzy matching for authentic, registered Indian and International
prescription brands and generic chemical entities mapped to active generic salts and standard outpatient indications.
"""

import re
from rapidfuzz import process, fuzz

MEANINGFUL_SUFFIXES = {
    "dsr", "ds", "sr", "xr", "lc", "cv", "plus", "d", "forte",
    "mr", "er", "cr", "dt", "h", "am", "av", "duo", "susp", "gel",
    "ls", "rd", "it", "sp", "th", "nt", "ct", "trio", "p", "gp"
}

PREFIX_REGEX = re.compile(
    r'^(tab|cap|syp|inj|oint|drop|drops|cream|gel|susp|suspension|lotion|sachet|powder|r/|rx|line\s*\d+[:.]?)\.?\s*',
    re.IGNORECASE
)

# ------------------------------------------------------------------------------
# 1. CANONICAL GENERIC CHEMICAL INGREDIENT LEXICON (WHO / INN / IP)
# ------------------------------------------------------------------------------
GENERIC_LEXICON = {
    "amoxicillin": {
        "salt": "amoxicillin",
        "class": "penicillin antibiotic",
        "typical_use": "bacterial respiratory/ear/skin infection"
    },
    "ampicillin": {
        "salt": "ampicillin",
        "class": "aminopenicillin antibiotic",
        "typical_use": "bacterial infection"
    },
    "ciprofloxacin": {
        "salt": "ciprofloxacin",
        "class": "fluoroquinolone antibiotic",
        "typical_use": "bacterial/urinary/GI infection"
    },
    "levofloxacin": {
        "salt": "levofloxacin",
        "class": "fluoroquinolone antibiotic",
        "typical_use": "respiratory or systemic bacterial infection"
    },
    "ofloxacin": {
        "salt": "ofloxacin",
        "class": "fluoroquinolone antibiotic",
        "typical_use": "bacterial/urinary/enteric infection"
    },
    "moxifloxacin": {
        "salt": "moxifloxacin",
        "class": "fluoroquinolone antibiotic",
        "typical_use": "respiratory tract infection"
    },
    "norfloxacin": {
        "salt": "norfloxacin",
        "class": "fluoroquinolone antibiotic",
        "typical_use": "urinary tract or gastrointestinal infection"
    },
    "cefuroxime": {
        "salt": "cefuroxime axetil",
        "class": "second-generation cephalosporin antibiotic",
        "typical_use": "bacterial respiratory/soft tissue infection"
    },
    "cefixime": {
        "salt": "cefixime",
        "class": "third-generation cephalosporin antibiotic",
        "typical_use": "bacterial infection / typhoid fever"
    },
    "cefpodoxime": {
        "salt": "cefpodoxime proxetil",
        "class": "third-generation cephalosporin antibiotic",
        "typical_use": "acute otitis media, pharyngitis, or pneumonia"
    },
    "ceftriaxone": {
        "salt": "ceftriaxone",
        "class": "third-generation cephalosporin antibiotic",
        "typical_use": "severe bacterial infection"
    },
    "ceftazidime": {
        "salt": "ceftazidime",
        "class": "third-generation cephalosporin antibiotic",
        "typical_use": "pseudomonal and hospital-acquired infection"
    },
    "cefepime": {
        "salt": "cefepime",
        "class": "fourth-generation cephalosporin antibiotic",
        "typical_use": "severe nosocomial infections and febrile neutropenia"
    },
    "azithromycin": {
        "salt": "azithromycin",
        "class": "macrolide antibiotic",
        "typical_use": "bacterial respiratory/throat infection"
    },
    "clarithromycin": {
        "salt": "clarithromycin",
        "class": "macrolide antibiotic",
        "typical_use": "respiratory or H. pylori infection"
    },
    "roxithromycin": {
        "salt": "roxithromycin",
        "class": "macrolide antibiotic",
        "typical_use": "respiratory tract infection"
    },
    "erythromycin": {
        "salt": "erythromycin",
        "class": "macrolide antibiotic",
        "typical_use": "bacterial throat, skin, and chest infections"
    },
    "doxycycline": {
        "salt": "doxycycline",
        "class": "tetracycline antibiotic",
        "typical_use": "bacterial/rickettsial infection"
    },
    "minocycline": {
        "salt": "minocycline",
        "class": "tetracycline antibiotic",
        "typical_use": "acne vulgaris and resistant bacterial infections"
    },
    "metronidazole": {
        "salt": "metronidazole",
        "class": "nitroimidazole antimicrobial",
        "typical_use": "anaerobic bacterial or amoebic infection"
    },
    "tinidazole": {
        "salt": "tinidazole",
        "class": "nitroimidazole antimicrobial",
        "typical_use": "trichomoniasis, giardiasis, and amoebiasis"
    },
    "ornidazole": {
        "salt": "ornidazole",
        "class": "nitroimidazole antimicrobial",
        "typical_use": "protozoal and anaerobic infections"
    },
    "faropenem": {
        "salt": "faropenem",
        "class": "penem antibiotic",
        "typical_use": "refractory respiratory or complicated urinary tract infection"
    },
    "meropenem": {
        "salt": "meropenem",
        "class": "carbapenem antibiotic",
        "typical_use": "severe hospital-acquired sepsis/pneumonia"
    },
    "ertapenem": {
        "salt": "ertapenem",
        "class": "carbapenem antibiotic",
        "typical_use": "complicated intra-abdominal and skin infections"
    },
    "imipenem": {
        "salt": "imipenem + cilastatin",
        "class": "carbapenem antibiotic",
        "typical_use": "severe multiresistant bacterial infection"
    },
    "piperacillin": {
        "salt": "piperacillin + tazobactam",
        "class": "extended-spectrum penicillin with beta-lactamase inhibitor",
        "typical_use": "severe nosocomial and intra-abdominal infection"
    },
    "vancomycin": {
        "salt": "vancomycin",
        "class": "glycopeptide antibiotic",
        "typical_use": "MRSA and severe gram-positive infection"
    },
    "linezolid": {
        "salt": "linezolid",
        "class": "oxazolidinone antibiotic",
        "typical_use": "resistant gram-positive MRSA/VRE infections"
    },
    "clindamycin": {
        "salt": "clindamycin",
        "class": "lincosamide antibiotic",
        "typical_use": "bone, joint, and soft tissue anaerobic infection"
    },
    "rifampicin": {
        "salt": "rifampicin",
        "class": "rifamycin antimycobacterial",
        "typical_use": "tuberculosis and leprosy combination therapy"
    },
    "isoniazid": {
        "salt": "isoniazid",
        "class": "first-line antitubercular agent",
        "typical_use": "tuberculosis treatment and prophylaxis"
    },
    "pyrazinamide": {
        "salt": "pyrazinamide",
        "class": "first-line antitubercular agent",
        "typical_use": "tuberculosis intensive phase"
    },
    "ethambutol": {
        "salt": "ethambutol",
        "class": "first-line antitubercular agent",
        "typical_use": "tuberculosis combination regimen"
    },
    "nitrofurantoin": {
        "salt": "nitrofurantoin",
        "class": "nitrofuran urinary antimicrobial",
        "typical_use": "acute cystitis and uncomplicated UTI"
    },
    "fosfomycin": {
        "salt": "fosfomycin trometamol",
        "class": "phosphonic acid antibacterial",
        "typical_use": "single-dose treatment of acute uncomplicated lower UTI"
    },
    "fluconazole": {
        "salt": "fluconazole",
        "class": "triazole antifungal",
        "typical_use": "candidiasis or systemic fungal infection"
    },
    "itraconazole": {
        "salt": "itraconazole",
        "class": "triazole antifungal",
        "typical_use": "dermatophyte or systemic fungal infection"
    },
    "voriconazole": {
        "salt": "voriconazole",
        "class": "triazole antifungal",
        "typical_use": "invasive aspergillosis and refractory fungal infection"
    },
    "posaconazole": {
        "salt": "posaconazole",
        "class": "triazole antifungal",
        "typical_use": "prophylaxis and treatment of invasive fungal infections"
    },
    "terbinafine": {
        "salt": "terbinafine",
        "class": "allylamine antifungal",
        "typical_use": "tinea, onychomycosis, or fungal nail infection"
    },
    "clotrimazole": {
        "salt": "clotrimazole",
        "class": "imidazole antifungal",
        "typical_use": "cutaneous and vulvovaginal candidiasis"
    },
    "miconazole": {
        "salt": "miconazole",
        "class": "imidazole antifungal",
        "typical_use": "dermatophyte and candidal infections"
    },
    "ketoconazole": {
        "salt": "ketoconazole",
        "class": "imidazole antifungal",
        "typical_use": "seborrheic dermatitis, dandruff, and fungal skin infection"
    },
    "luliconazole": {
        "salt": "luliconazole",
        "class": "imidazole antifungal",
        "typical_use": "tinea cruris, tinea corporis, and tinea pedis"
    },
    "amphotericin": {
        "salt": "liposomal amphotericin b",
        "class": "polyene antifungal",
        "typical_use": "life-threatening invasive fungal infections and mucormycosis"
    },
    "acyclovir": {
        "salt": "acyclovir",
        "class": "synthetic purine nucleoside antiviral",
        "typical_use": "herpes simplex or herpes zoster infection"
    },
    "valacyclovir": {
        "salt": "valacyclovir",
        "class": "antiviral prodrug",
        "typical_use": "herpes zoster (shingles) and genital herpes"
    },
    "ganciclovir": {
        "salt": "ganciclovir",
        "class": "antiviral nucleoside analogue",
        "typical_use": "cytomegalovirus (CMV) retinitis and systemic infection"
    },
    "oseltamivir": {
        "salt": "oseltamivir phosphate",
        "class": "neuraminidase inhibitor antiviral",
        "typical_use": "influenza A and B treatment and prophylaxis"
    },
    "remdesivir": {
        "salt": "remdesivir",
        "class": "viral RNA-dependent RNA polymerase inhibitor",
        "typical_use": "severe COVID-19 hospital management"
    },
    "nirmatrelvir": {
        "salt": "nirmatrelvir + ritonavir",
        "class": "SARS-CoV-2 main protease inhibitor",
        "typical_use": "early mild-to-moderate COVID-19 in high-risk patients"
    },
    "artemether": {
        "salt": "artemether",
        "class": "artemisinin derivative antimalarial",
        "typical_use": "malaria treatment"
    },
    "lumefantrine": {
        "salt": "lumefantrine",
        "class": "antimalarial aryl amino alcohol",
        "typical_use": "malaria combination therapy"
    },
    "artesunate": {
        "salt": "artesunate",
        "class": "artemisinin derivative antimalarial",
        "typical_use": "severe/falciparum malaria"
    },
    "chloroquine": {
        "salt": "chloroquine",
        "class": "4-aminoquinoline antimalarial",
        "typical_use": "vivax malaria prophylaxis and treatment"
    },
    "primaquine": {
        "salt": "primaquine",
        "class": "8-aminoquinoline antimalarial",
        "typical_use": "radical cure of vivax/ovale malaria hypnozoites"
    },
    "albendazole": {
        "salt": "albendazole",
        "class": "broad-spectrum anthelmintic",
        "typical_use": "intestinal worm infestation (roundworm, pinworm, hookworm, tapeworm)"
    },
    "mebendazole": {
        "salt": "mebendazole",
        "class": "anthelmintic",
        "typical_use": "gastrointestinal worm infestation"
    },
    "ivermectin": {
        "salt": "ivermectin",
        "class": "anti-parasitic macrocyclic lactone",
        "typical_use": "scabies, strongyloidiasis, and filariasis"
    },
    "diethylcarbamazine": {
        "salt": "diethylcarbamazine citrate",
        "class": "anthelmintic piperazine derivative",
        "typical_use": "lymphatic filariasis and tropical pulmonary eosinophilia"
    },
    "pantoprazole": {
        "salt": "pantoprazole",
        "class": "proton pump inhibitor",
        "typical_use": "gastric hyperacidity, GERD, and peptic ulcer"
    },
    "omeprazole": {
        "salt": "omeprazole",
        "class": "proton pump inhibitor",
        "typical_use": "acid reflux, dyspepsia, and gastric ulcer"
    },
    "rabeprazole": {
        "salt": "rabeprazole",
        "class": "proton pump inhibitor",
        "typical_use": "acid reflux, erosive esophagitis, and Zollinger-Ellison"
    },
    "esomeprazole": {
        "salt": "esomeprazole",
        "class": "proton pump inhibitor",
        "typical_use": "gastroesophageal reflux disease and NSAID gastroprotection"
    },
    "lansoprazole": {
        "salt": "lansoprazole",
        "class": "proton pump inhibitor",
        "typical_use": "peptic ulcer disease and H. pylori eradication"
    },
    "dexlansoprazole": {
        "salt": "dexlansoprazole",
        "class": "dual delayed-release PPI",
        "typical_use": "erosive esophagitis and nocturnal GERD"
    },
    "famotidine": {
        "salt": "famotidine",
        "class": "histamine H2-receptor antagonist",
        "typical_use": "gastric acid reduction and heartburn"
    },
    "ranitidine": {
        "salt": "ranitidine",
        "class": "histamine H2-receptor antagonist",
        "typical_use": "heartburn and hyperacidity"
    },
    "sucralfate": {
        "salt": "sucralfate",
        "class": "mucosal protective agent",
        "typical_use": "gastric/duodenal ulcer and stress erosion healing"
    },
    "ursodeoxycholic": {
        "salt": "ursodeoxycholic acid",
        "class": "naturally occurring bile acid",
        "typical_use": "cholesterol gallstones dissolution and primary biliary cholangitis"
    },
    "rifaximin": {
        "salt": "rifaximin",
        "class": "non-absorbable rifamycin gastrointestinal antibiotic",
        "typical_use": "irritable bowel syndrome with diarrhea (IBS-D) and hepatic encephalopathy"
    },
    "domperidone": {
        "salt": "domperidone",
        "class": "peripheral dopamine D2-receptor antagonist",
        "typical_use": "nausea, vomiting, and delayed gastric emptying"
    },
    "ondansetron": {
        "salt": "ondansetron",
        "class": "serotonin 5-HT3 receptor antagonist",
        "typical_use": "prevention and treatment of acute nausea and vomiting"
    },
    "metoclopramide": {
        "salt": "metoclopramide",
        "class": "prokinetic dopamine antagonist",
        "typical_use": "gastroesophageal reflux, nausea, and diabetic gastroparesis"
    },
    "itopride": {
        "salt": "itopride hydrochloride",
        "class": "prokinetic D2 and AChE inhibitor",
        "typical_use": "functional dyspepsia and postprandial fullness"
    },
    "levosulpiride": {
        "salt": "levosulpiride",
        "class": "dopaminergic prokinetic and neuromodulator",
        "typical_use": "functional dyspepsia, diabetic gastroparesis, and GERD"
    },
    "dicyclomine": {
        "salt": "dicyclomine hydrochloride",
        "class": "anticholinergic antispasmodic",
        "typical_use": "intestinal spasms, abdominal colic, and irritable bowel syndrome"
    },
    "mebeverine": {
        "salt": "mebeverine hydrochloride",
        "class": "musculotropic antispasmodic",
        "typical_use": "irritable bowel syndrome and abdominal cramping"
    },
    "drotaverine": {
        "salt": "drotaverine hydrochloride",
        "class": "phosphodiesterase-4 inhibitor antispasmodic",
        "typical_use": "smooth muscle colic, renal colic, and biliary spasm"
    },
    "loperamide": {
        "salt": "loperamide hydrochloride",
        "class": "peripheral opioid receptor agonist antidiarrheal",
        "typical_use": "acute non-infectious diarrhea and travelers diarrhea"
    },
    "lactulose": {
        "salt": "lactulose",
        "class": "synthetic disaccharide osmotic laxative",
        "typical_use": "chronic constipation and hepatic encephalopathy"
    },
    "polyethylene_glycol": {
        "salt": "polyethylene glycol 3350",
        "class": "osmotic laxative",
        "typical_use": "chronic constipation and bowel preparation"
    },
    "bisacodyl": {
        "salt": "bisacodyl",
        "class": "stimulant diphenylmethane laxative",
        "typical_use": "short-term relief of occasional constipation"
    },
    "mesalamine": {
        "salt": "mesalamine (5-aminosalicylic acid)",
        "class": "anti-inflammatory aminosalicylate",
        "typical_use": "ulcerative colitis induction and maintenance of remission"
    },
    "telmisartan": {
        "salt": "telmisartan",
        "class": "angiotensin II receptor blocker (arb)",
        "typical_use": "essential hypertension and cardiovascular risk reduction"
    },
    "losartan": {
        "salt": "losartan potassium",
        "class": "angiotensin II receptor blocker (arb)",
        "typical_use": "hypertension and diabetic nephropathy in type 2 diabetes"
    },
    "olmesartan": {
        "salt": "olmesartan medoxomil",
        "class": "angiotensin II receptor blocker (arb)",
        "typical_use": "essential hypertension"
    },
    "valsartan": {
        "salt": "valsartan",
        "class": "angiotensin II receptor blocker (arb)",
        "typical_use": "hypertension, heart failure, and post-myocardial infarction"
    },
    "ramipril": {
        "salt": "ramipril",
        "class": "angiotensin-converting enzyme (ace) inhibitor",
        "typical_use": "hypertension, heart failure, and post-infarction nephroprotection"
    },
    "enalapril": {
        "salt": "enalapril maleate",
        "class": "angiotensin-converting enzyme (ace) inhibitor",
        "typical_use": "hypertension and symptomatic congestive heart failure"
    },
    "lisinopril": {
        "salt": "lisinopril",
        "class": "ace inhibitor",
        "typical_use": "hypertension and acute myocardial infarction recovery"
    },
    "amlodipine": {
        "salt": "amlodipine besylate",
        "class": "dihydropyridine calcium channel blocker",
        "typical_use": "hypertension and chronic stable angina"
    },
    "cilnidipine": {
        "salt": "cilnidipine",
        "class": "dual L/N-type calcium channel blocker",
        "typical_use": "hypertension with tachycardia, proteinuria, or renal impairment"
    },
    "nifedipine": {
        "salt": "nifedipine",
        "class": "dihydropyridine calcium channel blocker",
        "typical_use": "chronic hypertension, angina, and Raynaud phenomenon"
    },
    "diltiazem": {
        "salt": "diltiazem hydrochloride",
        "class": "non-dihydropyridine calcium channel blocker",
        "typical_use": "angina pectoris, rate control in atrial fibrillation, and hypertension"
    },
    "verapamil": {
        "salt": "verapamil hydrochloride",
        "class": "phenylalkylamine calcium channel blocker",
        "typical_use": "supraventricular tachycardia, rate control in AF, and angina"
    },
    "bisoprolol": {
        "salt": "bisoprolol fumarate",
        "class": "cardioselective beta-1 adrenergic blocker",
        "typical_use": "hypertension and stable chronic heart failure with reduced EF"
    },
    "metoprolol": {
        "salt": "metoprolol succinate/tartrate",
        "class": "selective beta-1 adrenergic blocker",
        "typical_use": "hypertension, angina pectoris, and post-myocardial infarction"
    },
    "nebivolol": {
        "salt": "nebivolol hydrochloride",
        "class": "third-generation vasodilating beta-1 blocker with nitric oxide release",
        "typical_use": "hypertension and chronic mild-to-moderate heart failure"
    },
    "carvedilol": {
        "salt": "carvedilol",
        "class": "non-selective beta and alpha-1 blocker with antioxidant action",
        "typical_use": "congestive heart failure, left ventricular dysfunction, and hypertension"
    },
    "atenolol": {
        "salt": "atenolol",
        "class": "cardioselective beta-1 adrenergic blocker",
        "typical_use": "hypertension, angina, and secondary prevention post-MI"
    },
    "propranolol": {
        "salt": "propranolol hydrochloride",
        "class": "non-selective beta blocker",
        "typical_use": "tremors, migraine prophylaxis, performance anxiety, and portal hypertension"
    },
    "torsemide": {
        "salt": "torsemide",
        "class": "loop diuretic with antialdosterone properties",
        "typical_use": "edema associated with congestive heart failure, renal or hepatic disease"
    },
    "furosemide": {
        "salt": "furosemide",
        "class": "high-ceiling loop diuretic",
        "typical_use": "acute and chronic edema, pulmonary congestion, and fluid overload"
    },
    "spironolactone": {
        "salt": "spironolactone",
        "class": "aldosterone receptor antagonist / potassium-sparing diuretic",
        "typical_use": "heart failure with reduced EF, resistant hypertension, and ascites"
    },
    "eplerenone": {
        "salt": "eplerenone",
        "class": "selective mineralocorticoid receptor antagonist",
        "typical_use": "heart failure post-MI and hypertension"
    },
    "hydrochlorothiazide": {
        "salt": "hydrochlorothiazide",
        "class": "thiazide diuretic",
        "typical_use": "essential hypertension and mild fluid retention"
    },
    "chlorthalidone": {
        "salt": "chlorthalidone",
        "class": "long-acting thiazide-like diuretic",
        "typical_use": "hypertension and cardiovascular event risk reduction"
    },
    "indapamide": {
        "salt": "indapamide",
        "class": "thiazide-like indole diuretic",
        "typical_use": "essential hypertension in elderly and diabetic patients"
    },
    "clonidine": {
        "salt": "clonidine hydrochloride",
        "class": "central alpha-2 adrenergic agonist",
        "typical_use": "resistant hypertension and hypertensive urgency"
    },
    "prazosin": {
        "salt": "prazosin hydrochloride",
        "class": "selective alpha-1 adrenergic blocker",
        "typical_use": "hypertension, benign prostatic hyperplasia, and Raynaud disease"
    },
    "digoxin": {
        "salt": "digoxin",
        "class": "cardiac glycoside inotropic agent",
        "typical_use": "ventricular rate control in atrial fibrillation and severe systolic heart failure"
    },
    "amiodarone": {
        "salt": "amiodarone hydrochloride",
        "class": "class III antiarrhythmic agent",
        "typical_use": "recurrent ventricular arrhythmias and atrial fibrillation conversion"
    },
    "ivabradine": {
        "salt": "ivabradine hydrochloride",
        "class": "hyperpolarization-activated cyclic nucleotide-gated (HCN) channel blocker",
        "typical_use": "heart failure with resting heart rate >= 70 bpm and chronic stable angina"
    },
    "sacubitril": {
        "salt": "sacubitril + valsartan (ARNI)",
        "class": "angiotensin receptor-neprilysin inhibitor",
        "typical_use": "chronic heart failure with reduced ejection fraction (HFrEF)"
    },
    "nitroglycerin": {
        "salt": "glyceryl trinitrate",
        "class": "organic nitrate vasodilator",
        "typical_use": "acute relief and prophylaxis of angina pectoris"
    },
    "isosorbide_mononitrate": {
        "salt": "isosorbide-5-mononitrate",
        "class": "long-acting nitrate vasodilator",
        "typical_use": "maintenance therapy and prophylaxis of angina pectoris"
    },
    "metformin": {
        "salt": "metformin hydrochloride",
        "class": "biguanide antidiabetic",
        "typical_use": "first-line therapy for type 2 diabetes mellitus and PCOS"
    },
    "glimepiride": {
        "salt": "glimepiride",
        "class": "second-generation sulfonylurea",
        "typical_use": "type 2 diabetes mellitus glycemic control"
    },
    "glipizide": {
        "salt": "glipizide",
        "class": "second-generation sulfonylurea",
        "typical_use": "type 2 diabetes mellitus"
    },
    "gliclazide": {
        "salt": "gliclazide",
        "class": "second-generation sulfonylurea with antioxidant action",
        "typical_use": "type 2 diabetes mellitus with microvascular protection"
    },
    "glibenclamide": {
        "salt": "glibenclamide",
        "class": "second-generation sulfonylurea",
        "typical_use": "type 2 diabetes mellitus"
    },
    "vildagliptin": {
        "salt": "vildagliptin",
        "class": "dipeptidyl peptidase-4 (dpp-4) inhibitor",
        "typical_use": "type 2 diabetes mellitus postprandial glucose regulation"
    },
    "sitagliptin": {
        "salt": "sitagliptin",
        "class": "dipeptidyl peptidase-4 (dpp-4) inhibitor",
        "typical_use": "type 2 diabetes mellitus monotherapy or add-on"
    },
    "linagliptin": {
        "salt": "linagliptin",
        "class": "dpp-4 inhibitor with primarily non-renal excretion",
        "typical_use": "type 2 diabetes mellitus safe in renal impairment without dose adjustment"
    },
    "teneligliptin": {
        "salt": "teneligliptin",
        "class": "dpp-4 inhibitor",
        "typical_use": "type 2 diabetes mellitus glycemic management"
    },
    "dapagliflozin": {
        "salt": "dapagliflozin",
        "class": "sodium-glucose cotransporter 2 (sglt2) inhibitor",
        "typical_use": "type 2 diabetes, heart failure (HFrEF/HFpEF), and chronic kidney disease"
    },
    "empagliflozin": {
        "salt": "empagliflozin",
        "class": "sodium-glucose cotransporter 2 (sglt2) inhibitor",
        "typical_use": "type 2 diabetes with cardiovascular risk reduction and heart failure"
    },
    "canagliflozin": {
        "salt": "canagliflozin",
        "class": "sglt2 inhibitor",
        "typical_use": "type 2 diabetes and diabetic nephropathy with albuminuria"
    },
    "pioglitazone": {
        "salt": "pioglitazone hydrochloride",
        "class": "thiazolidinedione (tzd) insulin sensitizer",
        "typical_use": "insulin resistance in type 2 diabetes mellitus and NAFLD"
    },
    "voglibose": {
        "salt": "voglibose",
        "class": "alpha-glucosidase inhibitor",
        "typical_use": "delaying postprandial glucose spikes in type 2 diabetes"
    },
    "acarbose": {
        "salt": "acarbose",
        "class": "alpha-glucosidase inhibitor",
        "typical_use": "postprandial hyperglycemia control in type 2 diabetes"
    },
    "semaglutide": {
        "salt": "semaglutide",
        "class": "glucagon-like peptide-1 (glp-1) receptor agonist",
        "typical_use": "type 2 diabetes glycemic control, cardiovascular protection, and chronic weight management"
    },
    "liraglutide": {
        "salt": "liraglutide",
        "class": "glp-1 receptor agonist",
        "typical_use": "type 2 diabetes and chronic obesity management"
    },
    "dulaglutide": {
        "salt": "dulaglutide",
        "class": "once-weekly glp-1 receptor agonist",
        "typical_use": "type 2 diabetes glycemic and cardiovascular risk control"
    },
    "insulin_glargine": {
        "salt": "insulin glargine (rDNA origin)",
        "class": "long-acting peakless basal insulin analogue",
        "typical_use": "basal glycemic control in type 1 and type 2 diabetes mellitus"
    },
    "insulin_aspart": {
        "salt": "insulin aspart",
        "class": "rapid-acting prandial insulin analogue",
        "typical_use": "postprandial glucose control in diabetes mellitus"
    },
    "insulin_lispro": {
        "salt": "insulin lispro",
        "class": "rapid-acting insulin analogue",
        "typical_use": "mealtime glucose surge management in diabetes"
    },
    "insulin_degludec": {
        "salt": "insulin degludec",
        "class": "ultra-long-acting basal insulin",
        "typical_use": "once-daily basal insulin therapy for diabetes"
    },
    "levothyroxine": {
        "salt": "levothyroxine sodium",
        "class": "synthetic thyroid hormone (t4)",
        "typical_use": "primary, secondary, and tertiary hypothyroidism"
    },
    "carbimazole": {
        "salt": "carbimazole",
        "class": "antithyroid thionamide prodrug",
        "typical_use": "hyperthyroidism, Graves disease, and thyrotoxic crisis prep"
    },
    "methimazole": {
        "salt": "methimazole",
        "class": "antithyroid thionamide",
        "typical_use": "hyperthyroidism and preparation for thyroidectomy or radioiodine"
    },
    "atorvastatin": {
        "salt": "atorvastatin calcium",
        "class": "hmg-coa reductase inhibitor (statin)",
        "typical_use": "hypercholesterolemia, dyslipidemia, and primary/secondary ASCVD prevention"
    },
    "rosuvastatin": {
        "salt": "rosuvastatin calcium",
        "class": "potent hmg-coa reductase inhibitor (statin)",
        "typical_use": "hypercholesterolemia, familial dyslipidemia, and atherosclerotic risk reduction"
    },
    "simvastatin": {
        "salt": "simvastatin",
        "class": "hmg-coa reductase inhibitor (statin)",
        "typical_use": "hyperlipidemia and coronary artery disease prevention"
    },
    "fenofibrate": {
        "salt": "fenofibrate / fenofibric acid",
        "class": "fibric acid derivative (fibrate)",
        "typical_use": "severe hypertriglyceridemia and mixed dyslipidemia"
    },
    "ezetimibe": {
        "salt": "ezetimibe",
        "class": "cholesterol absorption inhibitor (npc1l1 blocker)",
        "typical_use": "hypercholesterolemia add-on to statin therapy"
    },
    "saroglitazar": {
        "salt": "saroglitazar",
        "class": "dual PPAR-alpha/gamma agonist",
        "typical_use": "diabetic dyslipidemia and non-alcoholic steatohepatitis (NASH)"
    },
    "aspirin": {
        "salt": "acetylsalicylic acid",
        "class": "irreversible cyclooxygenase (cox-1) inhibitor antiplatelet",
        "typical_use": "secondary prevention of myocardial infarction, stroke, and acute coronary syndrome"
    },
    "clopidogrel": {
        "salt": "clopidogrel bisulfate",
        "class": "thienopyridine p2y12 platelet inhibitor",
        "typical_use": "prevention of atherothrombotic events in CAD, stroke, and post-stent placement"
    },
    "ticagrelor": {
        "salt": "ticagrelor",
        "class": "reversible direct-acting oral p2y12 receptor antagonist",
        "typical_use": "acute coronary syndrome and high ischemic risk coronary disease"
    },
    "prasugrel": {
        "salt": "prasugrel hydrochloride",
        "class": "potent third-generation thienopyridine p2y12 inhibitor",
        "typical_use": "thrombotic event prevention during percutaneous coronary intervention (PCI)"
    },
    "warfarin": {
        "salt": "warfarin sodium",
        "class": "vitamin K antagonist oral anticoagulant",
        "typical_use": "mechanical heart valve thrombosis prophylaxis, DVT, and atrial fibrillation"
    },
    "acenocoumarol": {
        "salt": "acenocoumarol (nicoumalone)",
        "class": "coumarin derivative anticoagulant",
        "typical_use": "thromboembolism prevention and deep vein thrombosis management"
    },
    "apixaban": {
        "salt": "apixaban",
        "class": "direct factor Xa inhibitor novel oral anticoagulant (doac)",
        "typical_use": "stroke prevention in non-valvular atrial fibrillation and DVT/PE treatment"
    },
    "rivaroxaban": {
        "salt": "rivaroxaban",
        "class": "direct oral factor Xa inhibitor (doac)",
        "typical_use": "prevention and treatment of DVT, pulmonary embolism, and stroke in AF"
    },
    "dabigatran": {
        "salt": "dabigatran etexilate",
        "class": "direct thrombin (factor IIa) inhibitor (doac)",
        "typical_use": "stroke prophylaxis in non-valvular atrial fibrillation and venous thromboembolism"
    },
    "heparin": {
        "salt": "unfractionated heparin / low molecular weight heparin (enoxaparin)",
        "class": "parenteral anticoagulant",
        "typical_use": "acute DVT, pulmonary embolism, and unstable angina"
    },
    "paracetamol": {
        "salt": "paracetamol (acetaminophen)",
        "class": "analgesic and antipyretic",
        "typical_use": "mild-to-moderate pain, headache, and fever reduction"
    },
    "ibuprofen": {
        "salt": "ibuprofen",
        "class": "non-steroidal anti-inflammatory drug (nsaid)",
        "typical_use": "inflammatory pain, dysmenorrhea, dental ache, and musculoskeletal stiffness"
    },
    "aceclofenac": {
        "salt": "aceclofenac",
        "class": "preferential cox-2 inhibitor nsaid",
        "typical_use": "osteoarthritis, rheumatoid arthritis, ankylosing spondylitis, and acute lumbago"
    },
    "diclofenac": {
        "salt": "diclofenac sodium / potassium",
        "class": "potent non-steroidal anti-inflammatory drug (nsaid)",
        "typical_use": "acute musculoskeletal trauma, gout flares, and inflammatory arthropathies"
    },
    "nimesulide": {
        "salt": "nimesulide",
        "class": "preferential cox-2 inhibitor nsaid",
        "typical_use": "acute painful musculoskeletal trauma and severe inflammatory conditions"
    },
    "etoricoxib": {
        "salt": "etoricoxib",
        "class": "selective cox-2 inhibitor nsaid",
        "typical_use": "acute gouty arthritis, ankylosing spondylitis, and postoperative dental pain"
    },
    "celecoxib": {
        "salt": "celecoxib",
        "class": "selective cox-2 inhibitor nsaid",
        "typical_use": "osteoarthritis, rheumatoid arthritis, and acute pain with gastrointestinal safety"
    },
    "tramadol": {
        "salt": "tramadol hydrochloride",
        "class": "centrally acting opioid and SNRI analgesic",
        "typical_use": "moderate to moderately severe acute or chronic post-surgical and neuropathic pain"
    },
    "thiocolchicoside": {
        "salt": "thiocolchicoside",
        "class": "semi-synthetic colchicoside muscle relaxant and GABA-A modulator",
        "typical_use": "painful skeletal muscle spasms, torticollis, and acute low back pain"
    },
    "chlorzoxazone": {
        "salt": "chlorzoxazone",
        "class": "centrally acting skeletal muscle relaxant",
        "typical_use": "acute painful muscle spasms and sprains"
    },
    "baclofen": {
        "salt": "baclofen",
        "class": "centrally acting GABA-B agonist muscle relaxant",
        "typical_use": "severe spasticity resulting from spinal cord injury or multiple sclerosis"
    },
    "tizanidine": {
        "salt": "tizanidine hydrochloride",
        "class": "central alpha-2 adrenergic agonist muscle relaxant",
        "typical_use": "chronic muscle spasticity, spinal disorders, and tension headaches"
    },
    "serratiopeptidase": {
        "salt": "serratiopeptidase",
        "class": "proteolytic anti-inflammatory enzyme",
        "typical_use": "reduction of post-traumatic edema, swelling, and surgical hematoma"
    },
    "febuxostat": {
        "salt": "febuxostat",
        "class": "non-purine selective xanthine oxidase inhibitor",
        "typical_use": "chronic management of hyperuricemia and prevention of gout flares"
    },
    "allopurinol": {
        "salt": "allopurinol",
        "class": "purine analog xanthine oxidase inhibitor",
        "typical_use": "hyperuricemia, chronic gout prophylaxis, and uric acid nephrolithiasis"
    },
    "colchicine": {
        "salt": "colchicine",
        "class": "anti-gout alkaloid tubulin inhibitor",
        "typical_use": "acute gouty arthritis flares and familial Mediterranean fever"
    },
    "prednisolone": {
        "salt": "prednisolone",
        "class": "systemic synthetic corticosteroid",
        "typical_use": "severe inflammatory, allergic, and autoimmune disorders"
    },
    "methylprednisolone": {
        "salt": "methylprednisolone",
        "class": "intermediate-acting systemic glucocorticoid",
        "typical_use": "severe asthma exacerbation, anaphylaxis, and acute autoimmune flares"
    },
    "deflazacort": {
        "salt": "deflazacort",
        "class": "systemic glucocorticoid with reduced bone/metabolic side effects",
        "typical_use": "autoimmune diseases, nephrotic syndrome, and Duchenne muscular dystrophy"
    },
    "dexamethasone": {
        "salt": "dexamethasone",
        "class": "high-potency long-acting systemic glucocorticoid",
        "typical_use": "cerebral edema, acute croup, severe inflammatory states, and antiemetic adjuvant"
    },
    "methotrexate": {
        "salt": "methotrexate",
        "class": "antifolate disease-modifying antirheumatic drug (dmard)",
        "typical_use": "rheumatoid arthritis, psoriasis, and neoplastic disorders"
    },
    "hydroxychloroquine": {
        "salt": "hydroxychloroquine sulfate",
        "class": "antimalarial and immunomodulatory dmard",
        "typical_use": "systemic lupus erythematosus (SLE) and rheumatoid arthritis"
    },
    "sulfasalazine": {
        "salt": "sulfasalazine",
        "class": "anti-inflammatory and dmard azo conjugate",
        "typical_use": "rheumatoid arthritis, ulcerative colitis, and Crohn disease"
    },
    "cetirizine": {
        "salt": "cetirizine hydrochloride",
        "class": "second-generation piperazine antihistamine",
        "typical_use": "allergic rhinitis, hay fever, and chronic idiopathic urticaria"
    },
    "levocetirizine": {
        "salt": "levocetirizine dihydrochloride",
        "class": "active R-enantiomer second-generation antihistamine",
        "typical_use": "allergic rhinitis, seasonal allergies, and chronic pruritus"
    },
    "fexofenadine": {
        "salt": "fexofenadine hydrochloride",
        "class": "non-sedating second-generation antihistamine",
        "typical_use": "seasonal allergic rhinitis and chronic idiopathic urticaria without sedation"
    },
    "bilastine": {
        "salt": "bilastine",
        "class": "second-generation non-sedating piperidine antihistamine",
        "typical_use": "allergic rhinoconjunctivitis and pruritic skin flares"
    },
    "montelukast": {
        "salt": "montelukast sodium",
        "class": "leukotriene receptor antagonist (ltra)",
        "typical_use": "prophylaxis and chronic treatment of asthma and allergic rhinitis"
    },
    "salbutamol": {
        "salt": "salbutamol (albuterol) sulphate",
        "class": "short-acting beta-2 adrenergic agonist (saba) bronchodilator",
        "typical_use": "quick relief of acute bronchospasm in asthma and COPD"
    },
    "levosalbutamol": {
        "salt": "levosalbutamol (levalbuterol)",
        "class": "pure (R)-enantiomer short-acting beta-2 agonist",
        "typical_use": "acute bronchodilation with lower tachycardia incidence"
    },
    "formoterol": {
        "salt": "formoterol fumarate",
        "class": "long-acting rapid-onset beta-2 agonist (laba)",
        "typical_use": "long-term maintenance bronchodilation and SMART therapy in asthma/COPD"
    },
    "salmeterol": {
        "salt": "salmeterol xinafoate",
        "class": "long-acting beta-2 adrenergic agonist (laba)",
        "typical_use": "chronic maintenance controller for persistent asthma and COPD"
    },
    "ipratropium": {
        "salt": "ipratropium bromide",
        "class": "short-acting anticholinergic (sama) bronchodilator",
        "typical_use": "bronchospasm relief in COPD and severe acute asthma exacerbations"
    },
    "tiotropium": {
        "salt": "tiotropium bromide",
        "class": "long-acting muscarinic antagonist (lama) bronchodilator",
        "typical_use": "maintenance therapy for chronic obstructive pulmonary disease (COPD) and asthma"
    },
    "budesonide": {
        "salt": "budesonide",
        "class": "inhaled corticosteroid (ics)",
        "typical_use": "first-line anti-inflammatory maintenance controller for asthma and croup"
    },
    "fluticasone": {
        "salt": "fluticasone propionate / furoate",
        "class": "potent inhaled/intranasal corticosteroid",
        "typical_use": "allergic rhinitis nasal sprays and chronic asthma controller inhalers"
    },
    "beclomethasone": {
        "salt": "beclomethasone dipropionate",
        "class": "inhaled corticosteroid",
        "typical_use": "chronic asthma prophylaxis and maintenance therapy"
    },
    "dextromethorphan": {
        "salt": "dextromethorphan hydrobromide",
        "class": "centrally acting NMDA receptor antagonist antitussive",
        "typical_use": "temporary symptomatic suppression of dry, non-productive cough"
    },
    "ambroxol": {
        "salt": "ambroxol hydrochloride",
        "class": "secretolytic and mucolytic agent",
        "typical_use": "viscous mucus clearance in acute and chronic bronchitis"
    },
    "guaiphenesin": {
        "salt": "guaiphenesin",
        "class": "expectorant",
        "typical_use": "loosening thick chest phlegm and bronchial secretions"
    },
    "bromhexine": {
        "salt": "bromhexine hydrochloride",
        "class": "mucolytic agent",
        "typical_use": "respiratory tract disorders with excessive or sticky mucus"
    },
    "xylometazoline": {
        "salt": "xylometazoline hydrochloride",
        "class": "topical alpha-adrenergic sympathomimetic decongestant",
        "typical_use": "temporary relief of nasal congestion from cold, sinusitis, or allergies"
    },
    "oxymetazoline": {
        "salt": "oxymetazoline hydrochloride",
        "class": "long-acting topical nasal decongestant",
        "typical_use": "fast relief of acute nasal and sinus congestion"
    },
    "escitalopram": {
        "salt": "escitalopram oxalate",
        "class": "selective serotonin reuptake inhibitor (ssri)",
        "typical_use": "major depressive disorder, generalized anxiety disorder (GAD), and panic attacks"
    },
    "sertraline": {
        "salt": "sertraline hydrochloride",
        "class": "selective serotonin reuptake inhibitor (ssri)",
        "typical_use": "major depression, OCD, PTSD, and social anxiety disorder"
    },
    "fluoxetine": {
        "salt": "fluoxetine hydrochloride",
        "class": "selective serotonin reuptake inhibitor (ssri)",
        "typical_use": "major depressive disorder, bulimia nervosa, and panic disorder"
    },
    "duloxetine": {
        "salt": "duloxetine hydrochloride",
        "class": "serotonin-norepinephrine reuptake inhibitor (snri)",
        "typical_use": "depression, generalized anxiety, diabetic peripheral neuropathic pain, and fibromyalgia"
    },
    "venlafaxine": {
        "salt": "venlafaxine hydrochloride",
        "class": "serotonin-norepinephrine reuptake inhibitor (snri)",
        "typical_use": "major depression, social phobia, and generalized anxiety"
    },
    "amitriptyline": {
        "salt": "amitriptyline hydrochloride",
        "class": "tricyclic antidepressant (tca)",
        "typical_use": "chronic neuropathic pain, fibromyalgia, and nocturnal migraine prophylaxis"
    },
    "nortriptyline": {
        "salt": "nortriptyline hydrochloride",
        "class": "tricyclic antidepressant (tca)",
        "typical_use": "neuropathic pain and depressive disorders"
    },
    "pregabalin": {
        "salt": "pregabalin",
        "class": "voltage-gated calcium channel alpha-2-delta ligand",
        "typical_use": "peripheral neuropathic pain, post-herpetic neuralgia, fibromyalgia, and GAD"
    },
    "gabapentin": {
        "salt": "gabapentin",
        "class": "gaba analogue calcium channel modulator",
        "typical_use": "diabetic neuropathy, post-herpetic neuralgia, and partial seizures"
    },
    "clonazepam": {
        "salt": "clonazepam",
        "class": "high-potency benzodiazepine anticonvulsant and anxiolytic",
        "typical_use": "panic disorder, acute seizure disorders, and severe anxiety"
    },
    "alprazolam": {
        "salt": "alprazolam",
        "class": "short-acting triazolobenzodiazepine",
        "typical_use": "acute panic attacks and short-term anxiety relief"
    },
    "lorazepam": {
        "salt": "lorazepam",
        "class": "intermediate-acting benzodiazepine",
        "typical_use": "acute agitation, status epilepticus, and pre-procedural anxiety"
    },
    "diazepam": {
        "salt": "diazepam",
        "class": "long-acting benzodiazepine",
        "typical_use": "acute muscular spasm, alcohol withdrawal, and seizure emergency"
    },
    "zolpidem": {
        "salt": "zolpidem tartrate",
        "class": "non-benzodiazepine GABA-A receptor positive modulator (z-drug)",
        "typical_use": "short-term pharmacological management of acute insomnia"
    },
    "levetiracetam": {
        "salt": "levetiracetam",
        "class": "synaptic vesicle protein 2A (SV2A) ligand antiepileptic",
        "typical_use": "focal onset, myoclonic, and generalized tonic-clonic seizures"
    },
    "sodium_valproate": {
        "salt": "sodium valproate / divalproex sodium",
        "class": "broad-spectrum antiepileptic and mood stabilizer",
        "typical_use": "generalized/focal epilepsy, acute bipolar mania, and migraine prophylaxis"
    },
    "carbamazepine": {
        "salt": "carbamazepine",
        "class": "voltage-gated sodium channel blocker anticonvulsant",
        "typical_use": "focal epileptic seizures and trigeminal neuralgia"
    },
    "oxcarbazepine": {
        "salt": "oxcarbazepine",
        "class": "voltage-sensitive sodium channel blocker anticonvulsant",
        "typical_use": "monotherapy and adjunctive therapy for partial onset seizures"
    },
    "lamotrigine": {
        "salt": "lamotrigine",
        "class": "phenyltriazine antiepileptic and mood stabilizer",
        "typical_use": "bipolar I depression maintenance and refractory partial seizures"
    },
    "olanzapine": {
        "salt": "olanzapine",
        "class": "second-generation atypical antipsychotic",
        "typical_use": "schizophrenia and acute bipolar manic or mixed episodes"
    },
    "risperidone": {
        "salt": "risperidone",
        "class": "atypical benzisoxazole antipsychotic",
        "typical_use": "schizophrenia, bipolar mania, and irritability associated with autistic disorder"
    },
    "quetiapine": {
        "salt": "quetiapine fumarate",
        "class": "atypical dibenzothiazepine antipsychotic",
        "typical_use": "schizophrenia, bipolar depression, and major depressive augmentation"
    },
    "aripiprazole": {
        "salt": "aripiprazole",
        "class": "atypical dopamine D2 partial agonist antipsychotic",
        "typical_use": "schizophrenia, bipolar I maintenance, and depressive add-on"
    },
    "haloperidol": {
        "salt": "haloperidol",
        "class": "first-generation typical butyrophenone antipsychotic",
        "typical_use": "acute psychiatric delirium, psychosis, and Tourette disorder"
    },
    "betahistine": {
        "salt": "betahistine dihydrochloride",
        "class": "histaminergic H1 agonist / H3 antagonist",
        "typical_use": "vertigo, tinnitus, and hearing loss in Meniere disease"
    },
    "cinnarizine": {
        "salt": "cinnarizine",
        "class": "piperazine antihistamine and calcium channel antagonist",
        "typical_use": "vestibular vertigo, motion sickness, and peripheral vascular disease"
    },
    "flunarizine": {
        "salt": "flunarizine hydrochloride",
        "class": "selective calcium entry blocker",
        "typical_use": "prophylaxis of classical and common migraine, and vestibular vertigo"
    },
    "levodopa": {
        "salt": "levodopa + carbidopa",
        "class": "dopamine precursor with peripheral dopa-decarboxylase inhibitor",
        "typical_use": "Parkinson disease and post-encephalitic parkinsonism"
    },
    "donepezil": {
        "salt": "donepezil hydrochloride",
        "class": "reversible acetylcholinesterase inhibitor",
        "typical_use": "mild to moderately severe dementia in Alzheimer disease"
    },
    "memantine": {
        "salt": "memantine hydrochloride",
        "class": "uncompetitive NMDA receptor antagonist",
        "typical_use": "moderate to severe Alzheimer disease dementia"
    },
    "tamsulosin": {
        "salt": "tamsulosin hydrochloride",
        "class": "selective alpha-1A adrenergic receptor antagonist",
        "typical_use": "benign prostatic hyperplasia (BPH) urinary flow improvement"
    },
    "silodosin": {
        "salt": "silodosin",
        "class": "highly selective alpha-1A adrenergic blocker",
        "typical_use": "urinary symptoms of benign prostatic hyperplasia with minimal hypotension"
    },
    "alfuzosin": {
        "salt": "alfuzosin hydrochloride",
        "class": "uroselective alpha-1 adrenergic blocker",
        "typical_use": "lower urinary tract symptoms suggestive of benign prostatic hyperplasia"
    },
    "dutasteride": {
        "salt": "dutasteride",
        "class": "dual 5-alpha reductase type I and II inhibitor",
        "typical_use": "reduction of prostate enlargement and prevention of acute urinary retention"
    },
    "finasteride": {
        "salt": "finasteride",
        "class": "type II 5-alpha reductase inhibitor",
        "typical_use": "benign prostatic hyperplasia (5mg) and male androgenetic alopecia (1mg)"
    },
    "sildenafil": {
        "salt": "sildenafil citrate",
        "class": "phosphodiesterase type 5 (pde-5) inhibitor",
        "typical_use": "erectile dysfunction and pulmonary arterial hypertension (PAH)"
    },
    "tadalafil": {
        "salt": "tadalafil",
        "class": "long-acting pde-5 inhibitor",
        "typical_use": "erectile dysfunction, pulmonary hypertension, and BPH urinary symptoms"
    },
    "potassium_citrate": {
        "salt": "potassium citrate + citric acid",
        "class": "urinary alkalinizing agent",
        "typical_use": "alkalization of urine, prevention of uric acid and calcium oxalate kidney stones"
    },
    "cholecalciferol": {
        "salt": "cholecalciferol (vitamin d3)",
        "class": "fat-soluble secosteroid hormone precursor",
        "typical_use": "vitamin D deficiency, hypocalcemia, osteomalacia, and osteoporosis"
    },
    "calcium_carbonate": {
        "salt": "calcium carbonate + vitamin d3",
        "class": "dietary calcium and mineral supplement",
        "typical_use": "calcium replenishment in pregnancy, lactation, and postmenopausal bone loss"
    },
    "methylcobalamin": {
        "salt": "methylcobalamin (vitamin b12)",
        "class": "neurologically active water-soluble cobalamin coenzyme",
        "typical_use": "peripheral neuropathy, megaloblastic anemia, and vitamin B12 deficiency"
    },
    "folic_acid": {
        "salt": "folic acid (vitamin b9)",
        "class": "essential water-soluble B vitamin",
        "typical_use": "prevention of neural tube birth defects in pregnancy and nutritional macrocytic anemia"
    },
    "ferrous_ascorbate": {
        "salt": "ferrous ascorbate + folic acid",
        "class": "highly bioavailable elemental iron supplement",
        "typical_use": "iron deficiency anemia and nutritional support in pregnancy"
    },
    "pyridoxine": {
        "salt": "pyridoxine hydrochloride (vitamin b6)",
        "class": "essential water-soluble vitamin",
        "typical_use": "peripheral neuropathy prevention during isoniazid therapy and morning sickness"
    },
    "ascorbic_acid": {
        "salt": "ascorbic acid (vitamin c)",
        "class": "water-soluble antioxidant vitamin",
        "typical_use": "scurvy prophylaxis, collagen synthesis, and wound healing support"
    },
    "tocopherol": {
        "salt": "alpha-tocopheryl acetate (vitamin e)",
        "class": "lipid-soluble chain-breaking antioxidant",
        "typical_use": "skin barrier support, muscle cramps, and antioxidant therapy"
    },
    "norethisterone": {
        "salt": "norethisterone (norethindrone)",
        "class": "synthetic second-generation 19-nortestosterone progestin",
        "typical_use": "abnormal uterine bleeding, menorrhagia, endometriosis, and menses timing postponement"
    },
    "progesterone": {
        "salt": "natural micronized progesterone",
        "class": "bioidentical corpus luteum hormone",
        "typical_use": "threatened miscarriage, luteal phase support, and secondary amenorrhea"
    },
    "dydrogesterone": {
        "salt": "dydrogesterone",
        "class": "retroprogesterone oral progestogen",
        "typical_use": "habitual abortion, luteal insufficiency, dysmenorrhea, and endometriosis"
    },
    "levonorgestrel": {
        "salt": "levonorgestrel",
        "class": "second-generation synthetic progestin",
        "typical_use": "emergency post-coital contraception within 72 hours and oral contraception"
    },
    "misoprostol": {
        "salt": "misoprostol",
        "class": "synthetic prostaglandin E1 (PGE1) analog",
        "typical_use": "prevention of NSAID-induced gastric ulcers and post-partum hemorrhage"
    },
    "mifepristone": {
        "salt": "mifepristone",
        "class": "selective synthetic progesterone receptor antagonist",
        "typical_use": "medical termination of intrauterine pregnancy up to 63 days with misoprostol"
    }
}

# ------------------------------------------------------------------------------
# 2. CANONICAL REGISTERED BRAND DATABASE (CDSCO / IP / PACKAGE INSERTS / FDA)
# ------------------------------------------------------------------------------
RAW_BRAND_DATABASE = {
    "augmentin": {
        "salt": "amoxicillin + clavulanic acid",
        "class": "penicillin antibiotic with beta-lactamase inhibitor",
        "typical_use": "bacterial respiratory/skin infection"
    },
    "clavam": {
        "salt": "amoxicillin + clavulanic acid",
        "class": "penicillin antibiotic with beta-lactamase inhibitor",
        "typical_use": "bacterial infection"
    },
    "moxikind": {
        "salt": "amoxicillin + clavulanic acid",
        "class": "penicillin antibiotic with beta-lactamase inhibitor",
        "typical_use": "bacterial infection"
    },
    "novamox": {
        "salt": "amoxicillin",
        "class": "penicillin antibiotic",
        "typical_use": "bacterial infection"
    },
    "mox": {
        "salt": "amoxicillin",
        "class": "penicillin antibiotic",
        "typical_use": "bacterial infection"
    },
    "ciplox": {
        "salt": "ciprofloxacin",
        "class": "fluoroquinolone antibiotic",
        "typical_use": "bacterial infection"
    },
    "cifran": {
        "salt": "ciprofloxacin",
        "class": "fluoroquinolone antibiotic",
        "typical_use": "bacterial infection"
    },
    "ciprobid": {
        "salt": "ciprofloxacin",
        "class": "fluoroquinolone antibiotic",
        "typical_use": "bacterial infection"
    },
    "zoxan": {
        "salt": "ciprofloxacin",
        "class": "fluoroquinolone antibiotic",
        "typical_use": "bacterial eye/systemic infection"
    },
    "alcipro": {
        "salt": "ciprofloxacin",
        "class": "fluoroquinolone antibiotic",
        "typical_use": "bacterial infection"
    },
    "levomac": {
        "salt": "levofloxacin",
        "class": "fluoroquinolone antibiotic",
        "typical_use": "respiratory or systemic bacterial infection"
    },
    "tavanic": {
        "salt": "levofloxacin",
        "class": "fluoroquinolone antibiotic",
        "typical_use": "bacterial respiratory infection"
    },
    "lquin": {
        "salt": "levofloxacin",
        "class": "fluoroquinolone antibiotic",
        "typical_use": "bacterial infection"
    },
    "avelox": {
        "salt": "moxifloxacin",
        "class": "fluoroquinolone antibiotic",
        "typical_use": "respiratory tract infection"
    },
    "moxicip": {
        "salt": "moxifloxacin",
        "class": "fluoroquinolone antibiotic",
        "typical_use": "bacterial infection"
    },
    "zenflox": {
        "salt": "ofloxacin",
        "class": "fluoroquinolone antibiotic",
        "typical_use": "bacterial infection"
    },
    "oflox": {
        "salt": "ofloxacin",
        "class": "fluoroquinolone antibiotic",
        "typical_use": "bacterial/urinary/GI infection"
    },
    "norflox": {
        "salt": "norfloxacin",
        "class": "fluoroquinolone antibiotic",
        "typical_use": "urinary tract or gastrointestinal infection"
    },
    "ceftum": {
        "salt": "cefuroxime axetil",
        "class": "second-generation cephalosporin antibiotic",
        "typical_use": "bacterial respiratory/soft tissue infection"
    },
    "cetil": {
        "salt": "cefuroxime axetil",
        "class": "second-generation cephalosporin antibiotic",
        "typical_use": "bacterial infection"
    },
    "zinacef": {
        "salt": "cefuroxime",
        "class": "second-generation cephalosporin antibiotic",
        "typical_use": "bacterial infection"
    },
    "taxim": {
        "salt": "cefixime",
        "class": "third-generation cephalosporin",
        "typical_use": "bacterial infection / typhoid fever"
    },
    "zifi": {
        "salt": "cefixime",
        "class": "third-generation cephalosporin",
        "typical_use": "bacterial infection"
    },
    "mahacef": {
        "salt": "cefixime",
        "class": "third-generation cephalosporin",
        "typical_use": "bacterial infection"
    },
    "cefspan": {
        "salt": "cefixime",
        "class": "third-generation cephalosporin",
        "typical_use": "bacterial infection"
    },
    "cepodem": {
        "salt": "cefpodoxime proxetil",
        "class": "third-generation cephalosporin antibiotic",
        "typical_use": "acute otitis media, pharyngitis, or pneumonia"
    },
    "doxcef": {
        "salt": "cefpodoxime proxetil",
        "class": "third-generation cephalosporin antibiotic",
        "typical_use": "bacterial infection"
    },
    "monocef": {
        "salt": "ceftriaxone",
        "class": "third-generation cephalosporin",
        "typical_use": "severe bacterial infection"
    },
    "rocephin": {
        "salt": "ceftriaxone",
        "class": "third-generation cephalosporin",
        "typical_use": "severe bacterial infection"
    },
    "meronem": {
        "salt": "meropenem",
        "class": "carbapenem antibiotic",
        "typical_use": "severe hospital-acquired infection"
    },
    "invanz": {
        "salt": "ertapenem",
        "class": "carbapenem antibiotic",
        "typical_use": "complicated intra-abdominal or skin infection"
    },
    "azithral": {
        "salt": "azithromycin",
        "class": "macrolide antibiotic",
        "typical_use": "bacterial respiratory/throat infection"
    },
    "azee": {
        "salt": "azithromycin",
        "class": "macrolide antibiotic",
        "typical_use": "bacterial infection"
    },
    "zady": {
        "salt": "azithromycin",
        "class": "macrolide antibiotic",
        "typical_use": "respiratory tract infection"
    },
    "zithromax": {
        "salt": "azithromycin",
        "class": "macrolide antibiotic",
        "typical_use": "bacterial infection"
    },
    "klacid": {
        "salt": "clarithromycin",
        "class": "macrolide antibiotic",
        "typical_use": "respiratory or H. pylori infection"
    },
    "claribid": {
        "salt": "clarithromycin",
        "class": "macrolide antibiotic",
        "typical_use": "bacterial respiratory infection"
    },
    "rulide": {
        "salt": "roxithromycin",
        "class": "macrolide antibiotic",
        "typical_use": "respiratory tract infection"
    },
    "doxy": {
        "salt": "doxycycline",
        "class": "tetracycline antibiotic",
        "typical_use": "bacterial/rickettsial infection"
    },
    "doxt": {
        "salt": "doxycycline",
        "class": "tetracycline antibiotic",
        "typical_use": "bacterial infection"
    },
    "metrogyl": {
        "salt": "metronidazole",
        "class": "nitroimidazole antimicrobial",
        "typical_use": "amoebiasis or anaerobic infection"
    },
    "flagyl": {
        "salt": "metronidazole",
        "class": "nitroimidazole antimicrobial",
        "typical_use": "anaerobic bacterial/protozoal infection"
    },
    "bactrim": {
        "salt": "sulfamethoxazole + trimethoprim",
        "class": "sulfonamide combination antibacterial",
        "typical_use": "urinary tract or respiratory infection"
    },
    "septra": {
        "salt": "sulfamethoxazole + trimethoprim",
        "class": "antibacterial combination",
        "typical_use": "bacterial infection"
    },
    "diflucan": {
        "salt": "fluconazole",
        "class": "triazole antifungal",
        "typical_use": "candidiasis or systemic fungal infection"
    },
    "forcan": {
        "salt": "fluconazole",
        "class": "triazole antifungal",
        "typical_use": "fungal infection"
    },
    "itaspor": {
        "salt": "itraconazole",
        "class": "triazole antifungal",
        "typical_use": "systemic fungal or dermatophyte infection"
    },
    "canditral": {
        "salt": "itraconazole",
        "class": "triazole antifungal",
        "typical_use": "fungal infection"
    },
    "sporanox": {
        "salt": "itraconazole",
        "class": "triazole antifungal",
        "typical_use": "fungal infection"
    },
    "terbinaforce": {
        "salt": "terbinafine",
        "class": "allylamine antifungal",
        "typical_use": "onychomycosis or tinea fungal infection"
    },
    "acyclovir": {
        "salt": "acyclovir",
        "class": "antiviral agent",
        "typical_use": "herpes simplex or herpes zoster infection"
    },
    "zovirax": {
        "salt": "acyclovir",
        "class": "antiviral agent",
        "typical_use": "herpes viral infection"
    },
    "valcivir": {
        "salt": "valacyclovir",
        "class": "antiviral prodrug",
        "typical_use": "herpes zoster and genital herpes"
    },
    "tbact": {
        "salt": "mupirocin",
        "class": "topical antibacterial",
        "typical_use": "impetigo and superficial bacterial skin infections"
    },
    "coartem": {
        "salt": "artemether + lumefantrine",
        "class": "artemisinin-based combination (antimalarial)",
        "typical_use": "uncomplicated falciparum malaria"
    },
    "lumerax": {
        "salt": "artemether + lumefantrine",
        "class": "artemisinin-based combination (antimalarial)",
        "typical_use": "falciparum malaria"
    },
    "falcinil": {
        "salt": "artesunate",
        "class": "antimalarial",
        "typical_use": "malaria treatment"
    },
    "combither": {
        "salt": "artemether + lumefantrine",
        "class": "antimalarial combination",
        "typical_use": "malaria"
    },
    "larinate": {
        "salt": "artesunate + sulfadoxine-pyrimethamine",
        "class": "antimalarial",
        "typical_use": "malaria"
    },
    "zentel": {
        "salt": "albendazole",
        "class": "anthelmintic (anti-parasitic)",
        "typical_use": "intestinal worm infection (roundworm, pinworm, hookworm)"
    },
    "bandy": {
        "salt": "albendazole",
        "class": "anthelmintic (anti-parasitic)",
        "typical_use": "intestinal helminthic infection"
    },
    "noworm": {
        "salt": "albendazole",
        "class": "anthelmintic (anti-parasitic)",
        "typical_use": "intestinal worm infestation"
    },
    "bendex": {
        "salt": "albendazole",
        "class": "anthelmintic (anti-parasitic)",
        "typical_use": "parasitic worm infection"
    },
    "alminth": {
        "salt": "albendazole",
        "class": "anthelmintic (anti-parasitic)",
        "typical_use": "worm infestation"
    },
    "vermox": {
        "salt": "mebendazole",
        "class": "anthelmintic",
        "typical_use": "gastrointestinal worm infection"
    },
    "ivecop": {
        "salt": "ivermectin",
        "class": "anti-parasitic",
        "typical_use": "scabies or strongyloidiasis infection"
    },
    "ivermectol": {
        "salt": "ivermectin",
        "class": "anti-parasitic",
        "typical_use": "parasitic infection or scabies"
    },
    "pan": {
        "salt": "pantoprazole",
        "class": "proton pump inhibitor",
        "typical_use": "gastric hyperacidity, GERD, and peptic ulcer"
    },
    "pantocid": {
        "salt": "pantoprazole",
        "class": "proton pump inhibitor",
        "typical_use": "gastroesophageal reflux and ulcer healing"
    },
    "pantodac": {
        "salt": "pantoprazole",
        "class": "proton pump inhibitor",
        "typical_use": "acid peptic disease"
    },
    "pantop": {
        "salt": "pantoprazole",
        "class": "proton pump inhibitor",
        "typical_use": "gastric acidity / GERD"
    },
    "omez": {
        "salt": "omeprazole",
        "class": "proton pump inhibitor",
        "typical_use": "acid peptic disease and heartburn"
    },
    "omee": {
        "salt": "omeprazole",
        "class": "proton pump inhibitor",
        "typical_use": "gastric acidity"
    },
    "razo": {
        "salt": "rabeprazole",
        "class": "proton pump inhibitor",
        "typical_use": "acid reflux and erosive esophagitis"
    },
    "rabicip": {
        "salt": "rabeprazole",
        "class": "proton pump inhibitor",
        "typical_use": "acid peptic disease"
    },
    "happi": {
        "salt": "rabeprazole",
        "class": "proton pump inhibitor",
        "typical_use": "gastroesophageal reflux disease"
    },
    "rablet": {
        "salt": "rabeprazole",
        "class": "proton pump inhibitor",
        "typical_use": "acid reflux and peptic ulcers"
    },
    "cyra": {
        "salt": "rabeprazole",
        "class": "proton pump inhibitor",
        "typical_use": "gastric acidity"
    },
    "veloz": {
        "salt": "rabeprazole",
        "class": "proton pump inhibitor",
        "typical_use": "acid reflux and heartburn"
    },
    "parit": {
        "salt": "rabeprazole",
        "class": "proton pump inhibitor",
        "typical_use": "acid peptic disorder"
    },
    "nexpro": {
        "salt": "esomeprazole",
        "class": "proton pump inhibitor",
        "typical_use": "severe GERD and reflux esophagitis"
    },
    "esomac": {
        "salt": "esomeprazole",
        "class": "proton pump inhibitor",
        "typical_use": "gastroesophageal reflux disease"
    },
    "lanzol": {
        "salt": "lansoprazole",
        "class": "proton pump inhibitor",
        "typical_use": "gastric and duodenal ulcers"
    },
    "rantac": {
        "salt": "ranitidine",
        "class": "h2 receptor antagonist",
        "typical_use": "gastric acidity and heartburn"
    },
    "aciloc": {
        "salt": "ranitidine",
        "class": "h2 receptor antagonist",
        "typical_use": "gastric acidity and ulcer disease"
    },
    "zinetac": {
        "salt": "ranitidine",
        "class": "h2 receptor antagonist",
        "typical_use": "acid dyspepsia"
    },
    "gelusil": {
        "salt": "aluminium hydroxide + magnesium hydroxide + simethicone",
        "class": "antacid and antiflatulent suspension",
        "typical_use": "gastric acidity, heartburn, and gas"
    },
    "digene": {
        "salt": "magnesium hydroxide + aluminium hydroxide + simethicone",
        "class": "antacid suspension",
        "typical_use": "acidity, flatulence, and heartburn"
    },
    "mucaine": {
        "salt": "oxethazaine + aluminium hydroxide + magnesium hydroxide",
        "class": "local anesthetic antacid gel",
        "typical_use": "severe esophagitis and gastritis pain"
    },
    "sucrafil": {
        "salt": "sucralfate",
        "class": "mucosal protective agent",
        "typical_use": "gastric or duodenal ulcer protection"
    },
    "cremaffin": {
        "salt": "liquid paraffin + milk of magnesia",
        "class": "laxative emulsion",
        "typical_use": "constipation relief"
    },
    "duphalac": {
        "salt": "lactulose",
        "class": "osmotic laxative",
        "typical_use": "chronic constipation and hepatic encephalopathy"
    },
    "ondem": {
        "salt": "ondansetron",
        "class": "5-ht3 antagonist antiemetic",
        "typical_use": "nausea and vomiting prevention"
    },
    "vomikind": {
        "salt": "ondansetron",
        "class": "antiemetic",
        "typical_use": "nausea and vomiting"
    },
    "domstal": {
        "salt": "domperidone",
        "class": "prokinetic and antiemetic",
        "typical_use": "dyspepsia, gastric fullness, and nausea"
    },
    "motilium": {
        "salt": "domperidone",
        "class": "prokinetic",
        "typical_use": "nausea and upper GI motility disorder"
    },
    "colimex": {
        "salt": "dicyclomine + paracetamol",
        "class": "antispasmodic and analgesic",
        "typical_use": "abdominal cramp and colic pain"
    },
    "cyclopam": {
        "salt": "dicyclomine + paracetamol",
        "class": "antispasmodic and analgesic",
        "typical_use": "intestinal colic and abdominal pain"
    },
    "colospa": {
        "salt": "mebeverine",
        "class": "musculotropic antispasmodic",
        "typical_use": "irritable bowel syndrome (IBS)"
    },
    "glycomet": {
        "salt": "metformin",
        "class": "biguanide antidiabetic",
        "typical_use": "type 2 diabetes mellitus glycemic control"
    },
    "glucophage": {
        "salt": "metformin",
        "class": "biguanide antidiabetic",
        "typical_use": "type 2 diabetes mellitus glycemic control"
    },
    "gluconorm": {
        "salt": "metformin",
        "class": "biguanide antidiabetic",
        "typical_use": "type 2 diabetes mellitus"
    },
    "obimet": {
        "salt": "metformin",
        "class": "biguanide antidiabetic",
        "typical_use": "type 2 diabetes mellitus"
    },
    "formin": {
        "salt": "metformin",
        "class": "biguanide antidiabetic",
        "typical_use": "type 2 diabetes mellitus"
    },
    "amaryl": {
        "salt": "glimepiride",
        "class": "sulfonylurea antidiabetic",
        "typical_use": "type 2 diabetes mellitus"
    },
    "glador": {
        "salt": "glimepiride",
        "class": "sulfonylurea antidiabetic",
        "typical_use": "type 2 diabetes mellitus"
    },
    "zoryl": {
        "salt": "glimepiride",
        "class": "sulfonylurea antidiabetic",
        "typical_use": "type 2 diabetes mellitus"
    },
    "glimi": {
        "salt": "glimepiride",
        "class": "sulfonylurea antidiabetic",
        "typical_use": "type 2 diabetes mellitus"
    },
    "diamicron": {
        "salt": "gliclazide",
        "class": "sulfonylurea antidiabetic",
        "typical_use": "type 2 diabetes mellitus"
    },
    "daonil": {
        "salt": "glibenclamide",
        "class": "sulfonylurea antidiabetic",
        "typical_use": "type 2 diabetes mellitus"
    },
    "januvia": {
        "salt": "sitagliptin",
        "class": "dpp-4 inhibitor antidiabetic",
        "typical_use": "type 2 diabetes mellitus"
    },
    "galvus": {
        "salt": "vildagliptin",
        "class": "dpp-4 inhibitor antidiabetic",
        "typical_use": "type 2 diabetes mellitus"
    },
    "trajenta": {
        "salt": "linagliptin",
        "class": "dpp-4 inhibitor antidiabetic",
        "typical_use": "type 2 diabetes mellitus"
    },
    "forxiga": {
        "salt": "dapagliflozin",
        "class": "sglt2 inhibitor antidiabetic",
        "typical_use": "type 2 diabetes and renal/cardiac protection"
    },
    "jardiance": {
        "salt": "empagliflozin",
        "class": "sglt2 inhibitor antidiabetic",
        "typical_use": "type 2 diabetes and cardiovascular risk reduction"
    },
    "rybelsus": {
        "salt": "semaglutide",
        "class": "glp-1 receptor agonist",
        "typical_use": "type 2 diabetes glycemic control and weight management"
    },
    "mixtard": {
        "salt": "biphasic isophane human insulin",
        "class": "human insulin preparation",
        "typical_use": "insulin-dependent diabetes mellitus"
    },
    "lantus": {
        "salt": "insulin glargine",
        "class": "long-acting basal insulin analog",
        "typical_use": "basal glycemic control in diabetes"
    },
    "thyronorm": {
        "salt": "levothyroxine sodium",
        "class": "synthetic thyroid hormone",
        "typical_use": "hypothyroidism replacement therapy"
    },
    "eltroxin": {
        "salt": "levothyroxine sodium",
        "class": "thyroid hormone replacement",
        "typical_use": "hypothyroidism"
    },
    "concor": {
        "salt": "bisoprolol",
        "class": "cardioselective beta-1 blocker",
        "typical_use": "hypertension and angina pectoris"
    },
    "betaloc": {
        "salt": "metoprolol",
        "class": "beta-blocker",
        "typical_use": "hypertension, angina, and heart rate control"
    },
    "metolar": {
        "salt": "metoprolol",
        "class": "beta-blocker",
        "typical_use": "hypertension and angina"
    },
    "nebicard": {
        "salt": "nebivolol",
        "class": "vasodilating beta-blocker",
        "typical_use": "essential hypertension"
    },
    "telma": {
        "salt": "telmisartan",
        "class": "angiotensin receptor blocker (arb)",
        "typical_use": "essential hypertension"
    },
    "telmikind": {
        "salt": "telmisartan",
        "class": "angiotensin receptor blocker (arb)",
        "typical_use": "hypertension"
    },
    "telsar": {
        "salt": "telmisartan",
        "class": "angiotensin receptor blocker (arb)",
        "typical_use": "essential hypertension"
    },
    "losar": {
        "salt": "losartan",
        "class": "angiotensin receptor blocker (arb)",
        "typical_use": "hypertension and diabetic nephropathy"
    },
    "repace": {
        "salt": "losartan",
        "class": "angiotensin receptor blocker",
        "typical_use": "hypertension"
    },
    "amlong": {
        "salt": "amlodipine",
        "class": "dihydropyridine calcium channel blocker",
        "typical_use": "hypertension and chronic stable angina"
    },
    "stamlo": {
        "salt": "amlodipine",
        "class": "calcium channel blocker",
        "typical_use": "hypertension"
    },
    "cilacar": {
        "salt": "cilnidipine",
        "class": "l/n-type dual calcium channel blocker",
        "typical_use": "hypertension with kidney protection"
    },
    "cardace": {
        "salt": "ramipril",
        "class": "ace inhibitor",
        "typical_use": "hypertension and post-myocardial infarction care"
    },
    "envas": {
        "salt": "enalapril",
        "class": "ace inhibitor",
        "typical_use": "hypertension and heart failure"
    },
    "atorva": {
        "salt": "atorvastatin",
        "class": "hmg-coa reductase inhibitor (statin)",
        "typical_use": "hypercholesterolemia and cardiovascular prevention"
    },
    "lipitor": {
        "salt": "atorvastatin",
        "class": "hmg-coa reductase inhibitor (statin)",
        "typical_use": "dyslipidemia"
    },
    "rosuvas": {
        "salt": "rosuvastatin",
        "class": "statin lipid-lowering agent",
        "typical_use": "hyperlipidemia"
    },
    "rozucor": {
        "salt": "rosuvastatin",
        "class": "statin lipid-lowering agent",
        "typical_use": "hypercholesterolemia"
    },
    "ecosprin": {
        "salt": "aspirin",
        "class": "antiplatelet agent",
        "typical_use": "cardiovascular event prevention and antiplatelet therapy"
    },
    "clopilet": {
        "salt": "clopidogrel",
        "class": "antiplatelet agent",
        "typical_use": "prevention of ischemic stroke and myocardial infarction"
    },
    "deplatt": {
        "salt": "clopidogrel",
        "class": "antiplatelet agent",
        "typical_use": "atherothrombosis prevention"
    },
    "dytor": {
        "salt": "torsemide",
        "class": "loop diuretic",
        "typical_use": "edema and hypertension"
    },
    "lasix": {
        "salt": "furosemide",
        "class": "loop diuretic",
        "typical_use": "edema due to cardiac, hepatic, or renal disease"
    },
    "catapres": {
        "salt": "clonidine",
        "class": "centrally acting alpha-2 agonist",
        "typical_use": "hypertension"
    },
    "dolo": {
        "salt": "paracetamol",
        "class": "analgesic and antipyretic",
        "typical_use": "fever and mild-to-moderate pain"
    },
    "calpol": {
        "salt": "paracetamol",
        "class": "analgesic and antipyretic",
        "typical_use": "fever and pain"
    },
    "crocin": {
        "salt": "paracetamol",
        "class": "analgesic and antipyretic",
        "typical_use": "fever and body ache"
    },
    "pacimol": {
        "salt": "paracetamol",
        "class": "analgesic and antipyretic",
        "typical_use": "fever and pain relief"
    },
    "combiflam": {
        "salt": "ibuprofen + paracetamol",
        "class": "nsaid + analgesic combination",
        "typical_use": "inflammatory musculoskeletal pain and fever"
    },
    "ibugesic": {
        "salt": "ibuprofen + paracetamol",
        "class": "nsaid analgesic combination",
        "typical_use": "pain and swelling"
    },
    "brufen": {
        "salt": "ibuprofen",
        "class": "nsaid analgesic",
        "typical_use": "inflammatory arthritis and pain"
    },
    "voveran": {
        "salt": "diclofenac",
        "class": "nsaid anti-inflammatory",
        "typical_use": "orthopedic pain, arthritis, or post-traumatic swelling"
    },
    "voltaren": {
        "salt": "diclofenac",
        "class": "nsaid anti-inflammatory",
        "typical_use": "joint and musculoskeletal pain"
    },
    "zerodol": {
        "salt": "aceclofenac",
        "class": "nsaid analgesic",
        "typical_use": "joint pain, osteoarthritis, and inflammation"
    },
    "hifenac": {
        "salt": "aceclofenac",
        "class": "nsaid analgesic",
        "typical_use": "rheumatoid arthritis and osteoarthritis pain"
    },
    "meftal": {
        "salt": "mefenamic acid",
        "class": "nsaid analgesic",
        "typical_use": "dysmenorrhea, menstrual colic, or dental pain"
    },
    "chymooral": {
        "salt": "trypsin + chymotrypsin",
        "class": "proteolytic enzyme anti-inflammatory",
        "typical_use": "post-operative and post-traumatic edema"
    },
    "enzomac": {
        "salt": "trypsin + bromelain + rutoside",
        "class": "anti-inflammatory enzyme combination",
        "typical_use": "soft tissue swelling and inflammation"
    },
    "ultracet": {
        "salt": "tramadol + paracetamol",
        "class": "opioid analgesic combination",
        "typical_use": "moderate to severe acute pain"
    },
    "myoril": {
        "salt": "thiocolchicoside",
        "class": "muscle relaxant",
        "typical_use": "painful muscle spasms and lumbago"
    },
    "allegra": {
        "salt": "fexofenadine",
        "class": "non-sedating second-generation h1-antihistamine",
        "typical_use": "seasonal allergic rhinitis and chronic urticaria"
    },
    "cetzine": {
        "salt": "cetirizine",
        "class": "second-generation h1 antihistamine",
        "typical_use": "allergic rhinitis and urticaria"
    },
    "alerid": {
        "salt": "cetirizine",
        "class": "antihistamine",
        "typical_use": "allergy symptoms"
    },
    "zyrtec": {
        "salt": "cetirizine",
        "class": "antihistamine",
        "typical_use": "allergic rhinitis and hives"
    },
    "xyzal": {
        "salt": "levocetirizine",
        "class": "active enantiomer antihistamine",
        "typical_use": "allergy, runny nose, and itching"
    },
    "teczine": {
        "salt": "levocetirizine",
        "class": "antihistamine",
        "typical_use": "allergic rhinitis and skin allergy"
    },
    "montair": {
        "salt": "montelukast",
        "class": "leukotriene receptor antagonist",
        "typical_use": "bronchial asthma prophylaxis and allergic rhinitis"
    },
    "montek": {
        "salt": "montelukast",
        "class": "leukotriene receptor antagonist",
        "typical_use": "bronchial asthma and allergic rhinitis"
    },
    "asthalin": {
        "salt": "salbutamol",
        "class": "short-acting beta-2 agonist (saba) bronchodilator",
        "typical_use": "acute bronchospasm and asthma relief"
    },
    "ventolin": {
        "salt": "salbutamol",
        "class": "bronchodilator",
        "typical_use": "asthma and copd wheezing"
    },
    "duolin": {
        "salt": "ipratropium + levosalbutamol",
        "class": "anticholinergic + bronchodilator",
        "typical_use": "bronchospasm in asthma and copd"
    },
    "budecort": {
        "salt": "budesonide",
        "class": "corticosteroid inhaler/respules",
        "typical_use": "airway inflammation in bronchial asthma"
    },
    "foracort": {
        "salt": "formoterol + budesonide",
        "class": "laba + inhaled corticosteroid",
        "typical_use": "maintenance therapy for asthma and copd"
    },
    "seretide": {
        "salt": "salmeterol + fluticasone",
        "class": "laba + inhaled corticosteroid",
        "typical_use": "asthma and copd maintenance"
    },
    "ascoril": {
        "salt": "terbutaline + bromhexine + guaiphenesin",
        "class": "bronchodilator and expectorant",
        "typical_use": "productive cough and chest congestion"
    },
    "grilinctus": {
        "salt": "dextromethorphan + chlorpheniramine",
        "class": "antitussive cough syrup",
        "typical_use": "dry non-productive cough"
    },
    "alex": {
        "salt": "dextromethorphan + chlorpheniramine + phenylephrine",
        "class": "cough suppressant and decongestant",
        "typical_use": "cough and common cold symptoms"
    },
    "cheston": {
        "salt": "cetirizine + paracetamol + phenylephrine",
        "class": "cold preparation",
        "typical_use": "nasal congestion, cold, and fever"
    },
    "sinarest": {
        "salt": "paracetamol + phenylephrine + chlorpheniramine",
        "class": "cold and sinus relief preparation",
        "typical_use": "nasal congestion, fever, and common cold"
    },
    "nasivion": {
        "salt": "oxymetazoline",
        "class": "nasal decongestant spray/drops",
        "typical_use": "blocked nose and nasal congestion"
    },
    "otrivin": {
        "salt": "xylometazoline",
        "class": "topical nasal decongestant",
        "typical_use": "nasal congestion from colds or sinusitis"
    },
    "asthafen": {
        "salt": "ketotifen",
        "class": "mast cell stabilizer and h1-antihistamine",
        "typical_use": "prophylaxis of bronchial asthma and allergic disorders"
    },
    "zaditen": {
        "salt": "ketotifen",
        "class": "mast cell stabilizer",
        "typical_use": "allergic rhinitis and conjunctivitis"
    },
    "tegretol": {
        "salt": "carbamazepine",
        "class": "sodium channel blocker anticonvulsant",
        "typical_use": "epilepsy and trigeminal neuralgia"
    },
    "encorate": {
        "salt": "sodium valproate",
        "class": "broad-spectrum antiepileptic",
        "typical_use": "epilepsy and bipolar disorder prophylaxis"
    },
    "depakote": {
        "salt": "divalproex sodium",
        "class": "antiepileptic and mood stabilizer",
        "typical_use": "seizures, bipolar mania, and migraine prophylaxis"
    },
    "levipil": {
        "salt": "levetiracetam",
        "class": "second-generation antiepileptic",
        "typical_use": "partial onset and generalized seizures"
    },
    "keppra": {
        "salt": "levetiracetam",
        "class": "antiepileptic",
        "typical_use": "epileptic seizure control"
    },
    "gabapin": {
        "salt": "gabapentin",
        "class": "gaba analog",
        "typical_use": "neuropathic pain and partial seizures"
    },
    "neurontin": {
        "salt": "gabapentin",
        "class": "neuropathic pain agent",
        "typical_use": "post-herpetic neuralgia and neuropathic pain"
    },
    "pregabalin": {
        "salt": "pregabalin",
        "class": "calcium channel subunit modulator",
        "typical_use": "peripheral neuropathic pain and generalized anxiety"
    },
    "lyrica": {
        "salt": "pregabalin",
        "class": "neuropathic pain agent",
        "typical_use": "diabetic neuropathy, fibromyalgia, and neuralgia"
    },
    "nexito": {
        "salt": "escitalopram",
        "class": "selective serotonin reuptake inhibitor (ssri)",
        "typical_use": "major depressive disorder and generalized anxiety"
    },
    "cipralex": {
        "salt": "escitalopram",
        "class": "ssri antidepressant",
        "typical_use": "depression and anxiety disorders"
    },
    "alprax": {
        "salt": "alprazolam",
        "class": "triazolobenzodiazepine anxiolytic",
        "typical_use": "panic disorder and acute anxiety"
    },
    "ativan": {
        "salt": "lorazepam",
        "class": "benzodiazepine",
        "typical_use": "short-term anxiety and insomnia relief"
    },
    "betnovate": {
        "salt": "betamethasone valerate",
        "class": "topical corticosteroid",
        "typical_use": "inflammatory dermatoses, eczema, and psoriasis"
    },
    "diprovate": {
        "salt": "betamethasone dipropionate",
        "class": "potent topical corticosteroid",
        "typical_use": "inflammatory skin conditions"
    },
    "clobetamil": {
        "salt": "clobetasol propionate",
        "class": "very potent topical corticosteroid",
        "typical_use": "recalcitrant dermatoses and severe eczema"
    },
    "tenovate": {
        "salt": "clobetasol propionate",
        "class": "high-potency topical steroid",
        "typical_use": "plaque psoriasis and severe lichen planus"
    },
    "panderm": {
        "salt": "clobetasol + neomycin + miconazole",
        "class": "corticosteroid + antibiotic + antifungal cream",
        "typical_use": "mixed bacterial and fungal skin infections"
    },
    "quadriderm": {
        "salt": "betamethasone + gentamicin + tolnaftate + iodochlorhydroxyquin",
        "class": "multi-ingredient topical cream",
        "typical_use": "superficial mixed skin infections"
    },
    "telmah": {
        "salt": "telmisartan + hydrochlorothiazide",
        "class": "arb + thiazide diuretic",
        "typical_use": "hypertension uncontrolled on monotherapy"
    },
    "telmaam": {
        "salt": "telmisartan + amlodipine",
        "class": "arb + calcium channel blocker",
        "typical_use": "moderate to severe essential hypertension"
    },
    "telpres": {
        "salt": "telmisartan",
        "class": "angiotensin II receptor blocker",
        "typical_use": "hypertension"
    },
    "telpresct": {
        "salt": "telmisartan + chlorthalidone",
        "class": "arb + long-acting thiazide-like diuretic",
        "typical_use": "resistant hypertension"
    },
    "tazloc": {
        "salt": "telmisartan",
        "class": "angiotensin II receptor blocker",
        "typical_use": "hypertension and stroke risk reduction"
    },
    "tazloch": {
        "salt": "telmisartan + hydrochlorothiazide",
        "class": "arb + diuretic combination",
        "typical_use": "hypertension"
    },
    "tazlocam": {
        "salt": "telmisartan + amlodipine",
        "class": "arb + ccb combination",
        "typical_use": "hypertension"
    },
    "cilacart": {
        "salt": "cilnidipine + telmisartan",
        "class": "ccb + arb combination",
        "typical_use": "hypertension with renal protection"
    },
    "nexovas": {
        "salt": "cilnidipine",
        "class": "calcium channel blocker",
        "typical_use": "hypertension"
    },
    "concorcor": {
        "salt": "bisoprolol fumarate",
        "class": "cardioselective beta-1 blocker",
        "typical_use": "stable chronic heart failure titration"
    },
    "concoram": {
        "salt": "bisoprolol + amlodipine",
        "class": "beta blocker + ccb combination",
        "typical_use": "hypertension"
    },
    "nebilong": {
        "salt": "nebivolol",
        "class": "selective vasodilating beta blocker",
        "typical_use": "hypertension"
    },
    "nebicardh": {
        "salt": "nebivolol + hydrochlorothiazide",
        "class": "beta blocker + diuretic",
        "typical_use": "hypertension"
    },
    "seloken": {
        "salt": "metoprolol tartrate",
        "class": "beta-1 selective blocker",
        "typical_use": "angina and cardiac arrhythmias"
    },
    "cardaceh": {
        "salt": "ramipril + hydrochlorothiazide",
        "class": "ace inhibitor + diuretic",
        "typical_use": "hypertension"
    },
    "cardaceam": {
        "salt": "ramipril + amlodipine",
        "class": "ace inhibitor + ccb",
        "typical_use": "hypertension"
    },
    "losarh": {
        "salt": "losartan + hydrochlorothiazide",
        "class": "arb + thiazide diuretic",
        "typical_use": "hypertension"
    },
    "repaceh": {
        "salt": "losartan + hydrochlorothiazide",
        "class": "arb + diuretic",
        "typical_use": "hypertension"
    },
    "minipress": {
        "salt": "prazosin hydrochloride",
        "class": "alpha-1 adrenergic blocker",
        "typical_use": "hypertension, Raynaud syndrome, and PTSD nightmares"
    },
    "dytorplus": {
        "salt": "torsemide + spironolactone",
        "class": "loop diuretic + potassium-sparing aldosterone antagonist",
        "typical_use": "resistant cardiac/hepatic edema and ascites"
    },
    "aldactone": {
        "salt": "spironolactone",
        "class": "aldosterone receptor antagonist / potassium-sparing diuretic",
        "typical_use": "heart failure, ascites, and primary hyperaldosteronism"
    },
    "arkamin": {
        "salt": "clonidine hydrochloride",
        "class": "central alpha-2 adrenergic agonist",
        "typical_use": "hypertensive crisis and resistant hypertension"
    },
    "natrilix": {
        "salt": "indapamide",
        "class": "thiazide-like diuretic",
        "typical_use": "essential hypertension"
    },
    "cardivas": {
        "salt": "carvedilol",
        "class": "non-selective beta and alpha-1 blocker",
        "typical_use": "heart failure and post-MI left ventricular dysfunction"
    },
    "carca": {
        "salt": "carvedilol",
        "class": "beta-blocker with vasodilating action",
        "typical_use": "congestive heart failure and hypertension"
    },
    "stamlod": {
        "salt": "amlodipine + hydrochlorothiazide",
        "class": "ccb + diuretic",
        "typical_use": "hypertension"
    },
    "stamlom": {
        "salt": "amlodipine + metoprolol succinate",
        "class": "ccb + beta blocker",
        "typical_use": "hypertension and coronary artery disease"
    },
    "amlopres": {
        "salt": "amlodipine",
        "class": "calcium channel blocker",
        "typical_use": "hypertension and angina"
    },
    "angicam": {
        "salt": "amlodipine",
        "class": "calcium channel blocker",
        "typical_use": "hypertension"
    },
    "nicardia": {
        "salt": "nifedipine",
        "class": "dihydropyridine calcium channel blocker",
        "typical_use": "chronic angina and severe hypertension"
    },
    "depin": {
        "salt": "nifedipine retard",
        "class": "calcium channel blocker",
        "typical_use": "hypertension and Raynaud phenomenon"
    },
    "dilzem": {
        "salt": "diltiazem hydrochloride",
        "class": "non-dihydropyridine calcium channel blocker",
        "typical_use": "angina, supraventricular tachycardia, and atrial fibrillation"
    },
    "calaptin": {
        "salt": "verapamil hydrochloride",
        "class": "phenylalkylamine calcium channel blocker",
        "typical_use": "paroxysmal supraventricular tachycardia and angina"
    },
    "ismo": {
        "salt": "isosorbide mononitrate",
        "class": "nitrate vasodilator",
        "typical_use": "prophylaxis of angina pectoris"
    },
    "sorbitrate": {
        "salt": "isosorbide dinitrate",
        "class": "nitrate vasodilator",
        "typical_use": "acute and chronic angina relief"
    },
    "nitrocontin": {
        "salt": "nitroglycerin controlled release",
        "class": "nitrate vasodilator",
        "typical_use": "angina pectoris maintenance prophylaxis"
    },
    "monotrate": {
        "salt": "isosorbide-5-mononitrate",
        "class": "organic nitrate",
        "typical_use": "coronary artery disease and angina prophylaxis"
    },
    "ivabrad": {
        "salt": "ivabradine hydrochloride",
        "class": "HCN channel If current inhibitor",
        "typical_use": "stable chronic heart failure with resting HR >= 70 bpm"
    },
    "coralan": {
        "salt": "ivabradine",
        "class": "sinus node inhibitor",
        "typical_use": "angina and symptomatic heart failure"
    },
    "vymada": {
        "salt": "sacubitril + valsartan (ARNI)",
        "class": "angiotensin receptor-neprilysin inhibitor",
        "typical_use": "heart failure with reduced ejection fraction (HFrEF)"
    },
    "entresto": {
        "salt": "sacubitril + valsartan",
        "class": "angiotensin receptor neprilysin inhibitor",
        "typical_use": "heart failure with reduced ejection fraction"
    },
    "glycometgp": {
        "salt": "metformin + glimepiride",
        "class": "biguanide + sulfonylurea combination",
        "typical_use": "dual therapy for type 2 diabetes mellitus"
    },
    "glycomettrio": {
        "salt": "metformin + glimepiride + voglibose",
        "class": "triple oral antidiabetic combination",
        "typical_use": "uncontrolled type 2 diabetes with postprandial spikes"
    },
    "galvusmet": {
        "salt": "vildagliptin + metformin",
        "class": "dpp-4 inhibitor + biguanide combination",
        "typical_use": "type 2 diabetes mellitus dual glycemic control"
    },
    "jalra": {
        "salt": "vildagliptin",
        "class": "dpp-4 inhibitor",
        "typical_use": "type 2 diabetes mellitus"
    },
    "jalram": {
        "salt": "vildagliptin + metformin",
        "class": "dpp-4 inhibitor + biguanide",
        "typical_use": "type 2 diabetes mellitus"
    },
    "janumet": {
        "salt": "sitagliptin + metformin",
        "class": "dpp-4 inhibitor + biguanide",
        "typical_use": "type 2 diabetes mellitus"
    },
    "oxra": {
        "salt": "dapagliflozin",
        "class": "sglt2 inhibitor",
        "typical_use": "type 2 diabetes and cardio-renal protection"
    },
    "gibtulio": {
        "salt": "empagliflozin",
        "class": "sglt2 inhibitor",
        "typical_use": "type 2 diabetes and heart failure"
    },
    "ozempic": {
        "salt": "semaglutide (injectable)",
        "class": "GLP-1 receptor agonist",
        "typical_use": "type 2 diabetes and major adverse cardiovascular event reduction"
    },
    "victoza": {
        "salt": "liraglutide",
        "class": "GLP-1 receptor agonist",
        "typical_use": "type 2 diabetes and cardiovascular risk management"
    },
    "trajantaduo": {
        "salt": "linagliptin + metformin",
        "class": "dpp-4 inhibitor + biguanide",
        "typical_use": "type 2 diabetes mellitus"
    },
    "tenelimac": {
        "salt": "teneligliptin",
        "class": "dpp-4 inhibitor",
        "typical_use": "type 2 diabetes mellitus"
    },
    "zita": {
        "salt": "teneligliptin",
        "class": "dpp-4 inhibitor",
        "typical_use": "type 2 diabetes mellitus"
    },
    "tenepride": {
        "salt": "teneligliptin + metformin",
        "class": "dpp-4 inhibitor + biguanide",
        "typical_use": "type 2 diabetes mellitus"
    },
    "amarylm": {
        "salt": "glimepiride + metformin",
        "class": "sulfonylurea + biguanide",
        "typical_use": "type 2 diabetes mellitus"
    },
    "glucored": {
        "salt": "glibenclamide + metformin",
        "class": "sulfonylurea + biguanide combination",
        "typical_use": "type 2 diabetes mellitus"
    },
    "glynase": {
        "salt": "glipizide",
        "class": "second-generation sulfonylurea",
        "typical_use": "type 2 diabetes mellitus"
    },
    "volibo": {
        "salt": "voglibose",
        "class": "alpha-glucosidase inhibitor",
        "typical_use": "postprandial glucose spike reduction in diabetes"
    },
    "voglimac": {
        "salt": "voglibose",
        "class": "alpha-glucosidase inhibitor",
        "typical_use": "type 2 diabetes mellitus postprandial control"
    },
    "glucobay": {
        "salt": "acarbose",
        "class": "alpha-glucosidase inhibitor",
        "typical_use": "postprandial hyperglycemia control in type 2 diabetes"
    },
    "pioglit": {
        "salt": "pioglitazone",
        "class": "thiazolidinedione (tzd) insulin sensitizer",
        "typical_use": "insulin resistance in type 2 diabetes"
    },
    "pioz": {
        "salt": "pioglitazone",
        "class": "thiazolidinedione insulin sensitizer",
        "typical_use": "type 2 diabetes mellitus"
    },
    "reclimet": {
        "salt": "gliclazide + metformin",
        "class": "sulfonylurea + biguanide",
        "typical_use": "type 2 diabetes mellitus"
    },
    "basalog": {
        "salt": "insulin glargine",
        "class": "long-acting basal insulin analogue",
        "typical_use": "once-daily basal insulin therapy for diabetes"
    },
    "novorapid": {
        "salt": "insulin aspart",
        "class": "rapid-acting prandial insulin",
        "typical_use": "postprandial glucose control in diabetes"
    },
    "humalog": {
        "salt": "insulin lispro",
        "class": "rapid-acting insulin analogue",
        "typical_use": "mealtime glucose management in diabetes"
    },
    "ryzodeg": {
        "salt": "insulin degludec + insulin aspart",
        "class": "co-formulation basal + rapid insulin",
        "typical_use": "diabetes mellitus glycemic control"
    },
    "tresiba": {
        "salt": "insulin degludec",
        "class": "ultra-long-acting basal insulin",
        "typical_use": "type 1 and type 2 diabetes basal control"
    },
    "thyrox": {
        "salt": "levothyroxine sodium",
        "class": "synthetic thyroid hormone",
        "typical_use": "hypothyroidism"
    },
    "neomercazole": {
        "salt": "carbimazole",
        "class": "antithyroid thionamide prodrug",
        "typical_use": "hyperthyroidism and Graves disease"
    },
    "tapazole": {
        "salt": "methimazole",
        "class": "antithyroid agent",
        "typical_use": "hyperthyroidism"
    },
    "rosave": {
        "salt": "rosuvastatin",
        "class": "hmg-coa reductase inhibitor (statin)",
        "typical_use": "hypercholesterolemia and cardiovascular prevention"
    },
    "rozavel": {
        "salt": "rosuvastatin",
        "class": "hmg-coa reductase inhibitor",
        "typical_use": "dyslipidemia and plaque stabilization"
    },
    "crestor": {
        "salt": "rosuvastatin",
        "class": "high-intensity statin",
        "typical_use": "primary and secondary prevention of cardiovascular events"
    },
    "rosuvasf": {
        "salt": "rosuvastatin + fenofibrate",
        "class": "statin + fibrate combination",
        "typical_use": "mixed dyslipidemia and elevated triglycerides"
    },
    "storvas": {
        "salt": "atorvastatin",
        "class": "hmg-coa reductase inhibitor",
        "typical_use": "hypercholesterolemia and coronary heart disease"
    },
    "atorlipf": {
        "salt": "atorvastatin + fenofibrate",
        "class": "statin + fibrate combination",
        "typical_use": "mixed dyslipidemia with high triglycerides and low HDL"
    },
    "lipaglyn": {
        "salt": "saroglitazar",
        "class": "dual PPAR-alpha/gamma agonist",
        "typical_use": "diabetic dyslipidemia and non-alcoholic fatty liver disease (NAFLD)"
    },
    "ezetrol": {
        "salt": "ezetimibe",
        "class": "cholesterol absorption inhibitor",
        "typical_use": "hypercholesterolemia add-on to statin therapy"
    },
    "eliquis": {
        "salt": "apixaban",
        "class": "direct factor Xa inhibitor novel oral anticoagulant (doac)",
        "typical_use": "stroke prevention in non-valvular AF, and DVT/PE treatment"
    },
    "xarelto": {
        "salt": "rivaroxaban",
        "class": "direct factor Xa inhibitor (doac)",
        "typical_use": "stroke prevention in atrial fibrillation, DVT and PE prophylaxis"
    },
    "pradaxa": {
        "salt": "dabigatran etexilate",
        "class": "direct thrombin inhibitor (doac)",
        "typical_use": "thromboembolism prevention in non-valvular AF and DVT/PE"
    },
    "plavix": {
        "salt": "clopidogrel",
        "class": "p2y12 platelet inhibitor",
        "typical_use": "secondary prevention of atherothrombotic events"
    },
    "brilinta": {
        "salt": "ticagrelor",
        "class": "reversible oral p2y12 platelet inhibitor",
        "typical_use": "acute coronary syndrome and myocardial infarction prevention"
    },
    "acitrom": {
        "salt": "acenocoumarol (nicoumalone)",
        "class": "coumarin oral anticoagulant",
        "typical_use": "deep vein thrombosis, pulmonary embolism, and heart valve replacement"
    },
    "warf": {
        "salt": "warfarin sodium",
        "class": "vitamin K antagonist oral anticoagulant",
        "typical_use": "thromboembolism prophylaxis and mechanical valve anticoagulation"
    },
    "coumadin": {
        "salt": "warfarin sodium",
        "class": "vitamin K antagonist anticoagulant",
        "typical_use": "atrial fibrillation and venous thrombosis prophylaxis"
    },
    "ecosprinav": {
        "salt": "aspirin + atorvastatin",
        "class": "antiplatelet + statin combination",
        "typical_use": "secondary prevention of coronary artery disease and myocardial infarction"
    },
    "disprin": {
        "salt": "aspirin 350mg soluble",
        "class": "nsaid / antiplatelet",
        "typical_use": "acute tension headache, fever, and acute suspected heart attack"
    },
    "loprin": {
        "salt": "aspirin 75mg enteric-coated",
        "class": "cardioprotective antiplatelet",
        "typical_use": "secondary cardiovascular risk prevention"
    },
    "razod": {
        "salt": "rabeprazole + domperidone",
        "class": "ppi + prokinetic combination",
        "typical_use": "acid reflux with nausea, bloating, and delayed gastric emptying"
    },
    "razol": {
        "salt": "rabeprazole + levosulpiride",
        "class": "ppi + neuromodulator prokinetic",
        "typical_use": "functional dyspepsia, diabetic gastroparesis, and severe GERD"
    },
    "rabicipd": {
        "salt": "rabeprazole + domperidone",
        "class": "ppi + prokinetic",
        "typical_use": "gastroesophageal reflux disease with dyspepsia"
    },
    "pariet": {
        "salt": "rabeprazole",
        "class": "proton pump inhibitor",
        "typical_use": "peptic ulcer and GERD"
    },
    "nexproit": {
        "salt": "esomeprazole + itopride",
        "class": "ppi + prokinetic",
        "typical_use": "GERD with upper abdominal fullness"
    },
    "nexprord": {
        "salt": "esomeprazole + domperidone",
        "class": "ppi + prokinetic",
        "typical_use": "acid reflux with regurgitation and nausea"
    },
    "sompraz": {
        "salt": "esomeprazole",
        "class": "proton pump inhibitor",
        "typical_use": "acid reflux and Zollinger-Ellison syndrome"
    },
    "somprazd": {
        "salt": "esomeprazole + domperidone",
        "class": "ppi + prokinetic",
        "typical_use": "GERD and functional dyspepsia"
    },
    "pand": {
        "salt": "pantoprazole + domperidone",
        "class": "ppi + prokinetic combination",
        "typical_use": "acid indigestion, nausea, and gastroesophageal reflux"
    },
    "pantociddsr": {
        "salt": "pantoprazole + domperidone sustained release",
        "class": "ppi + prokinetic SR",
        "typical_use": "GERD, dyspepsia, and chronic acid regurgitation"
    },
    "pantopd": {
        "salt": "pantoprazole + domperidone",
        "class": "ppi + prokinetic",
        "typical_use": "acid reflux and heartburn"
    },
    "omezd": {
        "salt": "omeprazole + domperidone",
        "class": "ppi + prokinetic",
        "typical_use": "acid indigestion and nausea"
    },
    "famocid": {
        "salt": "famotidine",
        "class": "h2 receptor antagonist",
        "typical_use": "gastric acidity and night-time heartburn"
    },
    "sucrafilo": {
        "salt": "sucralfate + oxethazaine",
        "class": "mucosal protector + local anesthetic suspension",
        "typical_use": "severe pain from peptic ulcer or erosive gastritis"
    },
    "udiliv": {
        "salt": "ursodeoxycholic acid",
        "class": "hydrophilic bile acid",
        "typical_use": "dissolution of gallstones, cholestatic liver disease, and fatty liver"
    },
    "ursocol": {
        "salt": "ursodeoxycholic acid",
        "class": "hepatoprotective bile acid",
        "typical_use": "primary biliary cholangitis and liver enzyme elevation"
    },
    "hepamerz": {
        "salt": "l-ornithine l-aspartate (LOLA)",
        "class": "hepatic detoxifying amino acid complex",
        "typical_use": "hyperammonemia, fatty liver, and hepatic encephalopathy"
    },
    "rifagut": {
        "salt": "rifaximin",
        "class": "non-absorbable gastrointestinal antibiotic",
        "typical_use": "irritable bowel syndrome with diarrhea (IBS-D) and hepatic encephalopathy"
    },
    "rifaxigress": {
        "salt": "rifaximin",
        "class": "gastrointestinal antibiotic",
        "typical_use": "IBS-D and small intestinal bacterial overgrowth (SIBO)"
    },
    "xifaxan": {
        "salt": "rifaximin",
        "class": "gut-selective antibiotic",
        "typical_use": "travelers diarrhea and hepatic encephalopathy recurrence prevention"
    },
    "cremaffinplus": {
        "salt": "liquid paraffin + milk of magnesia + sodium picosulfate",
        "class": "triple laxative suspension",
        "typical_use": "refractory constipation and painful anal fissures"
    },
    "pegmove": {
        "salt": "polyethylene glycol 3350",
        "class": "osmotic laxative powder",
        "typical_use": "chronic idiopathic constipation in adults and children"
    },
    "dulcolax": {
        "salt": "bisacodyl",
        "class": "stimulant diphenylmethane laxative",
        "typical_use": "overnight relief of acute constipation"
    },
    "ganaton": {
        "salt": "itopride hydrochloride",
        "class": "prokinetic D2 and AChE inhibitor",
        "typical_use": "functional dyspepsia, postprandial fullness, and early satiety"
    },
    "librax": {
        "salt": "chlordiazepoxide + clidinium bromide",
        "class": "anxiolytic + anticholinergic antispasmodic",
        "typical_use": "irritable bowel syndrome, spastic colon, and nervous stomach"
    },
    "drotin": {
        "salt": "drotaverine hydrochloride",
        "class": "phosphodiesterase-4 inhibitor antispasmodic",
        "typical_use": "smooth muscle spasms, renal colic, biliary colic, and dysmenorrhea"
    },
    "drotinm": {
        "salt": "drotaverine + mefenamic acid",
        "class": "antispasmodic + nsaid combination",
        "typical_use": "severe dysmenorrhea and sharp abdominal colic"
    },
    "spasmoproxyvon": {
        "salt": "dicyclomine + paracetamol + tramadol",
        "class": "potent antispasmodic analgesic",
        "typical_use": "severe spasmodic visceral pain"
    },
    "eldoper": {
        "salt": "loperamide hydrochloride",
        "class": "peripheral opioid receptor antidiarrheal",
        "typical_use": "acute non-infectious diarrhea and IBS-D"
    },
    "imodium": {
        "salt": "loperamide",
        "class": "antidiarrheal agent",
        "typical_use": "symptomatic control of acute and chronic diarrhea"
    },
    "econorm": {
        "salt": "saccharomyces boulardii",
        "class": "probiotic yeast",
        "typical_use": "antibiotic-associated diarrhea and acute infectious gastroenteritis"
    },
    "darolac": {
        "salt": "probiotic combination (lactobacillus + bifidobacterium)",
        "class": "multi-strain gut flora restorer",
        "typical_use": "restoration of normal gut microbiome post-antibiotics"
    },
    "sporlac": {
        "salt": "bacillus coagulans (lactic acid bacillus)",
        "class": "spore-forming probiotic",
        "typical_use": "gastrointestinal dysbiosis and infantile diarrhea"
    },
    "vsl3": {
        "salt": "high-concentration probiotic formulation (450 billion CFU)",
        "class": "medical food probiotic",
        "typical_use": "ulcerative colitis, pouchitis, and severe IBS"
    },
    "zofran": {
        "salt": "ondansetron",
        "class": "5-HT3 antiemetic",
        "typical_use": "nausea and vomiting"
    },
    "emeset": {
        "salt": "ondansetron",
        "class": "5-HT3 antagonist antiemetic",
        "typical_use": "vomiting and gastrointestinal upset"
    },
    "perinorm": {
        "salt": "metoclopramide hydrochloride",
        "class": "prokinetic dopamine antagonist",
        "typical_use": "delayed gastric emptying, diabetic gastroparesis, and nausea"
    },
    "vomistop": {
        "salt": "domperidone",
        "class": "peripheral dopamine D2 antagonist",
        "typical_use": "nausea, vomiting, and fullness"
    },
    "stemetil": {
        "salt": "prochlorperazine maleate",
        "class": "phenothiazine antiemetic and vestibular sedative",
        "typical_use": "severe nausea, vomiting, dizziness, and Meniere vertigo"
    },
    "montairlc": {
        "salt": "montelukast + levocetirizine",
        "class": "leukotriene receptor antagonist + antihistamine",
        "typical_use": "allergic rhinitis, seasonal sneezing, runny nose, and asthma flare prophylaxis"
    },
    "telekastl": {
        "salt": "montelukast + levocetirizine",
        "class": "ltra + antihistamine combination",
        "typical_use": "chronic allergic rhinitis and nighttime allergic cough"
    },
    "monteklc": {
        "salt": "montelukast + levocetirizine",
        "class": "ltra + antihistamine",
        "typical_use": "allergic rhinitis and bronchospasm"
    },
    "allegram": {
        "salt": "fexofenadine + montelukast",
        "class": "antihistamine + ltra combination",
        "typical_use": "allergic rhinitis and asthma symptoms with daytime alertness"
    },
    "bilashine": {
        "salt": "bilastine",
        "class": "second-generation non-sedating antihistamine",
        "typical_use": "allergic rhinoconjunctivitis and itchy urticaria without CNS sedation"
    },
    "bilaran": {
        "salt": "bilastine",
        "class": "non-sedating antihistamine",
        "typical_use": "allergic rhinitis and skin allergies"
    },
    "bilasure": {
        "salt": "bilastine",
        "class": "antihistamine",
        "typical_use": "allergic rhinitis and hives"
    },
    "levocet": {
        "salt": "levocetirizine dihydrochloride",
        "class": "second-generation active antihistamine",
        "typical_use": "allergic rhinitis and pruritus"
    },
    "seroflo": {
        "salt": "fluticasone propionate + salmeterol xinafoate",
        "class": "ICS-LABA inhaler",
        "typical_use": "chronic maintenance therapy for persistent asthma and severe COPD"
    },
    "aerocort": {
        "salt": "beclomethasone + levosalbutamol",
        "class": "ICS + short-acting bronchodilator inhaler/rotacaps",
        "typical_use": "bronchospasm and airway inflammation"
    },
    "tiova": {
        "salt": "tiotropium bromide",
        "class": "long-acting muscarinic antagonist (lama) bronchodilator",
        "typical_use": "once-daily maintenance bronchodilation in COPD"
    },
    "spiriva": {
        "salt": "tiotropium",
        "class": "long-acting anticholinergic bronchodilator",
        "typical_use": "COPD maintenance therapy"
    },
    "flohale": {
        "salt": "fluticasone propionate",
        "class": "inhaled corticosteroid",
        "typical_use": "chronic persistent asthma prophylaxis"
    },
    "ascorild": {
        "salt": "dextromethorphan + phenylephrine + chlorpheniramine",
        "class": "antitussive + decongestant + antihistamine syrup",
        "typical_use": "dry hacking cough, nasal congestion, and throat tickle"
    },
    "ascorills": {
        "salt": "levosalbutamol + ambroxol + guaiphenesin",
        "class": "expectorant + mucolytic + bronchodilator",
        "typical_use": "wet cough, chest congestion, and mucus plugs in bronchitis"
    },
    "benadryl": {
        "salt": "diphenhydramine hydrochloride",
        "class": "first-generation sedating antihistamine and cough suppressant",
        "typical_use": "allergic cough, runny nose, and nocturnal cough relief"
    },
    "solvincold": {
        "salt": "paracetamol + phenylephrine + chlorpheniramine",
        "class": "analgesic + decongestant + antihistamine cold tablet",
        "typical_use": "fever, headache, nasal congestion, and sneezing in viral rhinitis"
    },
    "chestoncold": {
        "salt": "cetirizine + paracetamol + phenylephrine",
        "class": "cold, sinus, and allergy combination",
        "typical_use": "cold symptoms, sinus pain, and runny nose"
    },
    "flomist": {
        "salt": "fluticasone furoate/propionate",
        "class": "intranasal corticosteroid spray",
        "typical_use": "allergic rhinitis, seasonal nasal congestion, and itchy watery eyes"
    },
    "zerodolp": {
        "salt": "aceclofenac + paracetamol",
        "class": "nsaid + analgesic antipyretic combination",
        "typical_use": "inflammatory musculoskeletal pain, joint pain, and fever"
    },
    "zerodolsp": {
        "salt": "aceclofenac + paracetamol + serratiopeptidase",
        "class": "nsaid + analgesic + anti-edema enzyme",
        "typical_use": "acute painful swelling, postoperative trauma, and dental pain"
    },
    "zerodolth": {
        "salt": "aceclofenac + thiocolchicoside",
        "class": "nsaid + skeletal muscle relaxant",
        "typical_use": "severe muscle spasms, lumbago, neck stiffness, and sprains"
    },
    "hifenacth": {
        "salt": "aceclofenac + thiocolchicoside",
        "class": "nsaid + muscle relaxant",
        "typical_use": "muscle spasms and orthopedic trauma"
    },
    "nucoxia": {
        "salt": "etoricoxib",
        "class": "selective cox-2 inhibitor nsaid",
        "typical_use": "acute gouty arthritis, ankylosing spondylitis, and dental surgery pain"
    },
    "arcoxia": {
        "salt": "etoricoxib",
        "class": "selective cox-2 inhibitor",
        "typical_use": "acute pain and inflammatory arthritis"
    },
    "etoshine": {
        "salt": "etoricoxib",
        "class": "selective cox-2 inhibitor nsaid",
        "typical_use": "osteoarthritis and gout flares"
    },
    "sumo": {
        "salt": "nimesulide + paracetamol",
        "class": "nsaid + analgesic combination",
        "typical_use": "acute musculoskeletal pain, dental ache, and severe inflammatory trauma"
    },
    "nise": {
        "salt": "nimesulide",
        "class": "preferential cox-2 nsaid",
        "typical_use": "acute painful inflammatory conditions and dysmenorrhea"
    },
    "voveransr": {
        "salt": "diclofenac sodium sustained release 100mg",
        "class": "nsaid sustained release",
        "typical_use": "24-hour chronic arthritis and spondylitis pain relief"
    },
    "dynapar": {
        "salt": "diclofenac + paracetamol",
        "class": "potent nsaid + analgesic",
        "typical_use": "acute severe musculoskeletal injury and post-trauma pain"
    },
    "dynaparqps": {
        "salt": "diclofenac topical solution",
        "class": "topical nsaid quick penetrating solution",
        "typical_use": "localized joint and muscle pain without systemic GI side effects"
    },
    "flexon": {
        "salt": "ibuprofen + paracetamol",
        "class": "nsaid analgesic combination",
        "typical_use": "fever, dental ache, and musculoskeletal pain"
    },
    "tramazac": {
        "salt": "tramadol hydrochloride",
        "class": "opioid analgesic",
        "typical_use": "moderate to severe acute or chronic pain"
    },
    "tramal": {
        "salt": "tramadol",
        "class": "opioid analgesic",
        "typical_use": "postoperative and severe chronic pain"
    },
    "muscoril": {
        "salt": "thiocolchicoside",
        "class": "muscle relaxant",
        "typical_use": "acute musculoskeletal contractures and spasms"
    },
    "liofen": {
        "salt": "baclofen",
        "class": "GABA-B agonist muscle relaxant",
        "typical_use": "muscle spasticity in spinal cord trauma or neurological lesions"
    },
    "tizan": {
        "salt": "tizanidine hydrochloride",
        "class": "alpha-2 adrenergic muscle relaxant",
        "typical_use": "muscle spasms and chronic spinal pain"
    },
    "febutaz": {
        "salt": "febuxostat",
        "class": "non-purine selective xanthine oxidase inhibitor",
        "typical_use": "chronic management of hyperuricemia in gout"
    },
    "feburic": {
        "salt": "febuxostat",
        "class": "xanthine oxidase inhibitor",
        "typical_use": "gout and high uric acid levels"
    },
    "zyloric": {
        "salt": "allopurinol",
        "class": "xanthine oxidase inhibitor",
        "typical_use": "chronic gout prophylaxis and prevention of uric acid kidney stones"
    },
    "folitrax": {
        "salt": "methotrexate",
        "class": "antifolate dmard",
        "typical_use": "active rheumatoid arthritis, severe psoriasis, and Crohn disease"
    },
    "hcqs": {
        "salt": "hydroxychloroquine sulfate",
        "class": "antimalarial / immunomodulatory dmard",
        "typical_use": "systemic lupus erythematosus (SLE) and rheumatoid arthritis"
    },
    "saaz": {
        "salt": "sulfasalazine",
        "class": "dmard and aminosalicylate",
        "typical_use": "rheumatoid arthritis, ankylosing spondylitis, and ulcerative colitis"
    },
    "zycolchin": {
        "salt": "colchicine",
        "class": "anti-gout alkaloid",
        "typical_use": "acute gout flares and prevention of gout attacks"
    },
    "defcort": {
        "salt": "deflazacort",
        "class": "systemic glucocorticoid with bone-sparing properties",
        "typical_use": "severe autoimmune diseases, nephrotic syndrome, and asthma flares"
    },
    "wysolone": {
        "salt": "prednisolone",
        "class": "systemic corticosteroid",
        "typical_use": "inflammatory disorders, allergic reactions, and autoimmune conditions"
    },
    "omnacortil": {
        "salt": "prednisolone",
        "class": "systemic corticosteroid",
        "typical_use": "acute inflammatory states, severe asthma, and immune suppression"
    },
    "medrol": {
        "salt": "methylprednisolone",
        "class": "systemic glucocorticoid",
        "typical_use": "acute rheumatic disorders, severe allergic states, and spinal cord trauma"
    },
    "kenacort": {
        "salt": "triamcinolone acetonide",
        "class": "intermediate-acting glucocorticoid",
        "typical_use": "intra-articular joint injections and severe dermatological lesions"
    },
    "betnesol": {
        "salt": "betamethasone sodium phosphate",
        "class": "fast-acting glucocorticoid",
        "typical_use": "severe allergic emergencies, shock, and fetal lung maturation"
    },
    "cefakind": {
        "salt": "cefuroxime axetil",
        "class": "second-generation cephalosporin",
        "typical_use": "acute bacterial sinusitis, bronchitis, pharyngitis, and skin infections"
    },
    "zificv": {
        "salt": "cefixime + potassium clavulanate",
        "class": "cephalosporin + beta-lactamase inhibitor",
        "typical_use": "resistant ENT, respiratory, and urinary bacterial infections"
    },
    "taximo": {
        "salt": "cefixime",
        "class": "third-generation cephalosporin oral",
        "typical_use": "typhoid fever, bacterial bronchitis, and urinary tract infections"
    },
    "monocefo": {
        "salt": "cefpodoxime proxetil",
        "class": "third-generation cephalosporin oral",
        "typical_use": "acute bacterial otitis media, tonsillitis, and community-acquired pneumonia"
    },
    "gudcef": {
        "salt": "cefpodoxime proxetil",
        "class": "third-generation cephalosporin",
        "typical_use": "bacterial respiratory and skin infections"
    },
    "macpod": {
        "salt": "cefpodoxime proxetil",
        "class": "third-generation cephalosporin",
        "typical_use": "bacterial infections"
    },
    "farobact": {
        "salt": "faropenem sodium",
        "class": "oral penem antibiotic",
        "typical_use": "refractory respiratory tract infections, sinusitis, and complicated UTI"
    },
    "faronem": {
        "salt": "faropenem",
        "class": "oral penem antibiotic",
        "typical_use": "resistant community-acquired respiratory bacterial infections"
    },
    "doxicip": {
        "salt": "doxycycline",
        "class": "tetracycline antibiotic",
        "typical_use": "atypical respiratory infections, acne vulgaris, and rickettsial typhus"
    },
    "minoz": {
        "salt": "minocycline",
        "class": "tetracycline antibiotic",
        "typical_use": "inflammatory acne vulgaris and resistant bacterial skin infections"
    },
    "roxid": {
        "salt": "roxithromycin",
        "class": "macrolide antibiotic",
        "typical_use": "upper and lower respiratory tract infections and tonsillitis"
    },
    "vigamox": {
        "salt": "moxifloxacin 0.5% ophthalmic",
        "class": "fluoroquinolone antibiotic eye drops",
        "typical_use": "bacterial conjunctivitis and corneal ulcer prophylaxis"
    },
    "ciploxd": {
        "salt": "ciprofloxacin + dexamethasone",
        "class": "antibiotic + corticosteroid ear/eye drops",
        "typical_use": "acute otitis externa, otitis media with perforation, and post-op eye inflammation"
    },
    "ofloxoz": {
        "salt": "ofloxacin + ornidazole",
        "class": "fluoroquinolone + nitroimidazole combination",
        "typical_use": "mixed bacterial and amoebic diarrhea/dysentery and dental infections"
    },
    "metrogylp": {
        "salt": "povidone iodine + metronidazole",
        "class": "antiseptic + antimicrobial ointment",
        "typical_use": "infected surgical wounds, burns, and chronic diabetic ulcers"
    },
    "candiforce": {
        "salt": "itraconazole",
        "class": "triazole antifungal",
        "typical_use": "refractory tinea corporis, tinea cruris, and onychomycosis"
    },
    "fluka": {
        "salt": "fluconazole",
        "class": "triazole antifungal",
        "typical_use": "vaginal candidiasis, oral thrush, and systemic fungal prophylaxis"
    },
    "candid": {
        "salt": "clotrimazole 1%",
        "class": "topical imidazole antifungal",
        "typical_use": "athlete's foot, jock itch, ringworm, and sweat rashes"
    },
    "canesten": {
        "salt": "clotrimazole",
        "class": "topical antifungal / vaginal pessary",
        "typical_use": "vaginal thrush and fungal skin infections"
    },
    "lulifin": {
        "salt": "luliconazole 1%",
        "class": "broad-spectrum topical imidazole antifungal",
        "typical_use": "tinea cruris, tinea corporis, and tinea pedis with once-daily application"
    },
    "lulican": {
        "salt": "luliconazole",
        "class": "potent topical antifungal",
        "typical_use": "dermatophyte fungal skin infections"
    },
    "sebifin": {
        "salt": "terbinafine",
        "class": "allylamine antifungal",
        "typical_use": "tinea infections and fungal nail dystrophy"
    },
    "terbicip": {
        "salt": "terbinafine",
        "class": "allylamine antifungal",
        "typical_use": "fungal nail infections and extensive ringworm"
    },
    "nizral": {
        "salt": "ketoconazole 2% shampoo/cream",
        "class": "imidazole antifungal",
        "typical_use": "dandruff, seborrheic dermatitis, and pityriasis versicolor"
    },
    "ketocip": {
        "salt": "ketoconazole",
        "class": "antifungal",
        "typical_use": "cutaneous fungal infections and flaking scalp"
    },
    "famtrex": {
        "salt": "famciclovir",
        "class": "antiviral guanosine analogue",
        "typical_use": "herpes zoster and acute recurrent genital herpes"
    },
    "brivasure": {
        "salt": "brivudine",
        "class": "nucleoside analogue antiviral",
        "typical_use": "early treatment of acute herpes zoster in immunocompetent adults"
    },
    "paxlovid": {
        "salt": "nirmatrelvir + ritonavir",
        "class": "SARS-CoV-2 main protease inhibitor",
        "typical_use": "mild to moderate COVID-19 in patients at high risk of severe progression"
    },
    "pregeb": {
        "salt": "pregabalin",
        "class": "voltage-gated calcium channel alpha-2-delta ligand",
        "typical_use": "neuropathic pain, fibromyalgia, and spinal nerve compression"
    },
    "pregebm": {
        "salt": "pregabalin + methylcobalamin",
        "class": "neuropathic agent + neurotropic vitamin",
        "typical_use": "diabetic peripheral neuropathy, sciatica, and nerve regeneration"
    },
    "pregebnt": {
        "salt": "pregabalin + nortriptyline",
        "class": "calcium channel modulator + tricyclic antidepressant",
        "typical_use": "refractory neuropathic pain, radiculopathy, and nocturnal nerve burning"
    },
    "gabapinnt": {
        "salt": "gabapentin + nortriptyline",
        "class": "gaba analogue + TCA",
        "typical_use": "chronic neuropathic pain and diabetic nerve discomfort"
    },
    "gabaneuron": {
        "salt": "gabapentin + methylcobalamin",
        "class": "neuropathic agent + vitamin b12",
        "typical_use": "peripheral nerve numbness, tingling, and paresthesias"
    },
    "nexitoplus": {
        "salt": "escitalopram + clonazepam",
        "class": "ssri + benzodiazepine combination",
        "typical_use": "severe anxiety with acute panic symptoms and depressive agitation"
    },
    "clonafit": {
        "salt": "clonazepam",
        "class": "benzodiazepine anticonvulsant and anxiolytic",
        "typical_use": "panic attacks, social anxiety, and restless leg syndrome"
    },
    "clonotril": {
        "salt": "clonazepam",
        "class": "high-potency benzodiazepine",
        "typical_use": "panic disorder and seizure disorders"
    },
    "rivotril": {
        "salt": "clonazepam",
        "class": "benzodiazepine",
        "typical_use": "epilepsy and panic attacks"
    },
    "restyl": {
        "salt": "alprazolam",
        "class": "short-acting triazolobenzodiazepine",
        "typical_use": "acute panic attacks and transient acute anxiety"
    },
    "zolcalm": {
        "salt": "zolpidem tartrate",
        "class": "non-benzodiazepine GABA-A positive modulator (z-drug)",
        "typical_use": "short-term pharmacological relief of severe insomnia"
    },
    "zolfresh": {
        "salt": "zolpidem",
        "class": "hypnotic agent",
        "typical_use": "short-term treatment of sleep onset difficulty"
    },
    "oleanz": {
        "salt": "olanzapine",
        "class": "atypical antipsychotic",
        "typical_use": "schizophrenia and acute bipolar manic episodes"
    },
    "sizodon": {
        "salt": "risperidone",
        "class": "atypical antipsychotic",
        "typical_use": "schizophrenia and acute bipolar mania"
    },
    "serenace": {
        "salt": "haloperidol",
        "class": "typical butyrophenone antipsychotic",
        "typical_use": "acute psychiatric agitation, delirium, and severe psychosis"
    },
    "valparin": {
        "salt": "sodium valproate",
        "class": "broad-spectrum antiepileptic",
        "typical_use": "generalized tonic-clonic seizures, absence seizures, and bipolar disorder"
    },
    "tegrital": {
        "salt": "carbamazepine",
        "class": "sodium channel blocker anticonvulsant",
        "typical_use": "focal epileptic seizures and trigeminal neuralgia"
    },
    "epitril": {
        "salt": "clonazepam",
        "class": "benzodiazepine",
        "typical_use": "epileptic seizures and panic states"
    },
    "levera": {
        "salt": "levetiracetam",
        "class": "SV2A ligand antiepileptic",
        "typical_use": "partial onset and generalized tonic-clonic epileptic seizures"
    },
    "vertin": {
        "salt": "betahistine dihydrochloride",
        "class": "histaminergic antivertigo agent",
        "typical_use": "vertigo, dizziness, tinnitus, and ear fullness in Meniere disease"
    },
    "stugeron": {
        "salt": "cinnarizine",
        "class": "labyrinthine sedative and calcium antagonist",
        "typical_use": "vestibular vertigo, motion sickness, and peripheral circulatory disorders"
    },
    "dizitek": {
        "salt": "flunarizine hydrochloride",
        "class": "selective calcium entry blocker",
        "typical_use": "migraine prophylaxis and refractory vestibular vertigo"
    },
    "sibelium": {
        "salt": "flunarizine",
        "class": "calcium channel blocker",
        "typical_use": "prevention of classical migraine headaches"
    },
    "pacitane": {
        "salt": "trihexyphenidyl (benzhexol)",
        "class": "anticholinergic antiparkinsonian agent",
        "typical_use": "drug-induced extrapyramidal symptoms and Parkinson tremors"
    },
    "syndopa": {
        "salt": "levodopa + carbidopa",
        "class": "dopamine precursor + decarboxylase inhibitor",
        "typical_use": "idiopathic Parkinson disease motor symptoms"
    },
    "donecept": {
        "salt": "donepezil hydrochloride",
        "class": "reversible acetylcholinesterase inhibitor",
        "typical_use": "mild to moderate dementia in Alzheimer disease"
    },
    "memaneuron": {
        "salt": "memantine hydrochloride",
        "class": "uncompetitive NMDA receptor antagonist",
        "typical_use": "moderate to severe Alzheimer disease dementia"
    },
    "urimax": {
        "salt": "tamsulosin hydrochloride 0.4mg",
        "class": "selective alpha-1A adrenergic blocker",
        "typical_use": "benign prostatic hyperplasia (BPH) urinary hesitancy and weak stream"
    },
    "urimaxd": {
        "salt": "tamsulosin + dutasteride",
        "class": "alpha blocker + 5-alpha reductase inhibitor",
        "typical_use": "enlarged prostate with severe urinary obstruction and retention risk"
    },
    "silodal": {
        "salt": "silodosin",
        "class": "highly selective alpha-1A adrenergic blocker",
        "typical_use": "BPH urinary flow improvement with minimal postural hypotension"
    },
    "silofast": {
        "salt": "silodosin",
        "class": "uroselective alpha blocker",
        "typical_use": "lower urinary tract symptoms from enlarged prostate"
    },
    "dutas": {
        "salt": "dutasteride 0.5mg",
        "class": "dual 5-alpha reductase inhibitor",
        "typical_use": "prostate volume reduction and long-term BPH management"
    },
    "avodart": {
        "salt": "dutasteride",
        "class": "5-alpha reductase inhibitor",
        "typical_use": "benign prostatic hyperplasia"
    },
    "fincar": {
        "salt": "finasteride 5mg",
        "class": "type II 5-alpha reductase inhibitor",
        "typical_use": "benign prostatic hyperplasia symptom reduction"
    },
    "proscar": {
        "salt": "finasteride 5mg",
        "class": "5-alpha reductase inhibitor",
        "typical_use": "prostate enlargement"
    },
    "propecia": {
        "salt": "finasteride 1mg",
        "class": "5-alpha reductase inhibitor",
        "typical_use": "male androgenetic alopecia (pattern hair loss)"
    },
    "alfusin": {
        "salt": "alfuzosin hydrochloride 10mg PR",
        "class": "uroselective alpha-1 blocker",
        "typical_use": "benign prostatic hyperplasia and acute urinary retention catheter removal"
    },
    "xatral": {
        "salt": "alfuzosin",
        "class": "alpha-1 blocker",
        "typical_use": "benign prostatic hyperplasia"
    },
    "urik": {
        "salt": "potassium citrate + citric acid oral solution",
        "class": "urinary alkalinizing agent",
        "typical_use": "prevention of uric acid kidney stones and relief of painful burning urination"
    },
    "citralka": {
        "salt": "disodium hydrogen citrate syrup",
        "class": "systemic urinary alkalizer",
        "typical_use": "burning micturition, cystitis, and hyperuricemia"
    },
    "manforce": {
        "salt": "sildenafil citrate",
        "class": "phosphodiesterase type 5 (pde-5) inhibitor",
        "typical_use": "erectile dysfunction and pulmonary arterial hypertension"
    },
    "vigore": {
        "salt": "sildenafil",
        "class": "pde-5 inhibitor",
        "typical_use": "erectile dysfunction"
    },
    "megalis": {
        "salt": "tadalafil",
        "class": "long-acting pde-5 inhibitor",
        "typical_use": "erectile dysfunction and benign prostatic hyperplasia symptoms"
    },
    "cialis": {
        "salt": "tadalafil",
        "class": "pde-5 inhibitor",
        "typical_use": "erectile dysfunction and BPH lower urinary tract symptoms"
    },
    "becosules": {
        "salt": "vitamin b-complex + vitamin c",
        "class": "water-soluble multivitamin formulation",
        "typical_use": "mouth ulcers, glossitis, vitamin deficiency, and post-antibiotic recovery"
    },
    "neurobion": {
        "salt": "vitamin b1, b6, b12",
        "class": "neurotropic vitamin complex",
        "typical_use": "peripheral nerve tingling, numbness, and nutritional neuropathy"
    },
    "neurobionforte": {
        "salt": "vitamin b-complex with b12",
        "class": "high-dose neurotropic vitamins",
        "typical_use": "diabetic neuropathy support and vitamin B deficiency"
    },
    "supradyn": {
        "salt": "multivitamin + multiminerals + trace elements",
        "class": "daily comprehensive micronutrient tablet",
        "typical_use": "nutritional supplementation, general fatigue, and convalescence"
    },
    "shelcal": {
        "salt": "calcium carbonate 500mg + vitamin d3 250 IU",
        "class": "calcium and mineral supplement",
        "typical_use": "osteopenia, osteoporosis prevention, pregnancy, and lactation"
    },
    "shelcalhd": {
        "salt": "calcium carbonate 500mg + vitamin d3 500 IU",
        "class": "high-dose calcium and vitamin d3",
        "typical_use": "postmenopausal osteoporosis and chronic bone weakness"
    },
    "calcirol": {
        "salt": "cholecalciferol (vitamin d3 60,000 IU)",
        "class": "high-potency weekly secosteroid vitamin",
        "typical_use": "treatment of severe vitamin D deficiency, hypocalcemia, and rickets"
    },
    "drise": {
        "salt": "cholecalciferol 60,000 IU",
        "class": "vitamin d3 supplement",
        "typical_use": "vitamin D deficiency correction and bone density restoration"
    },
    "tayo": {
        "salt": "cholecalciferol 60,000 IU",
        "class": "vitamin d3 weekly capsule",
        "typical_use": "vitamin D deficiency and joint pain"
    },
    "oroferxt": {
        "salt": "ferrous ascorbate + folic acid",
        "class": "bioavailable iron supplement",
        "typical_use": "iron deficiency anemia, fatigue, and antenatal iron support"
    },
    "dexorange": {
        "salt": "ferric ammonium citrate + cyanocobalamin + folic acid syrup",
        "class": "hematinic syrup",
        "typical_use": "nutritional iron deficiency anemia and general debility"
    },
    "livogen": {
        "salt": "ferrous fumarate + folic acid",
        "class": "iron and folic acid supplement",
        "typical_use": "anemia prevention and red blood cell production"
    },
    "folvite": {
        "salt": "folic acid 5mg",
        "class": "essential water-soluble B vitamin",
        "typical_use": "preconception and pregnancy neural tube defect prevention, and macrocytic anemia"
    },
    "evion": {
        "salt": "alpha-tocopheryl acetate (vitamin e 400mg)",
        "class": "fat-soluble antioxidant capsule",
        "typical_use": "leg cramps, muscle twitches, oxidative skin support, and male subfertility"
    },
    "zincovit": {
        "salt": "multivitamin + multimineral + zinc (100% RDA)",
        "class": "immune-support multivitamin tablet",
        "typical_use": "nutritional immunity support, wound recovery, and viral infection convalescence"
    },
    "limcee": {
        "salt": "ascorbic acid 500mg (vitamin c) chewable",
        "class": "water-soluble antioxidant vitamin",
        "typical_use": "scurvy prevention, immune defense, and collagen tissue healing"
    },
    "celin": {
        "salt": "vitamin c 500mg chewable",
        "class": "ascorbic acid tablet",
        "typical_use": "vitamin C deficiency and antioxidant support"
    },
    "primolutn": {
        "salt": "norethisterone 5mg",
        "class": "synthetic progestin",
        "typical_use": "postponement of menstruation, dysfunctional uterine bleeding, and endometriosis"
    },
    "regestrone": {
        "salt": "norethisterone 5mg",
        "class": "oral progestogen",
        "typical_use": "heavy menstrual bleeding, secondary amenorrhea, and cycle regulation"
    },
    "susten": {
        "salt": "natural micronized progesterone",
        "class": "bioidentical corpus luteum hormone",
        "typical_use": "threatened abortion, recurrent pregnancy loss, and IVF luteal phase support"
    },
    "duphaston": {
        "salt": "dydrogesterone 10mg",
        "class": "oral retroprogesterone",
        "typical_use": "habitual miscarriage, threatened abortion, dysmenorrhea, and luteal insufficiency"
    },
    "unwanted72": {
        "salt": "levonorgestrel 1.5mg",
        "class": "single-dose emergency contraceptive",
        "typical_use": "emergency contraception taken within 72 hours of unprotected intercourse"
    },
    "ipill": {
        "salt": "levonorgestrel 1.5mg",
        "class": "emergency post-coital progestin",
        "typical_use": "post-coital pregnancy prevention within 72 hours"
    },
    "betnovatec": {
        "salt": "betamethasone valerate + clioquinol",
        "class": "topical corticosteroid + antibacterial/antifungal",
        "typical_use": "eczema or dermatitis with secondary bacterial or fungal infection"
    },
    "betnovaten": {
        "salt": "betamethasone valerate + neomycin",
        "class": "topical steroid + aminoglycoside antibiotic",
        "typical_use": "infected inflammatory skin conditions"
    },
    "clobetamilg": {
        "salt": "clobetasol propionate + gentamicin",
        "class": "potent topical steroid + antibacterial",
        "typical_use": "severe inflammatory dermatoses with secondary bacterial infection"
    },
    "pandermplus": {
        "salt": "clobetasol + neomycin + miconazole",
        "class": "triple corticosteroid + antibiotic + antifungal cream",
        "typical_use": "mixed cutaneous infections and severely inflamed eczema"
    },
    "fourderm": {
        "salt": "chlorhexidine + clobetasol + miconazole + neomycin",
        "class": "broad antimicrobial anti-inflammatory cream",
        "typical_use": "severe mixed cutaneous infections"
    },
    "silverex": {
        "salt": "silver sulfadiazine + chlorhexidine",
        "class": "antimicrobial burn cream",
        "typical_use": "second and third-degree burn wound infection prevention and healing"
    },
    "burnol": {
        "salt": "aminacrine + cetrimide",
        "class": "antiseptic first-aid cream",
        "typical_use": "minor superficial cuts, scratches, and first-degree burn dressing"
    },
    "soframycin": {
        "salt": "framycetin sulphate 1%",
        "class": "topical aminoglycoside antibiotic cream",
        "typical_use": "minor skin cuts, superficial abrasions, paronychia, and infected ulcers"
    },
    "bactroban": {
        "salt": "mupirocin 2%",
        "class": "topical antibacterial",
        "typical_use": "MRSA skin colonization eradication and superficial skin infections"
    },
    "tobrex": {
        "salt": "tobramycin 0.3% ophthalmic",
        "class": "aminoglycoside antibiotic eye drops",
        "typical_use": "superficial bacterial ocular infections and conjunctivitis"
    },
    "refreshtears": {
        "salt": "carboxymethylcellulose 0.5% eye drops",
        "class": "lubricating artificial tears",
        "typical_use": "dry eye syndrome, computer vision ocular fatigue, and burning sensations"
    },
    "tearsnaturale": {
        "salt": "dextran 70 + hypromellose eye drops",
        "class": "ophthalmic ocular lubricant",
        "typical_use": "dry eyes and eye irritation relief"
    },
    "systane": {
        "salt": "polyethylene glycol 400 + propylene glycol eye drops",
        "class": "advanced ocular surface lubricant",
        "typical_use": "extended dry eye relief and ocular burning/stinging relief"
    },
    "zocor": {
        "salt": "simvastatin",
        "class": "statin",
        "typical_use": "hypercholesterolemia"
    },
    "norvasc": {
        "salt": "amlodipine",
        "class": "calcium channel blocker",
        "typical_use": "hypertension and angina"
    },
    "zestril": {
        "salt": "lisinopril",
        "class": "ace inhibitor",
        "typical_use": "hypertension and heart failure"
    },
    "altace": {
        "salt": "ramipril",
        "class": "ace inhibitor",
        "typical_use": "hypertension and heart failure"
    },
    "cozaar": {
        "salt": "losartan",
        "class": "angiotensin II receptor blocker",
        "typical_use": "hypertension and diabetic nephropathy"
    },
    "hyzaar": {
        "salt": "losartan + hydrochlorothiazide",
        "class": "arb + diuretic combination",
        "typical_use": "hypertension"
    },
    "diovan": {
        "salt": "valsartan",
        "class": "angiotensin II receptor blocker",
        "typical_use": "hypertension and heart failure"
    },
    "lopressor": {
        "salt": "metoprolol tartrate",
        "class": "beta-1 blocker",
        "typical_use": "angina and hypertension"
    },
    "toprolxl": {
        "salt": "metoprolol succinate extended release",
        "class": "beta-1 blocker ER",
        "typical_use": "hypertension and heart failure"
    },
    "coreg": {
        "salt": "carvedilol",
        "class": "alpha/beta blocker",
        "typical_use": "heart failure and post-MI left ventricular dysfunction"
    },
    "singulair": {
        "salt": "montelukast sodium",
        "class": "leukotriene receptor antagonist",
        "typical_use": "asthma maintenance and allergic rhinitis"
    },
    "claritin": {
        "salt": "loratadine",
        "class": "second-generation antihistamine",
        "typical_use": "allergic rhinitis and urticaria"
    },
    "prilosec": {
        "salt": "omeprazole",
        "class": "proton pump inhibitor",
        "typical_use": "GERD, heartburn, and peptic ulcer"
    },
    "nexium": {
        "salt": "esomeprazole magnesium",
        "class": "proton pump inhibitor",
        "typical_use": "erosive esophagitis and acid reflux"
    },
    "prevacid": {
        "salt": "lansoprazole",
        "class": "proton pump inhibitor",
        "typical_use": "peptic ulcer and GERD"
    },
    "pepcid": {
        "salt": "famotidine",
        "class": "h2 receptor antagonist",
        "typical_use": "heartburn and hyperacidity"
    },
    "reglan": {
        "salt": "metoclopramide",
        "class": "prokinetic dopamine antagonist",
        "typical_use": "diabetic gastroparesis and GERD"
    },
    "ambien": {
        "salt": "zolpidem tartrate",
        "class": "sedative hypnotic (z-drug)",
        "typical_use": "short-term treatment of insomnia"
    },
    "xanax": {
        "salt": "alprazolam",
        "class": "triazolobenzodiazepine",
        "typical_use": "panic disorder and generalized anxiety"
    },
    "klonopin": {
        "salt": "clonazepam",
        "class": "benzodiazepine",
        "typical_use": "panic attacks and seizure disorders"
    },
    "valium": {
        "salt": "diazepam",
        "class": "benzodiazepine",
        "typical_use": "anxiety, muscle spasms, and seizure emergency"
    },
    "prozac": {
        "salt": "fluoxetine",
        "class": "ssri antidepressant",
        "typical_use": "major depression, OCD, and panic disorder"
    },
    "zoloft": {
        "salt": "sertraline hydrochloride",
        "class": "ssri antidepressant",
        "typical_use": "depression, anxiety, and PTSD"
    },
    "lexapro": {
        "salt": "escitalopram",
        "class": "ssri antidepressant",
        "typical_use": "depression and generalized anxiety disorder"
    },
    "celexa": {
        "salt": "citalopram",
        "class": "ssri antidepressant",
        "typical_use": "major depressive disorder"
    },
    "cymbalta": {
        "salt": "duloxetine hydrochloride",
        "class": "snri antidepressant",
        "typical_use": "depression, generalized anxiety, and diabetic neuropathic pain"
    },
    "effexor": {
        "salt": "venlafaxine",
        "class": "snri antidepressant",
        "typical_use": "depression, panic disorder, and social anxiety"
    },
    "wellbutrin": {
        "salt": "bupropion hydrochloride",
        "class": "ndri antidepressant",
        "typical_use": "major depressive disorder and smoking cessation"
    },
    "lamictal": {
        "salt": "lamotrigine",
        "class": "antiepileptic and mood stabilizer",
        "typical_use": "bipolar I depression and seizure disorders"
    },
    "topamax": {
        "salt": "topiramate",
        "class": "carbonic anhydrase inhibitor antiepileptic",
        "typical_use": "epilepsy and migraine headache prophylaxis"
    },
    "dilantin": {
        "salt": "phenytoin sodium",
        "class": "hydantoin anticonvulsant",
        "typical_use": "tonic-clonic seizures and status epilepticus prophylaxis"
    },
    "sinemet": {
        "salt": "carbidopa + levodopa",
        "class": "antiparkinsonian dopamine precursor",
        "typical_use": "Parkinson disease motor symptoms"
    },
    "mirapex": {
        "salt": "pramipexole",
        "class": "dopamine agonist",
        "typical_use": "Parkinson disease and restless legs syndrome"
    },
    "requip": {
        "salt": "ropinirole",
        "class": "dopamine agonist",
        "typical_use": "Parkinson disease and restless legs syndrome"
    },
    "namenda": {
        "salt": "memantine",
        "class": "NMDA receptor antagonist",
        "typical_use": "moderate to severe Alzheimer disease"
    },
    "aricept": {
        "salt": "donepezil",
        "class": "acetylcholinesterase inhibitor",
        "typical_use": "Alzheimer disease dementia"
    }
}

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
