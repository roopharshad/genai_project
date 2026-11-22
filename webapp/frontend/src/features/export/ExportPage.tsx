import React, { useState, useEffect } from 'react';
import { useOutletContext, useSearchParams } from 'react-router-dom';
import {
  FileDown,
  FileText,
  Image as ImageIcon,
  CheckCircle2,
  AlertCircle,
  Download,
  Share2,
  Table
} from 'lucide-react';
import { NeonButton } from '../../components/common/NeonButton';
import { Badge } from '../../components/common/Badge';
import { reportService, assetService, comparisonService } from '../../services/api';
import { Project, Asset } from '../../types';

/** Fetch a file with the login token and save it under `filename`. */
async function downloadFile(url: string, filename: string) {
  const token = localStorage.getItem('docrestore_token');
  const res = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!res.ok) {
    let msg = `Download failed (HTTP ${res.status})`;
    try { msg = (await res.json()).detail || msg; } catch { /* not JSON */ }
    throw new Error(msg);
  }
  const blob = await res.blob();
  const href = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = href;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(href), 2000);
}

const baseName = (name?: string) => (name || 'document').replace(/\.[^.]+$/, '');

export const ExportPage: React.FC = () => {
  const { currentProject } = useOutletContext<{ currentProject: Project | null }>();
  const [searchParams] = useSearchParams();

  const [assets, setAssets] = useState<Asset[]>([]);
  const [selectedAssetId, setSelectedAssetId] = useState<string>('');
  const [comparison, setComparison] = useState<any>(null);
  const [generatingPdf, setGeneratingPdf] = useState(false);
  const [generatedPdfUrl, setGeneratedPdfUrl] = useState<string | null>(null);
  const [reportsList, setReportsList] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const [aList, rList] = await Promise.all([
          assetService.list({ project_id: currentProject?.id }),
          reportService.list(currentProject?.id)
        ]);
        setAssets(aList);
        setReportsList(rList);

        const paramId = searchParams.get('assetId');
        if (paramId) {
          setSelectedAssetId(paramId);
        } else if (aList.length > 0) {
          setSelectedAssetId(aList[0].id);
        }
      } catch (err) {
        console.error("Error loading export assets", err);
      }
    }
    loadData();
  }, [currentProject?.id]);

  useEffect(() => {
    if (!selectedAssetId) return;
    comparisonService.getComparison(selectedAssetId).then(setComparison).catch(() => {});
  }, [selectedAssetId]);

  const [generatedReport, setGeneratedReport] = useState<any>(null);
  const [downloading, setDownloading] = useState<string | null>(null);

  const run = async (key: string, fn: () => Promise<void>) => {
    try {
      setDownloading(key);
      setError(null);
      await fn();
    } catch (err: any) {
      setError(err?.message || 'Download failed.');
    } finally {
      setDownloading(null);
    }
  };

  const downloadReport = (r: any) => run(`report-${r.id}`, () =>
    downloadFile(`/api/v1/reports/${r.id}/download`, `${(r.title || 'report').replace(/[^\w\- ]+/g, '_')}.${(r.stored_filename || '').endsWith('.pdf') ? 'pdf' : 'txt'}`));

  const handleGeneratePdfReport = async () => {
    if (!currentProject) return;
    try {
      setGeneratingPdf(true);
      setError(null);
      const res = await reportService.generatePdf(
        currentProject.id,
        `${currentProject.name} — Quality Evaluation Report`
      );
      setGeneratedPdfUrl(res.download_url);
      setGeneratedReport(res);
      setReportsList(prev => [res, ...prev]);
      await downloadFile(`/api/v1/reports/${res.id}/download`, `${baseName(currentProject.name)}_quality_report.pdf`);
    } catch (err: any) {
      setError(err?.message || "Failed to generate PDF report.");
    } finally {
      setGeneratingPdf(false);
    }
  };

  const handleExportConfigJson = () => {
    if (!comparison) return;
    const configData = {
      project_name: currentProject?.name,
      asset: comparison.asset,
      original_version: comparison.original_version,
      restored_version: comparison.restored_version,
      evaluation_metrics: comparison.evaluation,
      exported_at: new Date().toISOString()
    };
    const blob = new Blob([JSON.stringify(configData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `restoration_config_${selectedAssetId.slice(0, 8)}.json`;
    a.click();
  };

  const restored = comparison?.restored_version;

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-muted text-xs font-mono text-royal-purple mb-1 border border-border">
          <FileDown className="w-3.5 h-3.5" />
          <span>INTERFACE 08: ADVANCED EXPORT STUDIO</span>
        </div>
        <h1 className="text-2xl font-display font-bold text-text-primary tracking-tight">
          Export Restored Assets & Evaluation Reports
        </h1>
        <p className="mt-1 text-sm text-text-secondary">
          Export full-resolution restored PNG/JPEG screenshots, research evaluation PDFs, and CSV datasets.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-error/10 border border-error/30 text-error text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Export Options Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Option 1: Restored Screenshot Image */}
        <div className="p-6 rounded-card bg-surface border border-border shadow-card flex flex-col justify-between space-y-4">
          <div>
            <div className="w-10 h-10 rounded-xl bg-royal-purple/10 text-royal-purple flex items-center justify-center mb-3">
              <ImageIcon className="w-5 h-5" />
            </div>
            <h2 className="text-sm font-display font-bold text-text-primary">Restored Image Output</h2>
            <p className="text-xs text-text-secondary mt-1">
              Download lossless restored screenshot in full resolution.
            </p>
            {restored && (
              <div className="mt-3 text-[11px] font-mono text-steel space-y-1">
                <div>Version: <span className="font-semibold text-text-primary">{restored.version_type === 'enhanced' ? 'Restored + Enhanced' : restored.version_type === 'ai_reconstructed' ? 'AI reconstructed' : restored.version_type === 'original' ? 'Original (not restored yet)' : 'Restored'}</span></div>
                <div>Dimensions: <span className="text-text-primary">{restored.width} × {restored.height} px</span></div>
              </div>
            )}
          </div>
          <div>
            <NeonButton
              variant="primary" size="md" className="w-full"
              disabled={!restored || restored.version_type === 'original' || downloading === 'image'}
              icon={<Download className="w-4 h-4" />}
              onClick={() => run('image', () => downloadFile(restored.url, `restored_${baseName(comparison?.asset?.original_filename)}.png`))}
            >
              {restored && restored.version_type === 'original' ? 'Restore this document first'
                : downloading === 'image' ? 'Downloading...' : 'Download PNG Output'}
            </NeonButton>
          </div>
        </div>

        {/* Option 2: Quality Evaluation PDF Report */}
        <div className="p-6 rounded-card bg-surface border border-border shadow-card flex flex-col justify-between space-y-4">
          <div>
            <div className="w-10 h-10 rounded-xl bg-fuchsia-brand/10 text-hot-pink flex items-center justify-center mb-3">
              <FileText className="w-5 h-5" />
            </div>
            <h2 className="text-sm font-display font-bold text-text-primary">Formal Evaluation PDF</h2>
            <p className="text-xs text-text-secondary mt-1">
              Generates printable report containing PSNR, SSIM, OCR accuracy, and E1–E8 benchmark tables.
            </p>
            {generatedPdfUrl && (
              <div className="mt-3 text-xs text-success flex items-center gap-1.5 font-medium">
                <CheckCircle2 className="w-4 h-4" /> PDF generated and ready
              </div>
            )}
          </div>
          <div>
            {generatedPdfUrl && generatedReport ? (
              <NeonButton variant="ai" size="md" className="w-full" icon={<Download className="w-4 h-4" />}
                disabled={downloading === `report-${generatedReport.id}`}
                onClick={() => downloadReport(generatedReport)}>
                Download PDF Report
              </NeonButton>
            ) : (
              <NeonButton
                variant="ai"
                size="md"
                className="w-full"
                disabled={generatingPdf || !currentProject}
                onClick={handleGeneratePdfReport}
                icon={<FileDown className="w-4 h-4" />}
              >
                {generatingPdf ? 'Compiling PDF Report...' : 'Generate PDF Report'}
              </NeonButton>
            )}
          </div>
        </div>

        {/* Option 3: Metrics CSV Dataset */}
        <div className="p-6 rounded-card bg-surface border border-border shadow-card flex flex-col justify-between space-y-4">
          <div>
            <div className="w-10 h-10 rounded-xl bg-success/10 text-success flex items-center justify-center mb-3">
              <Table className="w-5 h-5" />
            </div>
            <h2 className="text-sm font-display font-bold text-text-primary">Evaluation Metrics CSV</h2>
            <p className="text-xs text-text-secondary mt-1">
              Raw tabular data including per-job inference latency, edge scores, and character accuracies.
            </p>
          </div>
          <div className="space-y-2">
            <NeonButton variant="outline" size="md" className="w-full" icon={<Download className="w-4 h-4" />}
              disabled={downloading === 'csv'}
              onClick={() => run('csv', () => downloadFile(reportService.exportCsvUrl(currentProject?.id), 'docrestore_evaluation_metrics.csv'))}>
              {downloading === 'csv' ? 'Exporting...' : 'Export Metrics CSV'}
            </NeonButton>
            <button
              onClick={handleExportConfigJson}
              disabled={!comparison}
              className="w-full text-center text-xs text-royal-purple font-medium hover:underline py-1"
            >
              Export Config JSON
            </button>
          </div>
        </div>
      </div>

      {/* Previously Generated Reports List */}
      <div className="p-6 rounded-card bg-surface border border-border shadow-card space-y-4">
        <h3 className="text-sm font-display font-bold text-text-primary">Archived Generated Reports</h3>
        {reportsList.length === 0 ? (
          <p className="text-xs text-text-secondary">No PDF reports generated yet for this project.</p>
        ) : (
          <div className="divide-y divide-border">
            {reportsList.map((r, i) => (
              <div key={r.id || i} className="py-3 flex items-center justify-between text-xs">
                <div className="flex items-center gap-3">
                  <FileText className="w-4 h-4 text-royal-purple" />
                  <div>
                    <div className="font-semibold text-text-primary">{r.title || 'Quality Evaluation Report'}</div>
                    <div className="text-[11px] text-steel font-mono">{r.stored_filename || r.filename}</div>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => downloadReport(r)}
                  disabled={downloading === `report-${r.id}`}
                  title="Download report"
                  className="p-2 hover:bg-surface-muted rounded text-royal-purple disabled:opacity-50"
                >
                  <Download className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

