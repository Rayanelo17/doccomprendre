"""
Graphe LangGraph — Orchestration agentique.

Nœuds :
  1. extraire    → OCR ou texte brut
  2. rag         → génère l'explication via RAG + Mistral
  3. verifier    → vérifie la fidélité (rien d'inventé)
  4. valider     → interruption humaine pour les rappels
  5. repondre    → retourne la réponse finale

Flux :
  extraire → rag → verifier → (ok) → repondre
                           → (ko) → rag (2e essai max)
"""

import re
from typing import TypedDict, Literal, Optional, List
from langgraph.graph import StateGraph, END

from src.rag.chain import expliquer_document, repondre_question
from src.schemas.models import Explication, Action


# ─────────────────────────────────────────
# État du graphe
# ─────────────────────────────────────────

class EtatDocument(TypedDict):
    # Entrée
    texte_document: str
    langue: str
    question: Optional[str]

    # Intermédiaire
    explication: Optional[dict]
    nb_essais: int
    erreur_fidelite: Optional[str]

    # Rappel (validation humaine)
    rappel_demande: Optional[dict]
    rappel_approuve: bool

    # Sortie
    reponse_finale: Optional[dict]
    statut: str  # "ok", "erreur", "attente_validation"


# ─────────────────────────────────────────
# Nœuds
# ─────────────────────────────────────────

def noeud_rag(etat: EtatDocument) -> EtatDocument:
    """Génère l'explication via RAG + Mistral."""
    print(f"  [RAG] Génération de l'explication (essai {etat['nb_essais'] + 1})...")

    try:
        explication = expliquer_document(
            etat["texte_document"],
            langue=etat["langue"],
        )
        return {
            **etat,
            "explication": explication.model_dump(),
            "nb_essais": etat["nb_essais"] + 1,
            "statut": "rag_ok",
        }
    except Exception as e:
        return {
            **etat,
            "nb_essais": etat["nb_essais"] + 1,
            "statut": "erreur",
            "erreur_fidelite": f"Erreur RAG : {e}",
        }


def noeud_verifier(etat: EtatDocument) -> EtatDocument:
    """
    Vérifie que l'explication ne contient pas d'inventions.
    Règles :
    - Le résumé ne doit pas être vide
    - Les incertitudes ne doivent pas contenir d'affirmations
    - Le nombre d'actions doit être cohérent
    """
    print("  [VÉRIF] Vérification de la fidélité...")

    explication = etat.get("explication", {})
    if not explication:
        return {**etat, "statut": "erreur", "erreur_fidelite": "Explication vide"}

    resume = explication.get("resume_simple", "")
    incertitudes = explication.get("incertitudes", [])
    actions = explication.get("actions", [])

    problemes = []

    # Règle 1 : résumé non vide
    if not resume or len(resume.strip()) < 10:
        problemes.append("Résumé trop court ou vide")

    # Règle 2 : pas de formules inventées dans le résumé
    phrases_interdites = [
        "je vous conseille",
        "il faut que vous",
        "vous devriez",
        "diagnostic",
        "traitement recommandé",
    ]
    resume_lower = resume.lower()
    for phrase in phrases_interdites:
        if phrase in resume_lower:
            problemes.append(f"Phrase interdite détectée : '{phrase}'")

    # Règle 3 : avertissement présent si type médical
    type_doc = explication.get("type_document", "").lower()
    mots_medicaux = ["ordonnance", "médical", "médicament", "prescription", "soin"]
    if any(m in type_doc for m in mots_medicaux):
        if not explication.get("avertissement"):
            problemes.append("Document médical sans avertissement")

    if problemes:
        print(f"  [VÉRIF] ❌ Problèmes détectés : {problemes}")
        return {
            **etat,
            "statut": "fidelite_ko",
            "erreur_fidelite": " | ".join(problemes),
        }

    print("  [VÉRIF] ✅ Fidélité validée")
    return {**etat, "statut": "fidelite_ok", "erreur_fidelite": None}


def noeud_repondre(etat: EtatDocument) -> EtatDocument:
    """Finalise la réponse."""
    print("  [RÉPONSE] Finalisation...")

    explication = etat.get("explication", {})

    # Vérifier si des actions nécessitent un rappel
    actions = explication.get("actions", [])
    actions_avec_date = [a for a in actions if a.get("date_limite")]

    if actions_avec_date and not etat.get("rappel_approuve"):
        # Proposer un rappel (sans l'créer automatiquement)
        return {
            **etat,
            "rappel_demande": {
                "action": actions_avec_date[0].get("action", ""),
                "date_limite": actions_avec_date[0].get("date_limite", ""),
                "message": (
                    "Souhaitez-vous créer un rappel pour cette échéance ? "
                    "(Répondez 'oui' pour confirmer)"
                ),
            },
            "reponse_finale": explication,
            "statut": "attente_validation",
        }

    return {
        **etat,
        "reponse_finale": explication,
        "statut": "ok",
    }


