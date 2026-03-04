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


def delta_e_lab(lab1, lab2):
    """Delta E (Euclidiano) entre dois LAB: sqrt((L1-L2)^2 + (a1-a2)^2 + (b1-b2)^2)."""
    import math
    return math.sqrt((lab1[0] - lab2[0])**2 + (lab1[1] - lab2[1])**2 + (lab1[2] - lab2[2])**2)


def match_percent(delta_e):
    """Coincidência aproximada em %: delta_E ~0 => 100%, ~10 => 0%. Objetivo: >= 95%."""
    return max(0.0, min(100.0, 100.0 - delta_e * 5.0))


def run_pipeline_on_image(img_path, region="skin", face_mask=None, wb_correction=None):
    """Roda preprocess + segment + extract e retorna mean_lab (L 0-100, a,b float) ou None."""
    if not os.path.isfile(img_path):
        return None
    with open(img_path, "rb") as f:
        data = f.read()
    pre = preprocess_pipeline(io.BytesIO(data), wb_correction=wb_correction)
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
    # (imagem, txt, região pipeline, região calibração para API)
    cases = [
        (os.path.join(REF_DIR, "rosto_papel.jpg"), os.path.join(REF_DIR, "rosto_papel.txt"), "skin", "skin_face"),
        (os.path.join(REF_DIR, "rosto.png"), os.path.join(REF_DIR, "rosto.txt"), "skin", "skin_face"),
        (os.path.join(REF_DIR, "interno_braco.png"), os.path.join(REF_DIR, "interno_braco.txt"), "skin", "skin_arm"),
        (os.path.join(REF_DIR, "externo_braco.png"), os.path.join(REF_DIR, "externo_braco.txt"), "skin", "skin_arm"),
        (os.path.join(REF_DIR, "cabelo.png"), os.path.join(REF_DIR, "cor_cabelo.txt"), "hair", "hair"),
    ]
    offsets_by_region = {"skin_face": [], "skin_arm": [], "hair": []}  # list of (dL, da, db)
    results = []

    # Usar rosto_papel para extrair WB e aplicar em todas (simula fluxo real)
    from processing.preprocess import get_white_balance_correction, load_image
    wb_correction = None
    rosto_papel_path = os.path.join(REF_DIR, "rosto_papel.jpg")
    if os.path.isfile(rosto_papel_path):
        with open(rosto_papel_path, "rb") as f:
            img_papel = load_image(io.BytesIO(f.read()))
        if img_papel is not None:
            da, db = get_white_balance_correction(img_papel)
            if abs(da) > 0.5 or abs(db) > 0.5:
                wb_correction = (da, db)
                print("WB a partir de rosto_papel.jpg: delta_a=%.1f delta_b=%.1f" % (da, db))

    for img_path, txt_path, region, region_key in cases:
        # rosto_papel é a fonte do WB; as outras imagens usam essa correção
        use_wb = wb_correction if os.path.basename(img_path) != "rosto_papel.jpg" else None
        our_lab = run_pipeline_on_image(img_path, region, wb_correction=use_wb)
        ref_hexes = parse_hex_from_txt(txt_path)
        if not ref_hexes:
            if our_lab is not None:
                our_hex = lab_to_hex(our_lab[0], our_lab[1], our_lab[2])
                print(os.path.basename(img_path), "our", our_hex, "(sem ref em", os.path.basename(txt_path) + ")")
            else:
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
        offsets_by_region[region_key].append((dL, da, db))
        our_hex = lab_to_hex(oL, oa, ob)
        ref_hex_approx = lab_to_hex(ref_L, ref_a, ref_b)
        de = delta_e_lab(our_lab, [ref_L, ref_a, ref_b])
        pct = match_percent(de)
        results.append({
            "image": os.path.basename(img_path),
            "region_key": region_key,
            "our_lab": our_lab,
            "our_hex": our_hex,
            "ref_lab": [ref_L, ref_a, ref_b],
            "ref_hex": ref_hex_approx,
            "offset": [round(dL, 2), round(da, 2), round(db, 2)],
            "delta_e": round(de, 2),
            "match_percent": round(pct, 1),
        })
        print(os.path.basename(img_path), "our", our_hex, "ref~", ref_hex_approx, "offset L,a,b:", round(dL, 1), round(da, 1), round(db, 1), "| delta_E=%.1f coincidência=%.0f%%" % (de, pct))

    import numpy as np
    # Calibração por região (skin_face, skin_arm, hair)
    # skin_face: offset de rosto_papel (cenário com papel)
    # skin_arm: offset só de interno_braco.png (referência confiável; externo_braco pode ter fallback impreciso)
    by_region = {}
    for rk, offsets in offsets_by_region.items():
        if not offsets:
            continue
        if rk == "skin_face" and len(offsets) >= 1:
            first = offsets[0]
            by_region[rk] = [round(first[0], 4), round(first[1], 4), round(first[2], 4)]
        elif rk == "skin_arm":
            # Usar só o primeiro (interno_braco) para não estragar com externo_braco
            first = offsets[0]
            by_region[rk] = [round(first[0], 4), round(first[1], 4), round(first[2], 4)]
        else:
            dLs = [x[0] for x in offsets]
            dAs = [x[1] for x in offsets]
            dBs = [x[2] for x in offsets]
            by_region[rk] = [
                round(float(np.median(dLs)), 4),
                round(float(np.median(dAs)), 4),
                round(float(np.median(dBs)), 4),
            ]
    # Fallback global (mediana de todos os offsets)
    all_offsets = []
    for off_list in offsets_by_region.values():
        all_offsets.extend(off_list)
    if not all_offsets:
        print("Nenhum par nosso/ref válido. Verifique imagens e .txt em referencia_cor/")
        return
    calib_L = float(np.median([x[0] for x in all_offsets]))
    calib_a = float(np.median([x[1] for x in all_offsets]))
    calib_b = float(np.median([x[2] for x in all_offsets]))
    calibration = {
        "offset_L": round(calib_L, 4),
        "offset_a": round(calib_a, 4),
        "offset_b": round(calib_b, 4),
        "by_region": by_region,
    }
    out_path = os.path.join(ROOT, "backend", "processing", "calib.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(calibration, f, indent=2)
    print("\nCalibração salva em", out_path, ":", calibration)

    # Coincidência após aplicar calibração por região
    print("\nCoincidência após calibração (por região):")
    for r in results:
        o = r["our_lab"]
        rk = r.get("region_key", "skin_face")
        off = by_region.get(rk, [calib_L, calib_a, calib_b])
        calib_L_app = o[0] + off[0]
        calib_a_app = o[1] + off[1]
        calib_b_app = o[2] + off[2]
        ref = r["ref_lab"]
        de_after = delta_e_lab([calib_L_app, calib_a_app, calib_b_app], ref)
        pct_after = match_percent(de_after)
        r["delta_e_after_calib"] = round(de_after, 2)
        r["match_percent_after_calib"] = round(pct_after, 1)
        print("  %s (%s): delta_E=%.1f coincidência=%.0f%%" % (r["image"], rk, de_after, pct_after))
    avg_match = sum(r.get("match_percent_after_calib", 0) for r in results) / max(1, len(results))
    print("  Média coincidência: %.0f%% (objetivo >= 95%%)" % avg_match)

    with open(os.path.join(ROOT, "backend", "scripts", "calib_report.json"), "w", encoding="utf-8") as f:
        json.dump({"calibration": calibration, "per_image": results}, f, indent=2)
    print("\nRelatório por imagem: backend/scripts/calib_report.json")


if __name__ == "__main__":
    main()
