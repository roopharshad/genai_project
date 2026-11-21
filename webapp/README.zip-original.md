# DocRestore AI — Legacy UI Asset Restorer

**DocRestore AI** is an advanced AI-powered web platform designed specifically to restore degraded, blurred, compressed, and low-resolution screenshots of software user interfaces for technical documentation, user guides, enterprise knowledge bases, and software archives.

---

## 1. Visual Identity & Design System: Royal Spectrum

DocRestore AI strictly follows the approved **Royal Spectrum** design specification:
- **Palette:** Royal Spectrum (C) with extreme neon accents
- **Layout:** Asymmetric Hybrid — Pure black navigation (`#111116`) + Creamy-white working surfaces (`#FFFDF8`)
- **Brand Hex Accents:**
  - Cream White: `#FFFDF8`
  - Pure Black: `#111116`
  - Graphite: `#24242D`
  - Royal Blue: `#155EEF`
  - Royal Purple: `#6528E0`
  - Neon Violet: `#873CFF`
  - Fuchsia: `#E6007E`
  - Hot Pink: `#FF28A8`
- **Typography:** Display: `Space Grotesk`, Interface: `Inter`, Technical/Code: `JetBrains Mono`

---

## 2. Complete ML Architecture & Formulation

DocRestore AI combines deep learning and generative diffusion models tailored for interface geometry and text preservation:

### 2.1 Controlled Degradation Pipeline
$$Y = D(J(N(H(X))))$$
- $H$: Gaussian / Motion blur
- $N$: Zero-mean Gaussian noise injection
- $J$: JPEG compression quantization
- $D$: Downsampling & resolution reduction

### 2.2 Primary Model: UI-Aware Residual U-Net
Rather than hallucinating ungrounded pixels, the model predicts a bounded correction to the input degraded screenshot:
$$R = F_\theta(Y)$$
$$\hat{X} = Y + F_\theta(Y)$$
**Combined UI-Aware Loss Function:**
$$\mathcal{L}_{U-Net} = \lambda_1 L_1 + \lambda_2 (1 - \text{SSIM}) + \lambda_3 L_{edge}$$
Where $L_{edge}$ computes Mean Absolute Error of horizontal and vertical Sobel gradient boundary responses to preserve buttons, dialogue borders, and separators.

### 2.3 Generative Model: Conditional Pixel Diffusion
Pixel-space diffusion model conditioned directly on degraded screenshot $Y$:
- Forward diffusion: $q(X_t | X_0) = \mathcal{N}(\sqrt{\bar{\alpha}_t} X_0, (1 - \bar{\alpha}_t) \mathbf{I})$
- Reverse sampling loop predicting added noise $\epsilon_\theta(X_t, Y, t)$
- Recovers fine interface texture and micro-typography.

### 2.4 Experimental Model: Residual-Conditioned Diffusion
1. Obtains base prediction from Residual U-Net: $U(Y)$
2. Computes residual: $R = X - U(Y)$
3. Diffusion model predicts fine residual correction: $\hat{R}$
4. Final reconstruction: $\hat{X} = U(Y) + \hat{R}$

### 2.5 Baselines and Benchmark Models
- **Real-ESRGAN**: Residual-in-Residual Dense Block comparison model.
- **SRCNN**: 3-layer Convolutional Neural Network super-resolution baseline.
- **OpenCV**: Bilateral filtering + unsharp masking + morphological edge sharpening.

---

## 3. The 9 Core Interfaces

1. **Interface 01 — Landing Page: Immersive AI Hero** (`/`)  
   Interactive split-slider showcase, architecture breakdown, and Royal Spectrum brand gradient.
2. **Interface 02 — Dashboard: Advanced Asymmetric Hybrid Dashboard** (`/dashboard`)  
   Active project statistics, recent restoration jobs, measurable stage tracking, and quick actions.
3. **Interface 03 — Upload & Import: Advanced Import Workspace** (`/upload`)  
   Drag-and-drop file upload, Laplacian blur score, noise estimation, and synthetic degradation generator ($Y = D(J(N(H(X)))))$.
4. **Interface 04 — Restoration Workspace: Advanced AI Controls** (`/restoration`)  
   Model selector (Residual U-Net [Primary], Conditional Diffusion, etc.), parameter sliders, real-time stage progress stepper.
5. **Interface 05 — Comparison Studio: Professional Comparison Studio** (`/comparison`)  
   Split draggable slider, side-by-side view, difference overlay, interactive zoom (100%–300%), and reference-based metrics badges.
6. **Interface 06 — Quality Analytics: Research-Oriented Analytics** (`/analytics`)  
   Recharts graphical visualizations, research experiment table E1 through E8, and loss ablation study.
7. **Interface 07 — Asset Library: Professional Asset Manager** (`/library`)  
   Resolution filters, filename search, asset deletion, and multi-version history drawer.
8. **Interface 08 — Export & Reports: Advanced Export Studio** (`/export`)  
   Lossless PNG download, ReportLab PDF generation, metrics CSV export, and configuration JSON.
9. **Interface 09 — Settings & Profile: Professional Settings** (`/settings`)  
   User profile, workspace members & RBAC, extreme neon glow toggles, and system runtime health.

---

## 4. Evaluation Protocol (Section 5.2)

- **PSNR, SSIM, and LPIPS** are calculated and presented **only** when a valid reference screenshot exists.
- **OCR Consistency**: Character error rate, word accuracy, and text region preservation.
- **Edge Preservation**: Sobel gradient Pearson correlation and Canny edge F1-score.
- Operational metrics: Inference latency (ms), model memory (MB), and checkpoint size.
- **No fabricated metrics**: All results are derived from real execution records.

---

## 5. Technology Stack

- **Frontend:** React 18, TypeScript, Vite 6, Tailwind CSS, Lucide React, Recharts, Axios.
- **Backend:** Python 3.13, FastAPI, SQLAlchemy 2.0, Pydantic v2, PyJWT, Argon2, ReportLab, Pillow, OpenCV, scikit-image.
- **ML Framework:** PyTorch 2.15 (CPU/CUDA ready).
- **Database:** PostgreSQL (with SQLite zero-config local fallback).

---

## 6. Getting Started

### 6.1 Backend Setup
```bash
cd backend
python -m pip install -r requirements.txt
python -m pytest tests/ -v
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 6.2 Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173` to explore the complete DocRestore AI platform.

