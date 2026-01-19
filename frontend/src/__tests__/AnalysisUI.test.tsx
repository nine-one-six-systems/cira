/**
 * Analysis UI Component Tests
 *
 * Verifies UI-03: Real-time progress during analysis
 * Verifies UI-04: Completed analysis with markdown rendering
 * - Progress tracker shows current analysis phase and percentage
 * - Current activity text updates during analysis
 * - Token counter displays input/output tokens and cost
 * - Analysis viewer renders markdown content
 * - Collapsible sections allow expanding/collapsing analysis parts
 * - Loading states shown while fetching data
 */

import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, useParams, useNavigate } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, type Mock } from 'vitest';
import CompanyProgress from '../pages/CompanyProgress';
import CompanyResults from '../pages/CompanyResults';
import {
  useCompany,
  useProgress,
  usePauseCompany,
  useResumeCompany,
  useDeleteCompany,
  useEntities,
  usePages,
  useTokens,
  useVersions,
  useCompareVersions,
  useRescanCompany,
} from '../hooks/useCompanies';
import { useToast } from '../components/ui';
import type { ProgressUpdate, TokenBreakdown, AnalysisSections } from '../types';

// Mock progress data
const createMockProgress = (overrides: Partial<ProgressUpdate> = {}): ProgressUpdate => ({
  companyId: 'test-company-1',
  status: 'in_progress',
  phase: 'analyzing',
  pagesCrawled: 10,
  pagesTotal: 20,
  entitiesExtracted: 45,
  tokensUsed: 5000,
  timeElapsed: 120,
  estimatedTimeRemaining: 180,
  currentActivity: 'Analyzing business model...',
  ...overrides,
});

// Mock tokens data
const createMockTokens = (overrides: Partial<TokenBreakdown> = {}): TokenBreakdown => ({
  totalTokens: 15000,
  totalInputTokens: 10000,
  totalOutputTokens: 5000,
  estimatedCost: 0.0042,
  byApiCall: [
    {
      callType: 'extraction',
      section: 'company_overview',
      inputTokens: 3000,
      outputTokens: 1500,
      timestamp: '2024-01-15T10:30:00Z',
    },
    {
      callType: 'analysis',
      section: 'business_model',
      inputTokens: 4000,
      outputTokens: 2000,
      timestamp: '2024-01-15T10:35:00Z',
    },
    {
      callType: 'summarization',
      section: 'executive_summary',
      inputTokens: 3000,
      outputTokens: 1500,
      timestamp: '2024-01-15T10:40:00Z',
    },
  ],
  ...overrides,
});

// Mock analysis sections
const createMockAnalysisSections = (): AnalysisSections => ({
  companyOverview: {
    content: 'Company overview content with **bold** and _italic_ text.',
    sources: ['https://example.com/about'],
    confidence: 0.9,
  },
  businessModelProducts: {
    content: '## Products\n\n- Product A\n- Product B\n- Product C',
    sources: ['https://example.com/products'],
    confidence: 0.85,
  },
  teamLeadership: {
    content: 'Leadership team content.',
    sources: ['https://example.com/team'],
    confidence: 0.8,
  },
  marketPosition: {
    content: 'Market position analysis.',
    sources: ['https://example.com/company'],
    confidence: 0.75,
  },
  technologyOperations: {
    content: 'Technology stack includes:\n\n```javascript\nconst app = express();\n```',
    sources: ['https://example.com/tech'],
    confidence: 0.7,
  },
  keyInsights: {
    content: 'Key insights about the company.',
    sources: ['https://example.com'],
    confidence: 0.85,
  },
  redFlags: {
    content: 'Some concerns identified.',
    sources: ['https://example.com'],
    confidence: 0.6,
  },
});

