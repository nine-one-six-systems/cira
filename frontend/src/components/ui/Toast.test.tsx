/**
 * Toast Component Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ToastProvider, useToast } from './Toast';

// Test component that uses the toast hook
function TestComponent() {
  const { showToast } = useToast();

  return (
    <div>
      <button onClick={() => showToast({ type: 'success', message: 'Success message' })}>
        Show Success
      </button>
      <button onClick={() => showToast({ type: 'error', message: 'Error message' })}>
        Show Error
      </button>
      <button onClick={() => showToast({ type: 'warning', message: 'Warning message' })}>
        Show Warning
      </button>
      <button onClick={() => showToast({ type: 'info', message: 'Info message' })}>
        Show Info
      </button>
      <button onClick={() => showToast({ type: 'success', message: 'No auto dismiss', duration: 0 })}>
        Persistent Toast
      </button>
    </div>
  );
}

describe('Toast', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  it('throws error when used outside provider', () => {
    // Suppress console error for this test
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      render(<TestComponent />);
    }).toThrow('useToast must be used within a ToastProvider');

    consoleSpy.mockRestore();
  });

  it('shows toast when showToast is called', async () => {
    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    );

    await act(async () => {
      screen.getByText('Show Success').click();
    });

    expect(screen.getByText('Success message')).toBeInTheDocument();
  });

  it('shows different toast types', async () => {
    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    );

    await act(async () => {
      screen.getByText('Show Error').click();
    });
    expect(screen.getByText('Error message')).toBeInTheDocument();

    await act(async () => {
      screen.getByText('Show Warning').click();
    });
    expect(screen.getByText('Warning message')).toBeInTheDocument();

    await act(async () => {
      screen.getByText('Show Info').click();
    });
    expect(screen.getByText('Info message')).toBeInTheDocument();
  });

  it('auto-removes toast after duration', async () => {
    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    );

    await act(async () => {
      screen.getByText('Show Success').click();
    });
    expect(screen.getByText('Success message')).toBeInTheDocument();

    // Fast forward past the default 5000ms duration
    await act(async () => {
      vi.advanceTimersByTime(5001);
    });

    await waitFor(() => {
      expect(screen.queryByText('Success message')).not.toBeInTheDocument();
    });
  });

  it('does not auto-remove toast when duration is 0', async () => {
    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    );

    await act(async () => {
      screen.getByText('Persistent Toast').click();
    });
    expect(screen.getByText('No auto dismiss')).toBeInTheDocument();

    // Fast forward 10 seconds
    await act(async () => {
      vi.advanceTimersByTime(10000);
    });

    // Toast should still be there
    expect(screen.getByText('No auto dismiss')).toBeInTheDocument();
  });

  it('removes toast when dismiss button is clicked', async () => {
    const user = userEvent.setup({ delay: null });

    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    );

    await act(async () => {
      screen.getByText('Show Success').click();
    });
    expect(screen.getByText('Success message')).toBeInTheDocument();

    await act(async () => {
      await user.click(screen.getByLabelText('Dismiss'));
    });

    await waitFor(() => {
      expect(screen.queryByText('Success message')).not.toBeInTheDocument();
    });
  });

  it('shows multiple toasts', async () => {
    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    );

    await act(async () => {
      screen.getByText('Show Success').click();
    });
    await act(async () => {
      screen.getByText('Show Error').click();
    });

    expect(screen.getByText('Success message')).toBeInTheDocument();
    expect(screen.getByText('Error message')).toBeInTheDocument();
  });

  it('has correct ARIA attributes', async () => {
    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    );

    await act(async () => {
      screen.getByText('Show Success').click();
    });

    const alerts = screen.getAllByRole('alert');
    expect(alerts.length).toBeGreaterThan(0);
    expect(alerts[0]).toHaveAttribute('aria-live', 'polite');
  });
});
