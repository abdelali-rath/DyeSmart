# color_segmentation.py - RGB-Farbraum-Segmentierung für Friseurfarben
import numpy as np
import colorsys
from typing import Dict, Tuple, List
import cv2
import os


class HairColorSegmenter:
    """
    Segmentiert RGB-Farben in Friseurfarben (10 Tiefen × 8 Nuancen)
    """

    def __init__(self):
        # Definiere die 10 Haartiefen-Stufen (1-10)
        self.depth_levels = {
            1: {"name": "Schwarz", "min_brightness": 0, "max_brightness": 20},
            2: {"name": "Sehr dunkelbraun", "min_brightness": 20, "max_brightness": 35},
            3: {"name": "Dunkelbraun", "min_brightness": 35, "max_brightness": 50},
            4: {"name": "Mittelbraun", "min_brightness": 50, "max_brightness": 65},
            5: {"name": "Hellbraun", "min_brightness": 65, "max_brightness": 80},
            6: {"name": "Dunkelblond", "min_brightness": 80, "max_brightness": 100},
            7: {"name": "Mittelblond", "min_brightness": 100, "max_brightness": 130},
            8: {"name": "Hellblond", "min_brightness": 130, "max_brightness": 160},
            9: {"name": "Sehr hellblond", "min_brightness": 160, "max_brightness": 190},
            10: {"name": "Platinblond", "min_brightness": 190, "max_brightness": 255}
        }

        # Nuancen
        self.nuance_levels = {
            0.0: {"name": "Neutral", "hue_range": None, "rgb_conditions": None},
            0.1: {"name": "Asch", "hue_range": (80, 150), "rgb_conditions": self._is_ash},
            0.3: {"name": "Gold", "hue_range": (25, 50), "rgb_conditions": self._is_gold},
            0.4: {"name": "Kupfer", "hue_range": (10, 25), "rgb_conditions": self._is_copper},
            0.6: {"name": "Rot", "hue_range": (0, 10), "rgb_conditions": self._is_red},
            0.7: {"name": "Violett", "hue_range": (130, 170), "rgb_conditions": self._is_violet},
            0.8: {"name": "Blau", "hue_range": (100, 130), "rgb_conditions": self._is_blue}
        }

        # Referenzfarben
        self.reference_colors = self._create_reference_palette()

    def _create_reference_palette(self) -> Dict[Tuple[float, float], List[int]]:
        """Erstellt eine Referenz-Palette mit typischen Haarfarben"""
        palette = {}

        # neutral usw.
        # (Dein Original-Palette-Code 1:1)
        # -------------------------------
        palette[(1.0, 0.0)] = [10, 10, 10]
        palette[(2.0, 0.0)] = [30, 20, 15]
        palette[(3.0, 0.0)] = [50, 35, 25]
        palette[(4.0, 0.0)] = [80, 55, 40]
        palette[(5.0, 0.0)] = [110, 80, 60]
        palette[(6.0, 0.0)] = [140, 110, 85]
        palette[(7.0, 0.0)] = [170, 140, 110]
        palette[(8.0, 0.0)] = [200, 170, 140]
        palette[(9.0, 0.0)] = [220, 200, 170]
        palette[(10.0, 0.0)] = [240, 230, 210]

        palette[(1.0, 0.1)] = [15, 15, 20]
        palette[(3.0, 0.1)] = [45, 40, 50]
        palette[(5.0, 0.1)] = [100, 95, 105]
        palette[(7.0, 0.1)] = [160, 155, 165]
        palette[(9.0, 0.1)] = [210, 210, 220]

        palette[(3.0, 0.3)] = [55, 45, 30]
        palette[(5.0, 0.3)] = [120, 100, 70]
        palette[(7.0, 0.3)] = [180, 150, 100]
        palette[(9.0, 0.3)] = [230, 200, 150]

        palette[(3.0, 0.4)] = [60, 35, 25]
        palette[(5.0, 0.4)] = [130, 70, 50]
        palette[(7.0, 0.4)] = [190, 110, 80]

        palette[(2.0, 0.6)] = [40, 15, 15]
        palette[(4.0, 0.6)] = [90, 40, 35]
        palette[(6.0, 0.6)] = [150, 70, 65]

        palette[(2.0, 0.7)] = [35, 15, 40]
        palette[(4.0, 0.7)] = [85, 40, 90]
        palette[(6.0, 0.7)] = [145, 70, 150]
        palette[(8.0, 0.7)] = [200, 140, 205]

        palette[(1.0, 0.8)] = [20, 20, 40]
        palette[(3.0, 0.8)] = [50, 50, 80]
        palette[(7.0, 0.8)] = [150, 155, 200]

        return palette

    # --- Klassifikation / Tools (deine Originalmethoden vollständig unverändert)
    # --------------------------------------------------------------------------
    def rgb_to_hsv(self, rgb):
        r, g, b = rgb[0]/255., rgb[1]/255., rgb[2]/255.
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        return h * 360, s * 100, v * 100

    def _is_ash(self, rgb, h, s, v):
        b_ratio = rgb[2] / (sum(rgb) + 0.001)
        return (b_ratio > 0.32 and s < 60) or (80 <= h <= 150 and s < 70)

    def _is_gold(self, rgb, h, s, v):
        r, g, b = rgb
        return (25 <= h <= 50 and s > 30) or (r > g * 0.8 and g > b * 1.5)

    def _is_copper(self, rgb, h, s, v):
        r, g, b = rgb
        return (10 <= h <= 25 and s > 40) or (r > 1.5 * g and b < r * 0.5)

    def _is_red(self, rgb, h, s, v):
        r, g, b = rgb
        return (h < 10 or h > 350) and s > 40 and r > g * 1.2

    def _is_violet(self, rgb, h, s, v):
        r, g, b = rgb
        return (130 <= h <= 170 and s > 30) or (r > 100 and b > 100 and g < r * 0.8)

    def _is_blue(self, rgb, h, s, v):
        r, g, b = rgb
        return (100 <= h < 130 and s > 30) or (b > r * 1.2 and b > g * 1.2)

    def get_brightness(self, rgb):
        return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]

    def find_closest_depth(self, brightness):
        for depth, info in self.depth_levels.items():
            if info["min_brightness"] <= brightness <= info["max_brightness"]:
                return float(depth), info["name"]
        closest = min(self.depth_levels.keys(),
                      key=lambda d: abs(brightness - ((self.depth_levels[d]["min_brightness"] +
                                                       self.depth_levels[d]["max_brightness"]) / 2)))
        return float(closest), self.depth_levels[closest]["name"]

    def find_closest_nuance(self, rgb, h, s, v):
        if s < 20 or v < 20 or v > 230:
            return 0.0, "Neutral"

        best_score = 0
        best_nuance = 0.0
        best_name = "Neutral"

        for nuance, info in self.nuance_levels.items():
            if nuance == 0.0:
                continue

            score = 0
            if info["hue_range"]:
                mn, mx = info["hue_range"]
                if mn <= h <= mx:
                    score += 50

            if info["rgb_conditions"]:
                if info["rgb_conditions"](rgb, h, s, v):
                    score += 30

            if nuance in [0.6, 0.7, 0.8] and s > 50:
                score += 20

            if score > best_score:
                best_score = score
                best_nuance = nuance
                best_name = info["name"]

        if best_score < 40:
            return 0.0, "Neutral"

        return best_nuance, best_name

    def classify_hair_color(self, rgb):
        h, s, v = self.rgb_to_hsv(rgb)
        brightness = self.get_brightness(rgb)
        depth, depth_name = self.find_closest_depth(brightness)
        nuance, nuance_name = self.find_closest_nuance(rgb, h, s, v)
        closest = self.find_closest_reference(depth, nuance, rgb)

        return {
            "rgb": rgb,
            "depth": depth,
            "depth_name": depth_name,
            "nuance": nuance,
            "nuance_name": nuance_name,
            "brightness": brightness,
            "hue": h,
            "saturation": s,
            "value": v,
            "closest_reference": closest,
            "color_name": f"{depth_name} mit {nuance_name}-Nuance"
        }

    def find_closest_reference(self, depth, nuance, rgb):
        min_dist = float("inf")
        best = None
        best_rgb = None

        for (d, n), ref_rgb in self.reference_colors.items():
            if abs(d - depth) <= 2 and abs(n - nuance) <= 0.2:
                dist = np.linalg.norm(np.array(ref_rgb) - np.array(rgb))
                if dist < min_dist:
                    min_dist = dist
                    best = (d, n)
                    best_rgb = ref_rgb

        if best:
            return {
                "depth": best[0],
                "nuance": best[1],
                "rgb": best_rgb,
                "distance": min_dist
            }
        return None


# --- UNIVERSAL FUNKTION (FLEXIBEL!)
def analyze_hair_color_from_image(rgb_or_path):
    """
    Universal: akzeptiert entweder
        • RGB-Liste → [R, G, B]
        • Bildpfad → 'bild.jpg'
    """
    seg = HairColorSegmenter()

    # Falls Pfad → Bild laden & Durchschnitt bestimmen
    if isinstance(rgb_or_path, str) and os.path.exists(rgb_or_path):
        img = cv2.imread(rgb_or_path)
        if img is None:
            return {"error": "Bild konnte nicht geladen werden"}

        h = img.shape[0]
        crop = img[:h // 2, :]
        avg = np.mean(crop, axis=0)
        rgb = [int(avg[2]), int(avg[1]), int(avg[0])]
        return seg.classify_hair_color(rgb)

    # Falls direkt RGB übergeben
    if isinstance(rgb_or_path, list) and len(rgb_or_path) == 3:
        return seg.classify_hair_color(rgb_or_path)

    return {"error": "Ungültige Eingabe für Farbanalyse"}
