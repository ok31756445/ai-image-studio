"use strict";

(() => {
  const algorithms = window.ImageAlgorithms;
  if (!algorithms) throw new Error("ImageAlgorithms 尚未載入");
  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => [...document.querySelectorAll(selector)];
  const studio = window.ImageStudio;
  if (!studio) return;

  const elements = {
    analysisCanvas: $("#analysisCanvas"),
    histogramCanvas: $("#histogramCanvas"),
    histogramEmpty: $("#histogramEmpty"),
    analysisStatus: $("#analysisStatus"),
    channelStatus: $("#channelStatus"),
    channelDescription: $("#channelDescription"),
    channelModes: $("#channelModes"),
    kernelSize: $("#kernelSize"),
    kernelPreset: $("#kernelPreset"),
    kernelMatrix: $("#kernelMatrix"),
    kernelNormalization: $("#kernelNormalization"),
    kernelDivisor: $("#kernelDivisor"),
    kernelBias: $("#kernelBias"),
    applyKernel: $("#applyKernel"),
    kernelStatus: $("#kernelStatus"),
    kernelProgress: $("#kernelProgress"),
    kernelProgressText: $("#kernelProgressText"),
    psnrValue: $("#psnrValue"),
    psnrNote: $("#psnrNote"),
    compareButton: $("#compareButton")
  };

  const CHANNELS = Object.freeze({
    original: { label: "Original", description: "完整 RGB 彩色影像；直方圖顯示 BT.709 亮度分布。", color: "#e8a84a" },
    r: { label: "R channel", description: "紅色分量轉為灰階強度圖；0 表示無紅光，255 表示紅色分量最高。", color: "#ff6b6b" },
    g: { label: "G channel", description: "綠色分量轉為灰階強度圖；適合觀察植被、亮部與感光細節。", color: "#67d391" },
    b: { label: "B channel", description: "藍色分量轉為灰階強度圖；適合觀察天空、冷色區域與雜訊。", color: "#68a8ff" },
    y: { label: "Y luminance", description: "YUV 的亮度分量：Y = 0.299R + 0.587G + 0.114B。", color: "#edf2f5" },
    u: { label: "U chroma", description: "YUV 的藍色色度分量，已加上 128 偏移映射至 0–255。", color: "#58c4d8" },
    v: { label: "V chroma", description: "YUV 的紅色色度分量，已加上 128 偏移映射至 0–255。", color: "#d989c8" }
  });

  const PRESETS = Object.freeze({
    identity: [0, 0, 0, 0, 1, 0, 0, 0, 0],
    sharpen: [0, -1, 0, -1, 5, -1, 0, -1, 0],
    gaussian: [1, 2, 1, 2, 4, 2, 1, 2, 1],
    emboss: [-2, -1, 0, -1, 1, 1, 0, 1, 2],
    edge: [-1, -1, -1, -1, 8, -1, -1, -1, -1]
  });

  let channelMode = "original";
  let kernelRunning = false;
  let evaluationRevision = 0;
  let analysisRenderTimer = 0;

  const { clampByte, channelValue } = algorithms;

  function createWorkingCanvas(source, maxPixels = 4_000_000) {
    const scale = Math.min(1, Math.sqrt(maxPixels / (source.width * source.height)));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(source.width * scale));
    canvas.height = Math.max(1, Math.round(source.height * scale));
    const context = canvas.getContext("2d", { alpha: true, willReadFrequently: true });
    context.imageSmoothingEnabled = true;
    context.imageSmoothingQuality = "high";
    context.drawImage(source, 0, 0, canvas.width, canvas.height);
    return canvas;
  }

  function renderChannelView() {
    if (!studio.hasImage()) return;
    const source = studio.getProcessedCanvas();
    if (channelMode === "original") {
      elements.analysisCanvas.hidden = true;
      drawSynchronizedHistogram(source);
      return;
    }

    const working = createWorkingCanvas(source);
    const context = working.getContext("2d", { willReadFrequently: true });
    const imageData = context.getImageData(0, 0, working.width, working.height);
    const data = imageData.data;
    for (let index = 0; index < data.length; index += 4) {
      const value = channelValue(channelMode, data[index], data[index + 1], data[index + 2]);
      data[index] = value;
      data[index + 1] = value;
      data[index + 2] = value;
    }
    elements.analysisCanvas.width = working.width;
    elements.analysisCanvas.height = working.height;
    elements.analysisCanvas.getContext("2d", { alpha: true }).putImageData(imageData, 0, 0);
    elements.analysisCanvas.hidden = false;
    drawSynchronizedHistogram(source);
  }

  function drawSynchronizedHistogram(source) {
    const sourceContext = source.getContext("2d", { willReadFrequently: true });
    const pixels = sourceContext.getImageData(0, 0, source.width, source.height).data;
    const { bins, pixelCount } = algorithms.histogramFromRgba(pixels, channelMode);

    const canvas = elements.histogramCanvas;
    const context = canvas.getContext("2d");
    const width = canvas.width;
    const height = canvas.height;
    const chartLeft = 37;
    const chartRight = width - 4;
    const chartBottom = height - 18;
    const chartTop = 10;
    const chartWidth = chartRight - chartLeft;
    const max = Math.max(...bins) || 1;
    context.clearRect(0, 0, width, height);
    context.strokeStyle = "rgba(127, 140, 150, .18)";
    context.lineWidth = 1;
    [0, .25, .5, .75, 1].forEach((ratio) => {
      const x = Math.round(chartLeft + ratio * chartWidth) + .5;
      context.beginPath(); context.moveTo(x, chartTop); context.lineTo(x, chartBottom); context.stroke();
    });
    context.beginPath();
    context.moveTo(chartLeft, chartBottom);
    bins.forEach((count, index) => {
      const x = chartLeft + index / 255 * chartWidth;
      const y = chartBottom - count / max * (chartBottom - chartTop);
      context.lineTo(x, y);
    });
    context.lineTo(chartRight, chartBottom);
    context.closePath();
    const gradient = context.createLinearGradient(chartLeft, 0, chartRight, 0);
    const color = CHANNELS[channelMode].color;
    gradient.addColorStop(0, `${color}44`);
    gradient.addColorStop(1, `${color}dd`);
    context.fillStyle = gradient;
    context.fill();
    context.fillStyle = "rgba(183, 192, 199, .9)";
    context.font = "9px Segoe UI";
    context.textAlign = "right";
    context.fillText(max.toLocaleString(), chartLeft - 5, chartTop + 3);
    context.fillText("0", chartLeft - 5, chartBottom);
    context.save();
    context.translate(9, (chartTop + chartBottom) / 2);
    context.rotate(-Math.PI / 2);
    context.textAlign = "center";
    context.fillText("像素數量", 0, 0);
    context.restore();
    context.textAlign = "left";
    canvas.setAttribute("aria-label", `${CHANNELS[channelMode].label} 直方圖；橫軸像素強度 0 到 255，縱軸像素數量，統計 ${pixelCount.toLocaleString()} 個非透明像素`);
    elements.histogramEmpty.hidden = true;
    elements.analysisStatus.textContent = CHANNELS[channelMode].label;
    elements.analysisStatus.classList.add("is-ready");
  }

  function selectChannel(mode) {
    if (!CHANNELS[mode]) return;
    channelMode = mode;
    $$(".channel-mode").forEach((button) => {
      const active = button.dataset.channel === mode;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    elements.channelStatus.textContent = CHANNELS[mode].label;
    elements.channelDescription.textContent = CHANNELS[mode].description;
    renderChannelView();
  }

  function scheduleChannelRender() {
    window.clearTimeout(analysisRenderTimer);
    analysisRenderTimer = window.setTimeout(renderChannelView, 90);
  }

  function centeredPreset(values, size) {
    if (size === 3) return [...values];
    const output = Array(size * size).fill(0);
    for (let y = 0; y < 3; y += 1) {
      for (let x = 0; x < 3; x += 1) output[(y + 1) * size + x + 1] = values[y * 3 + x];
    }
    return output;
  }

  function presetValues(name, size) {
    if (name === "gaussian" && size === 5) {
      const line = [1, 4, 6, 4, 1];
      return line.flatMap((vertical) => line.map((horizontal) => vertical * horizontal));
    }
    return centeredPreset(PRESETS[name] || PRESETS.identity, size);
  }

  function renderKernelMatrix(values = null) {
    const size = Number(elements.kernelSize.value);
    const matrix = values || presetValues(elements.kernelPreset.value, size);
    elements.kernelMatrix.dataset.size = String(size);
    elements.kernelMatrix.replaceChildren();
    matrix.forEach((value, index) => {
      const input = document.createElement("input");
      input.className = "kernel-cell";
      input.type = "number";
      input.step = "any";
      input.value = String(value);
      input.setAttribute("aria-label", `卷積核第 ${Math.floor(index / size) + 1} 列第 ${index % size + 1} 欄`);
      input.disabled = !studio.hasImage();
      elements.kernelMatrix.appendChild(input);
    });
    syncNormalization();
  }

  function matrixValues() {
    return $$(".kernel-cell").map((input) => Number(input.value));
  }

  function syncNormalization() {
    const mode = elements.kernelNormalization.value;
    const sum = matrixValues().reduce((total, value) => total + (Number.isFinite(value) ? value : 0), 0);
    if (mode === "sum") elements.kernelDivisor.value = String(Number(sum.toFixed(8)));
    if (mode === "none") elements.kernelDivisor.value = "1";
    elements.kernelDivisor.disabled = !studio.hasImage() || mode !== "custom";
  }

  function resolveKernel() {
    const size = Number(elements.kernelSize.value);
    const weights = matrixValues();
    const result = algorithms.validateKernel({
      size,
      weights,
      normalization: elements.kernelNormalization.value,
      customDivisor: elements.kernelDivisor.value,
      bias: elements.kernelBias.value
    });
    if (!result.ok) {
      studio.notify(result.error);
      return null;
    }
    return result.kernel;
  }

  async function convolve(source, kernel, isCancelled) {
    const width = source.width;
    const height = source.height;
    const inputContext = source.getContext("2d", { willReadFrequently: true });
    const input = inputContext.getImageData(0, 0, width, height);
    const output = new ImageData(width, height);
    const radius = Math.floor(kernel.size / 2);
    const activeWeights = [];
    kernel.weights.forEach((weight, index) => {
      if (weight !== 0) activeWeights.push({
        weight,
        dx: index % kernel.size - radius,
        dy: Math.floor(index / kernel.size) - radius
      });
    });
    let squaredError = 0;

    for (let y = 0; y < height; y += 1) {
      if (isCancelled()) throw new DOMException("卷積已取消", "AbortError");
      for (let x = 0; x < width; x += 1) {
        const targetIndex = (y * width + x) * 4;
        for (let channel = 0; channel < 3; channel += 1) {
          let sum = 0;
          for (let weightIndex = 0; weightIndex < activeWeights.length; weightIndex += 1) {
            const active = activeWeights[weightIndex];
            const sampleX = Math.max(0, Math.min(width - 1, x + active.dx));
            const sampleY = Math.max(0, Math.min(height - 1, y + active.dy));
            sum += input.data[(sampleY * width + sampleX) * 4 + channel] * active.weight;
          }
          const value = clampByte(sum / kernel.divisor + kernel.bias);
          output.data[targetIndex + channel] = value;
          const difference = input.data[targetIndex + channel] - value;
          squaredError += difference * difference;
        }
        output.data[targetIndex + 3] = input.data[targetIndex + 3];
      }
      if (y % 16 === 0) {
        elements.kernelProgressText.textContent = `正在計算濾波… ${Math.round((y + 1) / height * 100)}%`;
        await new Promise((resolve) => requestAnimationFrame(resolve));
      }
    }

    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    canvas.getContext("2d", { alpha: true }).putImageData(output, 0, 0);
    const { mse, psnr } = algorithms.psnrFromSquaredError(squaredError, width * height);
    return { canvas, psnr, mse };
  }

  async function applyKernel() {
    if (kernelRunning || !studio.hasImage()) return;
    const kernel = resolveKernel();
    if (!kernel) return;
    const source = studio.getProcessedCanvas();
    if (source.width * source.height > 12_000_000) {
      studio.notify("為避免瀏覽器記憶體不足，請先將影像縮至 1,200 萬像素以下再套用卷積");
      return;
    }

    const before = document.createElement("canvas");
    before.width = source.width;
    before.height = source.height;
    before.getContext("2d", { alpha: true }).drawImage(source, 0, 0);
    kernelRunning = true;
    const runRevision = ++evaluationRevision;
    elements.applyKernel.disabled = true;
    elements.kernelProgress.hidden = false;
    elements.kernelStatus.textContent = "計算中";
    elements.kernelStatus.classList.remove("is-ready");
    try {
      const result = await convolve(before, kernel, () => runRevision !== evaluationRevision);
      elements.psnrValue.textContent = Number.isFinite(result.psnr) ? `${result.psnr.toFixed(2)} dB` : "∞ dB";
      elements.psnrNote.textContent = Number.isFinite(result.psnr)
        ? `MSE ${result.mse.toFixed(4)} · 10 log₁₀(255² / MSE)`
        : "輸出與輸入完全相同，MSE = 0";
      elements.kernelStatus.textContent = "已完成";
      elements.kernelStatus.classList.add("is-ready");
      selectChannel("original");
      studio.commitCanvas(result.canvas, `卷積濾波完成 · PSNR ${Number.isFinite(result.psnr) ? result.psnr.toFixed(2) : "∞"} dB`, before);
      if (elements.compareButton.getAttribute("aria-pressed") !== "true") elements.compareButton.click();
    } catch (error) {
      if (error?.name === "AbortError") return;
      console.error(error);
      elements.kernelStatus.textContent = "計算失敗";
      studio.notify("卷積濾波失敗：請檢查矩陣與影像尺寸");
    } finally {
      kernelRunning = false;
      elements.kernelProgress.hidden = true;
      elements.applyKernel.disabled = !studio.hasImage();
    }
  }

  function resetKernelEvaluation() {
    evaluationRevision += 1;
    elements.psnrValue.textContent = "— dB";
    elements.psnrNote.textContent = "套用濾波後計算";
    elements.kernelStatus.textContent = "尚未套用";
    elements.kernelStatus.classList.remove("is-ready");
    elements.kernelProgress.hidden = true;
  }

  elements.channelModes.addEventListener("click", (event) => {
    const button = event.target.closest("[data-channel]");
    if (button && !button.disabled) selectChannel(button.dataset.channel);
  });
  elements.kernelSize.addEventListener("change", () => renderKernelMatrix());
  elements.kernelPreset.addEventListener("change", () => renderKernelMatrix());
  elements.kernelNormalization.addEventListener("change", syncNormalization);
  elements.kernelMatrix.addEventListener("input", syncNormalization);
  elements.applyKernel.addEventListener("click", applyKernel);
  window.addEventListener("image-studio:render", () => {
    scheduleChannelRender();
    $$(".kernel-cell").forEach((input) => { input.disabled = !studio.hasImage() || kernelRunning; });
    syncNormalization();
  });
  window.addEventListener("image-studio:workspace-reset", resetKernelEvaluation);

  renderKernelMatrix();
})();
