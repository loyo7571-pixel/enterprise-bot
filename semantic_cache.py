import chromadb
from langchain_community.embeddings import HuggingFaceEmbeddings

# 1. Connect to the existing ChromaDB folder
client = chromadb.PersistentClient(path="dev")

# 2. Create a NEW collection just for the cache
# (This keeps it separate from your PDF documents)
cache_collection = client.get_or_create_collection(name="semantic_cache")

# 3. Load the embedding model
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def get_cached_answer(question: str):
    # Convert the user's question into a vector
    question_vector = embeddings.embed_query(question)
    
    # Search the cache collection
    results = cache_collection.query(
        query_embeddings=[question_vector],
        n_results=1
    )
    
    # If the collection is empty, return None
    if not results["documents"] or not results["documents"][0]:
        return None
        
    distance = results["distances"][0][0]
    
    # ChromaDB distance: 0.0 is identical, 2.0 is opposite.
    # A distance < 0.3 means the questions are very similar.
    if distance < 0.3:
        print(f"✅ Semantic Cache Hit! (Distance: {distance:.2f})")
        return results["metadatas"][0][0]["answer"]
        
    print(f"❌ Cache Miss. Closest match distance: {distance:.2f}")
    return None

def set_cached_answer(question: str, answer: str):
    # We store the question as the document, and the answer in the metadata
    cache_collection.upsert(
        documents=[question],
        metadatas=[{"answer": answer}],
        ids=[str(hash(question))] # Use a hash of the question as the ID
    )