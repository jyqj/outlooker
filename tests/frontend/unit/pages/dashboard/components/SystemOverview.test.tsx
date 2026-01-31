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
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders email limit config card', () => {
    renderWithQueryClient(<SystemOverview />);
    expect(screen.getByText('邮件获取限制')).toBeInTheDocument();
  });

  it('renders system metrics card', () => {
    renderWithQueryClient(<SystemOverview />);
    expect(screen.getByText('系统指标')).toBeInTheDocument();
  });

  it('displays email limit input', () => {
    renderWithQueryClient(<SystemOverview />);
    const input = screen.getByRole('spinbutton');
    expect(input).toBeInTheDocument();
  });

  it('displays save button for config', () => {
    renderWithQueryClient(<SystemOverview />);
    expect(screen.getByRole('button', { name: '保存' })).toBeInTheDocument();
  });

  it('displays refresh cache button', () => {
    renderWithQueryClient(<SystemOverview />);
    expect(screen.getByRole('button', { name: '刷新缓存' })).toBeInTheDocument();
  });

  it('displays metrics labels', () => {
    renderWithQueryClient(<SystemOverview />);
    
    expect(screen.getByText('缓存命中')).toBeInTheDocument();
    expect(screen.getByText('缓存未命中')).toBeInTheDocument();
    expect(screen.getByText('IMAP 复用')).toBeInTheDocument();
    expect(screen.getByText('IMAP 创建')).toBeInTheDocument();
    expect(screen.getByText('缓存命中率')).toBeInTheDocument();
  });

  it('allows changing email limit value', () => {
    renderWithQueryClient(<SystemOverview />);
    
    const input = screen.getByRole('spinbutton');
    fireEvent.change(input, { target: { value: '10' } });
    
    expect(input).toHaveValue(10);
  });

  it('calls API when save button is clicked', async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: { success: true },
    });

    renderWithQueryClient(<SystemOverview />);
    
    const input = screen.getByRole('spinbutton');
    fireEvent.change(input, { target: { value: '15' } });
    
    const saveButton = screen.getByRole('button', { name: '保存' });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/api/system/config', { email_limit: 15 });
    });
  });

  it('shows saving state when save is in progress', async () => {
    (api.post as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({ data: { success: true } }), 100))
    );

    renderWithQueryClient(<SystemOverview />);
    
    const saveButton = screen.getByRole('button', { name: '保存' });
    fireEvent.click(saveButton);

    expect(screen.getByText('保存中...')).toBeInTheDocument();
  });

  it('calls API when refresh cache button is clicked', async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: { success: true },
    });

    renderWithQueryClient(<SystemOverview />);
    
    const refreshButton = screen.getByRole('button', { name: '刷新缓存' });
    fireEvent.click(refreshButton);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/api/system/cache/refresh');
    });
  });

  it('shows refreshing state when cache refresh is in progress', async () => {
    (api.post as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({ data: { success: true } }), 100))
    );

    renderWithQueryClient(<SystemOverview />);
    
    const refreshButton = screen.getByRole('button', { name: '刷新缓存' });
    fireEvent.click(refreshButton);

    expect(screen.getByText('刷新中...')).toBeInTheDocument();
  });

  it('renders with two-column grid layout', () => {
    const { container } = renderWithQueryClient(<SystemOverview />);
    const grid = container.querySelector('.grid');
    expect(grid).toHaveClass('grid-cols-1');
    expect(grid).toHaveClass('md:grid-cols-2');
  });
});
