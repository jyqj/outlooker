import { lazy, Suspense, type ReactNode } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import VerificationPage from './pages/VerificationPage';
import NotFoundPage from './pages/NotFoundPage';
import ToastContainer from './components/Toast';
import ErrorBoundary from './components/ErrorBoundary';
import { getStoredAccessToken, isAccessTokenValid } from './lib/api';
import { LoadingSpinner } from './components/ui';

const AdminLoginPage = lazy(() => import('./pages/AdminLoginPage'));
const AdminDashboardPage = lazy(() => import('./pages/AdminDashboardPage'));
const TagsPage = lazy(() => import('./pages/tags/TagsPage'));
const SettingsPage = lazy(() => import('./pages/settings/SettingsPage'));
const AuditPage = lazy(() => import('./pages/audit/AuditPage'));
const OutlookAccountsPage = lazy(() => import('./pages/outlook/OutlookAccountsPage'));
const OutlookAccountDetailPage = lazy(() => import('./pages/outlook/OutlookAccountDetailPage'));
const OutlookTasksPage = lazy(() => import('./pages/outlook/OutlookTasksPage'));
const AuxEmailPoolPage = lazy(() => import('./pages/outlook/AuxEmailPoolPage'));
const ChannelConsolePage = lazy(() => import('./pages/outlook/ChannelConsolePage'));

interface ProtectedRouteProps {
  children: ReactNode;
}

const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
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

function RouteLoadingFallback() {
  const { t } = useTranslation();
  return (
    <div className="min-h-screen flex items-center justify-center">
      <LoadingSpinner size="lg" text={t('common.loading')} />
    </div>
  );
}

function RouteBoundary({ children }: { children: ReactNode }) {
  return (
    <RouteErrorBoundary>
      <Suspense fallback={<RouteLoadingFallback />}>{children}</Suspense>
    </RouteErrorBoundary>
  );
}

function ProtectedPage({ children }: { children: ReactNode }) {
  return (
    <ProtectedRoute>
      <RouteBoundary>{children}</RouteBoundary>
    </ProtectedRoute>
  );
}

function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<RouteBoundary><VerificationPage /></RouteBoundary>} />
        <Route path="/admin/login" element={<RouteBoundary><AdminLoginPage /></RouteBoundary>} />
        <Route path="/admin" element={<ProtectedPage><AdminDashboardPage /></ProtectedPage>} />
        <Route path="/admin/tags" element={<ProtectedPage><TagsPage /></ProtectedPage>} />
        <Route path="/admin/audit" element={<ProtectedPage><AuditPage /></ProtectedPage>} />
        <Route path="/admin/settings" element={<ProtectedPage><SettingsPage /></ProtectedPage>} />
        <Route path="/admin/outlook/accounts" element={<ProtectedPage><OutlookAccountsPage /></ProtectedPage>} />
        <Route
          path="/admin/outlook/accounts/:email"
          element={<ProtectedPage><OutlookAccountDetailPage /></ProtectedPage>}
        />
        <Route path="/admin/outlook/tasks" element={<ProtectedPage><OutlookTasksPage /></ProtectedPage>} />
        <Route path="/admin/outlook/resources" element={<ProtectedPage><AuxEmailPoolPage /></ProtectedPage>} />
        <Route path="/admin/outlook/channels" element={<ProtectedPage><ChannelConsolePage /></ProtectedPage>} />
        <Route path="*" element={<RouteBoundary><NotFoundPage /></RouteBoundary>} />
      </Routes>
      <ToastContainer />
    </>
  );
}

export default App;
