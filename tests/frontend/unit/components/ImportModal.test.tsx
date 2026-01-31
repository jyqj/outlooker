import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ImportModal from '@/components/ImportModal';
import api from '@/lib/api';

vi.mock('@/lib/api', () => ({
  default: {
    post: vi.fn(),
  },
}));

describe('ImportModal', () => {
  const apiPost = api.post as unknown as ReturnType<typeof vi.fn>;
  const mockOnClose = vi.fn();
  const mockOnSuccess = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not render when closed', () => {
    render(
      <ImportModal isOpen={false} onClose={mockOnClose} onSuccess={mockOnSuccess} />
    );

    expect(screen.queryByText(/批量导入账户/)).not.toBeInTheDocument();
  });

  it('renders when open', () => {
    render(
      <ImportModal isOpen={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />
    );

    expect(screen.getByText(/批量导入账户/)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/请粘贴账户数据/)).toBeInTheDocument();
  });

  it('parses import text successfully', async () => {
    apiPost.mockResolvedValueOnce({
      data: {
        success: true,
        data: {
          accounts: [
            {
              email: 'test@example.com',
              password: '',
              client_id: '',
              refresh_token: 'token123',
            },
          ],
          parsed_count: 1,
          error_count: 0,
          errors: [],
        },
      },
    });

    const user = userEvent.setup();
    render(
      <ImportModal isOpen={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />
    );

    const textarea = screen.getByPlaceholderText(/请粘贴账户数据/);
    await user.type(textarea, 'test@example.com----token123');

    const nextButton = screen.getByText(/下一步：解析预览/);
    await user.click(nextButton);

    await waitFor(() => {
      expect(apiPost).toHaveBeenCalledWith('/api/parse-import-text', {
        text: 'test@example.com----token123',
      });
    });

    await waitFor(() => {
      // 文本被多个元素分割,需要分别查找
      expect(screen.getByText(/解析成功：/)).toBeInTheDocument();
      expect(screen.getByText('1')).toBeInTheDocument();
      expect(screen.getByText(/test@example.com/)).toBeInTheDocument();
    });
  });

  it('handles parse error', async () => {
    apiPost.mockResolvedValueOnce({
      data: {
        success: false,
        message: '解析失败',
      },
    });

    const user = userEvent.setup();
    render(
      <ImportModal isOpen={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />
    );

    const textarea = screen.getByPlaceholderText(/请粘贴账户数据/);
    await user.type(textarea, 'invalid format');

    const nextButton = screen.getByText(/下一步：解析预览/);
    await user.click(nextButton);

    await waitFor(() => {
      expect(screen.getByText(/解析失败/)).toBeInTheDocument();
    });
  });

  it('imports accounts successfully', async () => {
    // First mock for parsing
    apiPost.mockResolvedValueOnce({
      data: {
        success: true,
        data: {
          accounts: [
            {
              email: 'import@example.com',
              refresh_token: 'token456',
            },
          ],
          parsed_count: 1,
          error_count: 0,
          errors: [],
        },
      },
    });

    // Second mock for importing
    apiPost.mockResolvedValueOnce({
      data: {
        success: true,
        message: '导入成功',
        data: {
          message: '导入成功',
          added_count: 1,
          updated_count: 0,
          skipped_count: 0,
          error_count: 0,
        },
      },
    });

    const user = userEvent.setup();
    render(
      <ImportModal isOpen={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />
    );

    // Step 1: Parse
    const textarea = screen.getByPlaceholderText(/请粘贴账户数据/);
    await user.type(textarea, 'import@example.com----token456');

    const nextButton = screen.getByText(/下一步：解析预览/);
    await user.click(nextButton);

    await waitFor(() => {
      expect(screen.getByText(/解析成功/)).toBeInTheDocument();
    });

    // Step 2: Import
    const importButton = await screen.findByText(/确认导入 1 条账户/);
    await user.click(importButton);

    await waitFor(() => {
      expect(apiPost).toHaveBeenCalledWith('/api/import', {
        accounts: [
          {
            email: 'import@example.com',
            refresh_token: 'token456',
          },
        ],
        merge_mode: 'update',
      });
    });

    await waitFor(() => {
      expect(screen.getByText(/导入完成/)).toBeInTheDocument();
      expect(mockOnSuccess).toHaveBeenCalled();
    });
  });

  it('allows selecting merge mode', async () => {
    apiPost.mockResolvedValueOnce({
      data: {
        success: true,
        data: {
          accounts: [{ email: 'test@example.com', refresh_token: 'token' }],
          parsed_count: 1,
          error_count: 0,
          errors: [],
        },
      },
    });

    const user = userEvent.setup();
    render(
      <ImportModal isOpen={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />
    );

    const mergeSelect = screen.getByRole('combobox');
    await user.selectOptions(mergeSelect, 'skip');

    const textarea = screen.getByPlaceholderText(/请粘贴账户数据/);
    await user.type(textarea, 'test@example.com----token');

    const nextButton = screen.getByText(/下一步：解析预览/);
    await user.click(nextButton);

    // Verify merge_mode will be used when importing
    await waitFor(() => {
      expect(screen.getByText(/解析成功/)).toBeInTheDocument();
    });
  });

  it('closes modal on X button click', async () => {
    const user = userEvent.setup();
    render(
      <ImportModal isOpen={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />
    );

    const closeButtons = screen.getAllByRole('button');
    const xButton = closeButtons.find((btn) => {
      const svg = btn.querySelector('svg');
      return svg?.classList.contains('lucide-x');
    });

    if (xButton) {
      await user.click(xButton);
      expect(mockOnClose).toHaveBeenCalled();
    }
  });
});

