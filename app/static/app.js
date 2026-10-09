// Main Web Application Controller (API-Connected Architecture + PAA 125 Support)
// Manages: Examen Principal (Tab 1), Calificador OMR en la Nube (Tab 2), and Resultados Cards (Tab 3)

window.app = {
  // Storage Keys
  KEY_MASTER: 'scantron_master_exam',
  KEY_RESULTS: 'scantron_results',
  KEY_API_URL: 'scantron_api_url',

  masterExam: null,
  results: [],

  // Temporary operation holders
  tempApiResult: null,
  tempScannedAnswers: null,
  activeDeletingId: null,
  activeEditingId: null,
  activeEditingAnswers: {},
  masterEditorAnswers: {},

  init() {
    this.loadState();
    this.bindNavigation();
    this.bindApiConfigEvents();
    this.bindMasterExamEvents();
    this.bindGraderEvents();
    this.bindResultModals();
    this.renderAll();
    this.checkApiHealth();
    lucide.createIcons();
  },

  // ================= API CONFIG & HEALTH =================
  getApiUrl() {
    let url = localStorage.getItem(this.KEY_API_URL);
    if (!url || !url.trim()) {
      if (window.location.protocol.startsWith('http')) {
        return window.location.origin;
      }
      return 'http://localhost:8000';
    }
    return url.trim().replace(/\/+$/, '');
  },

  setApiUrl(url) {
    if (!url) {
      localStorage.removeItem(this.KEY_API_URL);
    } else {
      localStorage.setItem(this.KEY_API_URL, url.trim().replace(/\/+$/, ''));
    }
    this.checkApiHealth();
  },

  async checkApiHealth() {
    const dot = document.getElementById('api-status-dot');
    const text = document.getElementById('api-status-text');
    const apiUrl = this.getApiUrl();

    try {
      const resp = await fetch(`${apiUrl}/api/health`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });
      if (resp.ok) {
        if (dot) dot.className = "w-2 h-2 rounded-full bg-emerald-400 mr-1.5 animate-pulse";
        if (text) text.textContent = "API Conectada";
        return true;
      }
      throw new Error(`Status ${resp.status}`);
    } catch (e) {
      if (dot) dot.className = "w-2 h-2 rounded-full bg-rose-400 mr-1.5";
      if (text) text.textContent = "Sin Conexión";
      return false;
    }
  },

  bindApiConfigEvents() {
    const btnOpen = document.getElementById('btn-api-config');
    const modal = document.getElementById('modal-api-config');
    const btnClose = document.getElementById('btn-close-api-config');
    const btnSave = document.getElementById('btn-save-api');
    const btnTest = document.getElementById('btn-test-api');
    const inputUrl = document.getElementById('input-api-url');
    const feedback = document.getElementById('api-test-feedback');

    if (btnOpen) {
      btnOpen.addEventListener('click', () => {
        const current = localStorage.getItem(this.KEY_API_URL) || '';
        if (inputUrl) inputUrl.value = current;
        if (feedback) feedback.classList.add('hidden');
        if (modal) modal.classList.remove('hidden');
      });
    }

    if (btnClose && modal) {
      btnClose.addEventListener('click', () => modal.classList.add('hidden'));
    }

    if (btnTest && inputUrl && feedback) {
      btnTest.addEventListener('click', async () => {
        const testUrl = (inputUrl.value.trim() || window.location.origin).replace(/\/+$/, '');
        feedback.className = "text-xs p-2.5 rounded-xl border bg-blue-950/60 border-blue-800 text-blue-300 block";
        feedback.textContent = "Probando conexión con " + testUrl + "...";
        try {
          const resp = await fetch(`${testUrl}/api/health`);
          if (resp.ok) {
            feedback.className = "text-xs p-2.5 rounded-xl border bg-emerald-950/60 border-emerald-800 text-emerald-300 block";
            feedback.textContent = "✅ ¡Conexión exitosa! El servicio en Railway respondió correctamente.";
          } else {
            throw new Error(`El servidor respondió con código ${resp.status}`);
          }
        } catch (err) {
          feedback.className = "text-xs p-2.5 rounded-xl border bg-rose-950/60 border-rose-800 text-rose-300 block";
          feedback.textContent = "❌ No se pudo conectar: " + err.message;
        }
      });
    }

    if (btnSave && inputUrl && modal) {
      btnSave.addEventListener('click', () => {
        this.setApiUrl(inputUrl.value.trim());
        modal.classList.add('hidden');
        this.syncWithBackend();
      });
    }
  },

  // ================= LOCAL STATE MANAGEMENT =================
  loadState() {
    try {
      const masterStr = localStorage.getItem(this.KEY_MASTER);
      this.masterExam = masterStr ? JSON.parse(masterStr) : null;
    } catch (e) {
      this.masterExam = null;
    }

    try {
      const resultsStr = localStorage.getItem(this.KEY_RESULTS);
      this.results = resultsStr ? JSON.parse(resultsStr) : [];
    } catch (e) {
      this.results = [];
    }
  },

  saveMasterExamToStorage(exam) {
    this.masterExam = exam;
    localStorage.setItem(this.KEY_MASTER, JSON.stringify(exam));
    this.renderAll();
  },

  async deleteMasterExamFromStorage() {
    if (!confirm("¿Eliminar el Examen Principal? También se eliminará del servidor en la nube.")) return;
    
    if (this.masterExam && this.masterExam.id) {
      try {
        const apiUrl = this.getApiUrl();
        await fetch(`${apiUrl}/api/exams/${this.masterExam.id}`, { method: 'DELETE' });
      } catch (e) {
        console.warn("Could not delete from backend:", e);
      }
    }

    this.masterExam = null;
    localStorage.removeItem(this.KEY_MASTER);
    this.renderAll();
  },

  saveResultsToStorage() {
    localStorage.setItem(this.KEY_RESULTS, JSON.stringify(this.results));
    this.renderResults();
  },

  // ================= NAVIGATION =================
  bindNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');
    const sections = {
      'tab-master': document.getElementById('tab-master'),
      'tab-grader': document.getElementById('tab-grader'),
      'tab-results': document.getElementById('tab-results')
    };

    navButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetTab = btn.getAttribute('data-tab');

        if (window.scanner) window.scanner.stopLiveCamera();

        Object.entries(sections).forEach(([key, sec]) => {
          if (sec) sec.classList.toggle('hidden', key !== targetTab);
        });

        navButtons.forEach(b => {
          b.classList.remove('text-blue-400', 'active-tab');
          b.classList.add('text-slate-400');
        });
        btn.classList.remove('text-slate-400');
        btn.classList.add('text-blue-400', 'active-tab');

        if (targetTab === 'tab-results') {
          this.renderResults();
          this.fetchResultsFromApi();
        } else if (targetTab === 'tab-grader') {
          this.renderGraderView();
        } else if (targetTab === 'tab-master') {
          this.renderMasterExamView();
        }
      });
    });

    const goMasterBtn = document.getElementById('btn-go-to-master');
    if (goMasterBtn) {
      goMasterBtn.addEventListener('click', () => {
        const masterTabBtn = document.querySelector('[data-tab="tab-master"]');
        if (masterTabBtn) masterTabBtn.click();
      });
    }
  },

  renderAll() {
    this.renderMasterExamView();
    this.renderGraderView();
    this.renderResults();
  },

  async syncWithBackend() {
    if (!this.masterExam || !this.masterExam.id) {
      try {
        const apiUrl = this.getApiUrl();
        const resp = await fetch(`${apiUrl}/api/exams`);
        if (resp.ok) {
          const list = await resp.json();
          if (list && list.length > 0) {
            // Prefer PAA exam if available
            const preferred = list.find(e => e.is_paa || e.total_questions === 125) || list[0];
            const isPaa = (preferred.is_paa || preferred.total_questions === 125);
            const sections = this.buildSections(preferred.total_questions, isPaa ? "paa_official" : "2_halves");
            this.saveMasterExamToStorage({
              id: preferred.id,
              title: preferred.title,
              total_questions: preferred.total_questions,
              options_per_question: preferred.options_per_question,
              is_paa: isPaa,
              sections: sections,
              answers: preferred.answer_key,
              scanned_at: preferred.created_at
            });
          }
        }
      } catch (e) {
        console.warn("Sync failed:", e);
      }
    }
  },

  // ================= TAB 1: EXAMEN PRINCIPAL =================
  bindMasterExamEvents() {
    const scanMasterBtn = document.getElementById('btn-scan-master-sheet');
    if (scanMasterBtn) {
      scanMasterBtn.addEventListener('click', () => {
        if (window.scanner) window.scanner.startLiveCamera('master');
      });
    }

    const rescanMasterBtn = document.getElementById('btn-rescan-master');
    if (rescanMasterBtn) {
      rescanMasterBtn.addEventListener('click', () => {
        if (window.scanner) window.scanner.startLiveCamera('master');
      });
    }

    const downloadPdfBtn = document.getElementById('btn-download-pdf');
    if (downloadPdfBtn) {
      downloadPdfBtn.addEventListener('click', () => this.downloadExamPdf());
    }

    const manualBtn = document.getElementById('btn-create-master-manual');
    if (manualBtn) {
      manualBtn.addEventListener('click', () => this.openMasterKeyEditor(false));
    }

    const editKeyBtn = document.getElementById('btn-edit-master-key');
    if (editKeyBtn) {
      editKeyBtn.addEventListener('click', () => this.openMasterKeyEditor(true));
    }

    const deleteMasterBtn = document.getElementById('btn-delete-master');
    if (deleteMasterBtn) {
      deleteMasterBtn.addEventListener('click', () => this.deleteMasterExamFromStorage());
    }

    // Load PAA preset button
    const loadPaaBtn = document.getElementById('btn-load-paa-preset');
    if (loadPaaBtn) {
      loadPaaBtn.addEventListener('click', () => {
        const titleInput = document.getElementById('input-master-title');
        const qCountSelect = document.getElementById('select-master-q-count');
        const optsSelect = document.getElementById('select-master-opts-count');
        const secSelect = document.getElementById('select-master-sections-mode');

        if (titleInput) titleInput.value = "Examen Oficial PAA (125 Reactivos)";
        if (qCountSelect) qCountSelect.value = "125";
        if (optsSelect) optsSelect.value = "4";
        if (secSelect) secSelect.value = "paa_official";

        alert("🎓 Formato Oficial PAA cargado:\n• 125 Reactivos\n• 4 Secciones: Lectura (45), Redacción (25), Mate (45), Grid (10)\n• Escala College Board (400 - 1600 pts)");
      });
    }

    // Modal controls
    const closeEditorBtn = document.getElementById('btn-close-master-editor');
    const cancelEditorBtn = document.getElementById('btn-cancel-master-editor');
    const saveEditorBtn = document.getElementById('btn-save-master-editor');
    const randomKeyBtn = document.getElementById('btn-random-master-key');
    const editorModal = document.getElementById('modal-master-editor');

    if (closeEditorBtn) closeEditorBtn.addEventListener('click', () => editorModal.classList.add('hidden'));
    if (cancelEditorBtn) cancelEditorBtn.addEventListener('click', () => editorModal.classList.add('hidden'));

    if (randomKeyBtn) {
      randomKeyBtn.addEventListener('click', () => {
        const totalQ = this.masterExam ? this.masterExam.total_questions : parseInt(document.getElementById('select-master-q-count').value);
        const opts = ["A", "B", "C", "D"];
        const gridSamples = ["1/2", "3.5", "18", "4/5", "2.25", "10", "3/8", "125", "0.75", "42"];

        for (let q = 1; q <= totalQ; q++) {
          if (q >= 116 && q <= 125) {
            this.masterEditorAnswers[q] = gridSamples[(q - 116) % gridSamples.length];
          } else {
            this.masterEditorAnswers[q] = opts[Math.floor(Math.random() * opts.length)];
          }
        }
        this.renderMasterKeyEditorGrid();
      });
    }

    if (saveEditorBtn) {
      saveEditorBtn.addEventListener('click', async () => {
        const totalQ = this.masterExam ? this.masterExam.total_questions : parseInt(document.getElementById('select-master-q-count').value);
        const optsCount = this.masterExam ? this.masterExam.options_per_question : parseInt(document.getElementById('select-master-opts-count').value);
        const sectionsMode = document.getElementById('select-master-sections-mode').value;
        const examTitle = (document.getElementById('input-master-title')?.value || "Examen Parcial").trim();
        const isPaa = (totalQ === 125 || sectionsMode === "paa_official");

        for (let q = 1; q <= totalQ; q++) {
          if (!this.masterEditorAnswers[q]) {
            this.masterEditorAnswers[q] = (q >= 116 && q <= 125) ? "1" : "A";
          }
        }

        const sections = this.buildSections(totalQ, sectionsMode);

        // Save to API
        await this.persistExamToApi({
          title: examTitle,
          total_questions: totalQ,
          options_per_question: optsCount,
          sections: sections,
          answers: this.masterEditorAnswers,
          is_paa: isPaa
        });

        editorModal.classList.add('hidden');
      });
    }
  },

  buildSections(totalQuestions, mode) {
    if (mode === "paa_official" || totalQuestions === 125) {
      return [
        { name: "Lectura (Comprensión)", from: 1, to: 45, type: "LECTURA", area: "VERBAL" },
        { name: "Redacción Indirecta", from: 46, to: 70, type: "REDACCION", area: "VERBAL" },
        { name: "Matemáticas (Opción Múltiple)", from: 71, to: 115, type: "MATEMATICAS", area: "MATEMATICAS" },
        { name: "Matemáticas (Grid Numérico)", from: 116, to: 125, type: "MATEMATICASGRID", area: "MATEMATICAS" }
      ];
    } else if (mode === "single") {
      return [{ name: "Sección General", from: 1, to: totalQuestions, type: "GENERAL", area: "GENERAL" }];
    } else if (mode === "every_10") {
      const sections = [];
      let start = 1;
      let secNum = 1;
      while (start <= totalQuestions) {
        const end = Math.min(start + 9, totalQuestions);
        sections.push({ name: `Sección ${secNum}`, from: start, to: end, type: "GENERAL", area: "GENERAL" });
        start += 10;
        secNum++;
      }
      return sections;
    } else {
      // 2 halves (default)
      const half = Math.ceil(totalQuestions / 2);
      return [
        { name: "Sección 1 (Lectura / Verbal)", from: 1, to: half, type: "VERBAL", area: "VERBAL" },
        { name: "Sección 2 (Matemáticas)", from: half + 1, to: totalQuestions, type: "MATEMATICAS", area: "MATEMATICAS" }
      ];
    }
  },

  async persistExamToApi({ title, total_questions, options_per_question, sections, answers, is_paa }) {
    if (window.scanner) window.scanner.showLoading("Guardando Examen en Railway...", "Sincronizando clave con la API...");

    const apiUrl = this.getApiUrl();
    const payload = {
      title: title || "Examen Oficial PAA 125",
      subject: is_paa ? "Prueba de Aptitud Académica" : "Evaluación General",
      total_questions: total_questions,
      options_per_question: options_per_question,
      answer_key: answers,
      points_per_question: 1.0,
      penalty_per_wrong: 0.0,
      sections_config: { sections: sections },
      is_paa: !!is_paa
    };

    try {
      let resp;
      if (this.masterExam && this.masterExam.id) {
        resp = await fetch(`${apiUrl}/api/exams/${this.masterExam.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } else {
        resp = await fetch(`${apiUrl}/api/exams`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }

      let examData;
      if (resp.ok) {
        examData = await resp.json();
      } else {
        examData = { id: is_paa ? 'EXM-PAA125' : ('EXM-' + Date.now().toString().slice(-6)) };
      }

      const savedMaster = {
        id: examData.id,
        title: title,
        total_questions: total_questions,
        options_per_question: options_per_question,
        sections: sections,
        answers: answers,
        is_paa: !!is_paa,
        scanned_at: new Date().toLocaleString()
      };

      this.saveMasterExamToStorage(savedMaster);
      if (window.scanner) window.scanner.hideLoading();
      alert(`¡Examen Principal guardado con éxito!\n\nID: ${savedMaster.id}\nPreguntas: ${total_questions} ${is_paa ? '(Formato PAA)' : ''}\nSincronizado con la API.`);
    } catch (err) {
      if (window.scanner) window.scanner.hideLoading();
      console.warn("Error connecting to API, saving locally:", err);
      const savedMaster = {
        id: this.masterExam?.id || ('EXM-LOC' + Date.now().toString().slice(-4)),
        title: title,
        total_questions: total_questions,
        options_per_question: options_per_question,
        sections: sections,
        answers: answers,
        is_paa: !!is_paa,
        scanned_at: new Date().toLocaleString()
      };
      this.saveMasterExamToStorage(savedMaster);
      alert(`Guardado en modo local (sin conexión al servidor).\nID: ${savedMaster.id}`);
    }
  },

  downloadExamPdf() {
    if (!this.masterExam || !this.masterExam.id) {
      alert("Configura primero el Examen Principal para descargar la hoja.");
      return;
    }
    const apiUrl = this.getApiUrl();
    const pdfUrl = `${apiUrl}/api/exams/${this.masterExam.id}/pdf`;
    window.open(pdfUrl, '_blank');
  },

  renderMasterExamView() {
    const existsCard = document.getElementById('master-exists-card');
    const emptyCard = document.getElementById('master-empty-card');
    const metaText = document.getElementById('master-exam-meta');
    const titleEl = document.getElementById('master-exam-title');
    const answersContainer = document.getElementById('master-answers-display');

    if (!this.masterExam) {
      if (existsCard) existsCard.classList.add('hidden');
      if (emptyCard) emptyCard.classList.remove('hidden');
      return;
    }

    if (existsCard) existsCard.classList.remove('hidden');
    if (emptyCard) emptyCard.classList.add('hidden');

    if (titleEl) titleEl.textContent = this.masterExam.title || "Examen Principal Activo";

    const isPaa = (this.masterExam.is_paa || this.masterExam.total_questions === 125);
    if (metaText) {
      metaText.innerHTML = isPaa
        ? `<span class="text-amber-400 font-bold">🎓 Formato PAA College Board</span> • 125 reactivos (Escala 400 - 1600 pts)`
        : `${this.masterExam.total_questions} preguntas • ID: ${this.masterExam.id || 'N/A'}`;
    }

    if (answersContainer) {
      answersContainer.innerHTML = '';
      (this.masterExam.sections || []).forEach(sec => {
        const secBox = document.createElement('div');
        secBox.className = "bg-slate-950 p-3 rounded-xl border border-slate-800 space-y-2";

        const secTitle = document.createElement('div');
        secTitle.className = "text-xs font-semibold text-slate-300 flex items-center justify-between";
        secTitle.innerHTML = `<span>${sec.name}</span> <span class="text-slate-500 font-mono">P${sec.from}-P${sec.to}</span>`;
        secBox.appendChild(secTitle);

        const bubblesRow = document.createElement('div');
        bubblesRow.className = (sec.type === "MATEMATICASGRID")
          ? "grid grid-cols-2 sm:grid-cols-5 gap-2"
          : "grid grid-cols-5 sm:grid-cols-10 gap-1.5";

        for (let q = sec.from; q <= sec.to; q++) {
          const ans = this.masterExam.answers ? this.masterExam.answers[q] : '-';
          const bubble = document.createElement('div');
          bubble.className = "flex flex-col items-center bg-slate-900 border border-slate-800 rounded-lg p-1";
          bubble.innerHTML = `
            <span class="text-[9px] font-mono text-slate-400 leading-none">${q}</span>
            <span class="text-xs font-bold text-blue-400 mt-0.5 truncate max-w-full">${ans || '?'}</span>
          `;
          bubblesRow.appendChild(bubble);
        }

        secBox.appendChild(bubblesRow);
        answersContainer.appendChild(secBox);
      });
    }
  },

  openMasterKeyEditor(isEditingExisting) {
    const editorModal = document.getElementById('modal-master-editor');
    const totalQ = isEditingExisting && this.masterExam 
      ? this.masterExam.total_questions 
      : parseInt(document.getElementById('select-master-q-count').value) || 125;

    this.masterEditorAnswers = {};

    for (let q = 1; q <= totalQ; q++) {
      if (isEditingExisting && this.masterExam && this.masterExam.answers && this.masterExam.answers[q]) {
        this.masterEditorAnswers[q] = this.masterExam.answers[q];
      } else {
        this.masterEditorAnswers[q] = (q >= 116 && q <= 125) ? "1" : "A";
      }
    }

    this.renderMasterKeyEditorGrid();
    editorModal.classList.remove('hidden');
  },

  renderMasterKeyEditorGrid() {
    const container = document.getElementById('master-key-editor-grid');
    if (!container) return;
    container.innerHTML = '';

    const opts = ["A", "B", "C", "D"];
    const totalQ = Object.keys(this.masterEditorAnswers).length;

    for (let q = 1; q <= totalQ; q++) {
      const isGrid = (q >= 116 && q <= 125);
      const row = document.createElement('div');
      row.className = "flex items-center justify-between p-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs";

      const label = document.createElement('span');
      label.className = "font-bold font-mono text-slate-300 w-16";
      label.textContent = isGrid ? `P${q} (Grid):` : `P${q.toString().padStart(2, '0')}:`;
      row.appendChild(label);

      if (isGrid) {
        // Text Input for Grid Math values (fractions / decimals, e.g. 1/2, 3.5, 18)
        const inputWrap = document.createElement('div');
        inputWrap.className = "flex items-center space-x-1.5 flex-1 justify-end";
        
        const gridInput = document.createElement('input');
        gridInput.type = "text";
        gridInput.value = this.masterEditorAnswers[q] || "";
        gridInput.placeholder = "Ej: 1/2 o 3.5";
        gridInput.className = "bg-slate-950 border border-slate-700 text-white font-mono font-bold text-xs rounded-lg px-2.5 py-1 w-28 text-right focus:outline-none focus:ring-1 focus:ring-blue-500";
        gridInput.addEventListener('input', (e) => {
          this.masterEditorAnswers[q] = e.target.value.trim();
        });
        inputWrap.appendChild(gridInput);
        row.appendChild(inputWrap);
      } else {
        // Standard ABCD buttons
        const buttonsWrap = document.createElement('div');
        buttonsWrap.className = "flex items-center space-x-1.5";

        opts.forEach(letter => {
          const btn = document.createElement('button');
          btn.type = "button";
          const selected = (this.masterEditorAnswers[q] === letter);
          btn.className = `w-7 h-7 rounded-full text-xs font-bold transition-all ${
            selected
              ? 'bg-blue-600 text-white shadow-md shadow-blue-500/40'
              : 'bg-slate-800 text-slate-400 hover:bg-slate-750'
          }`;
          btn.textContent = letter;
          btn.addEventListener('click', () => {
            this.masterEditorAnswers[q] = letter;
            this.renderMasterKeyEditorGrid();
          });
          buttonsWrap.appendChild(btn);
        });

        row.appendChild(buttonsWrap);
      }

      container.appendChild(row);
    }
  },

  // ================= IMAGE DISPATCH FROM SCANNER =================
  async handleCapturedImage(fileOrBlob, target) {
    if (target === 'master') {
      await this.handleScanMasterViaApi(fileOrBlob);
    } else {
      await this.handleScanStudentViaApi(fileOrBlob);
    }
  },

  async handleScanMasterViaApi(fileOrBlob) {
    const isPaa = (this.masterExam?.is_paa || this.masterExam?.total_questions === 125 || document.getElementById('select-master-q-count')?.value === '125');
    const totalQ = isPaa ? 125 : parseInt(document.getElementById('select-master-q-count')?.value || '20');

    if (window.scanner) {
      window.scanner.showLoading(
        isPaa ? "Analizando Hoja Maestra PAA (125 Reactivos)..." : "Analizando Hoja Maestra...",
        "Detectando respuestas con OpenCV en Railway..."
      );
    }

    const optsCount = parseInt(document.getElementById('select-master-opts-count')?.value || '4');
    const apiUrl = this.getApiUrl();

    const formData = new FormData();
    formData.append('file', fileOrBlob, 'hoja_maestra.jpg');
    formData.append('total_questions', totalQ);
    formData.append('options_per_question', optsCount);
    formData.append('is_paa', isPaa);

    try {
      const resp = await fetch(`${apiUrl}/api/omr/scan-master`, {
        method: 'POST',
        body: formData
      });

      if (!resp.ok) {
        const errJson = await resp.json().catch(() => ({}));
        throw new Error(errJson.detail || `Error en el servidor: ${resp.status}`);
      }

      const data = await resp.json();
      if (window.scanner) window.scanner.hideLoading();

      this.masterEditorAnswers = data.detected_answers || {};
      for (let q = 1; q <= totalQ; q++) {
        if (!this.masterEditorAnswers[q]) {
          this.masterEditorAnswers[q] = (q >= 116 && q <= 125) ? "1" : "A";
        }
      }

      this.renderMasterKeyEditorGrid();
      const editorModal = document.getElementById('modal-master-editor');
      if (editorModal) editorModal.classList.remove('hidden');

      alert(`¡Hoja Maestra analizada!\n\nSe detectaron ${data.total_detected} de ${totalQ} respuestas.\nVerifica y confirma la clave a continuación.`);
    } catch (err) {
      if (window.scanner) window.scanner.hideLoading();
      alert(`Error al analizar la hoja maestra con la API: ${err.message}\nPuedes ingresar las respuestas manualmente con el botón 'Marcar a mano'.`);
    }
  },

  async handleScanStudentViaApi(fileOrBlob) {
    if (!this.masterExam) {
      alert("Por favor escanea o configura el Examen Principal primero.");
      return;
    }

    const isPaa = (this.masterExam.is_paa || this.masterExam.total_questions === 125);

    if (window.scanner) {
      window.scanner.showLoading(
        isPaa ? "Calificando Examen PAA Oficial..." : "Calificando Examen de Alumno...",
        isPaa ? "Aplicando baremo College Board (Escala 400-1600) y lectura Grid..." : "Ejecutando visión computacional..."
      );
    }

    const apiUrl = this.getApiUrl();
    const formData = new FormData();
    formData.append('file', fileOrBlob, 'hoja_alumno.jpg');
    formData.append('student_name', '');

    try {
      const resp = await fetch(`${apiUrl}/api/exams/${this.masterExam.id}/scan`, {
        method: 'POST',
        body: formData
      });

      if (!resp.ok) {
        const errJson = await resp.json().catch(() => ({}));
        throw new Error(errJson.detail || `Error en el servidor: ${resp.status}`);
      }

      const scanResult = await resp.json();
      if (window.scanner) window.scanner.hideLoading();

      this.tempApiResult = scanResult;
      this.openSaveStudentModal(scanResult);
    } catch (err) {
      if (window.scanner) window.scanner.hideLoading();
      alert(`Error al procesar la hoja del alumno: ${err.message}\nVerifica que la imagen esté bien iluminada y las 4 esquinas sean visibles.`);
    }
  },

  // ================= TAB 2: CALIFICADOR =================
  bindGraderEvents() {
    const openCamBtn = document.getElementById('btn-open-student-camera');
    if (openCamBtn) {
      openCamBtn.addEventListener('click', () => {
        if (!this.masterExam) {
          alert("Por favor escanea o configura el Examen Principal primero.");
          return;
        }
        if (window.scanner) window.scanner.startLiveCamera('student');
      });
    }

    const modalSave = document.getElementById('modal-save-student');
    const cancelModal = document.getElementById('btn-cancel-save-modal');
    const discardBtn = document.getElementById('btn-discard-student');
    const confirmSaveBtn = document.getElementById('btn-confirm-save-student');

    const closeModal = () => {
      if (modalSave) modalSave.classList.add('hidden');
      this.tempApiResult = null;
    };

    if (cancelModal) cancelModal.addEventListener('click', closeModal);
    if (discardBtn) discardBtn.addEventListener('click', closeModal);

    if (confirmSaveBtn) {
      confirmSaveBtn.addEventListener('click', () => {
        const nameInput = document.getElementById('input-student-name');
        const studentName = nameInput ? nameInput.value.trim() : '';

        if (!studentName) {
          alert("Por favor escribe el nombre del alumno para guardar.");
          if (nameInput) nameInput.focus();
          return;
        }

        this.finalizeGradedStudent(studentName);
        closeModal();
      });
    }
  },

  renderGraderView() {
    const alertBox = document.getElementById('grader-no-master-alert');
    const actionCard = document.getElementById('grader-action-card');
    const activeInfo = document.getElementById('grader-active-info');

    if (!this.masterExam) {
      if (alertBox) alertBox.classList.remove('hidden');
      if (actionCard) actionCard.classList.add('hidden');
    } else {
      if (alertBox) alertBox.classList.add('hidden');
      if (actionCard) actionCard.classList.remove('hidden');
      const isPaa = (this.masterExam.is_paa || this.masterExam.total_questions === 125);
      if (activeInfo) {
        activeInfo.innerHTML = isPaa
          ? `<span class="text-amber-400 font-bold">🎓 Examen PAA Activo (125 Reactivos)</span><br>Baremo College Board (400 - 1600 pts)`
          : `Calificando con: ${this.masterExam.title || 'Examen Principal'} (${this.masterExam.total_questions} preguntas)`;
      }
    }
  },

  openSaveStudentModal(scanResult) {
    const modalSave = document.getElementById('modal-save-student');
    const nameInput = document.getElementById('input-student-name');
    const matriculaVal = document.getElementById('save-modal-matricula-val');
    const countText = document.getElementById('save-modal-detected-count');
    const previewContainer = document.getElementById('save-modal-preview-sections');
    const imgWrap = document.getElementById('save-modal-annotated-wrap');
    const imgEl = document.getElementById('save-modal-annotated-img');

    if (nameInput) nameInput.value = '';

    if (matriculaVal) {
      matriculaVal.textContent = scanResult.student_id || 'S/N';
    }

    const isPaa = (scanResult.is_paa || scanResult.total_possible === 1600);

    if (countText) {
      countText.textContent = isPaa
        ? `Puntaje Global PAA: ${scanResult.puntaje_total_paa || scanResult.score} / 1600 pts`
        : `${scanResult.correct_count} aciertos de ${scanResult.total_possible} (${scanResult.percentage}%)`;
    }

    if (imgWrap && imgEl && scanResult.annotated_image_b64) {
      imgEl.src = scanResult.annotated_image_b64;
      imgWrap.classList.remove('hidden');
    } else if (imgWrap) {
      imgWrap.classList.add('hidden');
    }

    if (previewContainer) {
      if (isPaa) {
        previewContainer.innerHTML = `
          <span class="font-bold text-amber-300 block mb-1">🎓 Calificación Oficial PAA:</span>
          <div class="flex items-center justify-between text-xs text-slate-300 py-0.5">
            <span>Lectura y Redacción:</span>
            <span class="font-bold text-emerald-400">${scanResult.puntaje_verbal || 0} pts (${scanResult.verbal_aciertos || 0}/70 aciertos)</span>
          </div>
          <div class="flex items-center justify-between text-xs text-slate-300 py-0.5">
            <span>Matemáticas (con Grid):</span>
            <span class="font-bold text-blue-400">${scanResult.puntaje_mate || 0} pts (${scanResult.mate_aciertos || 0}/55 aciertos)</span>
          </div>
          <div class="flex items-center justify-between text-xs text-slate-300 pt-1 border-t border-slate-800">
            <span class="font-bold text-white">PUNTAJE GLOBAL:</span>
            <span class="font-black text-amber-400 text-sm">${scanResult.puntaje_total_paa || scanResult.score} / 1600 pts</span>
          </div>
        `;
      } else {
        previewContainer.innerHTML = `
          <span class="font-bold text-slate-300 block mb-1">Resumen de Evaluación:</span>
          <div class="flex items-center justify-between text-xs text-slate-300">
            <span>Calificación: <b>${scanResult.score} / ${scanResult.total_possible}</b></span>
            <span class="font-bold text-emerald-400">Aciertos: ${scanResult.correct_count} | Fallos: ${scanResult.wrong_count}</span>
          </div>
        `;
      }
    }

    if (modalSave) modalSave.classList.remove('hidden');
    setTimeout(() => { if (nameInput) nameInput.focus(); }, 200);
    lucide.createIcons();
  },

  finalizeGradedStudent(studentName) {
    if (!this.tempApiResult) return;

    const isPaa = (this.tempApiResult.is_paa || this.tempApiResult.total_possible === 1600);

    const record = {
      id: this.tempApiResult.id || ('res_' + Date.now()),
      exam_id: this.masterExam?.id || (isPaa ? 'EXM-PAA125' : 'EXM-001'),
      student_id: this.tempApiResult.student_id || 'S/N',
      student_name: studentName,
      is_paa: isPaa,
      score: this.tempApiResult.score,
      total_possible: this.tempApiResult.total_possible,
      percentage: this.tempApiResult.percentage,
      puntaje_verbal: this.tempApiResult.puntaje_verbal,
      puntaje_mate: this.tempApiResult.puntaje_mate,
      puntaje_total_paa: this.tempApiResult.puntaje_total_paa,
      verbal_aciertos: this.tempApiResult.verbal_aciertos,
      mate_aciertos: this.tempApiResult.mate_aciertos,
      correct_count: this.tempApiResult.correct_count,
      wrong_count: this.tempApiResult.wrong_count,
      blank_count: this.tempApiResult.blank_count,
      student_answers: this.tempApiResult.student_answers,
      question_details: this.tempApiResult.question_details,
      annotated_image_b64: this.tempApiResult.annotated_image_b64,
      scanned_at: new Date().toLocaleDateString() + ' ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    this.results.unshift(record);
    this.saveResultsToStorage();

    const resultsTabBtn = document.querySelector('[data-tab="tab-results"]');
    if (resultsTabBtn) resultsTabBtn.click();
  },

  // ================= TAB 3: RESULTADOS =================
  async fetchResultsFromApi() {
    if (!this.masterExam || !this.masterExam.id) return;
    const apiUrl = this.getApiUrl();
    try {
      const resp = await fetch(`${apiUrl}/api/exams/${this.masterExam.id}/results`);
      if (resp.ok) {
        const apiResults = await resp.json();
        if (apiResults && apiResults.length > 0) {
          this.results = apiResults;
          this.saveResultsToStorage();
        }
      }
    } catch (e) {
      console.warn("Could not fetch remote results:", e);
    }
  },

  renderResults() {
    const container = document.getElementById('results-cards-container');
    const totalEl = document.getElementById('stats-total');
    const avgEl = document.getElementById('stats-average');

    if (!container) return;

    totalEl.textContent = this.results.length;

    if (this.results.length === 0) {
      avgEl.textContent = "0";
      container.innerHTML = `
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center space-y-3 text-slate-400">
          <i data-lucide="clipboard-list" class="w-10 h-10 mx-auto text-slate-500"></i>
          <div>
            <h3 class="text-sm font-bold text-white">No hay alumnos calificados</h3>
            <p class="text-xs mt-1">Usa la pestaña "Calificador" para escanear hojas de exámenes con la cámara.</p>
          </div>
        </div>
      `;
      lucide.createIcons();
      return;
    }

    const isPaa = this.results.some(r => r.is_paa || r.total_possible === 1600);
    const totalScore = this.results.reduce((acc, r) => acc + (parseFloat(r.puntaje_total_paa || r.score) || 0), 0);
    const avg = totalScore / this.results.length;
    avgEl.textContent = isPaa ? Math.round(avg) + " pts" : avg.toFixed(1);

    container.innerHTML = '';

    this.results.forEach(res => {
      const cardWrap = document.createElement('div');
      cardWrap.className = "swipe-card-wrapper";
      cardWrap.setAttribute('data-id', res.id);

      const resIsPaa = (res.is_paa || res.total_possible === 1600);
      const scoreNum = parseFloat(res.puntaje_total_paa || res.score) || 0;
      const pass = resIsPaa ? (scoreNum >= 1000) : (parseFloat(res.percentage) >= 60);

      cardWrap.innerHTML = `
        <div class="swipe-action-left"><i data-lucide="trash-2" class="w-5 h-5 mr-1.5"></i> Borrar</div>
        <div class="swipe-action-right"><i data-lucide="edit-3" class="w-5 h-5 mr-1.5"></i> Editar</div>
        
        <div class="swipe-card-content p-4 space-y-3 cursor-pointer">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2.5">
              <div class="w-9 h-9 rounded-xl ${pass ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'} flex items-center justify-center font-bold text-xs">
                ${pass ? (resIsPaa ? 'AP' : 'AP') : 'RP'}
              </div>
              <div>
                <h3 class="text-sm font-bold text-white leading-tight">${res.student_name || 'Alumno Sin Nombre'}</h3>
                <p class="text-[11px] text-slate-400 mt-0.5">
                  ${resIsPaa ? '<span class="text-amber-400 font-semibold mr-1">PAA</span>' : ''}
                  Matrícula: <span class="font-mono text-blue-400">${res.student_id || 'S/N'}</span> • ${res.scanned_at || ''}
                </p>
              </div>
            </div>

            <div class="text-right">
              <span class="text-base font-extrabold ${pass ? 'text-emerald-400' : 'text-rose-400'}">
                ${resIsPaa ? scoreNum : scoreNum.toFixed(1)}
              </span>
              <span class="text-xs text-slate-400">/${res.total_possible || (resIsPaa ? 1600 : 10)}</span>
              <div class="text-[10px] font-semibold text-slate-400">
                ${resIsPaa ? `V:${res.puntaje_verbal || '-'} M:${res.puntaje_mate || '-'}` : `${res.percentage}%`}
              </div>
            </div>
          </div>

          <div class="flex items-center justify-between pt-2 border-t border-slate-800 text-[11px] text-slate-400">
            <span>✓ <b>${res.correct_count}</b> aciertos</span>
            <span>✗ <b>${res.wrong_count}</b> errores</span>
            <span>⚪ <b>${res.blank_count || 0}</b> blanco</span>
            <span class="text-blue-400 flex items-center">Ver hoja <i data-lucide="chevron-right" class="w-3.5 h-3.5 ml-0.5"></i></span>
          </div>
        </div>
      `;

      this.bindCardGestures(cardWrap, res);
      container.appendChild(cardWrap);
    });

    lucide.createIcons();
  },

  bindCardGestures(cardWrap, res) {
    const content = cardWrap.querySelector('.swipe-card-content');
    let startX = 0;
    let currentX = 0;
    let isSwiping = false;

    content.addEventListener('click', (e) => {
      if (Math.abs(currentX) > 10) return;
      this.openDetailModal(res);
    });

    content.addEventListener('touchstart', (e) => {
      startX = e.touches[0].clientX;
      isSwiping = true;
      content.classList.add('swiping');
    }, { passive: true });

    content.addEventListener('touchmove', (e) => {
      if (!isSwiping) return;
      currentX = e.touches[0].clientX - startX;
      if (Math.abs(currentX) > 130) {
        currentX = currentX > 0 ? 130 + (currentX - 130) * 0.2 : -130 + (currentX + 130) * 0.2;
      }
      content.style.transform = `translateX(${currentX}px)`;
    }, { passive: true });

    content.addEventListener('touchend', () => {
      if (!isSwiping) return;
      isSwiping = false;
      content.classList.remove('swiping');

      if (currentX < -85) {
        content.style.transform = 'translateX(-100px)';
        setTimeout(() => {
          content.style.transform = 'translateX(0px)';
          this.promptDeleteResult(res.id, res.student_name);
        }, 120);
      } else if (currentX > 85) {
        content.style.transform = 'translateX(100px)';
        setTimeout(() => {
          content.style.transform = 'translateX(0px)';
          this.openEditModal(res);
        }, 120);
      } else {
        content.style.transform = 'translateX(0px)';
      }
      currentX = 0;
    });
  },

  openDetailModal(res) {
    const modal = document.getElementById('modal-detail-results');
    const nameEl = document.getElementById('detail-student-name');
    const dateEl = document.getElementById('detail-date');
    const scoreBadge = document.getElementById('detail-score-badge');
    const pctBadge = document.getElementById('detail-percentage-badge');
    const correctEl = document.getElementById('detail-correct-count');
    const wrongEl = document.getElementById('detail-wrong-count');
    const blankEl = document.getElementById('detail-blank-count');
    const breakdownList = document.getElementById('detail-breakdown-list');
    const sectionsContainer = document.getElementById('detail-sections-container');
    const annotatedContainer = document.getElementById('detail-annotated-container');
    const annotatedImg = document.getElementById('detail-annotated-img');

    const isPaa = (res.is_paa || res.total_possible === 1600);

    if (nameEl) nameEl.textContent = `${res.student_name} (${res.student_id || 'S/N'})`;
    if (dateEl) dateEl.textContent = `Fecha: ${res.scanned_at || '--'}`;

    if (scoreBadge) {
      scoreBadge.textContent = isPaa
        ? `${res.puntaje_total_paa || res.score} pts`
        : `${parseFloat(res.score).toFixed(1)} / ${res.total_possible || 10}`;
    }
    if (pctBadge) {
      pctBadge.textContent = isPaa
        ? `Escala College Board (400 - 1600)`
        : `${res.percentage}% de efectividad`;
    }

    if (correctEl) correctEl.textContent = `✓ ${res.correct_count} aciertos`;
    if (wrongEl) wrongEl.textContent = `✗ ${res.wrong_count} fallos`;
    if (blankEl) blankEl.textContent = `⚪ ${res.blank_count || 0} en blanco`;

    // Sections container
    if (sectionsContainer) {
      if (isPaa) {
        sectionsContainer.innerHTML = `
          <div class="grid grid-cols-2 gap-2 text-xs">
            <div class="bg-slate-950 p-2.5 rounded-xl border border-slate-800">
              <span class="text-slate-400 block text-[10px] uppercase font-bold">Lectura y Redacción</span>
              <span class="text-lg font-black text-emerald-400">${res.puntaje_verbal || 0} pts</span>
              <span class="text-[10px] text-slate-500 block">${res.verbal_aciertos || 0}/70 aciertos</span>
            </div>
            <div class="bg-slate-950 p-2.5 rounded-xl border border-slate-800">
              <span class="text-slate-400 block text-[10px] uppercase font-bold">Matemáticas (inc. Grid)</span>
              <span class="text-lg font-black text-blue-400">${res.puntaje_mate || 0} pts</span>
              <span class="text-[10px] text-slate-500 block">${res.mate_aciertos || 0}/55 aciertos</span>
            </div>
          </div>
        `;
      } else {
        sectionsContainer.innerHTML = '';
      }
    }

    // Show annotated image if present
    if (annotatedContainer && annotatedImg) {
      if (res.annotated_image_b64) {
        annotatedImg.src = res.annotated_image_b64;
        annotatedContainer.classList.remove('hidden');
      } else {
        annotatedContainer.classList.add('hidden');
      }
    }

    // Breakdown list
    if (breakdownList) {
      breakdownList.innerHTML = '';
      (res.question_details || []).forEach(d => {
        const row = document.createElement('div');
        row.className = "flex items-center justify-between p-1.5 rounded-lg bg-slate-900 border border-slate-800";
        const isOk = (d.status === "correct" || d.is_correct);
        const color = isOk ? "text-emerald-400" : (d.status === "blank" ? "text-slate-400" : "text-rose-400");
        const symbol = isOk ? "✓" : (d.status === "blank" ? "⚪" : "✗");
        const secTag = d.section ? `<span class="text-[9px] font-mono text-slate-500 mr-1.5">[${d.section}]</span>` : '';

        row.innerHTML = `
          <div class="flex items-center">
            ${secTag}
            <span class="font-mono text-slate-300">P${d.question}:</span>
          </div>
          <span class="font-bold ${color}">
            ${symbol} Alumno: ${d.student_answer || 'En blanco'} (Clave: ${d.correct_answer || '?'})
          </span>
        `;
        breakdownList.appendChild(row);
      });
    }

    if (modal) modal.classList.remove('hidden');
    lucide.createIcons();
  },

  promptDeleteResult(id, studentName) {
    this.activeDeletingId = id;
    const modal = document.getElementById('modal-confirm-delete');
    const label = document.getElementById('delete-confirm-student-name');
    if (label) label.textContent = `¿Deseas eliminar las calificaciones de "${studentName}"?`;
    if (modal) modal.classList.remove('hidden');
  },

  async executeDeleteResult() {
    if (!this.activeDeletingId) return;

    try {
      const apiUrl = this.getApiUrl();
      await fetch(`${apiUrl}/api/results/${this.activeDeletingId}`, { method: 'DELETE' });
    } catch (e) {
      console.warn("Could not delete from API:", e);
    }

    this.results = this.results.filter(r => r.id !== this.activeDeletingId);
    this.saveResultsToStorage();

    const modal = document.getElementById('modal-confirm-delete');
    if (modal) modal.classList.add('hidden');
    this.activeDeletingId = null;
  },

  openEditModal(res) {
    this.activeEditingId = res.id;
    this.activeEditingAnswers = { ...(res.student_answers || {}) };

    const modal = document.getElementById('modal-edit-answers');
    const nameEl = document.getElementById('edit-modal-student-name');
    const container = document.getElementById('edit-answers-picker-grid');

    if (nameEl) nameEl.textContent = `Alumno: ${res.student_name}`;
    if (container) {
      container.innerHTML = '';
      const totalQ = this.masterExam ? this.masterExam.total_questions : (res.is_paa ? 125 : 20);
      const opts = ["A", "B", "C", "D"];

      for (let q = 1; q <= totalQ; q++) {
        const isGrid = (q >= 116 && q <= 125);
        const row = document.createElement('div');
        row.className = "flex items-center justify-between p-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs";

        const label = document.createElement('span');
        label.className = "font-bold font-mono text-slate-300 w-16";
        label.textContent = isGrid ? `P${q} (Grid):` : `P${q.toString().padStart(2, '0')}:`;
        row.appendChild(label);

        if (isGrid) {
          const gridInput = document.createElement('input');
          gridInput.type = "text";
          gridInput.value = this.activeEditingAnswers[q] || "";
          gridInput.placeholder = "Ej: 1/2";
          gridInput.className = "bg-slate-950 border border-slate-700 text-white font-mono font-bold text-xs rounded-lg px-2 py-1 w-24 text-right";
          gridInput.addEventListener('input', (e) => {
            this.activeEditingAnswers[q] = e.target.value.trim();
          });
          row.appendChild(gridInput);
        } else {
          const buttonsWrap = document.createElement('div');
          buttonsWrap.className = "flex items-center space-x-1.5";

          opts.forEach(letter => {
            const btn = document.createElement('button');
            btn.type = "button";
            const selected = (this.activeEditingAnswers[q] === letter);
            btn.className = `w-7 h-7 rounded-full text-xs font-bold transition-all ${
              selected
                ? 'bg-blue-600 text-white shadow-md shadow-blue-500/40'
                : 'bg-slate-800 text-slate-400 hover:bg-slate-750'
            }`;
            btn.textContent = letter;
            btn.addEventListener('click', () => {
              this.activeEditingAnswers[q] = letter;
              this.openEditModal(res);
            });
            buttonsWrap.appendChild(btn);
          });

          row.appendChild(buttonsWrap);
        }

        container.appendChild(row);
      }
    }

    if (modal) modal.classList.remove('hidden');
  },

  saveEditedAnswers() {
    if (!this.activeEditingId) return;

    const targetIdx = this.results.findIndex(r => r.id === this.activeEditingId);
    if (targetIdx === -1) return;

    const oldRecord = this.results[targetIdx];
    const totalQ = this.masterExam ? this.masterExam.total_questions : (oldRecord.is_paa ? 125 : 20);
    const masterAns = this.masterExam?.answers || {};

    let correct = 0;
    let wrong = 0;
    let blank = 0;
    const details = [];

    for (let q = 1; q <= totalQ; q++) {
      const student = (this.activeEditingAnswers[q] || "").toUpperCase().trim();
      const master = (masterAns[q] || "").toUpperCase().trim();
      let status = "blank";
      if (!student) blank++;
      else if (student === master) { status = "correct"; correct++; }
      else { status = "wrong"; wrong++; }

      details.push({
        question: q,
        student_answer: student,
        correct_answer: master,
        status: status,
        is_correct: (status === "correct")
      });
    }

    const finalScore = totalQ > 0 ? (correct / totalQ) * 10 : 0;
    const percentage = totalQ > 0 ? Math.round((correct / totalQ) * 100) : 0;

    this.results[targetIdx] = {
      ...oldRecord,
      student_answers: this.activeEditingAnswers,
      score: oldRecord.is_paa ? (correct * 10) : finalScore,
      percentage: percentage,
      correct_count: correct,
      wrong_count: wrong,
      blank_count: blank,
      question_details: details
    };

    this.saveResultsToStorage();

    const modal = document.getElementById('modal-edit-answers');
    if (modal) modal.classList.add('hidden');
    this.activeEditingId = null;
  },

  bindResultModals() {
    const cancelDelete = document.getElementById('btn-cancel-delete');
    const confirmDelete = document.getElementById('btn-confirm-delete');
    const deleteModal = document.getElementById('modal-confirm-delete');

    if (cancelDelete && deleteModal) {
      cancelDelete.addEventListener('click', () => deleteModal.classList.add('hidden'));
    }
    if (confirmDelete) {
      confirmDelete.addEventListener('click', () => this.executeDeleteResult());
    }

    const closeDetail = document.getElementById('btn-close-detail-modal');
    const dismissDetail = document.getElementById('btn-dismiss-detail');
    const detailModal = document.getElementById('modal-detail-results');

    if (closeDetail && detailModal) {
      closeDetail.addEventListener('click', () => detailModal.classList.add('hidden'));
    }
    if (dismissDetail && detailModal) {
      dismissDetail.addEventListener('click', () => detailModal.classList.add('hidden'));
    }

    const closeEdit = document.getElementById('btn-close-edit-modal');
    const cancelEdit = document.getElementById('btn-cancel-edit-answers');
    const saveEdit = document.getElementById('btn-save-recalculated');
    const editModal = document.getElementById('modal-edit-answers');

    if (closeEdit && editModal) {
      closeEdit.addEventListener('click', () => editModal.classList.add('hidden'));
    }
    if (cancelEdit && editModal) {
      cancelEdit.addEventListener('click', () => editModal.classList.add('hidden'));
    }
    if (saveEdit) {
      saveEdit.addEventListener('click', () => this.saveEditedAnswers());
    }

    const exportBtn = document.getElementById('btn-export-csv');
    if (exportBtn) {
      exportBtn.addEventListener('click', () => this.exportCsv());
    }
  },

  exportCsv() {
    if (this.masterExam && this.masterExam.id) {
      const apiUrl = this.getApiUrl();
      const exportUrl = `${apiUrl}/api/exams/${this.masterExam.id}/export`;
      window.open(exportUrl, '_blank');
      return;
    }

    if (this.results.length === 0) {
      alert("No hay resultados para exportar.");
      return;
    }

    const isPaa = this.results.some(r => r.is_paa || r.total_possible === 1600);
    let csvContent = isPaa
      ? "data:text/csv;charset=utf-8,ID,Fecha,Matricula,Nombre,Puntaje Global PAA,Puntaje Verbal,Puntaje Mate,Aciertos Verbal,Aciertos Mate,Total Aciertos,Errores\n"
      : "data:text/csv;charset=utf-8,ID,Fecha,Matricula,Nombre,Calificacion,Porcentaje,Aciertos,Errores\n";

    this.results.forEach(r => {
      if (isPaa) {
        csvContent += `"${r.id}","${r.scanned_at || ''}","${r.student_id || ''}","${r.student_name}","${r.puntaje_total_paa || r.score}","${r.puntaje_verbal || 0}","${r.puntaje_mate || 0}","${r.verbal_aciertos || 0}","${r.mate_aciertos || 0}","${r.correct_count}","${r.wrong_count}"\n`;
      } else {
        csvContent += `"${r.id}","${r.scanned_at || ''}","${r.student_id || ''}","${r.student_name}","${r.score}","${r.percentage}%","${r.correct_count}","${r.wrong_count}"\n`;
      }
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `calificaciones_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
};

document.addEventListener('DOMContentLoaded', () => {
  window.app.init();
});
