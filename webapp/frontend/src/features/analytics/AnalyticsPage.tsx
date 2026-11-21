import React, { useState, useEffect } from 'react';
import { useOutletContext, Link } from 'react-router-dom';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  LineChart,
  Line
} from 'recharts';
import {
  BarChart3,
  CheckCircle2,
  Cpu,
  Layers,
  FileDown,
  Info,
  Clock,
  Sparkles,
  ArrowUpRight,
  TrendingUp,
  ShieldCheck,
  Zap,
  Activity,
  AlertCircle
} from 'lucide-react';
import { Badge } from '../../components/common/Badge';
import { NeonButton } from '../../components/common/NeonButton';
import { analyticsService, reportService } from '../../services/api';
import { Experiment, AnalyticsOverview, Project } from '../../types';

export const AnalyticsPage: React.FC = () => {
  const { currentProject } = useOutletContext<{ currentProject: Project | null }>();
  const [activeTab, setActiveTab] = useState<'project' | 'benchmarks'>('project');
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAnalytics() {
      try {
        setLoading(true);
        const [expData, overviewData] = await Promise.all([
          analyticsService.getExperiments(),
          analyticsService.getOverview(currentProject?.id)
        ]);
        setExperiments(expData);
        setOverview(overviewData);
      } catch (err) {
        console.error("Failed to load analytics data", err);
      } finally {
        setLoading(false);
      }
    }
    loadAnalytics();
  }, [currentProject?.id]);

  // Format chart data from actual experiment benchmark records E1-E9
  const benchmarkChartData = experiments.map((exp) => ({
    code: exp.experiment_code,
    name: exp.name.split(' ')[0] + ' ' + (exp.name.split(' ')[1] || ''),
    psnr: exp.metrics_summary?.psnr ?? 0,
    ssim: exp.metrics_summary?.ssim ? Number((exp.metrics_summary.ssim * 100).toFixed(1)) : 0,
    ocr: exp.metrics_summary?.ocr_word_acc ? Number((exp.metrics_summary.ocr_word_acc * 100).toFixed(1)) : 0,
    edge: exp.metrics_summary?.edge_f1 ? Number((exp.metrics_summary.edge_f1 * 100).toFixed(1)) : 0,
    latency: exp.metrics_summary?.inference_time_ms ?? 0,
  }));

  // Format chart data from live project evaluations by model
  const projectModelChartData = (overview?.model_breakdown || []).map((m) => ({
    name: m.model_name.length > 18 ? m.model_name.slice(0, 16) + '...' : m.model_name,
    psnr: m.avg_psnr ?? 0,
    ssim: m.avg_ssim ? Number((m.avg_ssim * 100).toFixed(1)) : 0,
    ocr: m.avg_ocr ?? 0,
    edge: m.avg_edge ?? 0,
    count: m.count,
    latency: m.avg_latency ?? 0
  }));

  // Format timeline data from actual project runs
  const timelineChartData = (overview?.timeline || []).map((item, idx) => ({
    run: `#${idx + 1} (${item.time})`,
    psnr: item.psnr ?? 0,
    ocr: item.ocr ?? 0,
    ssim: item.ssim ?? 0,
    edge: item.edge ?? 0,
    model: item.model_name
  }));

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-muted text-xs font-mono text-royal-purple mb-1 border border-border">
            <BarChart3 className="w-3.5 h-3.5" />
            <span>INTERFACE 06: RESEARCH & LIVE QUALITY ANALYTICS</span>
          </div>
          <h1 className="text-2xl font-display font-bold text-text-primary tracking-tight">
            Restoration Quality Analytics & Evaluation Hub
          </h1>
          <p className="mt-1 text-sm text-text-secondary">
            {currentProject ? `Active Project: ${currentProject.name} — ` : ''}
            Quantitative evaluation across PSNR, SSIM, LPIPS perceptual distance, OCR word fidelity, and edge preservation.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <a href={reportService.exportCsvUrl(currentProject?.id)} download>
            <NeonButton variant="outline" size="sm" icon={<FileDown className="w-4 h-4" />}>
              Export Metrics CSV
            </NeonButton>
          </a>
        </div>
      </div>

      {/* Tab Switcher: Live Project Quality vs Research Benchmarks */}
      <div className="flex items-center gap-2 p-1 bg-surface-muted border border-border rounded-xl w-fit">
        <button
          type="button"
          onClick={() => setActiveTab('project')}
          className={`px-4 py-2 rounded-lg text-xs font-medium font-display transition-all flex items-center gap-2 ${
            activeTab === 'project'
              ? 'bg-sidebar text-white shadow-glow-purple'
              : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          <Activity className="w-3.5 h-3.5 text-neon-violet" />
          <span>Live Project Quality Analytics</span>
          {overview?.total_evaluations ? (
            <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-royal-purple text-white font-mono">
              {overview.total_evaluations}
            </span>
          ) : null}
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('benchmarks')}
          className={`px-4 py-2 rounded-lg text-xs font-medium font-display transition-all flex items-center gap-2 ${
            activeTab === 'benchmarks'
              ? 'bg-sidebar text-white shadow-glow-purple'
              : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          <Cpu className="w-3.5 h-3.5 text-hot-pink" />
          <span>E1–E9 Research Benchmarks & Ablations</span>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-hot-pink/20 text-hot-pink font-mono">
            {experiments.length}
          </span>
        </button>
      </div>

      {/* SECTION 1: LIVE PROJECT QUALITY ANALYTICS */}
      {activeTab === 'project' && (
        <div className="space-y-8">
          {/* Live Metrics Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            <div className="p-5 rounded-card bg-surface border border-border shadow-card space-y-2">
              <div className="flex items-center justify-between text-xs text-text-secondary">
                <span>Avg Reconstruction PSNR</span>
                <BarChart3 className="w-4 h-4 text-royal-purple" />
              </div>
              <div className="text-2xl font-display font-bold text-text-primary">
                {overview?.avg_psnr != null ? `${overview.avg_psnr} dB` : 'N/A'}
              </div>
              <div className="text-[11px] text-text-secondary">
                {overview?.avg_psnr != null ? 'Computed from paired reference frames' : 'No evaluations recorded yet'}
              </div>
            </div>

            <div className="p-5 rounded-card bg-surface border border-border shadow-card space-y-2">
              <div className="flex items-center justify-between text-xs text-text-secondary">
                <span>Avg Structural Similarity (SSIM)</span>
                <CheckCircle2 className="w-4 h-4 text-success" />
              </div>
              <div className="text-2xl font-display font-bold text-text-primary">
                {overview?.avg_ssim != null ? overview.avg_ssim : 'N/A'}
              </div>
              <div className="text-[11px] text-text-secondary">
                {overview?.avg_ssim != null ? 'Mean structural UI grid fidelity' : 'Awaiting completed jobs'}
              </div>
            </div>

            <div className="p-5 rounded-card bg-surface border border-border shadow-card space-y-2">
              <div className="flex items-center justify-between text-xs text-text-secondary">
                <span>Avg OCR Word Fidelity</span>
                <ShieldCheck className="w-4 h-4 text-neon-violet" />
              </div>
              <div className="text-2xl font-display font-bold text-text-primary">
                {overview?.avg_ocr_word_acc != null ? `${Math.round(overview.avg_ocr_word_acc * 100)}%` : 'N/A'}
              </div>
              <div className="text-[11px] text-text-secondary">
                {overview?.avg_ocr_word_acc != null ? 'Character geometry & readability' : 'No text evaluations yet'}
              </div>
            </div>

            <div className="p-5 rounded-card bg-surface border border-border shadow-card space-y-2">
              <div className="flex items-center justify-between text-xs text-text-secondary">
                <span>Total Live Evaluations</span>
                <Layers className="w-4 h-4 text-royal-blue" />
              </div>
              <div className="text-2xl font-display font-bold text-text-primary">
                {overview?.total_evaluations ?? 0}
              </div>
              <div className="text-[11px] text-text-secondary">
                {overview?.avg_inference_time_ms != null ? `Avg latency: ${overview.avg_inference_time_ms} ms` : 'Jobs evaluated in this project'}
              </div>
            </div>
          </div>

          {/* If No Live Evaluations Exist Yet */}
          {(!overview || overview.total_evaluations === 0) ? (
            <div className="p-12 text-center rounded-card bg-surface border border-dashed border-border shadow-card space-y-4">
              <div className="w-12 h-12 rounded-full bg-surface-muted text-steel flex items-center justify-center mx-auto">
                <AlertCircle className="w-6 h-6" />
              </div>
              <div className="max-w-md mx-auto">
                <h3 className="text-base font-display font-bold text-text-primary">
                  No Live Quality Evaluations Recorded Yet
                </h3>
                <p className="text-xs text-text-secondary mt-1.5 leading-relaxed">
                  When you execute a restoration job in the Restoration Studio, DocRestore AI automatically computes reference-based PSNR, SSIM, LPIPS, OCR text consistency, and Sobel edge preservation scores.
                </p>
                <div className="mt-5 flex justify-center gap-3">
                  <Link to="/restoration">
                    <NeonButton variant="ai" size="sm" icon={<Sparkles className="w-4 h-4" />}>
                      Launch Restoration Studio
                    </NeonButton>
                  </Link>
                  <button
                    type="button"
                    onClick={() => setActiveTab('benchmarks')}
                    className="px-4 py-2 rounded-lg text-xs font-medium border border-border hover:bg-surface-muted transition-colors text-text-primary"
                  >
                    View E1–E9 Research Benchmarks
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <>
              {/* Graphical Visualizations for Live Project */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Chart 1: Model Comparison for this Project */}
                <div className="p-6 rounded-card bg-surface border border-border shadow-card space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-sm font-display font-bold text-text-primary">
                        Model Performance on Project Screenshots
                      </h2>
                      <p className="text-[11px] text-text-secondary">
                        Comparison of models evaluated on your actual uploaded UI screenshots.
                      </p>
                    </div>
                    <Badge variant="ai">Live Data</Badge>
                  </div>
                  <div className="h-72 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={projectModelChartData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#E2E0E8" />
                        <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                        <YAxis tick={{ fontSize: 10 }} domain={[0, 40]} />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#111116', border: '1px solid #333', borderRadius: '8px', color: '#fff', fontSize: '11px' }}
                        />
                        <Legend wrapperStyle={{ fontSize: '11px' }} />
                        <Bar dataKey="psnr" name="PSNR (dB)" fill="#6528E0" radius={[4, 4, 0, 0]} />
                        <Bar dataKey="ocr" name="OCR Acc (%)" fill="#16A36A" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Chart 2: Metric Progression Over Time */}
                <div className="p-6 rounded-card bg-surface border border-border shadow-card space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-sm font-display font-bold text-text-primary">
                        Restoration Quality Progression (Recent Runs)
                      </h2>
                      <p className="text-[11px] text-text-secondary">
                        Tracking PSNR (dB) and OCR Consistency (%) across successive restoration jobs.
                      </p>
                    </div>
                    <Badge variant="success">Fidelity Trend</Badge>
                  </div>
                  <div className="h-72 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={timelineChartData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#E2E0E8" />
                        <XAxis dataKey="run" tick={{ fontSize: 10 }} />
                        <YAxis tick={{ fontSize: 10 }} domain={[0, 100]} />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#111116', border: '1px solid #333', borderRadius: '8px', color: '#fff', fontSize: '11px' }}
                        />
                        <Legend wrapperStyle={{ fontSize: '11px' }} />
                        <Line type="monotone" dataKey="ocr" name="OCR Word Acc (%)" stroke="#16A36A" strokeWidth={2.5} dot={{ r: 4 }} />
                        <Line type="monotone" dataKey="edge" name="Edge Preservation (%)" stroke="#E6007E" strokeWidth={2} dot={{ r: 3 }} />
                        <Line type="monotone" dataKey="psnr" name="PSNR (dB)" stroke="#6528E0" strokeWidth={2} dot={{ r: 3 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>

              {/* Detailed Live Project Evaluations Table */}
              <div className="p-6 rounded-card bg-surface border border-border shadow-card space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-base font-display font-bold text-text-primary">
                      Recent Project Restoration Evaluations
                    </h2>
                    <p className="text-xs text-text-secondary mt-0.5">
                      Empirical evaluation metrics calculated from verified paired UI assets.
                    </p>
                  </div>
                  <Link to="/restoration">
                    <NeonButton variant="outline" size="sm" icon={<Sparkles className="w-4 h-4" />}>
                      Run New Job
                    </NeonButton>
                  </Link>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-border text-steel font-mono text-[11px] uppercase">
                        <th className="py-3 px-3">Date / Time</th>
                        <th className="py-3 px-3">Target Asset</th>
                        <th className="py-3 px-3">Restoration Model</th>
                        <th className="py-3 px-3 text-right">PSNR</th>
                        <th className="py-3 px-3 text-right">SSIM</th>
                        <th className="py-3 px-3 text-right">OCR Word</th>
                        <th className="py-3 px-3 text-right">Edge Score</th>
                        <th className="py-3 px-3 text-right">Latency</th>
                        <th className="py-3 px-3 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {overview.recent_results.map((res) => (
                        <tr key={res.id} className="hover:bg-surface-muted/50 transition-colors">
                          <td className="py-3 px-3 font-mono text-steel">
                            {res.created_at ? new Date(res.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '-'}
                          </td>
                          <td className="py-3 px-3 font-medium text-text-primary">
                            {res.asset_filename || 'UI Screenshot'}
                          </td>
                          <td className="py-3 px-3">
                            <span className="font-semibold text-royal-purple">
                              {res.model_name || res.model_id}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-right font-mono text-text-primary">
                            {res.psnr != null ? `${res.psnr.toFixed(2)} dB` : '-'}
                          </td>
                          <td className="py-3 px-3 text-right font-mono text-text-primary">
                            {res.ssim != null ? res.ssim.toFixed(4) : '-'}
                          </td>
                          <td className="py-3 px-3 text-right font-mono text-success">
                            {res.ocr_word_acc != null ? `${Math.round(res.ocr_word_acc * 100)}%` : '-'}
                          </td>
                          <td className="py-3 px-3 text-right font-mono text-hot-pink">
                            {res.edge_score != null ? `${Math.round(res.edge_score * 100)}%` : '-'}
                          </td>
                          <td className="py-3 px-3 text-right font-mono text-steel">
                            {res.inference_time_ms != null ? `${res.inference_time_ms.toFixed(1)} ms` : '-'}
                          </td>
                          <td className="py-3 px-3 text-right">
                            <Link
                              to="/comparison"
                              className="text-xs text-royal-purple font-semibold hover:underline inline-flex items-center gap-1"
                            >
                              Inspect <ArrowUpRight className="w-3 h-3" />
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* SECTION 2: E1–E9 RESEARCH BENCHMARKS & ABLATIONS */}
      {activeTab === 'benchmarks' && (
        <div className="space-y-8">
          {/* Evaluation Ethics & Reference Rule Alert */}
          <div className="p-4 rounded-xl bg-purple-50/50 border border-royal-purple/30 text-xs text-text-primary flex items-start gap-3">
            <Info className="w-4 h-4 text-royal-purple shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-royal-purple">Strict Research Evaluation Protocol (Section 5.2):</div>
              <p className="text-text-secondary text-[11px] mt-0.5 leading-relaxed">
                PSNR, SSIM, and LPIPS are only computed when a verified paired reference screenshot exists. Degradation parameters and model checkpoints are recorded as reproducible metadata. No metrics or accuracy numbers are fabricated.
              </p>
            </div>
          </div>

          {/* Recharts Graphical Visualizations */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Chart 1: PSNR & SSIM Across Architectures */}
            <div className="p-6 rounded-card bg-surface border border-border shadow-card space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-display font-bold text-text-primary">Reconstruction Fidelity (PSNR & SSIM)</h2>
                  <p className="text-[11px] text-text-secondary">Higher is better. Demonstrates Residual U-Net, GFPGAN, and Hybrid Diffusion lead.</p>
                </div>
                <Badge variant="ai">E1–E9</Badge>
              </div>
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={benchmarkChartData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E2E0E8" />
                    <XAxis dataKey="code" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} domain={[20, 35]} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#111116', border: '1px solid #333', borderRadius: '8px', color: '#fff', fontSize: '11px' }}
                    />
                    <Legend wrapperStyle={{ fontSize: '11px' }} />
                    <Bar dataKey="psnr" name="PSNR (dB)" fill="#6528E0" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Chart 2: OCR Word Accuracy & Edge Preservation F1 */}
            <div className="p-6 rounded-card bg-surface border border-border shadow-card space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-display font-bold text-text-primary">Interface Integrity (OCR & Edge F1 %)</h2>
                  <p className="text-[11px] text-text-secondary">Measures preservation of text characters and button boundaries.</p>
                </div>
                <Badge variant="success">Preservation</Badge>
              </div>
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={benchmarkChartData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E2E0E8" />
                    <XAxis dataKey="code" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} domain={[50, 100]} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#111116', border: '1px solid #333', borderRadius: '8px', color: '#fff', fontSize: '11px' }}
                    />
                    <Legend wrapperStyle={{ fontSize: '11px' }} />
                    <Line type="monotone" dataKey="ocr" name="OCR Word Acc (%)" stroke="#16A36A" strokeWidth={2.5} dot={{ r: 4 }} />
                    <Line type="monotone" dataKey="edge" name="Edge F1 (%)" stroke="#E6007E" strokeWidth={2.5} dot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Comprehensive Experiment & Ablation Table */}
          <div className="p-6 rounded-card bg-surface border border-border shadow-card space-y-4">
            <div>
              <h2 className="text-base font-display font-bold text-text-primary">Formal Experiment Record Table (E1 – E9)</h2>
              <p className="text-xs text-text-secondary mt-0.5">
                Full research breakdown verifying ablations between L1, L1+SSIM, the combined UI-Aware loss, and GFPGAN Generative Feature Prior.
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-border text-steel font-mono text-[11px] uppercase">
                    <th className="py-3 px-3">Code</th>
                    <th className="py-3 px-3">Experiment & Architecture</th>
                    <th className="py-3 px-3">Loss / Formulation</th>
                    <th className="py-3 px-3 text-right">PSNR</th>
                    <th className="py-3 px-3 text-right">SSIM</th>
                    <th className="py-3 px-3 text-right">LPIPS</th>
                    <th className="py-3 px-3 text-right">OCR Word</th>
                    <th className="py-3 px-3 text-right">Edge F1</th>
                    <th className="py-3 px-3 text-right">Latency</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {experiments.map((exp) => {
                    const isPrimary = exp.experiment_code === 'E5';
                    const isGfpgan = exp.experiment_code === 'E9';
                    const m = exp.metrics_summary || {};
                    return (
                      <tr
                        key={exp.id}
                        className={`transition-colors ${
                          isPrimary
                            ? 'bg-purple-50/60 font-semibold'
                            : isGfpgan
                            ? 'bg-hot-pink/5 font-medium'
                            : 'hover:bg-surface-muted/40'
                        }`}
                      >
                        <td className="py-3 px-3 font-mono text-royal-purple">{exp.experiment_code}</td>
                        <td className="py-3 px-3">
                          <div className="font-medium text-text-primary flex items-center gap-1.5">
                            {exp.name}
                            {isPrimary && (
                              <span className="text-[9px] bg-royal-purple text-white px-1.5 py-0.2 rounded font-mono">
                                PRIMARY
                              </span>
                            )}
                            {isGfpgan && (
                              <span className="text-[9px] bg-hot-pink text-white px-1.5 py-0.2 rounded font-mono">
                                FEATURE PRIOR
                              </span>
                            )}
                          </div>
                          <div className="text-[10px] text-text-secondary line-clamp-1">{exp.description}</div>
                        </td>
                        <td className="py-3 px-3 font-mono text-[11px] text-text-secondary">
                          {exp.hyperparameters?.loss || exp.model_id}
                        </td>
                        <td className="py-3 px-3 text-right font-mono text-text-primary">
                          {m.psnr ? `${m.psnr} dB` : '-'}
                        </td>
                        <td className="py-3 px-3 text-right font-mono text-text-primary">
                          {m.ssim ? m.ssim : '-'}
                        </td>
                        <td className="py-3 px-3 text-right font-mono text-text-primary">
                          {m.lpips ? m.lpips : '-'}
                        </td>
                        <td className="py-3 px-3 text-right font-mono text-success">
                          {m.ocr_word_acc ? `${Math.round(m.ocr_word_acc * 100)}%` : '-'}
                        </td>
                        <td className="py-3 px-3 text-right font-mono text-hot-pink">
                          {m.edge_f1 ? `${Math.round(m.edge_f1 * 100)}%` : '-'}
                        </td>
                        <td className="py-3 px-3 text-right font-mono text-steel">
                          {m.inference_time_ms ? `${m.inference_time_ms} ms` : '-'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
