"use strict";

const MAX_PIXELS = 32_000_000;
const MAX_HISTORY = 12;
const DEFAULT_SETTINGS = Object.freeze({
  brightness: 0,
  contrast: 0,
  saturation: 0,
  temperature: 0,
  blur: 0,
  grayscale: 0,
  sepia: 0,
  rotation: 0,
  flipX: false,
  flipY: false
});

const PRESETS = Object.freeze({
  original: {},
  clean: { brightness: 6, contrast: 8, saturation: -4 },
  punch: { brightness: 2, contrast: 22, saturation: 28 },
  warm: { brightness: 5, contrast: 6, saturation: 10, temperature: 34, sepia: 8 },
  cool: { contrast: 10, saturation: -2, temperature: -32 },
  mono: { contrast: 18, saturation: -100, grayscale: 100 }
});

const MIME_LABELS = {
  "image/png": "PNG",
  "image/jpeg": "JPEG",
  "image/bmp": "BMP",
  "image/x-ms-bmp": "BMP",
  "image/webp": "WebP",
  "image/gif": "GIF"
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const elements = {
  fileInput: $("#fileInput"),
  uploadCard: $("#uploadCard"),
  sampleButton: $("#sampleButton"),
  emptyUploadButton: $("#emptyUploadButton"),
  emptyCanvas: $("#emptyCanvas"),
  canvasViewport: $("#canvasViewport"),
  canvasFrame: $("#canvasFrame"),
  canvasStack: $("#canvasStack"),
  editCanvas: $("#editCanvas"),
  analysisCanvas: $("#analysisCanvas"),
  compareCanvas: $("#compareCanvas"),
  faceOverlay: $("#faceOverlay"),
  compareButton: $("#compareButton"),
  compareDivider: $("#compareDivider"),
  compareRangeWrap: $("#compareRangeWrap"),
  compareRange: $("#compareRange"),
  cropOverlay: $("#cropOverlay"),
  cropOverlayLabel: $("#cropOverlayLabel"),
  resizeOverlay: $("#resizeOverlay"),
  resizeOverlayLabel: $("#resizeOverlayLabel"),
  toggleResizeDrag: $("#toggleResizeDrag"),
  toggleCropDrag: $("#toggleCropDrag"),
  resizeDetails: $("#resizeDetails"),
  cropDetails: $("#cropDetails"),
  cropHelp: $("#cropHelp"),
  cropX: $("#cropX"),
  cropY: $("#cropY"),
  cropWidth: $("#cropWidth"),
  cropHeight: $("#cropHeight"),
  resetCrop: $("#resetCrop"),
  applyCrop: $("#applyCrop"),
  resizeWidth: $("#resizeWidth"),
  resizeHeight: $("#resizeHeight"),
  ratioLock: $("#ratioLock"),
  applyResize: $("#applyResize"),
  undoButton: $("#undoButton"),
  redoButton: $("#redoButton"),
  resetButton: $("#resetButton"),
  resetAdjustments: $("#resetAdjustments"),
  rotateLeft: $("#rotateLeft"),
  rotateRight: $("#rotateRight"),
  flipHorizontal: $("#flipHorizontal"),
  flipVertical: $("#flipVertical"),
  zoomSelect: $("#zoomSelect"),
  fileName: $("#fileName"),
  fileMeta: $("#fileMeta"),
  canvasStatus: $("#canvasStatus"),
  histogramCanvas: $("#histogramCanvas"),
  histogramEmpty: $("#histogramEmpty"),
  analysisStatus: $("#analysisStatus"),
  statDimensions: $("#statDimensions"),
  statMegapixels: $("#statMegapixels"),
  statFormat: $("#statFormat"),
  statSize: $("#statSize"),
  statChannels: $("#statChannels"),
  statBitDepth: $("#statBitDepth"),
  formatField: $("#formatField"),
  qualityRange: $("#qualityRange"),
  qualityValue: $("#qualityValue"),
  exportName: $("#exportName"),
  exportEstimate: $("#exportEstimate"),
  downloadButton: $("#downloadButton"),
  exportShortcut: $("#exportShortcut"),
  toast: $("#toast"),
  liveRegion: $("#liveRegion")
};

const baseCanvas = document.createElement("canvas");
const originalCanvas = document.createElement("canvas");
const comparisonOverrideCanvas = document.createElement("canvas");
const settings = { ...DEFAULT_SETTINGS };
const undoStack = [];
const redoStack = [];

let fileInfo = null;
let renderFrame = 0;
let estimateTimer = 0;
let estimateSequence = 0;
let toastTimer = 0;
let ratioLocked = true;
let compareActive = false;
let temporaryCompare = false;
let activeComparePointerId = null;
let canvasToolMode = null;
let canvasToolDrag = null;
let hasComparisonOverride = false;
let restoringHistory = false;

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return "—";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / (1024 ** index);
  return `${value.toFixed(index === 0 || value >= 10 ? 0 : 1)} ${units[index]}`;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, Number(value) || 0));
}

