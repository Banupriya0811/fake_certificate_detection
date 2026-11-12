/**
 * Document Upload Scan view and Scan Result view.
 */
function renderScanView(root) {
  root.innerHTML = `
    <div class="page-header">
      <div class="page-eyebrow">Document Scan</div>
      <h1 class="page-title">Verify a Document</h1>
      <p class="page-subtitle">Upload a marksheet or certificate image to detect potential forgery.</p>
    </div>

    <div class="grid-2">
      <div class="card">
        <input id="file-input" type="file" accept=".png,.jpg,.jpeg,.bmp,.tiff,.webp" hidden />
        <div class="drop-zone" id="drop-zone">
          <div style="font-size: 2rem; margin-bottom: 0.5rem;">📄</div>
          <div style="font-weight: 700; font-size: 1.05rem;">Drop document image here</div>
          <div style="color: var(--text-muted); font-size: 0.88rem; margin-top: 0.25rem;">
            or click to browse (JPG, PNG, BMP, TIFF, WEBP — max 16 MB)
          </div>
          <div id="upload-preview" class="preview-box" hidden>
            <img id="upload-preview-img" alt="Selected document preview" />
            <div id="upload-preview-name" style="margin-top: 0.5rem; font-family: var(--mono); font-size: 0.8rem; color: var(--text-muted);"></div>
          </div>
        </div>

        <div style="display: flex; gap: 0.75rem; margin-top: 1.15rem; flex-wrap: wrap;">
          <button id="scan-submit-btn" class="btn btn-primary" style="flex: 1;" disabled>Analyse Document</button>
          <a href="#/camera" class="btn btn-outline">Use Camera</a>
        </div>
      </div>

      <div style="display: flex; flex-direction: column; gap: 1rem;">
        <div class="card">
          <div class="page-eyebrow" style="margin-bottom: 0.75rem;">Your Overview</div>
          <ul class="meta-list">
            <li><span>Signed in as</span><strong id="overview-user">—</strong></li>
            <li><span>Total scans</span><strong id="overview-total">—</strong></li>
            <li><span>Authentic found</span><strong id="overview-real" style="color: var(--teal);">—</strong></li>
            <li><span>Fake detected</span><strong id="overview-fake" style="color: var(--danger);">—</strong></li>
          </ul>
        </div>

        <div class="card">
          <div class="page-eyebrow" style="margin-bottom: 0.6rem;">Best Practices</div>
          <ul class="meta-list" style="color: var(--text-muted);">
            <li>Keep all four corners of the document visible</li>
            <li>Avoid shadows, glare, or heavy blur</li>
            <li>Use clear scans or straight smartphone photos</li>
          </ul>
        </div>
      </div>
    </div>
  `;

  let selectedFile = null;
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");
  const previewBox = document.getElementById("upload-preview");
  const previewImg = document.getElementById("upload-preview-img");
  const previewName = document.getElementById("upload-preview-name");
  const submitBtn = document.getElementById("scan-submit-btn");

  function setFile(file) {
    if (!file) return;
    selectedFile = file;
    const reader = new FileReader();
    reader.onload = (ev) => {
      previewImg.src = ev.target.result;
    };
    reader.readAsDataURL(file);
    previewName.textContent = `${file.name} (${Math.round(file.size / 1024)} KB)`;
    previewBox.hidden = false;
    submitBtn.disabled = false;
  }

  dropZone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => setFile(fileInput.files[0]));
  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
  });
  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    setFile(e.dataTransfer.files[0]);
  });

  submitBtn.addEventListener("click", async () => {
    if (!selectedFile) return;
    submitBtn.disabled = true;
    submitBtn.textContent = "Analysing...";
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      const data = await apiRequest("/api/scan/upload", {
        method: "POST",
        body: formData,
      });
      window.AppState.lastScanResult = data;
      window.location.hash = "#/result";
    } catch (err) {
      showToast(err.message, "error");
      submitBtn.disabled = false;
      submitBtn.textContent = "Analyse Document";
    }
  });

  apiRequest("/api/profile")
    .then((data) => {
      document.getElementById("overview-user").textContent = data.user.username;
      document.getElementById("overview-total").textContent = data.stats.total;
      document.getElementById("overview-real").textContent = data.stats.reals;
      document.getElementById("overview-fake").textContent = data.stats.fakes;
    })
    .catch(() => {});
}

function renderResultView(root) {
  const payload = window.AppState.lastScanResult;
  if (!payload) {
    window.location.hash = "#/scan";
    return;
  }

  const { scan, prediction, image_url } = payload;
  const isFake = Boolean(prediction.is_fake);
  const cls = isFake ? "fake" : "real";

  root.innerHTML = `
    <div style="max-width: 820px; margin: 0 auto;">
      <div class="card" style="margin-bottom: 1.25rem; text-align: center;">
        <div class="page-eyebrow">${isFake ? "Forgery Detected" : "Document Verified"}</div>
        <h1 class="verdict-title ${cls}">${escapeHtml(prediction.result)}</h1>
        <div style="max-width: 380px; margin: 1rem auto 0;">
          <div style="display: flex; justify-content: space-between; font-size: 0.84rem;">
            <span style="color: var(--text-muted);">Confidence Score</span>
            <strong>${prediction.confidence}%</strong>
          </div>
          <div class="progress-track">
            <div class="progress-fill ${cls}" style="width: ${prediction.confidence}%;"></div>
          </div>
        </div>
      </div>

      <div class="grid-equal">
        <div class="card" style="display: grid; place-items: center;">
          <img src="${escapeHtml(assetUrl(image_url))}" alt="Scanned document" style="max-width: 100%; max-height: 300px; border-radius: 8px; object-fit: contain;" />
        </div>

        <div class="card">
          <div class="page-eyebrow" style="margin-bottom: 0.75rem;">Scan Metadata</div>
          <ul class="meta-list">
            <li><span>Scan ID</span><strong>#${scan.id}</strong></li>
            <li><span>File</span><strong>${escapeHtml(scan.display_name)}</strong></li>
            <li><span>Real Probability</span><strong>${prediction.real_probability}%</strong></li>
            <li><span>Fake Probability</span><strong>${prediction.fake_probability}%</strong></li>
            <li><span>Inference Mode</span><strong>${escapeHtml(prediction.mode.toUpperCase())}</strong></li>
          </ul>
        </div>
      </div>

      <div style="display: flex; gap: 0.75rem; justify-content: center; margin-top: 1.5rem; flex-wrap: wrap;">
        <a href="#/scan" class="btn btn-primary">Scan Another Document</a>
        <a href="#/history" class="btn btn-outline">View History</a>
        <a href="#/camera" class="btn btn-outline">Open Camera</a>
      </div>
    </div>
  `;
}

