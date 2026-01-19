/**
 * AddCompany Component Tests
 *
 * Verifies UI-01: Company submission form with validation
 * - Form field rendering and required validation
 * - URL normalization (auto-add https://)
 * - Advanced options toggle
 * - Form submission and mutation calls
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, useNavigate } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, type Mock } from 'vitest';
import AddCompany from '../pages/AddCompany';
import { useCreateCompany } from '../hooks/useCompanies';
import { useToast } from '../components/ui';

// Mock the hooks
vi.mock('../hooks/useCompanies', () => ({
  useCreateCompany: vi.fn(),
}));

vi.mock('../components/ui', async () => {
  const actual = await vi.importActual('../components/ui');
  return {
    ...actual,
    useToast: vi.fn(),
  };
});

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: vi.fn(),
  };
});

// Test wrapper with providers
function createTestWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return function TestWrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>{children}</BrowserRouter>
      </QueryClientProvider>
    );
  };
}

describe('AddCompany Form Validation', () => {
  const mockMutateAsync = vi.fn();
  const mockShowToast = vi.fn();
  const mockNavigate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useCreateCompany as Mock).mockReturnValue({
      mutateAsync: mockMutateAsync,
      isPending: false,
    });

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });

    (useNavigate as Mock).mockReturnValue(mockNavigate);
  });

  it('renders all required form fields', () => {
    render(<AddCompany />, { wrapper: createTestWrapper() });

    // Company name input
    expect(screen.getByLabelText(/company name/i)).toBeInTheDocument();

    // Website URL input
    expect(screen.getByLabelText(/website url/i)).toBeInTheDocument();

    // Submit button
    expect(screen.getByRole('button', { name: /start analysis/i })).toBeInTheDocument();
  });

  it('marks required fields with required attribute', () => {
    render(<AddCompany />, { wrapper: createTestWrapper() });

    // Company name input should be required
    const nameInput = screen.getByLabelText(/company name/i);
    expect(nameInput).toBeRequired();

    // Website URL input should be required
    const urlInput = screen.getByLabelText(/website url/i);
    expect(urlInput).toBeRequired();
  });

  it('does not submit when form validation fails', async () => {
    const user = userEvent.setup();
    render(<AddCompany />, { wrapper: createTestWrapper() });

    // Click submit without filling fields - native validation should prevent submit
    const submitButton = screen.getByRole('button', { name: /start analysis/i });
    await user.click(submitButton);

    // Assert mutation was NOT called (form didn't submit due to native validation)
    expect(mockMutateAsync).not.toHaveBeenCalled();
  });

  it('url input has type url for browser validation', () => {
    render(<AddCompany />, { wrapper: createTestWrapper() });

    // Website URL input should have type="url" for browser-level validation
    const urlInput = screen.getByLabelText(/website url/i);
    expect(urlInput).toHaveAttribute('type', 'url');
  });

  it('accepts valid http URL and submits successfully', async () => {
    mockMutateAsync.mockResolvedValue({
      data: { companyId: 'test-123' },
    });

    const user = userEvent.setup();
    render(<AddCompany />, { wrapper: createTestWrapper() });

    // Fill in company name
    const nameInput = screen.getByLabelText(/company name/i);
    await user.type(nameInput, 'Test Company');

    // Enter valid http URL
    const urlInput = screen.getByLabelText(/website url/i);
    await user.type(urlInput, 'http://example.com');

    // Submit form
    const submitButton = screen.getByRole('button', { name: /start analysis/i });
    await user.click(submitButton);

    // Assert mutation was called (validation passed)
    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalled();
    });
  });

  it('auto-normalizes URL on blur', async () => {
    const user = userEvent.setup();
    render(<AddCompany />, { wrapper: createTestWrapper() });

    // Enter URL without protocol
    const urlInput = screen.getByLabelText(/website url/i);
    await user.type(urlInput, 'example.com');

    // Blur the field
    await user.tab();

    // Assert value is now 'https://example.com'
    await waitFor(() => {
      expect(urlInput).toHaveValue('https://example.com');
    });
  });

  it('enforces company name max length', async () => {
    const user = userEvent.setup();
    render(<AddCompany />, { wrapper: createTestWrapper() });

    // Enter 201 character name
    const longName = 'a'.repeat(201);
    const nameInput = screen.getByLabelText(/company name/i);
    await user.type(nameInput, longName);

    // Enter valid URL
    const urlInput = screen.getByLabelText(/website url/i);
    await user.type(urlInput, 'https://example.com');

    // Submit form
    const submitButton = screen.getByRole('button', { name: /start analysis/i });
    await user.click(submitButton);

    // Assert length validation error shown
    await waitFor(() => {
      expect(screen.getByText(/200 characters or less/i)).toBeInTheDocument();
    });
  });
});

describe('AddCompany Advanced Options', () => {
  const mockMutateAsync = vi.fn();
  const mockShowToast = vi.fn();
  const mockNavigate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useCreateCompany as Mock).mockReturnValue({
      mutateAsync: mockMutateAsync,
      isPending: false,
    });

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });

    (useNavigate as Mock).mockReturnValue(mockNavigate);
  });

  it('hides advanced options by default', () => {
    render(<AddCompany />, { wrapper: createTestWrapper() });

    // Max pages slider should not be visible (not in document or hidden)
    expect(screen.queryByLabelText(/max pages/i)).not.toBeInTheDocument();

    // Analysis mode select should not be visible
    expect(screen.queryByLabelText(/analysis mode/i)).not.toBeInTheDocument();
  });

  it('shows advanced options when toggled', async () => {
    const user = userEvent.setup();
    render(<AddCompany />, { wrapper: createTestWrapper() });

    // Click "Advanced Options" toggle
    const advancedToggle = screen.getByRole('button', { name: /advanced options/i });
    await user.click(advancedToggle);

    // Assert max pages slider now visible
    await waitFor(() => {
      expect(screen.getByLabelText(/max pages/i)).toBeInTheDocument();
    });

    // Assert analysis mode select now visible
    expect(screen.getByLabelText(/analysis mode/i)).toBeInTheDocument();
  });

  it('quick mode presets correct values', async () => {
    const user = userEvent.setup();
    render(<AddCompany />, { wrapper: createTestWrapper() });

    // Open advanced options
    const advancedToggle = screen.getByRole('button', { name: /advanced options/i });
    await user.click(advancedToggle);

    // Select 'quick' analysis mode
    const analysisModeSelect = screen.getByLabelText(/analysis mode/i);
    await user.selectOptions(analysisModeSelect, 'quick');

    // Verify preset values - maxPages should be 50
    const maxPagesSlider = screen.getByLabelText(/max pages/i);
    expect(maxPagesSlider).toHaveValue('50');

    // Check LinkedIn checkbox is unchecked (quick mode disables social links)
    const linkedInCheckbox = screen.getByRole('checkbox', { name: /linkedin/i });
    expect(linkedInCheckbox).not.toBeChecked();
  });
});

describe('AddCompany Submission', () => {
  const mockMutateAsync = vi.fn();
  const mockShowToast = vi.fn();
  const mockNavigate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useCreateCompany as Mock).mockReturnValue({
      mutateAsync: mockMutateAsync,
      isPending: false,
    });

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });

    (useNavigate as Mock).mockReturnValue(mockNavigate);
  });

  it('calls mutation with correct data', async () => {
    mockMutateAsync.mockResolvedValue({
      data: { companyId: 'test-123' },
    });

    const user = userEvent.setup();
    render(<AddCompany />, { wrapper: createTestWrapper() });

    // Fill in valid form data
    const nameInput = screen.getByLabelText(/company name/i);
    await user.type(nameInput, 'Test Company');

    const urlInput = screen.getByLabelText(/website url/i);
    await user.type(urlInput, 'https://example.com');

    // Submit form
    const submitButton = screen.getByRole('button', { name: /start analysis/i });
    await user.click(submitButton);

    // Assert mutateAsync called with correct payload
    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          companyName: 'Test Company',
          websiteUrl: 'https://example.com',
        })
      );
    });
  });

  it('shows loading state during submission', () => {
    (useCreateCompany as Mock).mockReturnValue({
      mutateAsync: mockMutateAsync,
      isPending: true,
    });

    render(<AddCompany />, { wrapper: createTestWrapper() });

    // Assert button shows "Starting Analysis..."
    const submitButton = screen.getByRole('button', { name: /starting analysis/i });
    expect(submitButton).toBeInTheDocument();

    // Assert button is disabled (loading state disables button)
    expect(submitButton).toBeDisabled();
  });

  it('redirects on successful submission', async () => {
    mockMutateAsync.mockResolvedValue({
      data: { companyId: 'test-company-123' },
    });

    const user = userEvent.setup();
    render(<AddCompany />, { wrapper: createTestWrapper() });

    // Fill in valid form data
    const nameInput = screen.getByLabelText(/company name/i);
    await user.type(nameInput, 'Test Company');

    const urlInput = screen.getByLabelText(/website url/i);
    await user.type(urlInput, 'https://example.com');

    // Submit form
    const submitButton = screen.getByRole('button', { name: /start analysis/i });
    await user.click(submitButton);

    // Assert navigation to progress page
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/companies/test-company-123/progress');
    });
  });

  it('shows error toast on submission failure', async () => {
    mockMutateAsync.mockRejectedValue(new Error('API Error'));

    const user = userEvent.setup();
    render(<AddCompany />, { wrapper: createTestWrapper() });

    // Fill in valid form data
    const nameInput = screen.getByLabelText(/company name/i);
    await user.type(nameInput, 'Test Company');

    const urlInput = screen.getByLabelText(/website url/i);
    await user.type(urlInput, 'https://example.com');

    // Submit form
    const submitButton = screen.getByRole('button', { name: /start analysis/i });
    await user.click(submitButton);

    // Assert error toast shown
    await waitFor(() => {
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'error',
        })
      );
    });
  });
});
