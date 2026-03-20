import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.tools import tool

DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/unified_vector_db")

_embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")

if os.path.isfile(os.path.join(DB_PATH, "index.faiss")):
    vectorstore = FAISS.load_local(DB_PATH, _embeddings, allow_dangerous_deserialization=True)
else:
    os.makedirs(DB_PATH, exist_ok=True)
    vectorstore = FAISS.from_texts(["init"], _embeddings)
    vectorstore.save_local(DB_PATH)
    print(f"⚠️  No FAISS index found — created empty index at {DB_PATH}")
    print("    Run scripts/load_vector_dbs.py to populate.")

@tool
def similarity_search(query: str, agent_name: str, k: int = 2) -> list:
    """Search the Knowledge Base for technical details, MITRE ATT&CK tactics, or SRE/Fintech patterns."""
    docs = vectorstore.similarity_search(query, k=k, filter={"agent": agent_name})
    return [d.page_content for d in docs]
