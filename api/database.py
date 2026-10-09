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
        sections_config TEXT DEFAULT '{}',
        is_paa INTEGER DEFAULT 0,
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
        annotated_image_b64 TEXT DEFAULT '',
        is_paa INTEGER DEFAULT 0,
        puntaje_verbal INTEGER DEFAULT 0,
        puntaje_mate INTEGER DEFAULT 0,
        puntaje_total_paa INTEGER DEFAULT 0,
        verbal_aciertos INTEGER DEFAULT 0,
        mate_aciertos INTEGER DEFAULT 0,
        scanned_at TEXT NOT NULL,
        FOREIGN KEY (exam_id) REFERENCES exams (id) ON DELETE CASCADE
    );
    """)

    # Migrations for existing DB if columns do not exist
    try:
        cursor.execute("ALTER TABLE exams ADD COLUMN is_paa INTEGER DEFAULT 0")
    except Exception:
        pass

    for col in [
        ("is_paa", "INTEGER DEFAULT 0"),
        ("puntaje_verbal", "INTEGER DEFAULT 0"),
        ("puntaje_mate", "INTEGER DEFAULT 0"),
        ("puntaje_total_paa", "INTEGER DEFAULT 0"),
        ("verbal_aciertos", "INTEGER DEFAULT 0"),
        ("mate_aciertos", "INTEGER DEFAULT 0")
    ]:
        try:
            cursor.execute(f"ALTER TABLE scan_results ADD COLUMN {col[0]} {col[1]}")
        except Exception:
            pass
    
    conn.commit()
    conn.close()

def create_exam(exam_data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    answer_key_json = json.dumps(exam_data.get("answer_key", {}))
    sections_json = json.dumps(exam_data.get("sections_config", {}))
    is_paa = 1 if exam_data.get("is_paa", False) else 0
    
    cursor.execute("""
    INSERT INTO exams (
        id, title, subject, total_questions, options_per_question,
        answer_key, points_per_question, penalty_per_wrong, sections_config, is_paa, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        exam_data["id"],
        exam_data["title"],
        exam_data.get("subject", ""),
        exam_data["total_questions"],
        exam_data.get("options_per_question", 4),
        answer_key_json,
        exam_data.get("points_per_question", 1.0),
        exam_data.get("penalty_per_wrong", 0.0),
        sections_json,
        is_paa,
        now
    ))
    
    conn.commit()
    conn.close()
    return get_exam(exam_data["id"])

def update_exam(exam_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    
    fields = []
    values = []
    for k, v in updates.items():
        if v is not None:
            if k in ["answer_key", "sections_config"]:
                fields.append(f"{k} = ?")
                values.append(json.dumps(v))
            elif k == "is_paa":
                fields.append(f"{k} = ?")
                values.append(1 if v else 0)
            elif k in ["title", "subject", "points_per_question", "penalty_per_wrong"]:
                fields.append(f"{k} = ?")
                values.append(v)
                
    if not fields:
        conn.close()
        return get_exam(exam_id)
        
    values.append(exam_id)
    query = f"UPDATE exams SET {', '.join(fields)} WHERE id = ?"
    cursor.execute(query, tuple(values))
    conn.commit()
    conn.close()
    return get_exam(exam_id)

def get_exam(exam_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT e.*, COUNT(s.id) as scan_count 
    FROM exams e 
    LEFT JOIN scan_results s ON e.id = s.exam_id 
    WHERE e.id = ?
    GROUP BY e.id
    """, (exam_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
        
    data = dict(row)
    data["answer_key"] = json.loads(data["answer_key"])
    data["sections_config"] = json.loads(data.get("sections_config") or "{}")
    data["is_paa"] = bool(data.get("is_paa", 0))
    return data

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
    
    result = []
    for row in rows:
        d = dict(row)
        d["answer_key"] = json.loads(d["answer_key"])
        d["sections_config"] = json.loads(d.get("sections_config") or "{}")
        d["is_paa"] = bool(d.get("is_paa", 0))
        result.append(d)
    return result

def delete_exam(exam_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM scan_results WHERE exam_id = ?", (exam_id,))
    cursor.execute("DELETE FROM exams WHERE id = ?", (exam_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def save_scan_result(result_data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    is_paa = 1 if result_data.get("is_paa", False) else 0

    cursor.execute("""
    INSERT INTO scan_results (
        id, exam_id, student_id, student_name, score, total_possible,
        percentage, correct_count, wrong_count, blank_count,
        student_answers, question_details, annotated_image_b64,
        is_paa, puntaje_verbal, puntaje_mate, puntaje_total_paa, verbal_aciertos, mate_aciertos, scanned_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        json.dumps(result_data["question_details"]),
        result_data.get("annotated_image_b64", ""),
        is_paa,
        result_data.get("puntaje_verbal", 0),
        result_data.get("puntaje_mate", 0),
        result_data.get("puntaje_total_paa", 0),
        result_data.get("verbal_aciertos", 0),
        result_data.get("mate_aciertos", 0),
        now
    ))
    
    conn.commit()
    conn.close()
    return get_scan_result(result_data["id"])

def get_scan_result(result_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scan_results WHERE id = ?", (result_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
        
    data = dict(row)
    data["student_answers"] = json.loads(data["student_answers"])
    data["question_details"] = json.loads(data["question_details"])
    data["is_paa"] = bool(data.get("is_paa", 0))
    return data

def get_scan_results(exam_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scan_results WHERE exam_id = ? ORDER BY scanned_at DESC", (exam_id,))
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        d = dict(row)
        d["student_answers"] = json.loads(d["student_answers"])
        d["question_details"] = json.loads(d["question_details"])
        d["is_paa"] = bool(d.get("is_paa", 0))
        results.append(d)
    return results

def delete_scan_result(result_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM scan_results WHERE id = ?", (result_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted
