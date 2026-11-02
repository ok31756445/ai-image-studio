"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const algorithms = require("../image-algorithms.js");

test("BT.601 YUV and RGB channel values are deterministic", () => {
  assert.equal(algorithms.channelValue("r", 255, 10, 20), 255);
  assert.equal(algorithms.channelValue("y", 255, 0, 0), 76);
  assert.equal(algorithms.channelValue("u", 255, 0, 0), 85);
  assert.equal(algorithms.channelValue("v", 255, 0, 0), 255);
});

test("histogram counts every non-transparent source pixel", () => {
  const rgba = new Uint8ClampedArray([
    0, 0, 0, 255,
    255, 0, 0, 255,
    255, 0, 0, 255,
    0, 255, 0, 0
  ]);
  const { bins, pixelCount } = algorithms.histogramFromRgba(rgba, "r");
  assert.equal(pixelCount, 3);
  assert.equal(bins[0], 1);
  assert.equal(bins[255], 2);
  assert.equal(bins.reduce((sum, count) => sum + count, 0), 3);
});

test("identity output produces MSE 0 and infinite PSNR", () => {
  const result = algorithms.psnrFromSquaredError(0, 4);
  assert.equal(result.mse, 0);
  assert.equal(result.psnr, Infinity);
});

test("known squared error produces the PSNR formula result", () => {
  const result = algorithms.psnrFromSquaredError(300, 100);
  assert.equal(result.mse, 1);
  assert.ok(Math.abs(result.psnr - 48.1308036) < 1e-6);
});

test("sum normalization rejects a zero-sum kernel", () => {
  const result = algorithms.validateKernel({
    size: 3,
    weights: [-1, -1, -1, -1, 8, -1, -1, -1, -1],
    normalization: "sum"
  });
  assert.equal(result.ok, false);
  assert.match(result.error, /不可為 0/);
});

test("custom non-zero divisor and finite bias are accepted", () => {
  const result = algorithms.validateKernel({
    size: 3,
    weights: [0, -1, 0, -1, 5, -1, 0, -1, 0],
    normalization: "custom",
    customDivisor: 2,
    bias: 12
  });
  assert.equal(result.ok, true);
  assert.equal(result.kernel.divisor, 2);
  assert.equal(result.kernel.bias, 12);
});
