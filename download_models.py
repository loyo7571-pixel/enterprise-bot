import os
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions

print("Downloading SentenceTransformer model...")
# This downloads the PyTorch model used by LangChain
SentenceTransformer('all-MiniLM-L6-v2')

print("Downloading ChromaDB ONNX model...")
# This downloads the 80MB ONNX model that ChromaDB uses internally
default_ef = embedding_functions.DefaultEmbeddingFunction()
default_ef(["test"]) # Trigger the download

print("All models downloaded successfully!")