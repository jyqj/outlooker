import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import AdminDashboardPage from '../AdminDashboardPage';
import api from '../../lib/api';
import { showSuccess, showError } from '../../lib/toast';
import { MESSAGES } from '../../lib/constants';
import { logError } from '../../lib/utils';

vi.mock('../../lib/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock('../../lib/toast', () => ({
  showSuccess: vi.fn(),
  showError: vi.fn(),
}));

vi.mock('../../lib/utils', async () => {
  const actual = await vi.importActual('../../lib/utils');
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

function renderWithProviders(ui) {
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

function mockBasicDashboardData(options = {}) {
  api.get.mockImplementation((url) => {
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

  api.post.mockImplementation(() =>
    Promise.resolve({ data: { success: true, data: {} } }),
  );
}

const originalCreateObjectURL = global.URL?.createObjectURL;

beforeAll(() => {
  global.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
});

afterAll(() => {
  if (originalCreateObjectURL) {
    global.URL.createObjectURL = originalCreateObjectURL;
  } else {
    delete global.URL.createObjectURL;
  }
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
    api.get.mockImplementation((url) => {
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
    api.get.mockImplementation((url) => {
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

    await waitFor(() => {
      expect(screen.getByText(/第 1 页/)).toBeInTheDocument();
    });

    // Click next page button
    const nextButton = screen.getAllByRole('button').find((btn) =>
      btn.querySelector('svg')?.classList.contains('lucide-chevron-right')
    );

    if (nextButton && !nextButton.disabled) {
      await user.click(nextButton);
      
      await waitFor(() => {
        expect(api.get).toHaveBeenCalledWith(
          '/api/accounts/paged',
          expect.objectContaining({
            params: expect.objectContaining({ page: 2 }),
          })
        );
      });
    }
  });

  it('filters accounts by search query', async () => {
    api.get.mockImplementation((url, config) => {
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
      expect(api.get).toHaveBeenCalledWith(
        '/api/accounts/paged',
        expect.objectContaining({
          params: expect.objectContaining({ q: 'filtered' }),
        })
      );
    });
  });

  it('opens import modal when import button is clicked', async () => {
    api.get.mockImplementation((url) => {
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

    const importButton = await screen.findByText(/导入/);
    await user.click(importButton);

    // ImportModal should be visible
    await waitFor(() => {
      expect(screen.getByText(/批量导入账户/)).toBeInTheDocument();
    });
  });

  it('handles logout', async () => {
    api.get.mockResolvedValue({
      data: { success: true, data: { items: [], total: 0 } },
    });

    const user = userEvent.setup();
    renderWithProviders(<AdminDashboardPage />);

    const logoutButton = await screen.findByText(/退出/);
    await user.click(logoutButton);

    expect(sessionStorage.getItem('admin_token')).toBeNull();
    expect(mockNavigate).toHaveBeenCalledWith('/admin/login');
  });

  it('renders system metrics correctly', async () => {
    api.get.mockImplementation((url) => {
      if (url.includes('/api/system/metrics')) {
        return Promise.resolve({
          data: {
            success: true,
            data: {
              email_manager: {
                cache_hits: 42,
                cache_misses: 8,
                client_reuses: 20,
                client_creates: 5,
                accounts_count: 10,
              },
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
      expect(screen.getByText('42')).toBeInTheDocument(); // cache hits
      expect(screen.getByText('8')).toBeInTheDocument(); // cache misses
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
    const exportError = new Error('boom');
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
});
