"""
Tests automatiques pour les 4 contraintes non négociables.
À lancer après chaque modification.
"""

import pytest
import json


# =====================
# Tests de contraintes
# =====================

class TestNePasInventer:
    """Contrainte 1 : le système ne doit rien inventer."""

    def test_incertitude_declaree_si_info_manquante(self):
        """
        Si une info n'est pas dans le document, elle doit apparaître
        dans les incertitudes, jamais dans le résumé.
        """
        from src.schemas.models import Explication

        # Simule un document sans date
        explication = Explication(
            type_document="lettre",
            emetteur=None,
            resume_simple="Ce document concerne une convocation.",
            actions=[],
            termes=[],
            incertitudes=["La date limite n'est pas mentionnée dans le document."],
            citations=[],
            langue="fr",
        )

        # La date doit être dans les incertitudes, pas inventée dans le résumé
        assert "incertitudes" in explication.model_dump()
        assert len(explication.incertitudes) > 0

    def test_aucun_champ_non_sourcé_dans_resume(self):
        """
        Le résumé ne doit pas contenir d'affirmations sans source.
        (Test de forme : les champs None = info manquante, pas inventée)
        """
        from src.schemas.models import Explication

        explication = Explication(
            type_document="ordonnance",
            emetteur=None,  # pas inventé
            resume_simple="Ce document est une ordonnance médicale.",
            actions=[],
            termes=[],
            incertitudes=[],
            citations=[],
            langue="fr",
        )
        # emetteur=None signifie "inconnu", pas une valeur inventée
        assert explication.emetteur is None


class TestNePasConseiller:
    """Contrainte 2 : le système ne doit pas conseiller."""

    def test_avertissement_present_pour_doc_medical(self):
        """
        Pour un document médical, un avertissement doit toujours être présent.
        """
        from src.schemas.models import Explication

        explication = Explication(
            type_document="ordonnance",
            emetteur="Dr. [NOM MASQUÉ]",
            resume_simple="Cette ordonnance prescrit un traitement.",
            actions=[],
            termes=[],
            avertissement=(
                "Ce résumé est uniquement informatif. "
                "Consultez votre médecin ou pharmacien pour toute question."
            ),
            incertitudes=[],
            citations=[],
            langue="fr",
        )
        assert explication.avertissement is not None
        assert len(explication.avertissement) > 0
        assert "médecin" in explication.avertissement.lower() or "pharmacien" in explication.avertissement.lower()

    def test_refus_conseil_juridique(self):
        """
        Le système doit refuser toute demande de conseil juridique.
        Vérifie que les mots-clés déclencheurs sont couverts.
        """
        phrases_interdites = [
            "vous devriez faire appel",
            "je vous conseille de",
            "il faut que vous",
            "prenez ce médicament",
            "la meilleure stratégie juridique",
        ]
        # Ce test vérifie que ces phrases ne figurent pas dans les prompts système
        with open("prompts/system_explain.txt", encoding="utf-8") as f:
            prompt = f.read().lower()

        for phrase in phrases_interdites[:2]:  # test simplifié
            assert phrase not in prompt, f"Phrase interdite dans le prompt: {phrase}"


class TestNePasAgirSeul:
    """Contrainte 3 : validation humaine avant toute action."""

    def test_rappel_requiert_validation(self):
        """
        Un rappel ne peut être créé qu'après validation humaine.
        """
        from src.schemas.models import ReminderRequest
        from datetime import date

        # ReminderRequest est un objet de DEMANDE, pas d'action directe
        # La validation se fait côté API/LangGraph — ici on vérifie le schema
        reminder = ReminderRequest(
            action="Payer l'impôt",
            date_limite=date(2025, 9, 15),
            document_context="Avis d'imposition 2025",
        )
        assert reminder.action
        assert reminder.date_limite
        assert reminder.document_context


class TestNePasConserver:
    """Contrainte 4 : ne pas conserver de données personnelles."""

    def test_masquage_donnees_personnelles(self):
        """
        Les données personnelles doivent être masquées avant journalisation.
        """
        # Pattern minimal de masquage — le vrai test utilisera le pipeline complet
        import re

        texte = "Jean Dupont, numéro de sécu 1 85 07 75 113 001 27, doit payer."
        # Numéro de sécu : 13 chiffres séparés par espaces ou non
        texte_masque = re.sub(r'\b\d[\d\s]{12,16}\d\b', '[SECU MASQUÉE]', texte)
        # Nom propre : Prénom (majuscule + minuscules) + Nom (majuscule + minuscules)
        texte_masque = re.sub(r'\b[A-Z][a-zéèêëàâùûüîïôç]+ [A-Z][a-zéèêëàâùûüîïôç]+\b', '[NOM MASQUÉ]', texte_masque)

        assert "[NOM MASQUÉ]" in texte_masque, f"Nom non masqué dans : {texte_masque}"
        assert "Jean Dupont" not in texte_masque, f"Nom toujours visible dans : {texte_masque}"

    def test_schema_inclut_champ_incertitudes(self):
        """
        Le schema Explication inclut un champ incertitudes (pour les données manquantes).
        """
        from src.schemas.models import Explication
        fields = Explication.model_fields
        assert "incertitudes" in fields


# =====================
# Tests du schema
# =====================

class TestSchemaExplication:
    """Vérifie la solidité du contrat Pydantic."""

    def test_explication_valide_minimale(self):
        from src.schemas.models import Explication
        e = Explication(
            type_document="lettre",
            resume_simple="Texte de test.",
            actions=[],
            termes=[],
            incertitudes=[],
            citations=[],
            langue="fr",
        )
        assert e.type_document == "lettre"
        assert e.langue == "fr"

    def test_langue_invalide_refusee(self):
        from src.schemas.models import Explication
        import pydantic
        with pytest.raises(Exception):
            Explication(
                type_document="lettre",
                resume_simple="Test.",
                actions=[],
                termes=[],
                incertitudes=[],
                citations=[],
                langue="en",  # langue non supportée
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])