"""
API do módulo de colorimetria pessoal.
Recebe fotos (rosto, braço interno, cabelo, braço externo opcional), processa e retorna perfil + paletas.
"""
import io
import traceback
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from processing.preprocess import preprocess_pipeline
from processing.segment import segment_face_mediapipe, segment_skin_region, segment_hair_region, get_region_pixels
from processing.extract import extract_region_features
from processing.classify import infer_subtom, infer_valor, infer_croma, infer_contrast, classify_season
from processing.recommend import generate_palettes, generate_recommendations_text

app = FastAPI(title="Colorimetria Pessoal", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/")
def root():
    return {"service": "colorimetria-pessoal", "status": "ok"}


@app.post("/analisar")
async def analisar_cores(
    rosto: UploadFile = File(...),
    braco_interno: UploadFile = File(...),
    cabelo: UploadFile = File(...),
    braco_externo: Optional[UploadFile] = File(None),
):
    """
    Analisa as fotos e retorna perfil cromático, paletas e recomendações.
    Fotos obrigatórias: rosto, braco_interno, cabelo. braco_externo opcional.
    """
    try:
        # 1) Carregar e pré-processar (UploadFile.read() é async e retorna bytes)
        data_rosto = await rosto.read()
        data_braco = await braco_interno.read()
        data_cabelo = await cabelo.read()
        data_braco_ext = await braco_externo.read() if braco_externo else None

        pre_rosto = preprocess_pipeline(io.BytesIO(data_rosto))
        pre_braco = preprocess_pipeline(io.BytesIO(data_braco))
        pre_cabelo = preprocess_pipeline(io.BytesIO(data_cabelo))
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

        # 6) Resposta estruturada
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
