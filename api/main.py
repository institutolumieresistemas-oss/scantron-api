import io
import os
import uuid
import csv
import json
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from api.database import (
    init_db, create_exam, get_exam, list_exams, delete_exam, update_exam,
    save_scan_result, get_scan_result, get_scan_results, delete_scan_result
)
from api.models import ExamCreate, ExamUpdate, ExamResponse, ScanStudentResponse, MasterScanResponse
from api.sheet_generator import generate_pdf_sheet
from api.omr_engine import process_omr_sheet, scan_master_sheet
from api.paa_engine import procesar_examen_paa, scan_master_paa_sheet

app = FastAPI(
    title="Scantron OMR API - PAA Ready",
    description="API REST para análisis y calificación automática de hojas de respuestas OMR y exámenes oficiales PAA (College Board / UDG).",
    version="1.1.0"
)

# Enable CORS for Mobile Apps (Ionic/Capacitor), Web Clients and Localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def build_default_paa_key():
    """Genera una clave predeterminada para el examen PAA 125 reactivos."""
    key = {}
    # 1 a 45: Lectura
    opts = ["A", "B", "C", "D"]
    for i in range(1, 46):
        key[str(i)] = opts[(i - 1) % 4]
    # 46 a 70: Redacción
    for i in range(46, 71):
        key[str(i)] = opts[(i - 46) % 4]
    # 71 a 115: Matemáticas ABCD
    for i in range(71, 116):
        key[str(i)] = opts[(i - 71) % 4]
    # 116 a 125: Matemáticas Grid (valores numéricos de ejemplo)
    grid_samples = ["1/2", "3.5", "18", "4/5", "2.25", "10", "3/8", "125", "0.75", "42"]
    for i in range(116, 126):
        key[str(i)] = grid_samples[i - 116]
    return key

@app.on_event("startup")
def startup_event():
    init_db()
    # Verifica si existe el examen oficial PAA 125 reactivos
    paa_exam = get_exam("EXM-PAA125")
    if not paa_exam:
        paa_sections = [
            {"name": "Lectura", "from": 1, "to": 45, "type": "LECTURA", "area": "VERBAL"},
            {"name": "Redacción", "from": 46, "to": 70, "type": "REDACCION", "area": "VERBAL"},
            {"name": "Matemáticas (Opción Múltiple)", "from": 71, "to": 115, "type": "MATEMATICAS", "area": "MATEMATICAS"},
            {"name": "Matemáticas (Grid Numérico)", "from": 116, "to": 125, "type": "MATEMATICASGRID", "area": "MATEMATICAS"}
        ]
        create_exam({
            "id": "EXM-PAA125",
            "title": "Examen PAA Oficial (125 Reactivos)",
            "subject": "Prueba de Aptitud Académica - College Board",
            "total_questions": 125,
            "options_per_question": 4,
            "answer_key": build_default_paa_key(),
            "points_per_question": 1.0,
            "penalty_per_wrong": 0.0,
            "sections_config": {"sections": paa_sections},
            "is_paa": True
        })

# --- HEALTH & INFO ---

@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "service": "Scantron OMR & PAA API",
        "version": "1.1.0",
        "paa_supported": True,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/exams/paa/template")
def get_paa_template_info():
    """Retorna la especificación completa del examen oficial PAA 125 reactivos."""
    return {
        "id": "EXM-PAA125",
        "title": "Examen PAA Oficial (125 Reactivos)",
        "total_questions": 125,
        "options_per_question": 4,
        "is_paa": True,
        "sections": [
            {"name": "Lectura", "from": 1, "to": 45, "total": 45, "area": "VERBAL"},
            {"name": "Redacción", "from": 46, "to": 70, "total": 25, "area": "VERBAL"},
            {"name": "Matemáticas (ABCD)", "from": 71, "to": 115, "total": 45, "area": "MATEMATICAS"},
            {"name": "Matemáticas (Grid Numérico)", "from": 116, "to": 125, "total": 10, "area": "MATEMATICAS"}
        ],
        "scoring": {
            "verbal_scale": "200 - 800",
            "math_scale": "200 - 800",
            "total_scale": "400 - 1600"
        }
    }

