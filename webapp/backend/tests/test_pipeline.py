import pytest
import numpy as np
import torch
from app.ml_engine.degradation.pipeline import DegradationPipeline, QualityAnalyzer
from app.ml_engine.models.residual_unet.architecture import ResidualUNet
from app.ml_engine.models.residual_unet.losses import UIAwareLoss
from app.ml_engine.inference.registry import ModelRegistry
from app.ml_engine.evaluation.metrics import MetricCalculator
from app.ml_engine.evaluation.edge_eval import EdgePreservationEvaluator
from app.ml_engine.evaluation.ocr_eval import OCREvaluator

def test_degradation_pipeline():
    # Create clean synthetic UI test patch (128x128x3)
    clean_img = np.full((128, 128, 3), 200, dtype=np.uint8)
    clean_img[20:60, 20:100] = [10, 40, 180] # Dark blue button

    config = {
        "blur_strength": 1.5,
        "noise_level": 12.0,
        "jpeg_quality": 40,
        "downsample_factor": 2.0,
        "seed": 42
    }
    degraded, meta = DegradationPipeline.degrade(clean_img, config)

    assert degraded.shape == clean_img.shape
    assert meta["formula"] == "Y = D(J(N(H(X))))"
    assert meta["seed"] == 42
    # Verify image was degraded (not identical)
    assert not np.array_equal(degraded, clean_img)

def test_residual_unet_architecture():
    model = ResidualUNet(in_channels=3, out_channels=3, base_channels=16)
    model.eval()

    # Input tensor [1, 3, 64, 64]
    x = torch.rand(1, 3, 64, 64)
    with torch.no_grad():
        residual = model.forward_residual(x)
        output = model(x)

    assert residual.shape == x.shape
    assert output.shape == x.shape
    # Bounded residual
    assert torch.all(residual >= -1.0) and torch.all(residual <= 1.0)
    # Output in [0, 1]
    assert torch.all(output >= 0.0) and torch.all(output <= 1.0)

def test_ui_aware_loss():
    loss_fn = UIAwareLoss(lambda1=1.0, lambda2=0.5, lambda3=0.5)
    pred = torch.rand(2, 3, 64, 64)
    target = torch.rand(2, 3, 64, 64)

    total_loss, components = loss_fn(pred, target)

    assert total_loss > 0.0
    assert "l1_loss" in components
    assert "ssim_loss" in components
    assert "edge_loss" in components

def test_all_models_inference():
    test_img = np.full((64, 64, 3), 220, dtype=np.uint8)
    test_img[10:30, 10:50] = [0, 0, 128]

    models = ["opencv", "srcnn", "residual_unet", "realesrgan", "conditional_diffusion", "residual_diffusion"]

    for m_id in models:
        restored, op_metrics = ModelRegistry.run_restoration(m_id, test_img, {"sampling_steps": 5})
        assert restored.shape == test_img.shape
        assert "inference_time_ms" in op_metrics
        assert op_metrics["model_id"] == m_id

def test_evaluation_metrics():
    img1 = np.full((64, 64, 3), 150, dtype=np.uint8)
    img2 = img1.copy()
    img2[10:20, 10:20] = 50

    psnr = MetricCalculator.calculate_psnr(img2, img1)
    ssim = MetricCalculator.calculate_ssim(img2, img1)
    lpips = MetricCalculator.calculate_lpips_approx(img2, img1)
    edge_eval = EdgePreservationEvaluator.evaluate(img2, img1)
    ocr_eval = OCREvaluator.evaluate_text_consistency(img2, img1)

    assert psnr is not None and psnr > 0
    assert ssim is not None and 0 <= ssim <= 1.0
    assert lpips is not None and lpips >= 0
    assert edge_eval is not None
    assert "overall_edge_preservation_score" in edge_eval
    assert ocr_eval is not None
    assert "estimated_word_accuracy" in ocr_eval

