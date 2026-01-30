import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import EmailViewModal from '../EmailViewModal';
import api from '../../lib/api';

vi.mock('../../lib/api', () => ({
  default: {
    get: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('../../lib/toast', () => ({
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

describe('EmailViewModal', () => {
  const mockOnClose = vi.fn();
  const mockEmail = 'test@example.com';

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not render when closed', () => {
    renderWithQueryClient(
      <EmailViewModal email={mockEmail} isOpen={false} onClose={mockOnClose} />
    );

    expect(screen.queryByText(mockEmail)).not.toBeInTheDocument();
  });

  it('renders email header when open', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: {
        success: true,
        data: { items: [] },
      },
    });

    renderWithQueryClient(
      <EmailViewModal email={mockEmail} isOpen={true} onClose={mockOnClose} />
    );

    expect(screen.getByText(mockEmail)).toBeInTheDocument();
    expect(screen.getByText('最新邮件预览')).toBeInTheDocument();
  });

  it('shows loading state while fetching', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise(() => {}) // Never resolves to keep loading state
    );

    renderWithQueryClient(
      <EmailViewModal email={mockEmail} isOpen={true} onClose={mockOnClose} />
    );

    expect(screen.getByText('正在获取邮件...')).toBeInTheDocument();
  });

  it('shows error state on fetch failure', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('Network error'));

    renderWithQueryClient(
      <EmailViewModal email={mockEmail} isOpen={true} onClose={mockOnClose} />
    );

    await waitFor(() => {
      expect(screen.getByText('加载邮件失败')).toBeInTheDocument();
    });
  });

  it('shows empty state when no messages', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: {
        success: true,
        data: { items: [] },
      },
    });

    renderWithQueryClient(
      <EmailViewModal email={mockEmail} isOpen={true} onClose={mockOnClose} />
    );

    await waitFor(() => {
      expect(screen.getByText('该邮箱暂无邮件')).toBeInTheDocument();
    });
  });

  it('displays email content when message exists', async () => {
    const mockMessage = {
      id: 'msg-123',
      subject: 'Test Subject',
      receivedDateTime: '2025-01-20T10:00:00Z',
      sender: {
        emailAddress: {
          name: 'Sender Name',
          address: 'sender@example.com',
        },
      },
      body: {
        content: 'Test email body content',
        contentType: 'text',
      },
    };

    (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: {
        success: true,
        data: { items: [mockMessage] },
      },
    });

    renderWithQueryClient(
      <EmailViewModal email={mockEmail} isOpen={true} onClose={mockOnClose} />
    );

    await waitFor(() => {
      expect(screen.getByText('Test Subject')).toBeInTheDocument();
    });

    expect(screen.getByText('Sender Name')).toBeInTheDocument();
    expect(screen.getByText('sender@example.com')).toBeInTheDocument();
    expect(screen.getByText('Test email body content')).toBeInTheDocument();
  });

  it('extracts and displays verification code', async () => {
    const mockMessage = {
      id: 'msg-123',
      subject: 'Your verification code',
      receivedDateTime: '2025-01-20T10:00:00Z',
      sender: {
        emailAddress: {
          name: 'Service',
          address: 'noreply@service.com',
        },
      },
      body: {
        content: 'Your verification code is 123456',
        contentType: 'text',
      },
    };

    (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: {
        success: true,
        data: { items: [mockMessage] },
      },
    });

    renderWithQueryClient(
      <EmailViewModal email={mockEmail} isOpen={true} onClose={mockOnClose} />
    );

    await waitFor(() => {
      expect(screen.getByText('123456')).toBeInTheDocument();
    });
  });

  it('handles refresh button click', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        success: true,
        data: { items: [] },
      },
    });

    renderWithQueryClient(
      <EmailViewModal email={mockEmail} isOpen={true} onClose={mockOnClose} />
    );

    await waitFor(() => {
      expect(screen.getByText('该邮箱暂无邮件')).toBeInTheDocument();
    });

    const refreshButton = screen.getByTitle('刷新邮件');
    fireEvent.click(refreshButton);

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledTimes(2);
    });
  });

  it('renders HTML content safely', async () => {
    const mockMessage = {
      id: 'msg-123',
      subject: 'HTML Email',
      receivedDateTime: '2025-01-20T10:00:00Z',
      sender: {
        emailAddress: {
          name: 'Service',
          address: 'noreply@service.com',
        },
      },
      body: {
        content: '<p>HTML content</p>',
        contentType: 'html',
      },
    };

    (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: {
        success: true,
        data: { items: [mockMessage] },
      },
    });

    renderWithQueryClient(
      <EmailViewModal email={mockEmail} isOpen={true} onClose={mockOnClose} />
    );

    await waitFor(() => {
      expect(screen.getByText('HTML content')).toBeInTheDocument();
    });
  });

  it('shows no subject placeholder when subject is empty', async () => {
    const mockMessage = {
      id: 'msg-123',
      subject: '',
      receivedDateTime: '2025-01-20T10:00:00Z',
      sender: {
        emailAddress: {
          name: 'Service',
          address: 'noreply@service.com',
        },
      },
      body: {
        content: 'Body content',
        contentType: 'text',
      },
    };

    (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: {
        success: true,
        data: { items: [mockMessage] },
      },
    });

    renderWithQueryClient(
      <EmailViewModal email={mockEmail} isOpen={true} onClose={mockOnClose} />
    );

    await waitFor(() => {
      expect(screen.getByText('(无主题)')).toBeInTheDocument();
    });
  });
});