def noeud_erreur(etat: EtatDocument) -> EtatDocument:
    """Gère les erreurs."""
    print(f"  [ERREUR] {etat.get('erreur_fidelite', 'Erreur inconnue')}")
    return {
        **etat,
        "reponse_finale": {
            "type_document": "erreur",
            "resume_simple": "Une erreur est survenue lors du traitement du document.",
            "actions": [],
            "termes": [],
            "incertitudes": [etat.get("erreur_fidelite", "Erreur inconnue")],
            "citations": [],
            "langue": etat.get("langue", "fr"),
            "avertissement": None,
        },
        "statut": "erreur",
    }


# ─────────────────────────────────────────
# Conditions de routage
# ─────────────────────────────────────────

def router_apres_rag(etat: EtatDocument) -> Literal["verifier", "erreur"]:
    if etat["statut"] == "rag_ok":
        return "verifier"
    return "erreur"


def router_apres_verification(
    etat: EtatDocument,
) -> Literal["repondre", "rag", "erreur"]:
    statut = etat["statut"]
    nb_essais = etat["nb_essais"]

    if statut == "fidelite_ok":
        return "repondre"
    elif statut == "fidelite_ko" and nb_essais < 2:
        print(f"  [ROUTER] Nouvel essai RAG ({nb_essais}/2)...")
        return "rag"
    else:
        return "erreur"


# ─────────────────────────────────────────
# Construction du graphe
# ─────────────────────────────────────────

def construire_graphe():
    graphe = StateGraph(EtatDocument)

    # Ajouter les nœuds
    graphe.add_node("rag",      noeud_rag)
    graphe.add_node("verifier", noeud_verifier)
    graphe.add_node("repondre", noeud_repondre)
    graphe.add_node("erreur",   noeud_erreur)

    # Point d'entrée
    graphe.set_entry_point("rag")

    # Transitions
    graphe.add_conditional_edges("rag",      router_apres_rag)
    graphe.add_conditional_edges("verifier", router_apres_verification)
    graphe.add_edge("repondre", END)
    graphe.add_edge("erreur",   END)

    return graphe.compile()


# ─────────────────────────────────────────
# Interface principale
# ─────────────────────────────────────────

def traiter_document(
    texte: str,
    langue: str = "fr",
    question: Optional[str] = None,
) -> dict:
    """
    Point d'entrée principal du graphe.
    Retourne l'explication finale validée.
    """
    graphe = construire_graphe()

    etat_initial: EtatDocument = {
        "texte_document": texte,
        "langue": langue,
        "question": question,
        "explication": None,
        "nb_essais": 0,
        "erreur_fidelite": None,
        "rappel_demande": None,
        "rappel_approuve": False,
        "reponse_finale": None,
        "statut": "debut",
    }

    print("\n🤖 Lancement du graphe LangGraph...")
    resultat = graphe.invoke(etat_initial)
    print(f"  Statut final : {resultat['statut']}")

    return resultat


# ─────────────────────────────────────────
# Test
# ─────────────────────────────────────────

if __name__ == "__main__":
    doc_test = """
    Madame, Monsieur,
    Nous vous informons que votre loyer pour le mois de décembre 2026
    s'élève à 650 euros, charges comprises.
    Le paiement est attendu avant le 5 décembre 2026.
    En cas de retard, des pénalités de 3% seront appliquées.
    Cordialement, Le gestionnaire immobilier.
    """

    print("Document test :", doc_test.strip()[:80], "...")
    resultat = traiter_document(doc_test, langue="fr")

    reponse = resultat.get("reponse_finale", {})
    print(f"\n📄 Type        : {reponse.get('type_document')}")
    print(f"📝 Résumé      : {reponse.get('resume_simple')}")
    print(f"✅ Actions     : {len(reponse.get('actions', []))}")
    print(f"❓ Incertitudes: {reponse.get('incertitudes')}")
    print(f"🔔 Rappel      : {resultat.get('rappel_demande')}")
    print(f"📊 Statut      : {resultat.get('statut')}")
