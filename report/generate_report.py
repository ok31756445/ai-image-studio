from __future__ import annotations

from pathlib import Path
import subprocess

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
STUDENT_ID = "C112152350"
STUDENT_NAME = "胡景翔"
SOURCE_CODE_URL = "https://github.com/ok31756445/ai-image-studio"
LIVE_DEMO_URL = "https://ai-image-studio-c112152350.streamlit.app/"
OUTPUT = ROOT / "output" / "pdf" / f"{STUDENT_ID}_{STUDENT_NAME}_期中專題.pdf"
SCREENSHOT = ROOT / "tmp" / "qa" / "python-workbench-1440.png"


def git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "尚未建立 commit"

pdfmetrics.registerFont(TTFont("JhengHei", r"C:\Windows\Fonts\msjh.ttc"))
pdfmetrics.registerFont(TTFont("JhengHeiBold", r"C:\Windows\Fonts\msjhbd.ttc"))
pdfmetrics.registerFontFamily("JhengHei", normal="JhengHei", bold="JhengHeiBold")

PAGE_W, PAGE_H = A4
INK = colors.HexColor("#172027")
MUTED = colors.HexColor("#5f6e78")
LINE = colors.HexColor("#d8e0e5")
PAPER = colors.HexColor("#f5f7f8")
AMBER = colors.HexColor("#d88d21")
CYAN = colors.HexColor("#248fa4")
DARK = colors.HexColor("#11161b")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="BodyZH", fontName="JhengHei", fontSize=9.5, leading=15, textColor=INK, spaceAfter=6))
styles.add(ParagraphStyle(name="SmallZH", fontName="JhengHei", fontSize=8, leading=12, textColor=MUTED))
styles.add(ParagraphStyle(name="TitleZH", fontName="JhengHeiBold", fontSize=26, leading=36, textColor=DARK, alignment=TA_CENTER))
styles.add(ParagraphStyle(name="SubtitleZH", fontName="JhengHei", fontSize=12, leading=19, textColor=MUTED, alignment=TA_CENTER))
styles.add(ParagraphStyle(name="ChapterZH", fontName="JhengHeiBold", fontSize=19, leading=27, textColor=DARK, spaceAfter=12))
styles.add(ParagraphStyle(name="H2ZH", fontName="JhengHeiBold", fontSize=13, leading=19, textColor=CYAN, spaceBefore=8, spaceAfter=6))
styles.add(ParagraphStyle(name="H3ZH", fontName="JhengHeiBold", fontSize=10.5, leading=16, textColor=INK, spaceBefore=5, spaceAfter=4))
styles.add(ParagraphStyle(name="CodeZH", fontName="JhengHei", fontSize=8.5, leading=13, textColor=INK, backColor=PAPER, borderColor=LINE, borderWidth=.5, borderPadding=7, spaceAfter=7))
styles.add(ParagraphStyle(name="CaptionZH", fontName="JhengHei", fontSize=7.5, leading=11, textColor=MUTED, alignment=TA_CENTER, spaceBefore=4, spaceAfter=9))
styles.add(ParagraphStyle(name="TableCellZH", fontName="JhengHei", fontSize=8, leading=12, textColor=INK))
styles.add(ParagraphStyle(name="TableHeadZH", fontName="JhengHeiBold", fontSize=8, leading=12, textColor=colors.white))


def p(text: str, style: str = "BodyZH") -> Paragraph:
    return Paragraph(text, styles[style])


def bullet(text: str) -> Paragraph:
    return Paragraph(f"• {text}", styles["BodyZH"])


def table(data, widths, header=True, font_size=8):
    normalized = []
    for row_index, row in enumerate(data):
        normalized.append([
            cell if isinstance(cell, Paragraph) else Paragraph(str(cell), styles["TableHeadZH" if header and row_index == 0 else "TableCellZH"])
            for cell in row
        ])
    result = Table(normalized, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("FONTNAME", (0, 0), (-1, -1), "JhengHei"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("LEADING", (0, 0), (-1, -1), font_size + 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), .45, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, PAPER]),
    ]
    if header:
        commands += [
            ("BACKGROUND", (0, 0), (-1, 0), DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "JhengHeiBold"),
        ]
    result.setStyle(TableStyle(commands))
    return result


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(.4)
    canvas.line(18 * mm, 16 * mm, PAGE_W - 18 * mm, 16 * mm)
    canvas.setFont("JhengHei", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 10.5 * mm, f"AI 光影研究室｜{STUDENT_ID} {STUDENT_NAME}")
    canvas.drawRightString(PAGE_W - 18 * mm, 10.5 * mm, f"{doc.page}")
    canvas.restoreState()


