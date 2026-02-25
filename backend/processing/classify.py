"""
Classificação cromática: subtom (quente/frio/neutro/oliva), valor, croma, contraste.
Sistema baseado em regras com thresholds interpretáveis.
"""
import numpy as np


def infer_subtom(skin_mean_lab, braco_interno_lab=None):
    """
    Subtom: quente (a>0, amarelo), frio (a<0, azul/vermelho azulado), neutro, oliva (b negativo + a).
    LAB: a+ = vermelho/magenta, a- = verde; b+ = amarelo, b- = azul.
    Pele quente: b positivo, a levemente positivo. Fria: a negativo ou b negativo. Oliva: a positivo, b negativo.
    """
    if skin_mean_lab is None or len(skin_mean_lab) < 3:
        return "neutro"
    a, b = float(skin_mean_lab[1]), float(skin_mean_lab[2])
    if braco_interno_lab is not None and len(braco_interno_lab) >= 3:
        a2, b2 = float(braco_interno_lab[1]), float(braco_interno_lab[2])
        a, b = (a + a2) / 2, (b + b2) / 2
    # Regras simples
    if b < -3 and a > 2:
        return "oliva"
    if a > 2 and b > 2:
        return "quente"
    if a < -1 or b < -2:
        return "frio"
    if -1 <= a <= 2 and -2 <= b <= 2:
        return "neutro"
    return "quente" if b > 0 else "frio"


def infer_valor(l_mean):
    """Valor (claridade): claro < 50 < médio < 65 < escuro."""
    if l_mean is None:
        return "médio"
    if l_mean < 40:
        return "escuro"
    if l_mean < 55:
        return "médio_escuro"
    if l_mean < 70:
        return "médio"
    return "claro"


def infer_croma(c_mean):
    """Croma (saturação): suave < 15 < moderado < 35 < intenso."""
    if c_mean is None or c_mean < 0:
        return "moderado"
    if c_mean < 12:
        return "suave"
    if c_mean < 25:
        return "moderado"
    return "intenso"


def infer_contrast(skin_lab, hair_lab):
    """Contraste geral: diferença L entre pele e cabelo."""
    if skin_lab is None or hair_lab is None:
        return "médio"
    l_skin = skin_lab[0] if len(skin_lab) >= 1 else 50
    l_hair = hair_lab[0] if len(hair_lab) >= 1 else 40
    diff = abs(l_skin - l_hair)
    if diff < 15:
        return "baixo"
    if diff < 35:
        return "médio"
    return "alto"


def classify_season(subtom, valor, croma, contraste):
    """
    Mapeia para sistema de 12 estações (simplificado em 4 + nuances).
    Primavera = quente claro; Verão = frio claro; Outono = quente escuro; Inverno = frio escuro.
    """
    quente = subtom in ("quente", "oliva", "neutro")
    claro = valor in ("claro", "médio")
    if quente and claro:
        base = "Primavera"
    elif not quente and claro:
        base = "Verão"
    elif quente and not claro:
        base = "Outono"
    else:
        base = "Inverno"
    if croma == "suave":
        return f"{base} suave"
    if croma == "intenso":
        return f"{base} intenso"
    return base
