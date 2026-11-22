import React, { useEffect, useRef, useState } from 'react';
import { useOutletContext, useSearchParams } from 'react-router-dom';
import {
  ScanSearch, FileText, MessageSquare, Wand2, AlertCircle, CheckCircle2, Loader2, Send, Save, Download, RefreshCw,
  XCircle, Sparkles
} from 'lucide-react';
import { NeonButton } from '../../components/common/NeonButton';
import { assetService, documentAiService } from '../../services/api';
import { Asset, Project } from '../../types';

type Tab = 'damage' | 'ocr' | 'chat' | 'reconstruct';

const LEVEL_STYLE: Record<string, string> = {
  none: 'bg-success/10 text-success border-success/30',
  mild: 'bg-yellow-50 text-yellow-700 border-yellow-300',
  moderate: 'bg-orange-50 text-orange-700 border-orange-300',
  severe: 'bg-error/10 text-error border-error/30',
};

const errText = (e: any) => e?.response?.data?.detail || e?.message || 'Request failed';

export const DocumentAIPage: React.FC = () => {
  const { currentProject } = useOutletContext<{ currentProject: Project | null }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [assets, setAssets] = useState<Asset[]>([]);
  const [assetId, setAssetId] = useState('');
  const [tab, setTab] = useState<Tab>((searchParams.get('tab') as Tab) || 'damage');
  const [status, setStatus] = useState<any>(null);

  useEffect(() => {
    documentAiService.status().then(setStatus).catch(() => {});
    assetService.list({ project_id: currentProject?.id }).then((list) => {
      setAssets(list);
      setAssetId(searchParams.get('assetId') || list[0]?.id || '');
    });
  }, [currentProject?.id]);

  const select = (id: string) => {
    setAssetId(id);
    setSearchParams({ assetId: id, tab });
  };

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: 'damage', label: 'Damage & Model Plan', icon: <ScanSearch className="w-4 h-4" /> },
    { id: 'ocr', label: 'OCR Review', icon: <FileText className="w-4 h-4" /> },
    { id: 'chat', label: 'Document Chat', icon: <MessageSquare className="w-4 h-4" /> },
    { id: 'reconstruct', label: 'AI Reconstruction', icon: <Wand2 className="w-4 h-4" /> },
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sidebar text-xs font-mono text-white mb-2 border border-neon-violet/30 shadow-glow-purple">
          <Sparkles className="w-3.5 h-3.5 text-hot-pink" />
          <span>DOCUMENT AI STUDIO</span>
        </div>
        <h1 className="text-2xl font-display font-bold text-text-primary tracking-tight">Analyse, Read and Ask About Your Document</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Damage detection, editable OCR, a Gemini-powered document assistant and marked AI reconstruction.
        </p>
      </div>

      {status && !status.gemini_configured && (
        <div className="p-3 rounded-xl bg-yellow-50 border border-yellow-300 text-yellow-800 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4" /> Document Chat needs GEMINI_API_KEY in the project .env file.
        </div>
      )}

      <div className="flex gap-2 overflow-x-auto pb-1">
        {assets.map((a) => (
          <button key={a.id} onClick={() => select(a.id)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium shrink-0 border transition-all ${
              assetId === a.id ? 'border-royal-purple bg-purple-50 text-royal-purple font-semibold shadow-sm'
                : 'border-border bg-white text-text-secondary hover:bg-surface-muted'}`}>
            {a.original_filename}
          </button>
        ))}
        {assets.length === 0 && <span className="text-xs text-text-secondary">Upload a document first.</span>}
      </div>

      <div className="flex rounded-lg border border-border bg-white p-1 w-fit">
        {tabs.map((t) => (
          <button key={t.id} onClick={() => { setTab(t.id); setSearchParams({ assetId, tab: t.id }); }}
            className={`px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 transition-colors ${
              tab === t.id ? 'bg-royal-purple text-white shadow-glow-purple' : 'text-text-secondary hover:text-text-primary'}`}>
            {t.icon}{t.label}
          </button>
        ))}
      </div>

      {assetId && tab === 'damage' && <DamagePanel key={assetId} assetId={assetId} />}
      {assetId && tab === 'ocr' && <OcrPanel key={assetId} assetId={assetId} />}
      {assetId && tab === 'chat' && <ChatPanel key={assetId} assetId={assetId} enabled={!!status?.gemini_configured} />}
      {assetId && tab === 'reconstruct' && <ReconstructPanel key={assetId} assetId={assetId} />}
    </div>
  );
};

const Card: React.FC<{ title: string; children: React.ReactNode; right?: React.ReactNode }> = ({ title, children, right }) => (
  <div className="p-5 rounded-card bg-surface border border-border shadow-card space-y-3">
    <div className="flex items-center justify-between">
      <h2 className="text-sm font-display font-bold text-text-primary">{title}</h2>
      {right}
    </div>
    {children}
  </div>
);

const Busy: React.FC<{ text: string }> = ({ text }) => (
  <div className="flex items-center gap-2 text-xs text-text-secondary py-6 justify-center">
    <Loader2 className="w-4 h-4 animate-spin text-royal-purple" /> {text}
  </div>
);

const ErrorBox: React.FC<{ text: string }> = ({ text }) => (
  <div className="p-3 rounded-xl bg-error/10 border border-error/30 text-error text-xs flex items-center gap-2">
    <AlertCircle className="w-4 h-4 shrink-0" /> {text}
  </div>
);

// ---------------------------------------------------------------- damage + plan
const DamagePanel: React.FC<{ assetId: string }> = ({ assetId }) => {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    documentAiService.damage(assetId).then(setData).catch((e) => setError(errText(e)));
  }, [assetId]);
  if (error) return <ErrorBox text={error} />;
  if (!data) return <Busy text="Detecting blur, fading, stains, creases, specks and tears..." />;
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Card title={`Damage Map (damage score ${data.damage_score}/100)`}
        right={<span className="text-[11px] font-mono text-steel">{data.elapsed_s}s</span>}>
        <img src={data.damage_map_url} alt="Damage map" className="w-full rounded-lg border border-border" />
        <div className="flex gap-3 text-[11px] text-text-secondary">
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-[#ffaa00]" />Stains</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-[#00c8ff]" />Creases / scratches</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-[#ff283c]" />Tears / burns / missing</span>
        </div>
      </Card>
      <div className="space-y-6">
        <Card title="Detected Damage">
          <div className="space-y-2">
            {Object.entries<any>(data.damages).map(([k, d]) => (
              <div key={k} className="flex items-start gap-3">
                <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border w-20 text-center shrink-0 ${LEVEL_STYLE[d.level]}`}>{d.level}</span>
                <div className="min-w-0">
                  <div className="text-xs font-semibold text-text-primary capitalize">{k.replace(/_/g, ' ')}
                    <span className="ml-2 font-mono text-steel">{Math.round(d.severity * 100)}%</span></div>
                  <div className="text-[11px] text-text-secondary">{d.evidence}</div>
                </div>
              </div>
            ))}
          </div>
        </Card>
        <Card title="Automatically Selected Restoration Models">
          <div className="space-y-1.5">
            {data.plan.map((p: any) => (
              <div key={p.stage} className="flex items-start gap-2 text-xs">
                {p.run ? <CheckCircle2 className="w-4 h-4 text-success shrink-0" /> : <XCircle className="w-4 h-4 text-steel shrink-0" />}
                <div>
                  <span className={`font-semibold ${p.run ? 'text-text-primary' : 'text-steel'}`}>{p.model}</span>
                  <span className="text-text-secondary"> — {p.reason}</span>
                </div>
              </div>
            ))}
          </div>
          <p className="text-[11px] text-text-secondary">This plan runs automatically when you restore the document in Restoration Studio.</p>
        </Card>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------- OCR review
