/**
 * Skeleton Component Tests
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Skeleton, SkeletonText, SkeletonCard, SkeletonTable } from './Skeleton';

describe('Skeleton', () => {
  it('renders with default rect variant', () => {
    const { container } = render(<Skeleton />);
    expect(container.querySelector('.rounded-md')).toBeInTheDocument();
  });

  it('renders with text variant', () => {
    const { container } = render(<Skeleton variant="text" />);
    expect(container.querySelector('.rounded')).toBeInTheDocument();
  });

  it('renders with circle variant', () => {
    const { container } = render(<Skeleton variant="circle" />);
    expect(container.querySelector('.rounded-full')).toBeInTheDocument();
  });

  it('applies custom width and height', () => {
    const { container } = render(<Skeleton width={200} height={100} />);
    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton.style.width).toBe('200px');
    expect(skeleton.style.height).toBe('100px');
  });

  it('accepts string width and height', () => {
    const { container } = render(<Skeleton width="50%" height="2rem" />);
    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton.style.width).toBe('50%');
    expect(skeleton.style.height).toBe('2rem');
  });

  it('renders multiple lines for text variant', () => {
    const { container } = render(<Skeleton variant="text" lines={3} />);
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons).toHaveLength(3);
  });

  it('has aria-hidden attribute', () => {
    const { container } = render(<Skeleton />);
    expect(container.firstChild).toHaveAttribute('aria-hidden', 'true');
  });

  it('applies custom className', () => {
    const { container } = render(<Skeleton className="custom-class" />);
    expect(container.firstChild).toHaveClass('custom-class');
  });
});

describe('SkeletonText', () => {
  it('renders with default 3 lines', () => {
    const { container } = render(<SkeletonText />);
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons).toHaveLength(3);
  });

  it('renders with specified number of lines', () => {
    const { container } = render(<SkeletonText lines={5} />);
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons).toHaveLength(5);
  });
});

describe('SkeletonCard', () => {
  it('renders a card-like skeleton structure', () => {
    const { container } = render(<SkeletonCard />);
    expect(container.querySelector('.bg-white')).toBeInTheDocument();
    expect(container.querySelector('.rounded-lg')).toBeInTheDocument();
  });
});

describe('SkeletonTable', () => {
  it('renders with default rows and columns', () => {
    const { container } = render(<SkeletonTable />);
    // Default is 5 rows + 1 header
    const rows = container.querySelectorAll('.border-t');
    expect(rows.length).toBeGreaterThanOrEqual(5);
  });

  it('renders with specified rows and columns', () => {
    const { container } = render(<SkeletonTable rows={3} columns={2} />);
    const rows = container.querySelectorAll('.border-t');
    expect(rows).toHaveLength(3);
  });
});
