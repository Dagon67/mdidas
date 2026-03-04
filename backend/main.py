"""
API do módulo de colorimetria pessoal.
Recebe fotos (rosto com folha branca, braço interno, cabelo, braço externo opcional), processa e retorna perfil + paletas.
Usa calibração LAB (calib.json) quando existir para alinhar com referências profissionais.
"""
import io
import json
import os
import traceback
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# Carrega calibração LAB se existir (gerada por backend/scripts/calibrate.py)
_CALIB = None
def _load_calib():
    global _CALIB
    if _CALIB is not None:
        return _CALIB
    path = os.path.join(os.path.dirname(__file__), "processing", "calib.json")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            _CALIB = json.load(f)
    else:
        _CALIB = {}
    return _CALIB

def _apply_calib(lab_list, region_key=None):
    """Aplica offset de calibração ao mean_lab [L, a, b]. region_key: 'skin_face', 'skin_arm', 'hair'."""
    if not lab_list or len(lab_list) < 3:
        return lab_list
    calib = _load_calib()
    if not calib:
        return lab_list
    by_region = calib.get("by_region") or {}
    if region_key and region_key in by_region:
        off = by_region[region_key]
        L = float(lab_list[0]) + off[0]
        a = float(lab_list[1]) + off[1]
        b = float(lab_list[2]) + off[2]
    else:
        L = float(lab_list[0]) + calib.get("offset_L", 0)
        a = float(lab_list[1]) + calib.get("offset_a", 0)
        b = float(lab_list[2]) + calib.get("offset_b", 0)
    return [L, a, b]

from processing.preprocess import preprocess_pipeline, get_white_balance_correction, load_image
from processing.segment import segment_face_mediapipe, segment_skin_region, segment_hair_region, get_region_pixels
from processing.extract import extract_region_features
from processing.classify import infer_subtom, infer_valor, infer_croma, infer_contrast, classify_season
from processing.recommend import generate_palettes, generate_recommendations_text, lab_to_hex

