/**
 * ProgressBar Component Tests
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProgressBar } from './ProgressBar';

describe('ProgressBar', () => {
  it('renders with correct aria attributes', () => {
    render(<ProgressBar value={50} />);
    const progressbar = screen.getByRole('progressbar');
    expect(progressbar).toHaveAttribute('aria-valuenow', '50');
    expect(progressbar).toHaveAttribute('aria-valuemin', '0');
    expect(progressbar).toHaveAttribute('aria-valuemax', '100');
  });

  it('renders label when provided', () => {
    render(<ProgressBar value={50} label="Loading" />);
    expect(screen.getByText('Loading')).toBeInTheDocument();
  });

  it('shows percentage when showPercentage is true', () => {
    render(<ProgressBar value={75} showPercentage />);
    expect(screen.getByText('75%')).toBeInTheDocument();
  });

  it('clamps value to 0-100 range', () => {
    const { rerender } = render(<ProgressBar value={-10} />);
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0');

    rerender(<ProgressBar value={150} />);
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '100');
  });

  it('applies color styles', () => {
    const { container, rerender } = render(<ProgressBar value={50} color="primary" />);
    expect(container.querySelector('.bg-primary')).toBeInTheDocument();

    rerender(<ProgressBar value={50} color="success" />);
    expect(container.querySelector('.bg-success')).toBeInTheDocument();

    rerender(<ProgressBar value={50} color="error" />);
    expect(container.querySelector('.bg-error')).toBeInTheDocument();
  });

  it('applies size styles', () => {
    const { container, rerender } = render(<ProgressBar value={50} size="sm" />);
    expect(container.querySelector('.h-1')).toBeInTheDocument();

    rerender(<ProgressBar value={50} size="lg" />);
    expect(container.querySelector('.h-3')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<ProgressBar value={50} className="custom-class" />);
    expect(container.firstChild).toHaveClass('custom-class');
  });

  it('has correct aria-label from label prop', () => {
    render(<ProgressBar value={50} label="Upload progress" />);
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-label', 'Upload progress');
  });
});
