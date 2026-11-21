"""
Standalone Training Script for DocRestore AI — UI-Aware Residual U-Net
Can be executed locally or on cloud GPU (e.g. Google Colab).
"""
import os
import argparse
from pathlib import Path
from torch.utils.data import DataLoader
from app.ml_engine.models.residual_unet.architecture import ResidualUNet
from app.ml_engine.training.dataset import UIScreenshotDataset
from app.ml_engine.training.trainer import ResidualUNetTrainer
from app.core.config import settings

def main():
    parser = argparse.ArgumentParser(description="Train DocRestore AI Primary Residual U-Net")
    parser.add_argument("--data_dir", type=str, default=str(settings.ORIGINALS_DIR), help="Path to clean UI screenshots")
    parser.add_argument("--epochs", type=int, default=30, help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=4, help="Batch size")
    parser.add_argument("--patch_size", type=int, default=128, help="Patch size (pixels)")
    parser.add_argument("--lr", type=float, default=0.0001, help="Learning rate (AdamW)")
    parser.add_argument("--device", type=str, default="cuda", help="Device (cuda or cpu)")
    args = parser.parse_args()

    data_path = Path(args.data_dir)
    image_files = list(data_path.glob("*.png")) + list(data_path.glob("*.jpg"))
    if not image_files:
        print(f"No screenshots found in {data_path}. Creating sample image for demonstration...")
        from PIL import Image
        sample = data_path / "sample_ui_for_training.png"
        Image.new("RGB", (256, 256), color=(210, 210, 210)).save(sample)
        image_files = [sample]

    # Split 70% train / 15% val / 15% test
    random_state = 42
    import random
    random.seed(random_state)
    random.shuffle(image_files)

    split_idx = max(1, int(len(image_files) * 0.8))
    train_files = image_files[:split_idx]
    val_files = image_files[split_idx:] if split_idx < len(image_files) else image_files

    print(f"Loaded {len(image_files)} screenshots. Train: {len(train_files)}, Val: {len(val_files)}")

    train_ds = UIScreenshotDataset(train_files, patch_size=args.patch_size, augment=True)
    val_ds = UIScreenshotDataset(val_files, patch_size=args.patch_size, augment=False)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False)

    model = ResidualUNet(in_channels=3, out_channels=3, base_channels=48)
    trainer = ResidualUNetTrainer(model=model, lr=args.lr, device=args.device)

    print("Beginning training with UI-Aware Combined Loss (L1 + SSIM + Sobel Edge)...")
    results = trainer.fit(train_loader, val_loader, epochs=args.epochs)
    print(f"Training complete. Best Validation Loss: {results['best_val_loss']:.5f}")
    print(f"Model saved to: {settings.CHECKPOINTS_DIR / 'best_residual_unet.pth'}")

if __name__ == "__main__":
    main()

