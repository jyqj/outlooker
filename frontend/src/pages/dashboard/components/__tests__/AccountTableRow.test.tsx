import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AccountTableRow } from '../AccountTableRow';
import type { Account } from '@/types';

describe('AccountTableRow', () => {
  const mockAccount: Account = {
    email: 'test@example.com',
    password: '***',
    client_id: 'client-123',
    refresh_token: '***',
    is_used: false,
    last_used_at: null,
  };

  const defaultProps = {
    account: mockAccount,
    isSelected: false,
    tags: [],
    onToggleSelect: vi.fn(),
    onViewEmails: vi.fn(),
    onManageTags: vi.fn(),
  };

  const renderInTable = (ui: React.ReactElement) => {
    return render(
      <table>
        <tbody>{ui}</tbody>
      </table>
    );
  };

  it('renders account email', () => {
    renderInTable(<AccountTableRow {...defaultProps} />);
    expect(screen.getByText('test@example.com')).toBeInTheDocument();
  });

  it('shows unselected state by default', () => {
    renderInTable(<AccountTableRow {...defaultProps} />);
    // Row should not have selected styling
    const row = screen.getByRole('row');
    expect(row).not.toHaveClass('bg-primary/5');
  });

  it('shows selected state when isSelected is true', () => {
    renderInTable(<AccountTableRow {...defaultProps} isSelected={true} />);
    // Row should have selected styling
    const row = screen.getByRole('row');
    expect(row).toHaveClass('bg-primary/5');
  });

  it('calls onToggleSelect when checkbox is clicked', () => {
    const onToggleSelect = vi.fn();
    renderInTable(<AccountTableRow {...defaultProps} onToggleSelect={onToggleSelect} />);
    
    const buttons = screen.getAllByRole('button');
    fireEvent.click(buttons[0]);
    
    expect(onToggleSelect).toHaveBeenCalledWith('test@example.com');
  });

  it('calls onViewEmails when mail button is clicked', () => {
    const onViewEmails = vi.fn();
    renderInTable(<AccountTableRow {...defaultProps} onViewEmails={onViewEmails} />);
    
    const viewEmailsButton = screen.getByTitle('查看邮件');
    fireEvent.click(viewEmailsButton);
    
    expect(onViewEmails).toHaveBeenCalledWith('test@example.com');
  });

  it('calls onManageTags when tag button is clicked', () => {
    const onManageTags = vi.fn();
    renderInTable(<AccountTableRow {...defaultProps} onManageTags={onManageTags} />);
    
    const manageTagsButton = screen.getByTitle('管理标签');
    fireEvent.click(manageTagsButton);
    
    expect(onManageTags).toHaveBeenCalledWith('test@example.com');
  });

  it('displays tags when provided', () => {
    renderInTable(<AccountTableRow {...defaultProps} tags={['VIP', '测试']} />);
    
    expect(screen.getByText('VIP')).toBeInTheDocument();
    expect(screen.getByText('测试')).toBeInTheDocument();
  });

  it('shows "无标签" when no tags', () => {
    renderInTable(<AccountTableRow {...defaultProps} tags={[]} />);
    expect(screen.getByText('无标签')).toBeInTheDocument();
  });

  it('shows "未使用(公共池)" badge when is_used is false', () => {
    renderInTable(<AccountTableRow {...defaultProps} />);
    expect(screen.getByText('未使用(公共池)')).toBeInTheDocument();
  });

  it('shows "已使用(公共池)" badge when is_used is true', () => {
    const usedAccount = { ...mockAccount, is_used: true, last_used_at: '2025-01-20 10:00' };
    renderInTable(<AccountTableRow {...defaultProps} account={usedAccount} />);
    
    expect(screen.getByText('已使用(公共池)')).toBeInTheDocument();
    expect(screen.getByText('最后使用：2025-01-20 10:00')).toBeInTheDocument();
  });

  it('applies selected row styling when selected', () => {
    const { container } = renderInTable(<AccountTableRow {...defaultProps} isSelected={true} />);
    const row = container.querySelector('tr');
    expect(row).toHaveClass('bg-primary/5');
  });
});
