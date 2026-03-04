"""
Script de calibração: roda o pipeline nas imagens de referencia_cor e compara
com as cores dos .txt (extraídas por ferramenta profissional). Calcula offset
LAB para aplicar no pipeline e deixar resultados condizentes.
Execute na raiz do projeto: python -m backend.scripts.calibrate
"""
import io
import os
import re
import sys
import json

# raiz do repositório (pasta que contém backend/ e referencia_cor/)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REF_DIR = os.path.join(ROOT, "referencia_cor")
sys.path.insert(0, os.path.join(ROOT, "backend"))

from processing.preprocess import preprocess_pipeline
from processing.segment import segment_face_mediapipe, segment_skin_region, segment_hair_region, get_region_pixels
from processing.extract import extract_region_features
from processing.recommend import hex_to_lab, lab_to_hex


def parse_hex_from_txt(txt_path, exclude_white=True):
    """Extrai listagem de cores HEX de um arquivo .txt no formato --name: #RRGGBBff; ou $name: #RRGGBBff;"""
    if not os.path.isfile(txt_path):
        return []
    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read()
    # Match #RRGGBB ou #RRGGBBff
    hexes = re.findall(r"#([0-9A-Fa-f]{6})(?:[0-9A-Fa-f]{2})?\b", text)
    out = []
    for h in hexes:
        hex_str = "#" + h
        if exclude_white:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            if r >= 250 and g >= 250 and b >= 250:
                continue
            if r <= 5 and g <= 5 and b <= 5:
                continue
        out.append(hex_str)
    return list(dict.fromkeys(out))


def run_pipeline_on_image(img_path, region="skin", face_mask=None):
    """Roda preprocess + segment + extract e retorna mean_lab (L 0-100, a,b float) ou None."""
    if not os.path.isfile(img_path):
        return None
    with open(img_path, "rb") as f:
        data = f.read()
    pre = preprocess_pipeline(io.BytesIO(data))
    if not pre:
        return None
    bgr, lab = pre["bgr"], pre["lab"]
    if region == "skin":
        if face_mask is None:
            face_mask = segment_face_mediapipe(bgr)
        skin_mask = segment_skin_region(bgr, face_mask)
        pixels = get_region_pixels(lab, skin_mask)
    else:
        hair_mask = segment_hair_region(bgr, None)
        pixels = get_region_pixels(lab, hair_mask)
    feat = extract_region_features(pixels)
    if not feat or not feat.get("mean_lab"):
        return None
    return feat["mean_lab"]


def main():
    # (imagem, arquivo_txt, região)
    cases = [
        (os.path.join(REF_DIR, "rosto_papel.jpg"), os.path.join(REF_DIR, "rosto_papel.txt"), "skin"),
        (os.path.join(REF_DIR, "rosto.png"), os.path.join(REF_DIR, "rosto.txt"), "skin"),
        (os.path.join(REF_DIR, "interno_braco.png"), os.path.join(REF_DIR, "interno_braco.txt"), "skin"),
        (os.path.join(REF_DIR, "externo_braco.png"), os.path.join(REF_DIR, "externo_braco.txt"), "skin"),
    ]
    offsets_l, offsets_a, offsets_b = [], [], []
    results = []

    for img_path, txt_path, region in cases:
        our_lab = run_pipeline_on_image(img_path, region)
        ref_hexes = parse_hex_from_txt(txt_path)
        if not ref_hexes:
            print("Skip (no ref hex):", txt_path)
            continue
        ref_labs = [hex_to_lab(h) for h in ref_hexes]
        ref_L = sum(l[0] for l in ref_labs) / len(ref_labs)
        ref_a = sum(l[1] for l in ref_labs) / len(ref_labs)
        ref_b = sum(l[2] for l in ref_labs) / len(ref_labs)
        if our_lab is None:
            print("Skip (pipeline failed):", img_path)
            continue
        oL, oa, ob = our_lab[0], our_lab[1], our_lab[2]
        dL = ref_L - oL
        da = ref_a - oa
        db = ref_b - ob
        offsets_l.append(dL)
        offsets_a.append(da)
        offsets_b.append(db)
        our_hex = lab_to_hex(oL, oa, ob)
        ref_hex_approx = lab_to_hex(ref_L, ref_a, ref_b)
        results.append({
            "image": os.path.basename(img_path),
            "our_lab": our_lab,
            "our_hex": our_hex,
            "ref_lab": [ref_L, ref_a, ref_b],
            "ref_hex": ref_hex_approx,
            "offset": [round(dL, 2), round(da, 2), round(db, 2)],
        })
        print(os.path.basename(img_path), "our", our_hex, "ref~", ref_hex_approx, "offset L,a,b:", round(dL, 1), round(da, 1), round(db, 1))

    if not offsets_l:
        print("Nenhum par nosso/ref válido. Verifique imagens e .txt em referencia_cor/")
        return

    # Calibração global: mediana dos offsets (mais robusto que média)
    import numpy as np
    calib_L = float(np.median(offsets_l))
    calib_a = float(np.median(offsets_a))
    calib_b = float(np.median(offsets_b))
    calibration = {
        "offset_L": round(calib_L, 4),
        "offset_a": round(calib_a, 4),
        "offset_b": round(calib_b, 4),
    }
    out_path = os.path.join(ROOT, "backend", "processing", "calib.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(calibration, f, indent=2)
    print("\nCalibração salva em", out_path, ":", calibration)
    with open(os.path.join(ROOT, "backend", "scripts", "calib_report.json"), "w", encoding="utf-8") as f:
        json.dump({"calibration": calibration, "per_image": results}, f, indent=2)
    print("Relatório por imagem: backend/scripts/calib_report.json")


if __name__ == "__main__":
    main()
