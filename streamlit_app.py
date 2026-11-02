"""AI Image Studio - Python/Streamlit implementation."""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, UnidentifiedImageError

from python_image_studio.core import (
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
from python_image_studio.face import annotate_faces, detect_faces

ROOT = Path(__file__).resolve().parent
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


def preset_matrix(name: str, size: int) -> list[list[float]]:
    if size in PRESETS.get(name, {}):
        return PRESETS[name][size]
    base = np.asarray(PRESETS[name][3], dtype=float)
    output = np.zeros((size, size), dtype=float)
    offset = (size - 3) // 2
    output[offset : offset + 3, offset : offset + 3] = base
    return output.tolist()


def load_uploaded_image(uploaded_file) -> tuple[Image.Image, dict[str, str]]:
    raw = uploaded_file.getvalue()
    try:
        image = Image.open(BytesIO(raw))
        image.load()
    except (UnidentifiedImageError, OSError) as error:
        raise ValueError("無法讀取影像；請使用 PNG、JPG/JPEG 或 BMP") from error
    if image.width * image.height > MAX_IMAGE_PIXELS:
        raise ValueError("影像超過 3,200 萬像素，請先縮小後再上傳")
    metadata = image_metadata(image, uploaded_file.name, len(raw))
    return image.convert("RGB"), metadata


def metadata_table(metadata: dict[str, str]) -> pd.DataFrame:
    return pd.DataFrame({"項目": list(metadata.keys()), "內容": list(metadata.values())})


def render_before_after(before: np.ndarray, after: np.ndarray) -> None:
    """Render a pointer/touch-draggable before/after comparison."""
    before_uri = base64.b64encode(encode_image(before)).decode("ascii")
    after_uri = base64.b64encode(encode_image(after)).decode("ascii")
    aspect = before.shape[1] / before.shape[0]
    height = min(560, max(260, round(720 / max(aspect, 0.25))))
    components.html(
        f"""
        <style>
          * {{ box-sizing:border-box; }} body {{ margin:0; background:transparent; font-family:system-ui,sans-serif; }}
          .compare {{ position:relative; width:100%; height:{height - 14}px; overflow:hidden; border-radius:12px;
            background:#0b1014; border:1px solid #34424d; touch-action:none; }}
          .compare img {{ position:absolute; inset:0; width:100%; height:100%; object-fit:contain; user-select:none; pointer-events:none; }}
          #after {{ clip-path:inset(0 0 0 50%); }}
          #line {{ position:absolute; top:0; bottom:0; left:50%; width:2px; background:#e8a84a; transform:translateX(-1px);
            box-shadow:0 0 0 1px rgba(0,0,0,.25); pointer-events:none; }}
          #handle {{ position:absolute; left:50%; top:50%; width:42px; height:42px; transform:translate(-50%,-50%);
            border-radius:50%; background:#e8a84a; color:#101820; display:grid; place-items:center; font-weight:800;
            box-shadow:0 4px 16px rgba(0,0,0,.35); pointer-events:none; }}
          input {{ position:absolute; inset:0; width:100%; height:100%; opacity:0; cursor:ew-resize; margin:0; }}
          .label {{ position:absolute; top:10px; padding:4px 8px; border-radius:999px; color:#edf1f4;
            background:rgba(13,18,23,.78); font-size:12px; pointer-events:none; }}
          .before {{ left:10px; }} .after {{ right:10px; }}
        </style>
        <div class="compare">
          <img src="data:image/png;base64,{before_uri}" alt="濾波前">
          <img id="after" src="data:image/png;base64,{after_uri}" alt="濾波後">
          <span class="label before">濾波前</span><span class="label after">濾波後</span>
          <div id="line"></div><div id="handle">↔</div>
          <input id="slider" aria-label="拖曳比較濾波前後" type="range" min="0" max="100" value="50">
        </div>
        <script>
          const slider=document.getElementById('slider'), after=document.getElementById('after');
          const line=document.getElementById('line'), handle=document.getElementById('handle');
          slider.addEventListener('input', () => {{
            const value=slider.value; after.style.clipPath=`inset(0 0 0 ${{value}}%)`;
            line.style.left=value+'%'; handle.style.left=value+'%';
          }});
        </script>
        """,
        height=height,
        scrolling=False,
    )


st.set_page_config(page_title="AI 光影研究室 · Python", page_icon=None, layout="wide")
st.markdown(
    """
    <style>
    :root { --accent:#e8a84a; --cyan:#52c7d9; --ink:#101820; }
    .stApp { background: #0d1217; color: #edf1f4; }
    [data-testid="stHeader"] { background: rgba(13,18,23,.88); }
    .hero { padding: 1.1rem 1.25rem; border: 1px solid #29343d; border-radius: 14px;
      background: linear-gradient(135deg,#151d24,#10171c); margin-bottom: 1rem; }
    .hero h1 { margin:0; font-size:2rem; letter-spacing:-.02em; }
    .hero p { margin:.35rem 0 0; color:#9cabB5; }
    .privacy { display:inline-block; margin-top:.75rem; padding:.3rem .6rem; border-radius:999px;
      color:#b9edf3; background:#173039; font-size:.78rem; }
    div[data-testid="stMetric"] { border:1px solid #29343d; border-radius:12px; padding:.7rem; background:#111920; }
    .stButton > button[kind="primary"] { background:#e8a84a; color:#111820; border:0; font-weight:700; }
    .stTabs [data-baseweb="tab-list"] { gap:.35rem; }
    .stTabs [data-baseweb="tab"] { min-height:44px; border-radius:8px; }
    </style>
    <div class="hero"><h1>AI 光影研究室 · Python</h1>
    <p>影像解析、RGB/YUV、精確直方圖、自訂卷積、PSNR 與離線人臉偵測。</p>
    <span class="privacy">影像只在目前的 Python 工作階段處理</span></div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("來源影像")
    uploaded = st.file_uploader("選擇 PNG、JPG/JPEG 或 BMP", type=["png", "jpg", "jpeg", "bmp"])
    st.caption("最大 32 MP；卷積上限 12 MP")
    if st.button("清除處理結果", width="stretch"):
        st.session_state.pop("filtered", None)
        st.session_state.pop("metrics", None)
        st.session_state.pop("detections", None)
        st.session_state.pop("annotated", None)

if uploaded is None:
    st.info("請從左側上傳影像以開始分析。")
    st.stop()

try:
    original_image, metadata = load_uploaded_image(uploaded)
except ValueError as error:
    st.error(str(error))
    st.stop()

file_token = f"{uploaded.name}:{uploaded.size}"
if st.session_state.get("file_token") != file_token:
    st.session_state.file_token = file_token
    for key in ("filtered", "metrics", "detections", "annotated"):
        st.session_state.pop(key, None)

rgb = ensure_rgb(original_image)
tab_info, tab_channels, tab_kernel, tab_face = st.tabs(
    ["01 基礎解析", "02 色彩與直方圖", "03 卷積與 PSNR", "04 人臉偵測"]
)

with tab_info:
    left, right = st.columns([1.45, 1])
    with left:
        st.image(original_image, caption=uploaded.name, width="stretch")
    with right:
        st.subheader("影像中繼資訊")
        st.dataframe(metadata_table(metadata), hide_index=True, width="stretch")
        st.caption("支援 PNG、JPEG 與 BMP；解碼後統一以 RGB 8-bit 進行演算法運算。")

with tab_channels:
    mode = st.radio("檢視模式", ["Original", "R", "G", "B", "Y", "U", "V"], horizontal=True)
    view = channel_plane(rgb, mode)
    bins = histogram(rgb, mode)
    view_column, histogram_column = st.columns([1.2, 1])
    with view_column:
        st.image(view, caption=f"{mode} 通道", width="stretch", clamp=True)
    with histogram_column:
        st.subheader("同步直方圖")
        chart = pd.DataFrame({"像素強度": np.arange(256), "像素數量": bins}).set_index("像素強度")
        st.bar_chart(chart, y="像素數量", height=360)
        st.caption(f"橫軸 0–255；完整統計 {int(bins.sum()):,} 個像素。")

with tab_kernel:
    controls, editor = st.columns([.8, 1.2])
    with controls:
        size = st.radio("矩陣尺寸", [3, 5], horizontal=True, format_func=lambda value: f"{value} × {value}")
        preset = st.selectbox("範例", list(PRESETS))
        normalization = st.selectbox("正規化", ["權重總和", "不正規化", "自訂除數"])
        custom_divisor = st.number_input("自訂除數", value=1.0, disabled=normalization != "自訂除數")
        bias = st.number_input("偏移量", value=0.0)
    with editor:
        initial = pd.DataFrame(preset_matrix(preset, size))
        matrix = st.data_editor(
            initial,
            key=f"kernel:{size}:{preset}",
            hide_index=True,
            width="stretch",
            num_rows="fixed",
        )
    if st.button("套用卷積濾波", type="primary", width="stretch"):
        try:
            spec = validate_kernel(matrix.to_numpy(), normalization, custom_divisor, bias)
            with st.spinner("正在計算卷積與 PSNR…"):
                filtered = apply_convolution(rgb, spec)
                score, mse = psnr(rgb, filtered)
            st.session_state.filtered = filtered
            st.session_state.metrics = (score, mse)
        except ValueError as error:
            st.error(str(error))
    if "filtered" in st.session_state:
        score, mse = st.session_state.metrics
        metric_a, metric_b = st.columns(2)
        metric_a.metric("PSNR", "∞ dB" if np.isinf(score) else f"{score:.2f} dB")
        metric_b.metric("MSE", f"{mse:.4f}")
        st.subheader("拖曳比較")
        st.caption("拖曳影像中央分隔線，同一位置比較濾波前後結果。")
        render_before_after(rgb, st.session_state.filtered)
        st.download_button(
            "下載濾波結果 PNG",
            data=encode_image(st.session_state.filtered),
            file_name=f"{Path(uploaded.name).stem}-filtered.png",
            mime="image/png",
            width="stretch",
        )

with tab_face:
    st.caption("MediaPipe BlazeFace 模型由專案本機檔案載入；回傳所有臉部邊界框、關鍵點與信心分數。")
    if st.button("啟動人臉偵測", type="primary", width="stretch"):
        try:
            with st.spinner("正在載入模型並分析影像…"):
                detections = detect_faces(rgb, FACE_MODEL)
                annotated = annotate_faces(rgb, detections)
            st.session_state.detections = detections
            st.session_state.annotated = annotated
        except (RuntimeError, ValueError, ImportError, OSError) as error:
            st.error(f"人臉偵測失敗：{error}")
    if "detections" in st.session_state:
        detections = st.session_state.detections
        average = np.mean([item["confidence"] for item in detections]) if detections else 0.0
        count_metric, confidence_metric = st.columns(2)
        count_metric.metric("偵測人臉", len(detections))
        confidence_metric.metric("平均信心", "—" if not detections else f"{average:.1%}")
        st.image(st.session_state.annotated, caption="人臉邊界框與關鍵點", width="stretch")
        if detections:
            result_rows = [
                {
                    "臉部": index,
                    "信心": f"{item['confidence']:.1%}",
                    "邊界框": f"x={item['x']}, y={item['y']}, {item['width']}×{item['height']} px",
                    "關鍵點": len(item["keypoints"]),
                }
                for index, item in enumerate(detections, 1)
            ]
            st.dataframe(result_rows, hide_index=True, width="stretch")
        else:
            st.warning("未偵測到臉部；請嘗試正面、清楚且光線充足的影像。")
