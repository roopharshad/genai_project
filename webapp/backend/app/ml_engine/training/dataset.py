import os
import random
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import torch
from torch.utils.data import Dataset
from PIL import Image
from app.ml_engine.degradation.pipeline import DegradationPipeline

class UIScreenshotDataset(Dataset):
    """
    PyTorch Dataset for UI screenshot paired restoration training.
    Extracts crops/patches and generates paired synthetic degradations on-the-fly:
    Y = D(J(N(H(X))))
    """
    def __init__(
        self,
        image_paths: List[Path],
        patch_size: int = 128,
        augment: bool = True,
        degrade_on_the_fly: bool = True
    ):
        self.image_paths = image_paths
        self.patch_size = patch_size
        self.augment = augment
        self.degrade_on_the_fly = degrade_on_the_fly

    def __len__(self) -> int:
        return len(self.image_paths)

    def _extract_patch(self, img_np: np.ndarray) -> np.ndarray:
        h, w = img_np.shape[:2]
        if h <= self.patch_size or w <= self.patch_size:
            # Resize if smaller than patch size
            return np.array(Image.fromarray(img_np).resize((self.patch_size, self.patch_size), Image.Resampling.LANCZOS))
        
        top = random.randint(0, h - self.patch_size)
        left = random.randint(0, w - self.patch_size)
        return img_np[top:top+self.patch_size, left:left+self.patch_size]

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, Dict[str, Any]]:
        path = self.image_paths[idx]
        with Image.open(path) as pil_img:
            clean_rgb = np.array(pil_img.convert("RGB"))

        # Extract patch
        patch_clean = self._extract_patch(clean_rgb)

        # Augmentation (Horizontal Flip)
        if self.augment and random.random() > 0.5:
            patch_clean = np.fliplr(patch_clean).copy()

        # Generate on-the-fly degradation Y = D(J(N(H(X))))
        if self.degrade_on_the_fly:
            blur_sigma = random.uniform(0.8, 2.5)
            noise_lvl = random.uniform(5.0, 20.0)
            jpeg_q = random.randint(25, 60)
            downsample = random.choice([1.0, 1.5, 2.0])

            config = {
                "blur_strength": blur_sigma,
                "blur_type": random.choice(["gaussian", "motion"]),
                "noise_level": noise_lvl,
                "jpeg_quality": jpeg_q,
                "downsample_factor": downsample,
                "resample_back": True,
                "seed": random.randint(1, 100000)
            }
            patch_degraded, meta = DegradationPipeline.degrade(patch_clean, config)
        else:
            patch_degraded = patch_clean
            meta = {}

        # Normalize to [0, 1] and transpose to [C, H, W]
        clean_tensor = torch.from_numpy(patch_clean.transpose((2, 0, 1))).float() / 255.0
        degraded_tensor = torch.from_numpy(patch_degraded.transpose((2, 0, 1))).float() / 255.0

        return degraded_tensor, clean_tensor, meta

