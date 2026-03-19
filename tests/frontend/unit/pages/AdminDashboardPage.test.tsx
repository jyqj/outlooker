import { describe, it, expect, vi, beforeAll, afterAll, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { showSuccess, showError } from '@/lib/toast';
import { MESSAGES } from '@/lib/constants';
import { logError } from '@/lib/utils';
import type { ReactElement } from 'react';

const { apiDefaultMock, mockClearAuthTokens } = vi.hoisted(() => ({
  apiDefaultMock: {
    get: vi.fn(),
    post: vi.fn(),
  },
  mockClearAuthTokens: vi.fn(),
}));

vi.mock('@/lib/api', () => ({
  default: apiDefaultMock,
  clearAuthTokens: mockClearAuthTokens,
  // useAccountsQuery 依赖该命名导出（内部会调用 default.get）
  getAccountsPaged: (params: unknown) =>
    apiDefaultMock.get('/api/accounts/paged', { params }).then((res: { data: unknown }) => res.data),
}));

vi.mock('@/lib/toast', () => ({
  showSuccess: vi.fn(),
  showError: vi.fn(),
}));

vi.mock('@/lib/utils', async () => {
  const actual = await vi.importActual('@/lib/utils');
  return {
    ...actual,
    logError: vi.fn(),
  };
});

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

import api from '@/lib/api';
import AdminDashboardPage from '@/pages/AdminDashboardPage';

type MockApi = {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
};

const apiMock = api as unknown as MockApi;

function renderWithProviders(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        {ui}
      </MemoryRouter>
    </QueryClientProvider>
  );
}

interface MockDashboardOptions {
  exportError?: unknown;
  exportResponse?: unknown;
  accountItems?: Array<{ email: string }>;
  accountTotal?: number;
}

function mockBasicDashboardData(options: MockDashboardOptions = {}) {
  apiMock.get.mockImplementation((url: string) => {
    if (url === '/api/export') {
      if (options.exportError) {
        return Promise.reject(options.exportError);
      }
      if (options.exportResponse) {
        return Promise.resolve(options.exportResponse);
      }
      return Promise.resolve({
        data: new Blob(['mock-export']),
      });
    }
    if (url.includes('/api/accounts/paged')) {
      return Promise.resolve({
        data: {
          success: true,
          data: {
            items: options.accountItems || [],
            total:
              options.accountTotal ??
              (options.accountItems ? options.accountItems.length : 0),
            page: 1,
            page_size: 10,
          },
        },
      });
    }
    if (url.includes('/api/accounts/tags')) {
      return Promise.resolve({
        data: {
          success: true,
          data: { tags: [], accounts: {} },
        },
      });
    }
    if (url.includes('/api/system/config')) {
      return Promise.resolve({
        data: {
          success: true,
          data: { email_limit: 5 },
        },
      });
    }
    if (url.includes('/api/system/metrics')) {
      return Promise.resolve({
        data: {
          success: true,
          data: {
            email_manager: {
              cache_hits: 0,
              cache_misses: 0,
              client_reuses: 0,
              client_creates: 0,
              accounts_count: 0,
            },
          },
        },
      });
    }
    return Promise.resolve({ data: { success: true, data: {} } });
  });

  apiMock.post.mockImplementation(() =>
    Promise.resolve({ data: { success: true, data: {} } }),
  );
}

const originalCreateObjectURL = global.URL.createObjectURL;

beforeAll(() => {
  (global.URL as unknown as { createObjectURL: unknown }).createObjectURL = vi.fn(
    () => 'blob:mock-url',
  );
});

afterAll(() => {
  (global.URL as unknown as { createObjectURL: unknown }).createObjectURL = originalCreateObjectURL;
});

