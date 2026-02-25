"""
Extração de características cromáticas: média, mediana, k-means, descarte de outliers.
"""
import numpy as np
from sklearn.cluster import KMeans


def discard_outliers(pixels_lab, l_min=15, l_max=95, c_max=80):
    """
    Descarta highlights, sombras e reflexos (L muito alto/baixo, croma extremo).
    pixels_lab: Nx3 (L, a, b).
    """
    if pixels_lab is None or len(pixels_lab) == 0:
        return pixels_lab
    L = pixels_lab[:, 0]
    a, b = pixels_lab[:, 1], pixels_lab[:, 2]
    chroma = np.sqrt(a.astype(np.float64) ** 2 + b.astype(np.float64) ** 2)
    mask = (L >= l_min) & (L <= l_max) & (chroma <= c_max)
    out = pixels_lab[mask]
    return out if len(out) > 10 else pixels_lab


def dominant_clusters(pixels_lab, n_clusters=3):
    """K-means nas cores, retorna centros e proporções."""
    if pixels_lab is None or len(pixels_lab) < n_clusters:
        return [], []
    n = min(n_clusters, len(pixels_lab))
    kmeans = KMeans(n_clusters=n, random_state=42, n_init=10)
    labels = kmeans.fit_predict(pixels_lab)
    centers = kmeans.cluster_centers_
    counts = np.bincount(labels, minlength=n)
    props = counts / counts.sum()
    return centers.tolist(), props.tolist()


def extract_region_features(pixels_lab):
    """
    Para uma região (pele, cabelo etc.): média, mediana, clusters.
    Retorna dict com mean_lab, median_lab, clusters, chroma_mean.
    """
    if pixels_lab is None or len(pixels_lab) == 0:
        return None
    pixels = discard_outliers(pixels_lab)
    if len(pixels) == 0:
        return None
    mean_lab = np.mean(pixels, axis=0).tolist()
    median_lab = np.median(pixels, axis=0).tolist()
    centers, props = dominant_clusters(pixels, n_clusters=3)
    l, a, b = mean_lab[0], mean_lab[1], mean_lab[2]
    chroma = np.sqrt(a * a + b * b)
    return {
        "mean_lab": mean_lab,
        "median_lab": median_lab,
        "clusters": centers,
        "cluster_proportions": props,
        "chroma_mean": float(chroma),
        "n_pixels": int(len(pixels)),
    }
