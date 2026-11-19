"""
OCR des images et PDF.
Utilise Tesseract pour extraire le texte.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import fitz  # PyMuPDF
from PIL import Image


def _check_tesseract() -> bool:
    """Vérifie que Tesseract est installé."""
    try:
        subprocess.run(["tesseract", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def detect_document_language(text: str) -> Tuple[str, float]:
    """
    Détecte la langue dominante du texte.
    Retourne ("fr"|"ar"|"ary", confidence).
    """
    if not text or len(text.strip()) < 10:
        return "fr", 0.5

    # Compter les caractères arabes
    arabic_count = sum(1 for c in text if "؀" <= c <= "ۿ")
    text_length = max(len(text), 1)
    arabic_ratio = arabic_count / text_length

    # Mots français courants
    french_words = {
        "le", "la", "les", "de", "du", "des", "et", "est", "sont", "pour",
        "avec", "dans", "sur", "que", "qui", "vous", "votre", "date",
        "monsieur", "madame", "avant", "après", "jour", "mois"
    }
    text_lower = text.lower()
    french_matches = sum(1 for w in french_words if f" {w} " in f" {text_lower} ")
    french_ratio = french_matches / len(french_words)

    # Décision
    if arabic_ratio > 0.3:
        return "ar", arabic_ratio
    elif french_ratio > 0.1:
        return "fr", french_ratio
    else:
        return "fr", 0.5  # défaut français


def extract_text_from_image(image_path: str, lang: str = "fra") -> str:
    """Applique Tesseract OCR sur une image avec preprocessing."""
    if not _check_tesseract():
        raise RuntimeError("Tesseract n'est pas installé ou pas dans le PATH")

    try:
        # Ouvrir et prétraiter l'image (grayscale pour meilleure OCR)
        img = Image.open(image_path)
        if img.mode != 'L':
            img = img.convert('L')  # Niveaux de gris

        # Créer un fichier temporaire
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
            img.save(tmp_path, format='PNG')

        # OCR avec mode de segmentation automatique (--psm 3)
        result = subprocess.run(
            ["tesseract", tmp_path, "stdout", "-l", lang, "--psm", "3"],
            capture_output=True,
            text=True,
            timeout=30
        )

        # Cleanup
        try:
            os.unlink(tmp_path)
        except:
            pass

        return result.stdout.strip()
    except Exception as e:
        raise RuntimeError(f"Erreur Tesseract : {e}")


def extract_text_from_pdf(pdf_path: str) -> str:
    """Convertit un PDF en texte avec PyMuPDF."""
    try:
        doc = fitz.open(pdf_path)
        texts = []
        for page in doc:
            page_text = page.get_text()
            if page_text.strip():
                texts.append(page_text)
        doc.close()
        return "\n\n".join(texts)
    except Exception as e:
        raise RuntimeError(f"Erreur PyMuPDF : {e}")


def extract_text_from_file(
    file_path: str,
    content_type: Optional[str] = None
) -> Tuple[str, str]:
    """
    Extrait le texte d'un fichier (PDF, image ou texte).
    Retourne (texte_extrait, langue_detectee).
    """
    path = Path(file_path)

    # Déterminer le type
    if content_type is None:
        ext = path.suffix.lower()
        if ext == ".pdf":
            content_type = "pdf"
        elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff"):
            content_type = "image"
        else:
            content_type = "text"

    # Extraction
    if content_type == "pdf":
        text = extract_text_from_pdf(file_path)
        # Si le PDF est vide (scanné), fallback sur OCR
        if not text or len(text.strip()) < 50:
            # Convertir première page en image et OCR
            try:
                doc = fitz.open(file_path)
                page = doc[0]
                pix = page.get_pixmap()
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    pix.save(tmp.name)
                    text = extract_text_from_image(tmp.name)
                doc.close()
                os.unlink(tmp.name)
            except:
                pass

    elif content_type == "image":
        text = extract_text_from_image(file_path)

    else:
        # Texte brut
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()

    # Détection de langue
    lang, _ = detect_document_language(text)

    return text, lang


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        path = sys.argv[1]
        text, lang = extract_text_from_file(path)
        print(f"Langue détectée : {lang}")
        print(f"Texte ({len(text)} chars) :")
        print(text[:500])
    else:
        print("Usage: python -m src.vision.ocr <fichier>")