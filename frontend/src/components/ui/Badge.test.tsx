/**
 * Badge Component Tests
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Badge } from './Badge';
import { getStatusBadgeVariant } from './badgeUtils';

describe('Badge', () => {
  it('renders children', () => {
    render(<Badge>Active</Badge>);
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('applies default variant styles', () => {
    render(<Badge>Default</Badge>);
    const badge = screen.getByText('Default');
    expect(badge.className).toContain('bg-neutral-100');
  });

  it('applies success variant styles', () => {
    render(<Badge variant="success">Success</Badge>);
    const badge = screen.getByText('Success');
    expect(badge.className).toContain('bg-success-100');
  });

  it('applies warning variant styles', () => {
    render(<Badge variant="warning">Warning</Badge>);
    const badge = screen.getByText('Warning');
    expect(badge.className).toContain('bg-warning-100');
  });

  it('applies error variant styles', () => {
    render(<Badge variant="error">Error</Badge>);
    const badge = screen.getByText('Error');
    expect(badge.className).toContain('bg-error-100');
  });

  it('applies info variant styles', () => {
    render(<Badge variant="info">Info</Badge>);
    const badge = screen.getByText('Info');
    expect(badge.className).toContain('bg-primary-100');
  });

  it('applies size styles', () => {
    const { rerender } = render(<Badge size="sm">Small</Badge>);
    expect(screen.getByText('Small').className).toContain('text-xs');

    rerender(<Badge size="md">Medium</Badge>);
    expect(screen.getByText('Medium').className).toContain('text-sm');
  });

  it('applies custom className', () => {
    render(<Badge className="custom-class">Custom</Badge>);
    expect(screen.getByText('Custom')).toHaveClass('custom-class');
  });
});

describe('getStatusBadgeVariant', () => {
  it('returns success for completed status', () => {
    expect(getStatusBadgeVariant('completed')).toBe('success');
  });

  it('returns warning for in_progress status', () => {
    expect(getStatusBadgeVariant('in_progress')).toBe('warning');
  });

  it('returns error for failed status', () => {
    expect(getStatusBadgeVariant('failed')).toBe('error');
  });

  it('returns info for paused status', () => {
    expect(getStatusBadgeVariant('paused')).toBe('info');
  });

  it('returns default for pending status', () => {
    expect(getStatusBadgeVariant('pending')).toBe('default');
  });

  it('returns default for unknown status', () => {
    expect(getStatusBadgeVariant('unknown')).toBe('default');
  });
});
