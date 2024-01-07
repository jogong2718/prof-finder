"""CREATE_VECTORSTORE.PY
This script creates a Faiss vectorstore from the faculty bios.
Dependencies: `dotenv`, 'faiss-cpu', `langchain`, `tqdm`
"""

# Library imports
import os
import time
import json

from tqdm import tqdm
from dotenv import load_dotenv

from langchain.vectorstores.faiss import FAISS
from langchain.docstore.document import Document
from langchain.embeddings import HuggingFaceInferenceAPIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter


# Load API key
load_dotenv(".env")
KEY = os.environ["HUGGINGFACEHUB_API_TOKEN"]

def get_data(path: str) -> list:
    """ Returns list of processed LangChain Documents """
    # Load documents
    print("Loading documents...")
    bios = json.load(open(path, "r"))
    documents = []
    none_count = 0

    for b in bios: 
        if b["bio"] is not None:
            documents.append(Document(page_content=b["bio"], metadata={
                "name": b["name"],
                "position": b["position"],
                "email": b["email"],
                "expertise": b["expertise"],
                "profile": b["profile"],
            }))
        else:
            none_count += 1
    
    print(f"Loaded {len(documents)} documents. {none_count} documents skipped since bio was None")

    print(f"Splitting {len(documents)} documents...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    fragments = splitter.split_documents(documents)

    return fragments

def get_vectorstore(fragments: list, model: HuggingFaceInferenceAPIEmbeddings, 
                    save_path: str) -> FAISS:
    """ Embeds documents and returns vectorstore """
    
    # Create vectorstore (400 docs at a time, else HuggingFace API blocks)
    print(f"Creating vectorstore with {len(fragments)} documents...")
    dbs = []
    for i in tqdm(range(0, len(fragments), 400)):
        db = FAISS.from_documents(fragments[i : i+400], model)
        db.save_local(f"{save_path}_{i}")
        dbs.append(db)
        time.sleep(5)

    # Merge partial vectorstores and save final copy
    for db in tqdm(dbs[1:]):
        dbs[0].merge_from(db)
    db.save_local(f"{save_path}_merged")

def main():
    # Load embeddings model
    model = HuggingFaceInferenceAPIEmbeddings(
        api_key=KEY, model_name="sentence-transformers/all-MiniLM-l6-v2"
    )

    # Get vectorstore
    fragments = get_data("data_new/json/bios.json")
    get_vectorstore(fragments, model, "data_new/faiss/bios_faiss")

if __name__ == "__main__":
    main()