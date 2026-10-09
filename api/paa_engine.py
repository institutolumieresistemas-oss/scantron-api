import cv2
import numpy as np
import base64
import math
from typing import Dict, List, Tuple, Optional, Any

# A4 Standard Processing Dimensions (as defined in MotorOMR.cs)
A4_WIDTH = 2480
A4_HEIGHT = 3508
RADIO_DIBUJO = 13
UMBRAL_LLENADO = 0.50

# TABLA OFICIAL PAA LECTURA Y REDACCIÓN (70 reactivos en total -> Escala 200 a 800)
TABLA_LECTURA = {
    70: 800, 69: 790, 68: 780, 67: 771, 66: 761, 65: 752, 64: 742, 63: 733, 62: 724, 61: 715,
    60: 707, 59: 698, 58: 689, 57: 681, 56: 672, 55: 663, 54: 655, 53: 647, 52: 638, 51: 630,
    50: 621, 49: 613, 48: 605, 47: 596, 46: 588, 45: 580, 44: 571, 43: 563, 42: 554, 41: 546,
    40: 538, 39: 529, 38: 521, 37: 512, 36: 504, 35: 495, 34: 487, 33: 479, 32: 470, 31: 462,
    30: 453, 29: 445, 28: 436, 27: 428, 26: 419, 25: 411, 24: 402, 23: 394, 22: 385, 21: 377,
    20: 363, 19: 360, 18: 352, 17: 343, 16: 335, 15: 326, 14: 318, 13: 310, 12: 301, 11: 293,
    10: 284, 9: 276, 8: 268, 7: 259, 6: 251, 5: 242, 4: 234, 3: 225, 2: 217, 1: 208, 0: 200
}

# TABLA OFICIAL PAA MATEMÁTICAS (55 reactivos en total -> Escala 200 a 800)
TABLA_MATE = {
    55: 800, 54: 795, 53: 787, 52: 778, 51: 769, 50: 759, 49: 749, 48: 739, 47: 730, 46: 721,
    45: 712, 44: 704, 43: 696, 42: 688, 41: 680, 40: 673, 39: 665, 38: 658, 37: 650, 36: 642,
    35: 634, 34: 626, 33: 617, 32: 608, 31: 598, 30: 588, 29: 577, 28: 566, 27: 555, 26: 543,
    25: 530, 24: 518, 23: 504, 22: 491, 21: 477, 20: 463, 19: 449, 18: 434, 17: 419, 16: 405,
    15: 390, 14: 375, 13: 360, 12: 342, 11: 330, 10: 315, 9: 300, 8: 285, 7: 271, 6: 258,
    5: 245, 4: 232, 3: 222, 2: 212, 1: 205, 0: 200
}

class PAAQuestionConfig:
    def __init__(self, q_id: int, num_visual: int, seccion: str, area: str,
                 x: int, y: int, opciones: int, espacio_x: int, espacio_y: int):
        self.id = q_id
        self.num_visual = num_visual
        self.seccion = seccion  # "LECTURA", "REDACCION", "MATEMATICAS", "MATEMATICASGRID"
        self.area = area        # "VERBAL", "MATEMATICAS"
        self.x = x
        self.y = y
        self.opciones = opciones
        self.espacio_x = espacio_x
        self.espacio_y = espacio_y

