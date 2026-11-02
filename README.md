# AI 光影研究室 · Python

目前主要版本已改為 **Python + Streamlit**，搭配 NumPy、Pillow 與 MediaPipe，提供互動式影像處理、色彩空間分析、卷積濾波與人臉偵測。原本的 JavaScript／Canvas 版本仍保留作為備份與 GitHub Pages 展示。

- 原始碼：https://github.com/ok31756445/ai-image-studio
- 現有靜態版：https://ok31756445.github.io/ai-image-studio/
- Python Live Demo：https://ai-image-studio-c112152350.streamlit.app/

## Python 版本機啟動

需要 Python 3.9 以上版本，建議 Python 3.12：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

安裝完成後亦可雙擊 `start-python.cmd`。瀏覽器會開啟 `http://localhost:8501`；在命令視窗按 `Ctrl+C` 可停止服務。

Python 版包含 PNG/JPG/BMP 解析、Original/R/G/B/Y/U/V 與 0–255 直方圖、3×3/5×5 可編輯卷積核、三種正規化、PSNR/MSE、可拖曳前後比較，以及本機 BlazeFace 多人臉偵測。模型以位元組載入，因此可在 Windows 中文路徑下正常使用。

Streamlit 介面沿用 JavaScript 版的暗色數位暗房設計：固定頂欄、左側編輯工具、中央點陣影像舞台與右側分析／匯出面板；窄螢幕會自動改為堆疊版面。

Streamlit Cloud 會依根目錄的 `packages.txt` 安裝 MediaPipe／OpenCV 所需的 GL、EGL、GLES 與 GLib 執行期；人臉偵測器則明確使用 CPU delegate，避免無 GPU 的雲端容器出現共享函式庫或加速器錯誤。

## Python 主版本功能

- PNG、JPG/JPEG、BMP 拖放與檔案選擇
- 即時顯示解析度、百萬像素、格式、檔案大小、色彩維度與位元深度
- Original、RGB 分離通道與 YUV（Y/U/V）分量檢視
- 通道切換時以完整非透明像素同步更新 0–255 像素強度／像素數量直方圖
- 3×3、5×5 自訂卷積核、正規化除數、偏移量與常用濾波預設
- 卷積前後滑桿對照與 PSNR／MSE 即時計算
- 原圖／處理結果滑桿對照
- 即時亮度直方圖與影像資訊
- MediaPipe AI 人臉偵測、信心分數與 6 組臉部關鍵點
- 每張臉的邊界框、信心度明細與多人臉總數
- PNG 處理結果下載
- 鍵盤操作、清楚焦點、reduced-motion 與響應式版面

舊版 JavaScript／Canvas 的裁切、尺寸拖曳、幾何變換、濾鏡、復原／重做與匿名化功能仍保留在原始碼及 GitHub Pages，但不列為目前 Python 主版本的核心驗收功能。

## 離線啟動

在 Windows 上雙擊 `start-offline.cmd`。它會啟動只綁定於 `127.0.0.1:4173` 的本機伺服器，並自動開啟瀏覽器。使用完畢回到命令視窗按 `Ctrl+C` 即可停止。

> 不要直接雙擊 `index.html`。瀏覽器會基於安全政策阻擋 `file://` 載入本機 WASM 模型。

所有影像處理均使用 Canvas API 在本機完成，檔案不會上傳到伺服器。MediaPipe 1.2.0、WASM 與 BlazeFace 模型已放在 `vendor/mediapipe/`，執行期間不從 CDN 下載。人臉分析只定位臉部與關鍵點，不進行身分辨識，也不推測年齡、性別、族群或情緒。

## 演算法定義

YUV 採 BT.601：

- `Y = 0.299R + 0.587G + 0.114B`
- `U = -0.168736R - 0.331264G + 0.5B + 128`
- `V = 0.5R - 0.418688G - 0.081312B + 128`

卷積使用奇數方陣（3×3 或 5×5），邊界像素採 clamp-to-edge 延伸。正規化可選權重總和、不正規化或自訂非零除數；零和矩陣會阻止除以零。

PSNR 以 RGB 三通道計算：

`MSE = (1 / 3WH) Σ[(R-R')² + (G-G')² + (B-B')²]`

`PSNR = 10 log10(255² / MSE) dB`

若 `MSE = 0`，介面顯示 `∞ dB`。

## Python 線上部署

1. 登入 [Streamlit Community Cloud](https://share.streamlit.io/) 並連接 GitHub。
2. 按 **Create app**，選擇 `ok31756445/ai-image-studio` 與 `main` 分支。
3. Main file path 填入 `streamlit_app.py`，按 **Deploy**。
4. 目前公開網址為 https://ai-image-studio-c112152350.streamlit.app/；重新部署後請以無痕視窗確認可免登入開啟。

## 舊版 JavaScript 部署

- 本機：`npm start`
- Docker / Hugging Face Spaces：以專案內的 `Dockerfile` 建置；容器使用 `7860` 連接埠。
- 純靜態代管：亦可部署至 GitHub Pages，但需確保 `vendor/mediapipe/` 完整上傳。

專案已包含 `.github/workflows/pages.yml`。推送至 GitHub 後，在儲存庫 **Settings → Pages → Source** 選擇 **GitHub Actions**，後續每次推送 `main` 都會先執行語法與演算法測試，再自動部署。

JavaScript 版不需要 npm 執行期套件；Python 版套件與產生報告所需套件均列在 `requirements.txt`。

## 驗證

```powershell
npm run check
npm test
python -m py_compile streamlit_app.py python_image_studio\core.py python_image_studio\face.py
python -m unittest tests.test_python_core -v
```

JavaScript 與 Python 自動化測試涵蓋 BT.601 YUV、RGB 通道、完整像素直方圖、MSE／PSNR 公式、零和卷積核與自訂除數。完整 AI 協作紀錄見 `docs/AI_AUDIT_TRAIL.md`。

## 測試邊界

- 影像上限：3,200 萬像素；卷積上限：1,200 萬像素，以控制雲端工作階段的記憶體與等待時間。
- 卷積核所有欄位必須是有限數值；正規化除數不可為 0。
- 上傳檔案以內容雜湊識別；換圖或清除結果會同步清除 PSNR、MSE、卷積與人臉結果。
- 人臉偵測對無人臉與多人臉情境提供明確結果，逐臉顯示信心度與邊界框。
