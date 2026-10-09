from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class ExamCreate(BaseModel):
    title: str = Field(..., description="Título del examen")
    subject: Optional[str] = Field("", description="Materia o asignatura")
    total_questions: int = Field(..., ge=5, le=150, description="Cantidad de preguntas (5 a 150)")
    options_per_question: int = Field(4, ge=3, le=5, description="Opciones por pregunta (3 a 5: A-C, A-D o A-E)")
    answer_key: Dict[str, str] = Field(..., description="Diccionario de respuestas correctas, ej: {'1': 'A', '2': 'C'}")
    points_per_question: float = Field(1.0, ge=0.1, description="Puntos por acierto")
    penalty_per_wrong: float = Field(0.0, ge=0.0, description="Penalización por respuesta incorrecta")
    sections_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Configuración de secciones")
    is_paa: Optional[bool] = Field(False, description="Indica si es el formato oficial PAA 125 reactivos")

class ExamUpdate(BaseModel):
    title: Optional[str] = None
    subject: Optional[str] = None
    answer_key: Optional[Dict[str, str]] = None
    points_per_question: Optional[float] = None
    penalty_per_wrong: Optional[float] = None
    sections_config: Optional[Dict[str, Any]] = None
    is_paa: Optional[bool] = None

class ExamResponse(BaseModel):
    id: str
    title: str
    subject: str
    total_questions: int
    options_per_question: int
    answer_key: Dict[str, str]
    points_per_question: float
    penalty_per_wrong: float
    sections_config: Optional[Dict[str, Any]] = None
    is_paa: Optional[bool] = False
    created_at: str
    scan_count: Optional[int] = 0

class QuestionFeedback(BaseModel):
    question: int
    section: Optional[str] = None
    area: Optional[str] = None
    correct_answer: Optional[str] = None
    student_answer: Optional[str] = None
    is_correct: bool
    status: str  # "correct", "wrong", "blank", "multiple"

class ScanStudentResponse(BaseModel):
    id: str
    exam_id: str
    student_id: str
    student_name: Optional[str] = ""
    is_paa: Optional[bool] = False
    score: float
    total_possible: float
    percentage: float
    puntaje_verbal: Optional[int] = None
    puntaje_mate: Optional[int] = None
    puntaje_total_paa: Optional[int] = None
    verbal_aciertos: Optional[int] = None
    mate_aciertos: Optional[int] = None
    correct_count: int
    wrong_count: int
    blank_count: int
    student_answers: Dict[str, str]
    question_details: List[QuestionFeedback]
    annotated_image_b64: Optional[str] = ""
    scanned_at: str

class MasterScanResponse(BaseModel):
    is_paa: Optional[bool] = False
    detected_answers: Dict[str, str]
    total_detected: int
    total_questions: int
    options_per_question: int
    annotated_image_b64: Optional[str] = ""
