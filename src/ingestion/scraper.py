"""
Scraper du corpus de référence.
Sources : service-public.fr (admin) + ameli.fr (médical)
Sauvegarde chaque page en JSON dans data/corpus/
"""

import json
import time
import re
from pathlib import Path
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

# Dossier de sortie
CORPUS_DIR = Path("data/corpus")
CORPUS_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ─────────────────────────────────────────
# Sources à scraper
# ─────────────────────────────────────────

SOURCES_ADMIN = [
    # Impôts et finances
    ("https://www.service-public.fr/particuliers/vosdroits/F1419", "avis_imposition"),
    ("https://www.service-public.fr/particuliers/vosdroits/F2679", "declaration_impots"),
    ("https://www.service-public.fr/particuliers/vosdroits/F2386", "impot_revenu_calcul"),
    # Logement
    ("https://www.service-public.fr/particuliers/vosdroits/F1168", "quittance_loyer"),
    ("https://www.service-public.fr/particuliers/vosdroits/F920",  "contrat_location"),
    ("https://www.service-public.fr/particuliers/vosdroits/F31428","conge_locataire"),
    # Travail et emploi
    ("https://www.service-public.fr/particuliers/vosdroits/F2386", "contrat_travail"),
    ("https://www.service-public.fr/particuliers/vosdroits/F87",   "fiche_paie"),
    ("https://www.service-public.fr/particuliers/vosdroits/F89",   "licenciement"),
    ("https://www.service-public.fr/particuliers/vosdroits/F2918", "arret_travail"),
    # Famille
    ("https://www.service-public.fr/particuliers/vosdroits/F13244","allocations_familiales"),
    ("https://www.service-public.fr/particuliers/vosdroits/F3005", "caf_aides"),
    # Documents d'identité
    ("https://www.service-public.fr/particuliers/vosdroits/F1480", "carte_identite"),
    ("https://www.service-public.fr/particuliers/vosdroits/F14807","passeport"),
    # Santé et social
    ("https://www.service-public.fr/particuliers/vosdroits/F20314","carte_vitale"),
    ("https://www.service-public.fr/particuliers/vosdroits/F163",  "cmu"),
]

SOURCES_MEDICAL = [
    # has-sante.fr — recommandations officielles
    ("https://www.has-sante.fr/jcms/p_3261767/fr/comprendre-votre-ordonnance", "comprendre_ordonnance"),
    ("https://www.has-sante.fr/jcms/p_3278153/fr/bon-usage-des-medicaments", "bon_usage_medicaments"),
    ("https://www.has-sante.fr/jcms/p_3194507/fr/sante-et-prevention", "sante_prevention"),
    # service-public.fr — volet médical et social (suite)
    ("https://www.service-public.fr/particuliers/vosdroits/F303",   "arret_maladie_salarie"),
    ("https://www.service-public.fr/particuliers/vosdroits/F3053",  "indemnites_journalieres"),
    ("https://www.service-public.fr/particuliers/vosdroits/F2265",  "conge_maternite"),
    ("https://www.service-public.fr/particuliers/vosdroits/F10027", "ald_exoneration"),
    ("https://www.service-public.fr/particuliers/vosdroits/F2302",  "medecin_traitant"),
    # URLs corrigées
    ("https://www.service-public.fr/particuliers/vosdroits/F170",   "hospitalisation_droits"),
    ("https://www.service-public.fr/particuliers/vosdroits/F20302", "complementaire_sante"),
    ("https://www.service-public.fr/particuliers/vosdroits/F11162", "remboursement_medicament"),
    ("https://www.service-public.fr/particuliers/vosdroits/F1550",  "invalidite_pension"),
    ("https://www.service-public.fr/particuliers/vosdroits/F31677", "accident_travail"),
]


# ─────────────────────────────────────────
# Extracteur de texte
# ─────────────────────────────────────────

def _clean_text(text: str) -> str:
    """Nettoie le texte extrait (espaces multiples, lignes vides)."""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_service_public(soup: BeautifulSoup) -> str:
    """Extrait le contenu principal de service-public.fr."""
    # Contenu principal
    main = soup.find("main") or soup.find("article") or soup.find("div", {"id": "main-content"})
    if not main:
        main = soup.find("div", class_=re.compile(r"content|main|article", re.I))
    if main:
        # Supprimer nav, footer, scripts
        for tag in main.find_all(["nav", "footer", "script", "style", "button"]):
            tag.decompose()
        return _clean_text(main.get_text(separator=" "))
    return _clean_text(soup.get_text(separator=" "))