app = FastAPI(title="Colorimetria Pessoal", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/")
def root():
    return {"service": "colorimetria-pessoal", "status": "ok"}


@app.post("/analisar")
async def analisar_cores(
    rosto: UploadFile = File(...),
    rosto_com_papel: Optional[UploadFile] = File(None),
    braco_interno: UploadFile = File(...),
    cabelo: UploadFile = File(...),
    braco_externo: Optional[UploadFile] = File(None),
):
    """
    Analisa as fotos e retorna perfil cromático, paletas e recomendações.
    Fotos obrigatórias: rosto, braco_interno, cabelo. rosto_com_papel (para calibrar branco) e braco_externo opcionais.
    Se rosto_com_papel for enviado, a correção de branco extraída dela é aplicada a todas as fotos.
    """
    try:
        # 1) Carregar bytes
        data_rosto = await rosto.read()
        data_braco = await braco_interno.read()
        data_cabelo = await cabelo.read()
        data_braco_ext = await braco_externo.read() if braco_externo else None

        # Correção de branco a partir da foto "rosto com papel" (quando fornecida)
        wb_correction = None
        if rosto_com_papel:
            data_papel = await rosto_com_papel.read()
            img_papel = load_image(io.BytesIO(data_papel))
            if img_papel is not None:
                da, db = get_white_balance_correction(img_papel)
                if abs(da) > 0.5 or abs(db) > 0.5:
                    wb_correction = (da, db)

        pre_rosto = preprocess_pipeline(io.BytesIO(data_rosto), wb_correction=wb_correction)
        pre_braco = preprocess_pipeline(io.BytesIO(data_braco), wb_correction=wb_correction)
        pre_cabelo = preprocess_pipeline(io.BytesIO(data_cabelo), wb_correction=wb_correction)
        if not pre_rosto or not pre_braco or not pre_cabelo:
            raise HTTPException(status_code=400, detail="Não foi possível processar uma ou mais imagens.")

        # 2) Segmentação
        face_mask_rosto = segment_face_mediapipe(pre_rosto["bgr"])
        skin_mask_rosto = segment_skin_region(pre_rosto["bgr"], face_mask_rosto)
        hair_mask_cabelo = segment_hair_region(pre_cabelo["bgr"], None)

        skin_pixels_rosto = get_region_pixels(pre_rosto["lab"], skin_mask_rosto)
        skin_pixels_braco = get_region_pixels(pre_braco["lab"], segment_skin_region(pre_braco["bgr"], None))
        hair_pixels = get_region_pixels(pre_cabelo["lab"], hair_mask_cabelo)

        # 3) Extração
        feat_skin_rosto = extract_region_features(skin_pixels_rosto)
        feat_skin_braco = extract_region_features(skin_pixels_braco)
        feat_hair = extract_region_features(hair_pixels)

        if not feat_skin_rosto:
            feat_skin_rosto = {"mean_lab": [50, 5, 15], "chroma_mean": 15}
        if not feat_skin_braco:
            feat_skin_braco = {"mean_lab": [52, 5, 14], "chroma_mean": 14}
        if not feat_hair:
            feat_hair = {"mean_lab": [35, 2, 5], "chroma_mean": 5}

        # Aplicar calibração LAB por região (skin_face, skin_arm, hair)
        if feat_skin_rosto and feat_skin_rosto.get("mean_lab"):
            feat_skin_rosto["mean_lab"] = _apply_calib(feat_skin_rosto["mean_lab"], "skin_face")
        if feat_skin_braco and feat_skin_braco.get("mean_lab"):
            feat_skin_braco["mean_lab"] = _apply_calib(feat_skin_braco["mean_lab"], "skin_arm")
        if feat_hair and feat_hair.get("mean_lab"):
            feat_hair["mean_lab"] = _apply_calib(feat_hair["mean_lab"], "hair")

        skin_mean = feat_skin_rosto.get("mean_lab") or feat_skin_braco.get("mean_lab")
        braco_mean = feat_skin_braco.get("mean_lab")
        hair_mean = feat_hair.get("mean_lab")

        # 4) Variáveis fundamentais
        subtom = infer_subtom(skin_mean, braco_mean)
        valor = infer_valor(skin_mean[0] if skin_mean else 55)
        croma = infer_croma(feat_skin_rosto.get("chroma_mean"))
        contraste = infer_contrast(skin_mean, hair_mean)
        season = classify_season(subtom, valor, croma, contraste)

        # 5) Paletas e textos
        paletas = generate_palettes(subtom, valor, croma, contraste, season)
        recomendacoes = generate_recommendations_text(subtom, valor, croma, contraste, season)

        # 6) Cores por parte do corpo (para sugestões personalizadas por região)
        def lab_to_hex_safe(lab_list):
            if not lab_list or len(lab_list) < 3:
                return "#888888"
            return lab_to_hex(float(lab_list[0]), float(lab_list[1]), float(lab_list[2]))

        cores_por_parte = {
            "rosto": {
                "hex": lab_to_hex_safe(feat_skin_rosto.get("mean_lab")),
                "dica": "Maquiagem, golas e acessórios perto do rosto: prefira tons que harmonizem com essa pele.",
            },
            "braco_interno": {
                "hex": lab_to_hex_safe(feat_skin_braco.get("mean_lab")),
                "dica": "Subtom da pele do braço ajuda a definir quente/frio; use essa referência em roupas de mangas e pulseiras.",
            },
            "cabelo": {
                "hex": lab_to_hex_safe(feat_hair.get("mean_lab")),
                "dica": "Tingimentos, chapéus e lenços: cores que conversem com seu cabelo natural valorizam o conjunto.",
            },
        }

        recomendacoes_por_parte = {
            "rosto": "Para realçar o rosto: bases e blushes no seu subtom; evite cores que criem máscara.",
            "braco_interno": "Pulseiras e mangas: tons neutros ou da sua paleta harmonizam com a pele exposta.",
            "cabelo": "Cabelo define seu contraste; use a paleta sugerida para roupas e acessórios que equilibrem com a cabeça.",
        }

        # 7) Resposta estruturada
        return {
            "perfil_cromatico": {
                "subtom": subtom,
                "valor": valor,
                "croma": croma,
                "contraste": contraste,
                "estacao": season,
                "skin_mean_lab": skin_mean,
                "hair_mean_lab": hair_mean,
            },
            "paletas": paletas,
            "recomendacoes_texto": recomendacoes,
            "cores_por_parte": cores_por_parte,
            "recomendacoes_por_parte": recomendacoes_por_parte,
            "metadados": {
                "versao": "1.0",
                "modelo": "regras",
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro no processamento: {str(e)}")
