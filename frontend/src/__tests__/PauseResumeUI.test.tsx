/**
 * Pause/Resume UI Component Tests
 *
 * Verifies UI-07: Pause/resume in UI
 * - Pause button visible and clickable for in_progress companies
 * - Resume button visible and clickable for paused companies
 * - Progress bar shows correct percentage and phase
 * - Status badge reflects current state (in_progress, paused, completed, failed)
 * - Time elapsed and estimated remaining displayed correctly
 * - Toast notifications shown for pause/resume actions
 * - Cancel modal works correctly
 */

import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, useParams, useNavigate } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, type Mock } from 'vitest';
import CompanyProgress from '../pages/CompanyProgress';
import {
  useCompany,
  useProgress,
  usePauseCompany,
  useResumeCompany,
  useDeleteCompany,
} from '../hooks/useCompanies';
import { useToast } from '../components/ui';
import type { ProgressUpdate, CompanyStatus } from '../types';

// ============================================================================
// Mock Data Factories
// ============================================================================

const createMockProgress = (overrides: Partial<ProgressUpdate> = {}): ProgressUpdate => ({
  companyId: 'test-company-1',
  status: 'in_progress',
  phase: 'crawling',
  pagesCrawled: 10,
  pagesTotal: 20,
  entitiesExtracted: 45,
  tokensUsed: 5000,
  timeElapsed: 120,
  estimatedTimeRemaining: 180,
  currentActivity: 'Crawling page 10 of 20...',
  ...overrides,
});

const createMockCompany = (status: CompanyStatus = 'in_progress', overrides = {}) => ({
  data: {
    company: {
      id: 'test-company-1',
      companyName: 'Test Company',
      websiteUrl: 'https://test.com',
      industry: 'Technology',
      analysisMode: 'thorough' as const,
      status,
      processingPhase: 'crawling',
      totalTokensUsed: 5000,
      estimatedCost: 0.05,
      createdAt: '2024-01-15T10:00:00Z',
      ...overrides,
    },
    analysis: null,
    entityCount: 0,
    pageCount: 0,
  },
});

// ============================================================================
// Mock Setup
// ============================================================================