function sanitizeFileName(value) {
  const clean = String(value || "processed-image")
    .trim()
    .replace(/[\\/:*?"<>|]+/g, "-")
    .replace(/\s+/g, "-")
    .replace(/^-+|-+$/g, "");
  return clean || "processed-image";
}

function showToast(message) {
  elements.toast.textContent = message;
  elements.toast.classList.add("is-visible");
  elements.liveRegion.textContent = message;
  clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => elements.toast.classList.remove("is-visible"), 2800);
}

function setLoadedControls(enabled) {
  const selectors = [
    "#presetGrid button", "#adjustmentControls input", "#resetAdjustments",
    "#rotateLeft", "#rotateRight", "#flipHorizontal", "#flipVertical",
    "#resizeWidth", "#resizeHeight", "#ratioLock", "#applyResize",
    "#toggleResizeDrag", "#cropX", "#cropY", "#cropWidth", "#cropHeight", "#toggleCropDrag", "#resetCrop", "#applyCrop", "#analyzeFacesButton",
    "#kernelSize", "#kernelPreset", "#kernelNormalization", "#kernelDivisor", "#kernelBias", "#applyKernel", ".kernel-cell", ".channel-mode",
    "#resetButton", "#compareButton", "#zoomSelect", "#exportName", "#downloadButton", "#exportShortcut"
  ];
  selectors.forEach((selector) => $$(selector).forEach((element) => { element.disabled = !enabled; }));
  elements.formatField.disabled = !enabled;
  updateQualityAvailability();
  updateHistoryButtons();
}

function updateHistoryButtons() {
  const loaded = Boolean(fileInfo);
  elements.undoButton.disabled = !loaded || undoStack.length === 0 || restoringHistory;
  elements.redoButton.disabled = !loaded || redoStack.length === 0 || restoringHistory;
}

function snapshot() {
  return {
    base: baseCanvas.toDataURL("image/png"),
    settings: { ...settings }
  };
}

function pushHistory() {
  if (!fileInfo || restoringHistory) return;
  undoStack.push(snapshot());
  if (undoStack.length > MAX_HISTORY) undoStack.shift();
  redoStack.length = 0;
  hasComparisonOverride = false;
  updateHistoryButtons();
}

function loadDataUrlIntoCanvas(dataUrl, targetCanvas) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => {
      targetCanvas.width = image.naturalWidth;
      targetCanvas.height = image.naturalHeight;
      const context = targetCanvas.getContext("2d", { alpha: true });
      context.clearRect(0, 0, targetCanvas.width, targetCanvas.height);
      context.drawImage(image, 0, 0);
      resolve();
    };
    image.onerror = reject;
    image.src = dataUrl;
  });
}

async function restoreSnapshot(target) {
  restoringHistory = true;
  updateHistoryButtons();
  try {
    await loadDataUrlIntoCanvas(target.base, baseCanvas);
    Object.assign(settings, DEFAULT_SETTINGS, target.settings);
    syncControlsFromSettings();
    resetCropInputs();
    syncResizeInputs();
    requestRender();
  } finally {
    restoringHistory = false;
    updateHistoryButtons();
  }
}

async function undo() {
  if (!undoStack.length || restoringHistory) return;
  const target = undoStack.pop();
  redoStack.push(snapshot());
  await restoreSnapshot(target);
  showToast("已復原上一個動作");
}

async function redo() {
  if (!redoStack.length || restoringHistory) return;
  const target = redoStack.pop();
  undoStack.push(snapshot());
  await restoreSnapshot(target);
  showToast("已重做上一個動作");
}

function resetSettings() {
  Object.assign(settings, DEFAULT_SETTINGS);
  syncControlsFromSettings();
}

function valueLabel(setting, value) {
  if (setting === "blur") return `${Number(value).toFixed(value % 1 ? 1 : 0)} px`;
  if (setting === "grayscale" || setting === "sepia") return `${value}%`;
  return value > 0 ? `+${value}` : String(value);
}

function updateRangeTrack(input) {
  const min = Number(input.min || 0);
  const max = Number(input.max || 100);
  const progress = ((Number(input.value) - min) / (max - min)) * 100;
  input.style.setProperty("--range-p", `${progress}%`);
}

function syncControlsFromSettings() {
  $$("[data-setting]").forEach((input) => {
    const key = input.dataset.setting;
    input.value = settings[key];
    const output = $(`#${key}Value`);
    if (output) output.textContent = valueLabel(key, settings[key]);
    updateRangeTrack(input);
  });

  const presetName = Object.entries(PRESETS).find(([, values]) => {
    const keys = ["brightness", "contrast", "saturation", "temperature", "blur", "grayscale", "sepia"];
    return keys.every((key) => settings[key] === (values[key] ?? 0));
  })?.[0];
  $$("[data-preset]").forEach((button) => button.classList.toggle("is-active", button.dataset.preset === presetName));
}

function createCanvas(width, height) {
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(width));
  canvas.height = Math.max(1, Math.round(height));
  return canvas;
}

function copyCanvas(source, target) {
  target.width = source.width;
  target.height = source.height;
  const context = target.getContext("2d", { alpha: true });
  context.clearRect(0, 0, target.width, target.height);
  context.drawImage(source, 0, 0);
}

function createTransformedCanvas(source) {
  const normalizedRotation = ((settings.rotation % 360) + 360) % 360;
  const swapDimensions = normalizedRotation === 90 || normalizedRotation === 270;
  const output = createCanvas(
    swapDimensions ? source.height : source.width,
    swapDimensions ? source.width : source.height
  );
  const context = output.getContext("2d", { alpha: true });
  context.save();
  context.translate(output.width / 2, output.height / 2);
  context.rotate(normalizedRotation * Math.PI / 180);
  context.scale(settings.flipX ? -1 : 1, settings.flipY ? -1 : 1);
  context.drawImage(source, -source.width / 2, -source.height / 2);
  context.restore();
  return output;
}

