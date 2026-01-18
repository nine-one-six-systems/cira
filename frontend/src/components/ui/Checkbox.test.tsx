/**
 * Checkbox Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Checkbox } from './Checkbox';

describe('Checkbox', () => {
  it('renders with label', () => {
    render(<Checkbox label="Accept terms" />);
    expect(screen.getByLabelText(/accept terms/i)).toBeInTheDocument();
  });

  it('is checked when checked prop is true', () => {
    render(<Checkbox label="Accept terms" checked onChange={() => {}} />);
    expect(screen.getByRole('checkbox')).toBeChecked();
  });

  it('is not checked when checked prop is false', () => {
    render(<Checkbox label="Accept terms" checked={false} onChange={() => {}} />);
    expect(screen.getByRole('checkbox')).not.toBeChecked();
  });

  it('calls onChange when clicked', async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();

    render(<Checkbox label="Accept terms" checked={false} onChange={handleChange} />);
    await user.click(screen.getByRole('checkbox'));

    expect(handleChange).toHaveBeenCalledWith(true);
  });

  it('shows description text', () => {
    render(
      <Checkbox
        label="Accept terms"
        description="By checking this you agree to the terms of service"
      />
    );
    expect(screen.getByText(/by checking this/i)).toBeInTheDocument();
  });

  it('is disabled when disabled prop is true', () => {
    render(<Checkbox label="Accept terms" disabled />);
    expect(screen.getByRole('checkbox')).toBeDisabled();
  });

  it('does not call onChange when disabled', async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();

    render(<Checkbox label="Accept terms" disabled onChange={handleChange} />);
    await user.click(screen.getByRole('checkbox'));

    expect(handleChange).not.toHaveBeenCalled();
  });

  it('has aria-describedby when description is provided', () => {
    render(<Checkbox label="Accept terms" description="Description text" />);
    const checkbox = screen.getByRole('checkbox');
    expect(checkbox).toHaveAttribute('aria-describedby');
  });
});
