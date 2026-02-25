"""
Geração de paletas e recomendações a partir do perfil cromático.
Cores em HEX e LAB; recomendações textuais explicáveis.
"""
import numpy as np

try:
    from colormath.color_objects import LabColor, sRGBColor
    from colormath.color_conversions import convert_color
    HAS_COLORMATH = True
except ImportError:
    HAS_COLORMATH = False


def lab_to_hex(L, a, b):
    """Converte LAB (L 0-100, a,b típicos -128..127) para HEX."""
    if HAS_COLORMATH:
        lab = LabColor(lab_l=L, lab_a=a, lab_b=b)
        rgb = convert_color(lab, sRGBColor)
        r = max(0, min(1, rgb.rgb_r))
        g = max(0, min(1, rgb.rgb_g))
        b_ = max(0, min(1, rgb.rgb_b))
        return "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b_*255))
    # Fallback aproximado
    L, a, b = float(L), float(a), float(b)
    y = (L + 16) / 116
    x = a / 500 + y
    z = y - b / 200
    x = 0.95047 * (x**3 if x > 0.008856 else (x - 16/116) / 7.787)
    y = 1.00000 * (y**3 if y > 0.008856 else (y - 16/116) / 7.787)
    z = 1.08883 * (z**3 if z > 0.008856 else (z - 16/116) / 7.787)
    r = x * 3.2406 + y * -1.5372 + z * -0.4986
    g = x * -0.9689 + y * 1.8758 + z * 0.0415
    b_ = x * 0.0557 + y * -0.2040 + z * 1.0570
    r = 1.055 * (r**(1/2.4)) - 0.055 if r > 0.0031308 else 12.92 * r
    g = 1.055 * (g**(1/2.4)) - 0.055 if g > 0.0031308 else 12.92 * g
    b_ = 1.055 * (b_**(1/2.4)) - 0.055 if b_ > 0.0031308 else 12.92 * b_
    r = max(0, min(255, int(255 * r)))
    g = max(0, min(255, int(255 * g)))
    b_ = max(0, min(255, int(255 * b_)))
    return "#{:02x}{:02x}{:02x}".format(r, g, b_)


def generate_palettes(subtom, valor, croma, contraste, season):
    """
    Gera paleta principal, neutra e destaque com base no perfil.
    Regras simplificadas por subtom e estação.
    """
    paleta_principal = []
    paleta_neutra = []
    paleta_destaque = []
    # Cores por subtom (LAB aproximado: L, a, b)
    if subtom == "quente":
        paleta_principal = [
            (65, 15, 45),   # coral
            (55, 25, 35),   # terracota
            (70, 10, 40),   # pêssego
            (50, 20, 25),   # mostarda suave
            (60, 5, 30),    # bege quente
        ]
        paleta_neutra = [(70, 2, 15), (55, 3, 12), (40, 2, 8), (75, 0, 10)]
        paleta_destaque = [(50, 35, 25), (45, 20, 5), (60, 30, 40)]
    elif subtom == "frio":
        paleta_principal = [
            (60, 15, -15),  # rosa frio
            (55, 20, -25),  # azul acinzentado
            (65, 5, -10),   # lavanda
            (50, 25, -20),  # ameixa
            (70, 8, -12),   # azul claro
        ]
        paleta_neutra = [(72, 0, -5), (55, 0, -8), (38, 0, -5), (78, 0, -3)]
        paleta_destaque = [(45, 30, -35), (50, 25, -30), (55, 20, -25)]
    elif subtom == "oliva":
        paleta_principal = [
            (58, 8, 20),    # verde oliva
            (62, 10, 25),   # verde sálvia
            (55, 15, 15),   # bronze
            (68, 5, 18),    # camurça
            (52, 12, 22),   # musgo
        ]
        paleta_neutra = [(65, 2, 10), (50, 3, 8), (40, 2, 5), (72, 1, 12)]
        paleta_destaque = [(48, 18, 28), (55, 15, 20), (60, 12, 25)]
    else:  # neutro
        paleta_principal = [
            (62, 8, 20), (60, 10, -5), (58, 12, 15), (65, 5, 10), (55, 15, 8),
        ]
        paleta_neutra = [(68, 1, 5), (52, 2, 4), (38, 1, 3), (75, 0, 5)]
        paleta_destaque = [(55, 22, 15), (50, 18, -10), (60, 15, 20)]

    def to_hex_list(tuples):
        return [{"lab": list(t), "hex": lab_to_hex(t[0], t[1], t[2])} for t in tuples]

    return {
        "principal": to_hex_list(paleta_principal),
        "neutra": to_hex_list(paleta_neutra),
        "destaque": to_hex_list(paleta_destaque),
    }


def generate_recommendations_text(subtom, valor, croma, contraste, season):
    """Recomendações textuais explicáveis."""
    textos = []
    textos.append(f"Seu perfil cromático foi classificado como **{season}** (subtom: {subtom}, valor: {valor}, croma: {croma}, contraste: {contraste}).")
    if subtom == "quente":
        textos.append("Cores quentes (amarelos, laranjas, corals, beiges) harmonizam com seu subtom.")
    elif subtom == "frio":
        textos.append("Cores frias (azuis, rosas frios, lavandas, cinzas azulados) harmonizam com seu subtom.")
    elif subtom == "oliva":
        textos.append("Verdes oliva, sálvia, tons terrosos e dourados suaves valorizam sua pele.")
    else:
        textos.append("Você tem boa flexibilidade: tons neutros e tanto quentes quanto frios suaves funcionam.")
    if contraste == "alto":
        textos.append("Seu contraste é alto: combinações com diferença clara entre claro e escuro ficam ótimas.")
    elif contraste == "baixo":
        textos.append("Seu contraste é suave: prefira paletas em tons próximos para looks harmônicos.")
    if croma == "suave":
        textos.append("Cores suaves e pouco saturadas tendem a destacar você sem competir.")
    elif croma == "intenso":
        textos.append("Cores mais saturadas e vivas combinam com sua intensidade natural.")
    return textos
