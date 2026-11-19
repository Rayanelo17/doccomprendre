from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import date


class Action(BaseModel):
    action: str
    date_limite: Optional[date] = None
    note: Optional[str] = None


class Terme(BaseModel):
    terme: str
    explication: str
    source: Optional[str] = None  # fichier + page du corpus


class Explication(BaseModel):
    type_document: str
    emetteur: Optional[str] = None
    resume_simple: str
    actions: List[Action]
    termes: List[Terme]
    avertissement: Optional[str] = None
    citations: List[str] = []
    incertitudes: List[str] = []  # ce qui manque dans le document
    langue: Literal["fr", "ar", "ary"]


class DocumentInput(BaseModel):
    content: str
    filename: Optional[str] = None
    content_type: str = "text"  # "text", "pdf", "image"


class QuestionInput(BaseModel):
    question: str
    document_id: str


class ChatResponse(BaseModel):
    explanation: Optional[Explication] = None
    response: Optional[str] = None
    uncertainty_notice: Optional[str] = None


class ReminderRequest(BaseModel):
    action: str
    date_limite: date
    document_context: str