/**
 * Company Results Page - Analysis results display
 *
 * Implements Task 8.5: Results View Page
 * - Tabs: Summary, Entities, Pages, Token Usage
 * - Summary: markdown, sidebar info
 * - Export dropdown
 * - Re-scan button
 */

import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  useCompany,
  useEntities,
  usePages,
  useTokens,
  useRescanCompany,
} from '../hooks/useCompanies';
import { exportAnalysis } from '../api/companies';
import {
  Button,
  Card,
  Tabs,
  Table,
  Badge,
  getStatusBadgeVariant,
  Select,
  Skeleton,
  Modal,
  useToast,
} from '../components/ui';
import type { Tab, TableColumn } from '../components/ui';
import type { Entity, Page, EntityType, PageType } from '../types';

// Utility functions
function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return num.toString();
}

function formatCost(cost: number): string {
  return '$' + cost.toFixed(4);
}

// Entity type labels
const ENTITY_TYPE_LABELS: Record<EntityType, string> = {
  person: 'Person',
  org: 'Organization',
  location: 'Location',
  product: 'Product',
  date: 'Date',
  money: 'Money',
  email: 'Email',
  phone: 'Phone',
  address: 'Address',
  social_handle: 'Social Handle',
  tech_stack: 'Tech Stack',
};

// Page type labels
const PAGE_TYPE_LABELS: Record<PageType, string> = {
  about: 'About',
  team: 'Team',
  product: 'Product',
  service: 'Service',
  contact: 'Contact',
  careers: 'Careers',
  pricing: 'Pricing',
  blog: 'Blog',
  news: 'News',
  other: 'Other',
};

const EXPORT_OPTIONS = [
  { value: 'markdown', label: 'Markdown (.md)' },
  { value: 'pdf', label: 'PDF (.pdf)' },
  { value: 'word', label: 'Word (.docx)' },
  { value: 'json', label: 'JSON (.json)' },
];

const ENTITY_TYPE_OPTIONS = [
  { value: '', label: 'All Types' },
  ...Object.entries(ENTITY_TYPE_LABELS).map(([value, label]) => ({ value, label })),
];

const PAGE_TYPE_OPTIONS = [
  { value: '', label: 'All Types' },
  ...Object.entries(PAGE_TYPE_LABELS).map(([value, label]) => ({ value, label })),
];

