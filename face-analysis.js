"use strict";

(() => {
  const MEDIAPIPE_MODULE = "./vendor/mediapipe/vision_bundle.mjs";
  const MEDIAPIPE_WASM = "./vendor/mediapipe/wasm";
  const FACE_MODEL = "./vendor/mediapipe/models/blaze_face_short_range.tflite";
  const DETECTION_MAX_DIMENSION = 1024;
  const MODEL_LOAD_TIMEOUT_MS = 20000;

  const $ = (selector) => document.querySelector(selector);
  const elements = {
    analyzeButton: $("#analyzeFacesButton"),
    modelBadge: $("#faceModelBadge"),
    progress: $("#faceProgress"),
    progressText: $("#faceProgressText"),
    cancelButton: $("#cancelFaceAnalysis"),
    error: $("#faceError"),
    errorText: $("#faceErrorText"),
    retryButton: $("#retryFaceModel"),
    results: $("#faceResults"),
    faceCount: $("#faceCount"),
    confidence: $("#faceConfidence"),
    keypointCount: $("#faceKeypointCount"),
    faceList: $("#faceList"),
    showBoxes: $("#showFaceBoxes"),
    showKeypoints: $("#showFaceKeypoints"),
    pixelateButton: $("#pixelateFaces"),
    blurButton: $("#blurFaces"),
    overlay: $("#faceOverlay"),
    source: $("#editCanvas")
  };

  let detector = null;
  let detectorType = null;
  let modelPromise = null;
  let detections = [];
  let analysisRunning = false;
  let analysisRunId = 0;
  let ignoreNextRender = false;

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, Number(value) || 0));
  }

  function setModelBadge(state, label) {
    elements.modelBadge.className = "ai-model-badge";
    if (state) elements.modelBadge.classList.add(`is-${state}`);
    elements.modelBadge.innerHTML = `<span aria-hidden="true"></span>${label}`;
  }

  function setProgress(visible, text = "") {
    elements.progress.hidden = !visible;
    if (text) elements.progressText.textContent = text;
    elements.cancelButton.hidden = !analysisRunning;
  }

  function showError(error) {
    setProgress(false);
    elements.error.hidden = false;
    const message = error?.message || "";
    elements.errorText.textContent = message.includes("本機伺服器")
      ? "瀏覽器會阻擋 file:// 載入 WASM；請雙擊 start-offline.cmd 開啟離線版。"
      : message.includes("逾時")
      ? "本機視覺模型載入逾時，請按「重新載入模型」。"
      : message.includes("fetch")
        ? "無法下載視覺模型，請檢查網路連線後重新載入。"
        : "模型初始化失敗；請重新載入，或改用最新版 Chrome／Edge。";
    setModelBadge("error", "載入失敗");
  }

  function withTimeout(promise, timeoutMs, message) {
    let timer;
    return Promise.race([
      promise,
      new Promise((_, reject) => {
        timer = window.setTimeout(() => reject(new Error(message)), timeoutMs);
      })
    ]).finally(() => window.clearTimeout(timer));
  }

  async function createMediaPipeDetector() {
    if (window.location.protocol === "file:") {
      throw new Error("離線模型需透過本機伺服器啟動");
    }
    const visionModule = await import(MEDIAPIPE_MODULE);
    const vision = await visionModule.FilesetResolver.forVisionTasks(MEDIAPIPE_WASM);
    try {
      return await visionModule.FaceDetector.createFromOptions(vision, {
        baseOptions: { modelAssetPath: FACE_MODEL, delegate: "GPU" },
        runningMode: "IMAGE",
        minDetectionConfidence: .5,
        minSuppressionThreshold: .3
      });
    } catch (_) {
      return visionModule.FaceDetector.createFromOptions(vision, {
        baseOptions: { modelAssetPath: FACE_MODEL },
        runningMode: "IMAGE",
        minDetectionConfidence: .5,
        minSuppressionThreshold: .3
      });
    }
  }

  async function ensureDetector(force = false) {
    if (detector && !force) return detector;
    if (modelPromise && !force) return modelPromise;
    if (force) {
      detector = null;
      detectorType = null;
      modelPromise = null;
    }

    elements.error.hidden = true;
    setModelBadge("loading", "模型載入中");
    setProgress(true, "正在從本機載入離線視覺模型…");
    elements.analyzeButton.disabled = true;

    modelPromise = (async () => {
      try {
        detector = await withTimeout(
          createMediaPipeDetector(),
          MODEL_LOAD_TIMEOUT_MS,
          "視覺模型載入逾時"
        );
        detectorType = "mediapipe";
      } catch (mediaPipeError) {
        if ("FaceDetector" in window) {
          detector = new window.FaceDetector({ fastMode: true, maxDetectedFaces: 20 });
          detectorType = "native";
        } else {
          throw mediaPipeError;
        }
      }
      setModelBadge("ready", detectorType === "mediapipe" ? "MediaPipe 離線就緒" : "瀏覽器模型就緒");
      setProgress(false);
      elements.error.hidden = true;
      elements.analyzeButton.disabled = !window.ImageStudio?.hasImage();
      return detector;
    })().catch((error) => {
      showError(error);
      elements.analyzeButton.disabled = !window.ImageStudio?.hasImage();
      modelPromise = null;
      throw error;
    });

    return modelPromise;
  }

  function createDetectionInput() {
    const sourceWidth = elements.source.width;
    const sourceHeight = elements.source.height;
    const scale = Math.min(1, DETECTION_MAX_DIMENSION / Math.max(sourceWidth, sourceHeight));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(sourceWidth * scale));
    canvas.height = Math.max(1, Math.round(sourceHeight * scale));
    const context = canvas.getContext("2d", { alpha: false });
    context.imageSmoothingEnabled = true;
    context.imageSmoothingQuality = "high";
    context.drawImage(elements.source, 0, 0, canvas.width, canvas.height);
    return {
      canvas,
      scaleX: sourceWidth / canvas.width,
      scaleY: sourceHeight / canvas.height
    };
  }

  function normalizeNativeDetection(detection, input) {
    const box = detection.boundingBox;
    const keypoints = (detection.landmarks || []).flatMap((landmark) => landmark.locations || []).map((point) => ({
      x: point.x / input.width,
      y: point.y / input.height
    }));
    return {
      boundingBox: { originX: box.x, originY: box.y, width: box.width, height: box.height },
      categories: [{ score: 1 }],
      keypoints
    };
  }

  function remapDetection(detection, scaleX, scaleY) {
    const box = detection.boundingBox;
    return {
      ...detection,
      boundingBox: {
        originX: box.originX * scaleX,
        originY: box.originY * scaleY,
        width: box.width * scaleX,
        height: box.height * scaleY
      }
    };
  }

  async function runDetector(input) {
    let results;
    if (detectorType === "mediapipe") {
      results = detector.detect(input.canvas).detections || [];
    } else {
      const nativeResults = await detector.detect(input.canvas);
      results = nativeResults.map((detection) => normalizeNativeDetection(detection, input.canvas));
    }
    return results.map((detection) => remapDetection(detection, input.scaleX, input.scaleY));
  }

  function clearOverlay() {
    const context = elements.overlay.getContext("2d");
    context.clearRect(0, 0, elements.overlay.width, elements.overlay.height);
  }

  function detectionBox(detection, padding = 0) {
    const box = detection.boundingBox;
    const padX = box.width * padding;
    const padY = box.height * padding;
    const x = Math.round(clamp(box.originX - padX, 0, elements.source.width - 1));
    const y = Math.round(clamp(box.originY - padY, 0, elements.source.height - 1));
    const width = Math.round(clamp(box.width + padX * 2, 1, elements.source.width - x));
    const height = Math.round(clamp(box.height + padY * 2, 1, elements.source.height - y));
    return { x, y, width, height };
  }

  function drawOverlay() {
    elements.overlay.width = elements.source.width;
    elements.overlay.height = elements.source.height;
    elements.overlay.style.width = elements.source.style.width;
    elements.overlay.style.height = elements.source.style.height;
    clearOverlay();
    if (!detections.length) return;

    const context = elements.overlay.getContext("2d");
    const scale = Math.max(elements.overlay.width, elements.overlay.height);
    const lineWidth = Math.max(2, Math.round(scale / 650));
    const fontSize = Math.max(13, Math.round(scale / 55));

    detections.forEach((detection, index) => {
      const { x, y, width, height } = detectionBox(detection);
      const score = Math.round((detection.categories?.[0]?.score || 0) * 100);
      if (elements.showBoxes.checked) {
        context.save();
        context.strokeStyle = "#79b8ff";
        context.lineWidth = lineWidth;
        context.setLineDash([lineWidth * 4, lineWidth * 2]);
        context.strokeRect(x, y, width, height);
        context.setLineDash([]);
        context.font = `700 ${fontSize}px Segoe UI, sans-serif`;
        const label = `FACE ${index + 1} · ${score}%`;
        const metrics = context.measureText(label);
        const labelHeight = fontSize + 12;
        const labelY = Math.max(0, y - labelHeight);
        context.fillStyle = "rgba(10, 18, 25, .9)";
        context.fillRect(x, labelY, metrics.width + 16, labelHeight);
        context.fillStyle = "#d9ebff";
        context.fillText(label, x + 8, labelY + fontSize + 3);
        context.restore();
      }

      if (elements.showKeypoints.checked) {
        context.save();
        (detection.keypoints || []).forEach((point) => {
          context.beginPath();
          context.arc(point.x * elements.overlay.width, point.y * elements.overlay.height, Math.max(3, lineWidth * 1.7), 0, Math.PI * 2);
          context.fillStyle = "#b8f34b";
          context.fill();
          context.strokeStyle = "rgba(10, 15, 12, .9)";
          context.lineWidth = lineWidth;
          context.stroke();
        });
        context.restore();
      }
    });
  }

  function renderResults() {
    const scores = detections.map((item) => item.categories?.[0]?.score || 0);
    const average = scores.length ? scores.reduce((sum, score) => sum + score, 0) / scores.length : 0;
    const keypointTotal = detections.reduce((sum, item) => sum + (item.keypoints?.length || 0), 0);
    elements.faceCount.textContent = String(detections.length);
    elements.confidence.textContent = detections.length ? `${Math.round(average * 100)}%` : "—";
    elements.keypointCount.textContent = String(keypointTotal);
    elements.results.hidden = false;
    elements.pixelateButton.disabled = detections.length === 0;
    elements.blurButton.disabled = detections.length === 0;
    elements.faceList.innerHTML = detections.length
      ? detections.map((detection, index) => {
        const box = detectionBox(detection);
        const score = Math.round((detection.categories?.[0]?.score || 0) * 100);
        return `<div class="face-result-item">
          <span class="face-result-index">${String(index + 1).padStart(2, "0")}</span>
          <span class="face-result-copy"><strong>臉部 ${index + 1}</strong><small>${box.width} × ${box.height} px · 信心 ${score}%</small></span>
          <button class="face-crop-button" type="button" data-face-crop="${index}" aria-label="裁切臉部 ${index + 1}">裁切</button>
        </div>`;
      }).join("")
      : `<div class="face-result-item"><span class="face-result-index">00</span><span class="face-result-copy"><strong>未偵測到臉部</strong><small>可嘗試較正面、明亮且清楚的影像</small></span></div>`;
    drawOverlay();
  }

  async function analyzeFaces() {
    if (!window.ImageStudio?.hasImage() || analysisRunning) return;
    const runId = ++analysisRunId;
    analysisRunning = true;
    elements.analyzeButton.disabled = true;
    elements.error.hidden = true;
    try {
      await ensureDetector();
      if (runId !== analysisRunId) return;
      const input = createDetectionInput();
      setProgress(true, `AI 正在分析 ${input.canvas.width} × ${input.canvas.height} 推論影像…`);
      await new Promise((resolve) => requestAnimationFrame(resolve));
      const startedAt = performance.now();
      const nextDetections = await runDetector(input);
      if (runId !== analysisRunId) return;
      detections = nextDetections;
      renderResults();
      elements.analyzeButton.querySelector("span").textContent = "重新分析目前影像";
      const elapsedSeconds = Math.max(.1, (performance.now() - startedAt) / 1000).toFixed(1);
      window.ImageStudio.notify(detections.length
        ? `分析完成：偵測到 ${detections.length} 張臉部（${elapsedSeconds} 秒）`
        : `分析完成：未偵測到臉部（${elapsedSeconds} 秒）`);
    } catch (error) {
      if (runId === analysisRunId) showError(error);
    } finally {
      if (runId === analysisRunId) {
        analysisRunning = false;
        setProgress(false);
        elements.analyzeButton.disabled = !window.ImageStudio?.hasImage();
      }
    }
  }

  function cancelAnalysis() {
    if (!analysisRunning) return;
    analysisRunId += 1;
    analysisRunning = false;
    setProgress(false);
    elements.analyzeButton.disabled = !window.ImageStudio?.hasImage();
    window.ImageStudio.notify("已取消人臉分析");
  }

  function clearResults(markStale = false) {
    if (!detections.length && elements.results.hidden) return;
    detections = [];
    clearOverlay();
    elements.results.hidden = true;
    elements.analyzeButton.querySelector("span").textContent = markStale ? "影像已變更，重新分析" : "啟動人臉偵測";
  }

  function cropFace(index) {
    const detection = detections[index];
    if (!detection) return;
    const source = window.ImageStudio.getProcessedCanvas();
    const { x, y, width, height } = detectionBox(detection, .18);
    const output = document.createElement("canvas");
    output.width = width;
    output.height = height;
    output.getContext("2d", { alpha: true }).drawImage(source, x, y, width, height, 0, 0, width, height);
    ignoreNextRender = true;
    window.ImageStudio.commitCanvas(output, `已裁切臉部 ${index + 1}（${width} × ${height} px）`);
    clearResults();
  }

  function anonymize(mode) {
    if (!detections.length) return;
    const source = window.ImageStudio.getProcessedCanvas();
    const output = document.createElement("canvas");
    output.width = source.width;
    output.height = source.height;
    const context = output.getContext("2d", { alpha: true });
    context.drawImage(source, 0, 0);

    detections.forEach((detection) => {
      const { x, y, width, height } = detectionBox(detection, .08);
      if (mode === "blur") {
        context.save();
        context.beginPath();
        context.ellipse(x + width / 2, y + height / 2, width / 2, height / 2, 0, 0, Math.PI * 2);
        context.clip();
        context.filter = `blur(${Math.max(12, Math.round(width / 10))}px)`;
        context.drawImage(source, 0, 0);
        context.restore();
      } else {
        const pixelSize = Math.max(8, Math.round(Math.min(width, height) / 14));
        const small = document.createElement("canvas");
        small.width = Math.max(1, Math.ceil(width / pixelSize));
        small.height = Math.max(1, Math.ceil(height / pixelSize));
        small.getContext("2d").drawImage(source, x, y, width, height, 0, 0, small.width, small.height);
        context.save();
        context.beginPath();
        context.ellipse(x + width / 2, y + height / 2, width / 2, height / 2, 0, 0, Math.PI * 2);
        context.clip();
        context.imageSmoothingEnabled = false;
        context.drawImage(small, 0, 0, small.width, small.height, x, y, width, height);
        context.restore();
      }
    });

    ignoreNextRender = true;
    const label = mode === "blur" ? "模糊" : "像素化";
    window.ImageStudio.commitCanvas(output, `已將 ${detections.length} 張臉部${label}`);
    clearResults();
  }

  elements.analyzeButton.addEventListener("click", analyzeFaces);
  elements.cancelButton.addEventListener("click", cancelAnalysis);
  elements.retryButton.addEventListener("click", () => ensureDetector(true).catch(() => {}));
  elements.showBoxes.addEventListener("change", drawOverlay);
  elements.showKeypoints.addEventListener("change", drawOverlay);
  elements.pixelateButton.addEventListener("click", () => anonymize("pixelate"));
  elements.blurButton.addEventListener("click", () => anonymize("blur"));
  elements.faceList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-face-crop]");
    if (button) cropFace(Number(button.dataset.faceCrop));
  });

  window.addEventListener("image-studio:render", () => {
    elements.overlay.style.width = elements.source.style.width;
    elements.overlay.style.height = elements.source.style.height;
    if (ignoreNextRender) {
      ignoreNextRender = false;
      return;
    }
    if (!analysisRunning && detections.length) clearResults(true);
  });
})();
