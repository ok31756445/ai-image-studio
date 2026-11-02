"use strict";

(function exposeImageAlgorithms(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.ImageAlgorithms = api;
})(typeof globalThis !== "undefined" ? globalThis : window, () => {
  const CHANNEL_MODES = new Set(["original", "r", "g", "b", "y", "u", "v"]);

  function clampByte(value) {
    return Math.max(0, Math.min(255, Math.round(value)));
  }

  function channelValue(mode, red, green, blue) {
    switch (mode) {
      case "r": return red;
      case "g": return green;
      case "b": return blue;
      case "y": return clampByte(.299 * red + .587 * green + .114 * blue);
      case "u": return clampByte(-.168736 * red - .331264 * green + .5 * blue + 128);
      case "v": return clampByte(.5 * red - .418688 * green - .081312 * blue + 128);
      default: return clampByte(.2126 * red + .7152 * green + .0722 * blue);
    }
  }

  function histogramFromRgba(data, mode = "original") {
    if (!CHANNEL_MODES.has(mode)) throw new RangeError(`不支援的色彩通道：${mode}`);
    if (!data || data.length % 4 !== 0) throw new TypeError("RGBA 資料長度必須是 4 的倍數");
    const bins = new Uint32Array(256);
    let pixelCount = 0;
    for (let index = 0; index < data.length; index += 4) {
      if (data[index + 3] === 0) continue;
      bins[channelValue(mode, data[index], data[index + 1], data[index + 2])] += 1;
      pixelCount += 1;
    }
    return { bins, pixelCount };
  }

  function psnrFromSquaredError(squaredError, pixelCount, channels = 3) {
    if (!Number.isFinite(squaredError) || squaredError < 0) throw new RangeError("平方誤差必須是非負有限數值");
    if (!Number.isSafeInteger(pixelCount) || pixelCount <= 0) throw new RangeError("像素數量必須是正整數");
    if (!Number.isSafeInteger(channels) || channels <= 0) throw new RangeError("通道數量必須是正整數");
    const mse = squaredError / (pixelCount * channels);
    const psnr = mse === 0 ? Infinity : 10 * Math.log10((255 * 255) / mse);
    return { mse, psnr };
  }

  function validateKernel({ size, weights, normalization = "sum", customDivisor = 1, bias = 0 }) {
    if (![3, 5].includes(size) || !Array.isArray(weights) || weights.length !== size * size) {
      return { ok: false, error: "卷積核必須是 3×3 或 5×5 方陣" };
    }
    if (weights.some((value) => !Number.isFinite(value))) {
      return { ok: false, error: "卷積核必須全部填入有效數字" };
    }
    if (!new Set(["sum", "none", "custom"]).has(normalization)) {
      return { ok: false, error: "不支援的正規化模式" };
    }
    let divisor = 1;
    if (normalization === "sum") divisor = weights.reduce((sum, value) => sum + value, 0);
    if (normalization === "custom") divisor = Number(customDivisor);
    if (!Number.isFinite(divisor) || Math.abs(divisor) < 1e-12) {
      return { ok: false, error: "正規化除數不可為 0；零和卷積核請改用「不正規化」或自訂非零除數" };
    }
    const normalizedBias = Number(bias);
    if (!Number.isFinite(normalizedBias)) return { ok: false, error: "偏移量必須是有效數字" };
    return { ok: true, kernel: { size, weights: [...weights], divisor, bias: normalizedBias } };
  }

  return Object.freeze({ clampByte, channelValue, histogramFromRgba, psnrFromSquaredError, validateKernel });
});
