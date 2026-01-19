/**
 * Dashboard Component Tests
 *
 * Verifies UI-02: Company list with status badges
 * - Company table rendering with data
 * - Status badge display
 * - Token usage and cost formatting
 * - Filtering by status and search
 * - Pagination
 * - Actions (View Progress, View Results, Export, Delete)
 * - Loading and error states
 */

import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, useNavigate } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, type Mock } from 'vitest';
import Dashboard from '../pages/Dashboard';
import { useCompanies, useDeleteCompany } from '../hooks/useCompanies';
import { useToast } from '../components/ui';

// Mock company data
const mockCompanies = [
  {
    id: '1',
    companyName: 'Acme Corp',
    websiteUrl: 'https://acme.com',
    industry: 'Technology',
    analysisMode: 'thorough' as const,
    status: 'completed' as const,
    totalTokensUsed: 5000,
    estimatedCost: 0.05,
    createdAt: '2024-01-15T10:00:00Z',
  },
  {
    id: '2',
    companyName: 'Beta Inc',
    websiteUrl: 'https://beta.com',
    industry: 'Finance',
    analysisMode: 'quick' as const,
    status: 'in_progress' as const,
    totalTokensUsed: 1000,
    estimatedCost: 0.01,
    createdAt: '2024-01-16T10:00:00Z',
  },
];

// Mock the hooks
vi.mock('../hooks/useCompanies', () => ({
  useCompanies: vi.fn(),
  useDeleteCompany: vi.fn(),
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

vi.mock('../api/companies', () => ({
  exportAnalysis: vi.fn(),
}));

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

describe('Dashboard Company List', () => {
  const mockShowToast = vi.fn();
  const mockNavigate = vi.fn();
  const mockRefetch = vi.fn();
  const mockDeleteMutateAsync = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useCompanies as Mock).mockReturnValue({
      data: {
        data: mockCompanies,
        meta: { total: 2, page: 1, pageSize: 10, totalPages: 1 },
      },
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    });

    (useDeleteCompany as Mock).mockReturnValue({
      mutateAsync: mockDeleteMutateAsync,
      isPending: false,
    });

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });

    (useNavigate as Mock).mockReturnValue(mockNavigate);
  });

  it('renders company table with data', () => {
    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Assert 'Acme Corp' visible in table
    expect(screen.getByText('Acme Corp')).toBeInTheDocument();

    // Assert 'Beta Inc' visible in table
    expect(screen.getByText('Beta Inc')).toBeInTheDocument();

    // Assert website URLs visible
    expect(screen.getByText('https://acme.com')).toBeInTheDocument();
    expect(screen.getByText('https://beta.com')).toBeInTheDocument();
  });

  it('displays correct status badges', () => {
    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Assert 'completed' badge visible
    expect(screen.getByText('completed')).toBeInTheDocument();

    // Assert 'in progress' badge visible (status is in_progress, displayed as "in progress")
    expect(screen.getByText('in progress')).toBeInTheDocument();
  });

  it('shows token usage and cost', () => {
    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Assert formatted token count (5.0K for 5000)
    expect(screen.getByText('5.0K')).toBeInTheDocument();

    // Assert formatted cost ($0.0500)
    expect(screen.getByText('$0.0500')).toBeInTheDocument();
  });

  it('shows empty state when no companies', () => {
    (useCompanies as Mock).mockReturnValue({
      data: {
        data: [],
        meta: { total: 0, page: 1, pageSize: 10, totalPages: 1 },
      },
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    });

    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Assert "No companies found" message
    expect(screen.getByText(/no companies found/i)).toBeInTheDocument();

    // Assert "Add Your First Company" button visible
    expect(screen.getByRole('link', { name: /add your first company/i })).toBeInTheDocument();
  });
});

describe('Dashboard Filtering', () => {
  const mockShowToast = vi.fn();
  const mockNavigate = vi.fn();
  const mockRefetch = vi.fn();
  const mockDeleteMutateAsync = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useCompanies as Mock).mockReturnValue({
      data: {
        data: mockCompanies,
        meta: { total: 2, page: 1, pageSize: 10, totalPages: 1 },
      },
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    });

    (useDeleteCompany as Mock).mockReturnValue({
      mutateAsync: mockDeleteMutateAsync,
      isPending: false,
    });

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });

    (useNavigate as Mock).mockReturnValue(mockNavigate);
  });

  it('has status filter dropdown', () => {
    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Select for status filter should exist
    const statusSelect = screen.getByLabelText(/status/i);
    expect(statusSelect).toBeInTheDocument();
  });

  it('has search input', () => {
    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Search input should exist
    const searchInput = screen.getByLabelText(/search/i);
    expect(searchInput).toBeInTheDocument();
  });

  it('allows typing in search field', async () => {
    const user = userEvent.setup();
    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Type in search field
    const searchInput = screen.getByLabelText(/search/i);
    await user.type(searchInput, 'acme');

    // Assert search input has value
    expect(searchInput).toHaveValue('acme');
  });

  it('has sort options', () => {
    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Sort by select should exist
    const sortSelect = screen.getByLabelText(/sort by/i);
    expect(sortSelect).toBeInTheDocument();
  });

  it('has sort order toggle button', () => {
    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Sort order toggle button should exist (shows ascending or descending)
    const sortOrderButton = screen.getByRole('button', { name: /descending|ascending/i });
    expect(sortOrderButton).toBeInTheDocument();
  });
});

