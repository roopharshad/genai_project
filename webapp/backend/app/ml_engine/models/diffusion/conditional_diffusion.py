import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Optional

class SinusoidalPositionEmbeddings(nn.Module):
    """Sinusoidal embeddings for diffusion timestep t."""
    def __init__(self, dim: int):
        super(SinusoidalPositionEmbeddings, self).__init__()
        self.dim = dim

    def forward(self, time: torch.Tensor) -> torch.Tensor:
        device = time.device
        half_dim = self.dim // 2
        embeddings = math.log(10000) / (half_dim - 1)
        embeddings = torch.exp(torch.arange(half_dim, device=device) * -embeddings)
        embeddings = time[:, None] * embeddings[None, :]
        embeddings = torch.cat((embeddings.sin(), embeddings.cos()), dim=-1)
        return embeddings


class ConditionalDiffusionUNet(nn.Module):
    """
    Compact Pixel-Space Conditional Diffusion Model for UI restoration.
    Receives noisy image X_t concatenated with degraded conditioning screenshot Y,
    conditioned on diffusion timestep t.
    """
    def __init__(self, in_channels: int = 6, out_channels: int = 3, time_dim: int = 64, base_ch: int = 32):
        super(ConditionalDiffusionUNet, self).__init__()
        self.time_dim = time_dim
        mid_ch = base_ch * 4

        # Timestep MLP
        self.time_mlp = nn.Sequential(
            SinusoidalPositionEmbeddings(time_dim),
            nn.Linear(time_dim, mid_ch),
            nn.SiLU(),
            nn.Linear(mid_ch, mid_ch),
        )

        # Encoder
        self.conv_in = nn.Conv2d(in_channels, base_ch, 3, padding=1)
        self.down1 = nn.Conv2d(base_ch, base_ch * 2, 3, stride=2, padding=1)
        self.down2 = nn.Conv2d(base_ch * 2, mid_ch, 3, stride=2, padding=1)

        # Bottleneck
        self.mid_conv1 = nn.Conv2d(mid_ch, mid_ch, 3, padding=1)
        self.mid_conv2 = nn.Conv2d(mid_ch, mid_ch, 3, padding=1)

        # Decoder
        self.up2 = nn.ConvTranspose2d(mid_ch, base_ch * 2, 2, stride=2)
        self.conv_dec2 = nn.Conv2d(base_ch * 4, base_ch * 2, 3, padding=1)
        
        self.up1 = nn.ConvTranspose2d(base_ch * 2, base_ch, 2, stride=2)
        self.conv_dec1 = nn.Conv2d(base_ch * 2, base_ch, 3, padding=1)

        self.conv_out = nn.Conv2d(base_ch, out_channels, 3, padding=1)
        self.act = nn.SiLU()

    def forward(self, x_t: torch.Tensor, y: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
        """
        x_t: [B, 3, H, W] noisy image
        y: [B, 3, H, W] degraded conditioning screenshot
        t: [B] diffusion timestep
        """
        # Embed timestep
        t_emb = self.time_mlp(t)[:, :, None, None] # [B, mid_ch, 1, 1]

        # Concatenate noisy image with condition: [B, 6, H, W]
        feat = torch.cat([x_t, y], dim=1)
        d0 = self.act(self.conv_in(feat))
        d1 = self.act(self.down1(d0))
        d2 = self.act(self.down2(d1))

        # Mid
        m = self.act(self.mid_conv1(d2)) + t_emb
        m = self.act(self.mid_conv2(m))

        # Up
        u2 = self.up2(m)
        if u2.shape != d1.shape:
            u2 = F.interpolate(u2, size=d1.shape[2:], mode="bilinear", align_corners=False)
        u2 = self.act(self.conv_dec2(torch.cat([u2, d1], dim=1)))

        u1 = self.up1(u2)
        if u1.shape != d0.shape:
            u1 = F.interpolate(u1, size=d0.shape[2:], mode="bilinear", align_corners=False)
        u1 = self.act(self.conv_dec1(torch.cat([u1, d0], dim=1)))

        eps_pred = self.conv_out(u1)
        return eps_pred


class ConditionalDiffusionEngine:
    """
    Forward diffusion schedule and reverse sampling for Conditional Diffusion.
    Linear / Cosine noise schedule.
    """
    def __init__(self, timesteps: int = 100, beta_start: float = 0.0001, beta_end: float = 0.02, device: str = "cpu"):
        self.timesteps = timesteps
        self.device = device

        self.betas = torch.linspace(beta_start, beta_end, timesteps, dtype=torch.float32)
        self.alphas = 1.0 - self.betas
        self.alphas_cumprod = torch.cumprod(self.alphas, dim=0)
        self.alphas_cumprod_prev = F.pad(self.alphas_cumprod[:-1], (1, 0), value=1.0)
        self.sqrt_alphas_cumprod = torch.sqrt(self.alphas_cumprod)
        self.sqrt_one_minus_alphas_cumprod = torch.sqrt(1.0 - self.alphas_cumprod)

    def q_sample(self, x_0: torch.Tensor, t: torch.Tensor, noise: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor]:
        """Forward diffusion: q(X_t | X_0) = sqrt(alpha_bar_t)*X_0 + sqrt(1 - alpha_bar_t)*epsilon"""
        if noise is None:
            noise = torch.randn_like(x_0)
        sqrt_alphas_cumprod_t = self.sqrt_alphas_cumprod.to(x_0.device)[t].view(-1, 1, 1, 1)
        sqrt_one_minus_alphas_cumprod_t = self.sqrt_one_minus_alphas_cumprod.to(x_0.device)[t].view(-1, 1, 1, 1)
        x_t = sqrt_alphas_cumprod_t * x_0 + sqrt_one_minus_alphas_cumprod_t * noise
        return x_t, noise

    @torch.no_grad()
    def p_sample_loop(self, model: nn.Module, y: torch.Tensor, num_steps: int = 15) -> torch.Tensor:
        """
        Reverse sampling loop: starts from random noise guided by conditioning image Y.
        Accelerated sampling steps for fast, responsive UI inference.
        """
        model.eval()
        b, c, h, w = y.shape
        x_t = torch.randn_like(y)

        # Subsample timesteps for fast generation
        step_indices = torch.linspace(self.timesteps - 1, 0, num_steps, dtype=torch.long, device=y.device)

        for i, step in enumerate(step_indices):
            t_batch = torch.full((b,), step, dtype=torch.long, device=y.device)
            predicted_noise = model(x_t, y, t_batch)

            alpha = self.alphas.to(y.device)[step]
            alpha_cumprod = self.alphas_cumprod.to(y.device)[step]

            # DDPM mean update
            coeff1 = 1.0 / torch.sqrt(alpha)
            coeff2 = (1.0 - alpha) / torch.sqrt(1.0 - alpha_cumprod)
            mean = coeff1 * (x_t - coeff2 * predicted_noise)

            if step > 0:
                noise = torch.randn_like(x_t)
                sigma = torch.sqrt(self.betas.to(y.device)[step])
                x_t = mean + sigma * noise * 0.5
            else:
                x_t = mean

        return torch.clamp(x_t, 0.0, 1.0)
