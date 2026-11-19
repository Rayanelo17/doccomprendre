"""
API FastAPI — point d'entrée du système.
Routes :
  POST /expliquer     → explique un document
  POST /question      → répond à une question sur un document
  GET  /health        → statut du système
"""

import uuid
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import tempfile
import shutil
from pathlib import Path

from src.rag.chain import expliquer_document, repondre_question
from src.schemas.models import Explication
from src.vision.ocr import extract_text_from_file

app = FastAPI(
    title="DocComprendre API",
    description="Assistant de compréhension de documents administratifs et médicaux",
    version="0.1.0",
)

# CORS pour Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────
# Modèles de requête
# ─────────────────────────────────────────

class ExpliquerRequest(BaseModel):
    texte: str
    langue: str = "fr"  # fr, ar, ary


class QuestionRequest(BaseModel):
    question: str
    texte_document: str
    langue: str = "fr"


class QuestionResponse(BaseModel):
    reponse: str
    langue: str


# ─────────────────────────────────────────
# Routes
# ─────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "0.1.0",
    }


@app.post("/expliquer", response_model=Explication)
def route_expliquer(req: ExpliquerRequest):
    """
    Reçoit un texte de document et retourne une explication structurée.
    """
    if not req.texte or len(req.texte.strip()) < 10:
        raise HTTPException(status_code=400, detail="Le texte du document est trop court.")

    if req.langue not in ("fr", "ar", "ary"):
        raise HTTPException(status_code=400, detail="Langue non supportée. Utilisez : fr, ar, ary.")

    try:
        explication = expliquer_document(req.texte, langue=req.langue)
        return explication
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'explication : {str(e)}")


@app.post("/expliquer-fichier", response_model=Explication)
async def route_expliquer_fichier(
    fichier: UploadFile = File(...),
    langue: str = Form("fr")
):
    """
    Reçoit un fichier (PDF, image) et retourne une explication structurée.
    """
    if langue not in ("fr", "ar", "ary"):
        raise HTTPException(status_code=400, detail="Langue non supportée. Utilisez : fr, ar, ary.")

    # Vérifier le type de fichier
    ext = Path(fichier.filename).suffix.lower()
    if ext not in (".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".txt"):
        raise HTTPException(
            status_code=400,
            detail="Format non supporté. Utilisez : PDF, PNG, JPG, JPEG, BMP, TXT"
        )

    # Sauvegarder temporairement
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            shutil.copyfileobj(fichier.file, tmp)
            tmp_path = tmp.name

        # Extraire le texte
        texte, lang_detectee = extract_text_from_file(tmp_path)

        # Cleanup
        Path(tmp_path).unlink(missing_ok=True)

        if not texte or len(texte.strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail="Impossible d'extraire du texte de ce fichier. Vérifiez qu'il contient du texte lisible."
            )

        # Générer l'explication
        explication = expliquer_document(texte, langue=langue)
        return explication

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement du fichier : {str(e)}")


@app.post("/question", response_model=QuestionResponse)
def route_question(req: QuestionRequest):
    """
    Répond à une question sur un document spécifique.
    """
    if not req.question or len(req.question.strip()) < 3:
        raise HTTPException(status_code=400, detail="La question est trop courte.")

    if not req.texte_document or len(req.texte_document.strip()) < 10:
        raise HTTPException(status_code=400, detail="Le texte du document est trop court.")

    try:
        reponse = repondre_question(req.question, req.texte_document, langue=req.langue)
        return QuestionResponse(reponse=reponse, langue=req.langue)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la réponse : {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
