"""Streamlit workbench UI aligned with the original JavaScript application."""

from __future__ import annotations

import base64
from html import escape
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, UnidentifiedImageError

from .core import (
    MAX_IMAGE_PIXELS,
    apply_convolution,
    channel_plane,
    encode_image,
    ensure_rgb,
    histogram,
    image_metadata,
    psnr,
    validate_kernel,
)
from .face import annotate_faces, detect_faces


ROOT = Path(__file__).resolve().parent.parent
FACE_MODEL = ROOT / "vendor" / "mediapipe" / "models" / "blaze_face_short_range.tflite"

PRESETS: dict[str, dict[int, list[list[float]]]] = {
    "原始": {3: [[0, 0, 0], [0, 1, 0], [0, 0, 0]], 5: np.eye(5).tolist()},
    "邊緣銳化": {3: [[0, -1, 0], [-1, 5, -1], [0, -1, 0]]},
    "高斯平滑": {
        3: [[1, 2, 1], [2, 4, 2], [1, 2, 1]],
        5: np.outer([1, 4, 6, 4, 1], [1, 4, 6, 4, 1]).tolist(),
    },
    "浮雕": {3: [[-2, -1, 0], [-1, 1, 1], [0, 1, 2]]},
    "邊緣偵測": {3: [[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]]},
}


