from __future__ import annotations

import json
import re
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[2]


def write(relative_path: str, content: str) -> None:
    path = ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).lstrip(), encoding="utf-8")


def replace_once(relative_path: str, old: str, new: str) -> None:
    path = ROOT / relative_path
    content = path.read_text(encoding="utf-8")
    if old not in content:
        if new in content:
            return
        raise RuntimeError(f"Expected text not found in {relative_path}: {old[:100]!r}")
    path.write_text(content.replace(old, new, 1), encoding="utf-8")


def regex_replace(relative_path: str, pattern: str, replacement: str) -> None:
    path = ROOT / relative_path
    content = path.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, dedent(replacement).lstrip("\n"), content, count=1, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError(f"Expected one match in {relative_path}, found {count}: {pattern}")
    path.write_text(updated, encoding="utf-8")


# ---------------------------------------------------------------------------
# Frontend asset graph: repair the entrypoint, split private routes, and make
# telemetry opt-in at runtime so the public verification page stays lean.
# ---------------------------------------------------------------------------
replace_once("frontend/index.html", "/src/main.jsx", "/src/main.tsx")

write(
    "frontend/src/App.tsx",
    r'''
    import React, { Suspense } from 'react';
    import { Navigate, Route, Routes } from 'react-router-dom';
    import { ToastContainer } from 'react-toastify';
    import { useTranslation } from 'react-i18next';
    import VerificationPage from './pages/VerificationPage';
    import NotFoundPage from './pages/NotFoundPage';
    import ErrorBoundary from './components/ErrorBoundary';
    import LoadingSpinner from './components/LoadingSpinner';
    import { isAccessTokenValid } from './lib/api/auth';
    import 'react-toastify/dist/ReactToastify.css';

    const AdminLoginPage = React.lazy(() => import('./pages/AdminLoginPage'));
    const AdminDashboardPage = React.lazy(() => import('./pages/AdminDashboardPage'));
    const AccountsPage = React.lazy(() => import('./pages/AccountsPage'));
    const OutlookAccountsPage = React.lazy(() => import('./pages/OutlookAccountsPage'));
    const OutlookWorkbenchPage = React.lazy(() => import('./pages/OutlookWorkbenchPage'));
    const ImportPage = React.lazy(() => import('./pages/ImportPage'));
    const EmailsPage = React.lazy(() => import('./pages/EmailsPage'));
    const BatchPage = React.lazy(() => import('./pages/BatchPage'));
    const TagsPage = React.lazy(() => import('./pages/TagsPage'));
    const AuditLogsPage = React.lazy(() => import('./pages/AuditLogsPage'));
    const SettingsPage = React.lazy(() => import('./pages/SettingsPage'));

    const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
      if (!isAccessTokenValid()) {
        return <Navigate to="/admin/login" replace />;
      }
      return <>{children}</>;
    };

    const RouteErrorBoundary: React.FC<{ children: React.ReactNode }> = ({ children }) => (
      <ErrorBoundary onReset={() => window.location.reload()}>{children}</ErrorBoundary>
    );

    const App: React.FC = () => {
      const { t } = useTranslation();

      return (
        <>
          <Suspense
            fallback={
              <div className="flex min-h-screen items-center justify-center">
                <LoadingSpinner size="lg" text={t('common.loading')} />
              </div>
            }
          >
            <Routes>
              <Route
                path="/"
                element={
                  <RouteErrorBoundary>
                    <VerificationPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/admin/login"
                element={
                  <RouteErrorBoundary>
                    <AdminLoginPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/admin/dashboard"
                element={
                  <ProtectedRoute>
                    <RouteErrorBoundary>
                      <AdminDashboardPage />
                    </RouteErrorBoundary>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/accounts"
                element={
                  <ProtectedRoute>
                    <RouteErrorBoundary>
                      <AccountsPage />
                    </RouteErrorBoundary>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/outlook-accounts"
                element={
                  <ProtectedRoute>
                    <RouteErrorBoundary>
                      <OutlookAccountsPage />
                    </RouteErrorBoundary>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/outlook-workbench"
                element={
                  <ProtectedRoute>
                    <RouteErrorBoundary>
                      <OutlookWorkbenchPage />
                    </RouteErrorBoundary>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/import"
                element={
                  <ProtectedRoute>
                    <RouteErrorBoundary>
                      <ImportPage />
                    </RouteErrorBoundary>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/emails"
                element={
                  <ProtectedRoute>
                    <RouteErrorBoundary>
                      <EmailsPage />
                    </RouteErrorBoundary>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/batch"
                element={
                  <ProtectedRoute>
                    <RouteErrorBoundary>
                      <BatchPage />
                    </RouteErrorBoundary>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/tags"
                element={
                  <ProtectedRoute>
                    <RouteErrorBoundary>
                      <TagsPage />
                    </RouteErrorBoundary>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/audit-logs"
                element={
                  <ProtectedRoute>
                    <RouteErrorBoundary>
                      <AuditLogsPage />
                    </RouteErrorBoundary>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/settings"
                element={
                  <ProtectedRoute>
                    <RouteErrorBoundary>
                      <SettingsPage />
                    </RouteErrorBoundary>
                  </ProtectedRoute>
                }
              />
              <Route path="/admin" element={<Navigate to="/admin/dashboard" replace />} />
              <Route
                path="*"
                element={
                  <RouteErrorBoundary>
                    <NotFoundPage />
                  </RouteErrorBoundary>
                }
              />
            </Routes>
          </Suspense>
          <ToastContainer
            position="top-right"
            autoClose={3000}
            hideProgressBar={false}
            newestOnTop={false}
            closeOnClick
            rtl={false}
            pauseOnFocusLoss
            draggable
            pauseOnHover
            theme="light"
          />
        </>
      );
    };

    export default App;
    ''',
)

