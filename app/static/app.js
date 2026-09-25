// Main Web Application Controller (Exams, Results, Navigation)

window.app = {
  exams: [],
  currentExam: null,
  answerKeySelection: {},

  init() {
    this.bindNavigation();
    this.bindExamModal();
    this.loadExams();
  },

  bindNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');
    const sections = {
      'tab-scan': document.getElementById('tab-scan'),
      'tab-exams': document.getElementById('tab-exams'),
      'tab-results': document.getElementById('tab-results')
    };

    navButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetTab = btn.getAttribute('data-tab');

        // Toggle sections
        Object.entries(sections).forEach(([key, section]) => {
          if (key === targetTab) {
            section.classList.remove('hidden');
          } else {
            section.classList.add('hidden');
          }
        });

        // Toggle active button style
        navButtons.forEach(b => {
          b.classList.remove('text-blue-400', 'active-tab');
          b.classList.add('text-slate-400');
        });
        btn.classList.remove('text-slate-400');
        btn.classList.add('text-blue-400', 'active-tab');

        // Specific tab refresh
        if (targetTab === 'tab-results') {
          const activeExamId = document.getElementById('select-active-exam').value;
          if (activeExamId) this.loadResults(activeExamId);
        }
      });
    });

    // Refresh exams button
    document.getElementById('btn-refresh-exams').addEventListener('click', () => this.loadExams());

    // Active exam select change
    const select = document.getElementById('select-active-exam');
    select.addEventListener('change', (e) => {
      const exam = this.exams.find(ex => ex.id === e.target.value);
      this.setActiveExam(exam);
    });
  },

  async loadExams() {
    try {
      const res = await fetch('/api/exams');
      if (!res.ok) throw new Error("Error cargando exámenes");
      this.exams = await res.json();
      this.renderExamSelect();
      this.renderExamsList();
    } catch (err) {
      console.error(err);
    }
  },

  renderExamSelect() {
    const select = document.getElementById('select-active-exam');
    select.innerHTML = '';

    if (this.exams.length === 0) {
      select.innerHTML = '<option value="">Sin exámenes creados. Crea uno primero.</option>';
      return;
    }

    this.exams.forEach(ex => {
      const opt = document.createElement('option');
      opt.value = ex.id;
      opt.textContent = `${ex.title} (${ex.total_questions} preguntas)`;
      select.appendChild(opt);
    });

    // Default to first exam
    this.setActiveExam(this.exams[0]);
  },

  setActiveExam(exam) {
    if (!exam) return;
    this.currentExam = exam;

    document.getElementById('select-active-exam').value = exam.id;
    document.getElementById('info-q-count').textContent = `Preguntas: ${exam.total_questions}`;
    document.getElementById('info-opt-count').textContent = `Opciones: ${exam.options_per_question} (A-${String.fromCharCode(64 + exam.options_per_question)})`;
    
    const pdfBtn = document.getElementById('btn-download-pdf-quick');
    pdfBtn.href = `/api/exams/${exam.id}/pdf`;
  },

  renderExamsList() {
    const container = document.getElementById('exams-list-container');
    container.innerHTML = '';

    if (this.exams.length === 0) {
      container.innerHTML = `
        <div class="text-center py-8 text-slate-500 text-xs">
          No hay exámenes creados todavía.<br>Presiona "Nuevo" para crear uno.
        </div>
      `;
      return;
    }

    this.exams.forEach(exam => {
      const card = document.createElement('div');
      card.className = "bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3";
      card.innerHTML = `
        <div class="flex items-start justify-between">
          <div>
            <h3 class="font-bold text-sm text-white">${exam.title}</h3>
            <p class="text-xs text-slate-400">${exam.subject ? exam.subject + ' • ' : ''}${exam.total_questions} preguntas • ${exam.options_per_question} opciones</p>
          </div>
          <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-950 text-blue-400 border border-blue-800">
            ${exam.scan_count || 0} escaneos
          </span>
        </div>

        <div class="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs">
          <a href="/api/exams/${exam.id}/pdf" target="_blank" class="text-blue-400 hover:text-blue-300 font-medium flex items-center">
            <i data-lucide="file-down" class="w-3.5 h-3.5 mr-1"></i> Imprimir Hoja
          </a>
          <div class="flex items-center space-x-2">
            <button onclick="app.selectAndScan('${exam.id}')" class="px-2.5 py-1 bg-blue-600/20 text-blue-400 hover:bg-blue-600/30 rounded-lg font-medium">
              Escanear
            </button>
            <button onclick="app.deleteExam('${exam.id}')" class="p-1 text-slate-500 hover:text-rose-400">
              <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
            </button>
          </div>
        </div>
      `;
      container.appendChild(card);
    });

    lucide.createIcons();
  },

  selectAndScan(examId) {
    const exam = this.exams.find(e => e.id === examId);
    if (exam) {
      this.setActiveExam(exam);
      // Switch to scan tab
      document.querySelector('[data-tab="tab-scan"]').click();
    }
  },

  async deleteExam(examId) {
    if (!confirm("¿Eliminar este examen y todos sus resultados escaneados?")) return;
    try {
      const res = await fetch(`/api/exams/${examId}`, { method: 'DELETE' });
      if (res.ok) {
        await this.loadExams();
      }
    } catch (err) {
      console.error(err);
    }
  },

  // Modal Create Exam & Answer Key Picker
  bindExamModal() {
    const modal = document.getElementById('modal-create-exam');
    const openBtn = document.getElementById('btn-open-create-exam');
    const closeBtn = document.getElementById('btn-close-create-modal');
    const qInput = document.getElementById('input-exam-questions');
    const optInput = document.getElementById('input-exam-options');
    const randomKeyBtn = document.getElementById('btn-quick-random-key');
    const form = document.getElementById('form-create-exam');

    openBtn.addEventListener('click', () => {
      modal.classList.remove('hidden');
      this.renderAnswerKeyPicker();
    });

    closeBtn.addEventListener('click', () => modal.classList.add('hidden'));

    qInput.addEventListener('input', () => this.renderAnswerKeyPicker());
    optInput.addEventListener('change', () => this.renderAnswerKeyPicker());

    randomKeyBtn.addEventListener('click', () => {
      const totalQ = parseInt(qInput.value) || 20;
      const optsCount = parseInt(optInput.value) || 4;
      const letters = ["A", "B", "C", "D", "E"].slice(0, optsCount);

      for (let i = 1; i <= totalQ; i++) {
        const randLetter = letters[Math.floor(Math.random() * letters.length)];
        this.answerKeySelection[i] = randLetter;
      }
      this.renderAnswerKeyPicker();
    });

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const totalQ = parseInt(qInput.value);
      const optsCount = parseInt(optInput.value);

      // Verify all questions have an answer key
      for (let i = 1; i <= totalQ; i++) {
        if (!this.answerKeySelection[i]) {
          this.answerKeySelection[i] = "A"; // default to A if missing
        }
      }

      const payload = {
        title: document.getElementById('input-exam-title').value.trim(),
        subject: document.getElementById('input-exam-subject').value.trim(),
        total_questions: totalQ,
        options_per_question: optsCount,
        answer_key: this.answerKeySelection,
        points_per_question: 1.0,
        penalty_per_wrong: 0.0
      };

      try {
        const res = await fetch('/api/exams', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!res.ok) throw new Error("Error al guardar examen");
        const created = await res.json();
        
        modal.classList.add('hidden');
        form.reset();
        await this.loadExams();
        this.setActiveExam(created);

        // Prompt user to print the sheet
        if (confirm(`¡Examen creado con éxito!\n\n¿Deseas descargar la plantilla de hoja imprimible en PDF ahora?`)) {
          window.open(`/api/exams/${created.id}/pdf`, '_blank');
        }
      } catch (err) {
        alert("Error: " + err.message);
      }
    });
  },

  renderAnswerKeyPicker() {
    const totalQ = Math.min(100, Math.max(5, parseInt(document.getElementById('input-exam-questions').value) || 20));
    const optsCount = parseInt(document.getElementById('input-exam-options').value) || 4;
    const letters = ["A", "B", "C", "D", "E"].slice(0, optsCount);

    const container = document.getElementById('answer-key-picker-grid');
    container.innerHTML = '';

    for (let q = 1; q <= totalQ; q++) {
      if (!this.answerKeySelection[q]) {
        this.answerKeySelection[q] = "A"; // default
      }

      const row = document.createElement('div');
      row.className = "flex items-center justify-between py-1 px-2 rounded-lg bg-slate-900 border border-slate-800";
      
      const qNum = document.createElement('span');
      qNum.className = "text-xs font-bold text-slate-300 w-8";
      qNum.textContent = `${q.toString().padStart(2, '0')}:`;
      row.appendChild(qNum);

      const bubblesGroup = document.createElement('div');
      bubblesGroup.className = "flex items-center space-x-1.5";

      letters.forEach(letter => {
        const btn = document.createElement('button');
        btn.type = "button";
        const isSelected = (this.answerKeySelection[q] === letter);
        btn.className = `w-6 h-6 rounded-full text-[11px] font-bold transition-all ${
          isSelected 
            ? 'bg-blue-600 text-white shadow-md shadow-blue-500/30' 
            : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
        }`;
        btn.textContent = letter;
        btn.addEventListener('click', () => {
          this.answerKeySelection[q] = letter;
          this.renderAnswerKeyPicker();
        });
        bubblesGroup.appendChild(btn);
      });

      row.appendChild(bubblesGroup);
      container.appendChild(row);
    }
  },

  // Results & Statistics Tab
  async loadResults(examId) {
    if (!examId) return;

    try {
      const res = await fetch(`/api/exams/${examId}/results`);
      if (!res.ok) throw new Error("Error cargando resultados");
      const results = await res.json();
      this.renderResults(results, examId);
    } catch (err) {
      console.error(err);
    }
  },

  renderResults(results, examId) {
    document.getElementById('stats-total').textContent = results.length;
    const exportBtn = document.getElementById('btn-export-csv');
    exportBtn.href = `/api/exams/${examId}/export-csv`;

    if (results.length === 0) {
      document.getElementById('stats-average').textContent = "0.0%";
      document.getElementById('results-table-body').innerHTML = `
        <div class="p-6 text-center text-slate-500 text-xs">
          Aún no hay hojas escaneadas para este examen.
        </div>
      `;
      return;
    }

    const avg = results.reduce((acc, cur) => acc + cur.percentage, 0) / results.length;
    document.getElementById('stats-average').textContent = `${avg.toFixed(1)}%`;

    const tbody = document.getElementById('results-table-body');
    tbody.innerHTML = '';

    results.forEach(r => {
      const row = document.createElement('div');
      row.className = "p-3 flex items-center justify-between hover:bg-slate-850 transition-colors";
      const passed = r.percentage >= 60.0;

      row.innerHTML = `
        <div>
          <div class="font-bold text-white flex items-center space-x-1.5">
            <span>${r.student_id}</span>
            ${r.student_name ? `<span class="text-slate-400 font-normal">(${r.student_name})</span>` : ''}
          </div>
          <div class="text-[11px] text-slate-400 mt-0.5">
            Aciertos: ${r.correct_count} • Fallos: ${r.wrong_count} • Blanco: ${r.blank_count}
          </div>
        </div>
        <div class="text-right">
          <div class="font-extrabold ${passed ? 'text-emerald-400' : 'text-rose-400'}">
            ${r.score} / ${r.total_possible}
          </div>
          <div class="text-[11px] font-semibold text-slate-400">${r.percentage}%</div>
        </div>
      `;
      tbody.appendChild(row);
    });
  }
};

document.addEventListener('DOMContentLoaded', () => window.app.init());
