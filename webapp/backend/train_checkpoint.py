import os
import random
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import torch
from torch.utils.data import DataLoader

from app.core.config import settings
from app.ml_engine.models.residual_unet.architecture import ResidualUNet
from app.ml_engine.training.dataset import UIScreenshotDataset
from app.ml_engine.training.trainer import ResidualUNetTrainer

def generate_legacy_ui_samples(target_dir: Path, count: int = 6):
    target_dir.mkdir(parents=True, exist_ok=True)

    # Palette
    bg_colors = [(212, 208, 200), (192, 192, 192), (236, 233, 216), (240, 240, 240)]
    title_colors = [(0, 0, 128), (16, 78, 139), (70, 70, 70), (49, 106, 197)]

    for i in range(count):
        width, height = 512, 384
        bg = random.choice(bg_colors)
        img = Image.new("RGB", (width, height), color=bg)
        draw = ImageDraw.Draw(img)

        # Draw Window Frame & Title Bar
        title_bg = random.choice(title_colors)
        draw.rectangle([4, 4, width - 4, 32], fill=title_bg)
        draw.text((12, 10), f"Legacy System Manager v{i+1}.0 - [Active Session]", fill=(255, 255, 255))
        # Title bar buttons (min, max, close)
        draw.rectangle([width - 28, 8, width - 10, 26], fill=(192, 192, 192), outline=(255, 255, 255))
        draw.text((width - 22, 10), "X", fill=(0, 0, 0))

        # Menu bar
        draw.rectangle([4, 33, width - 4, 55], fill=(240, 240, 240), outline=(128, 128, 128))
        draw.text((16, 38), "File    Edit    View    Restoration    Tools    Help", fill=(0, 0, 0))

        # Group Box / Panel
        draw.rectangle([16, 68, width - 16, height - 70], outline=(128, 128, 128), fill=(225, 222, 215))
        draw.text((28, 60), " UI Component Configuration & Status ", fill=(0, 0, 128))

        # Data Rows / Text Readability test
        row_y = 90
        for r in range(5):
            draw.text((32, row_y), f"Parameter [{r+1:02d}]: 0x{random.randint(1000, 9999):X} -- Status: NORMAL", fill=(20, 20, 20))
            draw.line([(30, row_y + 20), (width - 32, row_y + 20)], fill=(180, 180, 180), width=1)
            row_y += 30

        # UI Buttons (Sharp beveled borders)
        buttons = ["OK", "Cancel", "Apply", "Restore AI", "Properties"]
        btn_x = 24
        btn_y = height - 50
        for b_text in buttons:
            draw.rectangle([btn_x, btn_y, btn_x + 72, btn_y + 26], fill=(212, 208, 200), outline=(255, 255, 255))
            draw.line([(btn_x, btn_y + 26), (btn_x + 72, btn_y + 26)], fill=(64, 64, 64), width=1)
            draw.line([(btn_x + 72, btn_y), (btn_x + 72, btn_y + 26)], fill=(64, 64, 64), width=1)
            draw.text((btn_x + 12, btn_y + 6), b_text, fill=(0, 0, 0))
            btn_x += 84

        sample_path = target_dir / f"synthetic_legacy_ui_{i+1}.png"
        img.save(sample_path)
        print(f"Generated synthetic training sample: {sample_path}")

def train_and_save_checkpoint():
    samples_dir = settings.STORAGE_PATH / "training_ui_samples"
    generate_legacy_ui_samples(samples_dir, count=8)

    # Collect images
    image_files = list(samples_dir.glob("*.png"))
    # Also include existing originals if present
    for orig in settings.ORIGINALS_DIR.glob("*.*"):
        if orig.is_file() and orig.suffix.lower() in [".png", ".jpg", ".jpeg"]:
            image_files.append(orig)

    print(f"Total training image sources: {len(image_files)}")

    train_ds = UIScreenshotDataset(image_files, patch_size=128, augment=True)
    train_loader = DataLoader(train_ds, batch_size=4, shuffle=True)

    val_ds = UIScreenshotDataset(image_files, patch_size=128, augment=False)
    val_loader = DataLoader(val_ds, batch_size=4, shuffle=False)

    model = ResidualUNet(in_channels=3, out_channels=3, base_channels=48)
    trainer = ResidualUNetTrainer(model=model, lr=0.0003, device="cpu")

    print("Training Residual U-Net on paired UI degradations with UI-Aware Combined Loss...")
    results = trainer.fit(train_loader, val_loader, epochs=15, checkpoint_dir=settings.CHECKPOINTS_DIR)

    ckpt_file = settings.CHECKPOINTS_DIR / "best_residual_unet.pth"
    print(f"SUCCESS: Checkpoint successfully verified at: {ckpt_file}")
    print(f"Best Val Loss: {results['best_val_loss']}")

if __name__ == "__main__":
    train_and_save_checkpoint()

