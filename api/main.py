# api/main.py — full updated file

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from bot.rag_chain import ask_zabot
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI(
    title="Za6zoBot — Za6zo Support Bot",
    description="AI-powered support bot for Za6zo",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    reply: str
    session_id: str

API_KEY = os.getenv("ZABOT_API_KEY", "zabot-dev-key-change-in-production")

def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="Missing API key")
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


@app.on_event("startup")
async def startup_event():
    """
    Runs automatically when the server starts.
    If ChromaDB doesn't exist (first deploy or reset), builds it from knowledge base.
    """
    chroma_path = "chroma_db"
    if not os.path.exists(chroma_path) or not os.listdir(chroma_path):
        print("🔄 ChromaDB not found — running ingestion...")
        from bot.ingest import ingest_knowledge_base
        ingest_knowledge_base()
        print("✅ Ingestion complete")
    else:
        print("✅ ChromaDB found — skipping ingestion")

    # Pre-load the RAG chain so first user request is fast
    from bot.rag_chain import _get_components
    _get_components()
    print("✅ ZaBot is ready")

@app.get("/widget", response_class=HTMLResponse)
def serve_widget():
    widget_path = os.path.join(os.path.dirname(__file__), "..", "widget", "chat_widget.html")
    with open(widget_path, "r", encoding="utf-8") as f:
        return f.read()
@app.get("/")
def root():
    return {"status": "ZaBot is live", "app": "Za6zo Support Bot", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "ok", "bot": "ZaBot"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, api_key: str = Depends(verify_api_key)):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    from bot.rag_chain import ask_zabot
    reply = ask_zabot(request.message, session_id=request.session_id)
    return ChatResponse(reply=reply, session_id=request.session_id)