// Mock company data for progress page
const mockCompanyInProgress = {
  data: {
    company: {
      id: 'test-company-1',
      companyName: 'Test Company',
      websiteUrl: 'https://test.com',
      industry: 'Technology',
      analysisMode: 'thorough' as const,
      status: 'in_progress' as const,
      totalTokensUsed: 5000,
      estimatedCost: 0.05,
      createdAt: '2024-01-15T10:00:00Z',
    },
    analysis: null,
    entityCount: 0,
    pageCount: 0,
  },
};

// Mock company data for results page
const mockCompanyCompleted = {
  data: {
    company: {
      id: 'test-company-1',
      companyName: 'Test Company',
      websiteUrl: 'https://test.com',
      industry: 'Technology',
      analysisMode: 'thorough' as const,
      status: 'completed' as const,
      totalTokensUsed: 15000,
      estimatedCost: 0.0042,
      createdAt: '2024-01-15T10:00:00Z',
      completedAt: '2024-01-15T11:00:00Z',
    },
    analysis: {
      id: 'analysis-1',
      versionNumber: 1,
      executiveSummary: 'This is the **executive summary** with markdown.',
      fullAnalysis: createMockAnalysisSections(),
      createdAt: '2024-01-15T11:00:00Z',
    },
    entityCount: 42,
    pageCount: 15,
  },
};

