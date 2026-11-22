import torch
import torch.nn as nn
import torch.nn.functional as F

class ResidualConvBlock(nn.Module):
    """Convolution block with local residual connection."""
    def __init__(self, in_channels: int, out_channels: int):
        super(ResidualConvBlock, self).__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.act1 = nn.LeakyReLU(0.1, inplace=True)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.act2 = nn.LeakyReLU(0.1, inplace=True)

        if in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, bias=False),
                nn.BatchNorm2d(out_channels)
            )
        else:
            self.shortcut = nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        res = self.shortcut(x)
        out = self.act1(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out = self.act2(out + res)
        return out


class ResidualUNet(nn.Module):
    """
    Primary Model — UI-Aware Residual U-Net.
    
    Predicts residual correction:
        R = F_theta(Y)
    Restored output:
        X_hat = Y + F_theta(Y)
    
    Predicts a correction to the degraded input rather than reconstructing the
    complete image independently, preserving existing UI structures, borders, and text.
    """
    def __init__(self, in_channels: int = 3, out_channels: int = 3, base_channels: int = 48):
        super(ResidualUNet, self).__init__()
        b = base_channels

        # Encoder
        self.enc1 = ResidualConvBlock(in_channels, b)
        self.pool1 = nn.MaxPool2d(2)

        self.enc2 = ResidualConvBlock(b, b * 2)
        self.pool2 = nn.MaxPool2d(2)

        self.enc3 = ResidualConvBlock(b * 2, b * 4)
        self.pool3 = nn.MaxPool2d(2)

        # Bottleneck
        self.bottleneck = ResidualConvBlock(b * 4, b * 8)

        # Decoder
        self.up3 = nn.ConvTranspose2d(b * 8, b * 4, kernel_size=2, stride=2)
        self.dec3 = ResidualConvBlock(b * 8, b * 4)

        self.up2 = nn.ConvTranspose2d(b * 4, b * 2, kernel_size=2, stride=2)
        self.dec2 = ResidualConvBlock(b * 4, b * 2)

        self.up1 = nn.ConvTranspose2d(b * 2, b, kernel_size=2, stride=2)
        self.dec1 = ResidualConvBlock(b * 2, b)

        # Residual head
        self.out_conv = nn.Sequential(
            nn.Conv2d(b, b, kernel_size=3, padding=1),
            nn.LeakyReLU(0.1, inplace=True),
            nn.Conv2d(b, out_channels, kernel_size=3, padding=1),
            nn.Tanh() # Produces bounded residual corrections [-1.0, 1.0]
        )

    def forward_residual(self, y: torch.Tensor) -> torch.Tensor:
        """Predicts residual correction R = F_theta(Y)."""
        # Encoder
        e1 = self.enc1(y)
        e2 = self.enc2(self.pool1(e1))
        e3 = self.enc3(self.pool2(e2))

        # Bottleneck
        b = self.bottleneck(self.pool3(e3))

        # Decoder with skip connections
        d3 = self.up3(b)
        # Pad if dimension mismatch due to odd dimensions
        if d3.shape != e3.shape:
            d3 = F.interpolate(d3, size=e3.shape[2:], mode="bilinear", align_corners=False)
        d3 = self.dec3(torch.cat([d3, e3], dim=1))

        d2 = self.up2(d3)
        if d2.shape != e2.shape:
            d2 = F.interpolate(d2, size=e2.shape[2:], mode="bilinear", align_corners=False)
        d2 = self.dec2(torch.cat([d2, e2], dim=1))

        d1 = self.up1(d2)
        if d1.shape != e1.shape:
            d1 = F.interpolate(d1, size=e1.shape[2:], mode="bilinear", align_corners=False)
        d1 = self.dec1(torch.cat([d1, e1], dim=1))

        residual = self.out_conv(d1)
        return residual

    def forward(self, y: torch.Tensor) -> torch.Tensor:
        """
        Calculates restored output:
        X_hat = Y + F_theta(Y) clamped to [0, 1].
        """
        residual = self.forward_residual(y)
        restored = torch.clamp(y + residual, 0.0, 1.0)
        return restored

