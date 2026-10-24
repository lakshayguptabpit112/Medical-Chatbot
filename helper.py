import os
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader, WebBaseLoader
from langchain_core.documents import Document

from langchain_text_splitters import RecursiveCharacterTextSplitter
def load_text_file(data_folder: str) -> list[Document]:
    try:
        loader = DirectoryLoader(
            data_folder,
            glob="*.pdf",
            loader_cls=PyPDFLoader
            )
        documents = loader.load()
        return documents
    except Exception as e:
        print(f"Error loading PDF files: {e}")
        return []

def load_website_data(urls: list[str]) -> list[Document]:
    try:
        loader = WebBaseLoader(urls)
        return loader.load()
    except Exception as e:
        print(f"Error loading websites: {e}")
        return []

def load_all_data(data_folder: str, urls: list[str]) -> list[Document]:
    print("Loading PDFs...")
    pdf_docs = load_text_file(data_folder)
    
    print("Scraping Websites...")
    web_docs = load_website_data(urls)
    
    return pdf_docs + web_docs


def filterDocuments(docs:list[Document])-> list[Document]:
    minimalDocs:list[Document] = []
    
    for doc in docs:
        page_num = doc.metadata.get("page")
        
        if page_num:
            # It's a PDF! Grab the book name (e.g. "Medical.pdf") and the page number
            raw_path = doc.metadata.get("source", "Unknown Book")
            book_name = os.path.basename(raw_path)
            final_label = f"{book_name} - Page {page_num}"
        else:
            # It's a website! Grab the URL (and optionally the title if WebBaseLoader found one)
            final_label = doc.metadata.get("source", "Unknown Website")
            
        # 🚨 THE MAGIC TRICK: 
        # Don't delete the old metadata! Just add our new label into the existing dictionary!
        doc.metadata["ui_label"] = final_label
            
        minimalDocs.append(
            Document(
                page_content=doc.page_content, 
                metadata=doc.metadata # Pass the entire, enriched dictionary to Pinecone!
            )
        )
        
    return minimalDocs

def ChunkingDocuments(documents):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1800,
        chunk_overlap=240,
    )
    texts_chunk = text_splitter.split_documents(documents)
    return texts_chunk