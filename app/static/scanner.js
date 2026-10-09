// Mobile Camera and Image Capture Controller
// Captures high-res frames for Railway OpenCV API processing with fallback support

let activeStream = null;
let currentFacingMode = "environment";
let isTorchOn = false;
let countdownTimer = null;
let currentScanTarget = "student"; // 'master' or 'student'

const scanner = {
  elements: {},

  init() {
    this.cacheElements();
    this.bindEvents();
    window.scanner = this;
  },

  cacheElements() {
    this.elements = {
      liveContainer: document.getElementById('live-cam-container'),
      video: document.getElementById('live-video'),
      shutterFlash: document.getElementById('shutter-flash'),
      countdownOverlay: document.getElementById('countdown-overlay'),
      countdownNumber: document.getElementById('countdown-number'),
      timerBtnText: document.getElementById('timer-btn-text'),
      camStatusLabel: document.getElementById('cam-status-label'),
      loadingBox: document.getElementById('loading-box'),
      loadingTitle: document.getElementById('loading-title'),
      loadingDesc: document.getElementById('loading-desc'),

      // Inputs
      cameraInput: document.getElementById('input-camera-capture'),
      galleryInput: document.getElementById('input-gallery-capture'),

      // Controls
      btnCaptureLiveFrame: document.getElementById('btn-capture-live-frame'),
      btnTimerCapture: document.getElementById('btn-timer-capture'),
      btnCancelLiveCam: document.getElementById('btn-cancel-live-cam'),
      btnSwitchCam: document.getElementById('btn-switch-cam'),
      btnToggleTorch: document.getElementById('btn-toggle-torch'),
      btnCamGalleryFallback: document.getElementById('btn-cam-gallery-fallback')
    };
  },

  bindEvents() {
    // Capture live frame
    if (this.elements.btnCaptureLiveFrame) {
      this.elements.btnCaptureLiveFrame.addEventListener('click', () => {
        this.cancelCountdown();
        this.captureLiveFrame();
      });
    }

    // Auto-capture 3s timer
    if (this.elements.btnTimerCapture) {
      this.elements.btnTimerCapture.addEventListener('click', () => this.toggleCountdownTimer());
    }

    // Close camera
    if (this.elements.btnCancelLiveCam) {
      this.elements.btnCancelLiveCam.addEventListener('click', () => this.stopLiveCamera());
    }

    // Switch camera
    if (this.elements.btnSwitchCam) {
      this.elements.btnSwitchCam.addEventListener('click', () => this.switchCamera());
    }

    // Torch
    if (this.elements.btnToggleTorch) {
      this.elements.btnToggleTorch.addEventListener('click', () => this.toggleTorch());
    }

    // Gallery fallback inside camera
    if (this.elements.btnCamGalleryFallback) {
      this.elements.btnCamGalleryFallback.addEventListener('click', () => {
        this.stopLiveCamera();
        this.elements.galleryInput.click();
      });
    }

    // Native file inputs
    if (this.elements.cameraInput) {
      this.elements.cameraInput.addEventListener('change', (e) => this.handleFileSelected(e));
    }
    if (this.elements.galleryInput) {
      this.elements.galleryInput.addEventListener('change', (e) => this.handleFileSelected(e));
    }

    // Tab 2 Native Cam & Gallery buttons
    const btnNativeCam = document.getElementById('btn-student-native-cam');
    if (btnNativeCam) {
      btnNativeCam.addEventListener('click', () => {
        currentScanTarget = 'student';
        this.elements.cameraInput.click();
      });
    }

    const btnGallery = document.getElementById('btn-student-gallery');
    if (btnGallery) {
      btnGallery.addEventListener('click', () => {
        currentScanTarget = 'student';
        this.elements.galleryInput.click();
      });
    }
  },

  showLoading(title, desc) {
    if (this.elements.loadingTitle && title) this.elements.loadingTitle.textContent = title;
    if (this.elements.loadingDesc && desc) this.elements.loadingDesc.textContent = desc;
    if (this.elements.loadingBox) this.elements.loadingBox.classList.remove('hidden');
  },

  hideLoading() {
    if (this.elements.loadingBox) this.elements.loadingBox.classList.add('hidden');
  },

  async startLiveCamera(target = 'student', facing = 'environment') {
    currentScanTarget = target;
    currentFacingMode = facing;

    if (this.elements.camStatusLabel) {
      this.elements.camStatusLabel.textContent = target === 'master' ? 'Escaneando Hoja Maestra' : 'Calificando Hoja de Alumno';
    }

    if (this.elements.liveContainer) {
      this.elements.liveContainer.classList.remove('hidden');
    }

    const constraintList = [
      {
        video: {
          facingMode: { ideal: currentFacingMode },
          width: { ideal: 1920, min: 1280 },
          height: { ideal: 1080, min: 720 }
        }
      },
      {
        video: {
          facingMode: { ideal: currentFacingMode },
          width: { ideal: 1280 },
          height: { ideal: 720 }
        }
      },
      { video: { facingMode: currentFacingMode } },
      { video: true }
    ];

    let stream = null;
    let lastErr = null;

    for (const c of constraintList) {
      try {
        stream = await navigator.mediaDevices.getUserMedia(c);
        if (stream) break;
      } catch (err) {
        lastErr = err;
      }
    }

    if (!stream) {
      console.warn("Camera failed:", lastErr);
      alert("No se pudo iniciar la cámara en vivo del navegador. Abriendo cámara del dispositivo...");
      this.stopLiveCamera();
      this.elements.cameraInput.click();
      return;
    }

    activeStream = stream;
    this.elements.video.srcObject = stream;
    try {
      await this.elements.video.play();
    } catch (e) {
      console.error(e);
    }

    this.elements.liveContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    lucide.createIcons();
  },

  stopLiveCamera() {
    this.cancelCountdown();
    if (activeStream) {
      activeStream.getTracks().forEach(t => {
        try { t.stop(); } catch (e) {}
      });
      activeStream = null;
    }
    isTorchOn = false;
    if (this.elements.btnToggleTorch) {
      this.elements.btnToggleTorch.classList.remove('text-amber-400', 'bg-amber-500/30');
    }
    if (this.elements.liveContainer) {
      this.elements.liveContainer.classList.add('hidden');
    }
  },

  switchCamera() {
    const next = currentFacingMode === "environment" ? "user" : "environment";
    this.startLiveCamera(currentScanTarget, next);
  },

  async toggleTorch() {
    if (!activeStream) return;
    const track = activeStream.getVideoTracks()[0];
    if (!track) return;
    try {
      const caps = track.getCapabilities ? track.getCapabilities() : {};
      if (!caps.torch) {
        alert("La linterna no está disponible en este dispositivo.");
        return;
      }
      isTorchOn = !isTorchOn;
      await track.applyConstraints({ advanced: [{ torch: isTorchOn }] });
      if (this.elements.btnToggleTorch) {
        this.elements.btnToggleTorch.classList.toggle('text-amber-400', isTorchOn);
        this.elements.btnToggleTorch.classList.toggle('bg-amber-500/30', isTorchOn);
      }
    } catch (err) {
      console.warn(err);
    }
  },

  captureLiveFrame() {
    const video = this.elements.video;
    if (!video || !video.videoWidth) {
      alert("Iniciando cámara... por favor espera un instante.");
      return;
    }

    this.playShutterSound();
    this.triggerShutterFlash();

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    this.stopLiveCamera();

    // Export high-quality JPEG blob for OpenCV API
    canvas.toBlob((blob) => {
      if (!blob) {
        alert("Error al capturar la imagen de la cámara.");
        return;
      }
      this.dispatchCapturedImage(blob, currentScanTarget);
    }, 'image/jpeg', 0.88);
  },

  handleFileSelected(event) {
    const file = event.target.files[0];
    if (!file) return;

    this.stopLiveCamera();
    this.dispatchCapturedImage(file, currentScanTarget);
    event.target.value = '';
  },

  dispatchCapturedImage(fileOrBlob, target) {
    if (window.app && typeof window.app.handleCapturedImage === 'function') {
      window.app.handleCapturedImage(fileOrBlob, target);
    } else {
      console.error("App controller is not ready.");
    }
  },

  toggleCountdownTimer() {
    if (countdownTimer) {
      this.cancelCountdown();
      return;
    }

    let count = 3;
    const overlay = this.elements.countdownOverlay;
    const numEl = this.elements.countdownNumber;
    const btnText = this.elements.timerBtnText;

    if (overlay) overlay.classList.remove('hidden');
    if (numEl) numEl.textContent = count;
    if (btnText) btnText.textContent = "Cancel";

    countdownTimer = setInterval(() => {
      count--;
      if (count > 0) {
        if (numEl) numEl.textContent = count;
      } else {
        this.cancelCountdown();
        this.captureLiveFrame();
      }
    }, 1000);
  },

  cancelCountdown() {
    if (countdownTimer) {
      clearInterval(countdownTimer);
      countdownTimer = null;
    }
    if (this.elements.countdownOverlay) {
      this.elements.countdownOverlay.classList.add('hidden');
    }
    if (this.elements.timerBtnText) {
      this.elements.timerBtnText.textContent = "Auto 3s";
    }
  },

  triggerShutterFlash() {
    const flash = this.elements.shutterFlash;
    if (!flash) return;
    flash.classList.remove('opacity-0');
    flash.classList.add('bg-white', 'opacity-100');
    setTimeout(() => {
      flash.classList.remove('opacity-100');
      flash.classList.add('opacity-0');
    }, 120);
  },

  playShutterSound() {
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(800, audioCtx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(300, audioCtx.currentTime + 0.08);
      gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.08);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.08);
    } catch (e) {}
  }
};

document.addEventListener('DOMContentLoaded', () => {
  scanner.init();
});