def architecture_diagram():
    rows = [
        [p("Streamlit 輸入／狀態", "TableHeadZH"), p("Python 運算核心", "TableHeadZH"), p("分析與輸出", "TableHeadZH")],
        [p("PNG / JPG / BMP<br/>拖放、選檔", "SmallZH"), p("Pillow 解碼<br/>NumPy RGB 陣列", "SmallZH"), p("通道圖／直方圖<br/>PNG 下載", "SmallZH")],
        [p("中繼資訊<br/>尺寸、格式、大小", "SmallZH"), p("3×3／5×5 卷積<br/>正規化、偏移", "SmallZH"), p("PSNR／MSE<br/>前後滑桿比較", "SmallZH")],
        [p("Session State<br/>切換即清除舊結果", "SmallZH"), p("MediaPipe Face Detector<br/>CPU + BlazeFace", "SmallZH"), p("邊界框、總數<br/>逐臉信心度", "SmallZH")],
    ]
    diagram = Table(rows, colWidths=[52 * mm, 62 * mm, 52 * mm], rowHeights=[12 * mm, 22 * mm, 22 * mm, 24 * mm])
    diagram.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "JhengHei"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), .6, LINE),
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (1, 1), (1, -1), colors.HexColor("#eaf7fa")),
        ("BACKGROUND", (0, 1), (0, -1), PAPER),
        ("BACKGROUND", (2, 1), (2, -1), colors.HexColor("#fff5e7")),
    ]))
    return diagram


