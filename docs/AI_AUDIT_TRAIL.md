# AI 協作與 Prompt 歷程

AI 模型：OpenAI Codex（GPT-5 系列）。以下依本專案對話順序保存需求、產出與後續修正。公開網址與個人資料不由 AI 猜測。

| # | 原始 Prompt／需求 | AI 產出結果 | 除錯／Refinement |
|---:|---|---|---|
| 1 | 研究並安裝 `ui-ux-pro-max` skill | 研究 GitHub 專案結構與 Codex skill 安裝位置 | 發現安裝指令不支援 `--dry-run`，改用實際支援的安裝流程 |
| 2 | `error: unknown option '--dry-run'` | 移除不相容參數並改查驗 `SKILL.md` | 用 `Test-Path` 驗證技能是否實際存在 |
| 3 | `Test-Path ... False` | 重新確認安裝目錄與技能可用清單 | 最終讓 `ui-ux-pro-max` 出現在 Codex Skills 清單 |
| 4 | 如何開始使用 skill | 說明可直接在需求中指定技能 | 後續所有介面工作以技能規則驗收 |
| 5 | 開發具 GUI／Web App 的影像處理應用程式 | 建立瀏覽器本機影像工作台 | 逐步補上讀檔、Canvas 編輯、分析、匯出與離線隱私 |
| 6 | 基於 AI 輔助之互動式影像處理與人臉分析工具 | 建立三欄式深色工作介面與 MediaPipe 模組 | 加入狀態訊息、取消、錯誤與推論時間 |
| 7 | 人臉分析在分析什麼、為何很久 | 說明僅偵測臉框與關鍵點，不做身分或屬性推測 | 將模型狀態與隱私範圍寫入 UI |
| 8 | 改成離線載入 | 將 MediaPipe JS、WASM 與 BlazeFace 放入 `vendor` | 移除執行期間 CDN 依賴並補本機伺服器 |
| 9 | 推論很久、沒有結果 | 檢查模型初始化與大圖推論 | 將推論圖最長邊限制為 1024 px 並加入 20 秒載入逾時 |
| 10 | 沒有圖片卻一直顯示載入模型 | 分離「模型待命」與「影像分析」狀態 | 只有使用者啟動分析時才初始化模型 |
| 11 | 安裝 Frontend Design skill | 安裝並驗證 `frontend-design` | 與 `ui-ux-pro-max` 一起用於介面重構 |
| 12 | 用兩個 skill 調整專案並確認 Git 備份 | 建立基準 commit 與新版介面 | 保留使用者原有檔案，所有修正分批 commit |
| 13 | 關閉剛剛開的 port | 停止本機測試伺服器 | 後續測試皆明確記錄啟動與停止狀態 |
| 14 | 前後對比無法拖動 | 修正 Pointer Events、命中區與比較裁切 | 保留原生 range 作為鍵盤替代操作 |
| 15 | 尺寸與裁切改為拖動 | 加入畫布四角縮放、建立／移動／縮放裁切框 | 同步數字輸入、邊界限制、Esc 退出與復原歷史 |
| 16 | 加入讀檔、RGB/YUV、Histogram、Kernel、PSNR、Face 與 PDF 規格 | 完成四大核心模組、部署檔與報告產生器 | 加入 32 MP／12 MP 上限、公式、零除防呆與驗收表 |
| 17 | 正規化參數在哪裡 | 說明矩陣下方的正規化、除數與偏移量 | 保留權重總和、不正規化、自訂非零除數三種模式 |
| 18 | 按下重設後 PSNR 是否應清除 | 判定舊 PSNR 已失去比較基準 | 重設時清除 PSNR／MSE、卷積狀態與前後比較，並取消舊運算 |
| 19 | 依評分表檢查專案 | 實際驗收四大功能、部署、Prompt Log、PDF 與 UX | 找出公開連結、精確直方圖、正向人臉案例、完整 Prompt Log 等缺口 |
| 20 | 開始修正 | 將直方圖改為完整像素統計並加入測試與 Pages 工作流 | 補 PDF 驗收證據；公開 URL、學號與姓名留待使用者提供 |
| 21 | 我想改以 Python 去開發 | 將主版本移植為 Streamlit、NumPy、Pillow、MediaPipe Python，保留舊版作 Git 備份 | 實測發現 MediaPipe 無法開啟中文路徑模型，改以模型位元組載入；新增拖曳前後比較、深色主題與 Python CI 測試 |
| 22 | Streamlit Cloud 人臉偵測顯示 `libGL.so.1` 缺失 | 判定為 Linux 系統層缺少 OpenCV 圖形執行期 | 新增 `packages.txt` 安裝 `libgl1` 與 `libglib2.0-0`，由 Community Cloud 重建環境 |
| 23 | 雲端 Log 提示 `use_container_width` 即將移除 | 確認部署已成功，訊息屬 Streamlit API 淘汰警告 | 全面改用 `width="stretch"`，避免 2025-12-31 後失效並清除重複警告 |
| 24 | 雲端人臉偵測接著顯示 `libEGL.so.1` 缺失 | 完整 Log 證實 GL 已安裝，但 MediaPipe 原生層仍載入 EGL/GLES | 補上 `libegl1`、`libgles2`，並明確指定 MediaPipe CPU delegate |
| 25 | Python UI 改成與原本 JavaScript 版一致 | 以原版實際畫面與 CSS token 為基準重建 Streamlit 工作台 | 改為固定頂欄、左右工具面板、中央點陣畫布；保留響應式堆疊、焦點狀態與拖曳比較的鍵盤替代操作 |
| 26 | 依最終核心功能、繳交規範與 Rubric 再次驗收 | 對照 Python 程式、測試、公開部署與 PDF 報告逐項稽核 | 修正 5×5 identity 預設、加入內容雜湊狀態隔離與逐臉明細；補 U/V、自訂除數、5×5 測試，將正式報告全面改寫為 Python／Streamlit 架構 |
| 27 | 左側工具列收起後無法重新打開 | 發現自訂頂欄 CSS 同時隱藏 Streamlit 原生展開控制 | 保留原生可存取按鈕並重新定位於頂欄下方；實測「收起 → 展開」及鍵盤可見焦點狀態 |
| 28 | 人臉完成後發生 `StreamlitWidgetAlreadyInstantiatedError` | 找出程式在工作區 segmented control 建立後直接改寫同名 Session State | 改為暫存 `_next_stage_view`，於下一輪 widget 建立前套用；新增工作台狀態生命週期回歸測試 |

## 驗證方式

- `npm run check`：檢查所有 JavaScript 語法。
- `npm test`：驗證 BT.601 色彩公式、完整像素直方圖、PSNR 與卷積正規化防呆。
- `python -m unittest tests.test_python_core -v`：驗證 Python 版 BT.601、256-bin 直方圖、clamp-to-edge 卷積、PSNR 與零除數防呆。
- MediaPipe Python 實測：以多人臉照片驗證 3 張臉均產生邊界框、6 組關鍵點與信心分數。
- 瀏覽器實測：載入示範圖、切換 R/Y、套用銳化卷積、檢查 PSNR、除數 0、防呆與離線模型。
- PDF：產生後以 Poppler 逐頁轉成 PNG，檢查裁切、重疊、字型與頁碼。
