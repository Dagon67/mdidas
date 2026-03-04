"""
Pré-processamento: balanço de branco, normalização de exposição, conversão LAB/HSV.
"""
import io
import numpy as np
from PIL import Image
import cv2
from skimage import exposure


def load_image(bytes_io):
    """Carrega imagem a partir de bytes (BytesIO ou bytes)."""
    if hasattr(bytes_io, "getvalue"):
        data = bytes_io.getvalue()
    elif hasattr(bytes_io, "read"):
        data = bytes_io.read()
    else:
        data = bytes_io
    if not data or len(data) == 0:
        return None
    data = bytes(data)
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        pil = Image.open(io.BytesIO(data))
        img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    return img


def normalize_exposure(img_bgr):
    """Normalização de exposição (CLAHE em L ou equalize)."""
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_norm = clahe.apply(l)
    lab_norm = cv2.merge([l_norm, a, b])
    return cv2.cvtColor(lab_norm, cv2.COLOR_LAB2BGR)


def white_balance_simple(img_bgr):
    """Balanço de branco simples (Gray World assumption) quando não há referência."""
    result = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    avg_a = np.mean(result[:, :, 1])
    avg_b = np.mean(result[:, :, 2])
    result[:, :, 1] = result[:, :, 1] - (avg_a - 128)
    result[:, :, 2] = result[:, :, 2] - (avg_b - 128)
    return cv2.cvtColor(result, cv2.COLOR_LAB2BGR)


def _detect_white_mask(lab_uint8, l_min=240, chroma_max=15):
    """Máscara de pixels brancos: L alto (OpenCV 0-255) e croma baixo em a,b."""
    l_ch = lab_uint8[:, :, 0]
    a_ch = lab_uint8[:, :, 1].astype(np.float32) - 128
    b_ch = lab_uint8[:, :, 2].astype(np.float32) - 128
    chroma = np.sqrt(a_ch**2 + b_ch**2)
    mask = (l_ch >= l_min) & (chroma <= chroma_max)
    return mask


def get_white_balance_correction(img_bgr, white_l_min=240, white_chroma_max=18):
    """
    Obtém a correção de branco (delta_a, delta_b) a partir de uma imagem que contém
    papel branco. Retorna (delta_a, delta_b) em escala OpenCV LAB (0-255).
    Use apply_white_balance_correction(img, da, db) para aplicar a outra imagem.
    Se não houver região branca suficiente, retorna (0, 0).
    """
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    white_mask = _detect_white_mask(lab, l_min=white_l_min, chroma_max=white_chroma_max)
    n_white = np.sum(white_mask)
    if n_white < 100:
        return (0.0, 0.0)
    a_vals = lab[:, :, 1][white_mask]
    b_vals = lab[:, :, 2][white_mask]
    ref_a = float(np.median(a_vals))
    ref_b = float(np.median(b_vals))
    delta_a = ref_a - 128
    delta_b = ref_b - 128
    return (delta_a, delta_b)


def apply_white_balance_correction(img_bgr, delta_a, delta_b):
    """Aplica correção de branco (delta_a, delta_b em escala OpenCV) à imagem."""
    if abs(delta_a) < 0.5 and abs(delta_b) < 0.5:
        return img_bgr
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    lab[:, :, 1] = np.clip(lab[:, :, 1].astype(np.float32) - delta_a, 0, 255).astype(np.uint8)
    lab[:, :, 2] = np.clip(lab[:, :, 2].astype(np.float32) - delta_b, 0, 255).astype(np.uint8)
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def white_balance_by_reference(img_bgr, white_l_min=240, white_chroma_max=18):
    """
    Balanço de branco usando região de papel branco na imagem.
    Detecta pixels com L alto e croma baixo (neutros), calcula o desvio médio a,b
    e corrige a imagem para que essa região fique neutra (a,b=128 em OpenCV).
    """
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    white_mask = _detect_white_mask(lab, l_min=white_l_min, chroma_max=white_chroma_max)
    n_white = np.sum(white_mask)
    if n_white < 100:
        return white_balance_simple(img_bgr)
    a_vals = lab[:, :, 1][white_mask]
    b_vals = lab[:, :, 2][white_mask]
    ref_a = float(np.median(a_vals))
    ref_b = float(np.median(b_vals))
    lab[:, :, 1] = np.clip(lab[:, :, 1] - (ref_a - 128), 0, 255).astype(np.uint8)
    lab[:, :, 2] = np.clip(lab[:, :, 2] - (ref_b - 128), 0, 255).astype(np.uint8)
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def to_lab(img_bgr):
    """Converte BGR para LAB (L em [0,100], a,b ~[-128,127])."""
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l_scale = l.astype(np.float32) * (100 / 255)
    a_scale = a.astype(np.float32) - 128
    b_scale = b.astype(np.float32) - 128
    return np.stack([l_scale, a_scale, b_scale], axis=-1)


def to_hsv(img_bgr):
    """Converte BGR para HSV (H 0-180 OpenCV, S,V 0-255)."""
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)


def preprocess_pipeline(img_bytes, apply_white_balance=True, apply_exposure=True, use_white_reference=True, wb_correction=None):
    """
    Pipeline de pré-processamento.
    wb_correction: opcional (delta_a, delta_b) da imagem "rosto com papel"; quando dado, aplica
    essa correção em vez de detectar branco na própria imagem.
    Retorna dict com 'bgr', 'lab', 'hsv', 'bgr_norm' (normalizado).
    """
    img = load_image(img_bytes)
    if img is None:
        return None
    if apply_white_balance:
        if wb_correction is not None and len(wb_correction) >= 2:
            img = apply_white_balance_correction(img, wb_correction[0], wb_correction[1])
        elif use_white_reference:
            img = white_balance_by_reference(img)
        else:
            img = white_balance_simple(img)
    if apply_exposure:
        img = normalize_exposure(img)
    lab = to_lab(img)
    hsv = to_hsv(img)
    return {
        "bgr": img,
        "lab": lab,
        "hsv": hsv,
        "shape": img.shape,
    }
