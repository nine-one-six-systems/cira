/**
 * Select Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Select } from './Select';

const options = [
  { value: 'quick', label: 'Quick' },
  { value: 'thorough', label: 'Thorough' },
];

describe('Select', () => {
  it('renders with label', () => {
    render(<Select label="Mode" options={options} value="" onChange={() => {}} />);
    expect(screen.getByLabelText(/mode/i)).toBeInTheDocument();
  });

  it('renders all options', () => {
    render(<Select label="Mode" options={options} value="" onChange={() => {}} />);
    expect(screen.getByRole('option', { name: 'Quick' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Thorough' })).toBeInTheDocument();
  });

  it('shows placeholder when provided', () => {
    render(
      <Select
        label="Mode"
        options={options}
        value=""
        onChange={() => {}}
        placeholder="Select mode"
      />
    );
    expect(screen.getByRole('option', { name: 'Select mode' })).toBeInTheDocument();
  });

  it('calls onChange with selected value', async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();

    render(<Select label="Mode" options={options} value="" onChange={handleChange} />);
    await user.selectOptions(screen.getByLabelText(/mode/i), 'thorough');

    expect(handleChange).toHaveBeenCalledWith('thorough');
  });

  it('shows error message when error prop is provided', () => {
    render(
      <Select label="Mode" options={options} value="" onChange={() => {}} error="Required" />
    );
    expect(screen.getByRole('alert')).toHaveTextContent('Required');
  });

  it('has aria-invalid when error is present', () => {
    render(
      <Select label="Mode" options={options} value="" onChange={() => {}} error="Required" />
    );
    expect(screen.getByLabelText(/mode/i)).toHaveAttribute('aria-invalid', 'true');
  });

  it('is disabled when disabled prop is true', () => {
    render(<Select label="Mode" options={options} value="" onChange={() => {}} disabled />);
    expect(screen.getByLabelText(/mode/i)).toBeDisabled();
  });

  it('shows required indicator', () => {
    render(<Select label="Mode" options={options} value="" onChange={() => {}} required />);
    expect(screen.getByText('*')).toBeInTheDocument();
  });

  it('has correct selected value', () => {
    render(<Select label="Mode" options={options} value="thorough" onChange={() => {}} />);
    expect(screen.getByLabelText(/mode/i)).toHaveValue('thorough');
  });
});
