/**
 * Slider Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Slider } from './Slider';

describe('Slider', () => {
  it('renders with label', () => {
    render(<Slider label="Volume" value={50} onChange={() => {}} />);
    expect(screen.getByLabelText(/volume/i)).toBeInTheDocument();
  });

  it('renders input with correct type', () => {
    render(<Slider label="Volume" value={50} onChange={() => {}} />);
    expect(screen.getByRole('slider')).toHaveAttribute('type', 'range');
  });

  it('shows current value when showValue is true', () => {
    render(<Slider label="Volume" value={75} onChange={() => {}} showValue />);
    expect(screen.getByText('75')).toBeInTheDocument();
  });

  it('shows unit when provided', () => {
    render(<Slider label="Max Pages" value={100} onChange={() => {}} showValue unit="pages" />);
    expect(screen.getByText('pages')).toBeInTheDocument();
  });

  it('shows min and max values', () => {
    render(<Slider label="Volume" value={50} onChange={() => {}} min={0} max={100} />);
    expect(screen.getByText('0')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
  });

  it('shows min and max with units', () => {
    render(
      <Slider
        label="Max Pages"
        value={50}
        onChange={() => {}}
        min={10}
        max={500}
        unit="pages"
      />
    );
    expect(screen.getByText('10 pages')).toBeInTheDocument();
    expect(screen.getByText('500 pages')).toBeInTheDocument();
  });

  it('calls onChange with new value', () => {
    const handleChange = vi.fn();
    render(<Slider label="Volume" value={50} onChange={handleChange} />);

    const slider = screen.getByRole('slider');
    fireEvent.change(slider, { target: { value: '75' } });

    expect(handleChange).toHaveBeenCalledWith(75);
  });

  it('respects min and max attributes', () => {
    render(
      <Slider label="Volume" value={50} onChange={() => {}} min={10} max={90} />
    );
    const slider = screen.getByRole('slider');
    expect(slider).toHaveAttribute('min', '10');
    expect(slider).toHaveAttribute('max', '90');
  });

  it('respects step attribute', () => {
    render(<Slider label="Volume" value={50} onChange={() => {}} step={5} />);
    const slider = screen.getByRole('slider');
    expect(slider).toHaveAttribute('step', '5');
  });

  it('is disabled when disabled prop is true', () => {
    render(<Slider label="Volume" value={50} onChange={() => {}} disabled />);
    expect(screen.getByRole('slider')).toBeDisabled();
  });

  it('shows helper text when provided', () => {
    render(
      <Slider
        label="Volume"
        value={50}
        onChange={() => {}}
        helperText="Adjust the volume level"
      />
    );
    expect(screen.getByText('Adjust the volume level')).toBeInTheDocument();
  });

  it('has aria-describedby when helperText is provided', () => {
    render(
      <Slider
        label="Volume"
        value={50}
        onChange={() => {}}
        helperText="Help text"
      />
    );
    expect(screen.getByRole('slider')).toHaveAttribute('aria-describedby');
  });
});
