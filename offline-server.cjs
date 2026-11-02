"use strict";

const { execFile } = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");

const HOST = process.env.IMAGE_STUDIO_HOST || "127.0.0.1";
const PORT = Number(process.env.PORT || 4173);
const ROOT = path.resolve(__dirname);
const SHOULD_OPEN_BROWSER = !process.argv.includes("--no-open");
const MIME_TYPES = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".bmp": "image/bmp",
  ".gif": "image/gif",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".png": "image/png",
  ".webp": "image/webp",
  ".tflite": "application/octet-stream",
  ".wasm": "application/wasm"
};

function resolveRequestPath(url) {
  const pathname = decodeURIComponent(new URL(url, `http://${HOST}:${PORT}`).pathname);
  const relativePath = pathname === "/" ? "index.html" : pathname.slice(1);
  const filePath = path.resolve(ROOT, relativePath);
  return filePath === ROOT || filePath.startsWith(`${ROOT}${path.sep}`) ? filePath : null;
}

const server = http.createServer((request, response) => {
  const filePath = resolveRequestPath(request.url || "/");
  if (!filePath) {
    response.writeHead(403).end("Forbidden");
    return;
  }

  fs.stat(filePath, (statError, stats) => {
    const target = !statError && stats.isDirectory() ? path.join(filePath, "index.html") : filePath;
    fs.readFile(target, (readError, data) => {
      if (readError) {
        response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" }).end("Not found");
        return;
      }
      response.writeHead(200, {
        "Cache-Control": "no-cache",
        "Content-Type": MIME_TYPES[path.extname(target).toLowerCase()] || "application/octet-stream"
      });
      response.end(data);
    });
  });
});

server.on("error", (error) => {
  if (error.code === "EADDRINUSE") {
    console.error(`\n無法啟動：${PORT} 連接埠已被使用。請關閉先前的離線伺服器後重試。`);
  } else {
    console.error("\n本機伺服器啟動失敗：", error.message);
  }
  process.exitCode = 1;
});

server.listen(PORT, HOST, () => {
  const url = `http://${HOST}:${PORT}`;
  console.log(`\nAI 光影研究室離線版已啟動：${url}`);
  console.log("使用完畢請回到此視窗按 Ctrl+C 停止。\n");
  if (SHOULD_OPEN_BROWSER && process.platform === "win32" && HOST === "127.0.0.1") {
    execFile("cmd.exe", ["/c", "start", "", url], { windowsHide: true });
  }
});
