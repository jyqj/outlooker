import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ErrorBoundary from '../ErrorBoundary';

// Mock logError utility
vi.mock('../../lib/utils', () => ({
  logError: vi.fn(),
}));

// Component that throws an error
const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) {
    throw new Error('Test error message');
  }
  return <div>Normal content</div>;
};

describe('ErrorBoundary', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Suppress console.error for expected errors
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  it('renders children when no error occurs', () => {
    render(
      <ErrorBoundary>
        <div>Child content</div>
      </ErrorBoundary>
    );

    expect(screen.getByText('Child content')).toBeInTheDocument();
  });

  it('renders error UI when child throws', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('页面加载失败')).toBeInTheDocument();
    expect(screen.getByText('Test error message')).toBeInTheDocument();
  });

  it('shows retry button in error state', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('重新加载')).toBeInTheDocument();
  });

  it('calls onReset when retry button is clicked', () => {
    const mockOnReset = vi.fn();

    render(
      <ErrorBoundary onReset={mockOnReset}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    const retryButton = screen.getByText('重新加载');
    fireEvent.click(retryButton);

    expect(mockOnReset).toHaveBeenCalledTimes(1);
  });

  it('recovers from error when retry is clicked', () => {
    let shouldThrow = true;

    const TestComponent = () => {
      if (shouldThrow) {
        throw new Error('Initial error');
      }
      return <div>Recovered content</div>;
    };

    const { rerender } = render(
      <ErrorBoundary
        onReset={() => {
          shouldThrow = false;
        }}
      >
        <TestComponent />
      </ErrorBoundary>
    );

    // Should show error UI
    expect(screen.getByText('页面加载失败')).toBeInTheDocument();

    // Click retry
    const retryButton = screen.getByText('重新加载');
    fireEvent.click(retryButton);

    // Re-render to show recovered state
    rerender(
      <ErrorBoundary
        onReset={() => {
          shouldThrow = false;
        }}
      >
        <TestComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText('Recovered content')).toBeInTheDocument();
  });

  it('shows generic error message when error has no message', () => {
    const ErrorWithoutMessage = () => {
      throw new Error();
    };

    render(
      <ErrorBoundary>
        <ErrorWithoutMessage />
      </ErrorBoundary>
    );

    expect(screen.getByText('页面加载失败')).toBeInTheDocument();
    expect(screen.getByText('出现未知错误，请重试或联系管理员。')).toBeInTheDocument();
  });

  it('handles multiple children', () => {
    render(
      <ErrorBoundary>
        <div>First child</div>
        <div>Second child</div>
      </ErrorBoundary>
    );

    expect(screen.getByText('First child')).toBeInTheDocument();
    expect(screen.getByText('Second child')).toBeInTheDocument();
  });

  it('does not call onReset if not provided', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    const retryButton = screen.getByText('重新加载');
    
    // Should not throw when clicking without onReset
    expect(() => {
      fireEvent.click(retryButton);
    }).not.toThrow();
  });

  it('catches errors from deeply nested components', () => {
    const DeeplyNested = () => {
      return (
        <div>
          <div>
            <div>
              <ThrowError shouldThrow={true} />
            </div>
          </div>
        </div>
      );
    };

    render(
      <ErrorBoundary>
        <DeeplyNested />
      </ErrorBoundary>
    );

    expect(screen.getByText('页面加载失败')).toBeInTheDocument();
  });

  it('retry button is clickable in error state', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('页面加载失败')).toBeInTheDocument();
    
    const retryButton = screen.getByRole('button', { name: '重新加载' });
    expect(retryButton).toBeEnabled();
    
    // Clicking should not throw
    expect(() => fireEvent.click(retryButton)).not.toThrow();
  });

  it('renders with proper styling', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    const errorContainer = screen.getByText('页面加载失败').closest('div[class*="min-h-screen"]');
    expect(errorContainer).toBeInTheDocument();
  });
});
