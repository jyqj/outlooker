import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import type { ReactElement } from 'react';

const { apiMock, hooksMock, outlookApiMock, accountsRefetch, detailRefetch } = vi.hoisted(() => ({
  apiMock: {
    get: vi.fn(),
    post: vi.fn(),
  },
  hooksMock: {
    useDebounce: vi.fn((value: unknown) => value),
    useOutlookAccountsQuery: vi.fn(),
    useOutlookAccountDetailQuery: vi.fn(),
    useOutlookProfileQuery: vi.fn(),
    useOutlookAuthMethodsQuery: vi.fn(),
    useOutlookMailboxSettingsQuery: vi.fn(),
    useOutlookRegionalSettingsQuery: vi.fn(),
  },
  outlookApiMock: {
    batchRefreshOutlookTokens: vi.fn(() => Promise.resolve({ success: true })),
    refreshOutlookToken: vi.fn(() => Promise.resolve({ success: true })),
    updateOutlookProfile: vi.fn(() => Promise.resolve({ success: true })),
    updateOutlookMailboxSettings: vi.fn(() => Promise.resolve({ success: true })),
    updateOutlookRegionalSettings: vi.fn(() => Promise.resolve({ success: true })),
    changeOutlookPassword: vi.fn(() => Promise.resolve({ success: true })),
    revokeOutlookSessions: vi.fn(() => Promise.resolve({ success: true })),
    getOutlookRiskyUsers: vi.fn(() => Promise.resolve({ data: { value: [] } })),
    dismissOutlookRisk: vi.fn(() => Promise.resolve({ success: true })),
  },
  accountsRefetch: vi.fn(() => Promise.resolve({ data: undefined })),
  detailRefetch: vi.fn(() => Promise.resolve({ data: undefined })),
}));

vi.mock('@/lib/api', () => ({
  default: apiMock,
  clearAuthTokens: vi.fn(),
  getStoredAccessToken: vi.fn(() => 'token'),
  isAccessTokenValid: vi.fn(() => true),
}));

vi.mock('@/lib/api/outlook-accounts-api', () => outlookApiMock);
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
  const rendered = render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
  return { ...rendered, queryClient };
}

describe('Outlook workbench pages', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    hooksMock.useDebounce.mockImplementation((value: unknown) => value);
    hooksMock.useOutlookAccountsQuery.mockReturnValue({
      data: {
        data: {
          items: [
            {
              email: 'user@example.com',
              status: 'active',
              account_type: 'consumer',
              token: {
                status: 'active',
                has_access_token: true,
                has_refresh_token: true,
              },
              capabilities: { graph_ready: true },
            },
          ],
          total: 1,
          limit: 20,
          offset: 0,
        },
      },
      isLoading: false,
      isFetching: false,
      refetch: accountsRefetch,
    });
    hooksMock.useOutlookAccountDetailQuery.mockReturnValue({
      data: {
        data: {
          email: 'user@example.com',
          status: 'active',
          account_type: 'consumer',
          token: {
            status: 'active',
            expires_at: '2030-01-01T00:00:00+00:00',
            has_access_token: true,
            has_refresh_token: true,
          },
          capabilities: { graph_ready: true },
        },
      },
      isLoading: false,
      refetch: detailRefetch,
    });
    hooksMock.useOutlookProfileQuery.mockReturnValue({ data: { data: { displayName: 'User' } } });
    hooksMock.useOutlookAuthMethodsQuery.mockReturnValue({
      data: { data: { email_methods: [], totp_methods: [], phone_methods: [] } },
    });
    hooksMock.useOutlookMailboxSettingsQuery.mockReturnValue({ data: { data: { timeZone: 'UTC' } } });
    hooksMock.useOutlookRegionalSettingsQuery.mockReturnValue({ data: { data: { locale: 'en-US' } } });

    apiMock.get.mockImplementation((url: string) => {
      if (url === '/api/outlook/tasks') {
        return Promise.resolve({
          data: {
            data: {
              items: [
                {
                  id: 1,
                  task_type: 'bind',
                  status: 'pending',
                  target_email: 'user@example.com',
                },
              ],
            },
          },
        });
      }
      if (url === '/api/outlook/tasks/1') {
        return Promise.resolve({
          data: {
            data: {
              task: { id: 1, task_type: 'bind', status: 'pending' },
              steps: [],
            },
          },
        });
      }
      if (url === '/api/outlook/resources/aux-emails') {
        return Promise.resolve({
          data: {
            data: {
              items: [
                {
                  id: 1,
                  address: 'aux@example.com',
                  status: 'available',
                  fail_count: 0,
                },
              ],
            },
          },
        });
      }
      if (url === '/api/outlook/channels') {
        return Promise.resolve({
          data: {
            data: {
              items: [
                {
                  id: 1,
                  code: 'ch1',
                  name: 'Channel 1',
                  status: 'active',
                  priority: 10,
                },
              ],
            },
          },
        });
      }
      if (url === '/api/outlook/channels/stats') {
        return Promise.resolve({ data: { data: { tasks: { total: 1, success_rate: 1 } } } });
      }
      return Promise.resolve({ data: { success: true, data: {} } });
    });
    apiMock.post.mockResolvedValue({ data: { success: true, data: {} } });
  });

  it('renders the secret-free account health projection', () => {
    renderWithProviders(<OutlookAccountsPage />);
    expect(screen.getByText(/Outlook 账户/)).toBeInTheDocument();
    expect(screen.getByText('user@example.com')).toBeInTheDocument();
    expect(screen.getByText(/Refresh Ready/)).toBeInTheDocument();
  });

  it('refreshes only the current Outlook list query from the toolbar', async () => {
    renderWithProviders(<OutlookAccountsPage />);
    fireEvent.click(screen.getByRole('button', { name: '刷新' }));
    await waitFor(() => expect(accountsRefetch).toHaveBeenCalledTimes(1));
  });

  it('refreshes token metadata and the account detail projection', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/admin/outlook/accounts/:email" element={<OutlookAccountDetailPage />} />
      </Routes>,
      '/admin/outlook/accounts/user%40example.com'
    );

    fireEvent.click(screen.getByRole('button', { name: '刷新 Token' }));
    await waitFor(() => {
      expect(outlookApiMock.refreshOutlookToken).toHaveBeenCalledWith('user@example.com');
      expect(detailRefetch).toHaveBeenCalledTimes(1);
    });
  });

  it('renders outlook account detail page', () => {
    renderWithProviders(
      <Routes>
        <Route path="/admin/outlook/accounts/:email" element={<OutlookAccountDetailPage />} />
      </Routes>,
      '/admin/outlook/accounts/user%40example.com'
    );
    expect(screen.getByText(/账户详情/)).toBeInTheDocument();
    expect(screen.getByText(/Graph: Ready/)).toBeInTheDocument();
    expect(screen.getByText(/Refresh: Ready/)).toBeInTheDocument();
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
