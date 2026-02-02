import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import TagManageModal from '@/components/TagManageModal';
import api from '@/lib/api';
import type { ReactElement } from 'react';

vi.mock('@/lib/api', () => ({
  default: {
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

const renderWithQueryClient = (ui: ReactElement) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
};

describe('TagManageModal', () => {
  const mockOnClose = vi.fn();
  const mockOnSuccess = vi.fn();
  const mockEmail = 'test@example.com';

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not render when closed', () => {
    renderWithQueryClient(
      <TagManageModal
        email={mockEmail}
        currentTags={[]}
        isOpen={false}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );

    expect(screen.queryByText('管理标签')).not.toBeInTheDocument();
  });

  it('renders when open', () => {
    renderWithQueryClient(
      <TagManageModal
        email={mockEmail}
        currentTags={[]}
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );

    expect(screen.getByText('管理标签')).toBeInTheDocument();
    expect(screen.getByText(mockEmail)).toBeInTheDocument();
  });

  it('displays current tags', () => {
    renderWithQueryClient(
      <TagManageModal
        email={mockEmail}
        currentTags={['tag1', 'tag2']}
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );

    expect(screen.getByText('tag1')).toBeInTheDocument();
    expect(screen.getByText('tag2')).toBeInTheDocument();
    expect(screen.getByText('当前标签 (2)')).toBeInTheDocument();
  });

  it('shows empty state when no tags', () => {
    renderWithQueryClient(
      <TagManageModal
        email={mockEmail}
        currentTags={[]}
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );

    expect(screen.getByText('暂无标签')).toBeInTheDocument();
    expect(screen.getByText('当前标签 (0)')).toBeInTheDocument();
  });

  it('adds a new tag', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(
      <TagManageModal
        email={mockEmail}
        currentTags={[]}
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );

    const input = screen.getByPlaceholderText('输入标签名称...');
    await user.type(input, 'new-tag');

    // Find the plus button by looking for buttons with the Plus icon
    const buttons = screen.getAllByRole('button');
    const plusButton = buttons.find(btn => btn.querySelector('.lucide-plus'));
    
    expect(plusButton).toBeDefined();
    if (plusButton) {
      await user.click(plusButton);
    }

    // Check that the tag count increased
    await waitFor(() => {
      expect(screen.getByText('当前标签 (1)')).toBeInTheDocument();
    });
  });

  it('adds tag on form submit (enter key)', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(
      <TagManageModal
        email={mockEmail}
        currentTags={[]}
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );

    const input = screen.getByPlaceholderText('输入标签名称...');
    await user.type(input, 'enter-tag{enter}');

    await waitFor(() => {
      expect(screen.getByText('enter-tag')).toBeInTheDocument();
    });
  });

  it('does not add duplicate tags', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(
      <TagManageModal
        email={mockEmail}
        currentTags={['existing-tag']}
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );

    const input = screen.getByPlaceholderText('输入标签名称...');
    await user.type(input, 'existing-tag{enter}');

    // Should still only have one instance
    const tags = screen.getAllByText('existing-tag');
    expect(tags).toHaveLength(1);
  });

  it('shows correct tag count', () => {
    renderWithQueryClient(
      <TagManageModal
        email={mockEmail}
        currentTags={['tag-a', 'tag-b', 'tag-c']}
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );

    expect(screen.getByText('tag-a')).toBeInTheDocument();
    expect(screen.getByText('tag-b')).toBeInTheDocument();
    expect(screen.getByText('tag-c')).toBeInTheDocument();
    expect(screen.getByText('当前标签 (3)')).toBeInTheDocument();
  });

  it('saves tags on save button click', async () => {
    const user = userEvent.setup();
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: { success: true },
    });

    renderWithQueryClient(
      <TagManageModal
        email={mockEmail}
        currentTags={['tag1']}
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );

    const saveButton = screen.getByText('保存更改');
    await user.click(saveButton);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        `/api/accounts/${encodeURIComponent(mockEmail)}/tags`,
        {
          email: mockEmail,
          tags: ['tag1'],
        }
      );
    });

    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalled();
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  it('closes modal on cancel button click', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(
      <TagManageModal
        email={mockEmail}
        currentTags={[]}
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );

    const cancelButton = screen.getByText('取消');
    await user.click(cancelButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('shows saving state during save', async () => {
    const user = userEvent.setup();
    (api.post as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({ data: { success: true } }), 100))
    );

    renderWithQueryClient(
      <TagManageModal
        email={mockEmail}
        currentTags={['tag1']}
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );

    const saveButton = screen.getByText('保存更改');
    await user.click(saveButton);

    expect(screen.getByText('保存中...')).toBeInTheDocument();
  });

  it('trims whitespace from new tags', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(
      <TagManageModal
        email={mockEmail}
        currentTags={[]}
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );

    const input = screen.getByPlaceholderText('输入标签名称...');
    await user.type(input, '  trimmed-tag  {enter}');

    await waitFor(() => {
      expect(screen.getByText('trimmed-tag')).toBeInTheDocument();
    });
  });

  it('clears input after adding tag', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(
      <TagManageModal
        email={mockEmail}
        currentTags={[]}
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );

    const input = screen.getByPlaceholderText('输入标签名称...');
    await user.type(input, 'new-tag{enter}');

    await waitFor(() => {
      expect(input).toHaveValue('');
    });
  });
});