APP_CSS = """
<style>
:root {
  --bg:#0b0e11; --surface:#11161b; --raised:#182027; --hover:#202a32;
  --stage:#080b0e; --text:#edf2f5; --subtle:#b7c0c7; --muted:#7f8c96;
  --line:#27323a; --line-strong:#3a4852; --accent:#e8a84a;
  --accent-strong:#f1ba68; --accent-ink:#211506; --cyan:#58c4d8;
  --danger:#ff7d70; --focus:#7bd9e8;
}
html, body, [class*="css"] { font-family:"Segoe UI Variable","Noto Sans TC","Microsoft JhengHei",system-ui,sans-serif; }
.stApp { color:var(--text); background:var(--bg); }
[data-testid="stHeader"], [data-testid="stToolbar"], footer { display:none !important; }
.block-container { max-width:none; padding:84px 16px 18px; }
[data-testid="stSidebar"] { top:68px; height:calc(100dvh - 68px); background:var(--surface); border-right:1px solid var(--line); }
[data-testid="stSidebar"] > div:first-child { padding-top:14px; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap:.72rem; }

.workbench-header { position:fixed; z-index:999; inset:0 0 auto 0; height:68px; display:grid;
  grid-template-columns:1fr auto 1fr; align-items:center; gap:20px; padding:0 22px;
  border-bottom:1px solid var(--line); background:rgba(17,22,27,.98); }
.brand-lockup { display:flex; align-items:center; gap:11px; min-width:0; }
.brand-mark { width:38px; height:38px; display:grid; place-items:center; flex:0 0 auto;
  color:var(--accent-ink); background:var(--accent); border-radius:9px 9px 9px 2px;
  box-shadow:0 7px 24px rgba(232,168,74,.16); }
.brand-mark svg { width:23px; height:23px; fill:none; stroke:currentColor; stroke-width:1.8; stroke-linecap:round; stroke-linejoin:round; }
.brand-copy strong,.brand-copy small { display:block; }
.brand-copy strong { font:700 17px/1.15 Bahnschrift,"Segoe UI Variable",sans-serif; letter-spacing:.035em; }
.brand-copy small { margin-top:3px; color:var(--muted); font-size:10px; font-weight:650; }
.session-status { display:inline-flex; align-items:center; gap:8px; padding:7px 12px; border:1px solid var(--line);
  border-radius:7px; color:var(--subtle); background:#151c22; font-size:12px; font-weight:650; }
.session-dot { width:7px; height:7px; border-radius:50%; background:var(--accent); box-shadow:0 0 0 4px rgba(232,168,74,.09); }
.header-runtime { justify-self:end; padding:8px 12px; border:1px solid var(--line); border-radius:8px;
  color:var(--muted); font-size:11px; font-weight:700; }

.panel-heading { display:flex; align-items:center; justify-content:space-between; gap:10px;
  margin:6px 0 10px; padding-left:10px; border-left:2px solid var(--accent); }
.panel-heading h2 { margin:0; color:var(--text); font-size:13px; line-height:1.3; letter-spacing:.02em; }
.panel-badge { padding:4px 8px; border-radius:999px; color:var(--accent); background:rgba(232,168,74,.08); font-size:9px; font-weight:800; }
.panel-badge.ready { color:#bdeff6; background:rgba(88,196,216,.09); }
.panel-copy { margin:0 0 12px; color:var(--muted); font-size:11px; line-height:1.6; }
.panel-rule { height:1px; margin:18px -16px 14px; background:var(--line); }

[data-testid="stFileUploader"] { padding:10px 0 2px; }
[data-testid="stFileUploaderDropzone"] { min-height:138px; border:1px dashed #465147 !important;
  border-radius:10px !important; background:#141915 !important; }
[data-testid="stFileUploaderDropzone"] button { min-height:42px; color:var(--accent-ink) !important;
  background:var(--accent) !important; border:0 !important; font-weight:800 !important; }
[data-testid="stFileUploaderDropzoneInstructions"] span { color:var(--text) !important; font-weight:750; }
[data-testid="stFileUploaderDropzoneInstructions"] small { display:none; }

div[data-testid="stColumn"]:has(.stage-anchor) { min-height:calc(100dvh - 102px); padding:0 14px 10px;
  border:1px solid var(--line); background-color:var(--stage);
  background-image:radial-gradient(circle,rgba(127,140,150,.13) 1px,transparent 1px); background-size:24px 24px; }
div[data-testid="stColumn"]:has(.analysis-anchor) { padding:4px 16px 18px; border:1px solid var(--line); background:var(--surface); }
.stage-anchor,.analysis-anchor { height:0; overflow:hidden; }
.stage-toolbar { display:flex; justify-content:space-between; align-items:center; gap:12px; min-height:62px;
  margin:0 -14px 14px; padding:10px 16px; border-bottom:1px solid var(--line); background:rgba(17,22,27,.96); }
.file-summary strong,.file-summary small { display:block; overflow-wrap:anywhere; }
.file-summary strong { font-size:12px; } .file-summary small { margin-top:3px; color:var(--muted); font-size:10px; }
.stage-state { flex:0 0 auto; padding:5px 8px; border:1px solid var(--line); border-radius:7px; color:var(--subtle); font-size:10px; }
.empty-stage { min-height:calc(100dvh - 238px); display:flex; flex-direction:column; align-items:center; justify-content:center;
  padding:36px; text-align:center; }
.empty-stage svg { width:104px; height:82px; margin-bottom:20px; fill:none; stroke:#52616b; stroke-width:1.5; }
.empty-stage small { color:var(--accent); font-size:11px; font-weight:800; }
.empty-stage h1 { margin:10px 0 12px; color:var(--text); font-size:clamp(28px,3vw,42px); letter-spacing:-.035em; }
.empty-stage p { max-width:540px; margin:0; color:var(--muted); font-size:13px; line-height:1.8; }
.stage-footer { display:flex; justify-content:space-between; gap:12px; margin:14px -14px -10px; padding:10px 14px 0;
  border-top:1px solid var(--line); color:var(--muted); font-size:10px; }

[data-testid="stImage"] { padding:10px; border:1px solid var(--line); border-radius:10px; background:rgba(8,11,14,.88); }
[data-testid="stImage"] img { max-height:62dvh; object-fit:contain; }
[data-testid="stMetric"] { padding:12px !important; border:1px solid var(--line); border-radius:9px; background:var(--raised); }
[data-testid="stMetricLabel"] { color:var(--muted); }
[data-testid="stMetricValue"] { color:var(--text); font-variant-numeric:tabular-nums; }

.stButton > button, .stDownloadButton > button { min-height:44px; border:1px solid var(--line-strong);
  border-radius:9px; color:var(--text); background:var(--raised); font-weight:760; transition:background .14s,border-color .14s; }
.stButton > button:hover, .stDownloadButton > button:hover { border-color:#56636d; background:var(--hover); }
.stButton > button[kind="primary"] { color:var(--accent-ink); background:var(--accent); border-color:var(--accent); }
.stButton > button[kind="primary"]:hover { background:var(--accent-strong); border-color:var(--accent-strong); }
.stButton > button:focus-visible, .stDownloadButton > button:focus-visible { outline:2px solid var(--focus); outline-offset:2px; }

[data-baseweb="select"] > div, [data-baseweb="input"] > div, [data-testid="stNumberInput"] input {
  color:var(--text); background:#0d1216; border-color:var(--line-strong); }
[data-testid="stDataEditor"] { border:1px solid var(--line); border-radius:9px; overflow:hidden; }
[data-testid="stSegmentedControl"] [role="group"] { display:flex; flex-wrap:wrap; width:100%; }
[data-testid="stSegmentedControl"] button { min-width:calc(25% - 2px); min-height:42px; flex:1 0 calc(25% - 2px); padding-inline:7px; }
[data-testid="stPills"] [role="listbox"] { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:6px; width:100%; }
[data-testid="stPills"] button { width:100%; min-height:40px; justify-content:center; border:1px solid var(--line); border-radius:8px; }
[data-testid="stRadio"] [role="radiogroup"] { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:6px; width:100%; }
[data-testid="stRadio"] [role="radiogroup"] label { min-height:40px; margin:0; padding:0 6px; justify-content:center;
  gap:3px; border:1px solid var(--line); border-radius:8px; background:#12181d; font-size:10px; white-space:nowrap; }
[data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) { border-color:var(--accent); color:var(--accent-ink); background:var(--accent); }
[data-testid="stAlert"] { border-radius:9px; }
.meta-grid { display:grid; grid-template-columns:1fr 1fr; border:1px solid var(--line); border-radius:9px; overflow:hidden; }
.meta-item { min-width:0; padding:10px; border-right:1px solid var(--line); border-bottom:1px solid var(--line); }
.meta-item:nth-child(2n) { border-right:0; } .meta-item:nth-last-child(-n+2) { border-bottom:0; }
.meta-item small,.meta-item strong { display:block; overflow-wrap:anywhere; }
.meta-item small { color:var(--muted); font-size:9px; } .meta-item strong { margin-top:4px; color:var(--subtle); font-size:11px; font-weight:700; }
.privacy-note { padding:10px 11px; border:1px solid rgba(88,196,216,.18); border-radius:9px;
  color:#a9dce4; background:rgba(88,196,216,.06); font-size:10px; line-height:1.6; }

@media (max-width:900px) {
  .workbench-header { grid-template-columns:1fr auto; height:62px; padding:0 14px; }
  .session-status { display:none; } .header-runtime { font-size:0; } .header-runtime::after { content:"Python"; font-size:10px; }
  [data-testid="stSidebar"] { top:62px; height:calc(100dvh - 62px); }
  .block-container { padding:76px 10px 16px; }
  div[data-testid="stColumn"]:has(.stage-anchor), div[data-testid="stColumn"]:has(.analysis-anchor) { min-height:auto; }
  .stage-footer { flex-direction:column; }
}
@media (max-width:1100px) {
  div[data-testid="stHorizontalBlock"]:has(.stage-anchor) { flex-direction:column; }
  div[data-testid="stHorizontalBlock"]:has(.stage-anchor) > div[data-testid="stColumn"] { width:100%; flex:1 1 100%; }
  div[data-testid="stColumn"]:has(.analysis-anchor) { margin-top:10px; }
}
@media (max-width:480px) {
  .brand-copy small { display:none; } .brand-copy strong { font-size:15px; }
  .empty-stage { min-height:52dvh; padding:24px 12px; }
  .empty-stage h1 { font-size:27px; }
  [data-testid="stSegmentedControl"] button { min-width:calc(50% - 2px); flex-basis:calc(50% - 2px); }
}
@media (prefers-reduced-motion:reduce) { *,*::before,*::after { scroll-behavior:auto !important; transition:none !important; } }
</style>
"""