function renderNow() {
  if (!fileInfo || !baseCanvas.width || !baseCanvas.height) return;

  const before = createTransformedCanvas(baseCanvas);
  const editContext = elements.editCanvas.getContext("2d", { alpha: true });
  const compareContext = elements.compareCanvas.getContext("2d", { alpha: true });
  elements.editCanvas.width = before.width;
  elements.editCanvas.height = before.height;
  elements.compareCanvas.width = before.width;
  elements.compareCanvas.height = before.height;

  compareContext.clearRect(0, 0, before.width, before.height);
  const compareSource = hasComparisonOverride
    && comparisonOverrideCanvas.width === before.width
    && comparisonOverrideCanvas.height === before.height
    ? comparisonOverrideCanvas
    : before;
  compareContext.drawImage(compareSource, 0, 0);

  const brightness = Math.max(0, 100 + settings.brightness);
  const contrast = Math.max(0, 100 + settings.contrast);
  const saturation = Math.max(0, 100 + settings.saturation);
  editContext.clearRect(0, 0, before.width, before.height);
  editContext.filter = [
    `brightness(${brightness}%)`,
    `contrast(${contrast}%)`,
    `saturate(${saturation}%)`,
    `blur(${settings.blur}px)`,
    `grayscale(${settings.grayscale}%)`,
    `sepia(${settings.sepia}%)`
  ].join(" ");
  editContext.drawImage(before, 0, 0);
  editContext.filter = "none";

  if (settings.temperature !== 0) {
    const strength = Math.min(.34, Math.abs(settings.temperature) / 295);
    editContext.save();
    editContext.globalCompositeOperation = "soft-light";
    editContext.fillStyle = settings.temperature > 0
      ? `rgba(255, 126, 38, ${strength})`
      : `rgba(43, 126, 255, ${strength})`;
    editContext.fillRect(0, 0, before.width, before.height);
    editContext.restore();
  }

  updateCanvasDisplay();
  updateCompareView();
  updateCropOverlay();
  updateImageStats();
  drawHistogram();
  scheduleExportEstimate();
  window.dispatchEvent(new CustomEvent("image-studio:render", {
    detail: { width: elements.editCanvas.width, height: elements.editCanvas.height }
  }));
}

function requestRender() {
  cancelAnimationFrame(renderFrame);
  renderFrame = requestAnimationFrame(renderNow);
}

function updateCanvasDisplay() {
  if (!elements.editCanvas.width) return;
  const viewportWidth = Math.max(280, elements.canvasViewport.clientWidth - 64);
  const viewportHeight = Math.max(240, elements.canvasViewport.clientHeight - 64);
  const fitScale = Math.min(
    viewportWidth / elements.editCanvas.width,
    viewportHeight / elements.editCanvas.height,
    1
  );
  const selected = elements.zoomSelect.value;
  const scale = selected === "fit" ? fitScale : Number(selected);
  const displayWidth = Math.max(1, Math.round(elements.editCanvas.width * scale));
  const displayHeight = Math.max(1, Math.round(elements.editCanvas.height * scale));

  elements.canvasFrame.style.width = `${displayWidth}px`;
  elements.canvasFrame.style.height = `${displayHeight}px`;
  elements.canvasStack.style.width = `${displayWidth}px`;
  elements.canvasStack.style.height = `${displayHeight}px`;
  [elements.editCanvas, elements.analysisCanvas, elements.compareCanvas, elements.faceOverlay].forEach((canvas) => {
    canvas.style.width = `${displayWidth}px`;
    canvas.style.height = `${displayHeight}px`;
  });
  elements.canvasStatus.textContent = `${Math.round(scale * 100)}% · ${elements.editCanvas.width.toLocaleString()} × ${elements.editCanvas.height.toLocaleString()} px`;
  if (canvasToolMode === "resize") updateResizeOverlay();
  if (canvasToolMode === "crop") updateCropOverlay();
}

function updateCompareView() {
  const visible = compareActive || temporaryCompare;
  elements.compareCanvas.hidden = !visible;
  elements.compareRangeWrap.hidden = !compareActive;
  elements.compareDivider.hidden = !compareActive;
  if (temporaryCompare && !compareActive) {
    elements.compareCanvas.style.clipPath = "inset(0 0 0 0)";
    return;
  }
  const value = Number(elements.compareRange.value);
  elements.compareCanvas.style.clipPath = `inset(0 ${100 - value}% 0 0)`;
  elements.compareDivider.style.left = `${value}%`;
}

function clearCompareView() {
  compareActive = false;
  temporaryCompare = false;
  activeComparePointerId = null;
  elements.compareButton.setAttribute("aria-pressed", "false");
  elements.compareDivider.classList.remove("is-dragging");
  updateCompareView();
}

function updateCompareFromPointer(clientX) {
  const bounds = elements.canvasStack.getBoundingClientRect();
  if (!bounds.width) return;
  const value = clamp(((clientX - bounds.left) / bounds.width) * 100, 0, 100);
  elements.compareRange.value = String(Math.round(value * 10) / 10);
  updateRangeTrack(elements.compareRange);
  updateCompareView();
}

function beginCompareDrag(event) {
  if (!compareActive || (event.pointerType === "mouse" && event.button !== 0)) return;
  event.preventDefault();
  activeComparePointerId = event.pointerId;
  elements.compareDivider.classList.add("is-dragging");
  elements.compareDivider.setPointerCapture?.(event.pointerId);
  updateCompareFromPointer(event.clientX);
}

function moveCompareDrag(event) {
  if (event.pointerId !== activeComparePointerId) return;
  event.preventDefault();
  updateCompareFromPointer(event.clientX);
}

function endCompareDrag(event) {
  if (event.pointerId !== activeComparePointerId) return;
  if (elements.compareDivider.hasPointerCapture?.(event.pointerId)) {
    elements.compareDivider.releasePointerCapture(event.pointerId);
  }
  activeComparePointerId = null;
  elements.compareDivider.classList.remove("is-dragging");
}

function selectedFormat() {
  return $("input[name='format']:checked").value;
}

function updateQualityAvailability() {
  const loaded = Boolean(fileInfo);
  const lossy = selectedFormat() !== "image/png";
  elements.qualityRange.disabled = !loaded || !lossy;
  elements.qualityValue.textContent = lossy ? `${elements.qualityRange.value}%` : "無損";
  updateRangeTrack(elements.qualityRange);
}

function scheduleExportEstimate() {
  clearTimeout(estimateTimer);
  const sequence = ++estimateSequence;
  estimateTimer = window.setTimeout(() => {
    if (!fileInfo || sequence !== estimateSequence) return;
    const type = selectedFormat();
    const quality = Number(elements.qualityRange.value) / 100;
    elements.editCanvas.toBlob((blob) => {
      if (!blob || sequence !== estimateSequence) return;
      elements.exportEstimate.textContent = `${formatBytes(blob.size)} · ${MIME_LABELS[type]}`;
    }, type, quality);
  }, 260);
}