def build_story():
    story = []
    story += [Spacer(1, 22 * mm), p("AI 光影研究室", "TitleZH"), Spacer(1, 4 * mm), p("基於 Python 與 Streamlit 之互動式影像處理、色彩分析、卷積濾波與人臉偵測工具", "SubtitleZH"), Spacer(1, 16 * mm)]
    cover_info = [
        [p("報告狀態", "H3ZH"), p("正式繳交版；功能、排版與公開部署均已驗證", "BodyZH")],
        [p("學號／姓名", "H3ZH"), p(f"{STUDENT_ID}／{STUDENT_NAME}", "BodyZH")],
        [p("開發平台", "H3ZH"), p("Python 3.12、Streamlit 1.66、NumPy、Pillow、MediaPipe 1.2.0", "BodyZH")],
        [p("版本控制", "H3ZH"), p(f"Git；本報告依據 commit {git_head()} 產生", "BodyZH")],
        [p("產製日期", "H3ZH"), p("2026-11-02", "BodyZH")],
    ]
    story += [table(cover_info, [38 * mm, 125 * mm], header=False, font_size=9), Spacer(1, 18 * mm)]
    story += [p(f"Public Live Demo：{LIVE_DEMO_URL}<br/>Public Source Code：{SOURCE_CODE_URL}", "CodeZH")]
    story += [PageBreak()]

    story += [p("目錄與驗收摘要", "ChapterZH")]
    toc = [
        ["章節", "內容", "對應驗收"],
        ["Chapter 1", "專案概述、技術環境、相依性與啟動方式", "環境可重現"],
        ["Chapter 2", "Live Demo／Source Code 公開連結狀態與部署方法", "可執行成果"],
        ["Chapter 3", "四大功能、演算法、操作、測試與 PSNR 評估", "功能正確性、UX"],
        ["Chapter 4", "AI 模型版本、Prompt、產出與 Refinement 歷程", "AI Audit Trail"],
    ]
    story += [table(toc, [28 * mm, 92 * mm, 45 * mm]), Spacer(1, 8 * mm)]
    story += [p("完成度摘要", "H2ZH")]
    for item in [
        "已完成 PNG、JPG/JPEG、BMP 讀取、即時顯示與中繼資訊解析。",
        "已完成 Original、R/G/B、Y/U/V 通道檢視與同步 0–255 強度直方圖。",
        "已完成 3×3／5×5 任意卷積核、三種正規化模式、偏移量、PSNR 與前後對比。",
        "已完成 MediaPipe 多人臉框、總數、逐臉信心分數與 6 組臉部關鍵點。",
        "已完成內容雜湊狀態隔離；換圖或清除結果時同步移除 PSNR 與舊人臉結果。",
    ]:
        story.append(bullet(item))
    story += [PageBreak()]

    story += [p("Chapter 1｜專案概述與環境建置", "ChapterZH")]
    story += [p("1.1 專案目標", "H2ZH"), p("本專案將影像解碼、像素級色彩轉換、空間濾波、品質量化與人臉偵測整合在同一個 Streamlit 工作台。影像只存在於目前的 Python 工作階段，不送往第三方辨識服務。設計目標同時包含演算法可驗證性、操作即時性、部署可重現性與隱私。")]
    story += [p("1.2 開發環境", "H2ZH")]
    env = [
        ["項目", "版本／用途"],
        ["Python", "3.9+；建議 3.12，應用程式與報告產製語言"],
        ["Streamlit", "1.66.0；互動 UI、Session State、圖表與下載"],
        ["NumPy / Pandas", "像素運算、卷積、256-bin 直方圖與資料表"],
        ["Pillow", "PNG、JPEG、BMP 解碼、RGB 轉換與影像輸出"],
        ["MediaPipe", "1.2.0；CPU Face Detector 與 BlazeFace 本機模型"],
        ["Git", "基準、功能與修正版本控制"],
    ]
    story += [table(env, [42 * mm, 123 * mm]), p("1.3 requirements.txt 條目", "H2ZH")]
    reqs = [
        ["套件", "用途"],
        ["streamlit 1.66.0", "Web App 介面與互動狀態"],
        ["numpy / pandas", "像素演算法與資料整理"],
        ["mediapipe 1.2.0", "人臉偵測、框、關鍵點與信心度"],
        ["Pillow 12.0.0", "影像解碼、轉換、標註與匯出"],
        ["reportlab 4.4.4", "產生排版後 PDF"],
        ["pdfplumber 0.11.8", "抽取文字與頁面檢查"],
        ["pypdf 6.1.1", "PDF 結構與頁數驗證"],
    ]
    story += [table(reqs, [48 * mm, 117 * mm]), p("Linux 部署另由 packages.txt 安裝 libgl1、libegl1、libgles2 與 libglib2.0-0。", "SmallZH")]
    story += [p("1.4 啟動", "H2ZH"), p("python -m venv .venv<br/>.venv\\Scripts\\python -m pip install -r requirements.txt<br/>.venv\\Scripts\\python -m streamlit run streamlit_app.py", "CodeZH")]
    story += [PageBreak()]

    story += [p("Chapter 2｜可執行連結", "ChapterZH")]
    links = [
        ["項目", "目前狀態", "正式繳交要求"],
        ["Live Demo", LIVE_DEMO_URL, "已以公開網路驗證 HTTP 200，免登入可開啟"],
        ["Source Code", SOURCE_CODE_URL, "Public 儲存庫，包含 vendor、Dockerfile、README、完整原始碼"],
        ["本機執行", "已完成", "start-python.cmd 或 streamlit run streamlit_app.py"],
        ["Streamlit Cloud", "已部署", "main / streamlit_app.py；packages.txt 補齊 Linux 執行期"],
        ["GitHub Pages", "保留舊 JS 版", "作為版本備份，不是目前 Python 主版本"],
    ]
    story += [table(links, [33 * mm, 48 * mm, 84 * mm]), Spacer(1, 8 * mm)]
    story += [p("部署驗收清單", "H2ZH")]
    for item in [
        "Streamlit 首頁已由公開網路驗證 HTTP 200，免 GitHub 帳號即可開啟。",
        "使用 Public／無痕視窗測試，不依賴本機快取或私人權限。",
        "載入範例圖後測試通道、卷積、PSNR、前後對照與人臉偵測。",
        "Git tag 與正式 PDF 內的 commit hash 對齊。",
    ]:
        story.append(bullet(item))
    story += [p("部署方式", "H2ZH"), p("Streamlit Community Cloud 連接 Public GitHub 儲存庫，主程式指定 streamlit_app.py。requirements.txt 安裝 Python 套件，packages.txt 安裝 MediaPipe 所需 Linux 系統函式庫；Face Detector 明確指定 CPU delegate。")]
    story += [PageBreak()]

    story += [p("Chapter 3｜程式功能與操作說明書", "ChapterZH"), p("3.1 模組架構與資料流", "H2ZH"), architecture_diagram(), Spacer(1, 8 * mm)]
    story += [p("資料流：上傳檔案由 Pillow 解碼並轉成 RGB NumPy 陣列；通道切換呼叫 BT.601 轉換並同步重算 256-bin 直方圖；卷積結果與 PSNR 寫入 Streamlit Session State；MediaPipe 直接以 RGB 陣列進行 CPU 推論，再由 Pillow 標註邊界框、關鍵點與信心度。")]
    if SCREENSHOT.exists():
        img = Image(str(SCREENSHOT))
        img._restrictSize(168 * mm, 116 * mm)
        story += [Spacer(1, 3 * mm), img, p("圖 3-1　Y 亮度分量、同步直方圖、卷積矩陣與本機人臉模組整合畫面", "CaptionZH")]
    story += [PageBreak()]

    story += [p("3.2 功能 1：影像載入與基礎解析", "H2ZH")]
    story += [p("支援 PNG、JPG/JPEG、BMP，可拖放或選檔；載入後即時顯示解析度、百萬像素、格式、檔案大小、色彩維度與每通道 8-bit。超過 3,200 萬像素時拒絕處理並提示先縮小，以限制記憶體。")]
    story += [p("操作：選擇影像 → 檢查中央預覽與右側色階分布 → 使用縮放選單檢視細節。", "CodeZH")]
    story += [p("3.3 功能 2：RGB／YUV 與同步直方圖", "H2ZH")]
    story += [p("Original 模式以 BT.709 亮度計算直方圖；R/G/B 模式將指定頻道映射為灰階；Y/U/V 採 BT.601 轉換，U、V 加 128 偏移以落在 0–255。每次切換都以完整非透明 RGBA 像素重算 256 個 bins，橫軸為 0–255 強度，縱軸為實際像素數量。")]
    story += [p("Y = 0.299R + 0.587G + 0.114B<br/>U = -0.168736R - 0.331264G + 0.5B + 128<br/>V = 0.5R - 0.418688G - 0.081312B + 128", "CodeZH")]
    story += [p("3.4 功能 3：自訂卷積與 PSNR", "H2ZH")]
    story += [p("矩陣支援 3×3、5×5 與任意有限數值。預設含原始、銳化、高斯、浮雕、邊緣偵測。正規化可選權重總和、不正規化、自訂除數，並提供 bias。零和核搭配權重總和時會攔截除以零。卷積採 clamp-to-edge；大於 1,200 萬像素時要求先縮圖，避免主執行緒失去回應。")]
    story += [p("MSE = (1 / 3WH) Σ[(R-R')² + (G-G')² + (B-B')²]<br/>PSNR = 10 log10(255² / MSE) dB", "CodeZH")]
    story += [p("PSNR 越高表示濾波結果越接近輸入。MSE=0 時兩者完全相同，PSNR 定義為無限大。套用後工具自動開啟前後對照，可拖曳中央分隔線觀察局部差異。")]
    story += [PageBreak()]

    story += [p("3.5 功能 4：人臉偵測", "H2ZH")]
    story += [p("使用 MediaPipe Face Detector（BlazeFace Short Range）模型，模型檔隨儲存庫部署並以 bytes 載入；雲端明確使用 CPU delegate。介面回傳人臉總數、平均信心、逐臉信心、邊界框與 6 組關鍵點。模型不做身分、年齡、性別或情緒推測。")]
    story += [p("3.6 互動與狀態安全", "H2ZH")]
    story += [p("前後比較以原生 range 控制器覆蓋整張影像，支援滑鼠、觸控與鍵盤方向鍵。上傳檔案以 SHA-256 內容雜湊識別；換圖或按下「清除處理結果」會移除 filtered、metrics、detections 與 annotated，避免舊 PSNR 或人臉框殘留。")]
    story += [p("3.7 測試案例與邊界條件", "H2ZH")]
    tests = [
        ["案例", "輸入／操作", "預期結果"],
        ["格式", "PNG、JPEG、BMP", "可解碼、即時顯示、格式與大小正確"],
        ["通道", "切換 R/G/B/Y/U/V", "畫面與直方圖同步；bins 範圍 0–255"],
        ["零和卷積", "Edge kernel + sum normalization", "阻止除以零並提示改用 none/custom"],
        ["極端尺寸", ">32 MP 或卷積 >12 MP", "拒絕並要求先縮小，介面不凍結"],
        ["Identity kernel", "中心 1、其他 0", "MSE=0、PSNR=∞ dB"],
        ["多人臉", "同圖 2 人以上", "每張臉都有框與信心，總數正確"],
        ["無人臉", "風景／物件", "結果為 0，不產生殘留框"],
        ["狀態重設", "套用卷積後按清除", "PSNR、MSE 與前後比較同步移除"],
    ]
    story += [table(tests, [30 * mm, 58 * mm, 77 * mm], font_size=7.5)]
    story += [PageBreak()]

    story += [p("Chapter 4｜AI 協作與完整 Prompt 歷程", "ChapterZH")]
    story += [p("AI 模型：OpenAI Codex（GPT-5 系列）。以下依本專案對話順序保存原始需求、AI 產出結果與後續 Refinement。公開網址與個人資料不由 AI 猜測；詳細版同時保存在 docs/AI_AUDIT_TRAIL.md。")]
    audit = [
        ("技能安裝與排錯", "研究並安裝 ui-ux-pro-max；處理 unknown option --dry-run 與 Test-Path=False。", "確認 Codex skill 結構、SKILL.md 路徑及可用技能清單。", "移除不支援參數，改用支援的安裝方式並實際驗證。"),
        ("影像工具初版", "開發具 GUI／Web App 的 AI 影像處理與人臉分析工具。", "建立三欄本機影像工作台、Canvas 編輯、分析與匯出。", "補入離線、隱私、狀態、錯誤與響應式需求。"),
        ("模型效能", "人臉模型載入／推論太久、沒有結果，要求改成離線。", "將 MediaPipe JS、WASM 與 BlazeFace 放入 vendor。", "分離待命與分析狀態、加入逾時／取消、推論最長邊限制 1024 px。"),
        ("介面重構", "使用 frontend-design 與 ui-ux-pro-max 調整專案並確認 Git 備份。", "建立數位暗房視覺、語意化區段與明確狀態。", "建立基準 commit，保留使用者檔案並逐批驗證。"),
        ("前後比較", "前後對比無法拖動。", "讓可見分隔線直接處理 Pointer Events。", "擴大拖曳命中區並保留原生 range 鍵盤替代。"),
        ("尺寸與裁切", "兩個功能都要以拖動方式完成。", "加入尺寸四角與裁切建立／移動／縮放。", "同步數值、限制邊界與像素上限、加入 Esc 與復原歷史。"),
        ("期中規格", "加入格式、中繼資訊、RGB/YUV、Histogram、Kernel、PSNR、Face 與 PDF。", "完成四大核心模組、部署檔與報告產生器。", "加入公式、零除防呆、32 MP／12 MP 上限與驗收表。"),
        ("PSNR 重設", "按下重設後 PSNR 是否應清除。", "判定舊指標已失去比較基準。", "重設時清除 PSNR／MSE、卷積狀態、比較狀態並取消舊運算。"),
        ("Rubric 稽核", "依五項評分表檢查專案。", "實測讀檔、通道、直方圖、卷積、PSNR、模型、PDF 與部署。", "找出公開 URL、精確像素計數、多人臉證據與 Prompt Log 缺口。"),
        ("本輪修正", "開始修正。", "改為完整像素直方圖，建立演算法測試、Pages 工作流與完整 Audit Trail。", "保留公開 URL、學號與姓名為必須由使用者提供的最終資料。"),
        ("Python 遷移與最終驗收", "改用 Python，並依四大核心功能、繳交規範與 Rubric 再次檢查。", "完成 Streamlit 三欄工作台、NumPy/Pillow 演算法與 MediaPipe CPU 推論。", "修正 5×5 identity、內容雜湊狀態隔離、逐臉信心明細；8 項 Python 測試與 PDF 視覺驗證通過。"),
    ]
    for index, (stage, prompt, output, refinement) in enumerate(audit, 1):
        story.append(KeepTogether([
            p(f"4.{index} {stage}", "H3ZH"),
            p(f"<b>原始 Prompt／需求：</b>{prompt}<br/><b>AI 產出結果：</b>{output}<br/><b>除錯／Refinement：</b>{refinement}", "CodeZH"),
        ]))
    story += [Spacer(1, 7 * mm), p("AI 協作原則", "H2ZH")]
    for item in [
        "先以 Git commit 保存可回復基準，再進行介面與演算法修改。",
        "對模型載入、通道公式、卷積除數與拖曳座標逐項找出根因，不只改文案或等待時間。",
        "以 npm run check、npm test、git diff --check、瀏覽器互動與 PDF 逐頁轉圖驗證。",
        "公開部署 URL 與個人資料以實際提供及 HTTP 驗證結果為準，不由 AI 猜測。",
    ]:
        story.append(bullet(item))
    story += [Spacer(1, 10 * mm)]

    story += [p("評分標準對照與結論", "ChapterZH")]
    rubric = [
        ["Rubric", "權重", "本專案證據"],
        ["功能完整性與正確性", "35%", "格式／RGB-YUV／完整像素 Histogram／Kernel／PSNR／Face；8 項 Python 測試通過"],
        ["可執行與部署", "20%", "Public GitHub、Streamlit Live Demo、requirements.txt、packages.txt"],
        ["AI Prompt Log", "20%", "Chapter 4 依時序記錄 Prompt、產出與 Refinement"],
        ["技術報告與排版", "15%", "架構圖、操作、公式、截圖、測試、頁首頁尾與頁碼"],
        ["介面與 UX", "10%", "JS 版三欄視覺、44 px 操作區、鍵盤拖曳替代、除零／像素上限防呆"],
    ]
    story += [table(rubric, [43 * mm, 18 * mm, 104 * mm]), Spacer(1, 9 * mm)]
    story += [p("結論", "H2ZH"), p("本專案以無伺服器影像上傳的方式完成四大核心功能，並將演算法驗證與直接操作整合在同一個工作台。Public Live Demo 與 Source Code 已部署並以公開網路驗證 HTTP 200；正式 PDF 檔名、學生資料與版本資訊均符合繳交規範。")]
    story += [p("主要檔案", "H2ZH")]
    files = [
        ["檔案", "職責"],
        ["streamlit_app.py", "Streamlit Cloud 與本機執行入口"],
        ["python_image_studio/workbench.py", "三欄 UI、狀態、圖表、卷積與下載互動"],
        ["python_image_studio/core.py", "RGB/YUV、Histogram、Kernel、PSNR 與影像編碼"],
        ["python_image_studio/face.py", "MediaPipe CPU 推論、框、關鍵點與信心度"],
        ["requirements.txt / packages.txt", "Python 與 Linux 部署相依性"],
        ["report/generate_report.py", "本 PDF 產生器"],
    ]
    story += [table(files, [58 * mm, 107 * mm])]
    return story


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=22 * mm,
        title="AI 光影研究室 - 期中專題報告",
        author=f"{STUDENT_ID} {STUDENT_NAME}",
        subject="互動式影像處理、色彩分析、卷積濾波、PSNR 與人臉偵測",
    )
    document.build(build_story(), onFirstPage=header_footer, onLaterPages=header_footer)
    print(OUTPUT)


if __name__ == "__main__":
    main()
