import React, { useState, useEffect } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import {
  FolderKanban,
  Search,
  Filter,
  Trash2,
  Download,
  Eye,
  Sparkles,
  Layers,
  Calendar,
  HardDrive,
  FileImage,
  X
} from 'lucide-react';
import { NeonButton } from '../../components/common/NeonButton';
import { Badge } from '../../components/common/Badge';
import { assetService } from '../../services/api';
import { Project, Asset } from '../../types';

export const AssetLibraryPage: React.FC = () => {
  const { currentProject } = useOutletContext<{ currentProject: Project | null }>();

  const [assets, setAssets] = useState<Asset[]>([]);
  const [search, setSearch] = useState('');
  const [resolutionFilter, setResolutionFilter] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [selectedAssetForDrawer, setSelectedAssetForDrawer] = useState<Asset | null>(null);

  const fetchAssets = async () => {
    try {
      setLoading(true);
      const list = await assetService.list({
        project_id: currentProject?.id,
        resolution: resolutionFilter || undefined,
        search: search || undefined
      });
      setAssets(list);
    } catch (err) {
      console.error("Error loading asset library", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAssets();
  }, [currentProject?.id, resolutionFilter]);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this asset and all restored versions?")) return;
    try {
      await assetService.delete(id);
      setAssets(assets.filter(a => a.id !== id));
      if (selectedAssetForDrawer?.id === id) {
        setSelectedAssetForDrawer(null);
      }
    } catch (err) {
      alert("Failed to delete asset.");
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-muted text-xs font-mono text-royal-purple mb-1 border border-border">
            <FolderKanban className="w-3.5 h-3.5" />
            <span>INTERFACE 07: PROFESSIONAL ASSET MANAGER</span>
          </div>
          <h1 className="text-2xl font-display font-bold text-text-primary tracking-tight">
            UI Asset Library & Version Archives
          </h1>
          <p className="mt-1 text-sm text-text-secondary">
            Manage uploaded screenshots, inspect resolution categories, and trace multi-model restoration histories.
          </p>
        </div>

        <Link to="/upload">
          <NeonButton variant="primary" size="sm" icon={<FileImage className="w-4 h-4" />}>
            Upload New Asset
          </NeonButton>
        </Link>
      </div>

      {/* Filter and Search Controls */}
      <div className="p-4 rounded-xl bg-surface border border-border shadow-card flex flex-col sm:flex-row gap-4 items-center justify-between">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-steel absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by filename..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && fetchAssets()}
            className="w-full pl-9 pr-4 py-2 rounded-lg border border-border text-xs focus:outline-none focus:ring-2 focus:ring-focus bg-white"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Filter className="w-4 h-4 text-steel shrink-0" />
          <select
            value={resolutionFilter}
            onChange={(e) => setResolutionFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-border text-xs bg-white text-text-primary focus:outline-none focus:ring-2 focus:ring-focus"
          >
            <option value="">All Resolutions</option>
            <option value="low_res">Low Resolution (&lt; 800x600)</option>
            <option value="standard">Standard Definition</option>
            <option value="high_res">High Resolution (&gt; 1080p)</option>
          </select>
        </div>
      </div>

      {/* Assets Grid */}
      {loading ? (
        <div className="text-center py-16 text-xs text-steel font-mono">Loading assets...</div>
      ) : assets.length === 0 ? (
        <div className="text-center py-16 p-8 rounded-card bg-surface border border-dashed border-border">
          <FileImage className="w-10 h-10 text-steel mx-auto mb-2 opacity-50" />
          <div className="text-sm font-semibold text-text-primary">No assets match your search.</div>
          <p className="text-xs text-text-secondary mt-1">Upload screenshots or adjust resolution filters.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {assets.map((asset) => (
            <div
              key={asset.id}
              onClick={() => setSelectedAssetForDrawer(asset)}
              className="p-4 rounded-card bg-surface border border-border hover:border-royal-purple/50 shadow-card hover:shadow-card-hover transition-all cursor-pointer flex flex-col justify-between group"
            >
              <div>
                <div className="aspect-[4/3] rounded-xl bg-sidebar overflow-hidden relative mb-3 flex items-center justify-center p-2">
                  <img
                    src={`/storage/thumbnails/thumb_${asset.stored_filename}`}
                    alt={asset.original_filename}
                    className="max-h-full max-w-full object-contain rounded group-hover:scale-105 transition-transform"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = `/storage/originals/${asset.stored_filename}`;
                    }}
                  />
                  <div className="absolute top-2 right-2">
                    <Badge variant={asset.resolution_category === 'low_res' ? 'warning' : 'neutral'} size="sm">
                      {asset.resolution_category}
                    </Badge>
                  </div>
                </div>

                <div className="font-semibold text-xs text-text-primary truncate" title={asset.original_filename}>
                  {asset.original_filename}
                </div>
                <div className="text-[11px] text-steel font-mono mt-0.5 flex items-center justify-between">
                  <span>{asset.width} × {asset.height} px</span>
                  <span>{(asset.file_size / 1024).toFixed(0)} KB</span>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-border flex items-center justify-between">
                <Link
                  to={`/comparison?assetId=${asset.id}`}
                  onClick={(e) => e.stopPropagation()}
                  className="text-xs text-royal-purple font-medium hover:underline flex items-center gap-1"
                >
                  <Eye className="w-3.5 h-3.5" />
                  Compare
                </Link>

                <div className="flex items-center gap-2">
                  <a
                    href={`/storage/originals/${asset.stored_filename}`}
                    download={asset.original_filename}
                    onClick={(e) => e.stopPropagation()}
                    className="p-1.5 hover:bg-surface-muted rounded text-steel hover:text-text-primary transition-colors"
                    title="Download Original"
                  >
                    <Download className="w-3.5 h-3.5" />
                  </a>
                  <button
                    onClick={(e) => handleDelete(asset.id, e)}
                    className="p-1.5 hover:bg-error/10 rounded text-steel hover:text-error transition-colors"
                    title="Delete Asset"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Asset Version Drawer / Modal */}
      {selectedAssetForDrawer && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex justify-end">
          <div className="w-full max-w-lg bg-surface h-full shadow-2xl p-6 overflow-y-auto space-y-6 flex flex-col">
            <div className="flex items-center justify-between pb-4 border-b border-border">
              <div>
                <h3 className="font-display font-bold text-base text-text-primary">Asset Version Tree</h3>
                <p className="text-xs text-text-secondary truncate max-w-xs">{selectedAssetForDrawer.original_filename}</p>
              </div>
              <button
                onClick={() => setSelectedAssetForDrawer(null)}
                className="p-2 hover:bg-surface-muted rounded-lg text-steel"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Asset Details */}
            <div className="aspect-video bg-sidebar rounded-xl overflow-hidden flex items-center justify-center p-2">
              <img
                src={`/storage/originals/${selectedAssetForDrawer.stored_filename}`}
                alt="Selected"
                className="max-h-full max-w-full object-contain"
              />
            </div>

            <div className="space-y-3 flex-1">
              <div className="text-xs font-mono uppercase text-steel font-semibold">Available Versions</div>
              {selectedAssetForDrawer.versions && selectedAssetForDrawer.versions.length > 0 ? (
                selectedAssetForDrawer.versions.map((v) => (
                  <div key={v.id} className="p-3 rounded-xl border border-border bg-white flex items-center justify-between text-xs">
                    <div>
                      <div className="font-semibold text-text-primary flex items-center gap-2">
                        <span>Version {v.version_number}</span>
                        <Badge variant={v.version_type === 'original' ? 'neutral' : 'ai'} size="sm">
                          {v.version_type}
                        </Badge>
                      </div>
                      <div className="text-[11px] text-steel font-mono mt-0.5">
                        {v.model_id ? `Model: ${v.model_id}` : 'Original capture'} • {v.width}x{v.height}
                      </div>
                    </div>
                    <a
                      href={`/storage/${v.version_type === 'original' ? 'originals' : 'restored'}/${v.stored_filename}`}
                      download={`asset_v${v.version_number}_${selectedAssetForDrawer.original_filename}`}
                      className="p-2 hover:bg-surface-muted rounded-lg text-royal-purple"
                      title="Download this version"
                    >
                      <Download className="w-4 h-4" />
                    </a>
                  </div>
                ))
              ) : (
                <div className="p-3 rounded-xl border border-border bg-white text-xs">
                  <div className="font-semibold">Version 1 (Original)</div>
                  <div className="text-[11px] text-steel font-mono">Original upload</div>
                </div>
              )}
            </div>

            <div className="pt-4 border-t border-border flex gap-3">
              <Link to={`/restoration?assetId=${selectedAssetForDrawer.id}`} className="flex-1">
                <NeonButton variant="ai" size="sm" className="w-full" icon={<Sparkles className="w-4 h-4" />}>
                  Restore This Asset
                </NeonButton>
              </Link>
              <Link to={`/comparison?assetId=${selectedAssetForDrawer.id}`} className="flex-1">
                <NeonButton variant="outline" size="sm" className="w-full" icon={<Eye className="w-4 h-4" />}>
                  Comparison Studio
                </NeonButton>
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

