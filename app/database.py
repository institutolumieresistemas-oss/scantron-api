import sqlite3
import json
import os
from typing import List, Dict, Optional, Any
from datetime import datetime

DB_PATH = os.environ.get("DATABASE_PATH", "scantron.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Exams table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exams (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        subject TEXT DEFAULT '',
        total_questions INTEGER NOT NULL,
        options_per_question INTEGER DEFAULT 4,
        answer_key TEXT NOT NULL,
        points_per_question REAL DEFAULT 1.0,
        penalty_per_wrong REAL DEFAULT 0.0,
        created_at TEXT NOT NULL
    );
    """)
    
    # Scan Results table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scan_results (
        id TEXT PRIMARY KEY,
        exam_id TEXT NOT NULL,
        student_id TEXT DEFAULT 'S/N',
        student_name TEXT DEFAULT '',
        score REAL NOT NULL,
        total_possible REAL NOT NULL,
        percentage REAL NOT NULL,
        correct_count INTEGER NOT NULL,
        wrong_count INTEGER NOT NULL,
        blank_count INTEGER NOT NULL,
        student_answers TEXT NOT NULL,
        question_details TEXT NOT NULL,
        annotated_image_path TEXT DEFAULT '',
        scanned_at TEXT NOT NULL,
        FOREIGN KEY (exam_id) REFERENCES exams (id) ON DELETE CASCADE
    );
    """)
    
    conn.commit()
    conn.close()

def create_exam(exam_data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    cursor.execute("""
        INSERT INTO exams (id, title, subject, total_questions, options_per_question, answer_key, points_per_question, penalty_per_wrong, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        exam_data["id"],
        exam_data["title"],
        exam_data.get("subject", ""),
        exam_data["total_questions"],
        exam_data.get("options_per_question", 4),
        json.dumps(exam_data["answer_key"]),
        exam_data.get("points_per_question", 1.0),
        exam_data.get("penalty_per_wrong", 0.0),
        now
    ))
    conn.commit()
    conn.close()
    return get_exam(exam_data["id"])

def get_exam(exam_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM exams WHERE id = ?", (exam_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["answer_key"] = json.loads(d["answer_key"])
    return d

def list_exams() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.*, COUNT(s.id) as scan_count 
        FROM exams e 
        LEFT JOIN scan_results s ON e.id = s.exam_id 
        GROUP BY e.id 
        ORDER BY e.created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    exams = []
    for r in rows:
        d = dict(r)
        d["answer_key"] = json.loads(d["answer_key"])
        exams.append(d)
    return exams

def delete_exam(exam_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM scan_results WHERE exam_id = ?", (exam_id,))
    cursor.execute("DELETE FROM exams WHERE id = ?", (exam_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted

def save_scan_result(result_data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    cursor.execute("""
        INSERT INTO scan_results (
            id, exam_id, student_id, student_name, score, total_possible, percentage,
            correct_count, wrong_count, blank_count, student_answers, question_details,
            annotated_image_path, scanned_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        result_data["id"],
        result_data["exam_id"],
        result_data.get("student_id", "S/N"),
        result_data.get("student_name", ""),
        result_data["score"],
        result_data["total_possible"],
        result_data["percentage"],
        result_data["correct_count"],
        result_data["wrong_count"],
        result_data["blank_count"],
        json.dumps(result_data["student_answers"]),
        json.dumps(result_data.get("question_details", [])),
        result_data.get("annotated_image_path", ""),
        now
    ))
    conn.commit()
    conn.close()
    return result_data

def get_scan_results(exam_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scan_results WHERE exam_id = ? ORDER BY scanned_at DESC", (exam_id,))
    rows = cursor.fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d["student_answers"] = json.loads(d["student_answers"])
        d["question_details"] = json.loads(d["question_details"])
        results.append(d)
    return results

def get_scan_result(result_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scan_results WHERE id = ?", (result_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["student_answers"] = json.loads(d["student_answers"])
    d["question_details"] = json.loads(d["question_details"])
    return d

def delete_scan_result(result_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM scan_results WHERE id = ?", (result_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted
