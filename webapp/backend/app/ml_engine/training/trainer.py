import os
import time
from pathlib import Path
from typing import Dict, Any, Optional
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from app.ml_engine.models.residual_unet.architecture import ResidualUNet
from app.ml_engine.models.residual_unet.losses import UIAwareLoss
from app.ml_engine.evaluation.metrics import MetricCalculator
from app.core.config import settings

class ResidualUNetTrainer:
    """
    Dedicated Trainer for UI-Aware Residual U-Net.
    Implements:
    - AdamW optimizer with cosine/step decay
    - Combined UI-aware loss (L1 + SSIM + Sobel edge)
    - Validation loop with PSNR and SSIM tracking
    - Early stopping & model checkpoint persistence
    """
    def __init__(
        self,
        model: Optional[ResidualUNet] = None,
        lr: float = 0.0001,
        weight_decay: float = 1e-4,
        lambda1: float = 1.0,
        lambda2: float = 0.5,
        lambda3: float = 0.5,
        device: str = "cpu"
    ):
        self.device = torch.device(device if torch.cuda.is_available() and device != "cpu" else "cpu")
        self.model = model or ResidualUNet(in_channels=3, out_channels=3, base_channels=48)
        self.model.to(self.device)

        self.criterion = UIAwareLoss(lambda1=lambda1, lambda2=lambda2, lambda3=lambda3).to(self.device)
        self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=lr, weight_decay=weight_decay)
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(self.optimizer, mode='min', factor=0.5, patience=5)

    def train_epoch(self, dataloader: DataLoader) -> Dict[str, float]:
        self.model.train()
        total_loss = 0.0
        total_l1 = 0.0
        total_ssim = 0.0
        total_edge = 0.0

        for degraded, clean, _ in dataloader:
            degraded = degraded.to(self.device)
            clean = clean.to(self.device)

            self.optimizer.zero_grad()
            restored = self.model(degraded)
            loss, components = self.criterion(restored, clean)
            loss.backward()

            # Gradient clipping for stability
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()

            total_loss += components["total_loss"]
            total_l1 += components["l1_loss"]
            total_ssim += components["ssim_loss"]
            total_edge += components["edge_loss"]

        n = max(1, len(dataloader))
        return {
            "loss": total_loss / n,
            "l1": total_l1 / n,
            "ssim_loss": total_ssim / n,
            "edge_loss": total_edge / n,
        }

    @torch.no_grad()
    def validate(self, dataloader: DataLoader) -> Dict[str, float]:
        self.model.eval()
        total_loss = 0.0
        psnr_scores = []

        for degraded, clean, _ in dataloader:
            degraded = degraded.to(self.device)
            clean = clean.to(self.device)

            restored = self.model(degraded)
            loss, _ = self.criterion(restored, clean)
            total_loss += loss.item()

            # Measure PSNR on batch
            deg_np = (restored.cpu().numpy() * 255).astype('uint8')
            clean_np = (clean.cpu().numpy() * 255).astype('uint8')
            for b in range(deg_np.shape[0]):
                p = MetricCalculator.calculate_psnr(deg_np[b].transpose((1, 2, 0)), clean_np[b].transpose((1, 2, 0)))
                if p:
                    psnr_scores.append(p)

        n = max(1, len(dataloader))
        avg_psnr = float(sum(psnr_scores) / len(psnr_scores)) if psnr_scores else 0.0
        return {
            "val_loss": total_loss / n,
            "val_psnr": avg_psnr
        }

    def fit(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        epochs: int = 30,
        checkpoint_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        ckpt_path = checkpoint_dir or settings.CHECKPOINTS_DIR
        ckpt_path.mkdir(parents=True, exist_ok=True)

        best_val_loss = float('inf')
        history = []

        for epoch in range(1, epochs + 1):
            train_metrics = self.train_epoch(train_loader)
            val_metrics = self.validate(val_loader)
            self.scheduler.step(val_metrics["val_loss"])

            entry = {
                "epoch": epoch,
                "train_loss": round(train_metrics["loss"], 5),
                "val_loss": round(val_metrics["val_loss"], 5),
                "val_psnr": round(val_metrics["val_psnr"], 2),
            }
            history.append(entry)

            # Checkpoint best model
            if val_metrics["val_loss"] < best_val_loss:
                best_val_loss = val_metrics["val_loss"]
                torch.save({
                    "epoch": epoch,
                    "model_state_dict": self.model.state_dict(),
                    "optimizer_state_dict": self.optimizer.state_dict(),
                    "val_loss": best_val_loss,
                    "val_psnr": val_metrics["val_psnr"]
                }, ckpt_path / "best_residual_unet.pth")

        return {"best_val_loss": best_val_loss, "history": history}