def generar_plantilla_paa() -> List[PAAQuestionConfig]:
    """
    Construye la lista exacta de 125 reactivos PAA con sus coordenadas fijas
    idénticas a PlantillaExamen.cs de scanner lumi.
    """
    preguntas = []

    # 1. LECTURA (45 preguntas: 1 a 45)
    cols_lectura = [897, 1229, 1566, 1899, 2230]
    base_y_lectura = 107
    filas_lectura = 9
    sep_y = 53
    espacio_x = 60
    n_pregunta = 1
    for x in cols_lectura:
        for i in range(filas_lectura):
            preguntas.append(PAAQuestionConfig(
                q_id=len(preguntas),
                num_visual=n_pregunta,
                seccion="LECTURA",
                area="VERBAL",
                x=x,
                y=base_y_lectura + (i * sep_y),
                opciones=4,
                espacio_x=espacio_x,
                espacio_y=sep_y
            ))
            n_pregunta += 1

    # 2. REDACCIÓN (25 preguntas: 46 a 70)
    cols_redaccion = [897, 1229, 1566, 1899, 2230]
    base_y_redaccion = 723
    filas_redaccion = 5
    for x in cols_redaccion:
        for i in range(filas_redaccion):
            preguntas.append(PAAQuestionConfig(
                q_id=len(preguntas),
                num_visual=n_pregunta,
                seccion="REDACCION",
                area="VERBAL",
                x=x,
                y=base_y_redaccion + (i * sep_y),
                opciones=4,
                espacio_x=espacio_x,
                espacio_y=sep_y
            ))
            n_pregunta += 1

    # 3. MATEMÁTICAS OPCIÓN MÚLTIPLE (45 preguntas: 71 a 115)
    cols_mate = [908, 1241, 1561]
    base_y_mate = 1128
    filas_mate = 15
    for x in cols_mate:
        for i in range(filas_mate):
            preguntas.append(PAAQuestionConfig(
                q_id=len(preguntas),
                num_visual=n_pregunta,
                seccion="MATEMATICAS",
                area="MATEMATICAS",
                x=x,
                y=base_y_mate + (i * sep_y),
                opciones=4,
                espacio_x=espacio_x,
                espacio_y=sep_y
            ))
            n_pregunta += 1

    # 4. GRID MATEMÁTICAS 1 (2 reactivos: 116 y 117)
    cols_grid1 = [1931, 2248]
    base_y_grid1 = 1238
    for x in cols_grid1:
        preguntas.append(PAAQuestionConfig(
            q_id=len(preguntas),
            num_visual=n_pregunta,
            seccion="MATEMATICASGRID",
            area="MATEMATICAS",
            x=x,
            y=base_y_grid1,
            opciones=12,
            espacio_x=espacio_x,
            espacio_y=sep_y
        ))
        n_pregunta += 1

    # 5. GRID MATEMÁTICAS 2 (8 reactivos: 118 a 125)
    cols_grid2 = [138, 450, 759, 1071, 1365, 1683, 1989, 2303]
    base_y_grid2 = 2071
    for x in cols_grid2:
        preguntas.append(PAAQuestionConfig(
            q_id=len(preguntas),
            num_visual=n_pregunta,
            seccion="MATEMATICASGRID",
            area="MATEMATICAS",
            x=x,
            y=base_y_grid2,
            opciones=12,
            espacio_x=espacio_x,
            espacio_y=sep_y
        ))
        n_pregunta += 1

    return preguntas

# Singleton de la plantilla
PLANTILLA_PAA = generar_plantilla_paa()

