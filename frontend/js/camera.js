/**
 * Live Camera Capture view with simple rotate, brightness/contrast, and scan.
 */
window.ActiveCameraStream = null;

function stopCameraStream() {
  if (window.ActiveCameraStream) {
    window.ActiveCameraStream.getTracks().forEach((track) => track.stop());
    window.ActiveCameraStream = null;
  }
}

function renderCameraView(root) {
  root.innerHTML = `
    <div class="page-header">
      <div class="page-eyebrow">Live Capture</div>
      <h1 class="page-title">Camera Scan</h1>
      <p class="page-subtitle">Capture a document photo using your webcam, adjust if needed, and verify.</p>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="toolbar" id="cam-edit-tools" hidden>
          <button class="btn btn-outline btn-sm" id="btn-rotate-left">Rotate -90°</button>
          <button class="btn btn-outline btn-sm" id="btn-rotate-right">Rotate +90°</button>
          <button class="btn btn-outline btn-sm" id="btn-retake">Retake</button>
        </div>

        <div class="camera-stage">
          <video id="cam-video" autoplay playsinline></video>
          <canvas id="cam-canvas" hidden></canvas>
        </div>

        <div id="cam-sliders" style="margin-top: 0.9rem;" hidden>
          <label for="cam-brightness">Brightness: <span id="cam-br-label">100</span>%</label>
          <input id="cam-brightness" type="range" min="60" max="150" value="100" style="width: 100%; margin-bottom: 0.5rem;" />
          <label for="cam-contrast">Contrast: <span id="cam-ct-label">100</span>%</label>
          <input id="cam-contrast" type="range" min="60" max="150" value="100" style="width: 100%;" />
        </div>
      </div>

      <div class="card" style="display: flex; flex-direction: column; gap: 0.75rem;">
        <div class="page-eyebrow">Camera Controls</div>
        <div id="cam-status" style="font-size: 0.88rem; color: var(--text-muted);">Camera idle. Click Start Camera.</div>
        <button id="btn-start-cam" class="btn btn-outline">Start Camera</button>
        <button id="btn-capture-cam" class="btn btn-primary" disabled>Capture Photo</button>
        <button id="btn-submit-cam" class="btn btn-primary" hidden>Analyse Captured Photo</button>
      </div>
    </div>
  `;

  const video = document.getElementById("cam-video");
  const canvas = document.getElementById("cam-canvas");
  const ctx = canvas.getContext("2d");
  const statusEl = document.getElementById("cam-status");
  const startBtn = document.getElementById("btn-start-cam");
  const captureBtn = document.getElementById("btn-capture-cam");
  const submitBtn = document.getElementById("btn-submit-cam");
  const editTools = document.getElementById("cam-edit-tools");
  const sliders = document.getElementById("cam-sliders");
  const brSlider = document.getElementById("cam-brightness");
  const ctSlider = document.getElementById("cam-contrast");

  let baseCanvas = null;

  function drawFiltered() {
    if (!baseCanvas) return;
    const br = brSlider.value;
    const ct = ctSlider.value;
    document.getElementById("cam-br-label").textContent = br;
    document.getElementById("cam-ct-label").textContent = ct;
    canvas.width = baseCanvas.width;
    canvas.height = baseCanvas.height;
    ctx.filter = `brightness(${br}%) contrast(${ct}%)`;
    ctx.drawImage(baseCanvas, 0, 0);
    ctx.filter = "none";
  }

  function rotateBase(deg) {
    if (!baseCanvas) return;
    const tmp = document.createElement("canvas");
    tmp.width = baseCanvas.height;
    tmp.height = baseCanvas.width;
    const tctx = tmp.getContext("2d");
    tctx.translate(tmp.width / 2, tmp.height / 2);
    tctx.rotate((deg * Math.PI) / 180);
    tctx.drawImage(baseCanvas, -baseCanvas.width / 2, -baseCanvas.height / 2);
    baseCanvas = tmp;
    drawFiltered();
  }

  startBtn.addEventListener("click", async () => {
    try {
      stopCameraStream();
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } },
      });
      window.ActiveCameraStream = stream;
      video.srcObject = stream;
      video.hidden = false;
      canvas.hidden = true;
      editTools.hidden = true;
      sliders.hidden = true;
      submitBtn.hidden = true;
      captureBtn.disabled = false;
      statusEl.textContent = "Camera active. Align document and capture.";
    } catch (err) {
      statusEl.textContent = "Unable to access camera.";
      showToast("Camera permission denied or unavailable.", "error");
    }
  });

  captureBtn.addEventListener("click", () => {
    if (!video.videoWidth) return;
    baseCanvas = document.createElement("canvas");
    baseCanvas.width = video.videoWidth;
    baseCanvas.height = video.videoHeight;
    baseCanvas.getContext("2d").drawImage(video, 0, 0);
    brSlider.value = "100";
    ctSlider.value = "100";
    drawFiltered();

    stopCameraStream();
    video.hidden = true;
    canvas.hidden = false;
    editTools.hidden = false;
    sliders.hidden = false;
    submitBtn.hidden = false;
    captureBtn.disabled = true;
    statusEl.textContent = "Photo captured. Adjust or analyse now.";
  });

  document.getElementById("btn-rotate-left").addEventListener("click", () => rotateBase(-90));
  document.getElementById("btn-rotate-right").addEventListener("click", () => rotateBase(90));
  document.getElementById("btn-retake").addEventListener("click", () => startBtn.click());
  brSlider.addEventListener("input", drawFiltered);
  ctSlider.addEventListener("input", drawFiltered);

  submitBtn.addEventListener("click", async () => {
    submitBtn.disabled = true;
    submitBtn.textContent = "Analysing...";
    try {
      const imageData = canvas.toDataURL("image/jpeg", 0.92);
      const data = await apiRequest("/api/scan/camera", {
        method: "POST",
        body: JSON.stringify({ image_data: imageData }),
      });
      window.AppState.lastScanResult = data;
      window.location.hash = "#/result";
    } catch (err) {
      showToast(err.message, "error");
      submitBtn.disabled = false;
      submitBtn.textContent = "Analyse Captured Photo";
    }
  });
}