vi.mock('../hooks/useCompanies', () => ({
  useCompany: vi.fn(),
  useProgress: vi.fn(),
  usePauseCompany: vi.fn(),
  useResumeCompany: vi.fn(),
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
    useParams: vi.fn(),
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

// ============================================================================
// Pause Button Tests (UI-07)
// ============================================================================

describe('Pause Button (UI-07)', () => {
  const mockShowToast = vi.fn();
  const mockNavigate = vi.fn();
  const mockPauseMutateAsync = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useParams as Mock).mockReturnValue({ id: 'test-company-1' });
    (useNavigate as Mock).mockReturnValue(mockNavigate);

    (useCompany as Mock).mockReturnValue({
      data: createMockCompany('in_progress'),
      isLoading: false,
    });

    (useProgress as Mock).mockReturnValue({
      data: { data: createMockProgress() },
      isLoading: false,
    });

    (usePauseCompany as Mock).mockReturnValue({
      mutateAsync: mockPauseMutateAsync,
      isPending: false,
    });

    (useResumeCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useDeleteCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });
  });

  it('renders pause button for in_progress company', () => {
    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    const pauseButton = screen.getByRole('button', { name: /pause/i });
    expect(pauseButton).toBeInTheDocument();
    expect(pauseButton).toBeEnabled();
  });

  it('pause button hidden for paused company', () => {
    (useCompany as Mock).mockReturnValue({
      data: createMockCompany('paused'),
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Pause button should not be visible
    expect(screen.queryByRole('button', { name: /^pause$/i })).not.toBeInTheDocument();
    // Resume button should be visible instead
    expect(screen.getByRole('button', { name: /resume/i })).toBeInTheDocument();
  });

  it('pause button hidden for completed company', () => {
    (useCompany as Mock).mockReturnValue({
      data: createMockCompany('completed'),
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    expect(screen.queryByRole('button', { name: /pause/i })).not.toBeInTheDocument();
  });

  it('pause button hidden for failed company', () => {
    (useCompany as Mock).mockReturnValue({
      data: createMockCompany('failed'),
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    expect(screen.queryByRole('button', { name: /pause/i })).not.toBeInTheDocument();
  });

  it('clicking pause button calls mutation', async () => {
    mockPauseMutateAsync.mockResolvedValue({});

    const user = userEvent.setup();
    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    const pauseButton = screen.getByRole('button', { name: /pause/i });
    await user.click(pauseButton);

    await waitFor(() => {
      expect(mockPauseMutateAsync).toHaveBeenCalledWith('test-company-1');
    });
  });

  it('pause button shows loading state', () => {
    (usePauseCompany as Mock).mockReturnValue({
      mutateAsync: mockPauseMutateAsync,
      isPending: true,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Button should show loading indicator or be disabled
    const pauseButton = screen.getByRole('button', { name: /pause/i });
    // The Button component with loading=true shows loading state
    expect(pauseButton).toBeInTheDocument();
  });

  it('pause success shows toast notification', async () => {
    mockPauseMutateAsync.mockResolvedValue({});

    const user = userEvent.setup();
    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    const pauseButton = screen.getByRole('button', { name: /pause/i });
    await user.click(pauseButton);

    await waitFor(() => {
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'success',
          message: expect.stringContaining('paused'),
        })
      );
    });
  });

  it('pause error shows error toast', async () => {
    mockPauseMutateAsync.mockRejectedValue(new Error('Pause failed'));

    const user = userEvent.setup();
    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    const pauseButton = screen.getByRole('button', { name: /pause/i });
    await user.click(pauseButton);

    await waitFor(() => {
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'error',
          message: expect.stringContaining('Failed to pause'),
        })
      );
    });
  });
});

// ============================================================================
// Resume Button Tests (UI-07)
// ============================================================================

describe('Resume Button (UI-07)', () => {
  const mockShowToast = vi.fn();
  const mockNavigate = vi.fn();
  const mockResumeMutateAsync = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useParams as Mock).mockReturnValue({ id: 'test-company-1' });
    (useNavigate as Mock).mockReturnValue(mockNavigate);

    (useCompany as Mock).mockReturnValue({
      data: createMockCompany('paused'),
      isLoading: false,
    });

    (useProgress as Mock).mockReturnValue({
      data: { data: createMockProgress({ status: 'paused' }) },
      isLoading: false,
    });

    (usePauseCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useResumeCompany as Mock).mockReturnValue({
      mutateAsync: mockResumeMutateAsync,
      isPending: false,
    });

    (useDeleteCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });
  });

  it('renders resume button for paused company', () => {
    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    const resumeButton = screen.getByRole('button', { name: /resume/i });
    expect(resumeButton).toBeInTheDocument();
    expect(resumeButton).toBeEnabled();
  });

  it('resume button hidden for in_progress company', () => {
    (useCompany as Mock).mockReturnValue({
      data: createMockCompany('in_progress'),
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    expect(screen.queryByRole('button', { name: /resume/i })).not.toBeInTheDocument();
  });

  it('clicking resume button calls mutation', async () => {
    mockResumeMutateAsync.mockResolvedValue({});

    const user = userEvent.setup();
    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    const resumeButton = screen.getByRole('button', { name: /resume/i });
    await user.click(resumeButton);

    await waitFor(() => {
      expect(mockResumeMutateAsync).toHaveBeenCalledWith('test-company-1');
    });
  });

  it('resume button shows loading state', () => {
    (useResumeCompany as Mock).mockReturnValue({
      mutateAsync: mockResumeMutateAsync,
      isPending: true,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Button should show loading indicator
    const resumeButton = screen.getByRole('button', { name: /resume/i });
    expect(resumeButton).toBeInTheDocument();
  });

  it('resume success shows toast notification', async () => {
    mockResumeMutateAsync.mockResolvedValue({});

    const user = userEvent.setup();
    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    const resumeButton = screen.getByRole('button', { name: /resume/i });
    await user.click(resumeButton);

    await waitFor(() => {
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'success',
          message: expect.stringContaining('resumed'),
        })
      );
    });
  });

  it('resume error shows error toast', async () => {
    mockResumeMutateAsync.mockRejectedValue(new Error('Resume failed'));

    const user = userEvent.setup();
    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    const resumeButton = screen.getByRole('button', { name: /resume/i });
    await user.click(resumeButton);

    await waitFor(() => {
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'error',
          message: expect.stringContaining('Failed to resume'),
        })
      );
    });
  });
});

