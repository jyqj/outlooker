import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import AdminLoginPage from '../AdminLoginPage';
import api from '../../lib/api';

const apiModuleMock = vi.hoisted(() => ({
  default: {
    post: vi.fn(),
  },
  setAuthTokens: vi.fn(),
}));

vi.mock('../../lib/api', () => apiModuleMock);

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('AdminLoginPage', () => {
  const apiPost = api.post as unknown as ReturnType<typeof vi.fn>;
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  it('submits credentials and navigates on success', async () => {
    apiPost.mockResolvedValue({
      data: {
        access_token: 'token-123',
        refresh_token: 'refresh-456',
        expires_in: 3600,
        refresh_expires_in: 7200,
      },
    });

    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <AdminLoginPage />
      </MemoryRouter>
    );

    const usernameInput = screen.getByLabelText('用户名');
    await user.type(usernameInput, 'admin');
    const passwordInput = screen.getByLabelText('密码');
    await user.type(passwordInput, 'secret');
    await user.click(screen.getByRole('button', { name: '登 录' }));

    await waitFor(() => {
      expect(apiPost).toHaveBeenCalledWith('/api/admin/login', {
        username: 'admin',
        password: 'secret',
      });
    });

    expect(apiModuleMock.setAuthTokens).toHaveBeenCalledWith({
      accessToken: 'token-123',
      expiresIn: 3600,
    });
    expect(mockNavigate).toHaveBeenCalledWith('/admin');
  });

  it('shows error when login fails', async () => {
    apiPost.mockRejectedValue(new Error('invalid'));

    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <AdminLoginPage />
      </MemoryRouter>
    );

    const usernameInput = screen.getByLabelText('用户名');
    await user.type(usernameInput, 'admin');
    const passwordInput = screen.getByLabelText('密码');
    await user.type(passwordInput, 'wrong');
    await user.click(screen.getByRole('button', { name: '登 录' }));

    await waitFor(() => {
      expect(screen.getByText(/登录失败/)).toBeInTheDocument();
    });
  });
});
