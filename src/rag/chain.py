"""
Chaîne RAG complète :
- Recherche dans Chroma
- Génération avec Mistral (Ollama)
- Sortie validée par Pydantic
"""

import json
import re
from pathlib import Path
from typing import Optional

import requests
from langchain_chroma import Chroma
from langchain_community.embeddings import OllamaEmbeddings

from src.schemas.models import Action, Terme, Explication

CHROMA_DIR  = "./chroma_data"
COLLECTION  = "doccomprendre"
OLLAMA_URL  = "http://localhost:11434"
LLM_MODEL   = "mistral"
PROMPT_DIR  = Path("prompts")

# ─────────────────────────────────────────
# 1. Connexion à Chroma
# ─────────────────────────────────────────

def get_vectorstore() -> Chroma:
    embeddings = OllamaEmbeddings(
        model="nomic-embed-text",
        base_url=OLLAMA_URL,
    )
    return Chroma(
        collection_name=COLLECTION,
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR,
    )


# ─────────────────────────────────────────
# 2. Recherche RAG
# ─────────────────────────────────────────

def retrieve(query: str, k: int = 4) -> list[dict]:
    """Recherche les k chunks les plus pertinents."""
    vs = get_vectorstore()
    results = vs.similarity_search_with_score(query, k=k)
    return [
        {
            "contenu": doc.page_content,
            "source":  doc.metadata.get("slug", ""),
            "url":     doc.metadata.get("url", ""),
            "score":   round(float(score), 4),
        }
        for doc, score in results
    ]


# ─────────────────────────────────────────
# 3. Appel LLM (Ollama)
# ─────────────────────────────────────────

def _call_mistral(prompt: str) -> str:
    """Appel direct à l'API Ollama /api/generate."""
    resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": LLM_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 1024,   # limite la longueur de la réponse
                "temperature": 0.1,    # réponses plus déterministes
            },
        },
        timeout=300,  # 5 minutes
    )
    resp.raise_for_status()
    return resp.json().get("response", "").strip()


# ─────────────────────────────────────────
# 4. Parsing JSON → Pydantic
# ─────────────────────────────────────────

def _parse_explication(raw: str, langue: str) -> Explication:
    """
    Extrait le JSON de la réponse LLM et valide avec Pydantic.
    Si le parsing échoue, retourne une explication minimale avec incertitude.
    """
    # Cherche un bloc JSON dans la réponse
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return Explication(
            type_document="inconnu",
            resume_simple=raw[:500] if raw else "Impossible de générer une explication.",
            actions=[],
            termes=[],
            incertitudes=["Le modèle n'a pas retourné un format JSON valide."],
            citations=[],
            langue=langue,
            avertissement="Ce résumé est fourni à titre informatif uniquement.",
        )
    try:
        data = json.loads(match.group())
        # Normaliser les actions
        actions = []
        for a in data.get("actions", []):
            if isinstance(a, dict):
                actions.append(Action(
                    action=a.get("action", ""),
                    date_limite=a.get("date_limite"),
                    note=a.get("note"),
                ))
        # Normaliser les termes
        termes = []
        for t in data.get("termes", []):
            if isinstance(t, dict):
                termes.append(Terme(
                    terme=t.get("terme", ""),
                    explication=t.get("explication", ""),
                    source=t.get("source"),
                ))
        return Explication(
            type_document=data.get("type_document", "document"),
            emetteur=data.get("emetteur"),
            resume_simple=data.get("resume_simple", ""),
            actions=actions,
            termes=termes,
            avertissement=data.get("avertissement"),
            citations=data.get("citations", []),
            incertitudes=data.get("incertitudes", []),
            langue=langue,
        )
    except Exception as e:
        return Explication(
            type_document="inconnu",
            resume_simple=raw[:500],
            actions=[],
            termes=[],
            incertitudes=[f"Erreur de parsing : {e}"],
            citations=[],
            langue=langue,
            avertissement="Ce résumé est fourni à titre informatif uniquement.",
        )


# ─────────────────────────────────────────
# 5. Pipeline principal
# ─────────────────────────────────────────

def expliquer_document(
    document_texte: str,
    langue: str = "fr",
    k_contexte: int = 4,
) -> Explication:
    """
    Explique un document en s'appuyant sur le corpus RAG.
    Retourne un objet Explication validé Pydantic.
    """
    # Recherche dans le corpus
    contexte_chunks = retrieve(document_texte[:500], k=k_contexte)
    contexte_str = "\n\n".join(
        f"[Source: {c['source']}]\n{c['contenu']}"
        for c in contexte_chunks
    )

    lang_label = {"fr": "français", "ar": "arabe", "ary": "darija"}.get(langue, "français")

    prompt = f"""Explique ce document en JSON.

DOCUMENT :
{document_texte[:800]}

CONTEXTE DU CORPUS :
{contexte_str[:600]}

Réponds UNIQUEMENT avec ce JSON :
{{
  "type_document": "type du document",
  "emetteur": "émetteur ou null",
  "resume_simple": "explication en 3 phrases simples en {lang_label}",
  "actions": [{{"action": "action à faire", "date_limite": "YYYY-MM-DD ou null", "note": null}}],
  "termes": [{{"terme": "mot difficile", "explication": "définition simple", "source": null}}],
  "avertissement": "redirection vers professionnel si médical/juridique, sinon null",
  "citations": ["passage exact du document"],
  "incertitudes": ["info manquante"]
}}"""

    raw = _call_mistral(prompt)
    return _parse_explication(raw, langue)


def repondre_question(
    question: str,
    document_texte: str,
    langue: str = "fr",
) -> str:
    """
    Répond à une question sur un document spécifique.
    Ne répond qu'à partir du document fourni.
    """
    lang_label = {"fr": "français", "ar": "arabe", "ary": "darija"}.get(langue, "français")

    prompt = f"""Tu es un assistant de compréhension de documents.

DOCUMENT :
{document_texte[:2000]}

RÈGLES :
1. Réponds UNIQUEMENT à partir du document ci-dessus.
2. Si la réponse n'est pas dans le document, dis : "Cette information ne figure pas dans le document fourni."
3. Ne donne AUCUN conseil médical ou juridique.
4. Réponds en {lang_label} avec des phrases courtes.

QUESTION : {question}

RÉPONSE :"""

    return _call_mistral(prompt)


# ─────────────────────────────────────────
# 6. Test rapide
# ─────────────────────────────────────────

if __name__ == "__main__":
    doc_test = """
    Madame, Monsieur,
    Suite à votre déclaration de revenus, nous vous informons que le montant de votre impôt
    sur le revenu pour l'année 2024 s'élève à 1 450 euros.
    Vous devez régler cette somme avant le 15 septembre 2025.
    En cas de retard, une majoration de 10% sera appliquée.
    Pour tout renseignement, contactez votre centre des finances publiques.
    """

    print("\n🧪 Test de la chaîne RAG")
    print("=" * 50)
    print("Document :", doc_test.strip()[:100], "...")
    print("\nGénération de l'explication...")

    explication = expliquer_document(doc_test, langue="fr")

    print(f"\n📄 Type        : {explication.type_document}")
    print(f"📝 Résumé      : {explication.resume_simple}")
    print(f"✅ Actions     : {len(explication.actions)}")
    for a in explication.actions:
        print(f"   • {a.action} — {a.date_limite}")
    print(f"📚 Termes      : {len(explication.termes)}")
    for t in explication.termes:
        print(f"   • {t.terme} : {t.explication[:60]}...")
    print(f"⚠️  Avertissement : {explication.avertissement}")
    print(f"❓ Incertitudes : {explication.incertitudes}")
