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
OUTPUT = ROOT / "output" / "pdf" / "期中專題_報告草稿.pdf"
SCREENSHOT = ROOT / "tmp" / "qa" / "report-ui.png"


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
    canvas.drawString(18 * mm, 10.5 * mm, "AI 光影研究室｜期中專題報告草稿")
    canvas.drawRightString(PAGE_W - 18 * mm, 10.5 * mm, f"{doc.page}")
    canvas.restoreState()


def architecture_diagram():
    rows = [
        [p("影像輸入", "TableHeadZH"), p("Canvas 處理核心", "TableHeadZH"), p("分析與輸出", "TableHeadZH")],
        [p("PNG / JPG / BMP<br/>拖放、選檔、貼上", "SmallZH"), p("RGBA 解碼<br/>色彩調整／幾何轉換", "SmallZH"), p("通道圖／直方圖<br/>PNG、JPG、WebP", "SmallZH")],
        [p("中繼資訊<br/>尺寸、格式、大小", "SmallZH"), p("3×3／5×5 卷積<br/>正規化、偏移", "SmallZH"), p("PSNR／MSE<br/>前後滑桿比較", "SmallZH")],
        [p("本機檔案", "SmallZH"), p("MediaPipe Face Detection<br/>WASM + BlazeFace", "SmallZH"), p("邊界框、數量<br/>信心分數、匿名化", "SmallZH")],
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
    story += [Spacer(1, 22 * mm), p("AI 光影研究室", "TitleZH"), Spacer(1, 4 * mm), p("基於瀏覽器本機運算之互動式影像處理、色彩分析、卷積濾波與人臉偵測工具", "SubtitleZH"), Spacer(1, 16 * mm)]
    cover_info = [
        [p("報告狀態", "H3ZH"), p("功能版草稿；待提供身分與公開部署資訊後改為正式檔名", "BodyZH")],
        [p("學號／姓名", "H3ZH"), p("尚未提供", "BodyZH")],
        [p("開發平台", "H3ZH"), p("HTML5 Canvas、JavaScript ES2022、Node.js 18+、MediaPipe Tasks Vision 1.2.0", "BodyZH")],
        [p("版本控制", "H3ZH"), p(f"Git；本報告依據 commit {git_head()} 產生", "BodyZH")],
        [p("產製日期", "H3ZH"), p("2026-11-02", "BodyZH")],
    ]
    story += [table(cover_info, [38 * mm, 125 * mm], header=False, font_size=9), Spacer(1, 18 * mm)]
    story += [p("正式繳交前尚需補入：學號、姓名、Public Live Demo URL、Public Source Code URL。補齊後檔名應改為「學號_姓名_期中專題.pdf」。", "CodeZH")]
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
        "已完成 PNG、JPG/JPEG、BMP 讀取與即時顯示；額外支援 WebP、GIF。",
        "已完成 Original、R/G/B、Y/U/V 通道檢視與同步 0–255 強度直方圖。",
        "已完成 3×3／5×5 任意卷積核、三種正規化模式、偏移量、PSNR 與前後對比。",
        "已完成離線 MediaPipe 多人臉框、總數、信心分數與臉部關鍵點。",
        "已完成尺寸與裁切畫布拖曳，同時保留數字欄位與鍵盤替代操作。",
    ]:
        story.append(bullet(item))
    story += [PageBreak()]

    story += [p("Chapter 1｜專案概述與環境建置", "ChapterZH")]
    story += [p("1.1 專案目標", "H2ZH"), p("本專案將影像解碼、像素級色彩轉換、空間濾波、品質量化與人臉偵測整合在同一個瀏覽器工作台。所有影像與模型推論均在使用者裝置執行，不將影像傳送至伺服器。設計目標同時包含演算法可驗證性、操作即時性、隱私與離線可用性。")]
    story += [p("1.2 開發環境", "H2ZH")]
    env = [
        ["項目", "版本／用途"],
        ["JavaScript", "ES2022；影像處理、卷積、PSNR、互動控制"],
        ["HTML / CSS", "HTML5 Canvas、Pointer Events、響應式三欄介面"],
        ["Node.js", "18+；無第三方套件的靜態檔案伺服器"],
        ["MediaPipe", "Tasks Vision 1.2.0；本機 WASM 與 BlazeFace 模型"],
        ["Python", "3.11（報告產製工具）；非應用程式執行必要條件"],
        ["Git", "基準、功能與修正版本控制"],
    ]
    story += [table(env, [42 * mm, 123 * mm]), p("1.3 requirements.txt 條目", "H2ZH")]
    reqs = [
        ["套件", "用途"],
        ["reportlab 4.4.4", "產生排版後 PDF"],
        ["pdfplumber 0.11.8", "抽取文字與頁面檢查"],
        ["pypdf 6.1.1", "PDF 結構與頁數驗證"],
        ["Pillow 12.0.0", "報告圖像尺寸與輸出檢查"],
    ]
    story += [table(reqs, [48 * mm, 117 * mm]), p("主應用程式沒有 Python 或 npm 第三方依賴；requirements.txt 僅用於報告產製。", "SmallZH")]
    story += [p("1.4 啟動", "H2ZH"), p("Windows 可雙擊 start-offline.cmd；跨平台可執行 npm start，預設網址為 http://127.0.0.1:4173。Docker 部署時設定 IMAGE_STUDIO_HOST=0.0.0.0、PORT=7860。", "CodeZH")]
    story += [PageBreak()]

    story += [p("Chapter 2｜可執行連結", "ChapterZH")]
    links = [
        ["項目", "目前狀態", "正式繳交要求"],
        ["Live Demo", "尚未提供公開 URL", "部署至 Hugging Face Spaces／其他公開 HTTPS 網址，確認免登入可開啟"],
        ["Source Code", "尚未提供 GitHub／GitLab URL", "Public 儲存庫，包含 vendor、Dockerfile、README、完整原始碼"],
        ["本機執行", "已完成", "start-offline.cmd 或 npm start"],
        ["Docker", "已完成 Dockerfile", "Hugging Face Docker Space 使用 7860 port"],
        ["GitHub Pages", "工作流已完成", "推送 main 後先執行 npm check／test，再自動部署"],
    ]
    story += [table(links, [33 * mm, 48 * mm, 84 * mm]), Spacer(1, 8 * mm)]
    story += [p("部署驗收清單", "H2ZH")]
    for item in [
        "首頁、advanced-tools.js、MediaPipe WASM 與 TFLite 模型均回傳 HTTP 200。",
        "使用 Public／無痕視窗測試，不依賴本機快取或私人權限。",
        "載入範例圖後測試通道、卷積、PSNR、前後對照與人臉偵測。",
        "Git tag 與正式 PDF 內的 commit hash 對齊。",
    ]:
        story.append(bullet(item))
    story += [p("建議公開方式", "H2ZH"), p("Hugging Face Spaces 可直接使用專案 Dockerfile；GitHub 儲存庫則保留完整 vendor/mediapipe 離線模型。若使用 GitHub Pages，需確認伺服器以正確 MIME type 提供 .wasm 與 .tflite。")]
    story += [PageBreak()]

    story += [p("Chapter 3｜程式功能與操作說明書", "ChapterZH"), p("3.1 模組架構與資料流", "H2ZH"), architecture_diagram(), Spacer(1, 8 * mm)]
    story += [p("資料流：檔案經瀏覽器 Image 解碼為 RGBA Canvas；色彩／幾何調整產生處理畫布；通道模組只改變檢視層，不破壞輸出；卷積將核逐像素套用後提交歷史；MediaPipe 從處理畫布建立縮圖推論並將座標映射回原尺寸。")]
    if SCREENSHOT.exists():
        img = Image(str(SCREENSHOT))
        img._restrictSize(168 * mm, 116 * mm)
        story += [Spacer(1, 3 * mm), img, p("圖 3-1　Y 亮度分量、同步直方圖、卷積矩陣與本機人臉模組整合畫面", "CaptionZH")]
    story += [PageBreak()]

    story += [p("3.2 功能 1：影像載入與基礎解析", "H2ZH")]
    story += [p("支援 PNG、JPG/JPEG、BMP、WebP、GIF。可拖放、選檔或貼上；載入後即時顯示解析度、百萬像素、格式、檔案大小、RGBA 四通道與每通道 8-bit。超過 3,200 萬像素時等比例縮小，以限制記憶體。")]
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
    story += [p("使用 MediaPipe Face Detector（BlazeFace Short Range）離線模型。影像最長邊縮至 1024 px 推論，偵測框與 6 組關鍵點再依比例映射回原圖。介面回傳人臉總數、平均信心、各臉信心與邊界框，並提供單臉裁切、全臉模糊與像素化。模型不做身分、年齡、性別或情緒推測。")]
    story += [p("3.6 拖曳尺寸與裁切", "H2ZH")]
    story += [p("尺寸工具以四角控制點改變目標寬高；比例鎖定時依主導軸維持比例。裁切工具可在空白區拖出新框、拖框內移動、拖四角縮放。兩者都同步更新數值欄位，按「套用」才寫入影像與復原歷史；Esc 可離開拖曳模式。")]
    story += [p("3.7 測試案例與邊界條件", "H2ZH")]
    tests = [
        ["案例", "輸入／操作", "預期結果"],
        ["格式", "PNG、JPEG、BMP", "可解碼、即時顯示、格式與大小正確"],
        ["通道", "切換 R/G/B/Y/U/V", "畫面與直方圖同步；bins 範圍 0–255"],
        ["零和卷積", "Edge kernel + sum normalization", "阻止除以零並提示改用 none/custom"],
        ["極端尺寸", ">32 MP 或卷積 >12 MP", "縮圖或要求先縮小，介面不凍結"],
        ["Identity kernel", "中心 1、其他 0", "MSE=0、PSNR=∞ dB"],
        ["多人臉", "同圖 2 人以上", "每張臉都有框與信心，總數正確"],
        ["無人臉", "風景／物件", "結果為 0，不產生殘留框"],
        ["裁切邊界", "拖曳超出畫布", "X/Y/寬/高被限制在影像內"],
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
        "公開部署 URL 與個人資料不由 AI 猜測；缺少時明確列為尚待提供。",
    ]:
        story.append(bullet(item))
    story += [Spacer(1, 10 * mm)]

    story += [p("評分標準對照與結論", "ChapterZH")]
    rubric = [
        ["Rubric", "權重", "本專案證據"],
        ["功能完整性與正確性", "35%", "格式／RGB-YUV／完整像素 Histogram／Kernel／PSNR／Face；6 項演算法測試通過"],
        ["可執行與部署", "20%", "start-offline.cmd、npm start、Dockerfile；正式 URL 尚待提供"],
        ["AI Prompt Log", "20%", "Chapter 4 依時序記錄 Prompt、產出與 Refinement"],
        ["技術報告與排版", "15%", "架構圖、操作、公式、截圖、測試、頁首頁尾與頁碼"],
        ["介面與 UX", "10%", "拖曳＋數字替代、44 px 命中區、除零／尺寸／像素上限防呆"],
    ]
    story += [table(rubric, [43 * mm, 18 * mm, 104 * mm]), Spacer(1, 9 * mm)]
    story += [p("結論", "H2ZH"), p("本專案以無伺服器影像上傳的方式完成四大核心功能，並將演算法驗證與直接操作整合在同一個工作台。正式繳交前只需補上學號、姓名、公開 Live Demo 與 Source Code URL，重新產生 PDF 並以 Public／無痕環境完成最終驗收。")]
    story += [p("主要檔案", "H2ZH")]
    files = [
        ["檔案", "職責"],
        ["index.html / styles.css", "介面結構、色彩通道、矩陣、拖曳工具與響應式樣式"],
        ["app.js", "載圖、Canvas 編輯、幾何工具、前後對照、匯出、歷史"],
        ["advanced-tools.js", "RGB/YUV、同步直方圖、卷積、PSNR"],
        ["face-analysis.js", "MediaPipe 模型載入、推論、框與匿名化"],
        ["offline-server.cjs / Dockerfile", "本機與公開容器部署"],
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
        title="AI 光影研究室 - 期中專題報告草稿",
        author="尚待提供",
        subject="互動式影像處理、色彩分析、卷積濾波、PSNR 與人臉偵測",
    )
    document.build(build_story(), onFirstPage=header_footer, onLaterPages=header_footer)
    print(OUTPUT)


if __name__ == "__main__":
    main()
