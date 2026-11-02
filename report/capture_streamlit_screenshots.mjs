import fs from "node:fs/promises";
import path from "node:path";

const DEBUG_PORT = 9223;
const APP_URL = "http://127.0.0.1:8501/";
const outputDirectory = path.resolve("tmp", "qa", "report-python");
const uploadPath = path.resolve("images.jpg");

class CdpClient {
  constructor(url) {
    this.socket = new WebSocket(url);
    this.nextId = 1;
    this.pending = new Map();
  }

  async connect() {
    await new Promise((resolve, reject) => {
      this.socket.addEventListener("open", resolve, { once: true });
      this.socket.addEventListener("error", reject, { once: true });
    });
    this.socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      if (!message.id || !this.pending.has(message.id)) return;
      const { resolve, reject } = this.pending.get(message.id);
      this.pending.delete(message.id);
      if (message.error) reject(new Error(JSON.stringify(message.error)));
      else resolve(message.result);
    });
  }

  send(method, params = {}) {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }

  close() {
    this.socket.close();
  }
}

const delay = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

async function waitFor(client, expression, timeout = 30000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    const result = await client.send("Runtime.evaluate", {
      expression: `Boolean(${expression})`,
      returnByValue: true,
    });
    if (result.result.value) return;
    await delay(250);
  }
  throw new Error(`Timed out waiting for: ${expression}`);
}

async function evaluate(client, expression) {
  const result = await client.send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
  return result.result.value;
}

async function capture(client, filename) {
  await delay(700);
  const screenshot = await client.send("Page.captureScreenshot", {
    format: "png",
    captureBeyondViewport: false,
    fromSurface: true,
  });
  await fs.writeFile(path.join(outputDirectory, filename), Buffer.from(screenshot.data, "base64"));
}

async function main() {
  await fs.mkdir(outputDirectory, { recursive: true });
  const response = await fetch(`http://127.0.0.1:${DEBUG_PORT}/json/new?${encodeURIComponent(APP_URL)}`, {
    method: "PUT",
  });
  if (!response.ok) throw new Error(`Unable to create Chrome target: ${response.status}`);
  const target = await response.json();
  const client = new CdpClient(target.webSocketDebuggerUrl);
  await client.connect();
  await client.send("Page.enable");
  await client.send("Runtime.enable");
  await client.send("DOM.enable");
  await client.send("Emulation.setDeviceMetricsOverride", {
    width: 1440,
    height: 1000,
    deviceScaleFactor: 1,
    mobile: false,
  });

  await waitFor(client, `document.body?.innerText.includes("把影像帶進工作台")`);
  await waitFor(client, `document.querySelector('input[type="file"]')`);
  const inputResult = await client.send("Runtime.evaluate", {
    expression: `document.querySelector('input[type="file"]')`,
    returnByValue: false,
  });
  if (!inputResult.result.objectId) throw new Error("File input was not found");
  await client.send("DOM.setFileInputFiles", {
    objectId: inputResult.result.objectId,
    files: [uploadPath],
  });
  await waitFor(client, `document.body?.innerText.includes("images.jpg")`, 30000);
  await capture(client, "01-load-metadata.png");

  await evaluate(client, `(() => {
    const labels = [...document.querySelectorAll('[data-testid="stRadio"] label')];
    const target = labels.find((label) => label.innerText.trim() === 'Y');
    if (!target) return false;
    target.click();
    return true;
  })()`);
  await waitFor(client, `document.body?.innerText.includes("Y 通道檢視")`);
  await capture(client, "02-y-channel-histogram.png");

  await evaluate(client, `(() => {
    const buttons = [...document.querySelectorAll('button')];
    const target = buttons.find((button) => button.innerText.includes('套用卷積濾波'));
    if (!target) return false;
    target.click();
    return true;
  })()`);
  await waitFor(client, `document.body?.innerText.includes("PSNR")`, 30000);
  await evaluate(client, `(() => {
    const sidebar = document.querySelector('[data-testid="stSidebarContent"]');
    if (!sidebar) return false;
    sidebar.scrollTo({ top: sidebar.scrollHeight, behavior: 'instant' });
    return true;
  })()`);
  await capture(client, "03-kernel-psnr.png");

  await evaluate(client, `(() => {
    const buttons = [...document.querySelectorAll('button')];
    const target = buttons.find((button) => button.innerText.includes('啟動人臉偵測'));
    if (!target) return false;
    target.click();
    return true;
  })()`);
  await waitFor(client, `document.body?.innerText.includes("偵測人臉")`, 60000);
  await capture(client, "04-face-detection.png");

  await client.send("Page.close");
  client.close();
  console.log(outputDirectory);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
