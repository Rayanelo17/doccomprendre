"""
Pipeline d'ingestion complet :
1. Extraction (vision.ocr)
2. Création de chunks avec chevauchement
3. Génération d'embeddings (Nomic)
4. Stockage dans ChromaDB
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_nomic.embeddings import NomicEmbeddings

from src.schemas import Action, Terme, Explication
from src.vision.ocr import extract_text


class DocumentMetadata:
    """Métadonnées d'un document du corpus."""
    def __init__(
        self,
        source: str,
        title: str,
        doc_type: str,  # "admin" ou "medical"
        lang: str,  # "fr", "ar", "ary"
        page_count: int = 0,
        processed_at: str = ""
    ):
        self.source = source
        self.title = title
        self.doc_type = doc_type
        self.lang = lang
        self.page_count = page_count
        self.processed_at = processed_at or datetime.now().isoformat()

    def to_dict(self):
        return {
            "source": self.source,
            "title": self.title,
            "doc_type": self.doc_type,
            "lang": self.lang,
            "page_count": self.page_count,
            "processed_at": self.processed_at,
        }


def _get_chunks(text: str, lang: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Découpe un texte en chunks avec chevauchement."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        length_function=len,
    )
    chunks = splitter.create_documents([text])
    return [c.page_content for c in chunks]


def ingest_document(
    content: str,
    filename: Optional[str] = None,
    content_type: str = "text",
    source: str = "",
    title: str = "",
    doc_type: str = "admin",
    lang: str = "fr",
    chroma_collection: str = "doccomprendre",
    embeddings: Optional["NomicEmbeddings"] = None,
    **kwargs
) -> DocumentMetadata:
    """
    Ingest un document :
    - Extraction via OCR
    - Chunking
    - Embeddings + stockage Chroma
    """
    # Extraction
    text, detected_lang = extract_text(content, filename, content_type)
    if not text:
        raise ValueError("Texte vide après extraction")

    # Langue détectée != langue spécifiée
    actual_lang = detected_lang if not lang else lang

    # Metadata
    metadata = DocumentMetadata(
        source=source,
        title=title or filename or "unknown",
        doc_type=doc_type,
        lang=actual_lang,
        page_count=1,
    )

    # Chunks
    chunks = _get_chunks(text, actual_lang)
    if not chunks:
        chunks = [text]  # fallback

    # Embeddings
    if embeddings is None:
        embeddings = NomicEmbeddings(
            model="nomic-embed-text",
            api_key=os.getenv("NOMIC_API_KEY", ""),
        )

    # Store in Chroma
    vectorstore = Chroma(
        collection_name=chroma_collection,
        embedding_function=embeddings,
        persist_directory="./chroma_data",
    )
    vectorstore.add_texts(
        texts=chunks,
        metadatas=[metadata.to_dict()] * len(chunks),
    )
    vectorstore.persist()

    return metadata


def ingest_corpus(
    file_paths: List[str],
    doc_type: str = "admin",
    chroma_collection: str = "doccomprendre",
) -> List[DocumentMetadata]:
    """Ingest plusieurs documents d'un coup."""
    metadatas = []
    for path in file_paths:
        _, ext = os.path.splitext(path)
        ext = ext.lower()
        content_type = "pdf" if ext == ".pdf" else "image" if ext in (".png", ".jpg", ".jpeg") else "text"

        metadata = ingest_document(
            content=path,
            filename=path,
            content_type=content_type,
            source=path,
            doc_type=doc_type,
            chroma_collection=chroma_collection,
        )
        metadatas.append(metadata)
    return metadatas


if __name__ == "__main__":
    print("Pipeline d'ingestion initialisé")