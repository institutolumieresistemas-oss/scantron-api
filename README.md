# 📱 Scantron Móvil - Sistema OMR para Celulares

Sistema de corrección óptica de exámenes (**Optical Mark Recognition**) diseñado para operar desde el navegador de cualquier teléfono móvil (Android / iOS) sin requerir equipos costosos.

Optimizado para desplegarse fácilmente en **Railway** (backend y frontend integrados) y enlazable con tu dominio en **Hostinger**.

---

## 🚀 Características Principales

- **📸 Escaneo Móvil de Alta Precisión:**
  - Toma fotos directamente con la cámara del celular (enfoque automático, flash y alta resolución).
  - Incluye visor en vivo con retícula de alineación para guiar al profesor.
- **📐 Visión por Computadora (OpenCV):**
  - Detección de las 4 marcas de esquina de la hoja.
  - Corrección de perspectiva (*Perspective Warp*) para corregir fotos tomadas en ángulo o con inclinación.
  - Umbralización adaptativa (*Adaptive Thresholding*) para medir el porcentaje de llenado de cada burbuja.
- **📄 Generador Dinámico de Plantillas PDF (ReportLab):**
  - Genera hojas de respuesta listas para imprimir en papel tamaño Carta (Letter) o A4.
  - Cantidad de preguntas flexible y configurable: **10, 20, 25, 30, 50, 60, 80 o 100 preguntas**.
  - Opciones personalizables: 3 (A-C), 4 (A-D) o 5 (A-E) opciones.
  - Grilla de Matrícula / Código del estudiante (6 dígitos numéricos).
  - Código QR con los metadatos del examen.
- **📊 Calificación Inmediata y Hoja Marcada:**
  - Calificación instantánea en pantalla al tomar la foto.
  - Generación de la imagen anotada con marcas visuales:
    - 🟢 Círculo verde en respuestas correctas.
    - 🔴 Círculo rojo y tachadura en respuestas incorrectas del alumno.
    - 🟡 Círculo amarillo señalando cuál era la respuesta correcta.
- **📥 Estadísticas y Exportación a Excel:**
  - Cálculo de promedio general del grupo, total de evaluados y porcentaje de aprobación.
  - Exportación con un clic a archivo `.csv` compatible con Microsoft Excel y Google Sheets.
- **📲 PWA (Progressive Web App):**
  - Puede agregarse a la pantalla de inicio del celular como una aplicación nativa.

---

## 🛠️ Estructura del Proyecto

```
Sacntron/
├── app/
│   ├── main.py              # API FastAPI y rutas web
│   ├── omr_engine.py        # Algoritmo de visión por computadora y calibración OMR
│   ├── sheet_generator.py   # Generador vectorial de hojas de respuestas en PDF
│   ├── database.py          # Capa de almacenamiento SQLite
│   ├── models.py            # Modelos Pydantic de validación
│   └── static/              # Frontend web móvil (PWA)
│       ├── index.html       # Interfaz responsive para smartphones
│       ├── scanner.js       # Controlador de cámara y envío de fotos
│       ├── app.js           # Gestor de exámenes, notas y clave interactiva
│       ├── styles.css       # Estilos y retícula de escaneo
│       ├── icon.svg         # Icono de la aplicación
│       └── manifest.json    # Manifiesto PWA para instalación móvil
├── Dockerfile               # Contenedor optimizado para Railway (Python 3.11 + libgl1)
├── railway.json             # Configuración de despliegue en Railway
├── requirements.txt         # Dependencias Python
└── README.md
```

---

## 🌐 Cómo Desplegar en Railway (Paso a Paso)

Railway permite desplegar esta aplicación directamente con su Dockerfile sin configurar servidores manualmente:

1. **Subir este proyecto a un repositorio de GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial Scantron Mobile commit"
   git branch -M main
   git remote add origin https://github.com/TU-USUARIO/scantron-mobil.git
   git push -u origin main
   ```

2. **Crear el servicio en Railway:**
   - Entra a [Railway.app](https://railway.app) e inicia sesión.
   - Presiona **"New Project"** -> **"Deploy from GitHub repo"**.
   - Selecciona el repositorio `scantron-mobil`.
   - Railway detectará automáticamente el archivo `Dockerfile` y construirá la imagen con Python 3.11 y las librerías nativas de OpenCV (`libgl1`, `libglib2.0-0`).

3. **Generar el Dominio Público:**
   - En tu panel de Railway, ve a **Settings** -> **Networking** -> **Generate Domain**.
   - Obtendrás una URL pública segura HTTPS como:  
     `https://scantron-mobil-production.up.railway.app`

4. *(Opcional)* **Conectar tu dominio de Hostinger:**
   - Si tienes tu propio dominio en Hostinger (ejemplo: `miinstituto.com`), ve a la zona DNS de Hostinger y crea un registro:
     - **Tipo:** `CNAME`
     - **Nombre / Subdominio:** `scantron` (o `examenes`)
     - **Destino:** El dominio generado por Railway (ej. `scantron-mobil-production.up.railway.app`).
   - En Railway, ve a **Settings** -> **Custom Domain** y agrega `scantron.miinstituto.com`.

---

## 💻 Ejecución Local (En tu computadora)

1. Instalar las dependencias de Python:
   ```bash
   pip install -r requirements.txt
   ```

2. Iniciar el servidor local:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. Abrir en el navegador de tu computadora o celular (conectado a la misma red WiFi):
   ```
   http://localhost:8000
   ```

---

## 📱 Guía de Uso para el Profesor

1. **Crear Examen:**
   - Ve a la pestaña **Exámenes** y pulsa **"Nuevo"**.
   - Ingresa el título (ej. *Examen de Historia*), define el número de preguntas (ej. 20) y toca las burbujas para fijar la clave de respuestas correctas (A, B, C...).
   - Guarda el examen.
2. **Imprimir las Hojas:**
   - Presiona el botón **"Imprimir Hoja"** para descargar el PDF.
   - Imprímelo en cualquier impresora común tamaño Carta o A4. Reparte las copias a los alumnos.
3. **Escanear y Calificar:**
   - Abre la web en tu celular y pulsa **"Tomar Foto con Cámara"**.
   - Apunta la cámara a la hoja contestada de modo que se vean los 4 cuadros negros de las esquinas.
   - En 1 o 2 segundos verás la calificación en grande (*"18 / 20 • 90%"*), el ID del alumno y la opción de revisar la hoja con los círculos verdes y rojos.
4. **Descargar Calificaciones:**
   - En la pestaña **Notas**, pulsa **"Excel CSV"** para descargar la lista completa de calificaciones para tu registro oficial.
