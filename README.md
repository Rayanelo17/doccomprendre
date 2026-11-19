# DocComprendre - Assistant de compréhension de documents

Application d'IA pour expliquer les documents administratifs et médicaux en français, arabe ou darija.

## Prérequis

- Python 3.11+
- [Ollama](https://ollama.com) installé et lancé
- Tesseract OCR

## Installation

```bash
# Cloner le dépôt
git clone <repo-url>
cd projet-ia

# Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Installer les dépendances
pip install -e .
```

## Configuration

```bash
cp .env.example .env
# Éditer .env avec vos paramètres
```

## Lancement

```bash
# Démarrer Ollama
ollama serve
# ou dans un autre terminal: ollama run mistral

# Lancer l'application
streamlit run src/ui/main.py
```

## Architecture

- **UI** : Streamlit
- **API** : FastAPI
- **LLM** : Mistral (Ollama)
- **Embeddings** : Nomic Embed Text
- **Vecteurs** : Chroma
- **OCR** : Tesseract

## Évaluation

```bash
python eval/run_eval.py
```

## License

MIT