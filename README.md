# Enterprise AI SaaS Platform (RAG + LLMOps)

A production-grade, fully containerized AI RAG (Retrieval-Augmented Generation) application.
Users can upload PDFs/text files, ask questions, and get answers backed by a fast, semantically cached LLM backend.

## 🏗️ Architecture & Tech Stack

*   **Backend**: FastAPI, Uvicorn
*   **AI/LLM**: LangChain, Groq (LLM API), HuggingFace (Embeddings)
*   **Databases**: PostgreSQL (User Data & Chat History), ChromaDB (Vector Storage & Semantic Cache)
*   **DevOps**: Docker, Docker Compose, Kubernetes (Minikube), GitHub Actions (CI/CD)
*   **Security**: JWT Authentication (OAuth2), Kubernetes Secrets

### The Flow
1. User authenticates via JWT and uploads a document (`/upload`).
2. The document is chunked, embedded, and stored in ChromaDB.
3. User asks a question (`/ask`).
4. The backend checks a **Semantic Cache** (ChromaDB) to save API costs.
5. If not cached, it retrieves the top 2 chunks and prompts the Groq LLM.
6. The answer is saved to PostgreSQL chat history and returned to the user.

## 🚀 Running Locally (Docker Compose)

1. Clone the repository and create a `.env` file with your Groq API key:
   ```env
   GROQ_API_KEY=your key
