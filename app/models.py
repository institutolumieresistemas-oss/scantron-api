from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class ExamCreate(BaseModel):
    title: str = Field(..., description="Título del examen")
    subject: Optional[str] = Field("", description="Materia o asignatura")
    total_questions: int = Field(..., ge=5, le=100, description="Cantidad de preguntas (5 a 100)")
    options_per_question: int = Field(4, ge=3, le=5, description="Opciones por pregunta (3 a 5: A-C, A-D o A-E)")
    answer_key: Dict[str, str] = Field(..., description="Diccionario con la respuesta correcta por número, ej: {'1': 'A', '2': 'C'}")
    points_per_question: float = Field(1.0, ge=0.1, description="Puntos por acierto")
    penalty_per_wrong: float = Field(0.0, ge=0.0, description="Puntos de penalización por fallo")

class ExamResponse(BaseModel):
    id: str
    title: str
    subject: str
    total_questions: int
    options_per_question: int
    answer_key: Dict[str, str]
    points_per_question: float
    penalty_per_wrong: float
    created_at: str
    scan_count: Optional[int] = 0

class QuestionFeedback(BaseModel):
    question: int
    correct_answer: str
    student_answer: Optional[str]
    is_correct: bool
    status: str # "correct", "wrong", "blank", "multiple"

class ScanResultResponse(BaseModel):
    id: str
    exam_id: str
    student_id: str
    student_name: Optional[str] = ""
    score: float
    total_possible: float
    percentage: float
    correct_count: int
    wrong_count: int
    blank_count: int
    student_answers: Dict[str, str]
    question_details: List[QuestionFeedback]
    annotated_image_url: Optional[str] = ""
    scanned_at: str
