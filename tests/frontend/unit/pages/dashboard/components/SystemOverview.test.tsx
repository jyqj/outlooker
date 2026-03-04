import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SystemOverview } from '@/pages/dashboard/components/SystemOverview';
import api from '@/lib/api';

vi.mock('@/lib/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock('@/lib/toast', () => ({
  showSuccess: vi.fn(),
  showError: vi.fn(),
}));

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

const renderWithQueryClient = (ui: React.ReactElement) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
};

describe('SystemOverview', () => {
  const apiGet = api.get as unknown as ReturnType<typeof vi.fn>;
  const apiPost = api.post as unknown as ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();

    apiGet.mockImplementation((url: string) => {
      if (url === '/api/system/config') {
        return Promise.resolve({
          data: { success: true, data: { email_limit: 5 } },
        });
      }
      if (url === '/api/system/metrics') {
        return Promise.resolve({
          data: {
            success: true,
            data: {
              email_manager: {
                accounts_count: 2,
                email_cache: { total_messages: 10 },
              },
            },
          },
        });
      }
      return Promise.resolve({ data: { success: true, data: {} } });
    });

    apiPost.mockResolvedValue({ data: { success: true } });
  });

  it('renders overview cards', () => {
    renderWithQueryClient(<SystemOverview />);
    expect(screen.getByText('账户总数')).toBeInTheDocument();
    expect(screen.getByText('缓存邮件')).toBeInTheDocument();
    expect(screen.getByText('邮件获取限制')).toBeInTheDocument();
  });

  it('renders metrics values from API', async () => {
    renderWithQueryClient(<SystemOverview />);
    expect(await screen.findByText('2')).toBeInTheDocument();
    expect(await screen.findByText('10')).toBeInTheDocument();
  });

  it('calls API when save button is clicked', async () => {
    renderWithQueryClient(<SystemOverview />);

    const input = screen.getByRole('spinbutton');
    fireEvent.change(input, { target: { value: '15' } });

    fireEvent.click(screen.getByRole('button', { name: '保存' }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/api/system/config', { email_limit: 15 });
    });
  });

  it('shows saving state while saving', () => {
    apiPost.mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({ data: { success: true } }), 100))
    );

    renderWithQueryClient(<SystemOverview />);
    fireEvent.click(screen.getByRole('button', { name: '保存' }));

    // 当前实现使用省略号表示保存中状态
    expect(screen.getByRole('button', { name: '...' })).toBeInTheDocument();
  });

  it('calls API when cache clear button is clicked', async () => {
    renderWithQueryClient(<SystemOverview />);

    fireEvent.click(screen.getByRole('button', { name: '清理' }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/api/system/cache/refresh');
    });
  });

  it('shows refreshing state while clearing cache', () => {
    apiPost.mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({ data: { success: true } }), 100))
    );

    renderWithQueryClient(<SystemOverview />);
    fireEvent.click(screen.getByRole('button', { name: '清理' }));

    expect(screen.getByText('清理中')).toBeInTheDocument();
  });

  it('renders with three-column grid layout on desktop', () => {
    const { container } = renderWithQueryClient(<SystemOverview />);
    const grid = container.querySelector('.grid');
    expect(grid).toHaveClass('grid-cols-1');
    expect(grid).toHaveClass('md:grid-cols-3');
  });
});