def alinear_y_normalizar_a4(src: np.ndarray) -> np.ndarray:
    """
    Alinea la imagen al tamaño A4 (2480 x 3508) buscando los 4 marcadores
    de esquina, idéntico al método AlinearYNormalizar de MotorOMR.cs.
    """
    gray = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
    _, bin_img = cv2.threshold(gray, 110, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(bin_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidate_centers = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if 500 < area < 20000:
            x, y, w, h = cv2.boundingRect(cnt)
            candidate_centers.append((x + w / 2.0, y + h / 2.0))

    if len(candidate_centers) >= 4:
        # Puntos: TL, TR, BR, BL
        tl = min(candidate_centers, key=lambda p: p[0] + p[1])
        tr = min(candidate_centers, key=lambda p: -p[0] + p[1])
        br = max(candidate_centers, key=lambda p: p[0] + p[1])
        bl = max(candidate_centers, key=lambda p: -p[0] + p[1])

        origen = np.array([tl, tr, br, bl], dtype="float32")
        destino = np.array([
            [0, 0],
            [A4_WIDTH - 1, 0],
            [A4_WIDTH - 1, A4_HEIGHT - 1],
            [0, A4_HEIGHT - 1]
        ], dtype="float32")

        matrix = cv2.getPerspectiveTransform(origen, destino)
        warped = cv2.warpPerspective(src, matrix, (A4_WIDTH, A4_HEIGHT))
        return warped

    return cv2.resize(src, (A4_WIDTH, A4_HEIGHT))

def obtener_llenado_burbuja(gris: np.ndarray, x: int, y: int) -> float:
    """
    Calcula el porcentaje de llenado usando recorte Otsu (igual a MotorOMR.cs).
    """
    h, w = gris.shape[:2]
    x1 = max(0, min(x - RADIO_DIBUJO, w - 1))
    y1 = max(0, min(y - RADIO_DIBUJO, h - 1))
    x2 = max(0, min(x + RADIO_DIBUJO, w - 1))
    y2 = max(0, min(y + RADIO_DIBUJO, h - 1))

    if x2 <= x1 or y2 <= y1:
        return 0.0

    recorte = gris[y1:y2, x1:x2]
    _, binaria = cv2.threshold(recorte, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    total_pix = binaria.shape[0] * binaria.shape[1]
    if total_pix == 0:
        return 0.0
    return float(cv2.countNonZero(binaria)) / float(total_pix)

def revisar_zona_dudosa(gris: np.ndarray, x: int, y: int) -> bool:
    """
    Revisa el núcleo interno de la burbuja (radio reducido a la mitad)
    para confirmar si fue rellenado o solo tiene el borde (igual a MotorOMR.cs).
    """
    radio_nucleo = max(4, RADIO_DIBUJO // 2)
    h, w = gris.shape[:2]
    x1 = max(0, min(x - radio_nucleo, w - 1))
    y1 = max(0, min(y - radio_nucleo, h - 1))
    x2 = max(0, min(x + radio_nucleo, w - 1))
    y2 = max(0, min(y + radio_nucleo, h - 1))

    if x2 <= x1 or y2 <= y1:
        return False

    recorte = gris[y1:y2, x1:x2]
    _, binaria = cv2.threshold(recorte, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    total_pix = binaria.shape[0] * binaria.shape[1]
    if total_pix == 0:
        return False
    return (float(cv2.countNonZero(binaria)) / float(total_pix)) >= 0.40

def detectar_llenado(gris: np.ndarray, lienzo: np.ndarray, x: int, y: int) -> bool:
    """
    Detecta si la burbuja está marcada y la dibuja sobre el lienzo de inspección.
    """
    llenado = obtener_llenado_burbuja(gris, x, y)
    if llenado > UMBRAL_LLENADO:
        cv2.circle(lienzo, (x, y), RADIO_DIBUJO, (0, 0, 255), -1)
        return True
    elif llenado > 0.35:
        corregida = revisar_zona_dudosa(gris, x, y)
        color = (0, 0, 255) if corregida else (0, 255, 255)
        cv2.circle(lienzo, (x, y), RADIO_DIBUJO, color, -1)
        return corregida
    else:
        cv2.circle(lienzo, (x, y), RADIO_DIBUJO, (0, 255, 0), 1)
        return False

def analizar_reactivo(gris: np.ndarray, lienzo: np.ndarray, cfg: PAAQuestionConfig) -> str:
    """
    Lee las marcas de un reactivo. Si es opción múltiple regresa A, B, C, D, ?, X.
    Si es Grid Matemático regresa el valor numérico (ej. '1/2', '2.5', '18', etc.).
    """
    dist_x = cfg.espacio_x
    dist_y = cfg.espacio_y

    if cfg.seccion != "MATEMATICASGRID":
        detectados = []
        for i in range(cfg.opciones):
            x = cfg.x + (i * dist_x)
            y = cfg.y
            if detectar_llenado(gris, lienzo, x, y):
                detectados.append(i)

        if len(detectados) == 0:
            return "?"
        if len(detectados) > 1:
            return "X"
        return chr(ord('A') + detectados[0])
    else:
        # LÓGICA GRID MATEMÁTICAS (4 columnas, 12 filas)
        resultado_grid = ""
        se_encontro_vacio = False
        invalido = False
        x_inicial_real = cfg.x - dist_x

        for c in range(4):
            detectados_col = []
            x_col = x_inicial_real + (c * dist_x)

            for f in range(12):
                # Huecos estructurales del formato College Board / UDG:
                if f == 0 and (c == 0 or c == 3):
                    continue
                if f == 2 and c == 0:
                    continue

                y_fila = cfg.y + (f * dist_y)
                if detectar_llenado(gris, lienzo, x_col, y_fila):
                    detectados_col.append(f)

            if len(detectados_col) > 1:
                invalido = True
                continue

            if len(detectados_col) == 0:
                se_encontro_vacio = True
                resultado_grid += "-"
                continue

            if se_encontro_vacio:
                invalido = True

            idx = detectados_col[0]
            if idx == 0:
                resultado_grid += "/"
            elif idx == 1:
                resultado_grid += "."
            else:
                resultado_grid += str(idx - 2)

        if resultado_grid == "----":
            return "?"
        if invalido:
            return "X"

        return resultado_grid.rstrip("-")

def try_evaluar_matematica(texto: str) -> Optional[float]:
    """
    Convierte una cadena como '1/2', '3.5', '.75' a valor float.
    """
    if not texto or texto in ["?", "X"]:
        return None
    texto = texto.strip().replace(",", ".")
    try:
        if "/" in texto:
            partes = texto.split("/")
            if len(partes) == 2:
                num = float(partes[0])
                den = float(partes[1])
                if den == 0:
                    return None
                return num / den
        if texto.startswith("."):
            texto = "0" + texto
        return float(texto)
    except Exception:
        return None

def es_mismo_valor_grid(resp_base: str, resp_alumno: str) -> bool:
    """
    Evalúa equivalencia matemática (ej. '1/2' == '0.5' == '.50').
    """
    if resp_base == resp_alumno:
        return True
    val_base = try_evaluar_matematica(resp_base)
    val_alumno = try_evaluar_matematica(resp_alumno)
    if val_base is not None and val_alumno is not None:
        return abs(val_base - val_alumno) < 0.0001
    return False

def obtener_puntaje_escalado(aciertos: int, tabla: Dict[int, int]) -> int:
    """
    Convierte la cantidad de aciertos al puntaje oficial College Board (200 a 800).
    """
    if aciertos <= 0:
        return 200
    if aciertos in tabla:
        return tabla[aciertos]
    max_aciertos = max(tabla.keys())
    if aciertos >= max_aciertos:
        return tabla[max_aciertos]
    return 800

def procesar_examen_paa(
    image_bytes: bytes,
    clave_respuestas: Dict[str, str]
) -> Dict[str, Any]:
    """
    Flujo de calificación completo del Examen PAA 125 reactivos:
    1. Alineación A4 (2480 x 3508)
    2. Lectura de las 125 preguntas y grids matemáticos
    3. Calificación con reglas PAA y tablas oficiales 200-800
    4. Generación de imagen anotada con el banner oficial de College Board
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    raw = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if raw is None:
        raise ValueError("No se pudo decodificar la imagen.")

    normalizada = alinear_y_normalizar_a4(raw)
    lienzo = normalizada.copy()
    gris = cv2.cvtColor(normalizada, cv2.COLOR_BGR2GRAY)

    respuestas_alumno = {}
    detalles_preguntas = []
    verbal_aciertos = 0
    mate_aciertos = 0
    correct_count = 0
    wrong_count = 0
    blank_count = 0

    for cfg in PLANTILLA_PAA:
        q_num = cfg.num_visual
        q_str = str(q_num)
        marca_alumno = analizar_reactivo(gris, lienzo, cfg)
        respuestas_alumno[q_str] = marca_alumno

        resp_profe = clave_respuestas.get(q_str, "").strip().upper()

        es_correcto = False
        if marca_alumno in ["?", "X"] or resp_profe in ["?", "X", ""]:
            es_correcto = False
        elif cfg.seccion == "MATEMATICASGRID":
            es_correcto = es_mismo_valor_grid(resp_profe, marca_alumno)
        else:
            es_correcto = (marca_alumno == resp_profe)

        if es_correcto:
            correct_count += 1
            if cfg.area == "VERBAL":
                verbal_aciertos += 1
            else:
                mate_aciertos += 1
        elif marca_alumno == "?":
            blank_count += 1
        else:
            wrong_count += 1

        detalles_preguntas.append({
            "question": q_num,
            "section": cfg.seccion,
            "area": cfg.area,
            "correct_answer": resp_profe,
            "student_answer": marca_alumno,
            "is_correct": es_correcto,
            "status": "correct" if es_correcto else ("blank" if marca_alumno == "?" else "wrong")
        })

    # Cálculo oficial de escalas College Board PAA
    puntaje_verbal = obtener_puntaje_escalado(verbal_aciertos, TABLA_LECTURA)
    puntaje_mate = obtener_puntaje_escalado(mate_aciertos, TABLA_MATE)
    puntaje_total_paa = puntaje_verbal + puntaje_mate
    porcentaje = round((correct_count / 125.0) * 100.0, 1)

    # Banner Oficial College Board PAA en la cabecera
    banner_w, banner_h = 1000, 220
    bx1 = A4_WIDTH - banner_w - 60
    by1 = 40
    cv2.rectangle(lienzo, (bx1, by1), (bx1 + banner_w, by1 + banner_h), (25, 25, 25), -1)
    border_color = (0, 200, 0) if puntaje_total_paa >= 1000 else (0, 0, 220)
    cv2.rectangle(lienzo, (bx1, by1), (bx1 + banner_w, by1 + banner_h), border_color, 4)

    cv2.putText(lienzo, f"PUNTAJE GLOBAL PAA: {puntaje_total_paa} / 1600",
                (bx1 + 30, by1 + 60), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 230, 255), 3)
    cv2.putText(lienzo, f"Lectura y Redaccion: {puntaje_verbal} pts ({verbal_aciertos}/70)",
                (bx1 + 30, by1 + 115), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    cv2.putText(lienzo, f"Matematicas (inc. Grid): {puntaje_mate} pts ({mate_aciertos}/55)",
                (bx1 + 30, by1 + 160), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    cv2.putText(lienzo, f"Total Aciertos: {correct_count}/125 ({porcentaje}%) | Errores: {wrong_count}",
                (bx1 + 30, by1 + 200), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (180, 180, 180), 2)

    # Convertir a imagen JPEG en base64 (calidad 80 para transmisión fluida)
    _, enc_img = cv2.imencode(".jpg", lienzo, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    annotated_b64 = f"data:image/jpeg;base64,{base64.b64encode(enc_img).decode('utf-8')}"

    return {
        "is_paa": True,
        "student_id": "PAA-ALUMNO",
        "score": puntaje_total_paa,
        "total_possible": 1600,
        "percentage": porcentaje,
        "puntaje_verbal": puntaje_verbal,
        "puntaje_mate": puntaje_mate,
        "puntaje_total_paa": puntaje_total_paa,
        "verbal_aciertos": verbal_aciertos,
        "mate_aciertos": mate_aciertos,
        "correct_count": correct_count,
        "wrong_count": wrong_count,
        "blank_count": blank_count,
        "student_answers": respuestas_alumno,
        "question_details": detalles_preguntas,
        "annotated_image_b64": annotated_b64
    }

def scan_master_paa_sheet(image_bytes: bytes) -> Dict[str, Any]:
    """
    Escanea la hoja maestra de 125 reactivos con cámara o escáner
    y extrae automáticamente las respuestas correctas marcadas por el profesor.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    raw = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if raw is None:
        raise ValueError("No se pudo decodificar la imagen.")

    normalizada = alinear_y_normalizar_a4(raw)
    lienzo = normalizada.copy()
    gris = cv2.cvtColor(normalizada, cv2.COLOR_BGR2GRAY)

    respuestas_maestras = {}
    total_detectadas = 0

    for cfg in PLANTILLA_PAA:
        q_str = str(cfg.num_visual)
        marca = analizar_reactivo(gris, lienzo, cfg)
        respuestas_maestras[q_str] = "" if marca in ["?", "X"] else marca
        if respuestas_maestras[q_str]:
            total_detectadas += 1

    _, enc_img = cv2.imencode(".jpg", lienzo, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    annotated_b64 = f"data:image/jpeg;base64,{base64.b64encode(enc_img).decode('utf-8')}"

    return {
        "is_paa": True,
        "detected_answers": respuestas_maestras,
        "total_detected": total_detectadas,
        "total_questions": 125,
        "annotated_image_b64": annotated_b64
    }
