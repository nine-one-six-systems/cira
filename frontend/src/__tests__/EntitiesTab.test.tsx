/**
 * EntitiesTab Component Tests
 *
 * Verifies UI-05: Entity browser with filtering
 * - Entity table displays type, value, confidence, source
 * - Type filter dropdown filters entities by selected type
 * - Confidence displayed as colored progress bar
 * - Pagination controls navigate between pages
 * - Loading state shows skeleton while fetching
 */

import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, useParams } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, type Mock } from 'vitest';
import CompanyResults from '../pages/CompanyResults';
import {
  useCompany,
  useEntities,
  usePages,
  useTokens,
  useVersions,
  useCompareVersions,
  useRescanCompany,
} from '../hooks/useCompanies';
import { useToast } from '../components/ui';
import type { Entity, EntityType } from '../types';

// Mock entity data
const createMockEntity = (overrides: Partial<Entity> = {}): Entity => ({
  id: `entity-${Math.random().toString(36).substr(2, 9)}`,
  entityType: 'person',
  entityValue: 'John Smith',
  contextSnippet: 'CEO John Smith leads the company',
  sourceUrl: 'https://example.com/about',
  confidenceScore: 0.85,
  ...overrides,
});

const mockEntities: Entity[] = [
  createMockEntity({
    id: 'entity-1',
    entityType: 'person',
    entityValue: 'John Smith',
    contextSnippet: 'CEO John Smith leads the company',
    confidenceScore: 0.9,
    sourceUrl: 'https://example.com/about',
  }),
  createMockEntity({
    id: 'entity-2',
    entityType: 'org',
    entityValue: 'Acme Corporation',
    contextSnippet: 'Acme Corporation is a leading provider',
    confidenceScore: 0.75,
    sourceUrl: 'https://example.com/company',
  }),
  createMockEntity({
    id: 'entity-3',
    entityType: 'email',
    entityValue: 'contact@example.com',
    contextSnippet: 'Contact us at contact@example.com',
    confidenceScore: 0.45,
    sourceUrl: 'https://example.com/contact',
  }),
];

// Mock company data
const mockCompanyData = {
  data: {
    company: {
      id: 'test-company-1',
      companyName: 'Test Company',
      websiteUrl: 'https://test.com',
      industry: 'Technology',
      analysisMode: 'thorough' as const,
      status: 'completed' as const,
      totalTokensUsed: 5000,
      estimatedCost: 0.05,
      createdAt: '2024-01-15T10:00:00Z',
      completedAt: '2024-01-15T11:00:00Z',
    },
    analysis: {
      id: 'analysis-1',
      versionNumber: 1,
      executiveSummary: 'Test summary',
      fullAnalysis: null,
      createdAt: '2024-01-15T11:00:00Z',
    },
    entityCount: 42,
    pageCount: 15,
  },
};

