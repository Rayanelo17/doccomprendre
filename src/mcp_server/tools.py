"""
Serveur MCP — Outils exposés au graphe LangGraph.

Outils :
  - get_procedure_info    → cherche une procédure dans le corpus
  - get_user_deadlines    → liste les échéances de la session
  - create_reminder       → crée un rappel (après validation humaine)
"""

import hashlib
import json
from datetime import date, datetime
from typing import Optional
from functools import lru_cache

from src.rag.chain import retrieve


# ─────────────────────────────────────────
# Stockage en mémoire (session uniquement)
# Effacé à la fin de la session → contrainte "Ne pas conserver"
# ─────────────────────────────────────────

_SESSION_DEADLINES: list[dict] = []
_SESSION_REMINDERS: list[dict] = []


def _token_idempotence(action: str, date_limite: str, contenu: str) -> str:
    """
    Génère un jeton unique lié au contenu exact.
    Idempotent : même entrée = même jeton.
    Empêche la création de rappels en double.
    """
    payload = f"{action}|{date_limite}|{contenu}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


# ─────────────────────────────────────────
# Outil 1 : get_procedure_info
# ─────────────────────────────────────────

def get_procedure_info(query: str, k: int = 3) -> dict:
    """
    Recherche des informations de procédure dans le corpus.
    Retourne les passages les plus pertinents.

    Args:
        query: La question ou le terme à chercher
        k: Nombre de résultats (défaut 3)

    Returns:
        dict avec "resultats" (liste de passages sourcés)
    """
    try:
        chunks = retrieve(query, k=k)
        return {
            "outil": "get_procedure_info",
            "query": query,
            "resultats": [
                {
                    "contenu": c["contenu"][:300],
                    "source": c["source"],
                    "url": c["url"],
                    "score": c["score"],
                }
                for c in chunks
            ],
        }
    except Exception as e:
        return {"outil": "get_procedure_info", "erreur": str(e), "resultats": []}


# ─────────────────────────────────────────
# Outil 2 : get_user_deadlines
# ─────────────────────────────────────────

def get_user_deadlines() -> dict:
    """
    Retourne les échéances enregistrées pour la session en cours.
    Les données sont effacées en fin de session.

    Returns:
        dict avec "echeances" (liste triée par date)
    """
    echeances_triees = sorted(
        _SESSION_DEADLINES,
        key=lambda x: x.get("date_limite", "9999-12-31")
    )
    return {
        "outil": "get_user_deadlines",
        "nb_echeances": len(echeances_triees),
        "echeances": echeances_triees,
    }


def ajouter_echeance(action: str, date_limite: str, source_doc: str) -> None:
    """Ajoute une échéance à la session (utilisé en interne par le graphe)."""
    _SESSION_DEADLINES.append({
        "action": action,
        "date_limite": date_limite,
        "source_doc": source_doc,
        "ajoutee_le": datetime.now().isoformat(),
    })


# ─────────────────────────────────────────
# Outil 3 : create_reminder
# ─────────────────────────────────────────

def create_reminder(
    action: str,
    date_limite: str,
    contenu_document: str,
    approuve_par_utilisateur: bool = False,
) -> dict:
    """
    Crée un rappel pour une échéance.

    RÈGLE : Ne crée le rappel QUE si approuve_par_utilisateur=True.
    Le jeton d'idempotence empêche les doublons.

    Args:
        action: L'action à rappeler
        date_limite: La date limite (format YYYY-MM-DD)
        contenu_document: Extrait du document source (pour l'idempotence)
        approuve_par_utilisateur: DOIT être True pour créer le rappel

    Returns:
        dict avec "statut" et "token"
    """
    # Contrainte : validation humaine obligatoire
    if not approuve_par_utilisateur:
        return {
            "outil": "create_reminder",
            "statut": "refus",
            "message": (
                "Le rappel ne peut pas être créé sans validation explicite "
                "de l'utilisateur. Présentez d'abord le rappel à l'utilisateur "
                "et attendez sa confirmation."
            ),
            "token": None,
        }

    # Jeton d'idempotence
    token = _token_idempotence(action, date_limite, contenu_document)

    # Vérifier si ce rappel existe déjà
    for rappel in _SESSION_REMINDERS:
        if rappel["token"] == token:
            return {
                "outil": "create_reminder",
                "statut": "deja_existant",
                "message": f"Ce rappel existe déjà (token: {token})",
                "token": token,
            }

    # Créer le rappel
    rappel = {
        "token": token,
        "action": action,
        "date_limite": date_limite,
        "contenu_document": contenu_document[:100],  # tronqué pour la session
        "cree_le": datetime.now().isoformat(),
        "approuve": True,
    }
    _SESSION_REMINDERS.append(rappel)

    # Aussi ajouter aux échéances
    ajouter_echeance(action, date_limite, contenu_document[:50])

    return {
        "outil": "create_reminder",
        "statut": "cree",
        "message": f"Rappel créé pour '{action}' le {date_limite}",
        "token": token,
        "rappel": rappel,
    }


def effacer_session() -> None:
    """
    Efface toutes les données de la session.
    Contrainte "Ne pas conserver" — à appeler en fin de session.
    """
    _SESSION_DEADLINES.clear()
    _SESSION_REMINDERS.clear()


# ─────────────────────────────────────────
# Registry des outils MCP
# ─────────────────────────────────────────

OUTILS_MCP = {
    "get_procedure_info": get_procedure_info,
    "get_user_deadlines": get_user_deadlines,
    "create_reminder":    create_reminder,
}


def appeler_outil(nom: str, **kwargs) -> dict:
    """Point d'entrée unique pour appeler un outil MCP."""
    if nom not in OUTILS_MCP:
        return {"erreur": f"Outil '{nom}' non trouvé. Outils disponibles : {list(OUTILS_MCP)}"}
    return OUTILS_MCP[nom](**kwargs)


# ─────────────────────────────────────────
# Test
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("\n🔧 Test du serveur MCP")
    print("=" * 50)

    # Test 1 : get_procedure_info
    print("\n[1] get_procedure_info('arrêt maladie')...")
    r = get_procedure_info("arrêt maladie indemnités", k=2)
    for res in r["resultats"]:
        print(f"  • {res['source']} (score: {res['score']})")
        print(f"    {res['contenu'][:80]}...")

    # Test 2 : create_reminder sans approbation
    print("\n[2] create_reminder SANS approbation...")
    r = create_reminder("Payer le loyer", "2026-12-05", "loyer 650 euros", approuve_par_utilisateur=False)
    print(f"  Statut : {r['statut']}")
    print(f"  Message : {r['message']}")

    # Test 3 : create_reminder avec approbation
    print("\n[3] create_reminder AVEC approbation...")
    r = create_reminder("Payer le loyer", "2026-12-05", "loyer 650 euros", approuve_par_utilisateur=True)
    print(f"  Statut : {r['statut']}")
    print(f"  Token  : {r['token']}")

    # Test 4 : idempotence (même rappel = même token)
    print("\n[4] Idempotence — même rappel une 2e fois...")
    r2 = create_reminder("Payer le loyer", "2026-12-05", "loyer 650 euros", approuve_par_utilisateur=True)
    print(f"  Statut : {r2['statut']}")

    # Test 5 : get_user_deadlines
    print("\n[5] get_user_deadlines...")
    r = get_user_deadlines()
    print(f"  Échéances : {r['nb_echeances']}")
    for e in r["echeances"]:
        print(f"  • {e['action']} — {e['date_limite']}")
