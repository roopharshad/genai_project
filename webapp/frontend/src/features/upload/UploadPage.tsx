import React, { useState, useRef } from 'react';
import { useNavigate, useOutletContext } from 'react-router-dom';
import {
  UploadCloud,
  FileImage,
  AlertCircle,
  CheckCircle2,
  Sparkles,
  Sliders,
  Eye,
  Info,
  RefreshCw,
  Layers
} from 'lucide-react';
import { NeonButton } from '../../components/common/NeonButton';
import { Badge } from '../../components/common/Badge';
import { assetService } from '../../services/api';
import { Project, Asset } from '../../types';

export const UploadPage: React.FC = () => {
  const { currentProject } = useOutletContext<{ currentProject: Project | null }>();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadedAsset, setUploadedAsset] = useState<Asset | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Synthetic degradation generation states
  const [showSyntheticControls, setShowSyntheticControls] = useState(false);
  const [blurStrength, setBlurStrength] = useState(1.8);
  const [noiseLevel, setNoiseLevel] = useState(14.0);
  const [jpegQuality, setJpegQuality] = useState(38);
  const [downsampleFactor, setDownsampleFactor] = useState(2.0);
  const [generatingVariant, setGeneratingVariant] = useState(false);
  const [syntheticSuccess, setSyntheticSuccess] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const extOk = /\.(png|jpe?g|jfif|webp|bmp|tiff?)$/i.test(file.name);
      if (!file.type.startsWith('image/') && !extOk) {
        setError('Please select a valid image file (PNG, JPG/JPEG, WebP, BMP, TIFF).');
        return;
      }
      if (file.size > 25 * 1024 * 1024) {
        setError('File size exceeds the 25 MB maximum limit.');
        return;
      }
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setUploadedAsset(null);
      setSyntheticSuccess(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !currentProject) {
      setError('Please select a screenshot and ensure an active project is chosen.');
      return;
    }

    try {
      setUploading(true);
      setError(null);
      const asset = await assetService.upload(currentProject.id, selectedFile);
      setUploadedAsset(asset);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to upload screenshot. Please verify file content.');
    } finally {
      setUploading(false);
    }
  };

  const handleCreateSyntheticDegraded = async () => {
    if (!uploadedAsset) return;
    try {
      setGeneratingVariant(true);
      const res = await assetService.syntheticDegrade(uploadedAsset.id, {
        blur_strength: blurStrength,
        noise_level: noiseLevel,
        jpeg_quality: jpegQuality,
        downsample_factor: downsampleFactor,
        seed: 42
      });
      setSyntheticSuccess(`Generated controlled degraded variant (v${res.version_id.slice(0, 6)}) with formula Y = D(J(N(H(X))))`);
    } catch (err: any) {
      setError('Failed to generate synthetic degraded variant.');
    } finally {
      setGeneratingVariant(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-muted text-xs font-mono text-royal-purple mb-2 border border-border">
          <UploadCloud className="w-3.5 h-3.5" />
          <span>INTERFACE 03: ADVANCED IMPORT WORKSPACE</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-display font-bold text-text-primary tracking-tight">
          Upload & Inspect Legacy Screenshot
        </h1>
        <p className="mt-1 text-sm text-text-secondary">
          Upload degraded, compressed or legacy UI captures. The system analyzes blur, noise level, and interface edge density.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-error/10 border border-error/30 text-error text-xs flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Upload & Preview Split Area */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
        {/* Upload Dropzone */}
        <div className="p-6 rounded-card bg-surface border border-border shadow-card space-y-6">
          <div
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-border-strong hover:border-royal-purple/60 rounded-2xl p-10 text-center cursor-pointer transition-all hover:bg-surface-muted/50 group select-none"
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*,.jpg,.jpeg,.jfif,.png,.webp,.bmp,.tif,.tiff"
              onChange={handleFileChange}
              className="hidden"
            />
            <div className="w-14 h-14 rounded-2xl bg-royal-purple/10 text-royal-purple flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform">
              <UploadCloud className="w-7 h-7" />
            </div>
            <div className="text-sm font-semibold text-text-primary">
              {selectedFile ? selectedFile.name : 'Click or Drag & Drop Screenshot'}
            </div>
            <p className="text-xs text-text-secondary mt-1">
              Supports PNG, JPG/JPEG, WebP, BMP, TIFF up to 25 MB
            </p>
            {selectedFile && (
              <div className="mt-3 text-[11px] font-mono text-royal-purple bg-purple-50 inline-block px-2.5 py-1 rounded-full">
                {(selectedFile.size / 1024).toFixed(1)} KB • {selectedFile.type}
              </div>
            )}
          </div>

          <div className="flex items-center justify-between pt-2">
            <div className="text-xs text-steel font-mono">
              Target Project: <span className="font-semibold text-text-primary">{currentProject?.name || 'Default'}</span>
            </div>
            <NeonButton
              variant="primary"
              size="md"
              disabled={!selectedFile || uploading}
              onClick={handleUpload}
              icon={<Sparkles className="w-4 h-4" />}
            >
              {uploading ? 'Analyzing Image...' : 'Upload & Analyze Asset'}
            </NeonButton>
          </div>
        </div>

        {/* Preview & Initial Image Analysis Card */}
        <div className="p-6 rounded-card bg-surface border border-border shadow-card space-y-5">
          <div className="flex items-center justify-between pb-3 border-b border-border">
            <h2 className="text-sm font-display font-bold text-text-primary flex items-center gap-2">
              <Eye className="w-4 h-4 text-royal-purple" />
              Screenshot Preview & Property Analysis
            </h2>
            {uploadedAsset && <Badge variant="success">Stored in PostgreSQL</Badge>}
          </div>

          {previewUrl ? (
            <div className="space-y-4">
              <div className="w-full aspect-video rounded-xl overflow-hidden bg-slate-900 border border-border flex items-center justify-center p-2 relative">
                <img
                  src={previewUrl}
                  alt="Preview"
                  className="max-h-full max-w-full object-contain rounded"
                />
              </div>

              {/* Degradation Analysis Badges if uploaded */}
              {uploadedAsset?.degradation_analysis && (
                <div className="p-4 rounded-xl bg-surface-muted border border-border space-y-3">
                  <div className="text-xs font-mono uppercase text-steel font-semibold flex items-center gap-1.5">
                    <Info className="w-3.5 h-3.5 text-neon-violet" />
                    Automated UI Degradation Diagnostics
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="bg-white p-2.5 rounded-lg border border-border">
                      <div className="text-steel font-mono text-[11px]">Laplacian Blur Score</div>
                      <div className="font-bold text-text-primary mt-0.5">
                        {uploadedAsset.degradation_analysis.blur_metric_laplacian_var}
                        <span className="text-[10px] text-steel font-normal ml-1">
                          {uploadedAsset.degradation_analysis.blur_metric_laplacian_var < 120 ? '(Blurry)' : '(Sharp)'}
                        </span>
                      </div>
                    </div>
                    <div className="bg-white p-2.5 rounded-lg border border-border">
                      <div className="text-steel font-mono text-[11px]">Noise Standard Dev</div>
                      <div className="font-bold text-text-primary mt-0.5">
                        {uploadedAsset.degradation_analysis.noise_standard_deviation} σ
                      </div>
                    </div>
                    <div className="bg-white p-2.5 rounded-lg border border-border">
                      <div className="text-steel font-mono text-[11px]">Interface Edge Density</div>
                      <div className="font-bold text-text-primary mt-0.5">
                        {(uploadedAsset.degradation_analysis.edge_density_ratio * 100).toFixed(2)}%
                      </div>
                    </div>
                    <div className="bg-white p-2.5 rounded-lg border border-border">
                      <div className="text-steel font-mono text-[11px]">Recommended Model</div>
                      <div className="font-bold text-royal-purple uppercase mt-0.5 font-mono text-[11px]">
                        {uploadedAsset.degradation_analysis.recommended_model}
                      </div>
                    </div>
                  </div>

                  {/* Direct transition to Restoration Studio */}
                  <div className="pt-2">
                    <NeonButton
                      variant="ai"
                      size="sm"
                      className="w-full"
                      onClick={() => navigate(`/restoration?assetId=${uploadedAsset.id}`)}
                      icon={<Sparkles className="w-4 h-4" />}
                    >
                      Configure & Restore This Screenshot →
                    </NeonButton>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="h-64 flex flex-col items-center justify-center text-center p-6 text-text-secondary border border-dashed border-border rounded-xl">
              <FileImage className="w-10 h-10 text-steel mb-2 opacity-50" />
              <div className="text-xs">No screenshot selected yet.</div>
              <p className="text-[11px] text-steel mt-1">Select an image on the left to inspect its resolution and degradation metrics.</p>
            </div>
          )}
        </div>
      </div>

      {/* Synthetic Degradation Generation Studio */}
      {uploadedAsset && (
        <div className="p-6 rounded-card bg-surface border border-border shadow-card space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-display font-bold text-text-primary flex items-center gap-2">
                <Sliders className="w-4 h-4 text-hot-pink" />
                Controlled Synthetic Degradation Generator
              </h3>
              <p className="text-xs text-text-secondary mt-0.5">
                Generate paired training/evaluation variants using formula <code>Y = D(J(N(H(X))))</code> with reproducible seed.
              </p>
            </div>
            <button
              onClick={() => setShowSyntheticControls(!showSyntheticControls)}
              className="text-xs font-semibold text-royal-purple hover:underline"
            >
              {showSyntheticControls ? 'Hide Controls' : 'Open Degradation Tool'}
            </button>
          </div>

          {syntheticSuccess && (
            <div className="p-3 rounded-lg bg-success/15 border border-success/30 text-success text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{syntheticSuccess}</span>
            </div>
          )}

          {showSyntheticControls && (
            <div className="p-4 rounded-xl bg-surface-muted border border-border space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
                <div>
                  <label className="font-semibold text-text-primary block mb-1">
                    Gaussian Blur (H): {blurStrength} σ
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="5.0"
                    step="0.1"
                    value={blurStrength}
                    onChange={(e) => setBlurStrength(Number(e.target.value))}
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="font-semibold text-text-primary block mb-1">
                    Noise Level (N): {noiseLevel} σ
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="35.0"
                    step="1.0"
                    value={noiseLevel}
                    onChange={(e) => setNoiseLevel(Number(e.target.value))}
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="font-semibold text-text-primary block mb-1">
                    JPEG Quality (J): {jpegQuality}%
                  </label>
                  <input
                    type="range"
                    min="10"
                    max="90"
                    step="5"
                    value={jpegQuality}
                    onChange={(e) => setJpegQuality(Number(e.target.value))}
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="font-semibold text-text-primary block mb-1">
                    Downsample Factor (D): {downsampleFactor}x
                  </label>
                  <input
                    type="range"
                    min="1.0"
                    max="4.0"
                    step="0.5"
                    value={downsampleFactor}
                    onChange={(e) => setDownsampleFactor(Number(e.target.value))}
                    className="w-full"
                  />
                </div>
              </div>

              <div className="pt-2 flex justify-end">
                <NeonButton
                  variant="outline"
                  size="sm"
                  disabled={generatingVariant}
                  onClick={handleCreateSyntheticDegraded}
                  icon={<RefreshCw className={`w-3.5 h-3.5 ${generatingVariant ? 'animate-spin' : ''}`} />}
                >
                  {generatingVariant ? 'Generating Variant...' : 'Generate Controlled Paired Variant'}
                </NeonButton>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