describe('Dashboard Pagination', () => {
  const mockShowToast = vi.fn();
  const mockNavigate = vi.fn();
  const mockRefetch = vi.fn();
  const mockDeleteMutateAsync = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useCompanies as Mock).mockReturnValue({
      data: {
        data: mockCompanies,
        meta: { total: 2, page: 1, pageSize: 10, totalPages: 1 },
      },
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    });

    (useDeleteCompany as Mock).mockReturnValue({
      mutateAsync: mockDeleteMutateAsync,
      isPending: false,
    });

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });

    (useNavigate as Mock).mockReturnValue(mockNavigate);
  });

  it('shows correct pagination info', () => {
    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Assert "Showing 2 of 2 companies" visible
    expect(screen.getByText(/showing 2 of 2 companies/i)).toBeInTheDocument();

    // Assert "Page 1 of 1" visible
    expect(screen.getByText(/page 1 of 1/i)).toBeInTheDocument();
  });

  it('disables previous on first page', () => {
    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Assert Previous button is disabled
    const prevButton = screen.getByRole('button', { name: /previous/i });
    expect(prevButton).toBeDisabled();
  });

  it('disables next on last page', () => {
    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Assert Next button is disabled when on last page
    const nextButton = screen.getByRole('button', { name: /next/i });
    expect(nextButton).toBeDisabled();
  });

  it('enables navigation when multiple pages', () => {
    // Mock with more data to have multiple pages
    (useCompanies as Mock).mockReturnValue({
      data: {
        data: mockCompanies,
        meta: { total: 25, page: 1, pageSize: 10, totalPages: 3 },
      },
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    });

    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Assert Next button is enabled
    const nextButton = screen.getByRole('button', { name: /next/i });
    expect(nextButton).not.toBeDisabled();

    // Assert "Page 1 of 3" visible
    expect(screen.getByText(/page 1 of 3/i)).toBeInTheDocument();
  });
});

describe('Dashboard Actions', () => {
  const mockShowToast = vi.fn();
  const mockNavigate = vi.fn();
  const mockRefetch = vi.fn();
  const mockDeleteMutateAsync = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useCompanies as Mock).mockReturnValue({
      data: {
        data: mockCompanies,
        meta: { total: 2, page: 1, pageSize: 10, totalPages: 1 },
      },
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    });

    (useDeleteCompany as Mock).mockReturnValue({
      mutateAsync: mockDeleteMutateAsync,
      isPending: false,
    });

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });

    (useNavigate as Mock).mockReturnValue(mockNavigate);
  });

  it('shows View Progress for in_progress companies', () => {
    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Assert 'View Progress' link visible for Beta Inc (in_progress)
    const viewProgressLink = screen.getByRole('link', { name: /view progress/i });
    expect(viewProgressLink).toBeInTheDocument();
    expect(viewProgressLink).toHaveAttribute('href', '/companies/2/progress');
  });

  it('shows View Results for completed companies', () => {
    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Assert 'View Results' link visible for Acme Corp (completed)
    const viewResultsLink = screen.getByRole('link', { name: /view results/i });
    expect(viewResultsLink).toBeInTheDocument();
    expect(viewResultsLink).toHaveAttribute('href', '/companies/1');
  });

  it('shows Export button for completed companies', () => {
    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Assert 'Export' button visible for completed companies
    const exportButton = screen.getByRole('button', { name: /^export$/i });
    expect(exportButton).toBeInTheDocument();
  });

  it('shows Delete button for each company', () => {
    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Assert Delete buttons are visible (one for each company)
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
    expect(deleteButtons.length).toBeGreaterThanOrEqual(2);
  });

  it('opens delete confirmation modal', async () => {
    const user = userEvent.setup();
    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Click first Delete button
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
    await user.click(deleteButtons[0]);

    // Assert modal opens with confirmation text
    await waitFor(() => {
      expect(screen.getByText(/are you sure you want to delete/i)).toBeInTheDocument();
    });

    // Assert Cancel button in modal
    const modal = screen.getByRole('dialog');
    expect(within(modal).getByRole('button', { name: /cancel/i })).toBeInTheDocument();

    // Assert Delete button in modal (with variant danger)
    expect(within(modal).getByRole('button', { name: /delete/i })).toBeInTheDocument();
  });

  it('closes delete modal on cancel', async () => {
    const user = userEvent.setup();
    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Open delete modal
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
    await user.click(deleteButtons[0]);

    // Click Cancel
    const modal = screen.getByRole('dialog');
    const cancelButton = within(modal).getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    // Assert modal is closed
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });

  it('has Add Company link in header', () => {
    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Assert 'Add Company' link visible
    const addCompanyLink = screen.getByRole('link', { name: /add company/i });
    expect(addCompanyLink).toBeInTheDocument();
    expect(addCompanyLink).toHaveAttribute('href', '/add');
  });

  it('has Batch Upload link in header', () => {
    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Assert 'Batch Upload' link visible
    const batchUploadLink = screen.getByRole('link', { name: /batch upload/i });
    expect(batchUploadLink).toBeInTheDocument();
    expect(batchUploadLink).toHaveAttribute('href', '/batch');
  });
});