function updateImageStats() {
  const width = elements.editCanvas.width;
  const height = elements.editCanvas.height;
  const megapixels = width * height / 1_000_000;
  elements.statDimensions.textContent = `${width.toLocaleString()} × ${height.toLocaleString()}`;
  elements.statMegapixels.textContent = `${megapixels.toFixed(megapixels < 10 ? 1 : 0)} MP`;
  elements.statFormat.textContent = MIME_LABELS[fileInfo.type] || "影像";
  elements.statSize.textContent = formatBytes(fileInfo.size);
  elements.statChannels.textContent = "RGBA · 4 通道";
  elements.statBitDepth.textContent = "8 bit / channel";
  elements.fileMeta.textContent = `${width.toLocaleString()} × ${height.toLocaleString()} px · ${formatBytes(fileInfo.size)}`;
}

function drawHistogram() {
  if (!fileInfo) return;
  const source = elements.editCanvas;
  const sample = createCanvas(Math.min(320, source.width), Math.min(220, source.height));
  const sampleContext = sample.getContext("2d", { willReadFrequently: true });
  const ratio = Math.min(sample.width / source.width, sample.height / source.height);
  sample.width = Math.max(1, Math.round(source.width * ratio));
  sample.height = Math.max(1, Math.round(source.height * ratio));
  sampleContext.drawImage(source, 0, 0, sample.width, sample.height);

  const pixels = sampleContext.getImageData(0, 0, sample.width, sample.height).data;
  const bins = new Uint32Array(256);
  for (let index = 0; index < pixels.length; index += 4) {
    if (pixels[index + 3] === 0) continue;
    const luminance = Math.round(.2126 * pixels[index] + .7152 * pixels[index + 1] + .0722 * pixels[index + 2]);
    bins[luminance] += 1;
  }

  const canvas = elements.histogramCanvas;
  const context = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const max = Math.max(...bins) || 1;
  context.clearRect(0, 0, width, height);
  const gradient = context.createLinearGradient(0, 0, width, 0);
  gradient.addColorStop(0, "rgba(121, 184, 255, .72)");
  gradient.addColorStop(.55, "rgba(184, 243, 75, .8)");
  gradient.addColorStop(1, "rgba(255, 196, 107, .76)");
  context.beginPath();
  context.moveTo(0, height);
  bins.forEach((count, index) => {
    const x = index / 255 * width;
    const y = height - (count / max) * (height - 8);
    context.lineTo(x, y);
  });
  context.lineTo(width, height);
  context.closePath();
  context.fillStyle = gradient;
  context.fill();

  elements.histogramEmpty.hidden = true;
  elements.analysisStatus.textContent = "即時分析";
  elements.analysisStatus.classList.add("is-ready");
}

function resetCropInputs() {
  elements.cropX.value = 0;
  elements.cropY.value = 0;
  elements.cropWidth.value = baseCanvas.width || "";
  elements.cropHeight.value = baseCanvas.height || "";
  [elements.cropX, elements.cropY].forEach((input) => { input.max = Math.max(0, (input === elements.cropX ? baseCanvas.width : baseCanvas.height) - 1); });
  elements.cropWidth.max = baseCanvas.width || 1;
  elements.cropHeight.max = baseCanvas.height || 1;
  updateCropOverlay();
}

function cropValues() {
  const x = Math.round(clamp(elements.cropX.value, 0, Math.max(0, baseCanvas.width - 1)));
  const y = Math.round(clamp(elements.cropY.value, 0, Math.max(0, baseCanvas.height - 1)));
  const width = Math.round(clamp(elements.cropWidth.value, 1, baseCanvas.width - x));
  const height = Math.round(clamp(elements.cropHeight.value, 1, baseCanvas.height - y));
  return { x, y, width, height };
}

function updateCropOverlay() {
  if (!fileInfo || !elements.cropDetails.open) {
    elements.cropOverlay.hidden = true;
    return;
  }
  const transformed = settings.rotation % 360 !== 0 || settings.flipX || settings.flipY;
  elements.cropHelp.classList.toggle("is-warning", transformed);
  elements.cropHelp.textContent = transformed
    ? "裁切座標以旋轉前影像為準；套用後仍會保留目前方向。"
    : "輸入像素範圍，或直接在畫布拖曳裁切框。";

  if (transformed) {
    elements.cropOverlay.hidden = true;
    return;
  }
  const { x, y, width, height } = cropValues();
  elements.cropOverlay.hidden = false;
  elements.cropOverlay.style.left = `${x / baseCanvas.width * 100}%`;
  elements.cropOverlay.style.top = `${y / baseCanvas.height * 100}%`;
  elements.cropOverlay.style.width = `${width / baseCanvas.width * 100}%`;
  elements.cropOverlay.style.height = `${height / baseCanvas.height * 100}%`;
  elements.cropOverlayLabel.textContent = `${width.toLocaleString()} × ${height.toLocaleString()} px`;
  elements.cropOverlay.style.setProperty("--crop-third", `${elements.cropOverlay.clientHeight / 3}px`);
  elements.cropOverlay.style.setProperty("--crop-third-x", `${elements.cropOverlay.clientWidth / 3}px`);
}

function hasDirectionTransform() {
  return settings.rotation % 360 !== 0 || settings.flipX || settings.flipY;
}

