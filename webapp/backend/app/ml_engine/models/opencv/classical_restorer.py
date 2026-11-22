import cv2
import numpy as np
from PIL import Image
from typing import Dict, Any

class OpenCVRestorer:
    """
    Classical Baseline Restoration Engine (OpenCV).
    Combines:
    - Bilateral filter edge-preserving smoothing
    - Unsharp masking high-frequency edge boost
    - CLAHE (Contrast Limited Adaptive Histogram Equalization)
    - Morphological edge sharpening for button & box borders
    """

    @staticmethod
    def restore(image_np: np.ndarray, config: Dict[str, Any] = None) -> np.ndarray:
        config = config or {}
        d = config.get("bilateral_diameter", 7)
        sigma_color = config.get("sigma_color", 50.0)
        sigma_space = config.get("sigma_space", 50.0)
        unsharp_strength = config.get("unsharp_strength", 1.4)
        use_clahe = config.get("use_clahe", True)

        img = image_np.copy()

        # Step 1: Bilateral Filter (Smooths compression artifacts & noise while retaining sharp UI boundaries)
        filtered = cv2.bilateralFilter(img, d, sigma_color, sigma_space)

        # Step 2: Unsharp Masking
        # Mask = Original - Blurred
        blurred = cv2.GaussianBlur(filtered, (0, 0), 2.0)
        unsharp = cv2.addWeighted(filtered, 1.0 + unsharp_strength, blurred, -unsharp_strength, 0)

        # Step 3: CLAHE on Luminance channel for crisp UI text & icon contrast
        if use_clahe:
            lab = cv2.cvtColor(unsharp, cv2.COLOR_RGB2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=1.8, tileGridSize=(8, 8))
            cl = clahe.apply(l)
            enhanced_lab = cv2.merge((cl, a, b))
            result = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2RGB)
        else:
            result = unsharp

        return np.clip(result, 0, 255).astype(np.uint8)

