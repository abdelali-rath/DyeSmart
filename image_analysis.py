# image_analysis.py - Neue Version mit Farbsegmentierung & Preprocessing
import cv2
import numpy as np
from typing import Dict, Tuple
from color_segmentation import analyze_hair_color_from_image


def apply_color_correction_and_mask(image_path: str):
    bgr_bild = cv2.imread(image_path)
    if bgr_bild is None:
        raise FileNotFoundError(f"Bild nicht gefunden: {image_path}")

    height, width = bgr_bild.shape[:2]
    hair_region = bgr_bild[:height//2, :]

    lab = cv2.cvtColor(hair_region, cv2.COLOR_BGR2LAB)
    L, a, b = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    L_eq = clahe.apply(L)

    lab_eq = cv2.merge([L_eq, a, b])
    bgr_eq = cv2.cvtColor(lab_eq, cv2.COLOR_LAB2BGR)

    _, mask_raw = cv2.threshold(L_eq, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask_raw, cv2.MORPH_OPEN, kernel, iterations=1)

    hair_pixels = hair_region[mask == 255]

    return bgr_eq, mask, hair_pixels


def analyze_hair_image_simple(image_path: str) -> Dict:
    try:
        _, mask, hair_pixels_bgr = apply_color_correction_and_mask(image_path)

        if hair_pixels_bgr.size == 0:
            return {"error": "Keine Haarpixel gefunden – Hintergrund wirklich weiß?"}

        avg_bgr = np.mean(hair_pixels_bgr, axis=0)
        avg_rgb = [int(avg_bgr[2]), int(avg_bgr[1]), int(avg_bgr[0])]

        # KORREKT: wir geben nun RGB an analyze_hair_color_from_image()
        result = analyze_hair_color_from_image(avg_rgb)

        if "error" in result:
            return result

        return {
            "source_depth": result["depth"],
            "source_nuance": result["nuance"],
            "avg_color": avg_rgb,
            "depth_name": result["depth_name"],
            "nuance_name": result["nuance_name"],
            "info": f"Segmentierte Analyse: {result['color_name']} ({len(hair_pixels_bgr)} Pixel)",
            "full_analysis": result
        }

    except Exception as e:
        return {"error": f"Analysefehler: {str(e)}"}
