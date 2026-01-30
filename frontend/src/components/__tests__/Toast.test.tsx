import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import ToastContainer from '../Toast';

describe('ToastContainer', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  const dispatchToast = (message: string, type: string = 'info', duration: number = 3000) => {
    const event = new CustomEvent('showToast', {
      detail: { message, type, duration },
    });
    window.dispatchEvent(event);
  };

  it('renders without toasts initially', () => {
    render(<ToastContainer />);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('displays toast when event is dispatched', async () => {
    render(<ToastContainer />);

    act(() => {
      dispatchToast('Test message', 'info');
    });

    expect(screen.getByText('Test message')).toBeInTheDocument();
  });

  it('renders success toast with correct styling', () => {
    render(<ToastContainer />);

    act(() => {
      dispatchToast('Success message', 'success');
    });

    const toast = screen.getByText('Success message').closest('div');
    expect(toast).toHaveClass('bg-green-50');
  });

  it('renders error toast with correct styling', () => {
    render(<ToastContainer />);

    act(() => {
      dispatchToast('Error message', 'error');
    });

    const toast = screen.getByText('Error message').closest('div');
    expect(toast).toHaveClass('bg-red-50');
  });

  it('renders warning toast with correct styling', () => {
    render(<ToastContainer />);

    act(() => {
      dispatchToast('Warning message', 'warning');
    });

    const toast = screen.getByText('Warning message').closest('div');
    expect(toast).toHaveClass('bg-yellow-50');
  });

  it('renders info toast with correct styling', () => {
    render(<ToastContainer />);

    act(() => {
      dispatchToast('Info message', 'info');
    });

    const toast = screen.getByText('Info message').closest('div');
    expect(toast).toHaveClass('bg-blue-50');
  });

  it('auto-dismisses toast after duration', async () => {
    render(<ToastContainer />);

    act(() => {
      dispatchToast('Auto dismiss', 'info', 3000);
    });

    expect(screen.getByText('Auto dismiss')).toBeInTheDocument();

    await act(async () => {
      vi.advanceTimersByTime(3000);
    });

    expect(screen.queryByText('Auto dismiss')).not.toBeInTheDocument();
  });

  it('closes toast when close button is clicked', () => {
    render(<ToastContainer />);

    act(() => {
      dispatchToast('Closeable toast', 'info');
    });

    const closeButton = screen.getByLabelText('关闭');
    fireEvent.click(closeButton);

    expect(screen.queryByText('Closeable toast')).not.toBeInTheDocument();
  });

  it('displays multiple toasts', () => {
    render(<ToastContainer />);

    act(() => {
      dispatchToast('First toast', 'info');
      dispatchToast('Second toast', 'success');
      dispatchToast('Third toast', 'error');
    });

    expect(screen.getByText('First toast')).toBeInTheDocument();
    expect(screen.getByText('Second toast')).toBeInTheDocument();
    expect(screen.getByText('Third toast')).toBeInTheDocument();
  });

  it('removes only the clicked toast from multiple toasts', () => {
    render(<ToastContainer />);

    act(() => {
      dispatchToast('Toast 1', 'info');
      dispatchToast('Toast 2', 'success');
    });

    const closeButtons = screen.getAllByLabelText('关闭');
    fireEvent.click(closeButtons[0]);

    expect(screen.queryByText('Toast 1')).not.toBeInTheDocument();
    expect(screen.getByText('Toast 2')).toBeInTheDocument();
  });

  it('does not auto-dismiss when duration is 0', async () => {
    render(<ToastContainer />);

    act(() => {
      dispatchToast('Persistent toast', 'info', 0);
    });

    expect(screen.getByText('Persistent toast')).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(10000);
    });

    expect(screen.getByText('Persistent toast')).toBeInTheDocument();
  });

  it('defaults to info type when type is unknown', () => {
    render(<ToastContainer />);

    act(() => {
      dispatchToast('Unknown type', 'unknown' as 'info');
    });

    const toast = screen.getByText('Unknown type').closest('div');
    expect(toast).toHaveClass('bg-blue-50');
  });
});
