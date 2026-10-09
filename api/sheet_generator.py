import io
import math
import qrcode
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

PAGE_WIDTH, PAGE_HEIGHT = letter  # 612.0 x 792.0 points

# Normalization constants (Corner fiducial markers)
CORNER_MARGIN = 28.0
MARKER_SIZE = 32.0

def get_layout_config(total_questions: int, options_per_question: int = 4):
    """
    Returns column and grid parameters based on number of questions.
    """
    if total_questions <= 25:
        num_cols = 1 if total_questions <= 15 else 2
        per_col = 15 if num_cols == 1 else 13
    elif total_questions <= 50:
        num_cols = 2
        per_col = 25
    elif total_questions <= 75:
        num_cols = 3
        per_col = 25
    else:
        num_cols = 4
        per_col = math.ceil(total_questions / 4)
    
    return {
        "num_cols": num_cols,
        "per_col": per_col,
        "options": options_per_question
    }

def get_bubble_normalized_coords(total_questions: int, options_per_question: int = 4):
    """
    Computes exact normalized (u, v) coordinates (0.0 to 1.0, top-left origin)
    for every question bubble and student ID bubble.
    Shared directly with the OMR computer vision engine.
    """
    layout = get_layout_config(total_questions, options_per_question)
    num_cols = layout["num_cols"]
    per_col = layout["per_col"]
    
    bubble_map = {
        "student_id": {},  # col_idx (0..5) -> digit (0..9) -> (u, v)
        "questions": {}    # q_num (1..N) -> option ('A'..'E') -> (u, v)
    }
    
    # Student ID Grid coordinates (top right section)
    id_start_x = 345.0
    id_start_y = 665.0
    id_col_w = 20.0
    id_row_h = 14.5
    
    for c in range(6):  # 6 digit columns
        col_x = id_start_x + c * id_col_w
        for digit in range(10):
            pt_y = id_start_y - digit * id_row_h
            u = col_x / PAGE_WIDTH
            v = (PAGE_HEIGHT - pt_y) / PAGE_HEIGHT
            if c not in bubble_map["student_id"]:
                bubble_map["student_id"][c] = {}
            bubble_map["student_id"][c][digit] = (u, v)
            
    # Questions Grid coordinates
    grid_top_y = 460.0
    col_width = (PAGE_WIDTH - 90.0) / num_cols
    row_height = min(17.5, (grid_top_y - 60.0) / per_col)
    
    opt_labels = ["A", "B", "C", "D", "E"][:options_per_question]
    opt_spacing = 16.5
    
    q_num = 1
    for c in range(num_cols):
        col_x = 48.0 + c * col_width
        for r in range(per_col):
            if q_num > total_questions:
                break
            q_y = grid_top_y - r * row_height
            bubble_map["questions"][q_num] = {}
            
            # Question number is at col_x, bubbles start at col_x + 24
            bubbles_x_start = col_x + 24.0
            for opt_idx, opt_letter in enumerate(opt_labels):
                bx = bubbles_x_start + opt_idx * opt_spacing
                by = q_y
                u = bx / PAGE_WIDTH
                v = (PAGE_HEIGHT - by) / PAGE_HEIGHT
                bubble_map["questions"][q_num][opt_letter] = (u, v)
                
            q_num += 1
            
    return bubble_map

