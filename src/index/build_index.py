"""
Indexation du corpus dans Chroma.
- Lit les JSON de data/corpus/
- Découpe en chunks
- Génère les embeddings avec nomic-embed-text (Ollama)
- Stocke dans Chroma (fichier local)
"""

import json
from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import OllamaEmbeddings

CORPUS_DIR = Path("data/corpus")
CHROMA_DIR = "./chroma_data"
COLLECTION  = "doccomprendre"

# ─────────────────────────────────────────
# 1. Chargement des JSON
# ─────────────────────────────────────────

def load_corpus(corpus_dir: Path) -> List[Document]:
    docs = []
    for path in sorted(corpus_dir.glob("*.json")):
        if path.name == "index.json":
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        contenu = data.get("contenu", "").strip()
        if not contenu:
            print(f"  ⚠️  {path.name} — contenu vide, ignoré")
            continue

        doc = Document(
            page_content=contenu,
            metadata={
                "id":         data.get("id", path.stem),
                "slug":       data.get("slug", path.stem),
                "url":        data.get("url", ""),
                "titre":      data.get("titre", ""),
                "type":       data.get("type", "admin"),
                "langue":     data.get("langue", "fr"),
                "source":     path.name,
                "nb_chars":   data.get("nb_chars", len(contenu)),
            }
        )
        docs.append(doc)
    return docs

# ─────────────────────────────────────────
# 2. Chunking
# ─────────────────────────────────────────

def split_documents(docs: List[Document]) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        length_function=len,
        separators=["\n\n", "\n", ".", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    # Ajouter le numéro de chunk dans les métadonnées
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = i
    return chunks

# ─────────────────────────────────────────
# 3. Embeddings + Chroma
# ─────────────────────────────────────────

def build_index(chunks: List[Document]) -> Chroma:
    print(f"  Génération des embeddings ({len(chunks)} chunks)...")
    print("  (Ollama doit être lancé : ollama serve)")

    embeddings = OllamaEmbeddings(
        model="nomic-embed-text",
        base_url="http://localhost:11434",
    )

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION,
        persist_directory=CHROMA_DIR,
    )
    return vectorstore

# ─────────────────────────────────────────
# 4. Pipeline principal
# ─────────────────────────────────────────

def main():
    print("\n📚 Indexation du corpus")
    print("=" * 50)

    # Chargement
    print("\n[1/3] Chargement des documents...")
    docs = load_corpus(CORPUS_DIR)
    print(f"  ✅ {len(docs)} documents chargés")
    for d in docs:
        print(f"     • {d.metadata['slug']:35s} {d.metadata['nb_chars']:>7} chars  [{d.metadata['type']}]")

    # Chunking
    print(f"\n[2/3] Découpage en chunks (500 chars, overlap 50)...")
    chunks = split_documents(docs)
    print(f"  ✅ {len(chunks)} chunks générés")

    # Indexation
    print(f"\n[3/3] Indexation dans Chroma ({CHROMA_DIR})...")
    vectorstore = build_index(chunks)
    print(f"  ✅ Index créé : {CHROMA_DIR}")

    # Test rapide
    print("\n🔍 Test de recherche...")
    results = vectorstore.similarity_search("arrêt maladie indemnités", k=3)
    print(f"  Requête : 'arrêt maladie indemnités'")
    for i, r in enumerate(results, 1):
        print(f"  [{i}] {r.metadata['slug']} — {r.page_content[:100].strip()}...")

    print("\n✅ Indexation terminée.")


if __name__ == "__main__":
    main()
