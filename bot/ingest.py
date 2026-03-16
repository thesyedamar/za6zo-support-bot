# ingest.py — load docs → embed → store in ChromaDB
# bot/ingest.py
# Run this script ONCE to load your knowledge base into ChromaDB.
# Command: python bot/ingest.py

import os
from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma

# Step 1: Load environment variables from .env file
load_dotenv()

# Step 2: Define paths
KNOWLEDGE_BASE_DIR = "knowledge_base"   # folder with your .md files
CHROMA_DB_DIR = "chroma_db"             # where ChromaDB will save data

def ingest_knowledge_base():
    print("📂 Loading knowledge base documents...")

    # Step 3: Load all .md files from knowledge_base/ folder
    # DirectoryLoader finds all files, TextLoader reads each one
    loader = DirectoryLoader(
        KNOWLEDGE_BASE_DIR,
        glob="**/*.md",          # match all markdown files
        loader_cls=TextLoader,   # read them as plain text
        loader_kwargs={"encoding": "utf-8"}
    )
    documents = loader.load()
    print(f"✅ Loaded {len(documents)} documents")

    # Step 4: Split documents into smaller chunks
    # Why? Because LLMs have context limits.
    # We split into 500-char chunks with 50-char overlap so no info is lost at edges.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,       # each chunk = max 500 characters
        chunk_overlap=50,     # 50 characters overlap between chunks
        separators=["\n\n", "\n", ".", " "]  # prefer splitting at paragraphs
    )
    chunks = splitter.split_documents(documents)
    print(f"✅ Split into {len(chunks)} chunks")

    # Step 5: Create embeddings using Gemini
    # Embeddings = turning text into numbers so we can do similarity search
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",   # Gemini's free embedding model
        google_api_key=os.getenv("GEMINI_API_KEY")
    )

    # Step 6: Store chunks + their embeddings into ChromaDB
    # ChromaDB is a local vector database — saved in the chroma_db/ folder
    print("🔄 Creating embeddings and storing in ChromaDB...")
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DB_DIR
    )
    vectorstore.persist()  # save to disk so it survives restarts
    print(f"✅ Knowledge base stored in ChromaDB at '{CHROMA_DB_DIR}/'")
    print("🎉 Ingestion complete! You can now run the bot.")

if __name__ == "__main__":
    ingest_knowledge_base()