const OcrPanel: React.FC<{ assetId: string }> = ({ assetId }) => {
  const [data, setData] = useState<any>(null);
  const [lines, setLines] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<any>(null);
  const [hover, setHover] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  const load = (refresh = false) => {
    setLoading(true); setError(''); setSaved(null);
    documentAiService.getOcr(assetId, undefined, refresh).then((d) => {
      setData(d);
      const edited = d.edited_text ? d.edited_text.split('\n') : null;
      setLines(edited && edited.length === d.lines.length ? edited : d.lines.map((l: any) => l.text));
    }).catch((e) => setError(errText(e))).finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, [assetId]);

  const save = async (approve: boolean) => {
    setSaving(true); setError('');
    try { setSaved(await documentAiService.saveOcr(assetId, lines, data.version_id, approve)); }
    catch (e) { setError(errText(e)); }
    finally { setSaving(false); }
  };

  if (loading) return <Busy text="Reading text with PaddleOCR (first read can take ~25 s)..." />;
  if (error && !data) return <ErrorBox text={error} />;
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Card title={`Page (${data.version_type === 'original' ? 'original — restore it for better OCR' : 'restored version'})`}>
        <div className="relative">
          <img src={data.image_url} alt="Document" className="w-full rounded-lg border border-border" />
          {data.lines.map((l: any, i: number) => (
            <div key={i}
              className={`absolute border ${l.unreadable ? 'border-error bg-error/10' : 'border-royal-purple/40'} ${hover === i ? 'ring-2 ring-royal-purple bg-royal-purple/10' : ''}`}
              style={{ left: `${(l.box[0] / data.width) * 100}%`, top: `${(l.box[1] / data.height) * 100}%`,
                width: `${((l.box[2] - l.box[0]) / data.width) * 100}%`, height: `${((l.box[3] - l.box[1]) / data.height) * 100}%` }} />
          ))}
          {data.damaged_regions.map((r: any, i: number) => (
            <div key={`d${i}`} className="absolute border-2 border-dashed border-orange-500"
              style={{ left: `${(r.x / data.width) * 100}%`, top: `${(r.y / data.height) * 100}%`,
                width: `${(r.w / data.width) * 100}%`, height: `${(r.h / data.height) * 100}%` }} title="Damaged region" />
          ))}
        </div>
        <div className="flex flex-wrap gap-3 text-[11px] text-text-secondary">
          <span className="flex items-center gap-1"><span className="w-3 h-3 border border-royal-purple" />Read line</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 border border-error bg-error/10" />Unreadable (confidence &lt; 80%)</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 border-2 border-dashed border-orange-500" />Damaged region</span>
        </div>
      </Card>
      <Card title="Extracted Text — review and correct"
        right={<span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${data.status === 'approved' ? LEVEL_STYLE.none : LEVEL_STYLE.mild}`}>{data.status}</span>}>
        <div className="text-[11px] text-text-secondary">
          {data.lines.length} lines · mean confidence {data.mean_confidence ?? '—'} · {data.unreadable_lines} unreadable · source: {data.source}
        </div>
        <div className="space-y-1.5 max-h-[460px] overflow-y-auto pr-1">
          {lines.map((t, i) => {
            const l = data.lines[i];
            const changed = t.trim() !== (l?.text || '').trim();
            return (
              <div key={i} className="flex items-center gap-2" onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}>
                <span className={`text-[10px] font-mono w-10 text-right shrink-0 ${l?.unreadable ? 'text-error font-bold' : 'text-steel'}`}>
                  {l ? Math.round(l.score * 100) : '—'}%
                </span>
                <input value={t} onChange={(e) => setLines(lines.map((x, j) => (j === i ? e.target.value : x)))}
                  className={`flex-1 px-2 py-1 rounded border text-xs font-mono ${l?.unreadable ? 'border-error/50 bg-error/5' : 'border-border'} ${changed ? 'bg-yellow-50 border-yellow-400' : ''}`} />
              </div>
            );
          })}
          {lines.length === 0 && <div className="text-xs text-text-secondary">No text was found on this page.</div>}
        </div>
        {error && <ErrorBox text={error} />}
        {saved && <div className="text-xs text-success">Saved as {saved.status}: {saved.lines_saved} lines, {saved.lines_corrected} corrected. The chatbot and quality scores now use this text.</div>}
        <div className="flex flex-wrap gap-2 pt-2 border-t border-border">
          <NeonButton size="sm" variant="ai" disabled={saving} icon={<Save className="w-4 h-4" />} onClick={() => save(true)}>Approve & Save</NeonButton>
          <NeonButton size="sm" variant="outline" disabled={saving} onClick={() => save(false)}>Save Draft</NeonButton>
          <NeonButton size="sm" variant="outline" icon={<RefreshCw className="w-4 h-4" />} onClick={() => load(true)}>Re-run OCR</NeonButton>
          {data.status === 'approved' && (
            <a href={documentAiService.exportTextUrl(assetId)} onClick={(e) => {
              e.preventDefault();
              fetch(documentAiService.exportTextUrl(assetId), { headers: { Authorization: `Bearer ${localStorage.getItem('docrestore_token')}` } })
                .then((r) => r.blob()).then((b) => { const a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = 'transcription.txt'; a.click(); });
            }}>
              <NeonButton size="sm" variant="outline" icon={<Download className="w-4 h-4" />}>Download .txt</NeonButton>
            </a>
          )}
        </div>
      </Card>
    </div>
  );
};

// ---------------------------------------------------------------- Gemini chat
const QUICK = [
  'Summarise this document in 3-5 sentences.',
  'Transcribe the full text exactly. Mark unreadable words as [?].',
  'Explain any old-fashioned words or references in this document.',
  'Who wrote this, to whom, when and where? Quote the evidence.',
];

const ChatPanel: React.FC<{ assetId: string; enabled: boolean }> = ({ assetId, enabled }) => {
  const [msgs, setMsgs] = useState<{ role: string; content: string; meta?: string }[]>([]);
  const [q, setQ] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }); }, [msgs, busy]);

  const ask = async (text: string) => {
    if (!text.trim() || busy) return;
    const history = msgs.map(({ role, content }) => ({ role, content }));
    setMsgs([...msgs, { role: 'user', content: text }]);
    setQ(''); setBusy(true); setError('');
    try {
      const r = await documentAiService.chat(assetId, text, history);
      setMsgs((m) => [...m, { role: 'assistant', content: r.answer, meta: `${r.model} · text: ${r.text_source}` }]);
    } catch (e) { setError(errText(e)); }
    finally { setBusy(false); }
  };

  return (
    <Card title="Ask About This Document" right={<span className="text-[11px] font-mono text-steel">Gemini · page image + extracted text</span>}>
      {!enabled && <ErrorBox text="GEMINI_API_KEY is not configured on the server." />}
      <div className="flex flex-wrap gap-2">
        {QUICK.map((s) => (
          <button key={s} disabled={busy || !enabled} onClick={() => ask(s)}
            className="px-2.5 py-1 rounded-full border border-border text-[11px] text-text-secondary hover:border-royal-purple hover:text-royal-purple disabled:opacity-50">{s}</button>
        ))}
      </div>
      <div className="h-[420px] overflow-y-auto rounded-xl bg-surface-muted border border-border p-4 space-y-3">
        {msgs.length === 0 && <div className="text-xs text-text-secondary text-center pt-16">Ask a question, or pick a suggestion above.</div>}
        {msgs.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] px-3 py-2 rounded-xl text-xs whitespace-pre-wrap leading-relaxed ${
              m.role === 'user' ? 'bg-royal-purple text-white' : 'bg-white border border-border text-text-primary'}`}>
              {m.content}
              {m.meta && <div className="mt-1 text-[10px] font-mono text-steel">{m.meta}</div>}
            </div>
          </div>
        ))}
        {busy && <div className="flex items-center gap-2 text-xs text-text-secondary"><Loader2 className="w-4 h-4 animate-spin" />Thinking...</div>}
        <div ref={end} />
      </div>
      {error && <ErrorBox text={error} />}
      <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); ask(q); }}>
        <input value={q} onChange={(e) => setQ(e.target.value)} disabled={!enabled}
          placeholder="e.g. What is the main news in this letter?"
          className="flex-1 px-3 py-2 rounded-lg border border-border text-sm focus:outline-none focus:ring-2 focus:ring-royal-purple/30" />
        <NeonButton type="submit" variant="ai" disabled={busy || !q.trim() || !enabled} icon={<Send className="w-4 h-4" />}>Ask</NeonButton>
      </form>
      <p className="text-[11px] text-text-secondary">Answers come from the document only. Approve the text in OCR Review to give the assistant a corrected transcription.</p>
    </Card>
  );
};

