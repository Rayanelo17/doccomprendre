"""
Tests automatiques pour l'étape 3 — LangGraph + MCP.
"""

import pytest
from src.mcp_server.tools import (
    create_reminder,
    get_procedure_info,
    get_user_deadlines,
    effacer_session,
    _token_idempotence,
)


# ─────────────────────────────────────────
# Tests MCP
# ─────────────────────────────────────────

class TestCreateReminder:
    """Contrainte : aucun rappel sans validation humaine."""

    def setup_method(self):
        """Effacer la session avant chaque test."""
        effacer_session()

    def test_refus_sans_approbation(self):
        """Le rappel doit être refusé sans approbation."""
        r = create_reminder(
            action="Payer l'impôt",
            date_limite="2026-12-15",
            contenu_document="avis d'imposition 1450 euros",
            approuve_par_utilisateur=False,
        )
        assert r["statut"] == "refus"
        assert r["token"] is None

    def test_creation_avec_approbation(self):
        """Le rappel doit être créé avec approbation."""
        r = create_reminder(
            action="Payer l'impôt",
            date_limite="2026-12-15",
            contenu_document="avis d'imposition 1450 euros",
            approuve_par_utilisateur=True,
        )
        assert r["statut"] == "cree"
        assert r["token"] is not None
        assert len(r["token"]) == 16

    def test_idempotence(self):
        """Deux rappels identiques → même token, pas de doublon."""
        r1 = create_reminder(
            action="Payer l'impôt",
            date_limite="2026-12-15",
            contenu_document="avis d'imposition 1450 euros",
            approuve_par_utilisateur=True,
        )
        r2 = create_reminder(
            action="Payer l'impôt",
            date_limite="2026-12-15",
            contenu_document="avis d'imposition 1450 euros",
            approuve_par_utilisateur=True,
        )
        assert r1["token"] == r2["token"]
        assert r2["statut"] == "deja_existant"

    def test_token_lie_au_contenu(self):
        """Le token change si le contenu change."""
        t1 = _token_idempotence("Payer", "2026-12-15", "document A")
        t2 = _token_idempotence("Payer", "2026-12-15", "document B")
        assert t1 != t2


class TestGetProcedureInfo:
    """Tests de la recherche dans le corpus."""

    def test_retourne_resultats(self):
        """La recherche doit retourner au moins un résultat."""
        r = get_procedure_info("arrêt maladie", k=2)
        assert "resultats" in r
        assert len(r["resultats"]) > 0

    def test_resultats_contiennent_source(self):
        """Chaque résultat doit avoir une source."""
        r = get_procedure_info("loyer", k=2)
        for res in r["resultats"]:
            assert "source" in res
            assert "contenu" in res


class TestGetUserDeadlines:
    """Tests des échéances de session."""

    def setup_method(self):
        effacer_session()

    def test_session_vide_au_debut(self):
        """La session doit être vide après effacement."""
        r = get_user_deadlines()
        assert r["nb_echeances"] == 0
        assert r["echeances"] == []

    def test_echeance_ajoutee_apres_rappel(self):
        """Créer un rappel doit ajouter une échéance."""
        create_reminder(
            action="Payer le loyer",
            date_limite="2026-12-05",
            contenu_document="loyer 650 euros",
            approuve_par_utilisateur=True,
        )
        r = get_user_deadlines()
        assert r["nb_echeances"] == 1
        assert r["echeances"][0]["action"] == "Payer le loyer"


class TestEffacerSession:
    """Contrainte : Ne pas conserver — effacement en fin de session."""

    def test_effacer_vide_les_donnees(self):
        """Après effacement, la session est vide."""
        create_reminder(
            action="Test",
            date_limite="2026-12-01",
            contenu_document="test",
            approuve_par_utilisateur=True,
        )
        effacer_session()
        r = get_user_deadlines()
        assert r["nb_echeances"] == 0


class TestGrapheLangGraph:
    """Tests du graphe LangGraph (sans appel LLM)."""

    def test_etat_initial_structure(self):
        """L'état initial du graphe a tous les champs requis."""
        from src.agent.graph import EtatDocument
        etat: EtatDocument = {
            "texte_document": "test",
            "langue": "fr",
            "question": None,
            "explication": None,
            "nb_essais": 0,
            "erreur_fidelite": None,
            "rappel_demande": None,
            "rappel_approuve": False,
            "reponse_finale": None,
            "statut": "debut",
        }
        assert etat["nb_essais"] == 0
        assert etat["rappel_approuve"] is False

    def test_noeud_verifier_detecte_phrase_interdite(self):
        """Le nœud de vérification doit bloquer les conseils."""
        from src.agent.graph import noeud_verifier, EtatDocument

        etat: EtatDocument = {
            "texte_document": "test",
            "langue": "fr",
            "question": None,
            "explication": {
                "type_document": "lettre",
                "resume_simple": "je vous conseille de consulter un avocat immédiatement.",
                "actions": [],
                "termes": [],
                "avertissement": None,
                "citations": [],
                "incertitudes": [],
                "langue": "fr",
            },
            "nb_essais": 1,
            "erreur_fidelite": None,
            "rappel_demande": None,
            "rappel_approuve": False,
            "reponse_finale": None,
            "statut": "rag_ok",
        }

        resultat = noeud_verifier(etat)
        assert resultat["statut"] == "fidelite_ko"
        assert resultat["erreur_fidelite"] is not None

    def test_noeud_verifier_accepte_explication_valide(self):
        """Le nœud de vérification accepte une explication correcte."""
        from src.agent.graph import noeud_verifier, EtatDocument

        etat: EtatDocument = {
            "texte_document": "test",
            "langue": "fr",
            "question": None,
            "explication": {
                "type_document": "avis d'imposition",
                "resume_simple": "Vous devez payer 1450 euros avant le 15 septembre.",
                "actions": [],
                "termes": [],
                "avertissement": None,
                "citations": [],
                "incertitudes": [],
                "langue": "fr",
            },
            "nb_essais": 1,
            "erreur_fidelite": None,
            "rappel_demande": None,
            "rappel_approuve": False,
            "reponse_finale": None,
            "statut": "rag_ok",
        }

        resultat = noeud_verifier(etat)
        assert resultat["statut"] == "fidelite_ok"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
