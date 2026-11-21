import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Bell, Sparkles, Folder, CheckCircle, ChevronDown, User as UserIcon, LogOut, UserPlus, Shield } from 'lucide-react';
import { projectService, notificationService, authService } from '../../services/api';
import { Project, User } from '../../types';

interface TopbarProps {
  currentProject?: Project | null;
  onSelectProject?: (proj: Project) => void;
}

export const Topbar: React.FC<TopbarProps> = ({ currentProject, onSelectProject }) => {
  const navigate = useNavigate();
  const [currentUser, setCurrentUser] = useState<User | null>(() => {
    try {
      const stored = localStorage.getItem('docrestore_user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  const [projects, setProjects] = useState<Project[]>([]);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [showNotifs, setShowNotifs] = useState(false);
  const [showProjects, setShowProjects] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

  useEffect(() => {
    // Fetch live user identity
    authService.getMe().then((u) => {
      setCurrentUser(u);
      localStorage.setItem('docrestore_user', JSON.stringify(u));
    }).catch((err) => {
      if (err?.response?.status === 401) {
        authService.logout();
        navigate('/login');
      }
    });

    // Fetch user-authorized projects
    projectService.list().then((list) => {
      setProjects(list);
      if (list.length > 0 && !currentProject && onSelectProject) {
        onSelectProject(list[0]);
      }
    }).catch(() => {});

    // Fetch user notifications
    notificationService.list().then((data) => {
      setNotifications(data);
    }).catch(() => {});
  }, []);

  const unreadCount = notifications.filter(n => !n.is_read).length;

  // Compute initials dynamically
  const getInitials = (name?: string) => {
    if (!name) return 'U';
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  };

  const isPlatformAdmin = currentUser?.role === 'administrator' || currentUser?.role === 'platform_admin';
  const roleLabel = isPlatformAdmin ? 'Platform Administrator' : 'Standard User';

  const handleLogout = () => {
    authService.logout();
    setShowUserMenu(false);
    navigate('/login');
  };

  return (
    <header className="h-16 bg-surface border-b border-border px-6 flex items-center justify-between z-20 shrink-0">
      {/* Project Selector */}
      <div className="relative">
        <button
          onClick={() => setShowProjects(!showProjects)}
          className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg border border-border hover:border-royal-purple/50 bg-white transition-all text-xs font-medium text-text-primary"
        >
          <Folder className="w-3.5 h-3.5 text-royal-purple" />
          <span className="font-semibold">{currentProject ? currentProject.name : 'Select Project'}</span>
          <ChevronDown className="w-3.5 h-3.5 text-steel" />
        </button>

        {showProjects && (
          <div className="absolute left-0 mt-2 w-72 bg-white rounded-xl shadow-lg border border-border p-2 z-50">
            <div className="text-[10px] font-mono uppercase text-steel px-2 py-1">Authorized Projects</div>
            {projects.length === 0 ? (
              <div className="p-3 text-xs text-text-secondary text-center">No projects in this workspace yet.</div>
            ) : (
              projects.map((p) => (
                <button
                  key={p.id}
                  onClick={() => {
                    if (onSelectProject) onSelectProject(p);
                    setShowProjects(false);
                  }}
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs flex items-center justify-between hover:bg-surface-muted transition-colors ${
                    currentProject?.id === p.id ? 'bg-purple-50 text-royal-purple font-semibold' : 'text-text-primary'
                  }`}
                >
                  <span className="truncate">{p.name}</span>
                  {currentProject?.id === p.id && <CheckCircle className="w-3.5 h-3.5 text-royal-purple shrink-0" />}
                </button>
              ))
            )}
          </div>
        )}
      </div>

      {/* Right controls: Notifications & User Profile */}
      <div className="flex items-center gap-4">
        {/* Extreme Neon AI Engine Status Pill */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1 rounded-full bg-sidebar text-white text-xs font-mono border border-neon-violet/30 shadow-glow-purple">
          <Sparkles className="w-3 h-3 text-hot-pink animate-pulse" />
          <span>UI-Aware Residual Engine</span>
        </div>

        {/* Notifications Popover */}
        <div className="relative">
          <button
            onClick={() => setShowNotifs(!showNotifs)}
            className="p-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-surface-muted relative transition-colors"
          >
            <Bell className="w-4 h-4" />
            {unreadCount > 0 && (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-fuchsia-brand animate-ping" />
            )}
          </button>

          {showNotifs && (
            <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-xl border border-border p-3 z-50">
              <div className="flex items-center justify-between pb-2 border-b border-border text-xs font-semibold">
                <span>Notifications</span>
                <span className="text-[10px] text-royal-purple font-mono">{unreadCount} unread</span>
              </div>
              <div className="mt-2 max-h-60 overflow-y-auto space-y-2">
                {notifications.length === 0 ? (
                  <div className="text-center py-4 text-xs text-steel">No notifications yet</div>
                ) : (
                  notifications.map((n) => (
                    <div key={n.id} className="p-2 rounded-lg bg-surface-muted text-xs">
                      <div className="font-semibold text-text-primary">{n.title}</div>
                      <div className="text-text-secondary text-[11px] mt-0.5">{n.message}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* User Avatar with Dropdown */}
        <div className="relative pl-3 border-l border-border">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-2.5 text-left hover:opacity-85 transition-opacity"
          >
            <div className="w-8 h-8 rounded-full bg-gradient-brand flex items-center justify-center text-white text-xs font-bold font-display shadow-glow-blue">
              {getInitials(currentUser?.full_name)}
            </div>
            <div className="hidden sm:block text-left">
              <div className="text-xs font-semibold text-text-primary leading-none flex items-center gap-1">
                {currentUser?.full_name || 'Authenticated User'}
                <ChevronDown className="w-3 h-3 text-steel" />
              </div>
              <div className="text-[10px] text-steel font-mono mt-0.5">
                {currentUser?.email || 'user@docrestore.ai'}
              </div>
            </div>
          </button>

          {showUserMenu && (
            <div className="absolute right-0 mt-2 w-64 bg-white rounded-xl shadow-xl border border-border p-2 z-50">
              <div className="px-3 py-2 border-b border-border">
                <div className="text-xs font-bold text-text-primary">{currentUser?.full_name}</div>
                <div className="text-[11px] text-steel font-mono">{currentUser?.email}</div>
                <div className="mt-1 inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-purple-50 text-royal-purple border border-royal-purple/20">
                  <Shield className="w-3 h-3" />
                  <span>{roleLabel}</span>
                </div>
              </div>
              <div className="mt-1 space-y-1">
                {isPlatformAdmin && (
                  <Link
                    to="/admin"
                    onClick={() => setShowUserMenu(false)}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-royal-purple font-medium hover:bg-purple-50 transition-colors"
                  >
                    <Shield className="w-3.5 h-3.5" />
                    <span>Administrator Center</span>
                  </Link>
                )}
                <Link
                  to="/settings"
                  onClick={() => setShowUserMenu(false)}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-text-secondary hover:text-text-primary hover:bg-surface-muted transition-colors"
                >
                  <UserIcon className="w-3.5 h-3.5" />
                  <span>Account & Workspace Settings</span>
                </Link>
                <Link
                  to="/register"
                  onClick={() => setShowUserMenu(false)}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-text-secondary hover:text-text-primary hover:bg-surface-muted transition-colors"
                >
                  <UserPlus className="w-3.5 h-3.5 text-royal-purple" />
                  <span>Register Another Workspace</span>
                </Link>
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-error hover:bg-error/10 transition-colors"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>Sign Out / Switch Account</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
