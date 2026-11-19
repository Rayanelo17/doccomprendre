FROM python:3.11-slim

# Installer Tesseract + langues
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-ara \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installer les dépendances Python
COPY pyproject.toml .
RUN pip install --no-cache-dir \
    fastapi uvicorn python-multipart \
    streamlit \
    langgraph \
    langchain-core langchain-community langchain-chroma langchain-text-splitters \
    langchain-ollama \
    chromadb \
    pymupdf pillow \
    pydantic \
    requests beautifulsoup4 \
    pytesseract

# Copier le code source
COPY src/ ./src/
COPY prompts/ ./prompts/
COPY data/ ./data/

ENV PYTHONPATH=/app
ENV TESSERACT_LANG=fra+ara

EXPOSE 8080 8501
