import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BatchTagModal } from '@/pages/dashboard/components/BatchTagModal';

describe('BatchTagModal', () => {
  const defaultProps = {
    isOpen: true,
    mode: 'add' as const,
    selectedCount: 5,
    batchTags: '',
    loading: false,
    onTagsChange: vi.fn(),
    onModeChange: vi.fn(),
    onSubmit: vi.fn(),
    onClose: vi.fn(),
  };

  it('does not render when closed', () => {
    render(<BatchTagModal {...defaultProps} isOpen={false} />);
    expect(screen.queryByText('批量标签操作')).not.toBeInTheDocument();
  });

  it('renders when open', () => {
    render(<BatchTagModal {...defaultProps} />);
    expect(screen.getByText('批量标签操作 (5 个账户)')).toBeInTheDocument();
  });

  it('displays selected count in title', () => {
    render(<BatchTagModal {...defaultProps} selectedCount={10} />);
    expect(screen.getByText('批量标签操作 (10 个账户)')).toBeInTheDocument();
  });

  it('shows mode selector with correct options', () => {
    render(<BatchTagModal {...defaultProps} />);
    
    const select = screen.getByRole('combobox');
    expect(select).toHaveValue('add');
    
    expect(screen.getByText('添加标签')).toBeInTheDocument();
    expect(screen.getByText('移除标签')).toBeInTheDocument();
    expect(screen.getByText('替换标签')).toBeInTheDocument();
  });

  it('calls onModeChange when mode is changed', () => {
    const onModeChange = vi.fn();
    render(<BatchTagModal {...defaultProps} onModeChange={onModeChange} />);
    
    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'remove' } });
    
    expect(onModeChange).toHaveBeenCalledWith('remove');
  });

  it('shows add mode description', () => {
    render(<BatchTagModal {...defaultProps} mode="add" />);
    expect(screen.getByText('将这些标签添加到选中的账户')).toBeInTheDocument();
  });

  it('shows remove mode description', () => {
    render(<BatchTagModal {...defaultProps} mode="remove" />);
    expect(screen.getByText('从选中的账户移除这些标签')).toBeInTheDocument();
  });

  it('shows set mode description', () => {
    render(<BatchTagModal {...defaultProps} mode="set" />);
    expect(screen.getByText('用这些标签替换选中账户的所有标签（留空则清除所有标签）')).toBeInTheDocument();
  });

  it('shows tags input with placeholder', () => {
    render(<BatchTagModal {...defaultProps} />);
    expect(screen.getByPlaceholderText('例如: VIP, 测试, 常用')).toBeInTheDocument();
  });

  it('displays current batch tags value', () => {
    render(<BatchTagModal {...defaultProps} batchTags="VIP, 测试" />);
    expect(screen.getByDisplayValue('VIP, 测试')).toBeInTheDocument();
  });

  it('calls onTagsChange when tags input changes', () => {
    const onTagsChange = vi.fn();
    render(<BatchTagModal {...defaultProps} onTagsChange={onTagsChange} />);
    
    const input = screen.getByPlaceholderText('例如: VIP, 测试, 常用');
    fireEvent.change(input, { target: { value: 'new-tag' } });
    
    expect(onTagsChange).toHaveBeenCalledWith('new-tag');
  });

  it('calls onSubmit when confirm button is clicked', () => {
    const onSubmit = vi.fn();
    render(<BatchTagModal {...defaultProps} onSubmit={onSubmit} />);
    
    fireEvent.click(screen.getByRole('button', { name: '确认' }));
    
    expect(onSubmit).toHaveBeenCalled();
  });

  it('calls onClose when cancel button is clicked', () => {
    const onClose = vi.fn();
    render(<BatchTagModal {...defaultProps} onClose={onClose} />);
    
    fireEvent.click(screen.getByRole('button', { name: '取消' }));
    
    expect(onClose).toHaveBeenCalled();
  });

  it('shows loading state', () => {
    render(<BatchTagModal {...defaultProps} loading={true} />);
    
    expect(screen.getByText('处理中...')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '处理中...' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '取消' })).toBeDisabled();
  });

  it('disables buttons during loading', () => {
    render(<BatchTagModal {...defaultProps} loading={true} />);
    
    expect(screen.getByRole('button', { name: '取消' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '处理中...' })).toBeDisabled();
  });
});
