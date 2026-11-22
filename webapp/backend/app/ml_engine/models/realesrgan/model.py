import torch
import torch.nn as nn
import torch.nn.functional as F

class ResidualDenseBlock(nn.Module):
    """Residual Dense Block with dense connections."""
    def __init__(self, channels: int = 32, grow_channels: int = 16):
        super(ResidualDenseBlock, self).__init__()
        self.conv1 = nn.Conv2d(channels, grow_channels, 3, 1, 1)
        self.conv2 = nn.Conv2d(channels + grow_channels, grow_channels, 3, 1, 1)
        self.conv3 = nn.Conv2d(channels + 2 * grow_channels, channels, 3, 1, 1)
        self.act = nn.LeakyReLU(0.2, inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        c1 = self.act(self.conv1(x))
        c2 = self.act(self.conv2(torch.cat([x, c1], 1)))
        c3 = self.conv3(torch.cat([x, c1, c2], 1))
        return c3 * 0.2 + x


class RRDBNet(nn.Module):
    """
    Real-ESRGAN Comparison Model architecture with Residual-in-Residual Dense Blocks.
    Used for super-resolution and fine interface detail comparison.
    """
    def __init__(self, in_channels: int = 3, out_channels: int = 3, num_features: int = 32, num_blocks: int = 3):
        super(RRDBNet, self).__init__()
        self.conv_first = nn.Conv2d(in_channels, num_features, 3, 1, 1)
        self.body = nn.Sequential(*[ResidualDenseBlock(channels=num_features) for _ in range(num_blocks)])
        self.conv_body = nn.Conv2d(num_features, num_features, 3, 1, 1)

        # Upsampling block (supports 2x or 1x with refinement)
        self.conv_up = nn.Conv2d(num_features, num_features, 3, 1, 1)
        self.conv_last = nn.Conv2d(num_features, out_channels, 3, 1, 1)
        self.act = nn.LeakyReLU(0.2, inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.conv_first(x)
        res = self.conv_body(self.body(feat))
        feat = feat + res
        out = self.act(self.conv_up(feat))
        out = self.conv_last(out)
        # Residual addition with input
        if out.shape == x.shape:
            out = torch.clamp(x + out, 0.0, 1.0)
        else:
            out = torch.clamp(out, 0.0, 1.0)
        return out