function setCanvasToolMode(mode) {
  if (mode && hasDirectionTransform()) {
    showToast("請先將旋轉與翻轉還原，再使用畫布拖曳工具");
    return;
  }
  canvasToolMode = canvasToolMode === mode ? null : mode;
  elements.toggleResizeDrag.setAttribute("aria-pressed", String(canvasToolMode === "resize"));
  elements.toggleCropDrag.setAttribute("aria-pressed", String(canvasToolMode === "crop"));
  elements.resizeOverlay.hidden = canvasToolMode !== "resize";
  elements.canvasStack.classList.toggle("is-resize-tool", canvasToolMode === "resize");
  elements.canvasStack.classList.toggle("is-crop-tool", canvasToolMode === "crop");

  if (canvasToolMode === "resize") {
    elements.resizeDetails.open = true;
    updateResizeOverlay();
  }
  if (canvasToolMode === "crop") {
    elements.cropDetails.open = true;
    const values = cropValues();
    if (values.x === 0 && values.y === 0 && values.width === baseCanvas.width && values.height === baseCanvas.height) {
      const marginX = Math.max(1, Math.round(baseCanvas.width * .1));
      const marginY = Math.max(1, Math.round(baseCanvas.height * .1));
      setCropInputs(marginX, marginY, baseCanvas.width - marginX * 2, baseCanvas.height - marginY * 2);
    }
    updateCropOverlay();
  }
}

function updateResizeOverlay(handle = "se") {
  if (!fileInfo || canvasToolMode !== "resize") return;
  const width = Math.round(clamp(elements.resizeWidth.value, 1, 12000));
  const height = Math.round(clamp(elements.resizeHeight.value, 1, 12000));
  const widthPercent = width / baseCanvas.width * 100;
  const heightPercent = height / baseCanvas.height * 100;
  elements.resizeOverlay.style.width = `${widthPercent}%`;
  elements.resizeOverlay.style.height = `${heightPercent}%`;
  elements.resizeOverlay.style.left = handle.includes("w") ? `${100 - widthPercent}%` : "0";
  elements.resizeOverlay.style.top = handle.includes("n") ? `${100 - heightPercent}%` : "0";
  elements.resizeOverlayLabel.textContent = `${width.toLocaleString()} × ${height.toLocaleString()} px`;
}

function setCropInputs(x, y, width, height) {
  const safeX = Math.round(clamp(x, 0, Math.max(0, baseCanvas.width - 1)));
  const safeY = Math.round(clamp(y, 0, Math.max(0, baseCanvas.height - 1)));
  elements.cropX.value = safeX;
  elements.cropY.value = safeY;
  elements.cropWidth.value = Math.round(clamp(width, 1, baseCanvas.width - safeX));
  elements.cropHeight.value = Math.round(clamp(height, 1, baseCanvas.height - safeY));
  updateCropOverlay();
}

function canvasPoint(event) {
  const bounds = elements.canvasStack.getBoundingClientRect();
  return {
    x: clamp((event.clientX - bounds.left) / bounds.width * baseCanvas.width, 0, baseCanvas.width),
    y: clamp((event.clientY - bounds.top) / bounds.height * baseCanvas.height, 0, baseCanvas.height)
  };
}

function beginCanvasToolDrag(event) {
  if (!canvasToolMode || (event.pointerType === "mouse" && event.button !== 0)) return;
  const resizeHandle = event.target.closest?.("[data-resize-handle]");
  const cropHandle = event.target.closest?.("[data-crop-handle]");

  if (canvasToolMode === "resize" && !resizeHandle) return;
  event.preventDefault();
  const startPoint = canvasPoint(event);

  if (canvasToolMode === "resize") {
    canvasToolDrag = {
      pointerId: event.pointerId,
      kind: "resize",
      handle: resizeHandle.dataset.resizeHandle,
      startPoint,
      width: Number(elements.resizeWidth.value),
      height: Number(elements.resizeHeight.value)
    };
  } else {
    const current = cropValues();
    const insideOverlay = event.target.closest?.("#cropOverlay");
    canvasToolDrag = {
      pointerId: event.pointerId,
      kind: cropHandle ? "crop-resize" : insideOverlay ? "crop-move" : "crop-new",
      handle: cropHandle?.dataset.cropHandle || "",
      startPoint,
      current
    };
    if (!insideOverlay) setCropInputs(startPoint.x, startPoint.y, 1, 1);
  }

  elements.canvasStack.setPointerCapture?.(event.pointerId);
}

function moveCanvasToolDrag(event) {
  if (!canvasToolDrag || canvasToolDrag.pointerId !== event.pointerId) return;
  event.preventDefault();
  const point = canvasPoint(event);
  const drag = canvasToolDrag;

  if (drag.kind === "resize") {
    const directionX = drag.handle.includes("w") ? -1 : 1;
    const directionY = drag.handle.includes("n") ? -1 : 1;
    let width = clamp(drag.width + (point.x - drag.startPoint.x) * directionX, 1, 12000);
    let height = clamp(drag.height + (point.y - drag.startPoint.y) * directionY, 1, 12000);
    if (ratioLocked) {
      const widthChange = Math.abs(width / drag.width - 1);
      const heightChange = Math.abs(height / drag.height - 1);
      if (widthChange >= heightChange) height = width * baseCanvas.height / baseCanvas.width;
      else width = height * baseCanvas.width / baseCanvas.height;
    }
    if (width * height > MAX_PIXELS) {
      const safeScale = Math.sqrt(MAX_PIXELS / (width * height));
      width *= safeScale;
      height *= safeScale;
    }
    elements.resizeWidth.value = Math.max(1, Math.round(width));
    elements.resizeHeight.value = Math.max(1, Math.round(height));
    updateResizeOverlay(drag.handle);
    return;
  }

  if (drag.kind === "crop-new") {
    setCropInputs(
      Math.min(drag.startPoint.x, point.x),
      Math.min(drag.startPoint.y, point.y),
      Math.max(1, Math.abs(point.x - drag.startPoint.x)),
      Math.max(1, Math.abs(point.y - drag.startPoint.y))
    );
    return;
  }

  if (drag.kind === "crop-move") {
    const dx = point.x - drag.startPoint.x;
    const dy = point.y - drag.startPoint.y;
    setCropInputs(
      clamp(drag.current.x + dx, 0, baseCanvas.width - drag.current.width),
      clamp(drag.current.y + dy, 0, baseCanvas.height - drag.current.height),
      drag.current.width,
      drag.current.height
    );
    return;
  }

  const left = drag.current.x;
  const top = drag.current.y;
  const right = left + drag.current.width;
  const bottom = top + drag.current.height;
  const anchorX = drag.handle.includes("w") ? right : left;
  const anchorY = drag.handle.includes("n") ? bottom : top;
  setCropInputs(
    Math.min(anchorX, point.x),
    Math.min(anchorY, point.y),
    Math.max(1, Math.abs(point.x - anchorX)),
    Math.max(1, Math.abs(point.y - anchorY))
  );
}

