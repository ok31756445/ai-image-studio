from __future__ import annotations

from pathlib import Path
import subprocess
from xml.sax.saxutils import escape

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
SCREENSHOT_DIR = ROOT / "tmp" / "qa" / "report-python"
AUDIT_TRAIL = ROOT / "docs" / "AI_AUDIT_TRAIL.md"
REPORT_DATE = "2026-11-03"


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
        [p("中繼資訊<br/>尺寸、格式、大小", "SmallZH"), p("1–31 奇數列／欄<br/>正規化、偏移", "SmallZH"), p("PSNR／MSE<br/>前後滑桿比較", "SmallZH")],
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


def screenshot(name: str, caption: str, max_height: float = 104 * mm):
    path = SCREENSHOT_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"缺少報告截圖：{path}")
    figure = Image(str(path))
    figure._restrictSize(168 * mm, max_height)
    return [figure, p(caption, "CaptionZH")]


def load_audit_entries():
    entries = []
    for line in AUDIT_TRAIL.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and cells[0].isdigit():
            entries.append(tuple(escape(cell.replace("`", "")) for cell in cells[:4]))
    return entries


def build_story():
    story = []
    story += [Spacer(1, 22 * mm), p("AI 光影研究室", "TitleZH"), Spacer(1, 4 * mm), p("基於 Python 與 Streamlit 之互動式影像處理、色彩分析、卷積濾波與人臉偵測工具", "SubtitleZH"), Spacer(1, 16 * mm)]
    cover_info = [
        [p("報告狀態", "H3ZH"), p("正式繳交版；功能、排版與公開部署均已驗證", "BodyZH")],
        [p("學號／姓名", "H3ZH"), p(f"{STUDENT_ID}／{STUDENT_NAME}", "BodyZH")],
        [p("開發平台", "H3ZH"), p("Python 3.12、Streamlit 1.66、NumPy、Pillow、MediaPipe 1.2.0", "BodyZH")],
        [p("版本控制", "H3ZH"), p(f"Git；本報告依據 commit {git_head()} 產生", "BodyZH")],
        [p("產製日期", "H3ZH"), p(REPORT_DATE, "BodyZH")],
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
        "已完成 1–31 奇數列／欄的方形或矩形卷積核、三種正規化模式、偏移量、PSNR 與前後對比。",
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
        ["Live Demo", LIVE_DEMO_URL, f"Public；{REPORT_DATE} 公開網路驗證 HTTP 200，免登入可開啟"],
        ["Source Code", SOURCE_CODE_URL, f"Public；{REPORT_DATE} 驗證 HTTP 200，包含完整原始碼與部署檔"],
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
    story += [p("模組責任", "H2ZH")]
    modules = [
        ["模組", "責任與資料"],
        ["streamlit_app.py", "程式入口、頁面設定與工作台啟動"],
        ["workbench.py", "上傳、分頁、狀態生命週期、操作回饋與結果呈現"],
        ["core.py", "色彩轉換、256-bin Histogram、任意卷積核、MSE／PSNR"],
        ["face.py", "MediaPipe CPU 推論、邊界框、關鍵點與信心度"],
    ]
    story += [table(modules, [42 * mm, 123 * mm])]
    story += [PageBreak()]

    story += [p("3.2 功能 1：影像載入與基礎解析", "H2ZH")]
    story += [p("支援 PNG、JPG/JPEG、BMP，可拖放或選檔；載入後即時顯示解析度、百萬像素、格式、檔案大小、色彩維度與每通道 8-bit。超過 3,200 萬像素時拒絕處理並提示先縮小，以限制記憶體。")]
    story += [p("操作：選擇影像 → 檢查中央預覽與右側色階分布 → 使用縮放選單檢視細節。", "CodeZH")]
    story += screenshot("01-load-metadata.png", "圖 3-1　JPG 載入後即時顯示 553 × 554、RGB、檔案大小與 Original 強度直方圖。", 99 * mm)
    story += [p("實測結果", "H3ZH"), p("範例圖成功解碼為 553 × 554 RGB 影像，介面顯示 JPEG 格式與 25.2 KB；中央預覽和直方圖在同一輪更新，符合即時顯示要求。")]
    story += [PageBreak()]

    story += [p("3.3 功能 2：RGB／YUV 與同步直方圖", "H2ZH")]
    story += [p("Original 模式以 BT.709 亮度計算直方圖；R/G/B 模式將指定頻道映射為灰階；Y/U/V 採 BT.601 轉換，U、V 加 128 偏移以落在 0–255。每次切換都以完整非透明 RGBA 像素重算 256 個 bins，橫軸為 0–255 強度，縱軸為實際像素數量。")]
    story += [p("Y = 0.299R + 0.587G + 0.114B<br/>U = -0.168736R - 0.331264G + 0.5B + 128<br/>V = 0.5R - 0.418688G - 0.081312B + 128", "CodeZH")]
    story += screenshot("02-y-channel-histogram.png", "圖 3-2　切換 Y 亮度分量時，中央影像與下方 0–255 像素強度直方圖同步更新。", 105 * mm)
    story += [p("驗證重點：每個通道均保留原解析度；直方圖 256 個 bins 的總和等於影像像素數，縱軸標示像素數量而非抽樣比例。", "SmallZH")]
    story += [PageBreak()]

    story += [p("3.4 功能 3：自訂卷積與 PSNR", "H2ZH")]
    story += [p("矩陣列數與欄數可分別設定為 1–31 的奇數，因此支援 3×7 等矩形核及任意有限權重。預設含原始、銳化、高斯、浮雕、邊緣偵測。正規化可選權重總和、不正規化、自訂除數，並提供 bias。零和核搭配權重總和時會攔截除以零。卷積採 clamp-to-edge；大型矩陣依權重數量降低可處理像素上限，避免工作階段失去回應。")]
    story += [p("MSE = (1 / 3WH) Σ[(R-R')² + (G-G')² + (B-B')²]<br/>PSNR = 10 log10(255² / MSE) dB", "CodeZH")]
    story += [p("PSNR 越高表示濾波結果越接近輸入。MSE=0 時兩者完全相同，PSNR 定義為無限大。套用後工具自動開啟前後對照，可拖曳中央分隔線觀察局部差異。")]
    story += screenshot("03-kernel-psnr.png", "圖 3-3　任意奇數列／欄、矩陣編輯、Normalization、除數／偏移、可拖曳前後比較及 PSNR／MSE。", 90 * mm)
    story += [PageBreak()]

    story += [p("3.4.1 PSNR 客觀評估", "H2ZH")]
    psnr_results = [
        ["濾波器", "矩陣／正規化", "PSNR (dB)", "MSE", "解讀"],
        ["Identity", "3×3／不正規化", "∞", "0.0000", "輸出與原圖完全相同"],
        ["Sharpen", "3×3／不正規化", "25.2595", "193.6991", "強化邊緣，像素差異增加"],
        ["Gaussian", "5×5／權重總和", "32.8450", "33.7736", "有限值中最接近原圖"],
        ["Emboss", "3×3／不正規化", "16.8002", "1358.4919", "風格化幅度最大"],
    ]
    story += [table(psnr_results, [26 * mm, 39 * mm, 25 * mm, 25 * mm, 50 * mm], font_size=7.2)]
    story += [p("結果分析", "H3ZH"), p("Identity 的 MSE=0 驗證公式與實作一致。Gaussian 5×5 的最高有限 PSNR 表示平滑後仍最接近原圖；Sharpen 為保留主體並強化邊緣的中度改變；Emboss 的最低 PSNR 與最高 MSE 符合其強烈風格化效果。PSNR 用於量化像素差異，不等同主觀美感分數。")]
    story += [p("Normalization 防呆：權重總和模式若 ΣK=0，介面拒絕執行；自訂除數若為 0 同樣拒絕，避免 NaN／Infinity 汙染輸出。偶數尺寸、超過 31、空白或非有限數值也會收到明確錯誤。", "CodeZH")]
    story += [PageBreak()]

    story += [p("3.5 功能 4：人臉偵測", "H2ZH")]
    story += [p("使用 MediaPipe Face Detector（BlazeFace Short Range）模型，模型檔隨儲存庫部署並以 bytes 載入；雲端明確使用 CPU delegate。介面回傳人臉總數、平均信心、逐臉信心、邊界框與 6 組關鍵點。模型不做身分、年齡、性別或情緒推測。")]
    story += screenshot("04-face-detection.png", "圖 3-4　多人臉實測：3 張臉均標示邊界框與信心度，右側回傳總數 3、平均信心 95.0%。", 102 * mm)
    face_results = [
        ["偵測結果", "Face 1", "Face 2", "Face 3"],
        ["Confidence", "98.17%", "94.30%", "92.40%"],
        ["關鍵點", "6 組", "6 組", "6 組"],
    ]
    story += [table(face_results, [36 * mm, 43 * mm, 43 * mm, 43 * mm], font_size=7.5)]
    story += [PageBreak()]

    story += [p("3.6 互動與狀態安全", "H2ZH")]
    story += [p("前後比較以原生 range 控制器覆蓋整張影像，支援滑鼠、觸控與鍵盤方向鍵。上傳檔案以 SHA-256 內容雜湊識別；換圖或按下「清除處理結果」會移除 filtered、metrics、detections 與 annotated，避免舊 PSNR 或人臉框殘留。")]
    story += [p("3.7 測試案例與邊界條件", "H2ZH")]
    tests = [
        ["案例", "輸入／操作", "預期結果"],
        ["格式", "PNG、JPEG、BMP", "可解碼、即時顯示、格式與大小正確"],
        ["通道", "切換 R/G/B/Y/U/V", "畫面與直方圖同步；bins 範圍 0–255"],
        ["零和卷積", "Edge kernel + sum normalization", "阻止除以零並提示改用 none/custom"],
        ["極端尺寸", ">32 MP 或大型核超過動態上限", "拒絕並提示縮圖／縮小矩陣"],
        ["Identity kernel", "中心 1、其他 0", "MSE=0、PSNR=∞ dB"],
        ["多人臉", "同圖 2 人以上", "每張臉都有框與信心，總數正確"],
        ["無人臉", "風景／物件", "結果為 0，不產生殘留框"],
        ["狀態重設", "套用卷積後按清除", "PSNR、MSE 與前後比較同步移除"],
    ]
    story += [table(tests, [30 * mm, 58 * mm, 77 * mm], font_size=7.5)]
    story += [Spacer(1, 6 * mm), p("自動化測試摘要", "H2ZH")]
    story += [p("共 14 項 Python 測試通過，涵蓋 BT.601 Y/U/V、256-bin Histogram、clamp-to-edge、3×7、9×9、31×31 卷積核、偶數與超限拒絕、零除數、自訂除數、MSE／PSNR，以及 Streamlit 狀態生命週期。另以瀏覽器完成上傳、通道、前後拖曳、人臉與側欄收合／展開測試。")]
    story += [PageBreak()]

    story += [p("Chapter 4｜AI 協作與完整 Prompt 歷程", "ChapterZH")]
    story += [p("AI 模型：OpenAI Codex（GPT-5 系列）。以下不是對話截圖或摘要抽樣，而是依專案時間序從 docs/AI_AUDIT_TRAIL.md 載入的完整 30 筆 Prompt Audit Trail。每筆均保留原始需求、AI 產出與後續除錯／重構；公開網址與個人資料不由 AI 猜測。")]
    for number, prompt, output, refinement in load_audit_entries():
        story.append(KeepTogether([
            p(f"4.{number} Prompt 歷程", "H3ZH"),
            p(f"<b>原始 Prompt／需求：</b>{prompt}<br/><b>AI 產出結果：</b>{output}<br/><b>除錯／Refinement：</b>{refinement}", "CodeZH"),
        ]))
    story += [Spacer(1, 7 * mm), p("AI 協作原則", "H2ZH")]
    for item in [
        "先以 Git commit 保存可回復基準，再進行介面與演算法修改。",
        "對模型載入、通道公式、卷積除數與拖曳座標逐項找出根因，不只改文案或等待時間。",
        "以 14 項 Python 測試、git diff --check、瀏覽器互動與 PDF 逐頁轉圖驗證。",
        "公開部署 URL 與個人資料以實際提供及 HTTP 驗證結果為準，不由 AI 猜測。",
    ]:
        story.append(bullet(item))
    story += [Spacer(1, 10 * mm)]

    story += [p("評分標準對照與結論", "ChapterZH")]
    rubric = [
        ["Rubric", "權重", "本專案證據"],
        ["功能完整性與正確性", "35%", "格式／RGB-YUV／Histogram／任意奇數 Kernel／PSNR／Face；14 項 Python 測試通過"],
        ["可執行與部署", "20%", "Public GitHub、Streamlit Live Demo、requirements.txt、packages.txt"],
        ["AI Prompt Log", "20%", "Chapter 4 完整收錄 30 筆 Prompt、產出與 Refinement"],
        ["技術報告與排版", "15%", "架構圖、操作、公式、截圖、測試、頁首頁尾與頁碼"],
        ["介面與 UX", "10%", "Python 三欄工作台、拖曳比較、側欄恢復、除零／奇數尺寸／像素上限防呆"],
    ]
    story += [table(rubric, [43 * mm, 18 * mm, 104 * mm]), Spacer(1, 9 * mm)]
    story += [p("結論", "H2ZH"), p("本專案以無伺服器影像上傳的方式完成四大核心功能，並將演算法驗證與直接操作整合在同一個工作台。Public Live Demo 與 Source Code 已部署並以公開網路驗證 HTTP 200；正式 PDF 檔名、學生資料與版本資訊均符合繳交規範。")]
    story += [p("主要檔案", "H2ZH")]
    story += [p(
        "streamlit_app.py：執行入口　｜　python_image_studio/workbench.py：三欄 UI 與互動<br/>"
        "python_image_studio/core.py：RGB/YUV、Histogram、Kernel、PSNR　｜　python_image_studio/face.py：MediaPipe CPU 推論<br/>"
        "requirements.txt／packages.txt：部署相依性　｜　report/generate_report.py：本 PDF 產生器",
        "CodeZH",
    )]
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
