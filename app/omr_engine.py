import cv2
import numpy as np
import base64
from typing import Dict, List, Tuple, Optional, Any
from app.sheet_generator import get_bubble_normalized_coords, PAGE_WIDTH, PAGE_HEIGHT

WARPED_WIDTH = 1200
WARPED_HEIGHT = int(WARPED_WIDTH * (PAGE_HEIGHT / PAGE_WIDTH)) # 1553 px

def decode_image_bytes(image_bytes: bytes) -> np.ndarray:
    """Decode raw image bytes to OpenCV BGR image."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("No se pudo decodificar la imagen proporcionada.")
    return img

def order_points(pts: np.ndarray) -> np.ndarray:
    """
    Orders 4 points as: [Top-Left, Top-Right, Bottom-Right, Bottom-Left]
    """
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)] # Top-Left has smallest sum
    rect[2] = pts[np.argmax(s)] # Bottom-Right has largest sum

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)] # Top-Right has smallest difference
    rect[3] = pts[np.argmax(diff)] # Bottom-Left has largest difference
    return rect

def find_page_corners(img: np.ndarray) -> Optional[np.ndarray]:
    """
    Finds the 4 corners of the answer sheet.
    First tries to detect the 4 calibration corner squares.
    If not found, falls back to detecting the largest quadrilateral page contour.
    """
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # 1. Try finding corner square markers
    # Threshold for dark blocks
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 10
    )
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    img_area = w * h
    candidate_centers = []
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        # Looking for squares between 0.03% and 3.0% of total image area
        if 0.0003 * img_area < area < 0.03 * img_area:
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
            if len(approx) == 4:
                (x, y, cw, ch) = cv2.boundingRect(approx)
                aspect_ratio = cw / float(ch)
                if 0.7 <= aspect_ratio <= 1.35:
                    M = cv2.moments(cnt)
                    if M["m00"] != 0:
                        cx = M["m10"] / M["m00"]
                        cy = M["m01"] / M["m00"]
                        candidate_centers.append((cx, cy))
                        
    if len(candidate_centers) >= 4:
        # Group candidates into 4 quadrants
        mid_x = w / 2.0
        mid_y = h / 2.0
        tl_list = [p for p in candidate_centers if p[0] < mid_x and p[1] < mid_y]
        tr_list = [p for p in candidate_centers if p[0] >= mid_x and p[1] < mid_y]
        bl_list = [p for p in candidate_centers if p[0] < mid_x and p[1] >= mid_y]
        br_list = [p for p in candidate_centers if p[0] >= mid_x and p[1] >= mid_y]
        
        if tl_list and tr_list and bl_list and br_list:
            # Pick extreme points in each quadrant
            tl = min(tl_list, key=lambda p: p[0] + p[1])
            tr = min(tr_list, key=lambda p: -p[0] + p[1])
            bl = min(bl_list, key=lambda p: p[0] - p[1])
            br = max(br_list, key=lambda p: p[0] + p[1])
            return np.array([tl, tr, br, bl], dtype="float32")

    # 2. Fallback: Find largest 4-sided contour (the entire page)
    edged = cv2.Canny(blurred, 40, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    edged = cv2.dilate(edged, kernel, iterations=1)
    
    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
    
    for cnt in contours:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4 and cv2.contourArea(cnt) > 0.25 * img_area:
            pts = approx.reshape(4, 2)
            return order_points(pts)

    # 3. If image was already cropped or filled screen
    return np.array([
        [0, 0],
        [w - 1, 0],
        [w - 1, h - 1],
        [0, h - 1]
    ], dtype="float32")

def warp_perspective(img: np.ndarray, corners: np.ndarray) -> np.ndarray:
    """
    Warps image to standard 1200 x 1553 dimensions using perspective transform.
    """
    rect = order_points(corners)
    dst = np.array([
        [0, 0],
        [WARPED_WIDTH - 1, 0],
        [WARPED_WIDTH - 1, WARPED_HEIGHT - 1],
        [0, WARPED_HEIGHT - 1]
    ], dtype="float32")
    
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(img, M, (WARPED_WIDTH, WARPED_HEIGHT))
    return warped

def evaluate_bubble(thresh_img: np.ndarray, center_x: int, center_y: int, radius: int) -> float:
    """
    Calculates the fill ratio of a circle bubble.
    thresh_img has black background (0) and white filled ink/pencil (255).
    Returns ratio of filled pixels inside inner core (0.0 to 1.0).
    """
    # Create mask of inner 75% of the circle to ignore circular border ink
    inner_r = max(3, int(radius * 0.75))
    mask = np.zeros(thresh_img.shape, dtype=np.uint8)
    cv2.circle(mask, (center_x, center_y), inner_r, 255, -1)
    
    total_circle_pixels = cv2.countNonZero(mask)
    if total_circle_pixels == 0:
        return 0.0
        
    filled_pixels = cv2.countNonZero(cv2.bitwise_and(thresh_img, thresh_img, mask=mask))
    return float(filled_pixels) / float(total_circle_pixels)

def process_omr_sheet(
    image_bytes: bytes,
    exam: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Full Computer Vision Pipeline:
    1. Decode image
    2. Detect corners and warp
    3. Sample student ID bubbles
    4. Sample question bubbles
    5. Grade against answer key
    6. Generate visual marked sheet with highlights
    """
    img = decode_image_bytes(image_bytes)
    total_questions = exam.get("total_questions", 30)
    options_count = exam.get("options_per_question", 4)
    answer_key = exam.get("answer_key", {})
    points_per_q = exam.get("points_per_question", 1.0)
    penalty_wrong = exam.get("penalty_per_wrong", 0.0)

    # 1. Warp perspective
    corners = find_page_corners(img)
    warped = warp_perspective(img, corners)
    
    # 2. Preprocess warped image for bubble detection
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    
    # Adaptive threshold: filled bubbles (darker than paper) become white (255)
    # Background paper becomes black (0)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 12
    )

    # Coordinates map
    coords = get_bubble_normalized_coords(total_questions, options_count)
    bubble_radius_px = int(5.2 / PAGE_WIDTH * WARPED_WIDTH) # approx 10px

    # 3. Read Student ID (6 digits)
    student_id_digits = []
    id_map = coords["student_id"]
    for col_idx in range(6):
        col_scores = []
        for digit in range(10):
            if col_idx in id_map and digit in id_map[col_idx]:
                u, v = id_map[col_idx][digit]
                cx, cy = int(u * WARPED_WIDTH), int(v * WARPED_HEIGHT)
                ratio = evaluate_bubble(thresh, cx, cy, bubble_radius_px)
                col_scores.append((digit, ratio))
                
        if col_scores:
            col_scores.sort(key=lambda x: x[1], reverse=True)
            top_digit, top_ratio = col_scores[0]
            # Threshold for student ID bubble
            if top_ratio > 0.35:
                student_id_digits.append(str(top_digit))
            else:
                student_id_digits.append("-")
                
    detected_student_id = "".join(student_id_digits)
    if detected_student_id == "------":
        detected_student_id = "ANÓNIMO"

    # 4. Read Questions and Grade
    annotated = warped.copy()
    student_answers = {}
    question_details = []
    correct_count = 0
    wrong_count = 0
    blank_count = 0

    FILL_THRESHOLD = 0.38
    q_map = coords["questions"]

    for q_num in range(1, total_questions + 1):
        q_str = str(q_num)
        correct_ans = answer_key.get(q_str, "").upper()
        
        if q_num not in q_map:
            continue
            
        opt_scores = []
        for opt_letter, (u, v) in q_map[q_num].items():
            cx = int(u * WARPED_WIDTH)
            cy = int(v * WARPED_HEIGHT)
            fill_ratio = evaluate_bubble(thresh, cx, cy, bubble_radius_px)
            opt_scores.append((opt_letter, fill_ratio, (cx, cy)))

        # Sort options by fill ratio descending
        opt_scores.sort(key=lambda x: x[1], reverse=True)
        top_opt, top_score, top_pt = opt_scores[0]
        second_score = opt_scores[1][1] if len(opt_scores) > 1 else 0.0

        student_choice = None
        status = "blank"

        if top_score >= FILL_THRESHOLD:
            # Check for multiple marks
            if second_score >= FILL_THRESHOLD and (top_score - second_score) < 0.15:
                status = "multiple"
                student_choice = "MULTIPLE"
            else:
                student_choice = top_opt
                if correct_ans and student_choice == correct_ans:
                    status = "correct"
                else:
                    status = "wrong"
        else:
            status = "blank"
            student_choice = None

        is_correct = (status == "correct")
        if status == "correct":
            correct_count += 1
        elif status in ["wrong", "multiple"]:
            wrong_count += 1
        else:
            blank_count += 1

        student_answers[q_str] = student_choice or ""
        question_details.append({
            "question": q_num,
            "correct_answer": correct_ans,
            "student_answer": student_choice,
            "is_correct": is_correct,
            "status": status
        })

        # Draw Annotations on Annotated Image:
        # Green for correct, Red for student wrong, Yellow for correct answer indicator
        for opt_letter, score, pt in opt_scores:
            cx, cy = pt
            if opt_letter == correct_ans:
                if status == "correct":
                    # Mark green circle
                    cv2.circle(annotated, (cx, cy), bubble_radius_px + 3, (0, 200, 0), 2)
                    cv2.putText(annotated, "✓", (cx + 12, cy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 180, 0), 2)
                else:
                    # Mark yellow circle to show what the correct answer was
                    cv2.circle(annotated, (cx, cy), bubble_radius_px + 3, (0, 215, 255), 2)
            
            if opt_letter == student_choice and status != "correct":
                # Mark red circle with X
                cv2.circle(annotated, (cx, cy), bubble_radius_px + 3, (0, 0, 230), 2)
                cv2.line(annotated, (cx - 5, cy - 5), (cx + 5, cy + 5), (0, 0, 230), 2)
                cv2.line(annotated, (cx + 5, cy - 5), (cx - 5, cy + 5), (0, 0, 230), 2)

    # 5. Calculate Score
    raw_score = (correct_count * points_per_q) - (wrong_count * penalty_wrong)
    score = max(0.0, round(raw_score, 2))
    total_possible = round(total_questions * points_per_q, 2)
    percentage = round((score / total_possible * 100.0) if total_possible > 0 else 0.0, 1)

    # 6. Draw Score Banner on Annotated Image
    banner_bg = (245, 245, 245)
    cv2.rectangle(annotated, (WARPED_WIDTH - 380, 50), (WARPED_WIDTH - 30, 130), banner_bg, -1)
    border_color = (0, 180, 0) if percentage >= 60.0 else (0, 0, 220)
    cv2.rectangle(annotated, (WARPED_WIDTH - 380, 50), (WARPED_WIDTH - 30, 130), border_color, 2)
    
    cv2.putText(annotated, f"CALIFICACION: {score}/{total_possible} ({percentage}%)", 
                (WARPED_WIDTH - 365, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (20, 20, 20), 2)
    cv2.putText(annotated, f"Aciertos: {correct_count}  Fallos: {wrong_count}  Blanco: {blank_count}", 
                (WARPED_WIDTH - 365, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (80, 80, 80), 1)
    cv2.putText(annotated, f"Matricula: {detected_student_id}", 
                (WARPED_WIDTH - 365, 122), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (100, 100, 100), 1)

    # 7. Convert annotated image to base64 JPEG
    _, enc_img = cv2.imencode(".jpg", annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
    annotated_b64 = f"data:image/jpeg;base64,{base64.b64encode(enc_img).decode('utf-8')}"

    return {
        "student_id": detected_student_id,
        "score": score,
        "total_possible": total_possible,
        "percentage": percentage,
        "correct_count": correct_count,
        "wrong_count": wrong_count,
        "blank_count": blank_count,
        "student_answers": student_answers,
        "question_details": question_details,
        "annotated_image_b64": annotated_b64
    }
