from dotenv import load_dotenv
import warnings
import os
import time

warnings.filterwarnings("ignore")
load_dotenv()


from langchain_pinecone import PineconeVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pinecone import Pinecone, ServerlessSpec
from helper import load_all_data, filterDocuments, ChunkingDocuments



# --- CONFIGURATION ---
index_name = "rag-based-system-v3"
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")
data_folder = "./data" # You can change this if you want to load from a different folder!
my_urls = [
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



def EmbeddingsForDocument(documents):
    print(f"Uploading {len(documents)} chunks in batches to avoid Google API rate limits...")
    vector_db = PineconeVectorStore(index_name=index_name, embedding=embeddings)
    
    batch_size = 50
    print(f"Total chunks to upload: {len(documents)}")

    i = 0
    while i < len(documents):
        batch = documents[i : i + batch_size]
        print(f" -> Uploading chunks {i} to {i + len(batch)}...")
        
        try:
            # Try to upload the batch
            vector_db.add_documents(batch)
            
            # If successful, advance to the next batch
            i += batch_size 
            
            if i < len(documents):
                print(" -> Success! Waiting 60 seconds for Google API quota to reset...")
                time.sleep(60)
                
        except Exception as e:
            # If Google crashes (like a 429 error), don't crash the script! 
            # Just wait a bit longer and retry the exact same batch.
            print(f" -> [ERROR CAUGHT]: Google rejected the request (likely rate limit).")
            print(" -> Waiting 90 seconds to cool down before retrying this batch...")
            time.sleep(90)

def main():
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    
    # Check if index exists, if not, create it
    if not pc.has_index(index_name):
        print(f"Creating Pinecone index '{index_name}'...")
        pc.create_index(
            name=index_name,
            dimension=3072,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        while not pc.describe_index(index_name).status['ready']:
            time.sleep(1)
        print("Index is ready!")
        
    # Dynamically check how many chunks are already in Pinecone
    index_stats = pc.Index(index_name).describe_index_stats()
    uploaded_count = index_stats.total_vector_count
    
    print("Loading All Data from data folder And Urls...")
    documents = load_all_data(data_folder, my_urls)
    if documents:
        documents = filterDocuments(documents)
        chunked_docs = ChunkingDocuments(documents)
        total_chunks = len(chunked_docs)
        
        if uploaded_count < total_chunks:
            print(f"\nPinecone currently has {uploaded_count} out of {total_chunks} chunks.")
            print("Resuming upload from where we left off...")
            
            remaining_docs = chunked_docs[uploaded_count:]
            docs_to_upload_today = remaining_docs[:999]
            
            print(f"Uploading {len(docs_to_upload_today)} chunks for today's quota...")
            EmbeddingsForDocument(docs_to_upload_today)
            print("Today's batch is successfully uploaded!")
        else:
            print(f"\nAwesome! All {total_chunks} chunks are already uploaded to Pinecone!")
    else:
        print("No documents loaded.")

if __name__ == "__main__":
    main()
