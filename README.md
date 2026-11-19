# DocComprendre 📄

> Assistant de compréhension de documents administratifs et médicaux en français, arabe et darija.

## Démarrage rapide (moins de 10 minutes)

### Prérequis
- [Ollama](https://ollama.com) installé et lancé
- Python 3.11+
- Tesseract OCR

### Installation

```bash
git clone https://github.com/Rayanelo17/doccomprendre.git
cd doccomprendre

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

pip install fastapi uvicorn python-multipart streamlit langgraph \
    langchain-core langchain-community langchain-chroma \
    langchain-text-splitters langchain-ollama chromadb \
    pymupdf pillow pydantic requests beautifulsoup4 pytesseract
```

### Configuration

```bash
cp .env.example .env
```

### Lancement

```bash
# Terminal 1 — API
python -m src.api.main

# Terminal 2 — Interface
streamlit run src/ui/main.py
```

Ouvrir : http://localhost:8501

---

## Architecture

```
Utilisateur
    │
    ▼
Streamlit (UI) ──► FastAPI (API)
                       │
                   LangGraph
                  ┌────┴────┐
                 RAG     Vérif.
                  │         │
              Chroma    Contraintes
              Mistral
                  │
              MCP Server
         (procédures, rappels)
```

### Pile technique

| Couche | Outil |
|--------|-------|
| LLM | Mistral (Ollama) |
| Embeddings | nomic-embed-text (Ollama) |
| Base vectorielle | Chroma |
| OCR | Tesseract (fra + ara) |
| Orchestration | LangGraph |
| API | FastAPI |
| Interface | Streamlit |

---

## Les 4 contraintes non négociables

| Contrainte | Implémentation | Test |
|------------|----------------|------|
| Ne rien inventer | Champ `incertitudes` obligatoire | `test_contraintes.py` |
| Ne pas conseiller | Détection phrases interdites | `test_securite.py` |
| Ne pas agir seul | Approbation humaine + idempotence | `test_agent.py` |
| Ne pas conserver | `effacer_session()` en fin de session | `test_securite.py` |

---

## Tests

```bash
python -m pytest tests/ -v
# 36/36 tests passés
```

### Résultats

| Suite | Tests | Résultat |
|-------|-------|----------|
| Contraintes | 9 | ✅ |
| OCR | 6 | ✅ |
| Agent/MCP | 12 | ✅ |
| Sécurité | 9 | ✅ |

---

## Évaluation (scores de base — semaine 1)

| Métrique | Score |
|----------|-------|
| Fidélité | 50% |
| Longueur phrase | 17.2 mots |
| Taux avertissement | 100% |

```bash
python eval/run_eval.py
```

---

## Structure du projet

```
.
├── src/
│   ├── api/          # FastAPI
│   ├── ui/           # Streamlit
│   ├── agent/        # LangGraph
│   ├── mcp_server/   # Outils MCP
│   ├── rag/          # RAG + Mistral
│   ├── index/        # Chroma
│   ├── ingestion/    # Scraping + chunking
│   ├── vision/       # OCR Tesseract
│   └── schemas/      # Pydantic
├── eval/             # Métriques
├── tests/            # 36 tests
├── prompts/          # Prompts versionnés
├── data/corpus/      # 30 documents
└── docker-compose.yml
```

---

## Docker

```bash
docker compose up
```

Services : Ollama (11434) · Chroma (8001) · API (8080) · UI (8501)
