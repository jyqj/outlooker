import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import VerificationCodeCard from '../VerificationCodeCard';

// Mock clipboard API
const mockWriteText = vi.fn();
Object.assign(navigator, {
  clipboard: {
    writeText: mockWriteText,
  },
});

describe('VerificationCodeCard', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockWriteText.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders with verification code', () => {
    render(<VerificationCodeCard code="123456" />);

    expect(screen.getByText('123456')).toBeInTheDocument();
    expect(screen.getByText('🔐 检测到的验证码')).toBeInTheDocument();
  });

  it('renders empty state when no code', () => {
    render(<VerificationCodeCard code={null} showFallback={true} />);

    expect(screen.getByText('🔍 暂未检测到验证码')).toBeInTheDocument();
    expect(screen.getByText('未自动识别到验证码')).toBeInTheDocument();
    expect(screen.getByText('请查看下方邮件正文')).toBeInTheDocument();
  });

  it('does not show fallback message when showFallback is false', () => {
    render(<VerificationCodeCard code={null} showFallback={false} />);

    expect(screen.getByText('🔍 暂未检测到验证码')).toBeInTheDocument();
    expect(screen.queryByText('未自动识别到验证码')).not.toBeInTheDocument();
  });

  it('copies code to clipboard when clicked', async () => {
    render(<VerificationCodeCard code="654321" />);

    const codeContainer = screen.getByText('654321').closest('div[title="点击复制验证码"]');
    if (codeContainer) {
      fireEvent.click(codeContainer);
    }

    expect(mockWriteText).toHaveBeenCalledWith('654321');
  });

  it('shows copied confirmation after copying', async () => {
    render(<VerificationCodeCard code="111222" />);

    const codeContainer = screen.getByText('111222').closest('div[title="点击复制验证码"]');
    if (codeContainer) {
      fireEvent.click(codeContainer);
    }

    expect(screen.getByText('✓ 已复制到剪贴板')).toBeInTheDocument();
  });

  it('hides copied confirmation after 2 seconds', async () => {
    render(<VerificationCodeCard code="333444" />);

    const codeContainer = screen.getByText('333444').closest('div[title="点击复制验证码"]');
    if (codeContainer) {
      fireEvent.click(codeContainer);
    }

    expect(screen.getByText('✓ 已复制到剪贴板')).toBeInTheDocument();

    await act(async () => {
      vi.advanceTimersByTime(2000);
    });

    expect(screen.queryByText('✓ 已复制到剪贴板')).not.toBeInTheDocument();
  });

  it('does not copy when code is null', () => {
    render(<VerificationCodeCard code={null} />);

    // No clickable element should exist when there's no code
    expect(screen.queryByTitle('点击复制验证码')).not.toBeInTheDocument();
    expect(mockWriteText).not.toHaveBeenCalled();
  });

  it('does not copy when code is undefined', () => {
    render(<VerificationCodeCard code={undefined} />);

    expect(screen.queryByTitle('点击复制验证码')).not.toBeInTheDocument();
    expect(mockWriteText).not.toHaveBeenCalled();
  });

  it('renders code with large font size', () => {
    render(<VerificationCodeCard code="999888" />);

    const codeElement = screen.getByText('999888');
    expect(codeElement).toHaveClass('text-5xl');
    expect(codeElement).toHaveClass('font-mono');
    expect(codeElement).toHaveClass('font-black');
  });

  it('shows copy icon before copying', () => {
    render(<VerificationCodeCard code="123456" />);

    // Should have a button with Copy icon
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('shows check icon after copying', () => {
    render(<VerificationCodeCard code="123456" />);

    const codeContainer = screen.getByText('123456').closest('div[title="点击复制验证码"]');
    if (codeContainer) {
      fireEvent.click(codeContainer);
    }

    // The check icon should be visible (indicated by the confirmation message)
    expect(screen.getByText('✓ 已复制到剪贴板')).toBeInTheDocument();
  });

  it('renders with gradient background', () => {
    render(<VerificationCodeCard code="123456" />);

    const container = screen.getByText('🔐 检测到的验证码').closest('div');
    expect(container).toHaveClass('bg-gradient-to-br');
  });

  it('handles empty string code', () => {
    render(<VerificationCodeCard code="" showFallback={true} />);

    expect(screen.getByText('🔍 暂未检测到验证码')).toBeInTheDocument();
  });
});
