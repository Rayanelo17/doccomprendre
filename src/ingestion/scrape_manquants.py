"""
Scrape uniquement les documents manquants (404 corrigés).
"""
import sys
import os
sys.path.insert(0, os.path.abspath("."))

from src.ingestion.scraper import scrape_page, _extract_service_public, _extract_ameli, CORPUS_DIR

MANQUANTS = [
    ("https://www.service-public.fr/particuliers/vosdroits/F13605", "complementaire_sante",     "medical", _extract_service_public),
    ("https://www.service-public.fr/particuliers/vosdroits/F725",   "remboursement_medicament", "medical", _extract_service_public),
]

print("\n📥 Scraping des documents manquants")
print("=" * 50)
ok, ko = 0, []
for url, slug, doc_type, extractor in MANQUANTS:
    doc = scrape_page(url, slug, doc_type, extractor)
    if doc:
        ok += 1
    else:
        ko.append(slug)

print(f"\n✅ Récupérés : {ok}")
print(f"❌ Encore en erreur : {ko}")