write(
    "frontend/src/lib/telemetry.ts",
    r'''
    type SentryModule = typeof import('@sentry/react');

    interface ErrorContext {
      componentStack?: string | null;
    }

    let sentryModulePromise: Promise<SentryModule | null> | null = null;

    async function loadSentry(): Promise<SentryModule | null> {
      const dsn = import.meta.env.VITE_SENTRY_DSN?.trim();
      if (!dsn) {
        return null;
      }

      if (!sentryModulePromise) {
        sentryModulePromise = import('@sentry/react')
          .then((Sentry) => {
            Sentry.init({
              dsn,
              environment: import.meta.env.MODE,
              integrations: [Sentry.browserTracingIntegration(), Sentry.replayIntegration()],
              tracesSampleRate: import.meta.env.PROD ? 0.1 : 1,
              replaysSessionSampleRate: import.meta.env.PROD ? 0.01 : 0,
              replaysOnErrorSampleRate: 1,
            });
            return Sentry;
          })
          .catch((error: unknown) => {
            if (import.meta.env.DEV) {
              console.error('Failed to initialize telemetry', error);
            }
            return null;
          });
      }

      return sentryModulePromise;
    }

    export function initializeTelemetry(): void {
      void loadSentry();
    }

    export function captureException(error: unknown, context?: ErrorContext): void {
      void loadSentry().then((Sentry) => {
        if (!Sentry) {
          return;
        }

        const captureContext = context?.componentStack
          ? { extra: { componentStack: context.componentStack } }
          : undefined;
        Sentry.captureException(error, captureContext);
      });
    }
    ''',
)

write(
    "frontend/src/main.tsx",
    r'''
    import React from 'react';
    import ReactDOM from 'react-dom/client';
    import { BrowserRouter } from 'react-router-dom';
    import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
    import App from './App';
    import './index.css';
    import './i18n';
    import { initializeTelemetry } from './lib/telemetry';

    initializeTelemetry();

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: 1,
          refetchOnWindowFocus: false,
        },
      },
    });

    ReactDOM.createRoot(document.getElementById('root')!).render(
      <React.StrictMode>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </QueryClientProvider>
      </React.StrictMode>,
    );
    ''',
)

write(
    "frontend/src/components/ErrorBoundary.tsx",
    r'''
    import React, { Component, type ErrorInfo, type ReactNode } from 'react';
    import i18n from '../i18n';
    import { captureException } from '../lib/telemetry';
    import { logError } from '../utils/errorHandler';

    interface Props {
      children: ReactNode;
      fallback?: ReactNode;
      onReset?: () => void;
    }

    interface State {
      hasError: boolean;
      error?: Error;
    }

    class ErrorBoundary extends Component<Props, State> {
      constructor(props: Props) {
        super(props);
        this.state = { hasError: false };
      }

      static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
      }

      componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
        logError('React Error Boundary caught an error', error, errorInfo);
        captureException(error, { componentStack: errorInfo.componentStack });
      }

      handleReset = (): void => {
        this.setState({ hasError: false, error: undefined });
        this.props.onReset?.();
      };

      render(): ReactNode {
        if (!this.state.hasError) {
          return this.props.children;
        }

        if (this.props.fallback) {
          return this.props.fallback;
        }

        return (
          <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
            <div className="w-full max-w-md rounded-lg bg-white p-6 text-center shadow-lg">
              <div className="mb-4 text-5xl">⚠️</div>
              <h1 className="mb-2 text-xl font-semibold text-gray-900">
                {i18n.t('errorBoundary.title')}
              </h1>
              <p className="mb-6 text-gray-600">{i18n.t('errorBoundary.message')}</p>
              {import.meta.env.DEV && this.state.error && (
                <details className="mb-4 rounded bg-gray-100 p-3 text-left text-sm">
                  <summary className="cursor-pointer font-medium">
                    {i18n.t('errorBoundary.details')}
                  </summary>
                  <pre className="mt-2 overflow-auto text-xs text-red-600">
                    {this.state.error.message}
                    {'\n'}
                    {this.state.error.stack}
                  </pre>
                </details>
              )}
              <button
                type="button"
                onClick={this.handleReset}
                className="rounded-lg bg-blue-600 px-6 py-2 text-white transition-colors hover:bg-blue-700"
              >
                {i18n.t('errorBoundary.retry')}
              </button>
            </div>
          </div>
        );
      }
    }

    export default ErrorBoundary;
    ''',
)

write(
    "frontend/scripts/report-assets.mjs",
    r'''
    import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
    import { extname, join, relative } from 'node:path';
    import { gzipSync } from 'node:zlib';

    const distDir = new URL('../dist/', import.meta.url);
    const supportedExtensions = new Set(['.js', '.css', '.woff', '.woff2', '.svg']);

    if (!existsSync(distDir)) {
      console.error('dist/ does not exist; run npm run build first.');
      process.exit(1);
    }

    function walk(directory) {
      return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
        const path = join(directory.pathname, entry.name);
        return entry.isDirectory() ? walk(new URL(`${entry.name}/`, directory)) : [path];
      });
    }

    const rows = walk(distDir)
      .filter((path) => supportedExtensions.has(extname(path)))
      .map((path) => {
        const content = readFileSync(path);
        return {
          asset: relative(distDir.pathname, path),
          rawKiB: Number((statSync(path).size / 1024).toFixed(1)),
          gzipKiB: Number((gzipSync(content).length / 1024).toFixed(1)),
        };
      })
      .sort((left, right) => right.rawKiB - left.rawKiB);

    console.table(rows);
    console.log(
      `Total: ${rows.reduce((sum, row) => sum + row.rawKiB, 0).toFixed(1)} KiB raw / ` +
        `${rows.reduce((sum, row) => sum + row.gzipKiB, 0).toFixed(1)} KiB gzip`,
    );
    ''',
)