function endCanvasToolDrag(event) {
  if (!canvasToolDrag || canvasToolDrag.pointerId !== event.pointerId) return;
  if (elements.canvasStack.hasPointerCapture?.(event.pointerId)) elements.canvasStack.releasePointerCapture(event.pointerId);
  canvasToolDrag = null;
}

function syncResizeInputs() {
  elements.resizeWidth.value = baseCanvas.width || "";
  elements.resizeHeight.value = baseCanvas.height || "";
}

function setBaseFromCanvas(source) {
  copyCanvas(source, baseCanvas);
  resetCropInputs();
  syncResizeInputs();
}

function resetWorkspace() {
  if (!fileInfo) return;
  pushHistory();
  copyCanvas(originalCanvas, baseCanvas);
  resetSettings();
  resetCropInputs();
  syncResizeInputs();
  setCanvasToolMode(null);
  clearCompareView();
  window.dispatchEvent(new CustomEvent("image-studio:workspace-reset"));
  requestRender();
  showToast("已還原為載入時的原始影像");
}

function applyPreset(name) {
  if (!fileInfo || !PRESETS[name]) return;
  pushHistory();
  const transforms = { rotation: settings.rotation, flipX: settings.flipX, flipY: settings.flipY };
  Object.assign(settings, DEFAULT_SETTINGS, transforms, PRESETS[name]);
  syncControlsFromSettings();
  requestRender();
  showToast(`已套用「${$("[data-preset='" + name + "'] span:last-child").textContent}」風格`);
}

function applyCrop() {
  if (!fileInfo) return;
  const { x, y, width, height } = cropValues();
  if (x === 0 && y === 0 && width === baseCanvas.width && height === baseCanvas.height) {
    showToast("目前已是完整影像範圍");
    return;
  }
  pushHistory();
  const output = createCanvas(width, height);
  output.getContext("2d", { alpha: true }).drawImage(baseCanvas, x, y, width, height, 0, 0, width, height);
  setBaseFromCanvas(output);
  setCanvasToolMode(null);
  requestRender();
  showToast(`已裁切為 ${width} × ${height} px`);
}

function applyResize() {
  if (!fileInfo) return;
  const width = Math.round(clamp(elements.resizeWidth.value, 1, 12000));
  const height = Math.round(clamp(elements.resizeHeight.value, 1, 12000));
  if (width * height > MAX_PIXELS) {
    showToast("尺寸過大：請將輸出控制在 3,200 萬像素內");
    return;
  }
  if (width === baseCanvas.width && height === baseCanvas.height) {
    showToast("新尺寸與目前影像相同");
    return;
  }
  pushHistory();
  const output = createCanvas(width, height);
  const context = output.getContext("2d", { alpha: true });
  context.imageSmoothingEnabled = true;
  context.imageSmoothingQuality = "high";
  context.drawImage(baseCanvas, 0, 0, width, height);
  setBaseFromCanvas(output);
  setCanvasToolMode(null);
  requestRender();
  showToast(`尺寸已調整為 ${width} × ${height} px`);
}

function updateFileUi() {
  elements.fileName.textContent = fileInfo.name;
  elements.exportName.value = sanitizeFileName(fileInfo.name.replace(/\.[^.]+$/, "")) + "-edited";
  elements.emptyCanvas.hidden = true;
  elements.canvasFrame.hidden = false;
  setLoadedControls(true);
}

async function loadImageFile(file) {
  const extension = String(file?.name || "").split(".").pop().toLowerCase();
  const supportedExtension = ["png", "jpg", "jpeg", "bmp", "webp", "gif"].includes(extension);
  if (!file || (!file.type.startsWith("image/") && !supportedExtension)) {
    showToast("請選擇 PNG、JPG/JPEG、BMP、WebP 或 GIF 影像");
    return;
  }
  if (file.size > 40 * 1024 * 1024) {
    showToast("檔案超過 40 MB，請先縮小後再載入");
    return;
  }

  const objectUrl = URL.createObjectURL(file);
  const image = new Image();
  image.decoding = "async";
  image.onload = () => {
    try {
      let width = image.naturalWidth;
      let height = image.naturalHeight;
      const pixels = width * height;
      let wasScaled = false;
      if (pixels > MAX_PIXELS) {
        const scale = Math.sqrt(MAX_PIXELS / pixels);
        width = Math.max(1, Math.floor(width * scale));
        height = Math.max(1, Math.floor(height * scale));
        wasScaled = true;
      }
      const loaded = createCanvas(width, height);
      const context = loaded.getContext("2d", { alpha: true });
      context.imageSmoothingEnabled = true;
      context.imageSmoothingQuality = "high";
      context.drawImage(image, 0, 0, width, height);

      copyCanvas(loaded, originalCanvas);
      copyCanvas(loaded, baseCanvas);
      const detectedType = file.type || ({ jpg: "image/jpeg", jpeg: "image/jpeg", bmp: "image/bmp", png: "image/png", webp: "image/webp", gif: "image/gif" }[extension] || "image/png");
      fileInfo = { name: file.name || "pasted-image.png", type: detectedType, size: file.size || 0 };
      undoStack.length = 0;
      redoStack.length = 0;
      resetSettings();
      setCanvasToolMode(null);
      resetCropInputs();
      syncResizeInputs();
      updateFileUi();
      requestRender();
      showToast(wasScaled ? "影像已載入，並為瀏覽器效能縮小至 3,200 萬像素" : "影像已載入，可以開始編輯");
    } finally {
      URL.revokeObjectURL(objectUrl);
      elements.fileInput.value = "";
    }
  };
  image.onerror = () => {
    URL.revokeObjectURL(objectUrl);
    showToast("無法讀取這個影像檔案");
  };
  image.src = objectUrl;
}

