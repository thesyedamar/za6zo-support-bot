# Dockerfile — container build instructions
# Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first (for Docker layer caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project
COPY . .

# Expose port
EXPOSE 8000

# Run the FastAPI app
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

**`requirements.txt`** — replace your current one with this exact list:
```
fastapi
uvicorn[standard]
langchain
langchain-core
langchain-community
langchain-google-genai
langchain-chroma
langchain-text-splitters
chromadb
google-generativeai
python-dotenv
twilio
pydantic
```

---

**`.railwayignore`** — tells Railway what NOT to upload:
```
venv/
__pycache__/
*.pyc
.env
chroma_db/
.git/