// ---------------------------------------------------------------- LaMa reconstruction
const ReconstructPanel: React.FC<{ assetId: string }> = ({ assetId }) => {
  const [includeText, setIncludeText] = useState(false);
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<any>(null);
  const [error, setError] = useState('');
  const run = async () => {
    setBusy(true); setError(''); setRes(null);
    try { setRes(await documentAiService.reconstruct(assetId, includeText)); }
    catch (e) { setError(errText(e)); }
    finally { setBusy(false); }
  };
  return (
    <div className="space-y-6">
      <Card title="Reconstruct Missing and Torn Regions (LaMa)">
        <p className="text-xs text-text-secondary">
          Fills tears, holes, burns and missing paper detected on the latest version. The result is saved as a new
          version labelled <b>AI reconstructed</b>; the original stays unchanged and every generated pixel is marked in pink.
        </p>
        <label className="flex items-start gap-2 text-xs">
          <input type="checkbox" checked={includeText} onChange={(e) => setIncludeText(e.target.checked)} className="mt-0.5" />
          <span>Also fill damage that overlaps writing. <span className="text-error">Letters created there are AI guesses, not recovered text.</span></span>
        </label>
        <NeonButton variant="ai" disabled={busy} onClick={run} icon={busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />}>
          {busy ? 'Reconstructing...' : 'Run AI Reconstruction'}
        </NeonButton>
        {error && <ErrorBox text={error} />}
        {res?.status === 'nothing_to_reconstruct' && <div className="text-xs text-text-secondary">{res.message}</div>}
      </Card>
      {res?.status === 'ok' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card title="Reconstructed Result">
            <img src={res.image_url} alt="Reconstructed" className="w-full rounded-lg border border-border" />
          </Card>
          <Card title={`AI-Generated Regions Marked (${res.ai_generated_pct}% of page, ${res.regions.length} regions)`}>
            <img src={res.marked_url} alt="AI regions marked" className="w-full rounded-lg border-2 border-hot-pink" />
            <p className="text-[11px] text-text-secondary">Pink = generated by LaMa in {res.elapsed_s}s. Open Comparison Studio to compare versions.</p>
          </Card>
        </div>
      )}
    </div>
  );
};
