import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Dict

def gaussian_window(window_size: int, sigma: float) -> torch.Tensor:
    gauss = torch.Tensor([
        -(x - window_size // 2) ** 2 / float(2 * sigma ** 2) for x in range(window_size)
    ]).exp()
    return gauss / gauss.sum()

def create_window(window_size: int, channel: int) -> torch.Tensor:
    _1D_window = gaussian_window(window_size, 1.5).unsqueeze(1)
    _2D_window = _1D_window.mm(_1D_window.t()).float().unsqueeze(0).unsqueeze(0)
    window = _2D_window.expand(channel, 1, window_size, window_size).contiguous()
    return window

def ssim_tensor(img1: torch.Tensor, img2: torch.Tensor, window_size: int = 11) -> torch.Tensor:
    """Calculate SSIM between two 4D tensors [B, C, H, W] in [0, 1]."""
    channel = img1.size(1)
    window = create_window(window_size, channel).to(img1.device).type_as(img1)

    mu1 = F.conv2d(img1, window, padding=window_size // 2, groups=channel)
    mu2 = F.conv2d(img2, window, padding=window_size // 2, groups=channel)

    mu1_sq = mu1.pow(2)
    mu2_sq = mu2.pow(2)
    mu1_mu2 = mu1 * mu2

    sigma1_sq = F.conv2d(img1 * img1, window, padding=window_size // 2, groups=channel) - mu1_sq
    sigma2_sq = F.conv2d(img2 * img2, window, padding=window_size // 2, groups=channel) - mu2_sq
    sigma12 = F.conv2d(img1 * img2, window, padding=window_size // 2, groups=channel) - mu1_mu2

    C1 = 0.01 ** 2
    C2 = 0.03 ** 2

    ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))
    return ssim_map.mean()


class SobelEdgeLoss(nn.Module):
    """Measures edge preservation between predicted and target images using Sobel operator."""
    def __init__(self):
        super(SobelEdgeLoss, self).__init__()
        # Sobel X
        sobel_x = torch.tensor([[-1.0, 0.0, 1.0],
                                [-2.0, 0.0, 2.0],
                                [-1.0, 0.0, 1.0]], dtype=torch.float32).view(1, 1, 3, 3)
        # Sobel Y
        sobel_y = torch.tensor([[-1.0, -2.0, -1.0],
                                [ 0.0,  0.0,  0.0],
                                [ 1.0,  2.0,  1.0]], dtype=torch.float32).view(1, 1, 3, 3)

        self.register_buffer("sobel_x", sobel_x)
        self.register_buffer("sobel_y", sobel_y)

    def extract_edges(self, x: torch.Tensor) -> torch.Tensor:
        # Convert RGB to Luminance
        if x.size(1) == 3:
            gray = 0.299 * x[:, 0:1] + 0.587 * x[:, 1:2] + 0.114 * x[:, 2:3]
        else:
            gray = x

        edge_x = F.conv2d(gray, self.sobel_x, padding=1)
        edge_y = F.conv2d(gray, self.sobel_y, padding=1)
        edges = torch.sqrt(edge_x ** 2 + edge_y ** 2 + 1e-6)
        return edges

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        pred_edges = self.extract_edges(pred)
        target_edges = self.extract_edges(target)
        return F.l1_loss(pred_edges, target_edges)


class UIAwareLoss(nn.Module):
    """
    Combined UI-Aware Loss Function:
    L_UNet = lambda1 * L1 + lambda2 * (1 - SSIM) + lambda3 * L_edge
    """
    def __init__(self, lambda1: float = 1.0, lambda2: float = 0.5, lambda3: float = 0.5):
        super(UIAwareLoss, self).__init__()
        self.lambda1 = lambda1
        self.lambda2 = lambda2
        self.lambda3 = lambda3
        self.l1_loss = nn.L1Loss()
        self.edge_loss = SobelEdgeLoss()

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> Tuple[torch.Tensor, Dict[str, float]]:
        l1 = self.l1_loss(pred, target)
        ssim_val = ssim_tensor(pred, target)
        ssim_loss = 1.0 - ssim_val
        edge = self.edge_loss(pred, target)

        total_loss = self.lambda1 * l1 + self.lambda2 * ssim_loss + self.lambda3 * edge

        components = {
            "total_loss": float(total_loss.item()),
            "l1_loss": float(l1.item()),
            "ssim_metric": float(ssim_val.item()),
            "ssim_loss": float(ssim_loss.item()),
            "edge_loss": float(edge.item()),
        }
        return total_loss, components

