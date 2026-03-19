import React, { Suspense, type ReactNode } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import VerificationPage from './pages/VerificationPage';
import AdminLoginPage from './pages/AdminLoginPage';
import AdminDashboardPage from './pages/AdminDashboardPage';
import NotFoundPage from './pages/NotFoundPage';
import ToastContainer from './components/Toast';
import ErrorBoundary from './components/ErrorBoundary';
import { getStoredAccessToken, isAccessTokenValid } from './lib/api';
import { LoadingSpinner } from './components/ui';

const TagsPage = React.lazy(() => import('./pages/tags/TagsPage'));
const SettingsPage = React.lazy(() => import('./pages/settings/SettingsPage'));
const AuditPage = React.lazy(() => import('./pages/audit/AuditPage'));
const OutlookAccountsPage = React.lazy(() => import('./pages/outlook/OutlookAccountsPage'));
const OutlookAccountDetailPage = React.lazy(() => import('./pages/outlook/OutlookAccountDetailPage'));
const OutlookTasksPage = React.lazy(() => import('./pages/outlook/OutlookTasksPage'));
const AuxEmailPoolPage = React.lazy(() => import('./pages/outlook/AuxEmailPoolPage'));
const ChannelConsolePage = React.lazy(() => import('./pages/outlook/ChannelConsolePage'));

interface ProtectedRouteProps {
  children: ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const token = getStoredAccessToken();
  if (!token || !isAccessTokenValid()) {
    return <Navigate to="/admin/login" replace />;
  }
  return <>{children}</>;
};

function RouteErrorBoundary({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary onReset={() => window.location.reload()}>
      {children}
    </ErrorBoundary>
  );
}

function App() {
  const { t } = useTranslation();
  return (
    <>
      <Routes>
        <Route path="/" element={<RouteErrorBoundary><VerificationPage /></RouteErrorBoundary>} />
        <Route path="/admin/login" element={<RouteErrorBoundary><AdminLoginPage /></RouteErrorBoundary>} />
        <Route
          path="/admin"
          element={
            <ProtectedRoute>
              <RouteErrorBoundary>
                <AdminDashboardPage />
              </RouteErrorBoundary>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/tags"
          element={
            <ProtectedRoute>
              <RouteErrorBoundary>
                <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><LoadingSpinner size="lg" text={t('common.loading')} /></div>}>
                  <TagsPage />
                </Suspense>
              </RouteErrorBoundary>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/audit"
          element={
            <ProtectedRoute>
              <RouteErrorBoundary>
                <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><LoadingSpinner size="lg" text={t('common.loading')} /></div>}>
                  <AuditPage />
                </Suspense>
              </RouteErrorBoundary>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/settings"
          element={
            <ProtectedRoute>
              <RouteErrorBoundary>
                <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><LoadingSpinner size="lg" text={t('common.loading')} /></div>}>
                  <SettingsPage />
                </Suspense>
              </RouteErrorBoundary>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/outlook/accounts"
          element={
            <ProtectedRoute>
              <RouteErrorBoundary>
                <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><LoadingSpinner size="lg" text={t('common.loading')} /></div>}>
                  <OutlookAccountsPage />
                </Suspense>
              </RouteErrorBoundary>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/outlook/accounts/:email"
          element={
            <ProtectedRoute>
              <RouteErrorBoundary>
                <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><LoadingSpinner size="lg" text={t('common.loading')} /></div>}>
                  <OutlookAccountDetailPage />
                </Suspense>
              </RouteErrorBoundary>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/outlook/tasks"
          element={
            <ProtectedRoute>
              <RouteErrorBoundary>
                <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><LoadingSpinner size="lg" text={t('common.loading')} /></div>}>
                  <OutlookTasksPage />
                </Suspense>
              </RouteErrorBoundary>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/outlook/resources"
          element={
            <ProtectedRoute>
              <RouteErrorBoundary>
                <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><LoadingSpinner size="lg" text={t('common.loading')} /></div>}>
                  <AuxEmailPoolPage />
                </Suspense>
              </RouteErrorBoundary>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/outlook/channels"
          element={
            <ProtectedRoute>
              <RouteErrorBoundary>
                <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><LoadingSpinner size="lg" text={t('common.loading')} /></div>}>
                  <ChannelConsolePage />
                </Suspense>
              </RouteErrorBoundary>
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
      <ToastContainer />
    </>
  );
}

export default App;