def _heading(title: str, badge: str | None = None, ready: bool = False) -> None:
    badge_html = ""
    if badge:
        badge_class = "panel-badge ready" if ready else "panel-badge"
        badge_html = f'<span class="{badge_class}">{escape(badge)}</span>'
    st.markdown(
        f'<div class="panel-heading"><h2>{escape(title)}</h2>{badge_html}</div>',
        unsafe_allow_html=True,
    )


def _rule() -> None:
    st.markdown('<div class="panel-rule" aria-hidden="true"></div>', unsafe_allow_html=True)


def _preset_matrix(name: str, size: int) -> list[list[float]]:
    if size in PRESETS.get(name, {}):
        return PRESETS[name][size]
    base = np.asarray(PRESETS[name][3], dtype=float)
    output = np.zeros((size, size), dtype=float)
    offset = (size - 3) // 2
    output[offset : offset + 3, offset : offset + 3] = base
    return output.tolist()


def _load_image(uploaded_file) -> tuple[Image.Image, dict[str, str]]:
    raw = uploaded_file.getvalue()
    try:
        image = Image.open(BytesIO(raw))
        image.load()
    except (UnidentifiedImageError, OSError) as error:
        raise ValueError("無法讀取影像；請使用 PNG、JPG/JPEG 或 BMP") from error
    if image.width * image.height > MAX_IMAGE_PIXELS:
        raise ValueError("影像超過 3,200 萬像素，請先縮小後再上傳")
    return image.convert("RGB"), image_metadata(image, uploaded_file.name, len(raw))


