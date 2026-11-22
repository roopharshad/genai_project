import torch
import torch.nn as nn
import numpy as np

class SRCNN(nn.Module):
    """
    Super-Resolution Convolutional Neural Network (SRCNN).
    Classical 3-layer deep learning baseline:
    - Layer 1: Patch extraction and representation (9x9)
    - Layer 2: Non-linear mapping (1x1 / 5x5)
    - Layer 3: High-resolution reconstruction (5x5)
    """
    def __init__(self, in_channels: int = 3, out_channels: int = 3):
        super(SRCNN, self).__init__()
        self.conv1 = nn.Conv2d(in_channels, 64, kernel_size=9, padding=4)
        self.relu1 = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(64, 32, kernel_size=5, padding=2)
        self.relu2 = nn.ReLU(inplace=True)
        self.conv3 = nn.Conv2d(32, out_channels, kernel_size=5, padding=2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.relu1(self.conv1(x))
        out = self.relu2(self.conv2(out))
        out = self.conv3(out)
        return torch.clamp(out, 0.0, 1.0)

