import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any

# Import your ingestion pipeline function verbatim from ingestion.py
from ingestion import load_and_chunk_documents

def setup_vector_store(chunks: List[str], metadata_list: List[Dict[str, Any]], db_path: str = "./chroma_db"):
    """
    Initializes a persistent local ChromaDB instance, embeds chunks using 
    all-MiniLM-L6-v2, and indexes them with metadata.
    """
    print("\n" + "=" * 80)
    print("INITIALIZING VECTOR STORE (ChromaDB)")
    print("=" * 80)
    
    # 1. Initialize persistent client (saves data to local disk)
    client = chromadb.PersistentClient(path=db_path)
    
    # 2. Define the local embedding function matching planning.md
    # ChromaDB has a built-in wrapper for sentence-transformers so you don't have to manage tokens manually
    embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    
    # 3. Create or reset the collection
    collection_name = "knights_circle_reviews"
    try:
        # If running repeatedly, delete existing to prevent compounding duplicates
        client.delete_collection(name=collection_name)
    except Exception:
        pass
        
    collection = client.create_collection(
        name=collection_name,
        embedding_function=embedding_func,
        metadata={"hnsw:space": "cosine"} # Use cosine similarity for opinion text matching
    )
    
    # 4. Prepare batch inputs for ChromaDB
    # Every chunk needs a unique ID string
    ids = [f"id_{idx}" for idx in range(len(chunks))]
    
    # ChromaDB requires metadata dictionary values to be strings, ints, floats, or bools
    # Our extract_metadata_from_header already satisfies this.
    
    print(f"Embedding and indexing {len(chunks)} chunks into collection '{collection_name}'...")
    collection.add(
        documents=chunks,
        metadatas=metadata_list,
        ids=ids
    )
    print("✓ Successfully indexed vector database.")
    return collection


def retrieve_top_k(collection: any, query: str, k: int = 5) -> Dict[str, Any]:
    """
    Queries ChromaDB for the top-k most semantically similar chunks.
    """
    results = collection.query(
        query_texts=[query],
        n_results=k
    )
    return results


def run_evaluation_tests(collection: any):
    """
    Runs the system against 3 core evaluation queries to audit semantic alignment.
    """
    test_queries = [
        "What maintenance issues are reported in Phase 1 of Knights Circle?",
        "Which phases of Knights Circle are described as having reliable shuttle service?",
        "What should a student know about visitor parking and towing costs at Knights Circle?"
    ]
    
    print("\n" + "=" * 80)
    print("RUNNING RETRIEVAL EVALUATION")
    print("=" * 80)
    
    for idx, query in enumerate(test_queries, 1):
        print(f"\n\n[TEST QUERY {idx}]: \"{query}\"")
        print("-" * 80)
        
        # Pull top 4 chunks (since dataset size total is 14)
        results = retrieve_top_k(collection, query, k=4)
        
        # Chroma lists results as nested arrays because it supports multi-query batching.
        # We index [0] to extract results for our single query.
        documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        distances = results['distances'][0]
        
        for rank, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances), 1):
            # Convert cosine distance to a clear clarity metric
            # Cosine distance ranges from 0 (identical) to 2 (opposite).
            # Lower distance = stronger match.
            print(f"  Rank {rank} | Distance: {dist:.4f} | File: {meta['filename']}")
            print(f"  Phase Context: {meta['phase']} | Date: {meta['date']}")
            
            # Truncate view preview for clean validation readability
            preview = doc.replace('\n', ' ').strip()
            print(f"  Text: {preview[:140]}...")
            print("-" * 40)


if __name__ == "__main__":
    # Pull raw data objects through Milestone 3 script
    try:
        chunks, metadata_list, _ = load_and_chunk_documents("data")
        
        # Build db and execute validation tests
        collection = setup_vector_store(chunks, metadata_list)
        run_evaluation_tests(collection)
        
    except Exception as e:
        print(f"\n❌ Pipeline execution failed: {e}")
        print("Ensure 'ingestion.py' is in the same directory and the 'data/' folder exists.")