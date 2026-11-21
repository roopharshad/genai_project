import cv2
import numpy as np
from typing import Dict, Any, Optional

class EdgePreservationEvaluator:
    """
    Evaluates interface boundary and edge preservation between restored and reference screenshots.
    Measures:
    - Sobel edge gradient Pearson correlation
    - Canny edge binary overlap F1-score (Precision, Recall, F1)
    """

    @staticmethod
    def evaluate(restored_np: np.ndarray, reference_np: np.ndarray) -> Optional[Dict[str, float]]:
        if restored_np.shape != reference_np.shape:
            return None

        # Convert to grayscale
        if len(restored_np.shape) == 3:
            gray_res = cv2.cvtColor(restored_np, cv2.COLOR_RGB2GRAY)
            gray_ref = cv2.cvtColor(reference_np, cv2.COLOR_RGB2GRAY)
        else:
            gray_res = restored_np
            gray_ref = reference_np

        # Sobel gradients
        sobel_res_x = cv2.Sobel(gray_res, cv2.CV_64F, 1, 0, ksize=3)
        sobel_res_y = cv2.Sobel(gray_res, cv2.CV_64F, 0, 1, ksize=3)
        mag_res = np.sqrt(sobel_res_x ** 2 + sobel_res_y ** 2)

        sobel_ref_x = cv2.Sobel(gray_ref, cv2.CV_64F, 1, 0, ksize=3)
        sobel_ref_y = cv2.Sobel(gray_ref, cv2.CV_64F, 0, 1, ksize=3)
        mag_ref = np.sqrt(sobel_ref_x ** 2 + sobel_ref_y ** 2)

        # Correlation between gradient magnitudes
        flat_res = mag_res.flatten()
        flat_ref = mag_ref.flatten()
        if np.std(flat_res) > 0 and np.std(flat_ref) > 0:
            corr = float(np.corrcoef(flat_res, flat_ref)[0, 1])
        else:
            corr = 0.0

        # Canny edge maps
        canny_res = cv2.Canny(gray_res, 60, 150) > 0
        canny_ref = cv2.Canny(gray_ref, 60, 150) > 0

        intersection = np.logical_and(canny_res, canny_ref).sum()
        total_res = canny_res.sum()
        total_ref = canny_ref.sum()

        precision = float(intersection / (total_res + 1e-8))
        recall = float(intersection / (total_ref + 1e-8))
        if precision + recall > 0:
            f1 = float(2 * precision * recall / (precision + recall))
        else:
            f1 = 0.0

        return {
            "edge_correlation": round(corr, 4),
            "edge_f1_score": round(f1, 4),
            "edge_precision": round(precision, 4),
            "edge_recall": round(recall, 4),
            "overall_edge_preservation_score": round((corr * 0.5 + f1 * 0.5), 4)
        }

