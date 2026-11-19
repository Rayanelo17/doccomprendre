"""
Test OCR — Génère une image avec du texte et teste Tesseract.
"""

from PIL import Image, ImageDraw, ImageFont
import subprocess
from pathlib import Path

# Créer une image test
def creer_image_test():
    img = Image.new('RGB', (800, 600), color='white')
    d = ImageDraw.Draw(img)

    # Texte de test (ordonnance simplifiée)
    texte = """ORDONNANCE MEDICALE

Dr. Martin Dupont
12 rue de la Paix, Paris

Patient : M. Jean BERNARD
Date : 18/11/2026

Amoxicilline 1g
1 comprimé matin et soir pendant 7 jours

Doliprane 1000mg
1 comprimé toutes les 6h si douleur

A prendre pendant les repas.
"""

    # Dessiner le texte (police par défaut)
    y_offset = 50
    for ligne in texte.split('\n'):
        d.text((50, y_offset), ligne, fill='black')
        y_offset += 30

    # Sauvegarder
    output = Path("data/test_ordonnance.png")
    img.save(output)
    print(f"✅ Image créée : {output}")
    return output

# Test Tesseract
def test_tesseract(image_path):
    print(f"\n🔍 Test OCR sur {image_path}...")

    result = subprocess.run(
        ["tesseract", str(image_path), "stdout", "-l", "fra"],
        capture_output=True,
        text=True,
    )

    texte = result.stdout.strip()
    print(f"\n📄 Texte extrait ({len(texte)} chars) :")
    print("=" * 50)
    print(texte)
    print("=" * 50)

    return texte

if __name__ == "__main__":
    # Créer l'image
    img_path = creer_image_test()

    # Tester OCR
    texte_ocr = test_tesseract(img_path)

    if len(texte_ocr) > 50:
        print("\n✅ OCR fonctionne correctement")
    else:
        print("\n❌ OCR n'a pas extrait assez de texte")