package_json_path = ROOT / "frontend/package.json"
package_json = json.loads(package_json_path.read_text(encoding="utf-8"))
package_json.setdefault("scripts", {})["analyze:assets"] = "node scripts/report-assets.mjs"
package_json_path.write_text(json.dumps(package_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "frontend/src/assets/react.svg").unlink(missing_ok=True)

# ---------------------------------------------------------------------------
# SQLite/cache hot path: a page of fetched mail now uses one connection, one
# transaction, and one retention pass. Persistent/connection PRAGMAs are split.
# ---------------------------------------------------------------------------
write(
    "backend/app/db/connection.py",
    r'''
    """数据库连接管理模块。"""

    import asyncio
    import functools
    import sqlite3
    from collections.abc import Callable
    from concurrent.futures import ThreadPoolExecutor
    from pathlib import Path
    from typing import Any, TypeVar

    from .base import DB_EXECUTOR_MAX_WORKERS

    T = TypeVar("T")


    class ConnectionMixin:
        """管理SQLite连接和数据库专用线程池。"""

        def _init_connection(self, db_path: str, project_root: Path) -> None:
            db_path_obj = Path(db_path)
            if db_path_obj.is_absolute():
                resolved_path = db_path_obj.resolve()
            else:
                resolved_path = (project_root / db_path_obj).resolve()

            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            self.db_path = str(resolved_path)
            self._executor: ThreadPoolExecutor | None = None

        def _create_connection(self) -> sqlite3.Connection:
            conn = sqlite3.connect(
                self.db_path,
                timeout=10.0,
                check_same_thread=False,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA busy_timeout = 10000")
            return conn

        def get_connection(self) -> sqlite3.Connection:
            """获取数据库连接。调用方负责关闭连接。"""
            return self._create_connection()

        def _get_executor(self) -> ThreadPoolExecutor:
            if self._executor is None:
                self._executor = ThreadPoolExecutor(
                    max_workers=DB_EXECUTOR_MAX_WORKERS,
                    thread_name_prefix="outlooker-db",
                )
            return self._executor

        async def _run_in_thread(
            self,
            func: Callable[..., T],
            *args: Any,
            **kwargs: Any,
        ) -> T:
            loop = asyncio.get_running_loop()
            call = functools.partial(func, *args, **kwargs)
            return await loop.run_in_executor(self._get_executor(), call)

        def close(self) -> None:
            """关闭数据库线程池。"""
            executor = self._executor
            if executor is not None:
                executor.shutdown(wait=True)
                self._executor = None
    ''',
)

write(
    "backend/app/db/manager.py",
    r'''
    """数据库管理器。"""

    import logging
    from contextlib import closing
    from pathlib import Path

    from ..settings import settings
    from .accounts import AccountsMixin
    from .admin import AdminMixin
    from .base import BaseDatabase
    from .batch import BatchMixin
    from .connection import ConnectionMixin
    from .email_cache import EmailCacheMixin
    from .migrations import MigrationsMixin
    from .tags import TagsMixin

    logger = logging.getLogger(__name__)


    class DatabaseManager(
        ConnectionMixin,
        AdminMixin,
        AccountsMixin,
        EmailCacheMixin,
        BatchMixin,
        TagsMixin,
        MigrationsMixin,
        BaseDatabase,
    ):
        """SQLite数据库管理器，组合各领域Mixin。"""

        def __init__(self, db_path: str | None = None) -> None:
            project_root = Path(__file__).parent.parent.parent
            self._init_connection(db_path or settings.database_path, project_root)
            self.init_database()

        def init_database(self) -> None:
            """初始化数据库表和索引。"""
            with closing(self._create_connection()) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA journal_mode = WAL")

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS accounts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        client_id TEXT NOT NULL,
                        refresh_token TEXT NOT NULL,
                        status TEXT DEFAULT 'active',
                        group_name TEXT DEFAULT 'default',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS admins (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        is_active BOOLEAN DEFAULT 1,
                        last_login TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS email_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT NOT NULL,
                        folder TEXT NOT NULL DEFAULT 'inbox',
                        message_id TEXT NOT NULL,
                        subject TEXT,
                        sender_name TEXT,
                        sender_email TEXT,
                        received_date TIMESTAMP,
                        body_preview TEXT,
                        body_content TEXT,
                        body_type TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(email, folder, message_id)
                    )
                    """
                )

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS verification_codes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        account_email TEXT NOT NULL,
                        code TEXT NOT NULL,
                        subject TEXT,
                        sender TEXT,
                        received_at TIMESTAMP,
                        extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_used BOOLEAN DEFAULT 0,
                        UNIQUE(account_email, code, received_at)
                    )
                    """
                )

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS batch_tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id TEXT UNIQUE NOT NULL,
                        task_type TEXT NOT NULL,
                        status TEXT DEFAULT 'pending',
                        total_count INTEGER DEFAULT 0,
                        completed_count INTEGER DEFAULT 0,
                        success_count INTEGER DEFAULT 0,
                        failed_count INTEGER DEFAULT 0,
                        result_data TEXT,
                        error_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        started_at TIMESTAMP,
                        completed_at TIMESTAMP
                    )
                    """
                )

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS email_tags (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT NOT NULL,
                        tag_name TEXT NOT NULL,
                        tag_color TEXT DEFAULT '#3B82F6',
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(email, tag_name)
                    )
                    """
                )

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        admin_username TEXT NOT NULL,
                        action TEXT NOT NULL,
                        resource_type TEXT,
                        resource_id TEXT,
                        details TEXT,
                        ip_address TEXT,
                        user_agent TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS system_config (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        config_key TEXT UNIQUE NOT NULL,
                        config_value TEXT,
                        description TEXT,
                        updated_by TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                # Remove indexes duplicated by PRIMARY KEY/UNIQUE constraints.
                cursor.execute("DROP INDEX IF EXISTS idx_accounts_email")
                cursor.execute("DROP INDEX IF EXISTS idx_email_cache_email_folder")
                cursor.execute("DROP INDEX IF EXISTS idx_email_cache_email_folder_message_id")

                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_accounts_status
                    ON accounts(status)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_email_cache_message_id
                    ON email_cache(message_id)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_email_cache_retention
                    ON email_cache(email, folder, created_at DESC, id DESC)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_verification_codes_email
                    ON verification_codes(account_email)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_batch_tasks_status
                    ON batch_tasks(status)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_email_tags_email
                    ON email_tags(email)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_audit_logs_admin
                    ON audit_logs(admin_username)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_audit_logs_created
                    ON audit_logs(created_at)
                    """
                )

                conn.commit()
                cursor.execute("PRAGMA optimize")
                logger.info("数据库初始化完成")


    db_manager = DatabaseManager()
    ''',
)

email_cache_path = ROOT / "backend/app/db/email_cache.py"
email_cache_content = email_cache_path.read_text(encoding="utf-8")
if "from collections.abc import Sequence\n" not in email_cache_content:
    email_cache_content = email_cache_content.replace(
        "import logging\n",
        "import logging\nfrom collections.abc import Sequence\n",
        1,
    )
email_cache_path.write_text(email_cache_content, encoding="utf-8")

regex_replace(
    "backend/app/db/email_cache.py",
    r"    async def cache_email\(.*?(?=    async def get_cached_email\()",
    r'''
    @staticmethod
    def _prepare_cache_rows(
        email: str,
        folder_id: str,
        messages: Sequence[dict[str, Any]],
    ) -> list[tuple[Any, ...]]:
        rows: list[tuple[Any, ...]] = []
        for email_data in messages:
            message_id = str(email_data.get("id") or "")
            if not message_id:
                continue

            sender = email_data.get("sender") or {}
            sender_address = sender.get("emailAddress") or {} if isinstance(sender, dict) else {}
            body = email_data.get("body") or {}
            body_data = body if isinstance(body, dict) else {}

            rows.append(
                (
                    email,
                    folder_id,
                    message_id,
                    email_data.get("subject", ""),
                    sender_address.get("name", ""),
                    sender_address.get("address", ""),
                    email_data.get("receivedDateTime", ""),
                    email_data.get("bodyPreview", ""),
                    body_data.get("content", ""),
                    body_data.get("contentType", ""),
                )
            )
        return rows

    async def cache_emails(
        self,
        email: str,
        messages: Sequence[dict[str, Any]],
        folder: str | None = None,
    ) -> int:
        """在单连接、单事务中缓存一批邮件。"""
        folder_id = normalize_folder(folder or settings.default_folder)
        rows = self._prepare_cache_rows(email, folder_id, messages)
        if not rows:
            return 0

        cache_limit = max(settings.email_cache_limit_per_account, 0)

        def _sync_cache(conn: "sqlite3.Connection") -> int:
            try:
                cursor = conn.cursor()
                cursor.executemany(
                    """
                    INSERT INTO email_cache (
                        email, folder, message_id, subject,
                        sender_name, sender_email, received_date,
                        body_preview, body_content, body_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(email, folder, message_id) DO UPDATE SET
                        subject = excluded.subject,
                        sender_name = excluded.sender_name,
                        sender_email = excluded.sender_email,
                        received_date = excluded.received_date,
                        body_preview = excluded.body_preview,
                        body_content = excluded.body_content,
                        body_type = excluded.body_type,
                        created_at = CURRENT_TIMESTAMP
                    """,
                    rows,
                )
                cursor.execute(
                    """
                    DELETE FROM email_cache
                    WHERE id IN (
                        SELECT id
                        FROM email_cache
                        WHERE email = ? AND folder = ?
                        ORDER BY created_at DESC, id DESC
                        LIMIT -1 OFFSET ?
                    )
                    """,
                    (email, folder_id, cache_limit),
                )
                conn.commit()
                return len(rows)
            except Exception:
                conn.rollback()
                logger.exception("批量缓存邮件失败")
                return 0

        return await self._run_in_thread(
            lambda: self._execute_with_connection(_sync_cache)
        )

    async def cache_email(
        self,
        email: str,
        message_id: str,
        email_data: dict[str, Any],
        folder: str | None = None,
    ) -> bool:
        """兼容单封写入调用；内部复用批量事务。"""
        payload = dict(email_data)
        payload["id"] = message_id
        return await self.cache_emails(email, [payload], folder=folder) == 1

    ''',
)

# ---------------------------------------------------------------------------
# IMAP resource lifecycle: remove HTTP transport coupling, close partial
# connections, and hand each fetched page to the batch cache API once.
# ---------------------------------------------------------------------------
imap_path = ROOT / "backend/app/imap_client.py"
imap_content = imap_path.read_text(encoding="utf-8").replace(
    "from fastapi import HTTPException\n\n",
    "",
    1,
)
imap_path.write_text(imap_content, encoding="utf-8")

regex_replace(
    "backend/app/imap_client.py",
    r"    async def refresh_access_token\(.*?(?=    async def get_valid_access_token\()",
    r'''
    async def refresh_access_token(self) -> str:
        """使用刷新令牌获取新的访问令牌。"""
        if not self.refresh_token:
            raise _exceptions.TokenRefreshError("缺少刷新令牌")

        if not self.outlook_account_service:
            self.outlook_account_service = OutlookAccountService()

        try:
            result = await self.outlook_account_service.refresh_access_token(
                self.email,
                self.refresh_token,
                client_id=self.client_id,
            )
            access_token = result.get("access_token")
            if not access_token:
                raise _exceptions.TokenRefreshError("刷新令牌响应中未包含访问令牌")

            self.access_token = access_token
            self.token_expires_at = result.get("expires_at") or (
                datetime.now().timestamp() + int(result.get("expires_in", 3600))
            )
            if result.get("refresh_token"):
                self.refresh_token = result["refresh_token"]
            return access_token
        except (_exceptions.TokenRefreshError, _exceptions.IMAPError):
            raise
        except Exception as exc:
            logger.error("刷新访问令牌失败: %s", exc)
            raise _exceptions.TokenRefreshError(f"刷新访问令牌失败: {exc}") from exc

    ''',
)

regex_replace(
    "backend/app/imap_client.py",
    r"    async def create_imap_connection\(.*?(?=    async def get_messages\()",
    r'''
    async def create_imap_connection(
        self,
        folder: str | None = None,
    ) -> imaplib.IMAP4_SSL:
        """创建并认证IMAP连接。失败时确保释放已创建的socket。"""
        access_token = await self.get_valid_access_token()
        selected_folder = normalize_folder(folder or settings.default_folder)

        def _sync_connect() -> imaplib.IMAP4_SSL:
            imap_conn: imaplib.IMAP4_SSL | None = None
            try:
                context = ssl.create_default_context()
                imap_conn = imaplib.IMAP4_SSL(
                    settings.imap_host,
                    settings.imap_port,
                    ssl_context=context,
                    timeout=settings.imap_connection_timeout,
                )
                sock = getattr(imap_conn, "sock", None)
                if sock is not None:
                    sock.settimeout(settings.imap_operation_timeout)

                auth_string = f"user={self.email}\x01auth=Bearer {access_token}\x01\x01"
                imap_conn.authenticate("XOAUTH2", lambda _: auth_string.encode())
                status, _ = imap_conn.select(f'"{selected_folder}"')
                if status != "OK":
                    raise _exceptions.IMAPError(f"无法选择文件夹: {selected_folder}")
                return imap_conn
            except Exception:
                if imap_conn is not None:
                    self.close_imap_connection(imap_conn)
                raise

        try:
            return await asyncio.to_thread(_sync_connect)
        except (_exceptions.TokenRefreshError, _exceptions.IMAPError):
            raise
        except Exception as exc:
            logger.error("IMAP连接失败: %s", exc)
            raise _exceptions.IMAPConnectionError(f"IMAP连接失败: {exc}") from exc

    ''',
)

regex_replace(
    "backend/app/imap_client.py",
    r"    async def _cache_messages\(.*?(?=    @staticmethod\n    def close_imap_connection)",
    r'''
    async def _cache_messages(
        self,
        folder: str,
        messages: list[dict[str, Any]],
    ) -> None:
        cacheable_messages = [message for message in messages if message.get("id")]
        if not cacheable_messages:
            return

        try:
            cached_count = await db_manager.cache_emails(
                self.email,
                cacheable_messages,
                folder=folder,
            )
            if cached_count != len(cacheable_messages):
                logger.debug(
                    "邮件缓存未完整写入: expected=%s actual=%s",
                    len(cacheable_messages),
                    cached_count,
                )
        except Exception as exc:
            logger.warning("缓存邮件失败: %s", exc)

    ''',
)

# ---------------------------------------------------------------------------
# HTTP/static resource delivery and resilient application shutdown.
# ---------------------------------------------------------------------------
write(
    "backend/app/core/lifecycle.py",
    r'''
    """应用资源关闭辅助函数。"""

    import asyncio
    import logging
    from collections.abc import Callable
    from typing import Protocol

    logger = logging.getLogger(__name__)


    class AsyncCleanup(Protocol):
        async def cleanup_all(self) -> None: ...


    class Closable(Protocol):
        def close(self) -> None: ...


    async def shutdown_application_resources(
        *,
        stop_background_refresh: Callable[[], None],
        email_manager: AsyncCleanup,
        database_manager: Closable,
    ) -> None:
        """独立释放资源，避免一个步骤失败后跳过其他清理。"""
        try:
            stop_background_refresh()
        except Exception:
            logger.exception("停止后台刷新任务失败")

        try:
            await email_manager.cleanup_all()
        except Exception:
            logger.exception("清理邮箱客户端资源失败")

        try:
            await asyncio.to_thread(database_manager.close)
        except Exception:
            logger.exception("关闭数据库资源失败")
    ''',
)

write(
    "backend/app/static_assets.py",
    r'''
    """静态资源解析和缓存策略。"""

    from pathlib import Path

    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    from starlette.responses import Response
    from starlette.types import Scope

    IMMUTABLE_ASSET_CACHE_CONTROL = "public, max-age=31536000, immutable"
    PUBLIC_ASSET_CACHE_CONTROL = "public, max-age=3600"
    REVALIDATE_CACHE_CONTROL = "no-cache"


    def cache_control_for_path(request_path: str) -> str:
        normalized_path = request_path.replace("\\", "/").lstrip("/")
        if normalized_path == "index.html":
            return REVALIDATE_CACHE_CONTROL
        if normalized_path.startswith("assets/"):
            return IMMUTABLE_ASSET_CACHE_CONTROL
        return PUBLIC_ASSET_CACHE_CONTROL


    def resolve_static_file(static_dir: Path, request_path: str) -> Path | None:
        if not request_path:
            return None

        root = static_dir.resolve()
        candidate = (root / request_path).resolve()
        if not candidate.is_relative_to(root) or not candidate.is_file():
            return None
        return candidate


    def static_file_response(path: Path, request_path: str) -> FileResponse:
        return FileResponse(
            path,
            headers={"Cache-Control": cache_control_for_path(request_path)},
        )


    class CacheControlledStaticFiles(StaticFiles):
        """为挂载目录设置显式缓存策略。"""

        def __init__(self, *, directory: str | Path, cache_control: str) -> None:
            super().__init__(directory=directory)
            self.cache_control = cache_control

        async def get_response(self, path: str, scope: Scope) -> Response:
            response = await super().get_response(path, scope)
            if response.status_code < 400:
                response.headers["Cache-Control"] = self.cache_control
            return response
    ''',
)

write(
    "backend/app/core/middleware.py",
    r'''
    """性能监控中间件。"""

    import logging
    import time

    from fastapi import Request
    from starlette.middleware.base import BaseHTTPMiddleware

    from .metrics import metrics

    logger = logging.getLogger(__name__)


    class MetricsMiddleware(BaseHTTPMiddleware):
        """记录请求性能指标。"""

        EXCLUDED_PATH_PREFIXES = (
            "/docs",
            "/redoc",
            "/openapi.json",
            "/static",
            "/assets",
            "/favicon",
        )

        async def dispatch(self, request: Request, call_next):
            path = request.url.path
            if path.startswith(self.EXCLUDED_PATH_PREFIXES):
                return await call_next(request)

            start_time = time.perf_counter()
            success = True
            try:
                response = await call_next(request)
                success = response.status_code < 400
                return response
            except Exception:
                success = False
                raise
            finally:
                duration = time.perf_counter() - start_time
                metrics.record_request(path, duration, success)
                if duration > 1.0:
                    logger.warning(
                        "慢请求: %s %s 耗时 %.0fms",
                        request.method,
                        path,
                        duration * 1000,
                    )
    ''',
)

write(
    "backend/app/mail_api.py",
    r'''
    #!/usr/bin/env python3
    """Outlooker FastAPI应用入口。"""

    import asyncio
    import logging
    import os
    from contextlib import asynccontextmanager
    from pathlib import Path

    import sentry_sdk
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.gzip import GZipMiddleware
    from fastapi.responses import PlainTextResponse
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    from .core.lifecycle import shutdown_application_resources
    from .core.middleware import MetricsMiddleware
    from .core.security_headers import SecurityHeadersMiddleware
    from .db.manager import db_manager
    from .dependencies import create_default_admin
    from .email_client import email_manager
    from .refresh_token_service import start_background_refresh, stop_background_refresh
    from .routers import (
        accounts,
        batch,
        dashboard,
        emails,
        import_emails,
        outlook,
        search,
        tags,
        verification,
    )
    from .routers.admin import admin_auth, audit_logs, system_config
    from .settings import settings
    from .static_assets import (
        IMMUTABLE_ASSET_CACHE_CONTROL,
        REVALIDATE_CACHE_CONTROL,
        CacheControlledStaticFiles,
        resolve_static_file,
        static_file_response,
    )

    logger = logging.getLogger(__name__)

    STATIC_DIR = Path(
        os.getenv("STATIC_DIR", Path(__file__).resolve().parents[2] / "data/static")
    )


    @asynccontextmanager
    async def lifespan(_: FastAPI):
        logger.info("正在启动Outlooker服务...")
        logger.info("数据目录: %s", settings.data_dir)
        logger.info("数据库文件: %s", settings.database_path)
        logger.info("静态文件目录: %s", STATIC_DIR)

        try:
            created = create_default_admin()
            if created:
                logger.info("已创建默认管理员账户，请尽快修改密码")
        except Exception:
            logger.exception("初始化默认管理员失败")

        try:
            start_background_refresh()
            yield
        finally:
            logger.info("正在关闭Outlooker服务...")
            await shutdown_application_resources(
                stop_background_refresh=stop_background_refresh,
                email_manager=email_manager,
                database_manager=db_manager,
            )
            logger.info("Outlooker服务已关闭")


    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=os.getenv("ENVIRONMENT", "production"),
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            ],
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            send_default_pii=False,
        )
        logger.info("Sentry错误监控已启用")

    app = FastAPI(
        title="Outlooker API",
        description="Outlook邮件验证码管理API",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    app.include_router(verification.router, prefix="/api", tags=["verification"])
    app.include_router(accounts.router, prefix="/api/admin", tags=["accounts"])
    app.include_router(emails.router, prefix="/api/admin", tags=["emails"])
    app.include_router(import_emails.router, prefix="/api/admin", tags=["import"])
    app.include_router(batch.router, prefix="/api/admin", tags=["batch"])
    app.include_router(tags.router, prefix="/api/admin", tags=["tags"])
    app.include_router(search.router, prefix="/api/admin", tags=["search"])
    app.include_router(dashboard.router, prefix="/api/admin", tags=["dashboard"])
    app.include_router(outlook.router)
    app.include_router(admin_auth.router, prefix="/api/admin", tags=["admin-auth"])
    app.include_router(audit_logs.router, prefix="/api/admin", tags=["audit-logs"])
    app.include_router(system_config.router, prefix="/api/admin", tags=["system-config"])


    @app.get("/metrics", include_in_schema=False)
    async def prometheus_metrics() -> PlainTextResponse:
        return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


    static_assets_path = STATIC_DIR / "assets"
    if static_assets_path.exists():
        app.mount(
            "/assets",
            CacheControlledStaticFiles(
                directory=static_assets_path,
                cache_control=IMMUTABLE_ASSET_CACHE_CONTROL,
            ),
            name="assets",
        )
        logger.info("已挂载静态资源目录: %s", static_assets_path)
    else:
        logger.warning("静态资源目录不存在: %s", static_assets_path)

    if STATIC_DIR.exists():
        app.mount(
            "/static",
            CacheControlledStaticFiles(
                directory=STATIC_DIR,
                cache_control=REVALIDATE_CACHE_CONTROL,
            ),
            name="static",
        )
        logger.info("已挂载兼容静态目录: %s", STATIC_DIR)
    else:
        logger.warning("静态文件目录不存在: %s", STATIC_DIR)


    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        reserved_path = (
            full_path == "api"
            or full_path.startswith("api/")
            or full_path.startswith("docs")
            or full_path.startswith("redoc")
            or full_path.startswith("openapi.json")
        )
        if reserved_path:
            raise HTTPException(status_code=404, detail="Not Found")

        static_file = resolve_static_file(STATIC_DIR, full_path)
        if static_file is not None:
            return static_file_response(static_file, full_path)

        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return static_file_response(index_path, "index.html")

        logger.warning("前端静态文件不存在: %s", index_path)
        return PlainTextResponse(
            "Outlooker API 正在运行，但前端静态文件未找到。请先构建前端资源。",
            headers={"Cache-Control": "no-store"},
        )


    async def main() -> None:
        import uvicorn

        config = uvicorn.Config(
            "app.mail_api:app",
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level.lower(),
            reload=False,
        )
        server = uvicorn.Server(config)
        await server.serve()


    if __name__ == "__main__":
        asyncio.run(main())
    ''',
)

# ---------------------------------------------------------------------------
# Regression tests and operator-facing performance documentation.
# ---------------------------------------------------------------------------
write(
    "tests/backend/test_email_cache_batch.py",
    r'''
    from collections.abc import Iterator
    from contextlib import closing

    import pytest

    from app.db import email_cache as email_cache_module
    from app.db.manager import DatabaseManager
    from app.imap_client import IMAPEmailClient, db_manager as shared_db_manager


    @pytest.fixture
    def database(tmp_path) -> Iterator[DatabaseManager]:
        manager = DatabaseManager(str(tmp_path / "email-cache.db"))
        yield manager
        manager.close()


    @pytest.mark.asyncio
    async def test_batch_cache_uses_one_connection_and_preserves_row_identity(
        database: DatabaseManager,
        monkeypatch,
    ) -> None:
        connection_count = 0
        original_create_connection = database._create_connection

        def counted_connection():
            nonlocal connection_count
            connection_count += 1
            return original_create_connection()

        monkeypatch.setattr(database, "_create_connection", counted_connection)
        messages = [
            {
                "id": "1",
                "subject": "first",
                "sender": {"emailAddress": {"name": "A", "address": "a@example.com"}},
            },
            {
                "id": "2",
                "subject": "second",
                "sender": {"emailAddress": {"name": "B", "address": "b@example.com"}},
            },
            {
                "id": "3",
                "subject": "third",
                "sender": {"emailAddress": {"name": "C", "address": "c@example.com"}},
            },
        ]

        assert await database.cache_emails("batch@example.com", messages) == 3
        assert connection_count == 1

        with closing(original_create_connection()) as conn:
            row_id_before = conn.execute(
                """
                SELECT id FROM email_cache
                WHERE email = ? AND folder = ? AND message_id = ?
                """,
                ("batch@example.com", "inbox", "2"),
            ).fetchone()["id"]

        assert await database.cache_emails(
            "batch@example.com",
            [{"id": "2", "subject": "updated"}],
        ) == 1

        with closing(original_create_connection()) as conn:
            row_after = conn.execute(
                """
                SELECT id, subject FROM email_cache
                WHERE email = ? AND folder = ? AND message_id = ?
                """,
                ("batch@example.com", "inbox", "2"),
            ).fetchone()

        assert row_after["id"] == row_id_before
        assert row_after["subject"] == "updated"


    @pytest.mark.asyncio
    async def test_batch_cache_enforces_retention_once(
        database: DatabaseManager,
        monkeypatch,
    ) -> None:
        monkeypatch.setattr(email_cache_module.settings, "email_cache_limit_per_account", 2)
        messages = [{"id": str(index), "subject": str(index)} for index in range(1, 4)]

        assert await database.cache_emails("limit@example.com", messages) == 3
        with closing(database.get_connection()) as conn:
            rows = conn.execute(
                """
                SELECT message_id FROM email_cache
                WHERE email = ? AND folder = ?
                ORDER BY created_at DESC, id DESC
                """,
                ("limit@example.com", "inbox"),
            ).fetchall()

        assert [row["message_id"] for row in rows] == ["3", "2"]


    @pytest.mark.asyncio
    async def test_imap_cache_path_batches_a_page_once(monkeypatch) -> None:
        calls: list[tuple[str, list[str], str | None]] = []

        async def fake_cache_emails(email, messages, folder=None):
            calls.append((email, [message["id"] for message in messages], folder))
            return len(messages)

        monkeypatch.setattr(shared_db_manager, "cache_emails", fake_cache_emails)
        client = IMAPEmailClient("imap@example.com", {"refresh_token": "refresh"})

        await client._cache_messages(
            "inbox",
            [{"id": "10"}, {"id": ""}, {"subject": "invalid"}, {"id": "11"}],
        )

        assert calls == [("imap@example.com", ["10", "11"], "inbox")]


    @pytest.mark.asyncio
    async def test_database_executor_is_lazy_and_wal_is_persistent(
        database: DatabaseManager,
    ) -> None:
        assert database._executor is None
        await database.get_cache_metadata("lazy@example.com")
        assert database._executor is not None

        with closing(database.get_connection()) as conn:
            assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
            assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    ''',
)

write(
    "tests/backend/test_static_assets.py",
    r'''
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.static_assets import (
        IMMUTABLE_ASSET_CACHE_CONTROL,
        PUBLIC_ASSET_CACHE_CONTROL,
        REVALIDATE_CACHE_CONTROL,
        CacheControlledStaticFiles,
        cache_control_for_path,
        resolve_static_file,
        static_file_response,
    )


    def test_cache_control_policy_distinguishes_hashed_assets() -> None:
        assert cache_control_for_path("assets/app.abc123.js") == IMMUTABLE_ASSET_CACHE_CONTROL
        assert cache_control_for_path("index.html") == REVALIDATE_CACHE_CONTROL
        assert cache_control_for_path("favicon.svg") == PUBLIC_ASSET_CACHE_CONTROL


    def test_resolve_static_file_blocks_path_traversal(tmp_path) -> None:
        static_dir = tmp_path / "static"
        static_dir.mkdir()
        favicon = static_dir / "favicon.svg"
        favicon.write_text("<svg />", encoding="utf-8")
        secret = tmp_path / "secret.txt"
        secret.write_text("secret", encoding="utf-8")

        assert resolve_static_file(static_dir, "favicon.svg") == favicon.resolve()
        assert resolve_static_file(static_dir, "../secret.txt") is None
        assert resolve_static_file(static_dir, "missing.svg") is None


    def test_file_response_has_path_specific_cache_header(tmp_path) -> None:
        asset = tmp_path / "asset.js"
        asset.write_text("console.log('ok')", encoding="utf-8")
        response = static_file_response(asset, "assets/asset.hash.js")
        assert response.headers["cache-control"] == IMMUTABLE_ASSET_CACHE_CONTROL


    def test_static_files_mount_sets_cache_header(tmp_path) -> None:
        asset = tmp_path / "asset.js"
        asset.write_text("console.log('ok')", encoding="utf-8")
        app = FastAPI()
        app.mount(
            "/",
            CacheControlledStaticFiles(
                directory=tmp_path,
                cache_control=IMMUTABLE_ASSET_CACHE_CONTROL,
            ),
        )

        response = TestClient(app).get("/asset.js")
        assert response.status_code == 200
        assert response.headers["cache-control"] == IMMUTABLE_ASSET_CACHE_CONTROL
    ''',
)

write(
    "tests/backend/test_lifecycle.py",
    r'''
    import logging

    import pytest

    from app.core.lifecycle import shutdown_application_resources


    @pytest.mark.asyncio
    async def test_shutdown_continues_when_independent_cleanup_steps_fail(caplog) -> None:
        calls: list[str] = []

        def stop_background_refresh() -> None:
            calls.append("refresh")
            raise RuntimeError("refresh failed")

        class EmailManager:
            async def cleanup_all(self) -> None:
                calls.append("email")
                raise RuntimeError("email failed")

        class DatabaseManager:
            def close(self) -> None:
                calls.append("database")

        caplog.set_level(logging.ERROR)
        await shutdown_application_resources(
            stop_background_refresh=stop_background_refresh,
            email_manager=EmailManager(),
            database_manager=DatabaseManager(),
        )

        assert calls == ["refresh", "email", "database"]
        assert "停止后台刷新任务失败" in caplog.text
        assert "清理邮箱客户端资源失败" in caplog.text
    ''',
)

write(
    "tests/frontend/unit/lib/telemetry.test.ts",
    r'''
    import { describe, expect, it } from 'vitest';
    import { captureException, initializeTelemetry } from '@/lib/telemetry';

    describe('telemetry', () => {
      it('is a safe no-op when no DSN is configured', async () => {
        expect(() => initializeTelemetry()).not.toThrow();
        expect(() => captureException(new Error('test'))).not.toThrow();
        await Promise.resolve();
      });
    });
    ''',
)

write(
    "scripts/benchmarks/benchmark_email_cache_batch.py",
    r'''
    #!/usr/bin/env python3
    """比较逐封写入和页级批量写入邮件缓存的耗时。"""

    import argparse
    import asyncio
    import statistics
    import sys
    import tempfile
    import time
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT / "backend"))

    from app.db.manager import DatabaseManager  # noqa: E402


    def make_messages(count: int) -> list[dict[str, object]]:
        return [
            {
                "id": str(index),
                "subject": f"benchmark-{index}",
                "sender": {
                    "emailAddress": {
                        "name": "Benchmark",
                        "address": "benchmark@example.com",
                    }
                },
                "receivedDateTime": "2026-01-01T00:00:00Z",
                "body": {"contentType": "text", "content": "x" * 256},
            }
            for index in range(count)
        ]


    async def measure_serial(manager: DatabaseManager, messages) -> float:
        started = time.perf_counter()
        for message in messages:
            await manager.cache_email(
                "serial@example.com",
                str(message["id"]),
                message,
            )
        return time.perf_counter() - started


    async def measure_batch(manager: DatabaseManager, messages) -> float:
        started = time.perf_counter()
        await manager.cache_emails("batch@example.com", messages)
        return time.perf_counter() - started


    async def run(count: int, rounds: int) -> None:
        serial_samples: list[float] = []
        batch_samples: list[float] = []
        messages = make_messages(count)

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseManager(str(Path(temp_dir) / "benchmark.db"))
            try:
                for _ in range(rounds):
                    await manager.clear_all_cache()
                    serial_samples.append(await measure_serial(manager, messages))
                    await manager.clear_all_cache()
                    batch_samples.append(await measure_batch(manager, messages))
            finally:
                manager.close()

        serial = statistics.median(serial_samples)
        batch = statistics.median(batch_samples)
        speedup = serial / batch if batch else float("inf")
        print(f"messages={count} rounds={rounds}")
        print(f"serial median: {serial:.4f}s")
        print(f"batch median:  {batch:.4f}s")
        print(f"speedup:       {speedup:.2f}x")


    if __name__ == "__main__":
        parser = argparse.ArgumentParser()
        parser.add_argument("--count", type=int, default=100)
        parser.add_argument("--rounds", type=int, default=5)
        args = parser.parse_args()
        asyncio.run(run(args.count, args.rounds))
    ''',
)

write(
    "docs/performance-cache.md",
    r'''
    # 资产与缓存性能

    ## 前端资产边界

    公开验证码页面与管理后台现在拥有独立的路由代码块。管理端页面、图表依赖和 Sentry 浏览器 SDK 不再无条件进入公开首屏；只有配置 `VITE_SENTRY_DSN` 时才会异步加载监控代码。

    Vite 内容哈希文件通过 `/assets` 返回一年期 `immutable` 缓存头，`index.html` 始终重新验证，根目录公共文件（例如 `favicon.svg`）按真实 MIME 类型返回。响应体大于 1000 字节时启用 GZip。

    生产构建后可查看资产清单与原始/GZip体积：

    ```bash
    npm --prefix frontend run build
    npm --prefix frontend run analyze:assets
    ```

    CI 同时执行类型检查、Lint、测试、生产构建和资产清单输出，避免入口文件、懒加载模块或构建图损坏后进入主分支。

    ## 邮件缓存热路径

    IMAP 一次抓取返回的一页邮件现在通过 `cache_emails` 一次写入：共享一个 SQLite 连接、一个事务和一次容量淘汰。单封 `cache_email` 保留为兼容入口，并复用同一实现。

    写入使用 UPSERT，不再通过 `INSERT OR REPLACE` 删除并重建行。缓存容量查询由 `(email, folder, created_at DESC, id DESC)` 覆盖索引支持；与主键或唯一约束重复的显式索引在初始化时清理。

    SQLite WAL 模式只在初始化阶段设置；连接级参数仍在每个连接上设置。数据库线程池改为首次异步查询时创建。应用关闭时，后台刷新、邮箱客户端和数据库线程池分别清理，一个步骤失败不会跳过后续资源。

    本地比较逐封与批量写入：

    ```bash
    python scripts/benchmarks/benchmark_email_cache_batch.py --count 100 --rounds 5
    ```
    ''',
)

# CI now validates the production asset graph rather than only unit tests.
ci_path = ROOT / ".github/workflows/ci.yml"
ci_content = ci_path.read_text(encoding="utf-8")
if "concurrency:\n" not in ci_content:
    ci_content = ci_content.replace(
        "name: CI\n\n",
        "name: CI\n\nconcurrency:\n  group: ci-${{ github.workflow }}-${{ github.ref }}\n  cancel-in-progress: true\n\n",
        1,
    )
ci_content = ci_content.replace(
    "node-version: '20'\n",
    "node-version: '20'\n          cache: npm\n          cache-dependency-path: frontend/package-lock.json\n",
    1,
)
frontend_test_marker = "      - name: Run frontend tests\n        working-directory: frontend\n        run: npm run test\n"
frontend_build_steps = frontend_test_marker + "\n      - name: Build frontend\n        working-directory: frontend\n        run: npm run build\n\n      - name: Report production assets\n        working-directory: frontend\n        run: npm run analyze:assets\n"
if "- name: Build frontend\n" not in ci_content:
    if frontend_test_marker not in ci_content:
        raise RuntimeError("Unable to locate frontend test step in CI workflow")
    ci_content = ci_content.replace(frontend_test_marker, frontend_build_steps, 1)
ci_path.write_text(ci_content, encoding="utf-8")

# Bootstrap files must not be visible in the resulting pull request.
for relative_path in (
    ".github/refactor/apply_refactor.py",
    ".github/workflows/apply-refactor.yml",
):
    (ROOT / relative_path).unlink(missing_ok=True)

refactor_dir = ROOT / ".github/refactor"
if refactor_dir.exists() and not any(refactor_dir.iterdir()):
    refactor_dir.rmdir()
