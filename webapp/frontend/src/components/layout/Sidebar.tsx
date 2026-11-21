import React from 'react';
import { NavLink, Link } from 'react-router-dom';
import {
  LayoutDashboard,
  UploadCloud,
  Sparkles,
  SplitSquareVertical,
  BarChart3,
  FolderKanban,
  FileDown,
  Settings,
  ShieldAlert,
  Cpu,
  Layers,
  ExternalLink,
  LogIn,
  UserPlus
} from 'lucide-react';

interface SidebarProps {
  collapsed?: boolean;
}

export const Sidebar: React.FC<SidebarProps> = () => {
  const currentUser = (() => {
    try {
      const stored = localStorage.getItem('docrestore_user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  })();
  const isPlatformAdmin = currentUser?.role === 'administrator' || currentUser?.role === 'platform_admin';

  const navItems = [
    { to: '/dashboard', label: 'Dashboard', icon: <LayoutDashboard className="w-4 h-4" /> },
    { to: '/upload', label: 'Upload & Import', icon: <UploadCloud className="w-4 h-4" /> },
    { to: '/restoration', label: 'Restoration Studio', icon: <Sparkles className="w-4 h-4" />, highlight: true },
    { to: '/comparison', label: 'Comparison Studio', icon: <SplitSquareVertical className="w-4 h-4" /> },
    { to: '/analytics', label: 'Quality Analytics', icon: <BarChart3 className="w-4 h-4" /> },
    { to: '/library', label: 'Asset Library', icon: <FolderKanban className="w-4 h-4" /> },
    { to: '/export', label: 'Export & Reports', icon: <FileDown className="w-4 h-4" /> },
    { to: '/settings', label: 'Settings', icon: <Settings className="w-4 h-4" /> },
    { to: '/admin', label: 'Admin Center', icon: <ShieldAlert className="w-4 h-4" />, adminOnly: true },
  ];

  const visibleNavItems = navItems.filter((item) => !item.adminOnly || isPlatformAdmin);

  return (
    <aside className="w-64 bg-sidebar text-text-inverse flex flex-col h-screen border-r border-sidebar-panel shrink-0 select-none">
      {/* Brand Header */}
      <div className="p-5 border-b border-sidebar-panel flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-9 h-9 rounded-xl bg-gradient-brand flex items-center justify-center shadow-glow-purple group-hover:scale-105 transition-transform">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="font-display font-bold text-base tracking-tight text-white flex items-center gap-1.5">
              DocRestore <span className="text-neon-violet font-mono text-xs px-1 py-0.5 rounded bg-neon-violet/20">AI</span>
            </div>
            <div className="text-[10px] text-steel font-mono tracking-wider uppercase">Legacy UI Restorer</div>
          </div>
        </Link>
      </div>

      {/* Model Engine Status Card */}
      <div className="px-4 py-3 mx-3 my-3 rounded-xl bg-sidebar-panel border border-white/5">
        <div className="flex items-center justify-between text-xs mb-1">
          <span className="text-steel font-mono">PRIMARY MODEL</span>
          <span className="flex items-center gap-1 text-[11px] text-success">
            <span className="w-1.5 h-1.5 rounded-full bg-success animate-ping" />
            Active
          </span>
        </div>
        <div className="font-semibold text-xs text-white flex items-center gap-1.5">
          <Cpu className="w-3.5 h-3.5 text-neon-violet" />
          Residual U-Net (PyTorch)
        </div>
        <div className="text-[10px] text-steel mt-0.5 font-mono">
          UI-Aware Loss (L1 + SSIM + Sobel)
        </div>
      </div>

      {/* Navigation List */}
      <nav className="flex-1 px-3 py-2 space-y-1 overflow-y-auto">
        <div className="px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider text-steel">
          Restoration Platform
        </div>
        {visibleNavItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-btn text-xs font-medium transition-all duration-200 ${
                isActive
                  ? 'bg-royal-purple text-white shadow-glow-purple font-semibold'
                  : 'text-mist hover:text-white hover:bg-sidebar-panel'
              }`
            }
          >
            <span className="shrink-0">{item.icon}</span>
            <span className="truncate">{item.label}</span>
            {item.highlight && (
              <span className="ml-auto text-[9px] px-1.5 py-0.2 rounded-full bg-neon-magenta/20 text-hot-pink border border-neon-magenta/30 font-mono">
                AI
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer Info & Auth Navigation */}
      <div className="p-4 border-t border-sidebar-panel bg-sidebar-panel/40 space-y-2">
        <div className="flex items-center justify-between text-xs text-steel">
          <span className="font-mono text-[11px]">Royal Spectrum (C)</span>
          <span className="font-mono text-[11px] text-neon-violet">v1.0.0</span>
        </div>
        <div className="flex items-center justify-between pt-1 border-t border-white/5 text-[11px]">
          <Link 
            to="/"
            className="text-steel hover:text-white flex items-center gap-1 transition-colors"
          >
            <ExternalLink className="w-3 h-3" />
            Landing
          </Link>
          <Link 
            to="/login"
            className="text-steel hover:text-white flex items-center gap-1 transition-colors"
          >
            <LogIn className="w-3 h-3 text-neon-violet" />
            Sign In
          </Link>
          <Link 
            to="/register"
            className="text-steel hover:text-white flex items-center gap-1 transition-colors"
          >
            <UserPlus className="w-3 h-3 text-hot-pink" />
            Register
          </Link>
        </div>
      </div>
    </aside>
  );
};