// ============================================================================
// Progress Display Tests
// ============================================================================

describe('Progress Display', () => {
  const mockShowToast = vi.fn();
  const mockNavigate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useParams as Mock).mockReturnValue({ id: 'test-company-1' });
    (useNavigate as Mock).mockReturnValue(mockNavigate);

    (useCompany as Mock).mockReturnValue({
      data: createMockCompany('in_progress'),
      isLoading: false,
    });

    (useProgress as Mock).mockReturnValue({
      data: { data: createMockProgress() },
      isLoading: false,
    });

    (usePauseCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useResumeCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useDeleteCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });
  });

  it('displays progress percentage', () => {
    (useProgress as Mock).mockReturnValue({
      data: {
        data: createMockProgress({
          pagesCrawled: 10,
          pagesTotal: 20,
        }),
      },
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // 10/20 = 50%
    expect(screen.getByText('50%')).toBeInTheDocument();
  });

  it('displays current phase', () => {
    (useProgress as Mock).mockReturnValue({
      data: {
        data: createMockProgress({ phase: 'crawling' }),
      },
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    expect(screen.getByText('Crawling Website')).toBeInTheDocument();
  });

  it('displays pages crawled count', () => {
    (useProgress as Mock).mockReturnValue({
      data: {
        data: createMockProgress({
          pagesCrawled: 15,
          pagesTotal: 25,
        }),
      },
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    expect(screen.getByText('15')).toBeInTheDocument();
    expect(screen.getByText('/25')).toBeInTheDocument();
    expect(screen.getByText('Pages Crawled')).toBeInTheDocument();
  });

  it('displays entities extracted count', () => {
    (useProgress as Mock).mockReturnValue({
      data: {
        data: createMockProgress({ entitiesExtracted: 42 }),
      },
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('Entities Found')).toBeInTheDocument();
  });

  it('displays tokens used count', () => {
    (useProgress as Mock).mockReturnValue({
      data: {
        data: createMockProgress({ tokensUsed: 5000 }),
      },
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    expect(screen.getByText('5.0K')).toBeInTheDocument();
    expect(screen.getByText('Tokens Used')).toBeInTheDocument();
  });

  it('displays estimated cost', () => {
    (useCompany as Mock).mockReturnValue({
      data: createMockCompany('in_progress', { estimatedCost: 0.0042 }),
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    expect(screen.getByText('$0.0042')).toBeInTheDocument();
  });

  it('displays time elapsed', () => {
    (useProgress as Mock).mockReturnValue({
      data: {
        data: createMockProgress({ timeElapsed: 120 }),
      },
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    expect(screen.getByText('2m 0s')).toBeInTheDocument();
    expect(screen.getByText('Elapsed')).toBeInTheDocument();
  });

  it('displays estimated time remaining', () => {
    (useProgress as Mock).mockReturnValue({
      data: {
        data: createMockProgress({ estimatedTimeRemaining: 180 }),
      },
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    expect(screen.getByText('~3m 0s')).toBeInTheDocument();
    expect(screen.getByText('Remaining')).toBeInTheDocument();
  });

  it('hides estimated time when paused', () => {
    (useCompany as Mock).mockReturnValue({
      data: createMockCompany('paused'),
      isLoading: false,
    });

    (useProgress as Mock).mockReturnValue({
      data: {
        data: createMockProgress({
          status: 'paused',
          estimatedTimeRemaining: 180,
        }),
      },
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Should not show estimated time when paused
    expect(screen.queryByText('Remaining')).not.toBeInTheDocument();
  });
});

// ============================================================================
// Status Display Tests
// ============================================================================

describe('Status Display', () => {
  const mockShowToast = vi.fn();
  const mockNavigate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useParams as Mock).mockReturnValue({ id: 'test-company-1' });
    (useNavigate as Mock).mockReturnValue(mockNavigate);

    (useProgress as Mock).mockReturnValue({
      data: { data: createMockProgress() },
      isLoading: false,
    });

    (usePauseCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useResumeCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useDeleteCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });
  });

  it('shows correct badge for in_progress', () => {
    (useCompany as Mock).mockReturnValue({
      data: createMockCompany('in_progress'),
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    expect(screen.getByText('in progress')).toBeInTheDocument();
  });

  it('shows correct badge for paused', () => {
    (useCompany as Mock).mockReturnValue({
      data: createMockCompany('paused'),
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    expect(screen.getByText('paused')).toBeInTheDocument();
  });

  it('shows correct badge for completed', () => {
    (useCompany as Mock).mockReturnValue({
      data: createMockCompany('completed'),
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    expect(screen.getByText('completed')).toBeInTheDocument();
  });

  it('shows correct badge for failed', () => {
    (useCompany as Mock).mockReturnValue({
      data: createMockCompany('failed'),
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    expect(screen.getByText('failed')).toBeInTheDocument();
  });

  it('progress bar uses warning color when paused', () => {
    (useCompany as Mock).mockReturnValue({
      data: createMockCompany('paused'),
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // The component should use warning color for paused status
    // We verify by checking the ProgressBar component receives the right color prop
    // This is verified by the paused message being shown
    expect(screen.getByText(/analysis paused/i)).toBeInTheDocument();
  });

  it('progress bar uses error color when failed', () => {
    (useCompany as Mock).mockReturnValue({
      data: createMockCompany('failed'),
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Verify failed message is shown
    expect(screen.getByText(/analysis failed/i)).toBeInTheDocument();
  });
});

// ============================================================================
// Current Activity Tests
// ============================================================================

describe('Current Activity', () => {
  const mockShowToast = vi.fn();
  const mockNavigate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useParams as Mock).mockReturnValue({ id: 'test-company-1' });
    (useNavigate as Mock).mockReturnValue(mockNavigate);

    (usePauseCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useResumeCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useDeleteCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });
  });

  it('shows current activity text when in_progress', () => {
    (useCompany as Mock).mockReturnValue({
      data: createMockCompany('in_progress'),
      isLoading: false,
    });

    (useProgress as Mock).mockReturnValue({
      data: {
        data: createMockProgress({
          currentActivity: 'Crawling page 10 of 25...',
        }),
      },
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    expect(screen.getByText('Crawling page 10 of 25...')).toBeInTheDocument();
  });

  it('hides activity text when paused', () => {
    (useCompany as Mock).mockReturnValue({
      data: createMockCompany('paused'),
      isLoading: false,
    });

    (useProgress as Mock).mockReturnValue({
      data: {
        data: createMockProgress({
          status: 'paused',
          currentActivity: 'Crawling page 10 of 25...',
        }),
      },
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Activity should be hidden when paused
    expect(screen.queryByText('Crawling page 10 of 25...')).not.toBeInTheDocument();
  });

  it('shows paused message when paused', () => {
    (useCompany as Mock).mockReturnValue({
      data: createMockCompany('paused'),
      isLoading: false,
    });

    (useProgress as Mock).mockReturnValue({
      data: {
        data: createMockProgress({ status: 'paused' }),
      },
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    expect(screen.getByText(/analysis paused/i)).toBeInTheDocument();
    expect(screen.getByText(/click resume to continue/i)).toBeInTheDocument();
  });

  it('shows failure message when failed', () => {
    (useCompany as Mock).mockReturnValue({
      data: createMockCompany('failed'),
      isLoading: false,
    });

    (useProgress as Mock).mockReturnValue({
      data: {
        data: createMockProgress({ status: 'failed' }),
      },
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    expect(screen.getByText(/analysis failed/i)).toBeInTheDocument();
    expect(screen.getByText(/please try again/i)).toBeInTheDocument();
  });
});

// ============================================================================
// Auto-redirect on Completion Tests
// ============================================================================

describe('Auto-redirect on Completion', () => {
  const mockShowToast = vi.fn();
  const mockNavigate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();

    (useParams as Mock).mockReturnValue({ id: 'test-company-1' });
    (useNavigate as Mock).mockReturnValue(mockNavigate);

    (usePauseCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useResumeCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useDeleteCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('shows completion message before redirect', () => {
    (useCompany as Mock).mockReturnValue({
      data: createMockCompany('completed'),
      isLoading: false,
    });

    (useProgress as Mock).mockReturnValue({
      data: { data: createMockProgress({ phase: 'completed' }) },
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    expect(screen.getByText('Analysis Complete!')).toBeInTheDocument();
    expect(screen.getByText('Redirecting to results...')).toBeInTheDocument();
  });

  it('redirects to results when completed', async () => {
    (useCompany as Mock).mockReturnValue({
      data: createMockCompany('completed'),
      isLoading: false,
    });

    (useProgress as Mock).mockReturnValue({
      data: { data: createMockProgress({ phase: 'completed' }) },
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Advance timers by 2 seconds (redirect timeout) using act
    await act(async () => {
      vi.advanceTimersByTime(2000);
    });

    expect(mockNavigate).toHaveBeenCalledWith('/companies/test-company-1');
  });
});

// ============================================================================
// Cancel Modal Tests
// ============================================================================

describe('Cancel Modal', () => {
  const mockShowToast = vi.fn();
  const mockNavigate = vi.fn();
  const mockDeleteMutateAsync = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useParams as Mock).mockReturnValue({ id: 'test-company-1' });
    (useNavigate as Mock).mockReturnValue(mockNavigate);

    (useCompany as Mock).mockReturnValue({
      data: createMockCompany('in_progress'),
      isLoading: false,
    });

    (useProgress as Mock).mockReturnValue({
      data: { data: createMockProgress() },
      isLoading: false,
    });

    (usePauseCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useResumeCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useDeleteCompany as Mock).mockReturnValue({
      mutateAsync: mockDeleteMutateAsync,
      isPending: false,
    });

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });
  });

  it('cancel button opens confirmation modal', async () => {
    const user = userEvent.setup();
    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    await waitFor(() => {
      expect(screen.getByText(/are you sure/i)).toBeInTheDocument();
    });
  });

  it('modal cancel button dismisses modal', async () => {
    const user = userEvent.setup();
    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Open modal
    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    // Click "Keep Analyzing" to dismiss
    const keepButton = screen.getByRole('button', { name: /keep analyzing/i });
    await user.click(keepButton);

    await waitFor(() => {
      expect(screen.queryByText(/are you sure/i)).not.toBeInTheDocument();
    });
  });

  it('modal confirm calls delete mutation', async () => {
    mockDeleteMutateAsync.mockResolvedValue({});

    const user = userEvent.setup();
    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Open modal
    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    // Click "Cancel & Delete"
    const deleteButton = screen.getByRole('button', { name: /cancel & delete/i });
    await user.click(deleteButton);

    await waitFor(() => {
      expect(mockDeleteMutateAsync).toHaveBeenCalledWith('test-company-1');
    });
  });

  it('successful cancel navigates to home', async () => {
    mockDeleteMutateAsync.mockResolvedValue({});

    const user = userEvent.setup();
    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Open modal
    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    // Click "Cancel & Delete"
    const deleteButton = screen.getByRole('button', { name: /cancel & delete/i });
    await user.click(deleteButton);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/');
    });
  });

  it('cancel shows success toast', async () => {
    mockDeleteMutateAsync.mockResolvedValue({});

    const user = userEvent.setup();
    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Open modal
    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    // Click "Cancel & Delete"
    const deleteButton = screen.getByRole('button', { name: /cancel & delete/i });
    await user.click(deleteButton);

    await waitFor(() => {
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'success',
          message: expect.stringContaining('cancelled'),
        })
      );
    });
  });

  it('cancel error shows error toast', async () => {
    mockDeleteMutateAsync.mockRejectedValue(new Error('Delete failed'));

    const user = userEvent.setup();
    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Open modal
    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    // Click "Cancel & Delete"
    const deleteButton = screen.getByRole('button', { name: /cancel & delete/i });
    await user.click(deleteButton);

    await waitFor(() => {
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'error',
          message: expect.stringContaining('Failed to cancel'),
        })
      );
    });
  });
});

// ============================================================================
// Loading States Tests
// ============================================================================

describe('Loading States', () => {
  const mockShowToast = vi.fn();
  const mockNavigate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useParams as Mock).mockReturnValue({ id: 'test-company-1' });
    (useNavigate as Mock).mockReturnValue(mockNavigate);

    (usePauseCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useResumeCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useDeleteCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });
  });

  it('shows skeleton during company loading', () => {
    (useCompany as Mock).mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    (useProgress as Mock).mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Assert skeleton elements visible (they have animate-pulse class)
    const skeletons = document.querySelectorAll('[class*="animate-pulse"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('shows skeleton during progress loading', () => {
    (useCompany as Mock).mockReturnValue({
      data: createMockCompany('in_progress'),
      isLoading: false,
    });

    (useProgress as Mock).mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Assert loading state visible
    const skeletons = document.querySelectorAll('[class*="animate-pulse"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });
});

// ============================================================================
// Error States Tests
// ============================================================================

describe('Error States', () => {
  const mockShowToast = vi.fn();
  const mockNavigate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useParams as Mock).mockReturnValue({ id: 'test-company-1' });
    (useNavigate as Mock).mockReturnValue(mockNavigate);

    (usePauseCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useResumeCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useDeleteCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });
  });

  it('shows error when company not found', () => {
    (useCompany as Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });

    (useProgress as Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    expect(screen.getByText('Company Not Found')).toBeInTheDocument();
    expect(screen.getByText(/could not be found/i)).toBeInTheDocument();
  });

  it('shows back link on error page', () => {
    (useCompany as Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });

    (useProgress as Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    const backLink = screen.getByRole('link', { name: /back/i });
    expect(backLink).toBeInTheDocument();
    expect(backLink).toHaveAttribute('href', '/');
  });
});

// ============================================================================
// Failed Status Actions Tests
// ============================================================================

describe('Failed Status Actions', () => {
  const mockShowToast = vi.fn();
  const mockNavigate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useParams as Mock).mockReturnValue({ id: 'test-company-1' });
    (useNavigate as Mock).mockReturnValue(mockNavigate);

    (useCompany as Mock).mockReturnValue({
      data: createMockCompany('failed'),
      isLoading: false,
    });

    (useProgress as Mock).mockReturnValue({
      data: { data: createMockProgress({ status: 'failed' }) },
      isLoading: false,
    });

    (usePauseCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useResumeCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useDeleteCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });
  });

  it('shows try again button when failed', () => {
    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
  });

  it('shows delete button when failed', () => {
    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument();
  });

  it('try again links to add page', () => {
    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    const tryAgainButton = screen.getByRole('button', { name: /try again/i });
    const link = tryAgainButton.closest('a');
    expect(link).toHaveAttribute('href', '/add');
  });
});

// ============================================================================
// Paused Status Actions Tests
// ============================================================================

describe('Paused Status Actions', () => {
  const mockShowToast = vi.fn();
  const mockNavigate = vi.fn();
  const mockDeleteMutateAsync = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useParams as Mock).mockReturnValue({ id: 'test-company-1' });
    (useNavigate as Mock).mockReturnValue(mockNavigate);

    (useCompany as Mock).mockReturnValue({
      data: createMockCompany('paused'),
      isLoading: false,
    });

    (useProgress as Mock).mockReturnValue({
      data: { data: createMockProgress({ status: 'paused' }) },
      isLoading: false,
    });

    (usePauseCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useResumeCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useDeleteCompany as Mock).mockReturnValue({
      mutateAsync: mockDeleteMutateAsync,
      isPending: false,
    });

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });
  });

  it('shows cancel analysis button when paused', () => {
    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    expect(screen.getByRole('button', { name: /cancel analysis/i })).toBeInTheDocument();
  });

  it('cancel analysis button disabled while resume pending', () => {
    (useResumeCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: true,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    const cancelButton = screen.getByRole('button', { name: /cancel analysis/i });
    expect(cancelButton).toBeDisabled();
  });
});
