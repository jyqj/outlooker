import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import AdminLoginPage from '../AdminLoginPage';
import api from '../../lib/api';

vi.mock('../../lib/api', () => ({
  default: {
    post: vi.fn(),
  },
}));

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('AdminLoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  it('submits credentials and navigates on success', async () => {
    api.post.mockResolvedValue({
      data: { access_token: 'token-123' },
    });

    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <AdminLoginPage />
      </MemoryRouter>
    );

    const passwordInput = screen.getByLabelText('密码');
    await user.type(passwordInput, 'secret');
    await user.click(screen.getByRole('button', { name: '登 录' }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/api/admin/login', {
        username: 'admin',
        password: 'secret',
      });
    });

    expect(sessionStorage.getItem('admin_token')).toBe('token-123');
    expect(mockNavigate).toHaveBeenCalledWith('/admin');
  });

  it('shows error when login fails', async () => {
    api.post.mockRejectedValue(new Error('invalid'));

    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <AdminLoginPage />
      </MemoryRouter>
    );

    const passwordInput = screen.getByLabelText('密码');
    await user.type(passwordInput, 'wrong');
    await user.click(screen.getByRole('button', { name: '登 录' }));

    await waitFor(() => {
      expect(screen.getByText(/登录失败/)).toBeInTheDocument();
    });
  });
});