def _extract_ameli(soup: BeautifulSoup) -> str:
    """Extrait le contenu principal de ameli.fr."""
    main = soup.find("div", {"id": "main-content"}) or soup.find("main")
    if not main:
        main = soup.find("div", class_=re.compile(r"content|article|main", re.I))
    if main:
        for tag in main.find_all(["nav", "footer", "script", "style", "aside"]):
            tag.decompose()
        return _clean_text(main.get_text(separator=" "))
    return _clean_text(soup.get_text(separator=" "))


# ─────────────────────────────────────────
# Scraper principal
# ─────────────────────────────────────────

def scrape_page(
    url: str,
    slug: str,
    doc_type: str,
    extractor,
    delay: float = 1.5,
) -> Optional[dict]:
    """Scrape une page et retourne un dict JSON."""
    try:
        print(f"  Scraping {slug} ...", end=" ")
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.title.string.strip() if soup.title else slug
        texte = extractor(soup)

        if len(texte) < 100:
            print(f"⚠️  trop court ({len(texte)} chars) — ignoré")
            return None

        doc = {
            "id": f"{doc_type.upper()[:3]}-{slug}",
            "slug": slug,
            "url": url,
            "titre": title,
            "type": doc_type,
            "langue": "fr",
            "contenu": texte,
            "nb_chars": len(texte),
            "scraped_at": datetime.now().isoformat(),
        }

        # Sauvegarde
        out_path = CORPUS_DIR / f"{doc_type}_{slug}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

        print(f"✅ {len(texte)} chars → {out_path.name}")
        time.sleep(delay)
        return doc

    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur réseau : {e}")
        return None
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return None


def scrape_all() -> dict:
    """Lance le scraping complet et retourne un résumé."""
    results = {"admin": [], "medical": [], "errors": []}

    print("\n📥 Scraping — Documents ADMINISTRATIFS (service-public.fr)")
    print("=" * 60)
    for url, slug in SOURCES_ADMIN:
        doc = scrape_page(url, slug, "admin", _extract_service_public)
        if doc:
            results["admin"].append(doc["id"])
        else:
            results["errors"].append(slug)

    print(f"\n📥 Scraping — Documents MÉDICAUX (ameli.fr)")
    print("=" * 60)
    for url, slug in SOURCES_MEDICAL:
        doc = scrape_page(url, slug, "medical", _extract_ameli)
        if doc:
            results["medical"].append(doc["id"])
        else:
            results["errors"].append(slug)

    # Résumé
    print(f"\n{'=' * 60}")
    print(f"✅ Admin    : {len(results['admin'])} documents")
    print(f"✅ Médical  : {len(results['medical'])} documents")
    print(f"❌ Erreurs  : {len(results['errors'])} ({', '.join(results['errors'])})")
    print(f"📁 Corpus   : {CORPUS_DIR.resolve()}")

    # Index du corpus
    index_path = CORPUS_DIR / "index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"📋 Index    : {index_path}")

    return results


if __name__ == "__main__":
    import sys
    medical_only = "--medical-only" in sys.argv
    admin_only   = "--admin-only"   in sys.argv

    if medical_only:
        results = {"admin": [], "medical": [], "errors": []}
        print("\n📥 Scraping — Documents MÉDICAUX uniquement")
        print("=" * 60)
        for url, slug in SOURCES_MEDICAL:
            doc = scrape_page(url, slug, "medical", _extract_ameli)
            if doc:
                results["medical"].append(doc["id"])
            else:
                results["errors"].append(slug)
        print(f"\n✅ Médical : {len(results['medical'])} documents")
        print(f"❌ Erreurs : {len(results['errors'])} ({', '.join(results['errors'])})")
    elif admin_only:
        results = {"admin": [], "medical": [], "errors": []}
        print("\n📥 Scraping — Documents ADMIN uniquement")
        print("=" * 60)
        for url, slug in SOURCES_ADMIN:
            doc = scrape_page(url, slug, "admin", _extract_service_public)
            if doc:
                results["admin"].append(doc["id"])
            else:
                results["errors"].append(slug)
        print(f"\n✅ Admin   : {len(results['admin'])} documents")
        print(f"❌ Erreurs : {len(results['errors'])} ({', '.join(results['errors'])})")
    else:
        scrape_all()
