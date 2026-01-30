import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LoadingSpinner } from '../ui/LoadingSpinner';

describe('LoadingSpinner', () => {
  it('renders without text', () => {
    render(<LoadingSpinner />);
    // Should render spinner icon (svg element)
    const container = document.querySelector('.animate-spin');
    expect(container).toBeInTheDocument();
  });

  it('renders with text', () => {
    render(<LoadingSpinner text="Loading..." />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('renders with subText', () => {
    render(<LoadingSpinner text="Loading" subText="Please wait" />);
    expect(screen.getByText('Loading')).toBeInTheDocument();
    expect(screen.getByText('Please wait')).toBeInTheDocument();
  });

  it('renders different sizes', () => {
    const { rerender } = render(<LoadingSpinner size="sm" />);
    let spinner = document.querySelector('.w-4');
    expect(spinner).toBeInTheDocument();

    rerender(<LoadingSpinner size="lg" />);
    spinner = document.querySelector('.w-12');
    expect(spinner).toBeInTheDocument();

    rerender(<LoadingSpinner size="xl" />);
    spinner = document.querySelector('.w-16');
    expect(spinner).toBeInTheDocument();
  });

  it('renders with ring when showRing is true', () => {
    render(<LoadingSpinner showRing />);
    const ring = document.querySelector('.border-primary\\/20');
    expect(ring).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<LoadingSpinner className="custom-class" />);
    const container = document.querySelector('.custom-class');
    expect(container).toBeInTheDocument();
  });
});