describe('Dashboard Loading/Error States', () => {
  const mockShowToast = vi.fn();
  const mockNavigate = vi.fn();
  const mockRefetch = vi.fn();
  const mockDeleteMutateAsync = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useDeleteCompany as Mock).mockReturnValue({
      mutateAsync: mockDeleteMutateAsync,
      isPending: false,
    });

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });

    (useNavigate as Mock).mockReturnValue(mockNavigate);
  });

  it('shows skeleton during loading', () => {
    (useCompanies as Mock).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: mockRefetch,
    });

    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Assert skeleton elements are visible (skeletons have a specific class)
    const skeletons = document.querySelectorAll('[class*="animate-pulse"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('shows error state with retry button', () => {
    (useCompanies as Mock).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('API Error'),
      refetch: mockRefetch,
    });

    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Assert error message visible
    expect(screen.getByText(/failed to load companies/i)).toBeInTheDocument();

    // Assert Retry button visible
    const retryButton = screen.getByRole('button', { name: /retry/i });
    expect(retryButton).toBeInTheDocument();
  });

  it('calls refetch on retry button click', async () => {
    const user = userEvent.setup();

    (useCompanies as Mock).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('API Error'),
      refetch: mockRefetch,
    });

    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Click Retry button
    const retryButton = screen.getByRole('button', { name: /retry/i });
    await user.click(retryButton);

    // Assert refetch was called
    expect(mockRefetch).toHaveBeenCalled();
  });
});

describe('Dashboard Delete Flow', () => {
  const mockShowToast = vi.fn();
  const mockNavigate = vi.fn();
  const mockRefetch = vi.fn();
  const mockDeleteMutateAsync = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useCompanies as Mock).mockReturnValue({
      data: {
        data: mockCompanies,
        meta: { total: 2, page: 1, pageSize: 10, totalPages: 1 },
      },
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    });

    (useDeleteCompany as Mock).mockReturnValue({
      mutateAsync: mockDeleteMutateAsync,
      isPending: false,
    });

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });

    (useNavigate as Mock).mockReturnValue(mockNavigate);
  });

  it('calls delete mutation on confirm', async () => {
    mockDeleteMutateAsync.mockResolvedValue({});

    const user = userEvent.setup();
    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Open delete modal for first company
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
    await user.click(deleteButtons[0]);

    // Click Delete in modal
    const modal = screen.getByRole('dialog');
    const confirmDeleteButton = within(modal).getByRole('button', { name: /delete/i });
    await user.click(confirmDeleteButton);

    // Assert delete mutation was called
    await waitFor(() => {
      expect(mockDeleteMutateAsync).toHaveBeenCalled();
    });
  });

  it('shows success toast on successful delete', async () => {
    mockDeleteMutateAsync.mockResolvedValue({});

    const user = userEvent.setup();
    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Open delete modal for first company
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
    await user.click(deleteButtons[0]);

    // Click Delete in modal
    const modal = screen.getByRole('dialog');
    const confirmDeleteButton = within(modal).getByRole('button', { name: /delete/i });
    await user.click(confirmDeleteButton);

    // Assert success toast was shown
    await waitFor(() => {
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'success',
        })
      );
    });
  });

  it('shows error toast on failed delete', async () => {
    mockDeleteMutateAsync.mockRejectedValue(new Error('Delete failed'));

    const user = userEvent.setup();
    render(<Dashboard />, { wrapper: createTestWrapper() });

    // Open delete modal for first company
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
    await user.click(deleteButtons[0]);

    // Click Delete in modal
    const modal = screen.getByRole('dialog');
    const confirmDeleteButton = within(modal).getByRole('button', { name: /delete/i });
    await user.click(confirmDeleteButton);

    // Assert error toast was shown
    await waitFor(() => {
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'error',
        })
      );
    });
  });
});