function loadSampleImage() {
  const sample = createCanvas(1600, 1000);
  const context = sample.getContext("2d");
  const sky = context.createLinearGradient(0, 0, 0, sample.height);
  sky.addColorStop(0, "#18324a");
  sky.addColorStop(.5, "#d77752");
  sky.addColorStop(1, "#f0bd75");
  context.fillStyle = sky;
  context.fillRect(0, 0, sample.width, sample.height);

  context.fillStyle = "rgba(255, 222, 159, .9)";
  context.beginPath();
  context.arc(1240, 245, 105, 0, Math.PI * 2);
  context.fill();

  const layers = [
    ["#304c54", 580, 120, 1],
    ["#263b3e", 680, 190, .88],
    ["#172a29", 790, 260, .72]
  ];
  layers.forEach(([color, top, amplitude, offset], layerIndex) => {
    context.fillStyle = color;
    context.beginPath();
    context.moveTo(0, sample.height);
    for (let x = 0; x <= sample.width; x += 40) {
      const y = top + Math.sin(x / (150 + layerIndex * 35) + offset) * amplitude * .22 + Math.sin(x / 62) * amplitude * .06;
      context.lineTo(x, y);
    }
    context.lineTo(sample.width, sample.height);
    context.closePath();
    context.fill();
  });

  context.fillStyle = "rgba(255,255,255,.88)";
  context.font = "700 92px Segoe UI, sans-serif";
  context.fillText("EXPLORE", 100, 150);
  context.fillStyle = "rgba(255,255,255,.72)";
  context.font = "500 30px Segoe UI, sans-serif";
  context.fillText("A browser-local image workflow", 106, 205);

  sample.toBlob((blob) => {
    if (!blob) return;
    loadImageFile(new File([blob], "studio-sample.png", { type: "image/png" }));
  }, "image/png");
}

function downloadImage() {
  if (!fileInfo) return;
  const type = selectedFormat();
  const quality = Number(elements.qualityRange.value) / 100;
  const extension = type === "image/jpeg" ? "jpg" : type.split("/")[1];
  const name = `${sanitizeFileName(elements.exportName.value)}.${extension}`;
  elements.downloadButton.disabled = true;
  elements.downloadButton.textContent = "正在準備影像…";
  elements.editCanvas.toBlob((blob) => {
    elements.downloadButton.disabled = false;
    elements.downloadButton.innerHTML = `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 3v12m0 0 4-4m-4 4-4-4M5 15v4h14v-4"/></svg>下載處理後影像`;
    if (!blob) {
      showToast("匯出失敗，請改用另一種格式再試一次");
      return;
    }
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    showToast(`已下載 ${name}（${formatBytes(blob.size)}）`);
  }, type, quality);
}