def _clear_results() -> None:
    for key in ("filtered", "metrics", "detections", "annotated"):
        st.session_state.pop(key, None)
    st.session_state.stage_view = "原始影像"


def _activate_channel() -> None:
    st.session_state.stage_view = "色彩通道"


def _channel_buttons(*, disabled: bool = False) -> None:
    """Render all seven channels as the original 4 + 3 button grid."""
    options = ["Original", "R", "G", "B", "Y", "U", "V"]
    if disabled:
        st.radio(
            "影像通道檢視模式",
            options,
            index=0,
            key="empty_channel_mode",
            disabled=True,
            label_visibility="collapsed",
        )
    else:
        st.radio(
            "影像通道檢視模式",
            options,
            key="channel_mode",
            on_change=_activate_channel,
            label_visibility="collapsed",
        )


def _render_header() -> None:
    st.markdown(
        """
        <header class="workbench-header">
          <div class="brand-lockup">
            <span class="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M4 7.5A3.5 3.5 0 0 1 7.5 4h9A3.5 3.5 0 0 1 20 7.5v9a3.5 3.5 0 0 1-3.5 3.5h-9A3.5 3.5 0 0 1 4 16.5v-9Z"/><path d="m7.5 16 3.2-3.4 2.3 2.2 1.8-1.9 2.7 3.1M15.7 8.5h.01"/></svg></span>
            <span class="brand-copy"><strong>AI 光影研究室</strong><small>Python 影像處理與視覺分析</small></span>
          </div>
          <div class="session-status"><span class="session-dot"></span>影像僅在目前工作階段處理</div>
          <div class="header-runtime">Streamlit · CPU 推論</div>
        </header>
        """,
        unsafe_allow_html=True,
    )


