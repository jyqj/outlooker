import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Pagination } from '../Pagination';

describe('Pagination', () => {
  const defaultProps = {
    page: 1,
    pageSize: 10,
    totalPages: 5,
    totalRecords: 50,
    jumpToPage: '',
    pageNumbers: [1, 2, 3, 4, 5],
    isFirstPage: true,
    isLastPage: false,
    onPageChange: vi.fn(),
    onPageSizeChange: vi.fn(),
    onJumpToPageChange: vi.fn(),
    onJumpToPage: vi.fn(),
    onNextPage: vi.fn(),
    onPrevPage: vi.fn(),
  };

  it('displays total records', () => {
    render(<Pagination {...defaultProps} />);
    expect(screen.getByText('共 50 条记录')).toBeInTheDocument();
  });

  it('displays current page size in select', () => {
    render(<Pagination {...defaultProps} pageSize={20} />);
    const selects = screen.getAllByRole('combobox');
    expect(selects[0]).toHaveValue('20');
  });

  it('calls onPageSizeChange when page size is changed', () => {
    const onPageSizeChange = vi.fn();
    render(<Pagination {...defaultProps} onPageSizeChange={onPageSizeChange} />);
    
    const selects = screen.getAllByRole('combobox');
    fireEvent.change(selects[0], { target: { value: '50' } });
    
    expect(onPageSizeChange).toHaveBeenCalledWith('50');
  });

  it('disables prev button on first page', () => {
    render(<Pagination {...defaultProps} isFirstPage={true} />);
    
    // Find all buttons with ChevronLeft icon
    const buttons = screen.getAllByRole('button');
    const prevButton = buttons.find(btn => btn.querySelector('.lucide-chevron-left'));
    
    expect(prevButton).toBeDisabled();
  });

  it('enables prev button when not on first page', () => {
    render(<Pagination {...defaultProps} isFirstPage={false} page={2} />);
    
    const buttons = screen.getAllByRole('button');
    const prevButton = buttons.find(btn => btn.querySelector('.lucide-chevron-left'));
    
    expect(prevButton).not.toBeDisabled();
  });

  it('disables next button on last page', () => {
    render(<Pagination {...defaultProps} isLastPage={true} />);
    
    const buttons = screen.getAllByRole('button');
    const nextButton = buttons.find(btn => btn.querySelector('.lucide-chevron-right'));
    
    expect(nextButton).toBeDisabled();
  });

  it('enables next button when not on last page', () => {
    render(<Pagination {...defaultProps} isLastPage={false} />);
    
    const buttons = screen.getAllByRole('button');
    const nextButton = buttons.find(btn => btn.querySelector('.lucide-chevron-right'));
    
    expect(nextButton).not.toBeDisabled();
  });

  it('calls onPrevPage when prev button is clicked', () => {
    const onPrevPage = vi.fn();
    render(<Pagination {...defaultProps} isFirstPage={false} onPrevPage={onPrevPage} />);
    
    const buttons = screen.getAllByRole('button');
    const prevButton = buttons.find(btn => btn.querySelector('.lucide-chevron-left'));
    fireEvent.click(prevButton!);
    
    expect(onPrevPage).toHaveBeenCalled();
  });

  it('calls onNextPage when next button is clicked', () => {
    const onNextPage = vi.fn();
    render(<Pagination {...defaultProps} onNextPage={onNextPage} />);
    
    const buttons = screen.getAllByRole('button');
    const nextButton = buttons.find(btn => btn.querySelector('.lucide-chevron-right'));
    fireEvent.click(nextButton!);
    
    expect(onNextPage).toHaveBeenCalled();
  });

  it('renders page number buttons', () => {
    render(<Pagination {...defaultProps} pageNumbers={[1, 2, 3]} />);
    
    expect(screen.getByRole('button', { name: '1' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '2' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '3' })).toBeInTheDocument();
  });

  it('calls onPageChange when page number is clicked', () => {
    const onPageChange = vi.fn();
    render(<Pagination {...defaultProps} onPageChange={onPageChange} />);
    
    fireEvent.click(screen.getByRole('button', { name: '3' }));
    
    expect(onPageChange).toHaveBeenCalledWith(3);
  });

  it('renders ellipsis in page numbers', () => {
    render(<Pagination {...defaultProps} pageNumbers={[1, '...', 5]} />);
    expect(screen.getByText('...')).toBeInTheDocument();
  });

  it('shows jump to page input', () => {
    render(<Pagination {...defaultProps} />);
    expect(screen.getByPlaceholderText('页码')).toBeInTheDocument();
  });

  it('calls onJumpToPageChange when input changes', () => {
    const onJumpToPageChange = vi.fn();
    render(<Pagination {...defaultProps} onJumpToPageChange={onJumpToPageChange} />);
    
    const input = screen.getByPlaceholderText('页码');
    fireEvent.change(input, { target: { value: '3' } });
    
    expect(onJumpToPageChange).toHaveBeenCalledWith('3');
  });

  it('calls onJumpToPage when jump button is clicked', () => {
    const onJumpToPage = vi.fn();
    render(<Pagination {...defaultProps} jumpToPage="3" onJumpToPage={onJumpToPage} />);
    
    fireEvent.click(screen.getByRole('button', { name: '跳转' }));
    
    expect(onJumpToPage).toHaveBeenCalled();
  });

  it('calls onJumpToPage when Enter is pressed in input', () => {
    const onJumpToPage = vi.fn();
    render(<Pagination {...defaultProps} jumpToPage="3" onJumpToPage={onJumpToPage} />);
    
    const input = screen.getByPlaceholderText('页码');
    fireEvent.keyDown(input, { key: 'Enter' });
    
    expect(onJumpToPage).toHaveBeenCalled();
  });

  it('disables jump button when no page number entered', () => {
    render(<Pagination {...defaultProps} jumpToPage="" />);
    expect(screen.getByRole('button', { name: '跳转' })).toBeDisabled();
  });
});