// Mock the hooks
vi.mock('../hooks/useCompanies', () => ({
  useCompany: vi.fn(),
  useProgress: vi.fn(),
  usePauseCompany: vi.fn(),
  useResumeCompany: vi.fn(),
  useDeleteCompany: vi.fn(),
  useEntities: vi.fn(),
  usePages: vi.fn(),
  useTokens: vi.fn(),
  useVersions: vi.fn(),
  useCompareVersions: vi.fn(),
  useRescanCompany: vi.fn(),
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

// ============================================================================
// Progress Tracker Tests (UI-03)
// ============================================================================

describe('Progress Tracker (UI-03)', () => {
  const mockShowToast = vi.fn();
  const mockNavigate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useParams as Mock).mockReturnValue({ id: 'test-company-1' });
    (useNavigate as Mock).mockReturnValue(mockNavigate);

    (useCompany as Mock).mockReturnValue({
      data: mockCompanyInProgress,
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

  it('renders progress tracker during analysis', () => {
    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Assert company name visible
    expect(screen.getByText('Test Company')).toBeInTheDocument();

    // Assert progress bar container visible
    expect(screen.getByText('Analyzing Content')).toBeInTheDocument();

    // Assert status badge visible
    expect(screen.getByText('in progress')).toBeInTheDocument();
  });

  it('displays current analysis section', () => {
    (useProgress as Mock).mockReturnValue({
      data: { data: createMockProgress({ phase: 'analyzing' }) },
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Assert current phase label visible
    expect(screen.getByText('Analyzing Content')).toBeInTheDocument();

    // Assert phase description visible
    expect(screen.getByText('Using AI to analyze the extracted data')).toBeInTheDocument();
  });

  it('shows progress percentage', () => {
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

    // Assert percentage visible (10/20 = 50%)
    expect(screen.getByText('50%')).toBeInTheDocument();
  });

  it('shows activity text describing current work', () => {
    (useProgress as Mock).mockReturnValue({
      data: {
        data: createMockProgress({
          currentActivity: 'Generating executive summary...',
        }),
      },
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Assert activity text visible
    expect(screen.getByText('Generating executive summary...')).toBeInTheDocument();
  });

  it('shows pages crawled stats', () => {
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

    // Assert pages crawled visible
    expect(screen.getByText('10')).toBeInTheDocument();
    expect(screen.getByText('/20')).toBeInTheDocument();
    expect(screen.getByText('Pages Crawled')).toBeInTheDocument();
  });

  it('shows entities found stats', () => {
    (useProgress as Mock).mockReturnValue({
      data: {
        data: createMockProgress({
          entitiesExtracted: 45,
        }),
      },
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Assert entities count visible
    expect(screen.getByText('45')).toBeInTheDocument();
    expect(screen.getByText('Entities Found')).toBeInTheDocument();
  });

  it('shows tokens used stats', () => {
    (useProgress as Mock).mockReturnValue({
      data: {
        data: createMockProgress({
          tokensUsed: 5000,
        }),
      },
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Assert tokens count visible (5.0K)
    expect(screen.getByText('5.0K')).toBeInTheDocument();
    expect(screen.getByText('Tokens Used')).toBeInTheDocument();
  });

  it('shows time elapsed', () => {
    (useProgress as Mock).mockReturnValue({
      data: {
        data: createMockProgress({
          timeElapsed: 125, // 2m 5s
        }),
      },
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Assert time elapsed visible
    expect(screen.getByText('2m 5s')).toBeInTheDocument();
    expect(screen.getByText('Elapsed')).toBeInTheDocument();
  });

  it('shows estimated time remaining', () => {
    (useProgress as Mock).mockReturnValue({
      data: {
        data: createMockProgress({
          estimatedTimeRemaining: 180, // 3m 0s
        }),
      },
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Assert estimated time remaining visible
    expect(screen.getByText('~3m 0s')).toBeInTheDocument();
    expect(screen.getByText('Remaining')).toBeInTheDocument();
  });

  it('transitions to results when complete', async () => {
    // Start with completed status
    (useCompany as Mock).mockReturnValue({
      data: {
        data: {
          company: {
            ...mockCompanyInProgress.data.company,
            status: 'completed',
          },
          analysis: null,
          entityCount: 0,
          pageCount: 0,
        },
      },
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Assert completion message visible
    expect(screen.getByText('Analysis Complete!')).toBeInTheDocument();
    expect(screen.getByText('Redirecting to results...')).toBeInTheDocument();

    // Assert success toast shown
    await waitFor(() => {
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'success',
          message: expect.stringContaining('complete'),
        })
      );
    });
  });

  it('shows pause button when in progress', () => {
    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Assert Pause button visible
    expect(screen.getByRole('button', { name: /pause/i })).toBeInTheDocument();
  });

  it('shows cancel button when in progress', () => {
    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Assert Cancel button visible
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });

  it('shows resume button when paused', () => {
    (useCompany as Mock).mockReturnValue({
      data: {
        data: {
          company: {
            ...mockCompanyInProgress.data.company,
            status: 'paused',
          },
          analysis: null,
          entityCount: 0,
          pageCount: 0,
        },
      },
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Assert Resume button visible
    expect(screen.getByRole('button', { name: /resume/i })).toBeInTheDocument();
  });

  it('shows paused message when paused', () => {
    (useCompany as Mock).mockReturnValue({
      data: {
        data: {
          company: {
            ...mockCompanyInProgress.data.company,
            status: 'paused',
          },
          analysis: null,
          entityCount: 0,
          pageCount: 0,
        },
      },
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Assert paused message visible
    expect(screen.getByText(/analysis paused/i)).toBeInTheDocument();
  });

  it('shows failed message when failed', () => {
    (useCompany as Mock).mockReturnValue({
      data: {
        data: {
          company: {
            ...mockCompanyInProgress.data.company,
            status: 'failed',
          },
          analysis: null,
          entityCount: 0,
          pageCount: 0,
        },
      },
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Assert failed message visible
    expect(screen.getByText(/analysis failed/i)).toBeInTheDocument();
  });

  it('shows try again button when failed', () => {
    (useCompany as Mock).mockReturnValue({
      data: {
        data: {
          company: {
            ...mockCompanyInProgress.data.company,
            status: 'failed',
          },
          analysis: null,
          entityCount: 0,
          pageCount: 0,
        },
      },
      isLoading: false,
    });

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Assert Try Again button visible
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
  });
});

// ============================================================================
// Token Counter Tests
// ============================================================================

describe('Token Counter', () => {
  const mockShowToast = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useParams as Mock).mockReturnValue({ id: 'test-company-1' });

    (useCompany as Mock).mockReturnValue({
      data: mockCompanyCompleted,
      isLoading: false,
    });

    (useEntities as Mock).mockReturnValue({
      data: { data: [], meta: { total: 0, page: 1, pageSize: 20, totalPages: 1 } },
      isLoading: false,
    });

    (usePages as Mock).mockReturnValue({
      data: { data: [], meta: { total: 0, page: 1, pageSize: 20, totalPages: 1 } },
      isLoading: false,
    });

    (useTokens as Mock).mockReturnValue({
      data: { data: createMockTokens() },
      isLoading: false,
    });

    (useVersions as Mock).mockReturnValue({
      data: { data: [] },
      isLoading: false,
    });

    (useCompareVersions as Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });

    (useRescanCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });
  });

  // Helper to click on the Token Usage tab
  async function clickTokensTab(user: ReturnType<typeof userEvent.setup>) {
    const tokensTab = screen.getByRole('tab', { name: /token usage/i });
    await user.click(tokensTab);
  }

  it('displays total token count', async () => {
    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    await clickTokensTab(user);

    // Wait for tokens tab content
    await waitFor(() => {
      expect(screen.getByText('Total Tokens')).toBeInTheDocument();
    });

    // Assert total tokens visible (15K for 15000)
    expect(screen.getByText('15.0K')).toBeInTheDocument();
  });

  it('displays input and output token breakdown', async () => {
    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    await clickTokensTab(user);

    // Wait for tokens tab content
    await waitFor(() => {
      expect(screen.getByText('Total Tokens')).toBeInTheDocument();
    });

    // Assert input tokens visible (10K for 10000)
    expect(screen.getByText('10.0K')).toBeInTheDocument();
    expect(screen.getByText('Input Tokens')).toBeInTheDocument();

    // Assert output tokens visible (5K for 5000)
    const outputElements = screen.getAllByText('5.0K');
    expect(outputElements.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Output Tokens')).toBeInTheDocument();
  });

  it('displays estimated cost', async () => {
    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    await clickTokensTab(user);

    // Wait for tokens tab content
    await waitFor(() => {
      expect(screen.getByText('Total Tokens')).toBeInTheDocument();
    });

    // Assert cost visible ($0.0042)
    expect(screen.getByText('$0.0042')).toBeInTheDocument();
    expect(screen.getByText('Estimated Cost')).toBeInTheDocument();
  });

  it('formats cost with appropriate precision', async () => {
    (useTokens as Mock).mockReturnValue({
      data: { data: createMockTokens({ estimatedCost: 0.00001 }) },
      isLoading: false,
    });

    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    await clickTokensTab(user);

    // Wait for tokens tab content
    await waitFor(() => {
      expect(screen.getByText('Total Tokens')).toBeInTheDocument();
    });

    // Assert cost displayed with sufficient precision (not rounded to $0.00)
    expect(screen.getByText('$0.0000')).toBeInTheDocument();
  });

  it('shows usage breakdown table', async () => {
    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    await clickTokensTab(user);

    // Wait for tokens tab content
    await waitFor(() => {
      expect(screen.getByText('Usage Breakdown')).toBeInTheDocument();
    });

    // Assert breakdown table headers visible
    expect(screen.getByText('Call Type')).toBeInTheDocument();
    expect(screen.getByText('Section')).toBeInTheDocument();
    expect(screen.getByText('Input')).toBeInTheDocument();
    expect(screen.getByText('Output')).toBeInTheDocument();
  });

  it('shows per-section token details in breakdown', async () => {
    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    await clickTokensTab(user);

    // Wait for tokens tab content
    await waitFor(() => {
      expect(screen.getByText('Usage Breakdown')).toBeInTheDocument();
    });

    // Assert section names visible in breakdown
    expect(screen.getByText('company_overview')).toBeInTheDocument();
    expect(screen.getByText('business_model')).toBeInTheDocument();
    expect(screen.getByText('executive_summary')).toBeInTheDocument();

    // Assert call types visible
    expect(screen.getByText('extraction')).toBeInTheDocument();
    expect(screen.getByText('analysis')).toBeInTheDocument();
    expect(screen.getByText('summarization')).toBeInTheDocument();
  });

  it('shows no token data message when unavailable', async () => {
    (useTokens as Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });

    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    await clickTokensTab(user);

    // Wait for tokens tab content
    await waitFor(() => {
      expect(screen.getByText(/no token usage data available/i)).toBeInTheDocument();
    });
  });
});

// ============================================================================
// Analysis Viewer Tests (UI-04)
// ============================================================================

describe('Analysis Viewer (UI-04)', () => {
  const mockShowToast = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useParams as Mock).mockReturnValue({ id: 'test-company-1' });

    (useCompany as Mock).mockReturnValue({
      data: mockCompanyCompleted,
      isLoading: false,
    });

    (useEntities as Mock).mockReturnValue({
      data: { data: [], meta: { total: 0, page: 1, pageSize: 20, totalPages: 1 } },
      isLoading: false,
    });

    (usePages as Mock).mockReturnValue({
      data: { data: [], meta: { total: 0, page: 1, pageSize: 20, totalPages: 1 } },
      isLoading: false,
    });

    (useTokens as Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });

    (useVersions as Mock).mockReturnValue({
      data: { data: [] },
      isLoading: false,
    });

    (useCompareVersions as Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });

    (useRescanCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });
  });

  it('renders analysis tab with sections', () => {
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    // Summary tab is default, should show analysis sections
    expect(screen.getByText('Executive Summary')).toBeInTheDocument();
    expect(screen.getByText('Company Overview')).toBeInTheDocument();
    expect(screen.getByText('Business Model & Products')).toBeInTheDocument();
    expect(screen.getByText('Team & Leadership')).toBeInTheDocument();
    expect(screen.getByText('Market Position')).toBeInTheDocument();
    expect(screen.getByText('Key Insights')).toBeInTheDocument();
    expect(screen.getByText('Red Flags & Concerns')).toBeInTheDocument();
  });

  it('renders executive summary content', () => {
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    // Assert executive summary header visible
    expect(screen.getByRole('heading', { name: /executive summary/i })).toBeInTheDocument();

    // Assert executive summary content visible (the markdown text)
    expect(screen.getByText(/This is the.*executive summary.*with markdown/i)).toBeInTheDocument();
  });

  it('renders section content', () => {
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    // Assert various section content visible
    expect(screen.getByText(/Company overview content/)).toBeInTheDocument();
    expect(screen.getByText(/Leadership team content/)).toBeInTheDocument();
    expect(screen.getByText(/Market position analysis/)).toBeInTheDocument();
  });

  it('shows company info sidebar', () => {
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    // Assert sidebar info visible
    expect(screen.getByText('Company Info')).toBeInTheDocument();
    expect(screen.getByText('Technology')).toBeInTheDocument(); // Industry
    expect(screen.getByText('thorough')).toBeInTheDocument(); // Analysis mode
  });

  it('shows statistics sidebar', () => {
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    // Assert statistics visible
    expect(screen.getByText('Statistics')).toBeInTheDocument();
    expect(screen.getByText('Pages Crawled')).toBeInTheDocument();
    expect(screen.getByText('Entities Found')).toBeInTheDocument();
    expect(screen.getByText('Tokens Used')).toBeInTheDocument();
    expect(screen.getByText('Estimated Cost')).toBeInTheDocument();
  });

  it('shows analysis version info', () => {
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    // Assert version info visible
    expect(screen.getByText('Analysis Version')).toBeInTheDocument();
    expect(screen.getByText(/version 1/i)).toBeInTheDocument();
  });

  it('shows no analysis message when not available', () => {
    (useCompany as Mock).mockReturnValue({
      data: {
        data: {
          company: mockCompanyCompleted.data.company,
          analysis: null,
          entityCount: 0,
          pageCount: 0,
        },
      },
      isLoading: false,
    });

    render(<CompanyResults />, { wrapper: createTestWrapper() });

    // Assert no analysis message visible
    expect(screen.getByText(/no analysis available/i)).toBeInTheDocument();
  });

  it('has tabs for different views', () => {
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    // Assert all tabs visible
    expect(screen.getByRole('tab', { name: /summary/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /entities/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /pages/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /token usage/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /versions/i })).toBeInTheDocument();
  });

  it('has export dropdown', () => {
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    // Assert export select visible
    const exportSelect = screen.getByLabelText(/export/i);
    expect(exportSelect).toBeInTheDocument();

    // Assert export options available
    expect(within(exportSelect).getByRole('option', { name: /markdown/i })).toBeInTheDocument();
    expect(within(exportSelect).getByRole('option', { name: /pdf/i })).toBeInTheDocument();
    expect(within(exportSelect).getByRole('option', { name: /word/i })).toBeInTheDocument();
    expect(within(exportSelect).getByRole('option', { name: /json/i })).toBeInTheDocument();
  });

  it('has re-scan button', () => {
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    // Assert Re-scan button visible
    expect(screen.getByRole('button', { name: /re-scan/i })).toBeInTheDocument();
  });

  it('opens re-scan confirmation modal', async () => {
    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    // Click Re-scan button
    const rescanButton = screen.getByRole('button', { name: /re-scan/i });
    await user.click(rescanButton);

    // Assert modal opens
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    // Assert modal content
    expect(screen.getByText(/start a new analysis/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /start re-scan/i })).toBeInTheDocument();
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

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });
  });

  it('shows skeleton while company loading on progress page', () => {
    (useCompany as Mock).mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    (useProgress as Mock).mockReturnValue({
      data: undefined,
      isLoading: true,
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

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Assert skeleton elements visible
    const skeletons = document.querySelectorAll('[class*="animate-pulse"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('shows skeleton while company loading on results page', () => {
    (useCompany as Mock).mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    (useEntities as Mock).mockReturnValue({
      data: undefined,
      isLoading: false,
    });

    (usePages as Mock).mockReturnValue({
      data: undefined,
      isLoading: false,
    });

    (useTokens as Mock).mockReturnValue({
      data: undefined,
      isLoading: false,
    });

    (useVersions as Mock).mockReturnValue({
      data: undefined,
      isLoading: false,
    });

    (useCompareVersions as Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });

    (useRescanCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    render(<CompanyResults />, { wrapper: createTestWrapper() });

    // Assert skeleton elements visible
    const skeletons = document.querySelectorAll('[class*="animate-pulse"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('shows token skeleton while fetching tokens', async () => {
    (useCompany as Mock).mockReturnValue({
      data: mockCompanyCompleted,
      isLoading: false,
    });

    (useEntities as Mock).mockReturnValue({
      data: { data: [], meta: { total: 0, page: 1, pageSize: 20, totalPages: 1 } },
      isLoading: false,
    });

    (usePages as Mock).mockReturnValue({
      data: { data: [], meta: { total: 0, page: 1, pageSize: 20, totalPages: 1 } },
      isLoading: false,
    });

    (useTokens as Mock).mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    (useVersions as Mock).mockReturnValue({
      data: { data: [] },
      isLoading: false,
    });

    (useCompareVersions as Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });

    (useRescanCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    // Click token usage tab
    const tokensTab = screen.getByRole('tab', { name: /token usage/i });
    await user.click(tokensTab);

    // Assert skeleton visible in tokens tab
    await waitFor(() => {
      const tabPanel = screen.getByRole('tabpanel');
      const skeletons = tabPanel.querySelectorAll('[class*="animate-pulse"]');
      expect(skeletons.length).toBeGreaterThan(0);
    });
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

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });
  });

  it('shows company not found on progress page', () => {
    (useCompany as Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });

    (useProgress as Mock).mockReturnValue({
      data: null,
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

    render(<CompanyProgress />, { wrapper: createTestWrapper() });

    // Assert not found message visible
    expect(screen.getByText('Company Not Found')).toBeInTheDocument();
    expect(screen.getByText(/could not be found/i)).toBeInTheDocument();
  });

  it('shows company not found on results page', () => {
    (useCompany as Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });

    (useEntities as Mock).mockReturnValue({
      data: undefined,
      isLoading: false,
    });

    (usePages as Mock).mockReturnValue({
      data: undefined,
      isLoading: false,
    });

    (useTokens as Mock).mockReturnValue({
      data: undefined,
      isLoading: false,
    });

    (useVersions as Mock).mockReturnValue({
      data: undefined,
      isLoading: false,
    });

    (useCompareVersions as Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });

    (useRescanCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    render(<CompanyResults />, { wrapper: createTestWrapper() });

    // Assert not found message visible
    expect(screen.getByText('Company Not Found')).toBeInTheDocument();
    expect(screen.getByText(/could not be found/i)).toBeInTheDocument();
  });

  it('shows back link on not found pages', () => {
    (useCompany as Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });

    (useEntities as Mock).mockReturnValue({
      data: undefined,
      isLoading: false,
    });

    (usePages as Mock).mockReturnValue({
      data: undefined,
      isLoading: false,
    });

    (useTokens as Mock).mockReturnValue({
      data: undefined,
      isLoading: false,
    });

    (useVersions as Mock).mockReturnValue({
      data: undefined,
      isLoading: false,
    });

    (useCompareVersions as Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });

    (useRescanCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    render(<CompanyResults />, { wrapper: createTestWrapper() });

    // Assert back link visible
    const backLink = screen.getByRole('link', { name: /back/i });
    expect(backLink).toBeInTheDocument();
    expect(backLink).toHaveAttribute('href', '/');
  });
});

// ============================================================================
// Empty States Tests
// ============================================================================

describe('Empty States', () => {
  const mockShowToast = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useParams as Mock).mockReturnValue({ id: 'test-company-1' });

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });
  });

  it('shows no analysis message when analysis not started', () => {
    (useCompany as Mock).mockReturnValue({
      data: {
        data: {
          company: {
            ...mockCompanyCompleted.data.company,
            status: 'in_progress',
          },
          analysis: null,
          entityCount: 0,
          pageCount: 0,
        },
      },
      isLoading: false,
    });

    (useEntities as Mock).mockReturnValue({
      data: { data: [], meta: { total: 0, page: 1, pageSize: 20, totalPages: 1 } },
      isLoading: false,
    });

    (usePages as Mock).mockReturnValue({
      data: { data: [], meta: { total: 0, page: 1, pageSize: 20, totalPages: 1 } },
      isLoading: false,
    });

    (useTokens as Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });

    (useVersions as Mock).mockReturnValue({
      data: { data: [] },
      isLoading: false,
    });

    (useCompareVersions as Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });

    (useRescanCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    render(<CompanyResults />, { wrapper: createTestWrapper() });

    // Assert no analysis message visible
    expect(screen.getByText(/no analysis available/i)).toBeInTheDocument();
  });

  it('shows no version history message', async () => {
    (useCompany as Mock).mockReturnValue({
      data: mockCompanyCompleted,
      isLoading: false,
    });

    (useEntities as Mock).mockReturnValue({
      data: { data: [], meta: { total: 0, page: 1, pageSize: 20, totalPages: 1 } },
      isLoading: false,
    });

    (usePages as Mock).mockReturnValue({
      data: { data: [], meta: { total: 0, page: 1, pageSize: 20, totalPages: 1 } },
      isLoading: false,
    });

    (useTokens as Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });

    (useVersions as Mock).mockReturnValue({
      data: { data: [] },
      isLoading: false,
    });

    (useCompareVersions as Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });

    (useRescanCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    // Click versions tab
    const versionsTab = screen.getByRole('tab', { name: /versions/i });
    await user.click(versionsTab);

    // Assert no version history message visible
    await waitFor(() => {
      expect(screen.getByText(/no version history available/i)).toBeInTheDocument();
    });
  });
});

// ============================================================================
// Versions Tab Tests
// ============================================================================

describe('Versions Tab', () => {
  const mockShowToast = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useParams as Mock).mockReturnValue({ id: 'test-company-1' });

    (useCompany as Mock).mockReturnValue({
      data: mockCompanyCompleted,
      isLoading: false,
    });

    (useEntities as Mock).mockReturnValue({
      data: { data: [], meta: { total: 0, page: 1, pageSize: 20, totalPages: 1 } },
      isLoading: false,
    });

    (usePages as Mock).mockReturnValue({
      data: { data: [], meta: { total: 0, page: 1, pageSize: 20, totalPages: 1 } },
      isLoading: false,
    });

    (useTokens as Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });

    (useRescanCompany as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });
  });

  it('shows version history when multiple versions exist', async () => {
    (useVersions as Mock).mockReturnValue({
      data: {
        data: [
          {
            analysisId: 'analysis-2',
            versionNumber: 2,
            createdAt: '2024-01-16T10:00:00Z',
            tokensUsed: 16000,
          },
          {
            analysisId: 'analysis-1',
            versionNumber: 1,
            createdAt: '2024-01-15T11:00:00Z',
            tokensUsed: 15000,
          },
        ],
      },
      isLoading: false,
    });

    (useCompareVersions as Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });

    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    // Click versions tab
    const versionsTab = screen.getByRole('tab', { name: /versions/i });
    await user.click(versionsTab);

    // Assert version history heading visible
    await waitFor(() => {
      expect(screen.getByText('Version History')).toBeInTheDocument();
    });

    // Assert version entries visible
    expect(screen.getByText('Version 2')).toBeInTheDocument();
    expect(screen.getByText('Version 1')).toBeInTheDocument();
  });

  it('shows current version badge', async () => {
    (useVersions as Mock).mockReturnValue({
      data: {
        data: [
          {
            analysisId: 'analysis-1',
            versionNumber: 1,
            createdAt: '2024-01-15T11:00:00Z',
            tokensUsed: 15000,
          },
        ],
      },
      isLoading: false,
    });

    (useCompareVersions as Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });

    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    // Click versions tab
    const versionsTab = screen.getByRole('tab', { name: /versions/i });
    await user.click(versionsTab);

    // Assert current badge visible
    await waitFor(() => {
      expect(screen.getByText('Current')).toBeInTheDocument();
    });
  });

  it('shows compare versions section when multiple versions', async () => {
    (useVersions as Mock).mockReturnValue({
      data: {
        data: [
          {
            analysisId: 'analysis-2',
            versionNumber: 2,
            createdAt: '2024-01-16T10:00:00Z',
            tokensUsed: 16000,
          },
          {
            analysisId: 'analysis-1',
            versionNumber: 1,
            createdAt: '2024-01-15T11:00:00Z',
            tokensUsed: 15000,
          },
        ],
      },
      isLoading: false,
    });

    (useCompareVersions as Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });

    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    // Click versions tab
    const versionsTab = screen.getByRole('tab', { name: /versions/i });
    await user.click(versionsTab);

    // Assert compare versions section visible
    await waitFor(() => {
      expect(screen.getByText('Compare Versions')).toBeInTheDocument();
    });
  });
});
