"""
Tests unitaires pour le module OCR.
"""

import pytest
from pathlib import Path
from src.vision.ocr import (
    extract_text_from_image,
    extract_text_from_pdf,
    extract_text_from_file,
    detect_document_language,
)


class TestDetectLanguage:
    """Tests de détection de langue."""

    def test_detect_french(self):
        text = "Vous devez payer votre impôt avant le 15 septembre 2025."
        lang, conf = detect_document_language(text)
        assert lang == "fr"
        assert conf > 0

    def test_detect_arabic(self):
        text = "مرحبا بك في النظام الطبي"
        lang, conf = detect_document_language(text)
        assert lang == "ar"
        assert conf > 0.3

    def test_detect_empty(self):
        lang, conf = detect_document_language("")
        assert lang == "fr"  # défaut


class TestOCR:
    """Tests OCR sur l'image générée."""

    def test_extract_from_test_image(self):
        """Teste l'OCR sur l'image de test générée."""
        img_path = Path("data/test_ordonnance.png")

        if not img_path.exists():
            pytest.skip("Image de test non trouvée — lancer src/vision/test_ocr.py d'abord")

        text = extract_text_from_image(str(img_path), lang="fra")

        # Vérifications basiques
        assert len(text) > 100, "Le texte extrait est trop court"
        assert "ORDONNANCE" in text.upper() or "ORDONNANCE" in text
        assert "Patient" in text or "patient" in text.lower()

    def test_extract_from_file_text(self):
        """Teste l'extraction d'un fichier texte."""
        txt_path = Path("data/document_test.txt")

        if not txt_path.exists():
            pytest.skip("Fichier texte de test non trouvé")

        text, lang = extract_text_from_file(str(txt_path))
        assert len(text) > 50
        assert lang in ("fr", "ar", "ary")


class TestPDFExtraction:
    """Tests extraction PDF."""

    def test_pdf_missing_fallback(self):
        """Vérifie que l'erreur est bien levée sur PDF manquant."""
        with pytest.raises(RuntimeError):
            extract_text_from_pdf("nonexistent.pdf")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
