// Mobile Camera and Scanning Controller

let activeStream = null;

const scanner = {
  // Elements
  elements: {
    video: document.getElementById('live-video'),
    liveContainer: document.getElementById('live-cam-container'),
    cameraInput: document.getElementById('input-camera-capture'),
    galleryInput: document.getElementById('input-gallery-capture'),
    loadingBox: document.getElementById('loading-box'),
    resultBox: document.getElementById('result-box'),
    activeExamSelect: document.getElementById('select-active-exam'),
    // Result displays
    resStudentId: document.getElementById('res-student-id'),
    resScoreBadge: document.getElementById('res-score-badge'),
    resPercentageBadge: document.getElementById('res-percentage-badge'),
    resCorrectCount: document.getElementById('res-correct-count'),
    resWrongCount: document.getElementById('res-wrong-count'),
    resBlankCount: document.getElementById('res-blank-count'),
    resAnnotatedImg: document.getElementById('res-annotated-img'),
    annotatedWrapper: document.getElementById('annotated-img-wrapper'),
    btnToggleAnnotated: document.getElementById('btn-toggle-annotated-img'),
    resBreakdownList: document.getElementById('res-breakdown-list'),
    resBadgeIcon: document.getElementById('res-badge-icon')
  },

  init() {
    this.bindEvents();
  },

  bindEvents() {
    // Native mobile camera button
    document.getElementById('btn-open-native-camera').addEventListener('click', () => {
      if (!this.checkActiveExam()) return;
      this.elements.cameraInput.click();
    });

    // Gallery picker button
    document.getElementById('btn-open-gallery').addEventListener('click', () => {
      if (!this.checkActiveExam()) return;
      this.elements.galleryInput.click();
    });

    // File inputs change
    this.elements.cameraInput.addEventListener('change', (e) => this.handleFileSelected(e));
    this.elements.galleryInput.addEventListener('change', (e) => this.handleFileSelected(e));

    // Live Camera Stream
    document.getElementById('btn-start-live-cam').addEventListener('click', () => this.startLiveCamera());
    document.getElementById('btn-cancel-live-cam').addEventListener('click', () => this.stopLiveCamera());
    document.getElementById('btn-capture-live-frame').addEventListener('click', () => this.captureLiveFrame());

    // Toggle annotated image view
    this.elements.btnToggleAnnotated.addEventListener('click', () => {
      this.elements.annotatedWrapper.classList.toggle('hidden');
    });

    // Scan next button
    document.getElementById('btn-scan-next').addEventListener('click', () => {
      this.elements.resultBox.classList.add('hidden');
      this.elements.cameraInput.click();
    });
  },

  checkActiveExam() {
    const examId = this.elements.activeExamSelect.value;
    if (!examId) {
      alert("Por favor selecciona o crea un examen primero.");
      return false;
    }
    return true;
  },

  async startLiveCamera() {
    if (!this.checkActiveExam()) return;

    try {
      this.elements.liveContainer.classList.remove('hidden');
      const constraints = {
        video: {
          facingMode: { ideal: "environment" },
          width: { ideal: 1920 },
          height: { ideal: 1080 }
        }
      };

      activeStream = await navigator.mediaDevices.getUserMedia(constraints);
      this.elements.video.srcObject = activeStream;
      await this.elements.video.play();
    } catch (err) {
      console.error("Camera access error:", err);
      alert("No se pudo acceder a la cámara en vivo. Usa la opción 'Tomar Foto con Cámara'.");
      this.stopLiveCamera();
    }
  },

  stopLiveCamera() {
    if (activeStream) {
      activeStream.getTracks().forEach(track => track.stop());
      activeStream = null;
    }
    this.elements.liveContainer.classList.add('hidden');
  },

  captureLiveFrame() {
    const video = this.elements.video;
    if (!video.videoWidth) return;

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob((blob) => {
      this.stopLiveCamera();
      if (blob) {
        this.uploadAndProcess(blob);
      }
    }, 'image/jpeg', 0.92);
  },

  handleFileSelected(event) {
    const file = event.target.files[0];
    if (!file) return;
    this.uploadAndProcess(file);
    // Reset input
    event.target.value = '';
  },

  async uploadAndProcess(fileBlob) {
    const examId = this.elements.activeExamSelect.value;
    if (!examId) return;

    // Show loading
    this.elements.resultBox.classList.add('hidden');
    this.elements.loadingBox.classList.remove('hidden');

    const formData = new FormData();
    formData.append('file', fileBlob, 'scan.jpg');

    try {
      const response = await fetch(`/api/exams/${examId}/scan`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Error al procesar el examen.");
      }

      const result = await response.json();
      this.displayResults(result);

      // Trigger app refresh to update stats and results tab
      if (window.app) {
        window.app.loadResults(examId);
        window.app.loadExams();
      }
    } catch (err) {
      console.error(err);
      alert("⚠️ Error en escaneo:\n" + err.message + "\n\nAsegúrate de que la hoja esté iluminada y se vean las 4 esquinas negras.");
    } finally {
      this.elements.loadingBox.classList.add('hidden');
    }
  },

  displayResults(res) {
    this.elements.resStudentId.textContent = `Matrícula: ${res.student_id}`;
    this.elements.resScoreBadge.textContent = `${res.score} / ${res.total_possible}`;
    this.elements.resPercentageBadge.textContent = `${res.percentage}%`;

    this.elements.resCorrectCount.textContent = res.correct_count;
    this.elements.resWrongCount.textContent = res.wrong_count;
    this.elements.resBlankCount.textContent = res.blank_count;

    // Badge color according to passing score (>=60%)
    const passed = res.percentage >= 60.0;
    if (passed) {
      this.elements.resScoreBadge.className = "text-xl font-extrabold text-emerald-400";
      this.elements.resBadgeIcon.className = "w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold";
    } else {
      this.elements.resScoreBadge.className = "text-xl font-extrabold text-rose-400";
      this.elements.resBadgeIcon.className = "w-8 h-8 rounded-full bg-rose-500/20 text-rose-400 flex items-center justify-center font-bold";
    }

    // Set annotated image
    if (res.annotated_image_b64) {
      this.elements.resAnnotatedImg.src = res.annotated_image_b64;
    }

    // Question breakdown list
    this.elements.resBreakdownList.innerHTML = '';
    res.question_details.forEach(item => {
      const row = document.createElement('div');
      row.className = "flex items-center justify-between p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-[11px]";
      
      let statusBadge = "";
      if (item.status === "correct") {
        statusBadge = `<span class="text-emerald-400 font-bold">✓ Opción ${item.student_answer}</span>`;
      } else if (item.status === "wrong") {
        statusBadge = `<span class="text-rose-400 font-medium">Marcó ${item.student_answer || '?'} (Correcta: ${item.correct_answer})</span>`;
      } else if (item.status === "multiple") {
        statusBadge = `<span class="text-amber-400 font-medium">Múltiples marcas (Correcta: ${item.correct_answer})</span>`;
      } else {
        statusBadge = `<span class="text-slate-500 font-medium">En blanco (Correcta: ${item.correct_answer})</span>`;
      }

      row.innerHTML = `
        <span class="font-bold text-slate-300">Pregunta ${item.question}:</span>
        <div>${statusBadge}</div>
      `;
      this.elements.resBreakdownList.appendChild(row);
    });

    // Show result card
    this.elements.resultBox.classList.remove('hidden');
    this.elements.resultBox.scrollIntoView({ behavior: 'smooth' });
    lucide.createIcons();
  }
};

document.addEventListener('DOMContentLoaded', () => scanner.init());
