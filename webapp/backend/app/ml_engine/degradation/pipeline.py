import io
import cv2
import numpy as np
from PIL import Image
from typing import Dict, Any, Tuple, Optional

class DegradationPipeline:
    """
    Controlled degradation pipeline: Y = D(J(N(H(X))))
    Simulates real-world legacy UI degradations:
    - Blur (H)
    - Noise (N)
    - JPEG compression (J)
    - Downsampling (D)
    """

    @staticmethod
    def apply_blur(img: np.ndarray, blur_type: str = "gaussian", kernel_size: int = 5, sigma: float = 1.5) -> np.ndarray:
        """Apply Gaussian or Motion blur."""
        if kernel_size % 2 == 0:
            kernel_size += 1
        if kernel_size <= 1:
            return img

        if blur_type == "gaussian":
            return cv2.GaussianBlur(img, (kernel_size, kernel_size), sigmaX=sigma, sigmaY=sigma)
        elif blur_type == "motion":
            kernel = np.zeros((kernel_size, kernel_size))
            kernel[int((kernel_size - 1) / 2), :] = np.ones(kernel_size)
            kernel = kernel / kernel_size
            return cv2.filter2D(img, -1, kernel)
        else:
            return cv2.blur(img, (kernel_size, kernel_size))

    @staticmethod
    def apply_noise(img: np.ndarray, noise_level: float = 15.0, seed: Optional[int] = None) -> np.ndarray:
        """Apply zero-mean Gaussian noise with standard deviation noise_level."""
        if noise_level <= 0:
            return img
        if seed is not None:
            rng = np.random.default_rng(seed)
            noise = rng.normal(0, noise_level, img.shape)
        else:
            noise = np.random.normal(0, noise_level, img.shape)
        noisy = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
        return noisy

    @staticmethod
    def apply_jpeg_compression(img: np.ndarray, quality: int = 40) -> np.ndarray:
        """Apply JPEG compression block artifacts."""
        quality = max(5, min(95, quality))
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        result, encimg = cv2.imencode('.jpg', img, encode_param)
        if result:
            decimg = cv2.imdecode(encimg, 1)
            return decimg
        return img

    @staticmethod
    def apply_downsampling(img: np.ndarray, factor: float = 2.0, resample_back: bool = True) -> np.ndarray:
        """Apply downsampling and optional bicubic upsampling back to original resolution."""
        if factor <= 1.0:
            return img
        h, w = img.shape[:2]
        new_w = max(16, int(w / factor))
        new_h = max(16, int(h / factor))
        down = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        if resample_back:
            return cv2.resize(down, (w, h), interpolation=cv2.INTER_CUBIC)
        return down

    @classmethod
    def degrade(cls, image_np: np.ndarray, config: Dict[str, Any]) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Execute full degradation chain Y = D(J(N(H(X)))).
        Returns: (degraded_image_np, metadata)
        """
        seed = config.get("seed", 42)
        blur_strength = config.get("blur_strength", 1.5)
        blur_kernel = config.get("blur_kernel", 5)
        blur_type = config.get("blur_type", "gaussian")
        noise_level = config.get("noise_level", 12.0)
        jpeg_quality = config.get("jpeg_quality", 45)
        downsample_factor = config.get("downsample_factor", 2.0)
        resample_back = config.get("resample_back", True)

        img = image_np.copy()

        # Step 1: Blur H(X)
        if blur_strength > 0:
            img = cls.apply_blur(img, blur_type=blur_type, kernel_size=int(blur_kernel), sigma=float(blur_strength))

        # Step 2: Noise N(H(X))
        if noise_level > 0:
            img = cls.apply_noise(img, noise_level=float(noise_level), seed=seed)

        # Step 3: JPEG J(N(H(X)))
        if jpeg_quality < 100:
            img = cls.apply_jpeg_compression(img, quality=int(jpeg_quality))

        # Step 4: Downsampling D(J(N(H(X))))
        if downsample_factor > 1.0:
            img = cls.apply_downsampling(img, factor=float(downsample_factor), resample_back=resample_back)

        metadata = {
            "formula": "Y = D(J(N(H(X))))",
            "seed": seed,
            "blur": {"type": blur_type, "sigma": blur_strength, "kernel": blur_kernel},
            "noise": {"level": noise_level},
            "jpeg": {"quality": jpeg_quality},
            "downsample": {"factor": downsample_factor, "resample_back": resample_back},
            "output_shape": list(img.shape)
        }

        return img, metadata


class QualityAnalyzer:
    """Analyze quality and degradation characteristics of UI screenshots."""

    @staticmethod
    def estimate_blur(gray_img: np.ndarray) -> float:
        """Calculate Laplacian variance (higher = sharper, lower = blurred)."""
        laplacian = cv2.Laplacian(gray_img, cv2.CV_64F)
        return float(laplacian.var())

    @staticmethod
    def estimate_noise(gray_img: np.ndarray) -> float:
        """Estimate standard deviation of noise using MAD of Laplacian."""
        h, w = gray_img.shape
        sigma = np.std(gray_img.astype(np.float32) - cv2.GaussianBlur(gray_img, (3, 3), 1.0))
        return float(sigma)

    @staticmethod
    def estimate_edge_density(gray_img: np.ndarray) -> float:
        """Estimate density of UI edges."""
        edges = cv2.Canny(gray_img, 50, 150)
        return float(np.sum(edges > 0) / (gray_img.shape[0] * gray_img.shape[1]))

    @classmethod
    def analyze_image(cls, image_path: str) -> Dict[str, Any]:
        """Produce comprehensive UI degradation and property analysis."""
        img_bgr = cv2.imread(str(image_path))
        if img_bgr is None:
            return {"error": "Could not read image"}

        h, w, c = img_bgr.shape
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        blur_score = cls.estimate_blur(gray)
        noise_est = cls.estimate_noise(gray)
        edge_density = cls.estimate_edge_density(gray)

        # Resolution categorization
        total_pixels = h * w
        if total_pixels < 800 * 600:
            res_category = "low_res"
        elif total_pixels < 1920 * 1080:
            res_category = "standard"
        else:
            res_category = "high_res"

        # Degradation condition classification
        has_blur = blur_score < 120.0
        has_noise = noise_est > 8.0
        is_heavily_degraded = has_blur and has_noise

        return {
            "dimensions": {"width": w, "height": h, "channels": c},
            "resolution_category": res_category,
            "blur_metric_laplacian_var": round(blur_score, 2),
            "noise_standard_deviation": round(noise_est, 2),
            "edge_density_ratio": round(edge_density, 4),
            "detected_degradations": {
                "blur_detected": bool(has_blur),
                "noise_detected": bool(has_noise),
                "compression_artifacts": bool(blur_score < 180.0),
                "heavily_degraded": bool(is_heavily_degraded)
            },
            "recommended_model": "residual_unet" if not has_noise else "conditional_diffusion"
        }