# --- EXAMS MANAGEMENT ---

@app.get("/api/exams")
def get_all_exams():
    """Obtiene la lista de todos los exámenes configurados."""
    return list_exams()

@app.post("/api/exams")
def create_new_exam(exam_data: ExamCreate):
    """Crea un nuevo examen con su clave de respuestas."""
    exam_id = f"EXM-{uuid.uuid4().hex[:6].upper()}"
    new_exam = {
        "id": exam_id,
        "title": exam_data.title,
        "subject": exam_data.subject or "",
        "total_questions": exam_data.total_questions,
        "options_per_question": exam_data.options_per_question,
        "answer_key": exam_data.answer_key,
        "points_per_question": exam_data.points_per_question,
        "penalty_per_wrong": exam_data.penalty_per_wrong,
        "sections_config": exam_data.sections_config or {},
        "is_paa": exam_data.is_paa or (exam_data.total_questions == 125)
    }
    created = create_exam(new_exam)
    return created

@app.get("/api/exams/{exam_id}")
def get_one_exam(exam_id: str):
    """Obtiene el detalle y clave de un examen específico."""
    exam = get_exam(exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Examen no encontrado.")
    return exam

@app.put("/api/exams/{exam_id}")
def update_existing_exam(exam_id: str, updates: ExamUpdate):
    """Actualiza los datos o la clave de respuestas de un examen."""
    exam = get_exam(exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Examen no encontrado.")
    updated = update_exam(exam_id, updates.dict(exclude_unset=True))
    return updated

@app.delete("/api/exams/{exam_id}")
def remove_exam(exam_id: str):
    """Elimina un examen y todos sus resultados asociados."""
    success = delete_exam(exam_id)
    if not success:
        raise HTTPException(status_code=404, detail="Examen no encontrado.")
    return {"message": "Examen eliminado exitosamente."}

# --- PDF GENERATOR ---

@app.get("/api/exams/{exam_id}/pdf")
def download_sheet_pdf(exam_id: str):
    """Genera y descarga la plantilla en PDF para imprimir."""
    exam = get_exam(exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Examen no encontrado.")
    
    pdf_buffer = generate_pdf_sheet(exam)
    filename = f"plantilla_{exam_id}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )

# --- SCANNING & OMR ENGINE (CON SOPORTE PAA) ---

@app.post("/api/omr/scan-master")
async def scan_master_key_sheet(
    file: UploadFile = File(...),
    total_questions: int = Form(20),
    options_per_question: int = Form(4),
    is_paa: bool = Form(False)
):
    """
    Escanea una hoja maestra con la cámara y detecta automáticamente
    las respuestas marcadas. Si es PAA (125 reactivos), utiliza el motor de alta resolución A4.
    """
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="El archivo subido está vacío.")
    
    try:
        if is_paa or total_questions == 125:
            result = scan_master_paa_sheet(contents)
        else:
            result = scan_master_sheet(contents, total_questions, options_per_question)
        return result
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Error al analizar la hoja maestra: {str(e)}")

@app.post("/api/exams/{exam_id}/scan")
async def scan_student_sheet(
    exam_id: str,
    file: UploadFile = File(...),
    student_name: Optional[str] = Form("")
):
    """
    Escanea la hoja de un alumno, califica contra el examen y guarda el resultado.
    Soporta tanto exámenes regulares como el examen oficial PAA de 125 reactivos.
    """
    exam = get_exam(exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Examen no encontrado.")
    
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="El archivo subido está vacío.")
        
    try:
        is_paa_exam = exam.get("is_paa", False) or (exam.get("total_questions") == 125)
        if is_paa_exam:
            # Motor Oficial PAA 125 reactivos
            result = procesar_examen_paa(contents, exam.get("answer_key", {}))
        else:
            # Motor genérico OMR
            result = process_omr_sheet(contents, exam)
            result["is_paa"] = False
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Error al procesar la hoja del alumno: {str(e)}")

    # Guardar en base de datos
    result_id = str(uuid.uuid4())
    record = {
        "id": result_id,
        "exam_id": exam_id,
        "student_id": result.get("student_id", "S/N"),
        "student_name": student_name or "",
        "score": result["score"],
        "total_possible": result["total_possible"],
        "percentage": result["percentage"],
        "correct_count": result["correct_count"],
        "wrong_count": result["wrong_count"],
        "blank_count": result["blank_count"],
        "student_answers": result["student_answers"],
        "question_details": result["question_details"],
        "annotated_image_b64": result.get("annotated_image_b64", ""),
        "is_paa": result.get("is_paa", False),
        "puntaje_verbal": result.get("puntaje_verbal", 0),
        "puntaje_mate": result.get("puntaje_mate", 0),
        "puntaje_total_paa": result.get("puntaje_total_paa", 0),
        "verbal_aciertos": result.get("verbal_aciertos", 0),
        "mate_aciertos": result.get("mate_aciertos", 0)
    }
    saved_record = save_scan_result(record)
    return saved_record

# --- RESULTS & EXPORT ---

@app.get("/api/exams/{exam_id}/results")
def get_exam_results_list(exam_id: str):
    """Lista todos los exámenes calificados para una evaluación."""
    exam = get_exam(exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Examen no encontrado.")
    return get_scan_results(exam_id)

@app.get("/api/results/{result_id}")
def get_single_result(result_id: str):
    """Obtiene el resultado detallado de una calificación."""
    record = get_scan_result(result_id)
    if not record:
        raise HTTPException(status_code=404, detail="Resultado no encontrado.")
    return record

@app.delete("/api/results/{result_id}")
def remove_result(result_id: str):
    """Elimina el registro de calificación de un alumno."""
    success = delete_scan_result(result_id)
    if not success:
        raise HTTPException(status_code=404, detail="Resultado no encontrado.")
    return {"message": "Resultado eliminado exitosamente."}

@app.get("/api/exams/{exam_id}/export")
def export_results_to_csv(exam_id: str):
    """Exporta las calificaciones a un archivo CSV compatible con Excel."""
    exam = get_exam(exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Examen no encontrado.")
        
    results = get_scan_results(exam_id)
    is_paa = exam.get("is_paa", False) or (exam.get("total_questions") == 125)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    if is_paa:
        writer.writerow([
            "ID Evaluacion", "Fecha/Hora", "Matricula", "Nombre del Alumno",
            "Puntaje Total PAA (1600)", "Puntaje Verbal (800)", "Puntaje Matematicas (800)",
            "Aciertos Verbal (70)", "Aciertos Mate (55)", "Total Aciertos (125)", "Errores", "En Blanco"
        ])
        for r in results:
            writer.writerow([
                r["id"],
                r["scanned_at"],
                r.get("student_id", "S/N"),
                r.get("student_name", ""),
                r.get("puntaje_total_paa", r.get("score")),
                r.get("puntaje_verbal", 0),
                r.get("puntaje_mate", 0),
                r.get("verbal_aciertos", 0),
                r.get("mate_aciertos", 0),
                r.get("correct_count", 0),
                r.get("wrong_count", 0),
                r.get("blank_count", 0)
            ])
    else:
        writer.writerow([
            "ID Evaluacion", "Fecha/Hora", "Matricula", "Nombre del Alumno",
            "Calificacion", "Puntaje Maximo", "Porcentaje", "Aciertos", "Errores", "En Blanco"
        ])
        for r in results:
            writer.writerow([
                r["id"],
                r["scanned_at"],
                r["student_id"],
                r.get("student_name", ""),
                r["score"],
                r["total_possible"],
                f"{r['percentage']}%",
                r["correct_count"],
                r["wrong_count"],
                r["blank_count"]
            ])
        
    output.seek(0)
    filename = f"calificaciones_{exam_id}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# --- STATIC FALLBACK IF WEB ASSETS EXIST ---
static_dir = os.path.join(os.path.dirname(__file__), "..", "app", "static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    @app.get("/")
    def index():
        return {
            "service": "Scantron OMR & PAA API",
            "version": "1.1.0",
            "documentation": "/docs",
            "health": "/api/health"
        }