// Mock the hooks
vi.mock('../hooks/useCompanies', () => ({
  useCompany: vi.fn(),
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

// Helper to click on the Entities tab
async function clickEntitiesTab(user: ReturnType<typeof userEvent.setup>) {
  // Find and click the Entities tab
  const entitiesTab = screen.getByRole('tab', { name: /entities/i });
  await user.click(entitiesTab);
}

describe('Entity Table Display', () => {
  const mockShowToast = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useParams as Mock).mockReturnValue({ id: 'test-company-1' });

    (useCompany as Mock).mockReturnValue({
      data: mockCompanyData,
      isLoading: false,
    });

    (useEntities as Mock).mockReturnValue({
      data: {
        data: mockEntities,
        meta: { total: 3, page: 1, pageSize: 20, totalPages: 1 },
      },
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

  it('renders entity table with columns', async () => {
    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    await clickEntitiesTab(user);

    // Wait for entities tab content to load
    await waitFor(() => {
      expect(screen.getByText('John Smith')).toBeInTheDocument();
    });

    // Assert table headers visible (use getAllByText for 'Type' as it appears in filter label and table header)
    const typeElements = screen.getAllByText('Type');
    expect(typeElements.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Value')).toBeInTheDocument();
    expect(screen.getByText('Confidence')).toBeInTheDocument();
    expect(screen.getByText('Source')).toBeInTheDocument();

    // Assert 3 entity values in table
    expect(screen.getByText('Acme Corporation')).toBeInTheDocument();
    expect(screen.getByText('contact@example.com')).toBeInTheDocument();
  });

  it('displays entity type as badge', async () => {
    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    await clickEntitiesTab(user);

    // Wait for entities tab content to load
    await waitFor(() => {
      expect(screen.getByText('John Smith')).toBeInTheDocument();
    });

    // Assert Badge components show entity types (these also appear in dropdown, so use getAllByText)
    // The badges in the table are distinct from dropdown options
    const personElements = screen.getAllByText('Person');
    expect(personElements.length).toBeGreaterThanOrEqual(1);
    const orgElements = screen.getAllByText('Organization');
    expect(orgElements.length).toBeGreaterThanOrEqual(1);
    const emailElements = screen.getAllByText('Email');
    expect(emailElements.length).toBeGreaterThanOrEqual(1);
  });

  it('displays entity value with context snippet', async () => {
    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    await clickEntitiesTab(user);

    // Assert entity value visible
    await waitFor(() => {
      expect(screen.getByText('John Smith')).toBeInTheDocument();
    });

    // Assert context snippet visible (may be truncated with ellipsis)
    expect(screen.getByText(/CEO John Smith leads/)).toBeInTheDocument();
  });

  it('displays confidence as colored progress bar', async () => {
    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    await clickEntitiesTab(user);

    // Wait for content to load
    await waitFor(() => {
      expect(screen.getByText('John Smith')).toBeInTheDocument();
    });

    // Check for progress bars (confidence scores as percentages)
    expect(screen.getByText('90%')).toBeInTheDocument(); // 0.9 confidence
    expect(screen.getByText('75%')).toBeInTheDocument(); // 0.75 confidence
    expect(screen.getByText('45%')).toBeInTheDocument(); // 0.45 confidence

    // Verify color classes by checking for the progress bar elements
    // High confidence (>= 0.8) should have bg-success
    const progressBars = document.querySelectorAll('[class*="bg-success"], [class*="bg-warning"], [class*="bg-error"]');
    expect(progressBars.length).toBeGreaterThanOrEqual(3);
  });

  it('displays source URL as clickable link', async () => {
    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    await clickEntitiesTab(user);

    await waitFor(() => {
      expect(screen.getByText('John Smith')).toBeInTheDocument();
    });

    // Find links with target="_blank" (external links)
    const sourceLinks = screen.getAllByRole('link').filter(
      (link) => link.getAttribute('target') === '_blank'
    );

    // Should have at least 3 source links (one per entity)
    expect(sourceLinks.length).toBeGreaterThanOrEqual(3);

    // Check one has the expected href
    const aboutLink = sourceLinks.find(
      (link) => link.getAttribute('href') === 'https://example.com/about'
    );
    expect(aboutLink).toBeInTheDocument();
  });
});

describe('Type Filter', () => {
  const mockShowToast = vi.fn();
  let mockUseEntities: Mock;

  beforeEach(() => {
    vi.clearAllMocks();

    (useParams as Mock).mockReturnValue({ id: 'test-company-1' });

    (useCompany as Mock).mockReturnValue({
      data: mockCompanyData,
      isLoading: false,
    });

    mockUseEntities = vi.fn().mockReturnValue({
      data: {
        data: mockEntities,
        meta: { total: 3, page: 1, pageSize: 20, totalPages: 1 },
      },
      isLoading: false,
    });
    (useEntities as Mock).mockImplementation(mockUseEntities);

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

  it('type filter dropdown shows all options', async () => {
    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    await clickEntitiesTab(user);

    // Wait for entities tab content
    await waitFor(() => {
      expect(screen.getByText('John Smith')).toBeInTheDocument();
    });

    // Find the type filter select
    const typeSelect = screen.getByLabelText(/type/i);
    expect(typeSelect).toBeInTheDocument();

    // Check for All Types option
    const allTypesOption = within(typeSelect).getByRole('option', { name: /all types/i });
    expect(allTypesOption).toBeInTheDocument();

    // Check for entity type options
    expect(within(typeSelect).getByRole('option', { name: /person/i })).toBeInTheDocument();
    expect(within(typeSelect).getByRole('option', { name: /organization/i })).toBeInTheDocument();
    expect(within(typeSelect).getByRole('option', { name: /location/i })).toBeInTheDocument();
    expect(within(typeSelect).getByRole('option', { name: /email/i })).toBeInTheDocument();
  });

  it('selecting type filter updates displayed entities', async () => {
    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    await clickEntitiesTab(user);

    // Wait for entities tab content
    await waitFor(() => {
      expect(screen.getByText('John Smith')).toBeInTheDocument();
    });

    // Clear previous calls
    mockUseEntities.mockClear();

    // Select 'Person' from type filter
    const typeSelect = screen.getByLabelText(/type/i);
    await user.selectOptions(typeSelect, 'person');

    // Assert useEntities was called with type='person'
    await waitFor(() => {
      expect(mockUseEntities).toHaveBeenCalledWith(
        'test-company-1',
        expect.objectContaining({
          type: 'person',
        })
      );
    });
  });

  it('filter resets to page 1 when changed', async () => {
    // Mock with multiple pages
    mockUseEntities.mockReturnValue({
      data: {
        data: mockEntities,
        meta: { total: 50, page: 2, pageSize: 20, totalPages: 3 },
      },
      isLoading: false,
    });

    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    await clickEntitiesTab(user);

    // Wait for entities tab content
    await waitFor(() => {
      expect(screen.getByText('John Smith')).toBeInTheDocument();
    });

    // Clear previous calls
    mockUseEntities.mockClear();

    // Change type filter
    const typeSelect = screen.getByLabelText(/type/i);
    await user.selectOptions(typeSelect, 'org');

    // Assert useEntities was called with page=1
    await waitFor(() => {
      expect(mockUseEntities).toHaveBeenCalledWith(
        'test-company-1',
        expect.objectContaining({
          page: 1,
        })
      );
    });
  });
});

describe('Pagination', () => {
  const mockShowToast = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useParams as Mock).mockReturnValue({ id: 'test-company-1' });

    (useCompany as Mock).mockReturnValue({
      data: mockCompanyData,
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

  it('shows pagination when more than one page', async () => {
    (useEntities as Mock).mockReturnValue({
      data: {
        data: mockEntities,
        meta: { total: 50, page: 1, pageSize: 20, totalPages: 3 },
      },
      isLoading: false,
    });

    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    await clickEntitiesTab(user);

    await waitFor(() => {
      expect(screen.getByText('John Smith')).toBeInTheDocument();
    });

    // Assert pagination text visible
    expect(screen.getByText(/page 1 of 3/i)).toBeInTheDocument();

    // Assert Previous and Next buttons visible
    expect(screen.getByRole('button', { name: /previous/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /next/i })).toBeInTheDocument();
  });

  it('hides pagination when only one page', async () => {
    (useEntities as Mock).mockReturnValue({
      data: {
        data: mockEntities,
        meta: { total: 3, page: 1, pageSize: 20, totalPages: 1 },
      },
      isLoading: false,
    });

    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    await clickEntitiesTab(user);

    await waitFor(() => {
      expect(screen.getByText('John Smith')).toBeInTheDocument();
    });

    // Pagination should not be visible when only one page
    expect(screen.queryByText(/page 1 of 1/i)).not.toBeInTheDocument();
    // Only look within the entities tab for pagination buttons (not all pages)
    const entitiesPanel = screen.getByRole('tabpanel');
    expect(within(entitiesPanel).queryByRole('button', { name: /^previous$/i })).not.toBeInTheDocument();
  });

  it('Previous button disabled on page 1', async () => {
    (useEntities as Mock).mockReturnValue({
      data: {
        data: mockEntities,
        meta: { total: 50, page: 1, pageSize: 20, totalPages: 3 },
      },
      isLoading: false,
    });

    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    await clickEntitiesTab(user);

    await waitFor(() => {
      expect(screen.getByText('John Smith')).toBeInTheDocument();
    });

    // Assert Previous button is disabled on page 1
    const prevButton = screen.getByRole('button', { name: /previous/i });
    expect(prevButton).toBeDisabled();
  });

  it('Next button disabled on last page', async () => {
    // The component manages its own page state starting at 1, so we need to
    // navigate to the last page by clicking Next multiple times
    const mockUseEntities = vi.fn();
    // Return data that simulates being on page 1 initially, then updates
    mockUseEntities.mockReturnValue({
      data: {
        data: mockEntities,
        meta: { total: 50, page: 1, pageSize: 20, totalPages: 3 },
      },
      isLoading: false,
    });
    (useEntities as Mock).mockImplementation(mockUseEntities);

    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    await clickEntitiesTab(user);

    await waitFor(() => {
      expect(screen.getByText('John Smith')).toBeInTheDocument();
    });

    // Simulate being on page 3 by updating the mock to return last page
    mockUseEntities.mockReturnValue({
      data: {
        data: mockEntities,
        meta: { total: 50, page: 3, pageSize: 20, totalPages: 3 },
      },
      isLoading: false,
    });

    // Click Next twice to get to page 3
    const nextButton = screen.getByRole('button', { name: /next/i });
    await user.click(nextButton);
    await user.click(nextButton);

    // Wait for page state to update and Next to be disabled
    await waitFor(() => {
      expect(screen.getByText(/page 3 of 3/i)).toBeInTheDocument();
    });

    // Assert Next button is disabled on last page
    expect(screen.getByRole('button', { name: /next/i })).toBeDisabled();
  });

  it('clicking Next increments page', async () => {
    const mockUseEntities = vi.fn().mockReturnValue({
      data: {
        data: mockEntities,
        meta: { total: 50, page: 1, pageSize: 20, totalPages: 3 },
      },
      isLoading: false,
    });
    (useEntities as Mock).mockImplementation(mockUseEntities);

    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    await clickEntitiesTab(user);

    await waitFor(() => {
      expect(screen.getByText('John Smith')).toBeInTheDocument();
    });

    // Clear previous calls
    mockUseEntities.mockClear();

    // Click Next button
    const nextButton = screen.getByRole('button', { name: /next/i });
    await user.click(nextButton);

    // Assert page was incremented to 2
    await waitFor(() => {
      expect(mockUseEntities).toHaveBeenCalledWith(
        'test-company-1',
        expect.objectContaining({
          page: 2,
        })
      );
    });
  });

  it('clicking Previous decrements page', async () => {
    const mockUseEntities = vi.fn().mockReturnValue({
      data: {
        data: mockEntities,
        meta: { total: 50, page: 1, pageSize: 20, totalPages: 3 },
      },
      isLoading: false,
    });
    (useEntities as Mock).mockImplementation(mockUseEntities);

    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    await clickEntitiesTab(user);

    await waitFor(() => {
      expect(screen.getByText('John Smith')).toBeInTheDocument();
    });

    // First click Next to get to page 2 (so Previous is enabled)
    const nextButton = screen.getByRole('button', { name: /next/i });
    await user.click(nextButton);

    // Clear previous calls
    mockUseEntities.mockClear();

    // Now click Previous button
    const prevButton = screen.getByRole('button', { name: /previous/i });
    await user.click(prevButton);

    // Assert page was decremented to 1
    await waitFor(() => {
      expect(mockUseEntities).toHaveBeenCalledWith(
        'test-company-1',
        expect.objectContaining({
          page: 1,
        })
      );
    });
  });
});

describe('Loading and Empty States', () => {
  const mockShowToast = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useParams as Mock).mockReturnValue({ id: 'test-company-1' });

    (useCompany as Mock).mockReturnValue({
      data: mockCompanyData,
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

  it('shows skeleton while loading entities', async () => {
    (useEntities as Mock).mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    await clickEntitiesTab(user);

    // Wait for tab to be active
    await waitFor(() => {
      const tabPanel = screen.getByRole('tabpanel');
      expect(tabPanel).toBeInTheDocument();
    });

    // Assert skeleton elements are visible (have animate-pulse class)
    const skeletons = document.querySelectorAll('[class*="animate-pulse"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('shows empty message when no entities', async () => {
    (useEntities as Mock).mockReturnValue({
      data: {
        data: [],
        meta: { total: 0, page: 1, pageSize: 20, totalPages: 1 },
      },
      isLoading: false,
    });

    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    await clickEntitiesTab(user);

    // Assert 'No entities found' message visible
    await waitFor(() => {
      expect(screen.getByText(/no entities found/i)).toBeInTheDocument();
    });
  });

  it('shows entity count', async () => {
    (useEntities as Mock).mockReturnValue({
      data: {
        data: mockEntities,
        meta: { total: 42, page: 1, pageSize: 20, totalPages: 3 },
      },
      isLoading: false,
    });

    const user = userEvent.setup();
    render(<CompanyResults />, { wrapper: createTestWrapper() });

    await clickEntitiesTab(user);

    // Assert entity count visible
    await waitFor(() => {
      expect(screen.getByText(/42 entities found/i)).toBeInTheDocument();
    });
  });
});

describe('Entity Count in Tab', () => {
  const mockShowToast = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useParams as Mock).mockReturnValue({ id: 'test-company-1' });

    (useEntities as Mock).mockReturnValue({
      data: {
        data: mockEntities,
        meta: { total: 3, page: 1, pageSize: 20, totalPages: 1 },
      },
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

  it('tab shows entity count', () => {
    // Mock company with specific entity count
    (useCompany as Mock).mockReturnValue({
      data: {
        ...mockCompanyData,
        data: {
          ...mockCompanyData.data,
          entityCount: 15,
        },
      },
      isLoading: false,
    });

    render(<CompanyResults />, { wrapper: createTestWrapper() });

    // Assert tab label shows 'Entities (15)'
    const entitiesTab = screen.getByRole('tab', { name: /entities.*15/i });
    expect(entitiesTab).toBeInTheDocument();
  });

  it('tab shows correct count from company data', () => {
    (useCompany as Mock).mockReturnValue({
      data: mockCompanyData, // entityCount is 42
      isLoading: false,
    });

    render(<CompanyResults />, { wrapper: createTestWrapper() });

    // Assert tab label shows 'Entities (42)'
    const entitiesTab = screen.getByRole('tab', { name: /entities.*42/i });
    expect(entitiesTab).toBeInTheDocument();
  });
});
