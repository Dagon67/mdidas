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


def preprocess_pipeline(img_bytes, apply_white_balance=True, apply_exposure=True):
    """
    Pipeline de pré-processamento.
    Retorna dict com 'bgr', 'lab', 'hsv', 'bgr_norm' (normalizado).
    """
    img = load_image(img_bytes)
    if img is None:
        return None
    if apply_white_balance:
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