def _render_empty_stage() -> None:
    center, right = st.columns([2.35, 1], gap="small")
    with center:
        st.markdown('<div class="stage-anchor"></div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="stage-toolbar"><span class="file-summary"><strong>尚未載入影像</strong><small>從左側選擇檔案即可開始</small></span><span class="stage-state">準備就緒</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="empty-stage">
              <svg viewBox="0 0 120 96" aria-hidden="true"><rect x="15" y="14" width="90" height="68" rx="12"/><path d="m26 69 24-25 17 17 12-13 15 21"/><circle cx="79" cy="34" r="6"/><path d="M60 5v11M60 80v11M6 48h11m86 0h11"/></svg>
              <small>數位暗房已就緒</small><h1>把影像帶進工作台</h1>
              <p>從左側選擇 PNG、JPG/JPEG 或 BMP。色彩分析、卷積與人臉偵測會在目前的 Python 工作階段完成。</p>
            </div>
            <div class="stage-footer"><span>準備就緒</span><span>上傳影像後即可切換通道、濾波與人臉結果</span></div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown('<div class="analysis-anchor"></div>', unsafe_allow_html=True)
        _heading("色彩空間與通道", "等待影像")
        _channel_buttons(disabled=True)
        _rule()
        _heading("AI 人臉分析", "離線模型待命", ready=True)
        st.markdown('<p class="panel-copy">定位所有臉部邊界框與 6 組關鍵點，不推測身分或個人屬性。</p>', unsafe_allow_html=True)
        st.button("啟動人臉偵測", disabled=True, width="stretch")
        _rule()
        _heading("色階分布", "等待影像")
        st.info("載入影像後顯示 0–255 像素強度分布。")


def _render_compare(before: np.ndarray, after: np.ndarray) -> None:
    before_uri = base64.b64encode(encode_image(before)).decode("ascii")
    after_uri = base64.b64encode(encode_image(after)).decode("ascii")
    aspect = before.shape[1] / before.shape[0]
    height = min(560, max(280, round(710 / max(aspect, 0.3))))
    components.html(
        f"""
        <style>*{{box-sizing:border-box}}body{{margin:0;background:transparent;font-family:system-ui,sans-serif}}
        .c{{position:relative;width:100%;height:{height - 12}px;overflow:hidden;border:1px solid #27323a;border-radius:10px;background:#080b0e;touch-action:none}}
        img{{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;pointer-events:none;user-select:none}}#a{{clip-path:inset(0 0 0 50%)}}
        #l{{position:absolute;inset:0 auto 0 50%;width:2px;background:#e8a84a;transform:translateX(-1px);pointer-events:none}}
        #h{{position:absolute;left:50%;top:50%;width:42px;height:42px;display:grid;place-items:center;transform:translate(-50%,-50%);border-radius:50%;background:#e8a84a;color:#211506;font-weight:900;pointer-events:none}}
        input{{position:absolute;inset:0;width:100%;height:100%;margin:0;opacity:0;cursor:ew-resize}}span{{position:absolute;top:10px;padding:4px 8px;border-radius:999px;background:rgba(11,14,17,.8);color:#edf2f5;font-size:11px;pointer-events:none}}.b{{left:10px}}.a{{right:10px}}</style>
        <div class="c"><img src="data:image/png;base64,{before_uri}" alt="濾波前"><img id="a" src="data:image/png;base64,{after_uri}" alt="濾波後"><span class="b">濾波前</span><span class="a">濾波後</span><div id="l"></div><div id="h">↔</div><input id="s" aria-label="拖曳比較濾波前後" type="range" min="0" max="100" value="50"></div>
        <script>const s=document.getElementById('s'),a=document.getElementById('a'),l=document.getElementById('l'),h=document.getElementById('h');s.addEventListener('input',()=>{{const v=s.value;a.style.clipPath=`inset(0 0 0 ${{v}}%)`;l.style.left=v+'%';h.style.left=v+'%'}})</script>
        """,
        height=height,
        scrolling=False,
    )


def _metadata_html(metadata: dict[str, str]) -> str:
    keys = ["解析度", "像素", "格式", "檔案大小", "色彩維度", "位元深度"]
    items = "".join(
        f'<div class="meta-item"><small>{escape(key)}</small><strong>{escape(metadata.get(key, "—"))}</strong></div>'
        for key in keys
    )
    return f'<div class="meta-grid">{items}</div>'


def run_workbench() -> None:
    st.set_page_config(page_title="AI 光影研究室 · Python", page_icon=None, layout="wide", initial_sidebar_state="expanded")
    st.markdown(APP_CSS, unsafe_allow_html=True)
    _render_header()

    with st.sidebar:
        _heading("來源影像")
        uploaded = st.file_uploader("拖放或選擇影像", type=["png", "jpg", "jpeg", "bmp"], help="PNG、JPG/JPEG、BMP · 最大 32 MP")
        st.caption("PNG、JPG/JPEG、BMP · 最大 32 MP")
        if st.button("清除處理結果", width="stretch"):
            _clear_results()

    if uploaded is None:
        _render_empty_stage()
        st.stop()

    try:
        original_image, metadata = _load_image(uploaded)
    except ValueError as error:
        st.error(str(error))
        st.stop()

    file_token = f"{uploaded.name}:{uploaded.size}"
    if st.session_state.get("file_token") != file_token:
        st.session_state.file_token = file_token
        _clear_results()
        st.session_state.channel_mode = "Original"
    st.session_state.setdefault("channel_mode", "Original")
    st.session_state.setdefault("stage_view", "原始影像")
    rgb = ensure_rgb(original_image)

    with st.sidebar:
        _rule()
        _heading("自訂卷積濾波", "已套用" if "filtered" in st.session_state else "尚未套用")
        st.markdown('<p class="panel-copy">輸入 3×3 或 5×5 權重；邊界採 clamp-to-edge 延伸。</p>', unsafe_allow_html=True)
        size = st.segmented_control("矩陣尺寸", [3, 5], default=3, format_func=lambda value: f"{value} × {value}", width="stretch")
        preset = st.selectbox("範例", list(PRESETS))
        matrix = st.data_editor(pd.DataFrame(_preset_matrix(preset, size)), key=f"kernel:{size}:{preset}", hide_index=True, width="stretch", num_rows="fixed")
        normalization = st.selectbox("正規化", ["權重總和", "不正規化", "自訂除數"])
        custom_divisor = st.number_input("自訂除數", value=1.0, disabled=normalization != "自訂除數")
        bias = st.number_input("偏移量", value=0.0)
        if st.button("套用卷積濾波", type="primary", width="stretch"):
            try:
                spec = validate_kernel(matrix.to_numpy(), normalization, custom_divisor, bias)
                with st.spinner("正在計算濾波與 PSNR…"):
                    filtered = apply_convolution(rgb, spec)
                    score, mse = psnr(rgb, filtered)
                st.session_state.filtered = filtered
                st.session_state.metrics = (score, mse)
                st.session_state.stage_view = "卷積結果"
            except ValueError as error:
                st.error(str(error))
        if "metrics" in st.session_state:
            score, mse = st.session_state.metrics
            metric_a, metric_b = st.columns(2)
            metric_a.metric("PSNR", "∞ dB" if np.isinf(score) else f"{score:.2f} dB")
            metric_b.metric("MSE", f"{mse:.3f}")

    center, right = st.columns([2.35, 1], gap="small")
    with center:
        st.markdown('<div class="stage-anchor"></div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="stage-toolbar"><span class="file-summary"><strong>{escape(uploaded.name)}</strong><small>{escape(metadata["解析度"])} · {escape(metadata["檔案大小"])}</small></span><span class="stage-state">工作台檢視</span></div>',
            unsafe_allow_html=True,
        )
        available_views = ["原始影像", "色彩通道"]
        if "filtered" in st.session_state:
            available_views.append("卷積結果")
        if "annotated" in st.session_state:
            available_views.append("人臉結果")
        if st.session_state.stage_view not in available_views:
            st.session_state.stage_view = "原始影像"
        stage_view = st.segmented_control("工作區檢視", available_views, key="stage_view", width="stretch", label_visibility="collapsed")
        if stage_view == "色彩通道":
            mode = st.session_state.channel_mode
            st.image(channel_plane(rgb, mode), caption=f"{mode} 通道檢視", width="stretch", clamp=True)
        elif stage_view == "卷積結果" and "filtered" in st.session_state:
            _render_compare(rgb, st.session_state.filtered)
        elif stage_view == "人臉結果" and "annotated" in st.session_state:
            st.image(st.session_state.annotated, caption="人臉邊界框與關鍵點", width="stretch")
        else:
            st.image(original_image, caption="原始影像", width="stretch")
        st.markdown(
            '<div class="stage-footer"><span>影像已就緒</span><span>通道、卷積與人臉結果可由上方切換</span></div>',
            unsafe_allow_html=True,
        )

    with right:
        st.markdown('<div class="analysis-anchor"></div>', unsafe_allow_html=True)
        _heading("色彩空間與通道", st.session_state.channel_mode)
        _channel_buttons()
        st.markdown('<p class="panel-copy">切換 RGB 或 BT.601 YUV 分量；中央畫布與直方圖同步更新。</p>', unsafe_allow_html=True)
        _rule()
        detections = st.session_state.get("detections")
        _heading("AI 人臉分析", "分析完成" if detections is not None else "離線模型待命", ready=True)
        st.markdown('<p class="panel-copy">定位所有臉部邊界框與 6 組關鍵點，不推測身分、年齡、性別或情緒。</p>', unsafe_allow_html=True)
        if st.button("啟動人臉偵測", type="primary", width="stretch"):
            try:
                with st.spinner("正在載入模型並分析影像…"):
                    detected = detect_faces(rgb, FACE_MODEL)
                    st.session_state.annotated = annotate_faces(rgb, detected)
                st.session_state.detections = detected
                st.session_state.stage_view = "人臉結果"
                st.rerun()
            except (RuntimeError, ValueError, ImportError, OSError) as error:
                st.error(f"人臉偵測失敗：{error}。請重新啟動分析；若持續發生，請查看部署 Log。")
        if detections is not None:
            average = np.mean([item["confidence"] for item in detections]) if detections else 0.0
            count_metric, confidence_metric = st.columns(2)
            count_metric.metric("偵測人臉", len(detections))
            confidence_metric.metric("平均信心", "—" if not detections else f"{average:.1%}")
            if not detections:
                st.warning("未偵測到臉部；請改用正面、清楚且光線充足的照片。")
        st.markdown('<div class="privacy-note">模型在目前的 Python 工作階段執行；影像不會送往第三方辨識服務。</div>', unsafe_allow_html=True)
        _rule()
        _heading("色階分布", st.session_state.channel_mode)
        bins = histogram(rgb, st.session_state.channel_mode)
        chart = pd.DataFrame({"像素強度": np.arange(256), "像素數量": bins}).set_index("像素強度")
        st.bar_chart(chart, y="像素數量", height=220)
        st.caption(f"0–255 · 完整統計 {int(bins.sum()):,} 個像素")
        st.markdown(_metadata_html(metadata), unsafe_allow_html=True)
        _rule()
        _heading("匯出設定")
        export_image = st.session_state.get("filtered", rgb)
        export_suffix = "filtered" if "filtered" in st.session_state else "original"
        st.download_button(
            "下載處理後影像",
            data=encode_image(export_image),
            file_name=f"{Path(uploaded.name).stem}-{export_suffix}.png",
            mime="image/png",
            width="stretch",
        )

