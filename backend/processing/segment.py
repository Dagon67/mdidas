"""
Segmentação: rosto, pele, cabelo usando MediaPipe + OpenCV.
"""
import numpy as np
import cv2


def segment_face_mediapipe(img_bgr, mp_face=None):
    """
    Retorna máscara do rosto (região facial) usando MediaPipe Face Mesh.
    Se mp_face for None, usa região central como fallback (retângulo).
    """
    try:
        import mediapipe as mp
        if mp_face is None:
            mp_face = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
            )
        rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        h, w = img_bgr.shape[:2]
        results = mp_face.process(rgb)
        mask = np.zeros((h, w), dtype=np.uint8)
        if results.multi_face_landmarks:
            pts = []
            for lm in results.multi_face_landmarks[0].landmark:
                x, y = int(lm.x * w), int(lm.y * h)
                pts.append([x, y])
            pts = np.array(pts, dtype=np.int32)
            cv2.fillConvexPoly(mask, pts, 255)
        return mask
    except Exception:
        h, w = img_bgr.shape[:2]
        # Fallback: centro 60% da imagem (assume rosto no centro)
        x1, x2 = int(w * 0.2), int(w * 0.8)
        y1, y2 = int(h * 0.2), int(h * 0.75)
        mask = np.zeros((h, w), dtype=np.uint8)
        mask[y1:y2, x1:x2] = 255
        return mask


def segment_skin_region(img_bgr, face_mask=None):
    """
    Região de pele: dentro do rosto, excluindo cores muito escuras/claras (olhos, sombras).
    Usa range HSV para pele.
    """
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    if face_mask is None:
        face_mask = np.ones((img_bgr.shape[0], img_bgr.shape[1]), dtype=np.uint8) * 255
    # Range típico para pele em HSV (OpenCV: H 0-180)
    lower = np.array([0, 20, 70], dtype=np.uint8)
    upper = np.array([25, 180, 255], dtype=np.uint8)
    mask_hsv = cv2.inRange(hsv, lower, upper)
    # Também H 160-180 (tom vermelho)
    lower2 = np.array([160, 20, 70], dtype=np.uint8)
    upper2 = np.array([180, 180, 255], dtype=np.uint8)
    mask_hsv2 = cv2.inRange(hsv, lower2, upper2)
    skin_mask = cv2.bitwise_or(mask_hsv, mask_hsv2)
    skin_mask = cv2.bitwise_and(skin_mask, face_mask)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
    skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)
    return skin_mask


def segment_hair_region(img_bgr, face_mask=None):
    """
    Região de cabelo: geralmente mais escura que a pele, bordas superiores/laterais.
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    if face_mask is None:
        face_mask = np.ones((h, w), dtype=np.uint8) * 255
    # Cabelo tende a estar na metade superior e mais escuro
    _, dark_mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    top_region = np.zeros((h, w), dtype=np.uint8)
    top_region[: int(h * 0.6), :] = 255
    hair_mask = cv2.bitwise_and(dark_mask, top_region)
    hair_mask = cv2.bitwise_and(hair_mask, face_mask)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    hair_mask = cv2.morphologyEx(hair_mask, cv2.MORPH_CLOSE, kernel)
    return hair_mask


def get_region_pixels(lab, mask):
    """Retorna pixels LAB onde mask > 0 (em formato Nx3)."""
    h, w = lab.shape[:2]
    if mask.shape[:2] != (h, w):
        mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
    pts = np.where(mask.flatten() > 0)[0]
    return lab.reshape(-1, 3)[pts]
