import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, useOutletContext, Link } from 'react-router-dom';
import {
  Sparkles,
  Cpu,
  Layers,
  Sliders,
  CheckCircle2,
  AlertCircle,
  Play,
  RotateCcw,
  Zap,
  ArrowRight,
  Boxes
} from 'lucide-react';
import { NeonButton } from '../../components/common/NeonButton';
import { Badge } from '../../components/common/Badge';
import { restorationService, assetService } from '../../services/api';
import { Project, Asset, RestorationModel, RestorationJob } from '../../types';

export const RestorationPage: React.FC = () => {
  const { currentProject } = useOutletContext<{ currentProject: Project | null }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const currentUser = (() => {
    try {
      const stored = localStorage.getItem('docrestore_user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  })();
  const isPlatformAdmin = currentUser?.role === 'administrator' || currentUser?.role === 'platform_admin';

  const [advancedMode, setAdvancedMode] = useState(false);
  const [models, setModels] = useState<RestorationModel[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [selectedAssetId, setSelectedAssetId] = useState<string>('');
  const [selectedModelId, setSelectedModelId] = useState<string>('recommended');
  const [activeJob, setActiveJob] = useState<RestorationJob | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Dynamic parameters state
  const [paramsState, setParamsState] = useState<Record<string, any>>({
    blend_ratio: 1.0,
    base_channels: 48,
    sampling_steps: 15,
    unsharp_strength: 1.4,
  });

  useEffect(() => {
    async function loadData() {
      try {
        const [mList, aList] = await Promise.all([
          restorationService.getModels(),
          assetService.list({ project_id: currentProject?.id })
        ]);
        setModels(mList);
        setAssets(aList);

        const paramAssetId = searchParams.get('assetId');
        if (paramAssetId) {
          setSelectedAssetId(paramAssetId);
        } else if (aList.length > 0) {
          setSelectedAssetId(aList[0].id);
        }
      } catch (err) {
        console.error("Failed to load models or assets", err);
      }
    }
    loadData();
  }, [currentProject?.id, searchParams]);

  // Poll active job status
  useEffect(() => {
    if (!activeJob || activeJob.status === 'completed' || activeJob.status === 'failed') {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const updated = await restorationService.getJob(activeJob.id);
        setActiveJob(updated);
        if (updated.status === 'completed') {
          clearInterval(interval);
        }
      } catch (e) {
        console.error("Polling error", e);
      }
    }, 1200);

    return () => clearInterval(interval);
  }, [activeJob]);

  const handleSubmitJob = async () => {
    if (!selectedAssetId || !currentProject) {
      setError("Please select a target screenshot asset.");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const job = await restorationService.submitJob({
        project_id: currentProject.id,
        asset_id: selectedAssetId,
        model_id: selectedModelId,
        config_params: paramsState
      });
      setActiveJob(job);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to submit restoration job.");
    } finally {
      setLoading(false);
    }
  };

  const selectedModel = models.find(m => m.id === selectedModelId) || models[0];
  const selectedAsset = assets.find(a => a.id === selectedAssetId);

  const targetParams = !advancedMode
    ? (selectedModelId === 'recommended'
        ? [{ name: 'blend_ratio', label: 'Restoration Strength', type: 'float', default: 1.0, min: 0.5, max: 2.0 }]
        : (selectedModelId === 'gfpgan_prior'
            ? [{ name: 'blend_ratio', label: 'Prior Weight', type: 'float', default: 1.0, min: 0.5, max: 1.5 }]
            : (selectedModelId === 'balanced'
                ? [{ name: 'unsharp_strength', label: 'Edge Boost', type: 'float', default: 1.4, min: 1.0, max: 2.5 }]
                : [{ name: 'sampling_steps', label: 'Diffusion Steps', type: 'int', default: 15, min: 5, max: 30 }]
              )
          )
      )
    : (selectedModel?.parameters || []);

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sidebar text-xs font-mono text-white mb-2 border border-neon-violet/30 shadow-glow-purple">
          <Sparkles className="w-3.5 h-3.5 text-hot-pink" />
          <span>INTERFACE 04: ADVANCED AI RESTORATION CONTROLS</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-display font-bold text-text-primary tracking-tight">
          Configure & Launch AI Restoration Engine
        </h1>
        <p className="mt-1 text-sm text-text-secondary">
          Choose between UI-Aware Residual U-Net, Conditional Diffusion, or benchmark baselines to restore software screenshots.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-error/10 border border-error/30 text-error text-xs flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Main Grid: Selection & Configuration */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Left Column: Model Selection (2 Cols on lg) */}
        <div className="lg:col-span-2 space-y-6">
          {/* Target Asset Selector Card */}
          <div className="p-6 rounded-card bg-surface border border-border shadow-card space-y-4">
            <h2 className="text-sm font-display font-bold text-text-primary">1. Select Target Legacy Screenshot</h2>
            {assets.length === 0 ? (
              <div className="p-6 text-center border border-dashed border-border rounded-xl text-xs text-text-secondary">
                No screenshots found in current project.
                <div className="mt-2">
                  <Link to="/upload">
                    <NeonButton variant="outline" size="sm">Upload a Screenshot</NeonButton>
                  </Link>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {assets.map((asset) => (
                  <button
                    key={asset.id}
                    onClick={() => setSelectedAssetId(asset.id)}
                    className={`p-3 rounded-xl border text-left flex items-center gap-3 transition-all ${
                      selectedAssetId === asset.id
                        ? 'border-royal-purple bg-purple-50/50 shadow-card-hover ring-2 ring-royal-purple/20'
                        : 'border-border bg-white hover:bg-surface-muted'
                    }`}
                  >
                    <div className="w-12 h-12 rounded-lg bg-sidebar overflow-hidden shrink-0 flex items-center justify-center">
                      <img
                        src={`/storage/thumbnails/thumb_${asset.stored_filename}`}
                        alt={asset.original_filename}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          // Fallback to direct original if thumbnail missing
                          (e.target as HTMLImageElement).src = `/storage/originals/${asset.stored_filename}`;
                        }}
                      />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-xs font-semibold text-text-primary truncate">{asset.original_filename}</div>
                      <div className="text-[10px] text-steel font-mono">{asset.width}x{asset.height} • {asset.resolution_category}</div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Preset / Model Selector Cards */}
          <div className="p-6 rounded-card bg-surface border border-border shadow-card space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-display font-bold text-text-primary">
                  {advancedMode ? '2. Select Technical Architecture (Admin Mode)' : '2. Select Restoration Quality Preset'}
                </h2>
                <p className="text-xs text-text-secondary mt-0.5">
                  {advancedMode
                    ? 'Direct access to all 6 neural and classical research architectures.'
                    : 'Choose an optimized restoration preset tailored for software documentation.'}
                </p>
              </div>

              {isPlatformAdmin && (
                <button
                  type="button"
                  onClick={() => {
                    const next = !advancedMode;
                    setAdvancedMode(next);
                    setSelectedModelId(next ? 'residual_unet' : 'recommended');
                  }}
                  className="px-2.5 py-1 rounded-lg text-xs font-mono font-medium border border-neon-violet/30 text-neon-violet hover:bg-neon-violet/10 transition-colors"
                >
                  {advancedMode ? '← Switch to Presets' : 'Advanced Model Mode →'}
                </button>
              )}
            </div>

            {!advancedMode ? (
              /* User-Friendly Presets (Default for all normal users) */
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {[
                  {
                    id: 'recommended',
                    name: 'Recommended',
                    badge: 'Optimal Fidelity',
                    is_primary: true,
                    desc: 'UI-Aware Residual U-Net. Best overall quality for software documentation. Preserves text readability, character geometry, and sharp button borders.',
                    icon: <Cpu className="w-4 h-4 text-neon-violet" />
                  },
                  {
                    id: 'gfpgan_prior',
                    name: 'GFPGAN Feature Prior',
                    badge: 'Generative Prior',
                    is_primary: false,
                    desc: 'Generative Feature Prior GAN with StyleGAN2 SFT modulation to synthesize high-frequency UI details, crisp icons, and clear typography.',
                    icon: <Sparkles className="w-4 h-4 text-royal-purple" />
                  },
                  {
                    id: 'balanced',
                    name: 'Balanced',
                    badge: 'Ultra Fast',
                    is_primary: false,
                    desc: 'Fast baseline restoration. Rapid bilateral smoothing and unsharp edge sharpening for quick batch cleanups.',
                    icon: <Zap className="w-4 h-4 text-royal-purple" />
                  },
                  {
                    id: 'high_quality',
                    name: 'High Quality',
                    badge: 'Generative AI',
                    is_primary: false,
                    desc: 'Conditional diffusion generative restoration. Synthesizes fine sub-pixel interface details and resolves extreme compression blur.',
                    icon: <Sparkles className="w-4 h-4 text-hot-pink" />
                  }
                ].map((preset) => (
                  <button
                    key={preset.id}
                    type="button"
                    onClick={() => setSelectedModelId(preset.id)}
                    className={`p-4 rounded-xl border text-left transition-all relative ${
                      selectedModelId === preset.id
                        ? 'border-royal-purple bg-sidebar text-white shadow-glow-purple ring-2 ring-neon-violet/30'
                        : 'border-border bg-white hover:border-royal-purple/40 text-text-primary'
                    }`}
                  >
                    <span className={`absolute top-2 right-2 text-[9px] px-1.5 py-0.2 rounded font-mono uppercase font-bold ${
                      preset.is_primary ? 'bg-royal-purple text-white' : 'bg-surface-muted text-text-secondary border border-border'
                    }`}>
                      {preset.badge}
                    </span>
                    <div className="flex items-center gap-2 mb-1.5">
                      {preset.icon}
                      <span className="text-xs font-bold font-display">{preset.name}</span>
                    </div>
                    <p className={`text-[11px] leading-relaxed ${selectedModelId === preset.id ? 'text-mist' : 'text-text-secondary'}`}>
                      {preset.desc}
                    </p>
                  </button>
                ))}
              </div>
            ) : (
              /* Technical 6-Model Catalogue (Platform Administrators Only) */
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {models.map((m) => (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => setSelectedModelId(m.id)}
                    className={`p-4 rounded-xl border text-left transition-all relative ${
                      selectedModelId === m.id
                        ? 'border-royal-purple bg-sidebar text-white shadow-glow-purple ring-2 ring-neon-violet/30'
                        : 'border-border bg-white hover:border-royal-purple/40 text-text-primary'
                    }`}
                  >
                    {m.is_primary && (
                      <span className="absolute top-2 right-2 text-[9px] px-1.5 py-0.2 rounded bg-royal-purple text-white font-mono uppercase font-bold">
                        Primary
                      </span>
                    )}
                    <div className="flex items-center gap-2 mb-1.5">
                      {m.id === 'residual_unet' && <Cpu className="w-4 h-4 text-neon-violet" />}
                      {m.id === 'conditional_diffusion' && <Sparkles className="w-4 h-4 text-hot-pink" />}
                      {m.id === 'residual_diffusion' && <Layers className="w-4 h-4 text-laser-blue" />}
                      {m.id === 'realesrgan' && <Boxes className="w-4 h-4 text-steel" />}
                      {m.id === 'srcnn' && <Sliders className="w-4 h-4 text-steel" />}
                      {m.id === 'opencv' && <Zap className="w-4 h-4 text-steel" />}
                      <span className="text-xs font-bold font-display">{m.name}</span>
                    </div>
                    <p className={`text-[11px] line-clamp-2 ${selectedModelId === m.id ? 'text-mist' : 'text-text-secondary'}`}>
                      {m.purpose}
                    </p>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Hyperparameter Tuning & Execution */}
        <div className="space-y-6">
          {/* Configuration Card */}
          <div className="p-6 rounded-card bg-surface border border-border shadow-card space-y-4">
            <h2 className="text-sm font-display font-bold text-text-primary flex items-center gap-2">
              <Sliders className="w-4 h-4 text-royal-purple" />
              Restoration Parameters
            </h2>

            {targetParams && targetParams.length > 0 ? (
              <div className="space-y-4">
                {targetParams.map((p) => (
                  <div key={p.name} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="font-semibold text-text-primary">{p.label}</span>
                      <span className="font-mono text-royal-purple">{paramsState[p.name] ?? p.default}</span>
                    </div>
                    {p.type === 'int' || p.type === 'float' ? (
                      <input
                        type="range"
                        min={p.min ?? 1}
                        max={p.max ?? 64}
                        step={p.type === 'float' ? 0.1 : 1}
                        value={paramsState[p.name] ?? p.default}
                        onChange={(e) => setParamsState({ ...paramsState, [p.name]: Number(e.target.value) })}
                        className="w-full"
                      />
                    ) : null}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-text-secondary">
                This model operates with standardized baseline weights. No hyperparameter tuning required.
              </p>
            )}

            <div className="pt-3 border-t border-border">
              <NeonButton
                variant="ai"
                size="lg"
                className="w-full"
                disabled={loading || (activeJob !== null && activeJob.status !== 'completed' && activeJob.status !== 'failed')}
                onClick={handleSubmitJob}
                icon={<Play className="w-4 h-4 fill-white" />}
              >
                {loading ? 'Submitting Job...' : 'Execute Restoration Job'}
              </NeonButton>
            </div>
          </div>

          {/* Real Measurable Job Lifecycle Stepper */}
          {activeJob && (
            <div className="p-6 rounded-card bg-sidebar text-white border border-sidebar-panel shadow-glow-purple space-y-4">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-steel">JOB: {activeJob.id.slice(0, 8)}...</span>
                <span className="text-neon-violet font-semibold uppercase">{activeJob.status}</span>
              </div>

              {/* Progress Bar */}
              <div className="space-y-1">
                <div className="w-full bg-sidebar-panel rounded-full h-2.5 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-brand transition-all duration-300"
                    style={{ width: `${activeJob.progress}%` }}
                  />
                </div>
                <div className="flex justify-between text-[10px] text-steel font-mono">
                  <span>{activeJob.stage}</span>
                  <span>{activeJob.progress}%</span>
                </div>
              </div>

              {/* Measurable Stages */}
              <div className="space-y-2 pt-2 text-xs font-mono">
                <div className={`flex items-center gap-2 ${activeJob.progress >= 15 ? 'text-success' : 'text-steel'}`}>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Validation & Image Analysis</span>
                </div>
                <div className={`flex items-center gap-2 ${activeJob.progress >= 40 ? 'text-success' : 'text-steel'}`}>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Model Inference ({activeJob.model_name})</span>
                </div>
                <div className={`flex items-center gap-2 ${activeJob.progress >= 75 ? 'text-success' : 'text-steel'}`}>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Version Creation & Storage</span>
                </div>
                <div className={`flex items-center gap-2 ${activeJob.progress >= 90 ? 'text-success' : 'text-steel'}`}>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>PSNR, SSIM & Edge Evaluation</span>
                </div>
              </div>

              {/* Completion Action */}
              {activeJob.status === 'completed' && (
                <div className="pt-3 border-t border-white/10">
                  <NeonButton
                    variant="primary"
                    size="sm"
                    className="w-full"
                    onClick={() => navigate(`/comparison?assetId=${activeJob.asset_id}`)}
                    icon={<ArrowRight className="w-4 h-4" />}
                  >
                    Open in Comparison Studio →
                  </NeonButton>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

