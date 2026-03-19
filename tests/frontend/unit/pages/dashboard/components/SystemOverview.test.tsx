import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import type { ReactElement } from 'react';

vi.mock('@/lib/api', () => ({
  default: {
    get: vi.fn(),
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

import api from '@/lib/api';
import { SystemOverview } from '@/pages/dashboard/components/SystemOverview';

function renderWithProviders(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('SystemOverview', () => {
  const apiGet = api.get as unknown as ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    apiGet.mockResolvedValue({
      data: {
        success: true,
        data: {
          health: {
            total: 10,
            healthy: 7,
            token_expired: 1,
            token_invalid: 1,
            error: 0,
            unknown: 1,
          },
          tags: {
            tagged_accounts: 6,
            untagged_accounts: 4,
            tags: [{ name: 'alpha', count: 6, percentage: 60 }],
          },
          alerts: [{ level: 'warning', message: 'token expired', count: 1 }],
          recent_events: [{ event_type: 'health_check', timestamp: '2026-01-01T00:00:00Z' }],
        },
      },
    });
  });

  it('renders overview cards from dashboard summary', async () => {
    renderWithProviders(<SystemOverview />);
    expect(await screen.findByText('账户总数')).toBeInTheDocument();
    expect(screen.getByText('标签分布')).toBeInTheDocument();
    expect(screen.getByText('系统状态')).toBeInTheDocument();
  });

  it('renders health and tag metrics', async () => {
    renderWithProviders(<SystemOverview />);
    expect(await screen.findByText('10')).toBeInTheDocument();
    expect(screen.getByText(/已标记: 6/)).toBeInTheDocument();
    expect(screen.getByText(/未标记: 4/)).toBeInTheDocument();
  });

  it('renders alerts and recent activity blocks when provided', async () => {
    renderWithProviders(<SystemOverview />);
    expect(await screen.findByText('系统告警')).toBeInTheDocument();
    expect(screen.getByText('token expired')).toBeInTheDocument();
    expect(screen.getByText('最近活动')).toBeInTheDocument();
  });
});
