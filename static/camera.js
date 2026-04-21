class BillCamera {
  constructor(videoEl, overlayEl, feedbackEl, captureBtn) {
    this.video = videoEl;
    this.canvas = overlayEl;
    this.ctx = overlayEl.getContext("2d");
    this.feedback = feedbackEl;
    this.captureBtn = captureBtn;
    this.stream = null;
    this.intervalId = null;
    this.animFrameId = null;
    this.qualityOk = false;
  }

  async start() {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 1920 } },
      });
      this.video.srcObject = this.stream;
      await new Promise((resolve) => (this.video.onloadedmetadata = resolve));
      await this.video.play();
      this._syncCanvas();
      this._drawLoop();
      this._startLightingCheck();
      return true;
    } catch {
      return false;
    }
  }

  stop() {
    if (this.stream) this.stream.getTracks().forEach((t) => t.stop());
    if (this.intervalId) clearInterval(this.intervalId);
    if (this.animFrameId) cancelAnimationFrame(this.animFrameId);
    this.stream = null;
  }

  _syncCanvas() {
    this.canvas.width = this.canvas.offsetWidth || 640;
    this.canvas.height = this.canvas.offsetHeight || 480;
  }

  _frameRect() {
    const w = this.canvas.width, h = this.canvas.height;
    return { x: w * 0.05, y: h * 0.08, w: w * 0.9, h: h * 0.82 };
  }

  _drawLoop() {
    const draw = () => {
      if (!this.stream) return;
      const W = this.canvas.width, H = this.canvas.height;
      const fr = this._frameRect();
      const color = this.qualityOk ? "#22c55e" : "#facc15";

      this.ctx.clearRect(0, 0, W, H);

      // Dimmed surround with cutout
      this.ctx.save();
      this.ctx.fillStyle = "rgba(0,0,0,0.52)";
      this.ctx.beginPath();
      this.ctx.rect(0, 0, W, H);
      this.ctx.rect(fr.x, fr.y, fr.w, fr.h);
      this.ctx.fill("evenodd");
      this.ctx.restore();

      // Frame border
      this.ctx.strokeStyle = color;
      this.ctx.lineWidth = 2;
      this.ctx.strokeRect(fr.x, fr.y, fr.w, fr.h);

      // Corner brackets
      const cs = Math.min(fr.w, fr.h) * 0.09;
      this.ctx.lineWidth = Math.max(3, W * 0.005);
      this.ctx.strokeStyle = color;
      [
        [fr.x, fr.y + cs, fr.x, fr.y, fr.x + cs, fr.y],
        [fr.x + fr.w - cs, fr.y, fr.x + fr.w, fr.y, fr.x + fr.w, fr.y + cs],
        [fr.x, fr.y + fr.h - cs, fr.x, fr.y + fr.h, fr.x + cs, fr.y + fr.h],
        [fr.x + fr.w - cs, fr.y + fr.h, fr.x + fr.w, fr.y + fr.h, fr.x + fr.w, fr.y + fr.h - cs],
      ].forEach(([x1, y1, mx, my, x2, y2]) => {
        this.ctx.beginPath();
        this.ctx.moveTo(x1, y1);
        this.ctx.lineTo(mx, my);
        this.ctx.lineTo(x2, y2);
        this.ctx.stroke();
      });

      // Hint label
      this.ctx.fillStyle = "rgba(255,255,255,0.75)";
      this.ctx.font = `${Math.max(11, W * 0.022)}px sans-serif`;
      this.ctx.textAlign = "center";
      this.ctx.fillText("Align bill within frame", W / 2, fr.y - 8);

      this.animFrameId = requestAnimationFrame(draw);
    };
    this.animFrameId = requestAnimationFrame(draw);
  }

  // Returns { brightness, blurVariance } from a downsampled frame
  _analyzeFrame() {
    if (!this.video.videoWidth) return { brightness: 128, blurVariance: 999 };
    const SIZE = 80;
    const c = document.createElement("canvas");
    c.width = SIZE; c.height = SIZE;
    const cx = c.getContext("2d");
    cx.drawImage(this.video, 0, 0, SIZE, SIZE);
    const d = cx.getImageData(0, 0, SIZE, SIZE).data;

    // Grayscale + brightness
    const gray = new Float32Array(SIZE * SIZE);
    let brightSum = 0;
    for (let i = 0; i < SIZE * SIZE; i++) {
      gray[i] = 0.299 * d[i*4] + 0.587 * d[i*4+1] + 0.114 * d[i*4+2];
      brightSum += gray[i];
    }
    const brightness = brightSum / (SIZE * SIZE);

    // Laplacian variance — higher = sharper
    let lapSum = 0, lapSumSq = 0, n = 0;
    for (let y = 1; y < SIZE - 1; y++) {
      for (let x = 1; x < SIZE - 1; x++) {
        const lap =
          4 * gray[y * SIZE + x]
          - gray[(y-1) * SIZE + x]
          - gray[(y+1) * SIZE + x]
          - gray[y * SIZE + (x-1)]
          - gray[y * SIZE + (x+1)];
        lapSum += lap;
        lapSumSq += lap * lap;
        n++;
      }
    }
    const mean = lapSum / n;
    const blurVariance = lapSumSq / n - mean * mean;

    return { brightness, blurVariance };
  }

  _startLightingCheck() {
    this.intervalId = setInterval(() => {
      const { brightness, blurVariance } = this._analyzeFrame();

      if (brightness < 60) {
        this._setFeedback("🔴 Too dark — move to better lighting", "text-red-400");
        this.qualityOk = false;
        this.captureBtn.disabled = true;
      } else if (brightness > 210) {
        this._setFeedback("🟡 Too bright — reduce glare or step back", "text-yellow-400");
        this.qualityOk = false;
        this.captureBtn.disabled = true;
      } else if (blurVariance < 30) {
        this._setFeedback("🔵 Too blurry — hold the camera steady", "text-blue-400");
        this.qualityOk = false;
        this.captureBtn.disabled = true;
      } else {
        this._setFeedback("🟢 Quality good — tap Capture", "text-green-400");
        this.qualityOk = true;
        this.captureBtn.disabled = false;
      }
    }, 600);
  }

  _setFeedback(text, colorClass) {
    this.feedback.textContent = text;
    this.feedback.className = `${colorClass} text-sm text-center mt-2 font-medium`;
  }

  // Returns base64 JPEG of the cropped frame area
  capture() {
    const vw = this.video.videoWidth, vh = this.video.videoHeight;
    const fr = this._frameRect();
    const scaleX = vw / this.canvas.width;
    const scaleY = vh / this.canvas.height;

    const crop = document.createElement("canvas");
    crop.width = fr.w * scaleX;
    crop.height = fr.h * scaleY;
    crop.getContext("2d").drawImage(
      this.video,
      fr.x * scaleX, fr.y * scaleY, fr.w * scaleX, fr.h * scaleY,
      0, 0, crop.width, crop.height
    );
    return crop.toDataURL("image/jpeg", 0.92).split(",")[1];
  }
}