describe('AdminDashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.setItem('admin_token', 'test-token');
  });

  afterEach(() => {
    sessionStorage.clear();
  });

  it('loads and renders account list', async () => {
    apiMock.get.mockImplementation((url: string) => {
      if (url.includes('/api/accounts/paged')) {
        return Promise.resolve({
          data: {
            success: true,
            data: {
              items: [
                { email: 'test1@example.com' },
                { email: 'test2@example.com' },
              ],
              total: 2,
              page: 1,
              page_size: 10,
            },
          },
        });
      }
      if (url.includes('/api/accounts/tags')) {
        return Promise.resolve({
          data: {
            success: true,
            data: { tags: [], accounts: {} },
          },
        });
      }
      if (url.includes('/api/system/config')) {
        return Promise.resolve({
          data: {
            success: true,
            data: { email_limit: 5 },
          },
        });
      }
      if (url.includes('/api/system/metrics')) {
        return Promise.resolve({
          data: {
            success: true,
            data: {
              email_manager: {
                cache_hits: 10,
                cache_misses: 2,
                client_reuses: 5,
                client_creates: 3,
                accounts_count: 2,
              },
            },
          },
        });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    renderWithProviders(<AdminDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('test1@example.com')).toBeInTheDocument();
      expect(screen.getByText('test2@example.com')).toBeInTheDocument();
    });
  });

  it('handles pagination buttons', async () => {
    apiMock.get.mockImplementation((url: string) => {
      if (url.includes('/api/accounts/paged')) {
        return Promise.resolve({
          data: {
            success: true,
            data: {
              items: [{ email: 'test@example.com' }],
              total: 25,
              page: 1,
              page_size: 10,
            },
          },
        });
      }
      return Promise.resolve({ data: { success: true, data: {} } });
    });

    const user = userEvent.setup();
    renderWithProviders(<AdminDashboardPage />);

    // Wait for page to load - check for total records text instead
    await waitFor(() => {
      expect(screen.getByText(/共 25 条记录/)).toBeInTheDocument();
    });

    // Click next page button
    const nextButton = screen
      .getAllByRole('button')
      .find((btn) => btn.querySelector('svg')?.classList.contains('lucide-chevron-right')) as
      | HTMLButtonElement
      | undefined;

    if (nextButton && !nextButton.disabled) {
      await user.click(nextButton);

      await waitFor(() => {
        expect(apiMock.get).toHaveBeenCalledWith(
          '/api/accounts/paged',
          expect.objectContaining({
            params: expect.objectContaining({ page: 2 }),
          })
        );
      });
    }
  });

  it('filters accounts by search query', async () => {
    apiMock.get.mockImplementation((url: string, config?: { params?: { q?: string } }) => {
      if (url.includes('/api/accounts/paged')) {
        const searchQuery = config?.params?.q || '';
        return Promise.resolve({
          data: {
            success: true,
            data: {
              items: searchQuery ? [{ email: 'filtered@example.com' }] : [],
              total: searchQuery ? 1 : 0,
              page: 1,
              page_size: 10,
            },
          },
        });
      }
      return Promise.resolve({ data: { success: true, data: {} } });
    });

    const user = userEvent.setup();
    renderWithProviders(<AdminDashboardPage />);

    const searchInput = screen.getByPlaceholderText(/搜索邮箱/);
    await user.type(searchInput, 'filtered');

    await waitFor(() => {
      expect(apiMock.get).toHaveBeenCalledWith(
        '/api/accounts/paged',
        expect.objectContaining({
          params: expect.objectContaining({ q: 'filtered' }),
        })
      );
    });
  });

  it('opens import modal when import button is clicked', async () => {
    apiMock.get.mockImplementation((url: string) => {
      if (url.includes('/api/accounts/paged')) {
        return Promise.resolve({
          data: {
            success: true,
            data: { items: [], total: 0, page: 1, page_size: 10 },
          },
        });
      }
      return Promise.resolve({ data: { success: true, data: {} } });
    });

    const user = userEvent.setup();
    renderWithProviders(<AdminDashboardPage />);

    const importButton = await screen.findByRole('button', { name: /导入/ });
    await user.click(importButton);

    // ImportModal should be visible
    await waitFor(() => {
      expect(screen.getByText(/批量导入账户/)).toBeInTheDocument();
    });
  });

  it('handles logout', async () => {
    apiMock.get.mockResolvedValue({
      data: { success: true, data: { items: [], total: 0 } },
    });
    apiMock.post.mockResolvedValue({ data: { success: true } });

    const user = userEvent.setup();
    renderWithProviders(<AdminDashboardPage />);

    const logoutButton = await screen.findByText(/退出/);
    await user.click(logoutButton);

    await waitFor(() => {
      expect(apiMock.post).toHaveBeenCalledWith('/api/admin/logout', {});
    });
    expect(mockClearAuthTokens).toHaveBeenCalled();
    expect(mockNavigate).toHaveBeenCalledWith('/admin/login');
  });

  it('renders overview summary correctly', async () => {
    apiMock.get.mockImplementation((url: string) => {
      if (url.includes('/api/dashboard/summary')) {
        return Promise.resolve({
          data: {
            success: true,
            data: {
              health: {
                total: 42,
                healthy: 40,
                token_expired: 1,
                token_invalid: 1,
                error: 0,
                unknown: 0,
              },
              tags: {
                tagged_accounts: 30,
                untagged_accounts: 12,
                tags: [{ name: 'alpha', count: 30, percentage: 71.4 }],
              },
              alerts: [],
              recent_events: [],
            },
          },
        });
      }
      if (url.includes('/api/accounts/paged')) {
        return Promise.resolve({
          data: {
            success: true,
            data: { items: [], total: 0, page: 1, page_size: 10 },
          },
        });
      }
      return Promise.resolve({ data: { success: true, data: {} } });
    });

    renderWithProviders(<AdminDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('账户总数')).toBeInTheDocument();
      expect(screen.getByText('标签分布')).toBeInTheDocument();
      expect(screen.getByText('42')).toBeInTheDocument();
      expect(screen.getByText(/已标记: 30/)).toBeInTheDocument();
    });
  });

  it('shows success toast when export succeeds', async () => {
    mockBasicDashboardData();
    const user = userEvent.setup();
    renderWithProviders(<AdminDashboardPage />);

    const exportButton = await screen.findByText(/导出/);
    await user.click(exportButton);

    await waitFor(() => {
      expect(showSuccess).toHaveBeenCalledWith(MESSAGES.SUCCESS_EXPORT);
    });
    expect(showError).not.toHaveBeenCalled();
  });

  it('logs and shows toast when export fails', async () => {
    const exportError: any = new Error('boom');
    exportError.response = { data: { message: '导出接口失败' } };
    mockBasicDashboardData({ exportError });

    const user = userEvent.setup();
    renderWithProviders(<AdminDashboardPage />);

    const exportButton = await screen.findByText(/导出/);
    await user.click(exportButton);

    await waitFor(() => {
      expect(showError).toHaveBeenCalledWith('导出接口失败');
    });
    expect(logError).toHaveBeenCalledWith('导出失败', exportError);
  });

  it('shows error state and retries loading accounts', async () => {
    const user = userEvent.setup();
    let accountCall = 0;

    apiMock.get.mockImplementation((url: string) => {
      if (url.includes('/api/accounts/paged')) {
        accountCall += 1;
        if (accountCall === 1) {
          return Promise.reject(new Error('load-fail'));
        }
        return Promise.resolve({
          data: {
            success: true,
            data: { items: [], total: 0, page: 1, page_size: 10 },
          },
        });
      }
      if (url.includes('/api/accounts/tags')) {
        return Promise.resolve({
          data: { success: true, data: { tags: [], accounts: {} } },
        });
      }
      if (url.includes('/api/system/config')) {
        return Promise.resolve({
          data: { success: true, data: { email_limit: 5 } },
        });
      }
      if (url.includes('/api/system/metrics')) {
        return Promise.resolve({
          data: {
            success: true,
            data: {
              email_manager: {
                cache_hits: 0,
                cache_misses: 0,
                client_reuses: 0,
                client_creates: 0,
                accounts_count: 0,
              },
            },
          },
        });
      }
      return Promise.resolve({ data: { success: true, data: {} } });
    });

    renderWithProviders(<AdminDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/加载账户列表失败/)).toBeInTheDocument();
    });

    await user.click(screen.getByText(/重新加载/));

    await waitFor(() => {
      expect(screen.getByText(/暂无账户数据/)).toBeInTheDocument();
    });
    expect(accountCall).toBeGreaterThanOrEqual(2);
  });
});
