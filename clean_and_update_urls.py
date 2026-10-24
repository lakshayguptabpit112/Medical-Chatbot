from dotenv import load_dotenv
import warnings
import os
import time
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from helper import load_website_data, filterDocuments, ChunkingDocuments

warnings.filterwarnings("ignore")
load_dotenv()

# --- CONFIGURATION ---
index_name = "rag-based-system-v3"
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")

old_mayo_urls = [
        # --- RESPIRATORY & VIRUSES ---
        "https://www.mayoclinic.org/diseases-conditions/common-cold/symptoms-causes/syc-20351605",
        "https://www.mayoclinic.org/diseases-conditions/flu/symptoms-causes/syc-20351719",
        "https://www.mayoclinic.org/diseases-conditions/coronavirus/symptoms-causes/syc-20479963",
        "https://www.mayoclinic.org/diseases-conditions/asthma/symptoms-causes/syc-20369653",
        "https://www.mayoclinic.org/diseases-conditions/pneumonia/symptoms-causes/syc-20354204",
        "https://www.mayoclinic.org/diseases-conditions/strep-throat/symptoms-causes/syc-20350338",

        # --- HEART & METABOLIC ---
        "https://www.mayoclinic.org/diseases-conditions/high-blood-pressure/symptoms-causes/syc-20373410",
        "https://www.mayoclinic.org/diseases-conditions/high-blood-cholesterol/symptoms-causes/syc-20350800",
        "https://www.mayoclinic.org/diseases-conditions/diabetes/symptoms-causes/syc-20371444",
        "https://www.mayoclinic.org/diseases-conditions/type-2-diabetes/symptoms-causes/syc-20351193",

        # --- STOMACH & DIGESTION ---
        "https://www.mayoclinic.org/diseases-conditions/food-poisoning/symptoms-causes/syc-20356230",
        "https://www.mayoclinic.org/diseases-conditions/gerd/symptoms-causes/syc-20361940",
        "https://www.mayoclinic.org/diseases-conditions/irritable-bowel-syndrome/symptoms-causes/syc-20360016",
        "https://www.mayoclinic.org/diseases-conditions/diarrhea/symptoms-causes/syc-20352241",

        # --- HEAD, PAIN & BONES ---
        "https://www.mayoclinic.org/symptoms/headache/basics/definition/sym-20050800",
        "https://www.mayoclinic.org/diseases-conditions/migraine-headache/symptoms-causes/syc-20360201",
        "https://www.mayoclinic.org/diseases-conditions/osteoarthritis/symptoms-causes/syc-20351925",
        "https://www.mayoclinic.org/diseases-conditions/back-pain/symptoms-causes/syc-20369906",

        # --- MENTAL HEALTH ---
        "https://www.mayoclinic.org/diseases-conditions/anxiety/symptoms-causes/syc-20350961",
        "https://www.mayoclinic.org/diseases-conditions/depression/symptoms-causes/syc-20356007",
        "https://www.mayoclinic.org/diseases-conditions/insomnia/symptoms-causes/syc-20355167"
    ]

