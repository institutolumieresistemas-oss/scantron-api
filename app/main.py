import io
import uuid
import csv
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.database import (
    init_db, create_exam, get_exam, list_exams, delete_exam,
    save_scan_result, get_scan_results, delete_scan_result
)
from app.models import ExamCreate
from app.sheet_generator import generate_pdf_sheet
from app.omr_engine import process_omr_sheet

app = FastAPI(
    title="Scantron Móvil API",
    description="Sistema OMR para escaneo y calificación de exámenes con cámara de celular",
    version="1.0.0"
)

# Enable CORS for mobile browsers and external frontends (e.g. Hostinger)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    init_db()
    # Create sample demo exam if database is empty
    exams = list_exams()
    if not exams:
        sample_key = {str(i): ("A" if i % 4 == 1 else "B" if i % 4 == 2 else "C" if i % 4 == 3 else "D") for i in range(1, 21)}
        create_exam({
            "id": "EXM-DEMO20",
            "title": "Examen de Demostración (20 Preguntas)",
            "subject": "Evaluación General",
            "total_questions": 20,
            "options_per_question": 4,
            "answer_key": sample_key,
            "points_per_question": 1.0,
            "penalty_per_wrong": 0.0
        })

# --- EXAMS ENDPOINTS ---

@app.get("/api/exams")
def get_all_exams():
    return list_exams()

@app.post("/api/exams")
def create_new_exam(exam_data: ExamCreate):
    exam_id = f"EXM-{uuid.uuid4().hex[:6].upper()}"
    new_exam = {
        "id": exam_id,
        "title": exam_data.title,
        "subject": exam_data.subject or "",
        "total_questions": exam_data.total_questions,
        "options_per_question": exam_data.options_per_question,
        "answer_key": exam_data.answer_key,
        "points_per_question": exam_data.points_per_question,
        "penalty_per_wrong": exam_data.penalty_per_wrong
    }
    created = create_exam(new_exam)
    return created

@app.get("/api/exams/{exam_id}")
def get_one_exam(exam_id: str):
    exam = get_exam(exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Examen no encontrado.")
    return exam

@app.delete("/api/exams/{exam_id}")
def remove_exam(exam_id: str):
    success = delete_exam(exam_id)
    if not success:
        raise HTTPException(status_code=404, detail="Examen no encontrado.")
    return {"message": "Examen eliminado exitosamente."}

# --- PDF GENERATION ---

@app.get("/api/exams/{exam_id}/pdf")
def download_sheet_pdf(exam_id: str):
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

# --- SCANNING & GRADING ---

@app.post("/api/exams/{exam_id}/scan")
async def scan_exam_sheet(
    exam_id: str,
    file: UploadFile = File(...),
    student_name: Optional[str] = Form("")
):
    exam = get_exam(exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Examen no encontrado.")
    
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="El archivo subido está vacío.")
        
    try:
        # Run OMR computer vision analysis
        result = process_omr_sheet(contents, exam)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Error al procesar la hoja: {str(e)}")

    # Save to database
    result_id = str(uuid.uuid4())
    record = {
        "id": result_id,
        "exam_id": exam_id,
        "student_id": result["student_id"],
        "student_name": student_name or "",
        "score": result["score"],
        "total_possible": result["total_possible"],
        "percentage": result["percentage"],
        "correct_count": result["correct_count"],
        "wrong_count": result["wrong_count"],
        "blank_count": result["blank_count"],
        "student_answers": result["student_answers"],
        "question_details": result["question_details"],
        "annotated_image_path": ""
    }
    save_scan_result(record)

    return {
        "id": result_id,
        "exam_id": exam_id,
        "student_id": result["student_id"],
        "student_name": student_name or "",
        "score": result["score"],
        "total_possible": result["total_possible"],
        "percentage": result["percentage"],
        "correct_count": result["correct_count"],
        "wrong_count": result["wrong_count"],
        "blank_count": result["blank_count"],
        "student_answers": result["student_answers"],
        "question_details": result["question_details"],
        "annotated_image_b64": result["annotated_image_b64"]
    }

# --- RESULTS & EXPORT ---

@app.get("/api/exams/{exam_id}/results")
def get_results_for_exam(exam_id: str):
    exam = get_exam(exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Examen no encontrado.")
    results = get_scan_results(exam_id)
    return results

@app.delete("/api/results/{result_id}")
def remove_scan_result(result_id: str):
    success = delete_scan_result(result_id)
    if not success:
        raise HTTPException(status_code=404, detail="Resultado no encontrado.")
    return {"message": "Resultado eliminado."}

@app.get("/api/exams/{exam_id}/export-csv")
def export_csv(exam_id: str):
    exam = get_exam(exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Examen no encontrado.")
        
    results = get_scan_results(exam_id)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow([
        "ID Resultado", "Fecha Escaneo", "Matrícula", "Nombre Alumno",
        "Calificación", "Total Posible", "Porcentaje (%)",
        "Aciertos", "Fallos", "En Blanco"
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

# Static files for Mobile Web App
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
