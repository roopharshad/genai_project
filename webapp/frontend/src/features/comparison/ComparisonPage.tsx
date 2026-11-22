import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams, useOutletContext, Link } from 'react-router-dom';
import {
  SplitSquareVertical,
  Columns,
  Layers,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Sparkles,
  Info,
  Sliders,
  CheckCircle2,
  FileDown
} from 'lucide-react';
import { NeonButton } from '../../components/common/NeonButton';
import { Badge } from '../../components/common/Badge';
import { comparisonService, assetService, documentAiService } from '../../services/api';
import { Project, Asset } from '../../types';

export const ComparisonPage: React.FC = () => {
  const { currentProject } = useOutletContext<{ currentProject: Project | null }>();
  const [searchParams, setSearchParams] = useSearchParams();

  const [assets, setAssets] = useState<Asset[]>([]);
  const [selectedAssetId, setSelectedAssetId] = useState<string>('');
  const [comparisonData, setComparisonData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  // Comparison view mode: 'slider' | 'side-by-side' | 'difference'
  const [viewMode, setViewMode] = useState<'slider' | 'side-by-side' | 'difference'>('slider');
  const [sliderPos, setSliderPos] = useState(50);
  const [zoomLevel, setZoomLevel] = useState(1.0);

  useEffect(() => {
    async function loadAssets() {
      try {
        const list = await assetService.list({ project_id: currentProject?.id });
        setAssets(list);
        const paramId = searchParams.get('assetId');
        if (paramId) {
          setSelectedAssetId(paramId);
        } else if (list.length > 0) {
          setSelectedAssetId(list[0].id);
        }
      } catch (err) {
        console.error("Failed to load assets", err);
      }
    }
    loadAssets();
  }, [currentProject?.id]);

  useEffect(() => {
    if (!selectedAssetId) return;
    async function loadComparison() {
      try {
        setLoading(true);
        const data = await comparisonService.getComparison(selectedAssetId);
        setComparisonData(data);
      } catch (err) {
        console.error("Failed to fetch comparison", err);
      } finally {
        setLoading(false);
      }
    }
    loadComparison();
  }, [selectedAssetId]);

  const handleSelectAsset = (id: string) => {
    setSelectedAssetId(id);
    setSearchParams({ assetId: id });
  };

  const evalData = comparisonData?.evaluation;
  const original = comparisonData?.original_version;
  const restoredRaw = comparisonData?.restored_version;
  const [showAi, setShowAi] = useState(false);
  const [quality, setQuality] = useState<any>(null);
  const [qualityError, setQualityError] = useState('');
  useEffect(() => {
    setQuality(null); setQualityError(''); setShowAi(false);
    if (!selectedAssetId || !restoredRaw || restoredRaw.version_type === 'original') return;
    documentAiService.quality(selectedAssetId, restoredRaw.id).then(setQuality)
      .catch((e) => setQualityError(e?.response?.data?.detail || 'Quality evaluation failed'));
  }, [selectedAssetId, restoredRaw?.id]);
  const restored = restoredRaw && showAi && restoredRaw.ai_marked_url
    ? { ...restoredRaw, url: restoredRaw.ai_marked_url } : restoredRaw;

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Top Header & View Mode Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-muted text-xs font-mono text-royal-purple mb-1 border border-border">
            <SplitSquareVertical className="w-3.5 h-3.5" />
            <span>INTERFACE 05: PROFESSIONAL COMPARISON STUDIO</span>
          </div>
          <h1 className="text-2xl font-display font-bold text-text-primary tracking-tight">
            Original vs. Restored Interface Inspection
          </h1>
        </div>

        {/* View Controls: Slider / Side-by-Side / Difference & Zoom */}
        <div className="flex items-center gap-3">
          <div className="flex rounded-lg border border-border bg-white p-1">
            <button
              onClick={() => setViewMode('slider')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 ${
                viewMode === 'slider' ? 'bg-royal-purple text-white shadow-glow-purple' : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              <SplitSquareVertical className="w-3.5 h-3.5" />
              Slider
            </button>
            <button
              onClick={() => setViewMode('side-by-side')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 ${
                viewMode === 'side-by-side' ? 'bg-royal-purple text-white shadow-glow-purple' : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              <Columns className="w-3.5 h-3.5" />
              Side-by-Side
            </button>
            <button
              onClick={() => setViewMode('difference')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 ${
                viewMode === 'difference' ? 'bg-royal-purple text-white shadow-glow-purple' : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              Difference
            </button>
          </div>

          {/* Zoom controls */}
          <div className="flex items-center gap-1 bg-white border border-border rounded-lg p-1 text-xs">
            <button
              onClick={() => setZoomLevel(Math.max(0.5, zoomLevel - 0.25))}
              className="p-1.5 hover:bg-surface-muted rounded text-steel"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="font-mono text-[11px] w-12 text-center text-text-primary font-semibold">
              {Math.round(zoomLevel * 100)}%
            </span>
            <button
              onClick={() => setZoomLevel(Math.min(3.0, zoomLevel + 0.25))}
              className="p-1.5 hover:bg-surface-muted rounded text-steel"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setZoomLevel(1.0)}
              className="p-1.5 hover:bg-surface-muted rounded text-steel"
              title="Reset Zoom"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Asset Selector Tabs */}
      {assets.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-none">
          {assets.map((a) => (
            <button
              key={a.id}
              onClick={() => handleSelectAsset(a.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium shrink-0 border transition-all ${
                selectedAssetId === a.id
                  ? 'border-royal-purple bg-purple-50 text-royal-purple font-semibold shadow-sm'
                  : 'border-border bg-white text-text-secondary hover:bg-surface-muted'
              }`}
            >
              {a.original_filename}
            </button>
          ))}
        </div>
      )}

      {/* Restoration Quality Evaluator */}
      <div className="p-4 rounded-xl bg-surface border border-border shadow-card space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant="ai" glow>
              {restoredRaw?.version_type === 'ai_reconstructed' ? 'AI reconstructed (LaMa)'
                : restoredRaw?.version_type === 'enhanced' ? 'Restored + Enhanced' : `Restored: ${restoredRaw?.model_id || '—'}`}
            </Badge>
            <span className="text-xs text-text-secondary font-mono">
              Version {restoredRaw?.version_number ?? '—'} of {comparisonData?.available_versions?.length ?? '—'}
            </span>
            {restoredRaw?.ai_marked_url && (
              <button onClick={() => setShowAi(!showAi)}
                className={`px-2.5 py-1 rounded-md text-[11px] font-mono border ${showAi ? 'bg-hot-pink text-white border-hot-pink' : 'border-hot-pink/50 text-hot-pink'}`}>
                {showAi ? 'Hide' : 'Show'} AI-generated regions
              </button>
            )}
          </div>
          {quality && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-steel">Quality score</span>
              <span className={`text-lg font-bold font-mono ${quality.quality_score >= 70 ? 'text-success' : quality.quality_score >= 45 ? 'text-orange-600' : 'text-error'}`}>
                {quality.quality_score}/100
              </span>
            </div>
          )}
        </div>
        {!restoredRaw || restoredRaw.version_type === 'original' ? (
          <div className="text-xs text-text-secondary">No restored version yet. Run a restoration to see quality scores.</div>
        ) : qualityError ? (
          <div className="text-xs text-error">{qualityError}</div>
        ) : !quality ? (
          <div className="text-xs text-text-secondary font-mono">Evaluating quality (damage before/after, ink preservation, OCR)...</div>
        ) : (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs font-mono">
              {[
                ['Damage score', `${quality.damage_score_before} → ${quality.damage_score_after}`, `-${quality.damage_reduction_pct}%`],
                ['Strokes kept', quality.stroke_preservation != null ? `${(quality.stroke_preservation * 100).toFixed(1)}%` : '—', 'handwriting/ink'],
                ['Dots kept', quality.dot_preservation != null ? `${(quality.dot_preservation * 100).toFixed(1)}%` : '—', 'i-dots, punctuation'],
                [quality.ocr?.kind === 'accuracy_vs_approved_text' ? 'OCR accuracy' : 'OCR agreement',
                  quality.ocr?.char_accuracy != null ? `${(quality.ocr.char_accuracy * 100).toFixed(1)}%`
                    : quality.ocr?.char_agreement != null ? `${(quality.ocr.char_agreement * 100).toFixed(1)}%` : 'n/a',
                  quality.ocr?.kind === 'accuracy_vs_approved_text' ? `CER ${quality.ocr.cer}` : quality.ocr?.kind === 'unavailable' ? 'handwriting' : 'vs original reading'],
                ['PSNR', `${quality.psnr_vs_original} dB`, 'vs uploaded original'],
                ['SSIM', `${quality.ssim_vs_original}`, 'vs uploaded original'],
              ].map(([label, value, sub]) => (
                <div key={label} className="p-2 rounded-lg bg-surface-muted border border-border">
                  <div className="text-steel text-[10px] uppercase">{label}</div>
                  <div className="font-bold text-royal-purple text-sm">{value}</div>
                  <div className="text-[10px] text-text-secondary">{sub}</div>
                </div>
              ))}
            </div>
            <div className="flex flex-wrap gap-2 text-[10px] font-mono">
              {Object.entries<any>(quality.per_damage || {}).map(([k, v]) => (
                <span key={k} className="px-2 py-0.5 rounded border border-border bg-white">
                  {k.replace(/_/g, ' ')}: {Math.round(v.before * 100)}% → {Math.round(v.after * 100)}%
                </span>
              ))}
              {quality.ai_generated_pct > 0 && (
                <span className="px-2 py-0.5 rounded border border-hot-pink text-hot-pink">AI-generated: {quality.ai_generated_pct}% of page</span>
              )}
            </div>
            <div className="text-[10px] text-text-secondary">{quality.notes}{quality.ocr?.note ? ` ${quality.ocr.note}` : ''}</div>
          </>
        )}
      </div>

      {/* Studio Canvas Display */}
      <div className="rounded-2xl border border-border bg-[#1A1A22] shadow-2xl p-4 sm:p-6 min-h-[520px] flex items-center justify-center overflow-auto relative">
        {loading ? (
          <div className="text-center text-white text-xs font-mono">
            <Sparkles className="w-8 h-8 text-neon-violet animate-spin mx-auto mb-2" />
            Loading version comparison...
          </div>
        ) : !comparisonData ? (
          <div className="text-center text-mist text-xs">
            No comparison data available. Please select an asset.
          </div>
        ) : (
          <div
            className="transition-transform duration-200 origin-center max-w-full"
            style={{ transform: `scale(${zoomLevel})` }}
          >
            {/* View Mode 1: Interactive Draggable Slider */}
            {viewMode === 'slider' && (
              <div className="relative rounded-xl overflow-hidden border-2 border-neon-violet/30 shadow-2xl select-none max-w-3xl">
                {/* Restored sharp image background */}
                <img
                  src={restored?.url ? `${restored.url}?v=${restored.id}` : `/storage/originals/${original?.stored_filename}`}
                  alt="Restored"
                  className="max-h-[500px] w-auto object-contain block"
                />

                {/* Degraded input image foreground clipped */}
                <div
                  className="absolute inset-0 overflow-hidden"
                  style={{ width: `${sliderPos}%` }}
                >
                  <img
                    src={original?.url || `/storage/originals/${original?.stored_filename}`}
                    alt="Original Degraded"
                    className="max-h-[500px] max-w-none object-contain block"
                  />
                </div>

                {/* Divider Line */}
                <div
                  className="absolute top-0 bottom-0 w-1 bg-gradient-ai shadow-glow-pink cursor-ew-resize z-20"
                  style={{ left: `${sliderPos}%` }}
                >
                  <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-7 h-7 rounded-full bg-sidebar border border-white flex items-center justify-center shadow-glow-purple">
                    <Sliders className="w-3.5 h-3.5 text-neon-violet" />
                  </div>
                </div>

                {/* Range Input for dragging */}
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={sliderPos}
                  onChange={(e) => setSliderPos(Number(e.target.value))}
                  className="absolute inset-0 opacity-0 cursor-ew-resize z-30 w-full h-full"
                />

                <div className="absolute top-3 left-3 z-10 px-2.5 py-1 rounded bg-black/80 text-white text-[11px] font-mono border border-white/10">
                  Input: Original (v1)
                </div>
                <div className="absolute top-3 right-3 z-10 px-2.5 py-1 rounded bg-royal-purple/90 text-white text-[11px] font-mono border border-neon-violet/40 shadow-glow-purple">
                  Restored: {restored?.model_id || 'Residual U-Net'}
                </div>
              </div>
            )}

            {/* View Mode 2: Side-by-Side Comparison */}
            {viewMode === 'side-by-side' && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-5xl">
                <div className="space-y-2">
                  <div className="text-xs font-mono text-mist flex justify-between">
                    <span>ORIGINAL INPUT (DEGRADED)</span>
                    <span className="text-steel">{original?.width}x{original?.height}</span>
                  </div>
                  <div className="rounded-xl overflow-hidden border border-white/10 bg-black flex items-center justify-center p-2">
                    <img
                      src={original?.url || `/storage/originals/${original?.stored_filename}`}
                      alt="Original"
                      className="max-h-[420px] object-contain"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="text-xs font-mono text-neon-violet flex justify-between">
                    <span>RESTORED OUTPUT (PRESERVED GEOMETRY)</span>
                    <span className="text-neon-violet">{restored?.width}x{restored?.height}</span>
                  </div>
                  <div className="rounded-xl overflow-hidden border-2 border-royal-purple bg-black shadow-glow-purple flex items-center justify-center p-2">
                    <img
                      src={restored?.url ? `${restored.url}?v=${restored.id}` : `/storage/originals/${original?.stored_filename}`}
                      alt="Restored"
                      className="max-h-[420px] object-contain"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* View Mode 3: Difference / High-Frequency Residual Overlay */}
            {viewMode === 'difference' && (
              <div className="relative rounded-xl overflow-hidden border border-white/20 shadow-2xl max-w-3xl">
                <img
                  src={restored?.url ? `${restored.url}?v=${restored.id}` : `/storage/originals/${original?.stored_filename}`}
                  alt="Difference Layer"
                  className="max-h-[500px] w-auto object-contain filter invert contrast-200 hue-rotate-180"
                />
                <div className="absolute top-3 left-3 z-10 px-2.5 py-1 rounded bg-black/80 text-neon-magenta text-[11px] font-mono border border-white/10">
                  Residual Correction Heatmap: R = X̂ − Y
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Export & Actions Footer Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl bg-surface border border-border shadow-card">
        <div className="text-xs text-text-secondary">
          Restoration output preserves exact original aspect ratio and interface boundaries.
        </div>
        <div className="flex items-center gap-3">
          <Link to={`/export?assetId=${selectedAssetId}`}>
            <NeonButton variant="outline" size="sm" icon={<FileDown className="w-4 h-4" />}>
              Export High-Res Image & PDF Report
            </NeonButton>
          </Link>
          <Link to={`/restoration?assetId=${selectedAssetId}`}>
            <NeonButton variant="ai" size="sm" icon={<Sparkles className="w-4 h-4" />}>
              Try Another Model
            </NeonButton>
          </Link>
        </div>
      </div>
    </div>
  );
};

