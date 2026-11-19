"""
run_eval.py — Harnais d'évaluation principal.
Lance toutes les métriques et logue dans MLflow.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
import subprocess

# Import du pipeline RAG
sys.path.insert(0, os.path.abspath("."))
from src.rag.chain import expliquer_document

# =====================
# Métriques
# =====================


def fidelite(explication: dict, document_annote: dict) -> dict:
    """
    Fidélité : part des informations clés retrouvées dans l'explication.
    Retourne dict avec score et informations inventées.
    """
    infos_cles = document_annote.get("informations_cles", [])
    resume = explication.get("resume_simple", "")
    actions_str = " ".join(a.get("action", "") for a in explication.get("actions", []))
    termes_str = " ".join(t.get("terme", "") + " " + t.get("explication", "") for t in explication.get("termes", []))
    full_text = (resume + " " + actions_str + " " + termes_str).lower()

    retrouvees = 0
    manquees = []
    for info in infos_cles:
        if not info.get("obligatoire", True):
            continue
        valeur = info.get("valeur", "").lower()
        if valeur and valeur in full_text:
            retrouvees += 1
        else:
            manquees.append(info.get("valeur", ""))

    total_obligatoires = sum(1 for i in infos_cles if i.get("obligatoire", True))
    score = retrouvees / total_obligatoires if total_obligatoires > 0 else 0.0

    # Informations inventées : celles dans l'explication mais pas dans le document original
    inventees = 0  # TODO: NLP plus avancé — pour l'instant c'est un placeholder

    return {
        "score_fidelite": round(score, 3),
        "informations_retrouvees": retrouvees,
        "informations_manquees": manquees,
        "informations_inventees": inventees,
    }


def refus(explication: dict, document_annote: dict) -> dict:
    """
    Refus : taux de blocage sur demandes de conseil médical/juridique.
    Pour l'instant, vérifie la présence de l'avertissement.
    """
    avertissement = explication.get("avertissement", "")
    has_warning = avertissement is not None and len(avertissement) > 0
    return {
        "has_avertissement": has_warning,
        "avertissement": avertissement,
    }


def lisibilite(explication: dict) -> dict:
    """
    Lisibilité : longueur moyenne des phrases, mots simples.
    Version basique pour la semaine 1.
    """
    resume = explication.get("resume_simple", "")
    phrases = [p.strip() for p in resume.split(".") if p.strip()]
    nb_phrases = len(phrases)
    nb_mots = len(resume.split())
    longueur_moyenne = nb_mots / nb_phrases if nb_phrases > 0 else 0

    return {
        "nb_phrases": nb_phrases,
        "nb_mots": nb_mots,
        "longueur_moyenne_phrase": round(longueur_moyenne, 1),
    }


# =====================
# Runner
# =====================


def run_evaluation(dataset_path: str = "eval/datasets/schema_annotation.json"):
    """
    Lance l'évaluation sur le jeu annoté.
    """
    print(f"\n📊 Lancement de l'évaluation — {datetime.now().isoformat()}")
    print(f"Dataset: {dataset_path}\n")

    with open(dataset_path) as f:
        data = json.load(f)

    exemples = data.get("examples", [])
    print(f"Nombre de documents: {len(exemples)}")

    resultats = []
    for exemple in exemples:
        doc_id = exemple.get("id")
        print(f"\n  Évaluation de {doc_id}...")

        # Appel du vrai pipeline RAG
        contenu_doc = exemple.get("contenu_original", "")
        langue_attendue = exemple.get("langue_attendue", "fr")

        try:
            explication_obj = expliquer_document(contenu_doc, langue=langue_attendue)
            explication_dict = explication_obj.model_dump()
        except Exception as e:
            print(f"    ❌ Erreur pipeline : {e}")
            explication_dict = {
                "type_document": "erreur",
                "emetteur": None,
                "resume_simple": f"Erreur : {e}",
                "actions": [],
                "termes": [],
                "avertissement": None,
                "citations": [],
                "incertitudes": [f"Erreur technique : {e}"],
                "langue": langue_attendue,
            }

        score_fid = fidelite(explication_dict, exemple)
        score_lis = lisibilite(explication_dict)
        score_ref = refus(explication_dict, exemple)

        resultats.append({
            "doc_id": doc_id,
            "fidelite": score_fid,
            "lisibilite": score_lis,
            "refus": score_ref,
        })

        print(f"    Fidélité     : {score_fid['score_fidelite']:.1%}")
        print(f"    Long. phrase : {score_lis['longueur_moyenne_phrase']:.1f} mots/phrase")
        print(f"    Avertissement: {'✅' if score_ref['has_avertissement'] else '❌'}")

    # Résumé global
    moy_fidelite = sum(r["fidelite"]["score_fidelite"] for r in resultats) / max(len(resultats), 1)
    moy_longueur = sum(r["lisibilite"]["longueur_moyenne_phrase"] for r in resultats) / max(len(resultats), 1)
    pct_avertissement = sum(1 for r in resultats if r["refus"]["has_avertissement"]) / max(len(resultats), 1)

    print(f"\n{'='*40}")
    print(f"RÉSULTATS GLOBAUX")
    print(f"{'='*40}")
    print(f"  Fidélité moyenne       : {moy_fidelite:.1%}")
    print(f"  Longueur phrase moyenne: {moy_longueur:.1f} mots")
    print(f"  Taux avertissement     : {pct_avertissement:.1%}")

    # Sauvegarde des résultats
    output_path = f"eval/resultats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(resultats, f, ensure_ascii=False, indent=2)
    print(f"\nRésultats sauvegardés: {output_path}")

    return resultats


if __name__ == "__main__":
    dataset = sys.argv[1] if len(sys.argv) > 1 else "eval/datasets/schema_annotation.json"
    run_evaluation(dataset)