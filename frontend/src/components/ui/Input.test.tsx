/**
 * Input Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Input } from './Input';

describe('Input', () => {
  it('renders with label', () => {
    render(<Input label="Email" value="" onChange={() => {}} />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
  });

  it('calls onChange with new value', async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();

    render(<Input label="Name" value="" onChange={handleChange} />);
    await user.type(screen.getByLabelText(/name/i), 'test');

    expect(handleChange).toHaveBeenCalledWith('t');
    expect(handleChange).toHaveBeenCalledWith('e');
    expect(handleChange).toHaveBeenCalledWith('s');
    expect(handleChange).toHaveBeenCalledWith('t');
  });

  it('shows error message when error prop is provided', () => {
    render(<Input label="Email" value="" onChange={() => {}} error="Invalid email" />);
    expect(screen.getByRole('alert')).toHaveTextContent('Invalid email');
  });

  it('has aria-invalid when error is present', () => {
    render(<Input label="Email" value="" onChange={() => {}} error="Invalid" />);
    expect(screen.getByLabelText(/email/i)).toHaveAttribute('aria-invalid', 'true');
  });

  it('shows helper text', () => {
    render(<Input label="Email" value="" onChange={() => {}} helperText="Enter your email" />);
    expect(screen.getByText('Enter your email')).toBeInTheDocument();
  });

  it('is disabled when disabled prop is true', () => {
    render(<Input label="Email" value="" onChange={() => {}} disabled />);
    expect(screen.getByLabelText(/email/i)).toBeDisabled();
  });

  it('shows required indicator', () => {
    render(<Input label="Email" value="" onChange={() => {}} required />);
    expect(screen.getByText('*')).toBeInTheDocument();
  });

  it('applies error styles when error is present', () => {
    render(<Input label="Email" value="" onChange={() => {}} error="Error" />);
    const input = screen.getByLabelText(/email/i);
    expect(input.className).toContain('border-error');
  });

  it('renders with correct type', () => {
    render(<Input label="Website" type="url" value="" onChange={() => {}} />);
    expect(screen.getByLabelText(/website/i)).toHaveAttribute('type', 'url');
  });

  it('shows placeholder text', () => {
    render(<Input label="Email" placeholder="you@example.com" value="" onChange={() => {}} />);
    expect(screen.getByPlaceholderText('you@example.com')).toBeInTheDocument();
  });
});
