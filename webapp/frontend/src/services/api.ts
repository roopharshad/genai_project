import axios from 'axios';
import {
  User,
  Workspace,
  Project,
  Asset,
  RestorationModel,
  RestorationJob,
  Experiment,
  EvaluationResult
} from '../types';

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach JWT token from localStorage if present
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('docrestore_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authService = {
  login: async (email: string, password: string) => {
    const res = await api.post('/auth/login', { email, password });
    return res.data;
  },
  register: async (email: string, password: string, full_name: string, workspace_name?: string) => {
    const res = await api.post('/auth/register', { email, password, full_name, workspace_name });
    return res.data;
  },
  getMe: async () => {
    const res = await api.get('/auth/me');
    return res.data;
  },
  logout: () => {
    localStorage.removeItem('docrestore_token');
    localStorage.removeItem('docrestore_user');
  }
};

export const workspaceService = {
  list: async (): Promise<Workspace[]> => {
    const res = await api.get('/workspaces/');
    return res.data;
  },
  create: async (name: string, description?: string): Promise<Workspace> => {
    const res = await api.post('/workspaces/', { name, description });
    return res.data;
  }
};

export const projectService = {
  list: async (workspace_id?: string): Promise<Project[]> => {
    const res = await api.get('/projects/', { params: { workspace_id } });
    return res.data;
  },
  create: async (workspace_id: string, name: string, description?: string): Promise<Project> => {
    const res = await api.post('/projects/', { workspace_id, name, description });
    return res.data;
  },
  getDetails: async (id: string) => {
    const res = await api.get(`/projects/${id}`);
    return res.data;
  }
};

export const assetService = {
  list: async (params?: { project_id?: string; resolution?: string; search?: string }): Promise<Asset[]> => {
    const res = await api.get('/assets/', { params });
    return res.data;
  },
  get: async (id: string): Promise<Asset> => {
    const res = await api.get(`/assets/${id}`);
    return res.data;
  },
  upload: async (project_id: string, file: File): Promise<Asset> => {
    const formData = new FormData();
    formData.append('project_id', project_id);
    formData.append('file', file);
    const res = await api.post('/assets/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },
  syntheticDegrade: async (id: string, params: {
    blur_strength?: number;
    noise_level?: number;
    jpeg_quality?: number;
    downsample_factor?: number;
    seed?: number;
  }) => {
    const res = await api.post(`/assets/${id}/synthetic-degrade`, null, { params });
    return res.data;
  },
  delete: async (id: string) => {
    const res = await api.delete(`/assets/${id}`);
    return res.data;
  }
};

export const restorationService = {
  getModels: async (): Promise<RestorationModel[]> => {
    const res = await api.get('/restorations/models');
    return res.data;
  },
  submitJob: async (data: {
    project_id: string;
    asset_id: string;
    model_id: string;
    config_params?: Record<string, any>;
  }): Promise<RestorationJob> => {
    const res = await api.post('/restorations/jobs', data);
    return res.data;
  },
  listJobs: async (params?: { project_id?: string; asset_id?: string; status?: string }): Promise<RestorationJob[]> => {
    const res = await api.get('/restorations/jobs', { params });
    return res.data;
  },
  getJob: async (id: string): Promise<RestorationJob> => {
    const res = await api.get(`/restorations/jobs/${id}`);
    return res.data;
  }
};

export const comparisonService = {
  getComparison: async (assetId: string, originalVersionId?: string, restoredVersionId?: string) => {
    const res = await api.get(`/comparisons/${assetId}`, {
      params: { original_version_id: originalVersionId, restored_version_id: restoredVersionId }
    });
    return res.data;
  }
};

export const analyticsService = {
  getExperiments: async (): Promise<Experiment[]> => {
    const res = await api.get('/analytics/experiments');
    return res.data;
  },
  getOverview: async (project_id?: string) => {
    const res = await api.get('/analytics/overview', { params: { project_id } });
    return res.data;
  }
};

export const reportService = {
  list: async (project_id?: string) => {
    const res = await api.get('/reports/', { params: { project_id } });
    return res.data;
  },
  generatePdf: async (project_id: string, title?: string) => {
    const res = await api.post('/reports/generate', null, { params: { project_id, title } });
    return res.data;
  },
  exportCsvUrl: (project_id?: string) => {
    return `/api/v1/reports/export/csv${project_id ? `?project_id=${project_id}` : ''}`;
  }
};

export const notificationService = {
  list: async () => {
    const res = await api.get('/notifications/');
    return res.data;
  },
  markRead: async (id: string) => {
    const res = await api.patch(`/notifications/${id}/read`);
    return res.data;
  }
};

export const settingsService = {
  get: async () => {
    const res = await api.get('/settings/');
    return res.data;
  },
  updateProfile: async (full_name: string) => {
    const res = await api.patch('/settings/profile', { full_name });
    return res.data;
  }
};

export default api;