new_urls = [
    # WHO URLs
    "https://www.who.int/news-room/fact-sheets/detail/coronavirus-disease-(covid-19)",
    "https://www.who.int/news-room/fact-sheets/detail/asthma",
    "https://www.who.int/news-room/fact-sheets/detail/tuberculosis",
    "https://www.who.int/news-room/fact-sheets/detail/influenza-(seasonal)",
    "https://www.who.int/news-room/fact-sheets/detail/pneumonia",
    "https://www.who.int/news-room/fact-sheets/detail/chronic-obstructive-pulmonary-disease-(copd)",
    "https://www.who.int/news-room/fact-sheets/detail/hepatitis-b",
    "https://www.who.int/news-room/fact-sheets/detail/hepatitis-c",
    "https://www.who.int/news-room/fact-sheets/detail/cholera",
    "https://www.who.int/news-room/fact-sheets/detail/dengue-and-severe-dengue",
    "https://www.who.int/news-room/fact-sheets/detail/diabetes",
    "https://www.who.int/news-room/fact-sheets/detail/cardiovascular-diseases-(cvds)",
    "https://www.who.int/news-room/fact-sheets/detail/obesity-and-overweight",
    "https://www.who.int/news-room/fact-sheets/detail/hypertension",
    "https://www.who.int/news-room/fact-sheets/detail/anaemia",
    "https://www.who.int/news-room/fact-sheets/detail/depression",
    "https://www.who.int/news-room/fact-sheets/detail/dementia",
    "https://www.who.int/news-room/fact-sheets/detail/epilepsy",
    "https://www.who.int/news-room/fact-sheets/detail/schizophrenia",
    "https://www.who.int/news-room/fact-sheets/detail/autism-spectrum-disorders",
    "https://www.who.int/news-room/fact-sheets/detail/parkinson-disease",
    "https://www.who.int/news-room/fact-sheets/detail/hiv-aids",
    "https://www.who.int/news-room/fact-sheets/detail/malaria",
    "https://www.who.int/news-room/fact-sheets/detail/ebola-virus-disease",
    "https://www.who.int/news-room/fact-sheets/detail/zika-virus",
    "https://www.who.int/news-room/fact-sheets/detail/rabies",
    "https://www.who.int/news-room/fact-sheets/detail/poliomyelitis",
    "https://www.who.int/news-room/fact-sheets/detail/measles",
    "https://www.who.int/news-room/fact-sheets/detail/tetanus",
    "https://www.who.int/news-room/fact-sheets/detail/cancer",
    "https://www.who.int/news-room/fact-sheets/detail/breast-cancer",
    "https://www.who.int/news-room/fact-sheets/detail/cervical-cancer",
    "https://www.who.int/news-room/fact-sheets/detail/blindness-and-visual-impairment",
    "https://www.who.int/news-room/fact-sheets/detail/deafness-and-hearing-loss",
    "https://www.who.int/news-room/fact-sheets/detail/burns",
    "https://www.who.int/news-room/fact-sheets/detail/headache-disorders",
    
    # Wikipedia URLs
    "https://en.wikipedia.org/wiki/Common_cold",
    "https://en.wikipedia.org/wiki/Streptococcal_pharyngitis",
    "https://en.wikipedia.org/wiki/Foodborne_illness",
    "https://en.wikipedia.org/wiki/Gastroesophageal_reflux_disease",
    "https://en.wikipedia.org/wiki/Irritable_bowel_syndrome",
    "https://en.wikipedia.org/wiki/Diarrhea",
    "https://en.wikipedia.org/wiki/Migraine",
    "https://en.wikipedia.org/wiki/Osteoarthritis",
    "https://en.wikipedia.org/wiki/Back_pain",
    "https://en.wikipedia.org/wiki/Hypercholesterolemia",
    "https://en.wikipedia.org/wiki/Anxiety_disorder",
    "https://en.wikipedia.org/wiki/Insomnia"
]

def main():
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index(index_name)
    
    print("--- 1. DELETING MAYO CLINIC URLS ---")
    try:
        index.delete(filter={"source": {"$in": old_mayo_urls}})
        print("✅ Mayo Clinic data deleted!")
    except Exception as e:
        print(f"Warning: {e}")
        
    print("\n--- 2. SCRAPING NEW URLS ---")
    documents = load_website_data(new_urls)
    if not documents: return
        
    print("Filtering and Chunking documents using helper.py...")
    documents = filterDocuments(documents)
    chunked_docs = ChunkingDocuments(documents)
    total_chunks = len(chunked_docs)
    
    print("\n--- 3. UPLOADING NEW URLS TO PINECONE ---")
    vector_db = PineconeVectorStore(index_name=index_name, embedding=embeddings)
    batch_size = 50
    for i in range(0, total_chunks, batch_size):
        batch = chunked_docs[i:i + batch_size]
        print(f" -> Uploading chunks {i} to {i + len(batch)}...")
        vector_db.add_documents(batch)
        if i + batch_size < total_chunks:
            time.sleep(60)

    print("\n✅ Clean and Update Complete!")

if __name__ == "__main__":
    main()