export default function CompanyResults() {
  const { id } = useParams<{ id: string }>();
  const { showToast } = useToast();

  // Filter state
  const [entityTypeFilter, setEntityTypeFilter] = useState('');
  const [pageTypeFilter, setPageTypeFilter] = useState('');
  const [entityPage, setEntityPage] = useState(1);
  const [pagePage, setPagePage] = useState(1);

  // Export state
  const [exportFormat, setExportFormat] = useState('');
  const [isExporting, setIsExporting] = useState(false);

  // Rescan modal state
  const [rescanModalOpen, setRescanModalOpen] = useState(false);

  // Fetch data
  const { data: companyData, isLoading: companyLoading } = useCompany(id || '');
  const { data: entitiesData, isLoading: entitiesLoading } = useEntities(id || '', {
    type: entityTypeFilter || undefined,
    page: entityPage,
    pageSize: 20,
  });
  const { data: pagesData, isLoading: pagesLoading } = usePages(id || '', {
    pageType: pageTypeFilter || undefined,
    page: pagePage,
    pageSize: 20,
  });
  const { data: tokensData, isLoading: tokensLoading } = useTokens(id || '');

  // Mutations
  const rescanMutation = useRescanCompany();

  // Handle export
  const handleExport = async (format: string) => {
    if (!id || !format) return;
    setIsExporting(true);
    try {
      const blob = await exportAnalysis(id, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const extension = format === 'word' ? 'docx' : format;
      a.download = `${companyData?.data.company.companyName || 'analysis'}-analysis.${extension}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      showToast({
        type: 'success',
        message: 'Export downloaded successfully',
      });
    } catch {
      showToast({
        type: 'error',
        message: 'Failed to export analysis',
      });
    } finally {
      setIsExporting(false);
      setExportFormat('');
    }
  };

  // Handle rescan
  const handleRescan = async () => {
    if (!id) return;
    try {
      await rescanMutation.mutateAsync(id);
      showToast({
        type: 'success',
        message: 'Re-scan started! Redirecting to progress...',
      });
      setRescanModalOpen(false);
      // Redirect happens automatically via navigation
    } catch {
      showToast({
        type: 'error',
        message: 'Failed to start re-scan',
      });
    }
  };

  // Entity table columns
  const entityColumns: TableColumn<Entity>[] = [
    {
      key: 'entityType',
      header: 'Type',
      render: (_value, entity) => (
        <Badge variant="default" size="sm">
          {ENTITY_TYPE_LABELS[entity.entityType] || entity.entityType}
        </Badge>
      ),
    },
    {
      key: 'entityValue',
      header: 'Value',
      render: (_value, entity) => (
        <div>
          <div className="font-medium text-neutral-900">{entity.entityValue}</div>
          {entity.contextSnippet && (
            <div className="text-xs text-neutral-500 truncate max-w-md mt-1">
              ...{entity.contextSnippet}...
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'confidenceScore',
      header: 'Confidence',
      render: (_value, entity) => (
        <div className="flex items-center gap-2">
          <div className="w-16 h-2 bg-neutral-200 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${
                entity.confidenceScore >= 0.8
                  ? 'bg-success'
                  : entity.confidenceScore >= 0.6
                  ? 'bg-warning'
                  : 'bg-error'
              }`}
              style={{ width: `${entity.confidenceScore * 100}%` }}
            />
          </div>
          <span className="text-sm text-neutral-600">
            {Math.round(entity.confidenceScore * 100)}%
          </span>
        </div>
      ),
    },
    {
      key: 'sourceUrl',
      header: 'Source',
      render: (_value, entity) => (
        <a
          href={entity.sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary hover:underline text-sm truncate block max-w-xs"
        >
          {new URL(entity.sourceUrl).pathname || '/'}
        </a>
      ),
    },
  ];

  // Page table columns
  const pageColumns: TableColumn<Page>[] = [
    {
      key: 'pageType',
      header: 'Type',
      render: (_value, page) => (
        <Badge variant={page.isExternal ? 'warning' : 'default'} size="sm">
          {PAGE_TYPE_LABELS[page.pageType] || page.pageType}
          {page.isExternal && ' (External)'}
        </Badge>
      ),
    },
    {
      key: 'url',
      header: 'URL',
      render: (_value, page) => (
        <a
          href={page.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary hover:underline truncate block max-w-lg"
        >
          {page.url}
        </a>
      ),
    },
    {
      key: 'crawledAt',
      header: 'Crawled',
      render: (_value, page) => (
        <span className="text-neutral-600 text-sm">{formatDate(page.crawledAt)}</span>
      ),
    },
  ];

  // Loading state
  if (companyLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Skeleton className="h-6 w-16" />
            <Skeleton className="h-9 w-48" />
          </div>
          <div className="flex gap-3">
            <Skeleton className="h-10 w-24" />
            <Skeleton className="h-10 w-24" />
          </div>
        </div>
        <Skeleton className="h-12 w-full" />
        <div className="grid grid-cols-3 gap-6">
          <div className="col-span-2">
            <Skeleton className="h-[500px]" />
          </div>
          <Skeleton className="h-[500px]" />
        </div>
      </div>
    );
  }

  // Error or not found
  if (!companyData || !id) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Link
            to="/"
            className="text-neutral-500 hover:text-neutral-700 flex items-center gap-1"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10 19l-7-7m0 0l7-7m-7 7h18"
              />
            </svg>
            Back
          </Link>
          <h1 className="text-3xl font-bold text-neutral-900">Company Not Found</h1>
        </div>
        <Card>
          <p className="text-neutral-600 text-center py-8">
            The requested company could not be found.
          </p>
        </Card>
      </div>
    );
  }

  const company = companyData.data.company;
  const analysis = companyData.data.analysis;
  const entityCount = companyData.data.entityCount;
  const pageCount = companyData.data.pageCount;

  // Summary tab content
  const SummaryContent = (
    <div className="grid grid-cols-3 gap-6">
      {/* Main Content */}
      <div className="col-span-2">
        <Card>
          {analysis ? (
            <div className="prose prose-neutral max-w-none">
              <h2 className="text-xl font-semibold mb-4">Executive Summary</h2>
              <div className="whitespace-pre-wrap text-neutral-700">
                {analysis.executiveSummary}
              </div>

              {analysis.fullAnalysis?.companyOverview && (
                <>
                  <h3 className="text-lg font-semibold mt-6 mb-3">Company Overview</h3>
                  <p className="text-neutral-600">
                    {analysis.fullAnalysis.companyOverview.content}
                  </p>
                </>
              )}

              {analysis.fullAnalysis?.businessModelProducts && (
                <>
                  <h3 className="text-lg font-semibold mt-6 mb-3">Business Model & Products</h3>
                  <p className="text-neutral-600">
                    {analysis.fullAnalysis.businessModelProducts.content}
                  </p>
                </>
              )}

              {analysis.fullAnalysis?.teamLeadership && (
                <>
                  <h3 className="text-lg font-semibold mt-6 mb-3">Team & Leadership</h3>
                  <p className="text-neutral-600">
                    {analysis.fullAnalysis.teamLeadership.content}
                  </p>
                </>
              )}

              {analysis.fullAnalysis?.marketPosition && (
                <>
                  <h3 className="text-lg font-semibold mt-6 mb-3">Market Position</h3>
                  <p className="text-neutral-600">
                    {analysis.fullAnalysis.marketPosition.content}
                  </p>
                </>
              )}

              {analysis.fullAnalysis?.keyInsights && (
                <>
                  <h3 className="text-lg font-semibold mt-6 mb-3">Key Insights</h3>
                  <p className="text-neutral-600">
                    {analysis.fullAnalysis.keyInsights.content}
                  </p>
                </>
              )}

              {analysis.fullAnalysis?.redFlags && (
                <>
                  <h3 className="text-lg font-semibold mt-6 mb-3 text-warning">
                    Red Flags & Concerns
                  </h3>
                  <p className="text-neutral-600">
                    {analysis.fullAnalysis.redFlags.content}
                  </p>
                </>
              )}
            </div>
          ) : (
            <p className="text-neutral-500 text-center py-8">
              No analysis available yet.
            </p>
          )}
        </Card>
      </div>

      {/* Sidebar */}
      <div className="space-y-6">
        {/* Company Info */}
        <Card padding="sm">
          <h3 className="font-semibold text-neutral-900 mb-4">Company Info</h3>
          <dl className="space-y-3">
            <div>
              <dt className="text-xs text-neutral-500 uppercase">Status</dt>
              <dd className="mt-1">
                <Badge variant={getStatusBadgeVariant(company.status)}>
                  {company.status.replace('_', ' ')}
                </Badge>
              </dd>
            </div>
            {company.industry && (
              <div>
                <dt className="text-xs text-neutral-500 uppercase">Industry</dt>
                <dd className="text-neutral-900">{company.industry}</dd>
              </div>
            )}
            <div>
              <dt className="text-xs text-neutral-500 uppercase">Analysis Mode</dt>
              <dd className="text-neutral-900 capitalize">{company.analysisMode}</dd>
            </div>
            <div>
              <dt className="text-xs text-neutral-500 uppercase">Created</dt>
              <dd className="text-neutral-900">{formatDate(company.createdAt)}</dd>
            </div>
            {company.completedAt && (
              <div>
                <dt className="text-xs text-neutral-500 uppercase">Completed</dt>
                <dd className="text-neutral-900">{formatDate(company.completedAt)}</dd>
              </div>
            )}
          </dl>
        </Card>

        {/* Stats */}
        <Card padding="sm">
          <h3 className="font-semibold text-neutral-900 mb-4">Statistics</h3>
          <dl className="space-y-3">
            <div className="flex justify-between">
              <dt className="text-neutral-500">Pages Crawled</dt>
              <dd className="font-medium">{pageCount}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-neutral-500">Entities Found</dt>
              <dd className="font-medium">{entityCount}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-neutral-500">Tokens Used</dt>
              <dd className="font-medium">{formatNumber(company.totalTokensUsed)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-neutral-500">Estimated Cost</dt>
              <dd className="font-medium">{formatCost(company.estimatedCost)}</dd>
            </div>
          </dl>
        </Card>

        {/* Version Info */}
        {analysis && (
          <Card padding="sm">
            <h3 className="font-semibold text-neutral-900 mb-4">Analysis Version</h3>
            <p className="text-neutral-600">
              Version {analysis.versionNumber}
            </p>
            <p className="text-sm text-neutral-500 mt-1">
              Generated {formatDate(analysis.createdAt)}
            </p>
          </Card>
        )}
      </div>
    </div>
  );

  // Entities tab content
  const EntitiesContent = (
    <Card>
      <div className="space-y-4">
        {/* Filter */}
        <div className="flex items-center gap-4">
          <div className="w-48">
            <Select
              label="Type"
              options={ENTITY_TYPE_OPTIONS}
              value={entityTypeFilter}
              onChange={(value) => {
                setEntityTypeFilter(value);
                setEntityPage(1);
              }}
              placeholder="Filter by type..."
            />
          </div>
          <span className="text-sm text-neutral-500">
            {entitiesData?.meta.total ?? 0} entities found
          </span>
        </div>

        {/* Table */}
        {entitiesLoading ? (
          <Skeleton className="h-[400px]" />
        ) : (
          <>
            <Table
              data={entitiesData?.data ?? []}
              columns={entityColumns}
              emptyMessage="No entities found"
            />

            {/* Pagination */}
            {entitiesData && entitiesData.meta.totalPages > 1 && (
              <div className="flex items-center justify-between pt-4 border-t">
                <span className="text-sm text-neutral-500">
                  Page {entityPage} of {entitiesData.meta.totalPages}
                </span>
                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setEntityPage(entityPage - 1)}
                    disabled={entityPage === 1}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setEntityPage(entityPage + 1)}
                    disabled={entityPage >= entitiesData.meta.totalPages}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </Card>
  );

  // Pages tab content
  const PagesContent = (
    <Card>
      <div className="space-y-4">
        {/* Filter */}
        <div className="flex items-center gap-4">
          <div className="w-48">
            <Select
              label="Type"
              options={PAGE_TYPE_OPTIONS}
              value={pageTypeFilter}
              onChange={(value) => {
                setPageTypeFilter(value);
                setPagePage(1);
              }}
              placeholder="Filter by type..."
            />
          </div>
          <span className="text-sm text-neutral-500">
            {pagesData?.meta.total ?? 0} pages crawled
          </span>
        </div>

        {/* Table */}
        {pagesLoading ? (
          <Skeleton className="h-[400px]" />
        ) : (
          <>
            <Table
              data={pagesData?.data ?? []}
              columns={pageColumns}
              emptyMessage="No pages crawled"
            />

            {/* Pagination */}
            {pagesData && pagesData.meta.totalPages > 1 && (
              <div className="flex items-center justify-between pt-4 border-t">
                <span className="text-sm text-neutral-500">
                  Page {pagePage} of {pagesData.meta.totalPages}
                </span>
                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setPagePage(pagePage - 1)}
                    disabled={pagePage === 1}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setPagePage(pagePage + 1)}
                    disabled={pagePage >= pagesData.meta.totalPages}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </Card>
  );

  // Tokens tab content
  const TokensContent = (
    <Card>
      {tokensLoading ? (
        <Skeleton className="h-[300px]" />
      ) : tokensData?.data ? (
        <div className="space-y-6">
          {/* Summary */}
          <div className="grid grid-cols-4 gap-4">
            <div className="text-center p-4 bg-neutral-50 rounded-lg">
              <div className="text-2xl font-bold text-neutral-900">
                {formatNumber(tokensData.data.totalTokens)}
              </div>
              <div className="text-sm text-neutral-500">Total Tokens</div>
            </div>
            <div className="text-center p-4 bg-neutral-50 rounded-lg">
              <div className="text-2xl font-bold text-neutral-900">
                {formatNumber(tokensData.data.totalInputTokens)}
              </div>
              <div className="text-sm text-neutral-500">Input Tokens</div>
            </div>
            <div className="text-center p-4 bg-neutral-50 rounded-lg">
              <div className="text-2xl font-bold text-neutral-900">
                {formatNumber(tokensData.data.totalOutputTokens)}
              </div>
              <div className="text-sm text-neutral-500">Output Tokens</div>
            </div>
            <div className="text-center p-4 bg-primary-50 rounded-lg">
              <div className="text-2xl font-bold text-primary">
                {formatCost(tokensData.data.estimatedCost)}
              </div>
              <div className="text-sm text-neutral-500">Estimated Cost</div>
            </div>
          </div>

          {/* Breakdown */}
          <div>
            <h3 className="font-semibold text-neutral-900 mb-4">Usage Breakdown</h3>
            <Table
              data={tokensData.data.byApiCall.map((call, idx) => ({ ...call, id: idx }))}
              columns={[
                {
                  key: 'callType',
                  header: 'Call Type',
                  render: (_value, call) => (
                    <Badge variant="default" size="sm">
                      {call.callType}
                    </Badge>
                  ),
                },
                {
                  key: 'section',
                  header: 'Section',
                  render: (_value, call) => call.section || '-',
                },
                {
                  key: 'inputTokens',
                  header: 'Input',
                  render: (_value, call) => formatNumber(call.inputTokens),
                },
                {
                  key: 'outputTokens',
                  header: 'Output',
                  render: (_value, call) => formatNumber(call.outputTokens),
                },
                {
                  key: 'timestamp',
                  header: 'Time',
                  render: (_value, call) => formatDate(call.timestamp),
                },
              ]}
              emptyMessage="No API calls recorded"
            />
          </div>
        </div>
      ) : (
        <p className="text-neutral-500 text-center py-8">
          No token usage data available.
        </p>
      )}
    </Card>
  );

  // Tab definitions with content
  const tabs: Tab[] = [
    { id: 'summary', label: 'Summary', content: SummaryContent },
    { id: 'entities', label: `Entities (${entityCount})`, content: EntitiesContent },
    { id: 'pages', label: `Pages (${pageCount})`, content: PagesContent },
    { id: 'tokens', label: 'Token Usage', content: TokensContent },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            to="/"
            className="text-neutral-500 hover:text-neutral-700 flex items-center gap-1"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10 19l-7-7m0 0l7-7m-7 7h18"
              />
            </svg>
            Back
          </Link>
          <div>
            <h1 className="text-3xl font-bold text-neutral-900">{company.companyName}</h1>
            <p className="text-neutral-500">{company.websiteUrl}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Select
            label="Export"
            options={EXPORT_OPTIONS}
            value={exportFormat}
            onChange={(value) => {
              setExportFormat(value);
              if (value) handleExport(value);
            }}
            placeholder="Export..."
            disabled={isExporting}
          />
          <Button onClick={() => setRescanModalOpen(true)}>Re-scan</Button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs tabs={tabs} defaultTab="summary" />

      {/* Re-scan Confirmation Modal */}
      <Modal
        isOpen={rescanModalOpen}
        onClose={() => setRescanModalOpen(false)}
        title="Re-scan Company"
        size="sm"
      >
        <div className="space-y-4">
          <p className="text-neutral-600">
            This will start a new analysis for <strong>{company.companyName}</strong>.
            The new analysis will be saved as a new version (keeping the previous one).
          </p>
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setRescanModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleRescan} loading={rescanMutation.isPending}>
              Start Re-scan
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
