import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import type { ReactElement } from 'react';

const { apiMock, hooksMock } = vi.hoisted(() => ({
  apiMock: {
    get: vi.fn(),
    post: vi.fn(),
  },
  hooksMock: {
    useOutlookAccountsQuery: vi.fn(),
    useOutlookAccountDetailQuery: vi.fn(),
    useOutlookProfileQuery: vi.fn(),
    useOutlookAuthMethodsQuery: vi.fn(),
    useOutlookMailboxSettingsQuery: vi.fn(),
    useOutlookRegionalSettingsQuery: vi.fn(),
  },
}));

vi.mock('@/lib/api', () => ({
  default: apiMock,
  clearAuthTokens: vi.fn(),
  getStoredAccessToken: vi.fn(() => 'token'),
  isAccessTokenValid: vi.fn(() => true),
}));

vi.mock('@/lib/api/outlook-accounts-api', () => ({
  batchRefreshOutlookTokens: vi.fn(() => Promise.resolve({ success: true })),
  updateOutlookProfile: vi.fn(() => Promise.resolve({ success: true })),
  updateOutlookMailboxSettings: vi.fn(() => Promise.resolve({ success: true })),
  updateOutlookRegionalSettings: vi.fn(() => Promise.resolve({ success: true })),
  changeOutlookPassword: vi.fn(() => Promise.resolve({ success: true })),
  revokeOutlookSessions: vi.fn(() => Promise.resolve({ success: true })),
  getOutlookRiskyUsers: vi.fn(() => Promise.resolve({ data: { value: [] } })),
  dismissOutlookRisk: vi.fn(() => Promise.resolve({ success: true })),
}));

vi.mock('@/lib/hooks', () => hooksMock);

vi.mock('@/pages/dashboard/components/DashboardHeader', () => ({
  DashboardHeader: ({ onLogout }: { onLogout: () => void }) => (
    <div>
      <button onClick={onLogout}>logout</button>
      <span>header</span>
    </div>
  ),
}));

import OutlookAccountsPage from '@/pages/outlook/OutlookAccountsPage';
import OutlookAccountDetailPage from '@/pages/outlook/OutlookAccountDetailPage';
import OutlookTasksPage from '@/pages/outlook/OutlookTasksPage';
import AuxEmailPoolPage from '@/pages/outlook/AuxEmailPoolPage';
import ChannelConsolePage from '@/pages/outlook/ChannelConsolePage';

class MockEventSource {
  onmessage: ((this: EventSource, ev: MessageEvent) => unknown) | null = null;
  close() {}
}

(globalThis as unknown as { EventSource: typeof EventSource }).EventSource =
  MockEventSource as unknown as typeof EventSource;

function renderWithProviders(ui: ReactElement, route = '/') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        {ui}
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('Outlook workbench pages', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    hooksMock.useOutlookAccountsQuery.mockReturnValue({
      data: {
        data: {
          items: [
            {
              email: 'user@example.com',
              status: 'active',
              account_type: 'consumer',
              token: { status: 'active' },
              capabilities: { graph_ready: true },
            },
          ],
          total: 1,
        },
      },
      isLoading: false,
    });
    hooksMock.useOutlookAccountDetailQuery.mockReturnValue({
      data: {
        data: {
          email: 'user@example.com',
          status: 'active',
          account_type: 'consumer',
          token: { status: 'active' },
          capabilities: { graph_ready: true },
        },
      },
      isLoading: false,
    });
    hooksMock.useOutlookProfileQuery.mockReturnValue({ data: { data: { displayName: 'User' } } });
    hooksMock.useOutlookAuthMethodsQuery.mockReturnValue({
      data: { data: { email_methods: [], totp_methods: [], phone_methods: [] } },
    });
    hooksMock.useOutlookMailboxSettingsQuery.mockReturnValue({ data: { data: { timeZone: 'UTC' } } });
    hooksMock.useOutlookRegionalSettingsQuery.mockReturnValue({ data: { data: { locale: 'en-US' } } });

    apiMock.get.mockImplementation((url: string) => {
      if (url === '/api/outlook/tasks') {
        return Promise.resolve({ data: { data: { items: [{ id: 1, task_type: 'bind', status: 'pending', target_email: 'user@example.com' }] } } });
      }
      if (url === '/api/outlook/tasks/1') {
        return Promise.resolve({ data: { data: { task: { id: 1, task_type: 'bind', status: 'pending' }, steps: [] } } });
      }
      if (url === '/api/outlook/resources/aux-emails') {
        return Promise.resolve({ data: { data: { items: [{ id: 1, address: 'aux@example.com', status: 'available', fail_count: 0 }] } } });
      }
      if (url === '/api/outlook/channels') {
        return Promise.resolve({ data: { data: { items: [{ id: 1, code: 'ch1', name: 'Channel 1', status: 'active', priority: 10 }] } } });
      }
      if (url === '/api/outlook/channels/stats') {
        return Promise.resolve({ data: { data: { tasks: { total: 1, success_rate: 1 } } } });
      }
      return Promise.resolve({ data: { success: true, data: {} } });
    });
    apiMock.post.mockResolvedValue({ data: { success: true, data: {} } });
  });

  it('renders outlook accounts page', async () => {
    renderWithProviders(<OutlookAccountsPage />);
    expect(screen.getByText(/Outlook 账户/)).toBeInTheDocument();
    expect(screen.getByText('user@example.com')).toBeInTheDocument();
  });

  it('renders outlook account detail page', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/admin/outlook/accounts/:email" element={<OutlookAccountDetailPage />} />
      </Routes>,
      '/admin/outlook/accounts/user%40example.com'
    );
    expect(screen.getByText(/账户详情/)).toBeInTheDocument();
    expect(screen.getByText(/Graph: Ready/)).toBeInTheDocument();
  });

  it('renders tasks page with loaded task', async () => {
    renderWithProviders(<OutlookTasksPage />);
    await waitFor(() => {
      expect(screen.getByText(/任务状态/)).toBeInTheDocument();
      expect(screen.getByText(/#1/)).toBeInTheDocument();
    });
  });

  it('renders aux email pool page with resources', async () => {
    renderWithProviders(<AuxEmailPoolPage />);
    await waitFor(() => {
      expect(screen.getByText(/辅助邮箱资源池/)).toBeInTheDocument();
      expect(screen.getByText(/aux@example.com/)).toBeInTheDocument();
    });
  });

  it('renders channel console page with channels', async () => {
    renderWithProviders(<ChannelConsolePage />);
    await waitFor(() => {
      expect(screen.getByText(/渠道控制台/)).toBeInTheDocument();
      expect(screen.getByText(/Channel 1/)).toBeInTheDocument();
    });
  });
});