def generate_pdf_sheet(exam: dict) -> io.BytesIO:
    """
    Generates a printable Letter-size OMR sheet for the given exam.
    Returns in-memory BytesIO PDF.
    """
    total_questions = exam.get("total_questions", 30)
    options_count = exam.get("options_per_question", 4)
    exam_id = exam.get("id", "EXM-001")
    exam_title = exam.get("title", "Evaluación")
    exam_subject = exam.get("subject", "")
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setTitle(f"Scantron - {exam_title}")
    
    # 1. Four High-Contrast Corner Calibration Markers (Fiducials)
    corners = [
        (CORNER_MARGIN, PAGE_HEIGHT - CORNER_MARGIN - MARKER_SIZE),  # Top-Left
        (PAGE_WIDTH - CORNER_MARGIN - MARKER_SIZE, PAGE_HEIGHT - CORNER_MARGIN - MARKER_SIZE),  # Top-Right
        (CORNER_MARGIN, CORNER_MARGIN),  # Bottom-Left
        (PAGE_WIDTH - CORNER_MARGIN - MARKER_SIZE, CORNER_MARGIN)  # Bottom-Right
    ]
    
    p.setFillColor(colors.black)
    for cx, cy in corners:
        p.rect(cx, cy, MARKER_SIZE, MARKER_SIZE, stroke=0, fill=1)
        p.setFillColor(colors.white)
        p.circle(cx + MARKER_SIZE / 2, cy + MARKER_SIZE / 2, 4.5, stroke=0, fill=1)
        p.setFillColor(colors.black)
        p.circle(cx + MARKER_SIZE / 2, cy + MARKER_SIZE / 2, 2.0, stroke=0, fill=1)

    # 2. Header and Exam Info
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(70, PAGE_HEIGHT - 48, exam_title[:45])
    
    p.setFont("Helvetica", 9)
    if exam_subject:
        p.drawString(70, PAGE_HEIGHT - 62, f"Materia: {exam_subject}")
    p.drawString(70, PAGE_HEIGHT - 74, f"Código Examen: {exam_id}  |  Preguntas: {total_questions}")
    
    # Instructions Box
    p.setStrokeColor(colors.gray)
    p.setLineWidth(0.6)
    p.rect(70, PAGE_HEIGHT - 120, 240, 38, fill=0)
    p.setFont("Helvetica-Bold", 7.5)
    p.drawString(75, PAGE_HEIGHT - 94, "INSTRUCCIONES DE LLENADO:")
    p.setFont("Helvetica", 7)
    p.drawString(75, PAGE_HEIGHT - 105, "• Rellene completamente los círculos con lápiz oscuro o tinta negra.")
    p.drawString(75, PAGE_HEIGHT - 115, "• No haga tachaduras ni marque más de una opción por pregunta.")

    # QR Code containing exam metadata
    try:
        qr = qrcode.QRCode(box_size=2, border=1)
        qr.add_data(f"SCANTRON:{exam_id}:Q{total_questions}:O{options_count}")
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)
        
        from reportlab.lib.utils import ImageReader
        qr_reader = ImageReader(qr_buffer)
        p.drawImage(qr_reader, 260, PAGE_HEIGHT - 82, width=48, height=48)
    except Exception:
        pass

    # 3. Student Info and Student ID Grid
    p.setFont("Helvetica-Bold", 8)
    p.drawString(70, PAGE_HEIGHT - 138, "NOMBRE DEL ALUMNO:")
    p.line(180, PAGE_HEIGHT - 140, 310, PAGE_HEIGHT - 140)
    
    p.drawString(70, PAGE_HEIGHT - 156, "FECHA:")
    p.line(110, PAGE_HEIGHT - 158, 200, PAGE_HEIGHT - 158)
    
    p.drawString(215, PAGE_HEIGHT - 156, "GRUPO:")
    p.line(260, PAGE_HEIGHT - 158, 310, PAGE_HEIGHT - 158)

    # Student ID (Matrícula) Section
    p.setFont("Helvetica-Bold", 8.5)
    p.drawString(345, PAGE_HEIGHT - 54, "MATRÍCULA / CÓDIGO:")
    
    id_start_x = 345.0
    id_start_y = 665.0
    id_col_w = 20.0
    id_row_h = 14.5
    
    for c in range(6):
        bx = id_start_x + c * id_col_w
        p.rect(bx - 7, PAGE_HEIGHT - 74, 14, 14, stroke=1, fill=0)
    
    p.setFont("Helvetica", 6.5)
    for c in range(6):
        col_x = id_start_x + c * id_col_w
        for digit in range(10):
            pt_y = id_start_y - digit * id_row_h
            p.setStrokeColor(colors.black)
            p.setLineWidth(0.6)
            p.circle(col_x, pt_y, 5.0, stroke=1, fill=0)
            p.drawString(col_x - 1.8, pt_y - 2.2, str(digit))

    # Divider line
    p.setStrokeColor(colors.lightgrey)
    p.setLineWidth(1)
    p.line(CORNER_MARGIN + 10, PAGE_HEIGHT - 172, PAGE_WIDTH - CORNER_MARGIN - 10, PAGE_HEIGHT - 172)

    # 4. Questions Grid
    layout = get_layout_config(total_questions, options_count)
    num_cols = layout["num_cols"]
    per_col = layout["per_col"]
    
    grid_top_y = 460.0
    col_width = (PAGE_WIDTH - 90.0) / num_cols
    row_height = min(17.5, (grid_top_y - 60.0) / per_col)
    opt_labels = ["A", "B", "C", "D", "E"][:options_count]
    opt_spacing = 16.5
    bubble_radius = 5.2
    
    q_num = 1
    for c in range(num_cols):
        col_x = 48.0 + c * col_width
        
        # Column Header (A B C D E)
        p.setFont("Helvetica-Bold", 7.5)
        p.setFillColor(colors.gray)
        for opt_idx, opt_letter in enumerate(opt_labels):
            bx = col_x + 24.0 + opt_idx * opt_spacing
            p.drawString(bx - 2.5, grid_top_y + 12, opt_letter)
            
        for r in range(per_col):
            if q_num > total_questions:
                break
            q_y = grid_top_y - r * row_height
            
            p.setFillColor(colors.black)
            p.setFont("Helvetica-Bold", 7.5)
            p.drawRightString(col_x + 16, q_y - 2.5, f"{q_num:02d}")
            
            bubbles_x_start = col_x + 24.0
            for opt_idx, opt_letter in enumerate(opt_labels):
                bx = bubbles_x_start + opt_idx * opt_spacing
                by = q_y
                
                p.setStrokeColor(colors.black)
                p.setLineWidth(0.65)
                p.circle(bx, by, bubble_radius, stroke=1, fill=0)
                p.drawString(bx - 1.8, by - 1.8, opt_letter)
                
            q_num += 1

    # Footer
    p.setFont("Helvetica", 7)
    p.setFillColor(colors.gray)
    p.drawCentredString(PAGE_WIDTH / 2, 14, f"Scantron Móvil • ID: {exam_id} • Hoja Oficial de Calificación")
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer
