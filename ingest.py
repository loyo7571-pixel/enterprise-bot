from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# 1. Load your text file
loader = TextLoader("file1.txt")
docs = loader.load()

# 2. Split it
splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=30)
chunks = splitter.split_documents(docs)

# 3. Setup embeddings
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# 4. Save to Chroma (This creates the "dev" folder!)
vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="dev"
)

print(f"Successfully ingested {len(chunks)} chunks into the 'dev' database.")