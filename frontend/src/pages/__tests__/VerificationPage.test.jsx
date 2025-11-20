import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import VerificationPage from '../VerificationPage';
import api from '../../lib/api';

vi.mock('../../lib/api', () => ({
  default: {
    get: vi.fn(),
  },
}));

describe('VerificationPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loads latest message for configured account and displays extracted code', async () => {
    api.get.mockResolvedValue({
      data: {
        success: true,
        data: {
          items: [
            {
              id: '1',
              subject: 'Login code',
              body: { content: 'Your security code is 654321', contentType: 'text' },
              bodyPreview: '',
              sender: { emailAddress: { name: 'System', address: 'no-reply@example.com' } },
              from: { emailAddress: { name: 'System', address: 'no-reply@example.com' } },
            },
          ],
        },
      },
    });

    const user = userEvent.setup();
    render(<VerificationPage />);

    await user.type(screen.getByLabelText(/邮箱地址/), 'user@example.com');
    await user.click(screen.getByRole('button', { name: /获取最新验证码/ }));

    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/api/messages', {
      params: expect.objectContaining({ email: 'user@example.com', page: 1, page_size: 1 }),
    }));

    expect(await screen.findByText('654321')).toBeInTheDocument();
  });

  it('shows error message when account is not configured', async () => {
    api.get.mockResolvedValue({
      data: {
        success: false,
        message: '未在配置中找到该邮箱',
      },
    });

    const user = userEvent.setup();
    render(<VerificationPage />);

    await user.type(screen.getByLabelText(/邮箱地址/), 'missing@example.com');
    await user.click(screen.getByRole('button', { name: /获取最新验证码/ }));

    await waitFor(() => {
      expect(screen.getByText(/未在配置中找到该邮箱/)).toBeInTheDocument();
    });

    // Verify error message is displayed
    expect(screen.getByText(/请检查邮箱地址是否正确/)).toBeInTheDocument();
  });
});
