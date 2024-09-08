import os
from pathlib import Path

import chromadb
from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    Document
)
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

from dotenv import load_dotenv

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")

embed_model = OpenAIEmbedding(
    model="text-embedding-3-large",
    api_key=openai_api_key
)

llm = OpenAI(
    model="gpt-4o-mini",
    api_key=openai_api_key
)

def load_docs(ticker: str) -> list[Document]:
    import json
    
    file_path = Path(f"./data/raw/{ticker}/sec.json")
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, 'r') as file:
        data = json.load(file)

    facts_dict = {}
    for key, value in data.items():
        facts_dict[key] = value['facts']
    
    documents = []
    for key, value in facts_dict.items():
        for fact in value:
            doc = Document(
                text=fact,
                metadata={
                    "company": ticker,
                    "ticker": ticker
                    }
            )
            documents.append(doc)
    return documents


def save_index(ticker: str) -> VectorStoreIndex:
    
    db = chromadb.PersistentClient(path="./chroma_db")
    chroma_collection = db.get_or_create_collection(ticker)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    documents = load_docs(ticker)
    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=embed_model
    )

    return index

def load_index(ticker: str) -> VectorStoreIndex:

    db = chromadb.PersistentClient(path="./chroma_db")
    chroma_collection = db.get_or_create_collection(ticker)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    index = VectorStoreIndex.from_vector_store(
        vector_store,
        embed_model=embed_model,
    )
    return index
    
def make_engine(
        ticker: str,
        chat_mode: str = "best",
        verbose: bool = True,
        similarity_top_k: int = 5,
        ):

    index = load_index(ticker)
    query_engine = index.as_query_engine(
        chat_mode=chat_mode,
        llm=llm,
        verbose=verbose,
        similarity_top_k=similarity_top_k,
    )
    
    return query_engine

def make_engines(
        ticker_list: list[str],
        ):

    engines = {}
    for ticker in ticker_list:
        engines[ticker] = make_engine(ticker)
    return engines

def get_indexed_tickers():
    indexed_file = Path("./indexed.txt")
    if indexed_file.exists():
        with open(indexed_file, "r", encoding="utf-8") as f:
            return [line.strip().lower() for line in f if line.strip()]
    return []