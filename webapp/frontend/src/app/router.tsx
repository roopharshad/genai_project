import React from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { MainLayout } from '../components/layout/MainLayout';
import { LandingPage } from '../features/landing/LandingPage';
import { DashboardPage } from '../features/dashboard/DashboardPage';
import { UploadPage } from '../features/upload/UploadPage';
import { RestorationPage } from '../features/restoration/RestorationPage';
import { ComparisonPage } from '../features/comparison/ComparisonPage';
import { AnalyticsPage } from '../features/analytics/AnalyticsPage';
import { AssetLibraryPage } from '../features/library/AssetLibraryPage';
import { ExportPage } from '../features/export/ExportPage';
import { SettingsPage } from '../features/settings/SettingsPage';
import { OnboardingPage } from '../features/onboarding/OnboardingPage';
import { AdminDashboardPage } from '../features/admin/AdminDashboardPage';
import { LoginPage } from '../features/auth/LoginPage';
import { RegisterPage } from '../features/auth/RegisterPage';

const AdminRouteGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  try {
    const stored = localStorage.getItem('docrestore_user');
    const user = stored ? JSON.parse(stored) : null;
    if (user?.role === 'administrator' || user?.role === 'platform_admin') {
      return <>{children}</>;
    }
  } catch {}
  return <Navigate to="/dashboard" replace />;
};

export const router = createBrowserRouter([
  {
    path: '/',
    element: <LandingPage />,
  },
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/register',
    element: <RegisterPage />,
  },
  {
    path: '/onboarding',
    element: <OnboardingPage />,
  },
  {
    element: <MainLayout />,
    children: [
      {
        path: '/dashboard',
        element: <DashboardPage />,
      },
      {
        path: '/upload',
        element: <UploadPage />,
      },
      {
        path: '/restoration',
        element: <RestorationPage />,
      },
      {
        path: '/comparison',
        element: <ComparisonPage />,
      },
      {
        path: '/analytics',
        element: <AnalyticsPage />,
      },
      {
        path: '/library',
        element: <AssetLibraryPage />,
      },
      {
        path: '/export',
        element: <ExportPage />,
      },
      {
        path: '/settings',
        element: <SettingsPage />,
      },
      {
        path: '/admin',
        element: (
          <AdminRouteGuard>
            <AdminDashboardPage />
          </AdminRouteGuard>
        ),
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);

