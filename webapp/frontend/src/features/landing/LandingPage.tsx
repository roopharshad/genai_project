import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Sparkles,
  ArrowRight,
  Cpu,
  Layers,
  CheckCircle2,
  Sliders,
  ShieldCheck,
  Zap,
  BarChart2,
  FileText,
  ScanText,
  Boxes,
  LogIn,
  UserPlus
} from 'lucide-react';
import { NeonButton } from '../../components/common/NeonButton';

export const LandingPage: React.FC = () => {
  const [sliderPos, setSliderPos] = useState(52);

  return (
    <div className="min-h-screen bg-sidebar text-white selection:bg-neon-violet selection:text-white">
      {/* Top Navbar */}
      <header className="border-b border-sidebar-panel sticky top-0 z-50 bg-sidebar/90 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-brand flex items-center justify-center shadow-glow-purple">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-display font-bold text-xl tracking-tight text-white">
                DocRestore <span className="text-neon-violet">AI</span>
              </span>
              <div className="text-[10px] text-steel font-mono tracking-widest uppercase">
                Legacy UI Asset Restorer
              </div>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-mist">
            <a href="#demo" className="hover:text-white transition-colors">Interactive Demo</a>
            <a href="#models" className="hover:text-white transition-colors">ML Architecture</a>
            <a href="#pipeline" className="hover:text-white transition-colors">Restoration Pipeline</a>
            <a href="#benchmarks" className="hover:text-white transition-colors">Evaluation & OCR</a>
          </nav>

          <div className="flex items-center gap-3">
            <Link
              to="/login"
              className="text-xs font-semibold text-mist hover:text-white transition-colors px-3 py-2 rounded-lg hover:bg-white/5 flex items-center gap-1.5"
            >
              <LogIn className="w-3.5 h-3.5 text-neon-violet" />
              Sign In
            </Link>
            <Link to="/register">
              <NeonButton variant="primary" size="sm" glow={true} icon={<UserPlus className="w-3.5 h-3.5" />}>
                Create Account
              </NeonButton>
            </Link>
            <Link to="/dashboard">
              <NeonButton variant="outline-dark" size="sm" glow={false} icon={<ArrowRight className="w-4 h-4" />}>
                Launch Studio
              </NeonButton>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative pt-20 pb-28 overflow-hidden bg-gradient-to-b from-sidebar via-[#171720] to-sidebar">
        {/* Extreme Neon Ambient Glow Backdrops */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[350px] bg-royal-purple/25 rounded-full blur-[140px] pointer-events-none" />
        <div className="absolute top-1/3 left-1/4 w-[450px] h-[300px] bg-laser-blue/20 rounded-full blur-[120px] pointer-events-none" />
        <div className="absolute top-1/3 right-1/4 w-[450px] h-[300px] bg-fuchsia-brand/20 rounded-full blur-[120px] pointer-events-none" />

        <div className="max-w-7xl mx-auto px-6 relative z-10 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-sidebar-panel border border-neon-violet/40 text-xs font-mono text-mist mb-8 shadow-glow-purple">
            <Sparkles className="w-3.5 h-3.5 text-hot-pink animate-pulse" />
            <span>Advanced Hybrid Deep Learning + Generative AI</span>
          </div>

          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-display font-extrabold tracking-tight text-white max-w-5xl mx-auto leading-[1.08]">
            Restore Legacy UI Screenshots with{' '}
            <span className="bg-gradient-brand bg-clip-text text-transparent">
              Pixel-Perfect Geometry
            </span>
          </h1>

          <p className="mt-6 text-lg sm:text-xl text-mist max-w-3xl mx-auto font-normal leading-relaxed">
            DocRestore AI rescues blurred, degraded, and compressed legacy software interfaces for documentation, manuals, and enterprise knowledge bases. Prioritizing text readability, sharp buttons, and interface boundaries.
          </p>

          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Link to="/register">
              <NeonButton variant="ai" size="lg" glow={true} icon={<UserPlus className="w-5 h-5" />}>
                Get Started Free
              </NeonButton>
            </Link>
            <Link to="/login">
              <NeonButton
                variant="outline-dark"
                size="lg"
                glow={true}
                className="border-neon-violet/60 text-white bg-sidebar-panel hover:bg-sidebar-panel/80 hover:border-laser-blue"
                icon={<LogIn className="w-5 h-5 text-neon-violet" />}
              >
                Sign In
              </NeonButton>
            </Link>
            <Link to="/dashboard">
              <NeonButton variant="primary" size="lg" icon={<ArrowRight className="w-5 h-5" />}>
                Live Studio Demo
              </NeonButton>
            </Link>
          </div>

          {/* Key Feature Badges */}
          <div className="mt-14 grid grid-cols-2 sm:grid-cols-4 gap-4 max-w-4xl mx-auto text-left">
            <div className="p-4 rounded-xl bg-sidebar-panel/80 border border-white/5">
              <ScanText className="w-5 h-5 text-laser-blue mb-2" />
              <div className="text-xs font-semibold text-white">OCR Consistency</div>
              <div className="text-[11px] text-steel">Character & word fidelity preserved</div>
            </div>
            <div className="p-4 rounded-xl bg-sidebar-panel/80 border border-white/5">
              <Cpu className="w-5 h-5 text-neon-violet mb-2" />
              <div className="text-xs font-semibold text-white">UI-Aware Residual U-Net</div>
              <div className="text-[11px] text-steel">Predicts correction R = F_theta(Y)</div>
            </div>
            <div className="p-4 rounded-xl bg-sidebar-panel/80 border border-white/5">
              <Boxes className="w-5 h-5 text-hot-pink mb-2" />
              <div className="text-xs font-semibold text-white">Conditional Diffusion</div>
              <div className="text-[11px] text-steel">Pixel-space generative fine details</div>
            </div>
            <div className="p-4 rounded-xl bg-sidebar-panel/80 border border-white/5">
              <BarChart2 className="w-5 h-5 text-success mb-2" />
              <div className="text-xs font-semibold text-white">Reference-Based Metrics</div>
              <div className="text-[11px] text-steel">Verified PSNR, SSIM, LPIPS, Edge F1</div>
            </div>
          </div>
        </div>
      </section>

      {/* Interactive Before / After Comparison Showcase */}
      <section id="demo" className="py-20 bg-[#16161D] border-y border-white/5 relative">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-display font-bold text-white tracking-tight">
              Interactive Restoration Studio Showcase
            </h2>
            <p className="mt-2 text-sm text-mist max-w-2xl mx-auto">
              Drag the slider to compare synthetic degraded screenshot against the restored output produced by the UI-Aware Residual U-Net.
            </p>
          </div>

          {/* Interactive Split View Slider */}
          <div className="relative w-full max-w-4xl mx-auto aspect-[4/3] sm:aspect-[16/10] rounded-2xl overflow-hidden shadow-2xl border-2 border-neon-violet/40 select-none">
            {/* Background: Restored Sharp UI */}
            <div className="absolute inset-0 bg-[#E0DFE5] flex items-center justify-center p-6">
              <div className="w-full h-full bg-[#C0C0C0] rounded border-2 border-black p-4 flex flex-col justify-between shadow-lg">
                <div className="bg-[#000080] text-white px-3 py-1.5 font-bold text-sm flex justify-between items-center">
                  <span>Legacy Database Connection Manager (Restored 4K Definition)</span>
                  <div className="flex gap-1">
                    <span className="w-3 h-3 bg-[#C0C0C0] border border-black inline-block text-[9px] text-black font-bold text-center leading-3">_</span>
                    <span className="w-3 h-3 bg-[#C0C0C0] border border-black inline-block text-[9px] text-black font-bold text-center leading-3">X</span>
                  </div>
                </div>
                <div className="p-4 bg-white border border-gray-600 space-y-3 font-mono text-xs text-black">
                  <div className="font-bold text-blue-900 border-b pb-1">RESTORED INTERFACE GEOMETRY [UI-AWARE RESIDUAL U-NET]</div>
                  <div>Host: <span className="font-bold text-green-700">srv-alpha01.internal.corp.net:5432</span></div>
                  <div>Target Namespace: <span className="font-bold text-purple-700">SYS_DOCS_ARCHIVE_1998</span></div>
                  <div>Protocol: <span className="font-bold text-gray-800">Kerberos v5 / NTLMv2 [Active]</span></div>
                  <div className="p-2 bg-green-50 border border-green-300 text-green-900 rounded">
                    [METRICS] PSNR: 30.68 dB | SSIM: 0.9184 | OCR Word Accuracy: 89.4% | Edge F1: 0.876
                  </div>
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <div className="px-5 py-1.5 bg-[#C0C0C0] border-2 border-t-white border-l-white border-b-black border-r-black text-black font-bold text-xs">
                    Execute
                  </div>
                  <div className="px-5 py-1.5 bg-[#000080] text-white font-bold text-xs border border-black">
                    OK
                  </div>
                </div>
              </div>
            </div>

            {/* Foreground: Degraded UI Clipped by slider */}
            <div
              className="absolute inset-0 overflow-hidden pointer-events-none"
              style={{ width: `${sliderPos}%` }}
            >
              <div className="w-full h-full bg-[#9E9E9E] flex items-center justify-center p-6 filter blur-[2px] contrast-75">
                <div className="w-full h-full bg-[#A8A8A8] rounded border border-gray-800 p-4 flex flex-col justify-between">
                  <div className="bg-[#101050] text-gray-300 px-3 py-1.5 font-bold text-sm">
                    Legacy Database Connection Manager (Degraded JPEG / Blur)
                  </div>
                  <div className="p-4 bg-gray-200 border border-gray-500 space-y-3 font-mono text-xs text-gray-800">
                    <div className="font-bold text-gray-600">INPUT DEGRADED SCREENSHOT Y = D(J(N(H(X))))</div>
                    <div>Host: srv-alpha01.internal.corp.net:5432</div>
                    <div>Target Namespace: SYS_DOCS_ARCHIVE_1998</div>
                    <div>Protocol: Kerberos v5 / NTLMv2 [Active]</div>
                    <div className="p-2 bg-gray-300 text-gray-700">
                      [BLUR DETECTED] Laplacian Var: 94.2 | Noise: 11.4 | High-freq loss
                    </div>
                  </div>
                  <div className="flex justify-end gap-3 pt-2">
                    <div className="px-5 py-1.5 bg-gray-400 text-gray-800 text-xs">Execute</div>
                    <div className="px-5 py-1.5 bg-gray-500 text-gray-300 text-xs">OK</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Split Drag Line & Handle */}
            <div
              className="absolute top-0 bottom-0 w-1 bg-gradient-ai shadow-glow-pink cursor-ew-resize z-30"
              style={{ left: `${sliderPos}%` }}
            >
              <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-8 h-8 rounded-full bg-sidebar border-2 border-white flex items-center justify-center shadow-glow-purple text-[10px] font-bold text-white">
                <Sliders className="w-4 h-4 text-neon-violet" />
              </div>
            </div>

            {/* Hidden Input for Touch/Drag Slider */}
            <input
              type="range"
              min="0"
              max="100"
              value={sliderPos}
              onChange={(e) => setSliderPos(Number(e.target.value))}
              className="absolute inset-0 opacity-0 cursor-ew-resize z-40 w-full h-full"
            />

            {/* Badges on preview */}
            <div className="absolute top-4 left-4 z-20 px-3 py-1 rounded bg-black/80 backdrop-blur text-white text-xs font-mono border border-white/10">
              Input: Degraded Screenshot (Y)
            </div>
            <div className="absolute top-4 right-4 z-20 px-3 py-1 rounded bg-royal-purple/90 backdrop-blur text-white text-xs font-mono border border-neon-violet/40 shadow-glow-purple">
              Restored: Residual U-Net (X̂)
            </div>
          </div>
        </div>
      </section>

      {/* Model Hierarchy Section */}
      <section id="models" className="py-24 bg-sidebar">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <span className="text-xs font-mono uppercase text-neon-violet tracking-widest">Model Hierarchy</span>
            <h2 className="mt-3 text-3xl sm:text-4xl font-display font-bold text-white tracking-tight">
              Six Specialized Restoration & Benchmark Engines
            </h2>
            <p className="mt-4 text-sm text-mist">
              Each model maintains a discrete implementation, configuration, and evaluation pipeline without mixing results.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Model 1: Residual U-Net */}
            <div className="p-6 rounded-card bg-sidebar-panel border-2 border-royal-purple/60 relative overflow-hidden shadow-card-hover group">
              <div className="absolute top-0 right-0 px-3 py-1 bg-royal-purple text-white text-[10px] font-mono font-bold uppercase rounded-bl-lg">
                Primary Model
              </div>
              <div className="w-10 h-10 rounded-xl bg-royal-purple/20 flex items-center justify-center text-neon-violet mb-4">
                <Cpu className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-display font-bold text-white">UI-Aware Residual U-Net</h3>
              <p className="mt-2 text-xs text-mist leading-relaxed">
                Predicts a residual correction R = F_theta(Y) rather than reconstructing from scratch. Optimized with combined loss (L1 + SSIM + Sobel edge).
              </p>
              <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between text-xs font-mono text-steel">
                <span>Loss: Combined UI-Aware</span>
                <span className="text-neon-violet font-semibold">PSNR: 30.68 dB</span>
              </div>
            </div>

            {/* Model 2: Conditional Diffusion */}
            <div className="p-6 rounded-card bg-sidebar-panel border border-white/10 hover:border-fuchsia-brand/40 transition-all">
              <div className="w-10 h-10 rounded-xl bg-fuchsia-brand/20 flex items-center justify-center text-hot-pink mb-4">
                <Sparkles className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-display font-bold text-white">Conditional Pixel Diffusion</h3>
              <p className="mt-2 text-xs text-mist leading-relaxed">
                Pixel-space diffusion model conditioned on degraded screenshot Y. Recovers complex high-frequency details and icon textures through reverse sampling.
              </p>
              <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between text-xs font-mono text-steel">
                <span>Type: Generative Diffusion</span>
                <span className="text-hot-pink font-semibold">LPIPS: 0.104</span>
              </div>
            </div>

            {/* Model 3: Residual-Conditioned Diffusion */}
            <div className="p-6 rounded-card bg-sidebar-panel border border-white/10 hover:border-laser-blue/40 transition-all">
              <div className="w-10 h-10 rounded-xl bg-laser-blue/20 flex items-center justify-center text-laser-blue mb-4">
                <Layers className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-display font-bold text-white">Residual-Conditioned Diffusion</h3>
              <p className="mt-2 text-xs text-mist leading-relaxed">
                Advanced hybrid model: Takes U-Net base prediction U(Y) and trains diffusion to synthesize the residual error R = X - U(Y) for ultra-fine UI resolution.
              </p>
              <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between text-xs font-mono text-steel">
                <span>Type: Hybrid Experimental</span>
                <span className="text-laser-blue font-semibold">PSNR: 31.05 dB</span>
              </div>
            </div>

            {/* Model 4: Real-ESRGAN */}
            <div className="p-6 rounded-card bg-sidebar-panel border border-white/10">
              <div className="w-10 h-10 rounded-xl bg-surface-muted/10 flex items-center justify-center text-mist mb-4">
                <Boxes className="w-5 h-5 text-white" />
              </div>
              <h3 className="text-lg font-display font-bold text-white">Real-ESRGAN Benchmark</h3>
              <p className="mt-2 text-xs text-mist leading-relaxed">
                Residual-in-Residual Dense Block architecture used as an advanced super-resolution benchmark for fine edge evaluation.
              </p>
              <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between text-xs font-mono text-steel">
                <span>Type: Comparison Model</span>
                <span className="text-white">SSIM: 0.895</span>
              </div>
            </div>

            {/* Model 5: SRCNN */}
            <div className="p-6 rounded-card bg-sidebar-panel border border-white/10">
              <div className="w-10 h-10 rounded-xl bg-surface-muted/10 flex items-center justify-center text-mist mb-4">
                <Sliders className="w-5 h-5 text-white" />
              </div>
              <h3 className="text-lg font-display font-bold text-white">SRCNN Baseline</h3>
              <p className="mt-2 text-xs text-mist leading-relaxed">
                Classic 3-layer Convolutional Neural Network super-resolution baseline providing historical deep learning benchmark comparisons.
              </p>
              <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between text-xs font-mono text-steel">
                <span>Type: Classical CNN</span>
                <span className="text-white">PSNR: 26.85 dB</span>
              </div>
            </div>

            {/* Model 6: OpenCV */}
            <div className="p-6 rounded-card bg-sidebar-panel border border-white/10">
              <div className="w-10 h-10 rounded-xl bg-surface-muted/10 flex items-center justify-center text-mist mb-4">
                <Zap className="w-5 h-5 text-white" />
              </div>
              <h3 className="text-lg font-display font-bold text-white">OpenCV Classical Baseline</h3>
              <p className="mt-2 text-xs text-mist leading-relaxed">
                Bilateral filtering, unsharp masking, and morphological edge sharpening representing traditional non-neural image processing.
              </p>
              <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between text-xs font-mono text-steel">
                <span>Type: Classical Baseline</span>
                <span className="text-white">Latency: 14.2 ms</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-sidebar-panel bg-sidebar py-12 text-center text-xs text-steel font-mono">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-success inline-block" />
            <span>DocRestore AI — Approved Royal Spectrum Specification</span>
          </div>
          <div>
            PyTorch 2.15 • FastAPI • PostgreSQL • React • Vite
          </div>
        </div>
      </footer>
    </div>
  );
};

