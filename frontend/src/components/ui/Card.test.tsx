/**
 * Card Component Tests
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Card } from './Card';

describe('Card', () => {
  it('renders children', () => {
    render(<Card>Card content</Card>);
    expect(screen.getByText('Card content')).toBeInTheDocument();
  });

  it('renders title when provided', () => {
    render(<Card title="Card Title">Content</Card>);
    expect(screen.getByText('Card Title')).toBeInTheDocument();
  });

  it('renders actions when provided', () => {
    render(
      <Card title="Card" actions={<button>Action</button>}>
        Content
      </Card>
    );
    expect(screen.getByRole('button', { name: 'Action' })).toBeInTheDocument();
  });

  it('applies padding styles', () => {
    const { container, rerender } = render(<Card padding="none">Content</Card>);
    // With padding none, the content div should not have padding classes
    expect(container.querySelector('.p-4')).not.toBeInTheDocument();

    rerender(<Card padding="lg">Content</Card>);
    expect(container.querySelector('.p-6')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<Card className="custom-class">Content</Card>);
    expect(container.firstChild).toHaveClass('custom-class');
  });

  it('shows header border only when title or actions exist', () => {
    const { container, rerender } = render(<Card>Content only</Card>);
    expect(container.querySelector('.border-b')).not.toBeInTheDocument();

    rerender(<Card title="Title">Content</Card>);
    expect(container.querySelector('.border-b')).toBeInTheDocument();
  });
});
