"""Pure NumPy/Pillow image-processing algorithms used by the Streamlit UI."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Literal

import numpy as np
from PIL import Image

ChannelMode = Literal["Original", "R", "G", "B", "Y", "U", "V"]
NormalizationMode = Literal["權重總和", "不正規化", "自訂除數"]

MAX_IMAGE_PIXELS = 32_000_000
MAX_CONVOLUTION_PIXELS = 12_000_000


@dataclass(frozen=True)
class KernelSpec:
    weights: np.ndarray
    divisor: float
    bias: float


def ensure_rgb(image: Image.Image | np.ndarray) -> np.ndarray:
    if isinstance(image, Image.Image):
        array = np.asarray(image.convert("RGB"), dtype=np.uint8)
    else:
        array = np.asarray(image)
        if array.ndim == 2:
            array = np.repeat(array[..., None], 3, axis=2)
        if array.ndim != 3 or array.shape[2] < 3:
            raise ValueError("影像必須包含至少 3 個色彩通道")
        array = np.asarray(array[..., :3], dtype=np.uint8)
    return np.ascontiguousarray(array)


def image_metadata(image: Image.Image, filename: str, file_size: int) -> dict[str, str]:
    width, height = image.size
    channels = len(image.getbands())
    image_format = (image.format or filename.rsplit(".", 1)[-1]).upper()
    return {
        "檔名": filename,
        "解析度": f"{width:,} × {height:,} px",
        "像素": f"{width * height / 1_000_000:.2f} MP",
        "格式": "JPEG" if image_format == "JPG" else image_format,
        "檔案大小": format_bytes(file_size),
        "色彩維度": f"{image.mode} · {channels} 通道",
        "位元深度": "8 bit / channel",
    }


def format_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def channel_plane(image: Image.Image | np.ndarray, mode: ChannelMode) -> np.ndarray:
    rgb = ensure_rgb(image).astype(np.float32)
    red, green, blue = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    if mode == "Original":
        return ensure_rgb(image)
    if mode == "R":
        plane = red
    elif mode == "G":
        plane = green
    elif mode == "B":
        plane = blue
    elif mode == "Y":
        plane = 0.299 * red + 0.587 * green + 0.114 * blue
    elif mode == "U":
        plane = -0.168736 * red - 0.331264 * green + 0.5 * blue + 128
    elif mode == "V":
        plane = 0.5 * red - 0.418688 * green - 0.081312 * blue + 128
    else:
        raise ValueError(f"不支援的色彩通道：{mode}")
    return np.clip(np.rint(plane), 0, 255).astype(np.uint8)


def histogram(image: Image.Image | np.ndarray, mode: ChannelMode) -> np.ndarray:
    rgb = ensure_rgb(image)
    if mode == "Original":
        values = np.rint(
            0.2126 * rgb[..., 0].astype(np.float32)
            + 0.7152 * rgb[..., 1].astype(np.float32)
            + 0.0722 * rgb[..., 2].astype(np.float32)
        ).astype(np.uint8)
    else:
        values = channel_plane(rgb, mode)
    return np.bincount(values.reshape(-1), minlength=256).astype(np.int64)


def validate_kernel(
    matrix: np.ndarray | list[list[float]],
    normalization: NormalizationMode,
    custom_divisor: float = 1.0,
    bias: float = 0.0,
) -> KernelSpec:
    weights = np.asarray(matrix, dtype=np.float64)
    if weights.shape not in {(3, 3), (5, 5)}:
        raise ValueError("卷積核必須是 3×3 或 5×5 方陣")
    if not np.isfinite(weights).all():
        raise ValueError("卷積核必須全部是有限數值")
    if normalization == "權重總和":
        divisor = float(weights.sum())
    elif normalization == "不正規化":
        divisor = 1.0
    elif normalization == "自訂除數":
        divisor = float(custom_divisor)
    else:
        raise ValueError("不支援的正規化模式")
    if not np.isfinite(divisor) or abs(divisor) < 1e-12:
        raise ValueError("正規化除數不可為 0；零和卷積核請改用不正規化或非零自訂除數")
    normalized_bias = float(bias)
    if not np.isfinite(normalized_bias):
        raise ValueError("偏移量必須是有限數值")
    return KernelSpec(weights=weights, divisor=divisor, bias=normalized_bias)


def apply_convolution(image: Image.Image | np.ndarray, kernel: KernelSpec) -> np.ndarray:
    rgb = ensure_rgb(image)
    height, width = rgb.shape[:2]
    if height * width > MAX_CONVOLUTION_PIXELS:
        raise ValueError("卷積上限為 1,200 萬像素；請先縮小影像")
    radius = kernel.weights.shape[0] // 2
    # float32 keeps a 12 MP convolution within a practical memory budget while
    # still providing more than enough precision for an 8-bit output image.
    source = rgb.astype(np.float32)
    padded = np.pad(source, ((radius, radius), (radius, radius), (0, 0)), mode="edge")
    output = np.zeros_like(source)
    for row in range(kernel.weights.shape[0]):
        for column in range(kernel.weights.shape[1]):
            weight = kernel.weights[row, column]
            if weight == 0:
                continue
            output += weight * padded[row : row + height, column : column + width]
    output = output / kernel.divisor + kernel.bias
    return np.clip(np.rint(output), 0, 255).astype(np.uint8)


def psnr(reference: Image.Image | np.ndarray, result: Image.Image | np.ndarray) -> tuple[float, float]:
    left = ensure_rgb(reference).astype(np.float32)
    right = ensure_rgb(result).astype(np.float32)
    if left.shape != right.shape:
        raise ValueError("PSNR 比較影像的尺寸必須相同")
    mse = float(np.mean(np.square(left - right)))
    score = float("inf") if mse == 0 else float(10 * np.log10((255.0**2) / mse))
    return score, mse


def encode_image(image: Image.Image | np.ndarray, image_format: str = "PNG", quality: int = 92) -> bytes:
    pil_image = image if isinstance(image, Image.Image) else Image.fromarray(ensure_rgb(image))
    buffer = BytesIO()
    save_options = {"quality": int(quality)} if image_format.upper() in {"JPEG", "WEBP"} else {}
    if image_format.upper() == "JPEG":
        pil_image = pil_image.convert("RGB")
    pil_image.save(buffer, format=image_format.upper(), **save_options)
    return buffer.getvalue()