function bindEvents() {
  elements.fileInput.addEventListener("change", (event) => loadImageFile(event.target.files[0]));
  elements.emptyUploadButton.addEventListener("click", () => elements.fileInput.click());
  elements.sampleButton.addEventListener("click", loadSampleImage);

  [elements.uploadCard, elements.canvasViewport].forEach((target) => {
    ["dragenter", "dragover"].forEach((eventName) => target.addEventListener(eventName, (event) => {
      event.preventDefault();
      event.stopPropagation();
      elements.uploadCard.classList.add("is-dragging");
      elements.canvasViewport.classList.add("is-dragging");
    }));
    ["dragleave", "drop"].forEach((eventName) => target.addEventListener(eventName, (event) => {
      event.preventDefault();
      event.stopPropagation();
      elements.uploadCard.classList.remove("is-dragging");
      elements.canvasViewport.classList.remove("is-dragging");
      if (eventName === "drop") loadImageFile(event.dataTransfer.files[0]);
    }));
  });

  window.addEventListener("paste", (event) => {
    const file = [...event.clipboardData.files].find((item) => item.type.startsWith("image/"));
    if (file) loadImageFile(file);
  });

  $$("[data-preset]").forEach((button) => button.addEventListener("click", () => applyPreset(button.dataset.preset)));

  $$("[data-setting]").forEach((input) => {
    input.addEventListener("pointerdown", () => { input.dataset.historyArmed = "true"; });
    input.addEventListener("keydown", (event) => {
      if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End", "PageUp", "PageDown"].includes(event.key) && !event.repeat) pushHistory();
    });
    input.addEventListener("input", () => {
      if (input.dataset.historyArmed === "true") {
        pushHistory();
        input.dataset.historyArmed = "false";
      }
      const key = input.dataset.setting;
      settings[key] = Number(input.value);
      $(`#${key}Value`).textContent = valueLabel(key, settings[key]);
      updateRangeTrack(input);
      $$("[data-preset]").forEach((button) => button.classList.remove("is-active"));
      requestRender();
    });
  });

  elements.resetAdjustments.addEventListener("click", () => {
    const changed = ["brightness", "contrast", "saturation", "temperature", "blur", "grayscale", "sepia"].some((key) => settings[key] !== 0);
    if (!changed) return showToast("光線與色彩目前已是原始值");
    pushHistory();
    ["brightness", "contrast", "saturation", "temperature", "blur", "grayscale", "sepia"].forEach((key) => { settings[key] = 0; });
    syncControlsFromSettings();
    requestRender();
    showToast("光線與色彩已歸零");
  });

  const transform = (callback, message) => {
    if (!fileInfo) return;
    setCanvasToolMode(null);
    pushHistory();
    callback();
    requestRender();
    showToast(message);
  };
  elements.rotateLeft.addEventListener("click", () => transform(() => { settings.rotation = (settings.rotation - 90 + 360) % 360; }, "已向左旋轉 90°"));
  elements.rotateRight.addEventListener("click", () => transform(() => { settings.rotation = (settings.rotation + 90) % 360; }, "已向右旋轉 90°"));
  elements.flipHorizontal.addEventListener("click", () => transform(() => { settings.flipX = !settings.flipX; }, "已水平翻轉"));
  elements.flipVertical.addEventListener("click", () => transform(() => { settings.flipY = !settings.flipY; }, "已垂直翻轉"));

  elements.ratioLock.addEventListener("click", () => {
    ratioLocked = !ratioLocked;
    elements.ratioLock.classList.toggle("is-active", ratioLocked);
    elements.ratioLock.setAttribute("aria-pressed", String(ratioLocked));
    showToast(ratioLocked ? "已鎖定長寬比" : "已解除長寬比鎖定");
  });
  elements.resizeWidth.addEventListener("input", () => {
    if (ratioLocked && baseCanvas.width) elements.resizeHeight.value = Math.max(1, Math.round(Number(elements.resizeWidth.value) * baseCanvas.height / baseCanvas.width));
    updateResizeOverlay();
  });
  elements.resizeHeight.addEventListener("input", () => {
    if (ratioLocked && baseCanvas.height) elements.resizeWidth.value = Math.max(1, Math.round(Number(elements.resizeHeight.value) * baseCanvas.width / baseCanvas.height));
    updateResizeOverlay();
  });
  elements.toggleResizeDrag.addEventListener("click", () => setCanvasToolMode("resize"));
  elements.applyResize.addEventListener("click", applyResize);

  [elements.cropX, elements.cropY, elements.cropWidth, elements.cropHeight].forEach((input) => input.addEventListener("input", updateCropOverlay));
  elements.cropDetails.addEventListener("toggle", () => {
    if (!elements.cropDetails.open && canvasToolMode === "crop") setCanvasToolMode(null);
    updateCropOverlay();
  });
  elements.resizeDetails.addEventListener("toggle", () => {
    if (!elements.resizeDetails.open && canvasToolMode === "resize") setCanvasToolMode(null);
  });
  elements.toggleCropDrag.addEventListener("click", () => setCanvasToolMode("crop"));
  elements.resetCrop.addEventListener("click", resetCropInputs);
  elements.applyCrop.addEventListener("click", applyCrop);

  elements.canvasStack.addEventListener("pointerdown", beginCanvasToolDrag);
  elements.canvasStack.addEventListener("pointermove", moveCanvasToolDrag);
  elements.canvasStack.addEventListener("pointerup", endCanvasToolDrag);
  elements.canvasStack.addEventListener("pointercancel", endCanvasToolDrag);

  elements.compareButton.addEventListener("click", () => {
    compareActive = !compareActive;
    elements.compareButton.setAttribute("aria-pressed", String(compareActive));
    updateCompareView();
  });
  elements.compareRange.addEventListener("input", updateCompareView);
  elements.compareDivider.addEventListener("pointerdown", beginCompareDrag);
  elements.compareDivider.addEventListener("pointermove", moveCompareDrag);
  elements.compareDivider.addEventListener("pointerup", endCompareDrag);
  elements.compareDivider.addEventListener("pointercancel", endCompareDrag);
  elements.zoomSelect.addEventListener("change", updateCanvasDisplay);

  elements.undoButton.addEventListener("click", undo);
  elements.redoButton.addEventListener("click", redo);
  elements.resetButton.addEventListener("click", resetWorkspace);

  $$('input[name="format"]').forEach((radio) => radio.addEventListener("change", () => {
    updateQualityAvailability();
    scheduleExportEstimate();
  }));
  elements.qualityRange.addEventListener("input", () => {
    elements.qualityValue.textContent = `${elements.qualityRange.value}%`;
    updateRangeTrack(elements.qualityRange);
    scheduleExportEstimate();
  });
  elements.downloadButton.addEventListener("click", downloadImage);
  elements.exportShortcut.addEventListener("click", () => {
    document.querySelector("#exportSection").scrollIntoView({ behavior: "smooth", block: "center" });
    elements.downloadButton.focus({ preventScroll: true });
  });

  window.addEventListener("resize", () => requestAnimationFrame(updateCanvasDisplay));
  window.addEventListener("keydown", (event) => {
    const editable = event.target.matches("input, textarea, select");
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {
      event.preventDefault();
      event.shiftKey ? redo() : undo();
      return;
    }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "y") {
      event.preventDefault();
      redo();
      return;
    }
    if (event.key === "Escape" && canvasToolMode) {
      setCanvasToolMode(null);
      return;
    }
    if (!fileInfo || editable) return;
    if (event.key.toLowerCase() === "r") {
      event.preventDefault();
      elements.rotateRight.click();
    }
    if (event.code === "Space" && !event.repeat) {
      event.preventDefault();
      temporaryCompare = true;
      updateCompareView();
    }
  });
  window.addEventListener("keyup", (event) => {
    if (event.code === "Space" && temporaryCompare) {
      temporaryCompare = false;
      updateCompareView();
    }
  });
}

function init() {
  elements.compareCanvas.hidden = true;
  setLoadedControls(false);
  $$("input[type='range']").forEach(updateRangeTrack);
  bindEvents();
}

window.ImageStudio = Object.freeze({
  hasImage: () => Boolean(fileInfo),
  getProcessedCanvas: () => elements.editCanvas,
  commitCanvas: (source, message = "已套用 AI 影像處理", compareSource = null) => {
    if (!fileInfo || !(source instanceof HTMLCanvasElement)) return false;
    pushHistory();
    hasComparisonOverride = compareSource instanceof HTMLCanvasElement;
    if (hasComparisonOverride) copyCanvas(compareSource, comparisonOverrideCanvas);
    copyCanvas(source, baseCanvas);
    resetSettings();
    resetCropInputs();
    syncResizeInputs();
    requestRender();
    showToast(message);
    return true;
  },
  notify: showToast
});

init();
