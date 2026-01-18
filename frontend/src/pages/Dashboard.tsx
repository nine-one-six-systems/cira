/**
 * Dashboard Page - Main company list view
 *
 * Implements Task 8.1: Dashboard / Company List Page
 * - Table: Name, Website, Status, Tokens, Actions
 * - Filters: status, date range, search
 * - Pagination
 * - Actions: View, Export, Delete
 */

import { useState, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  useCompanies,
  useDeleteCompany,
} from '../hooks/useCompanies';
import {
  Table,
  Button,
  Badge,
  getStatusBadgeVariant,
  Select,
  Input,
  Modal,
  Skeleton,
  useToast,
} from '../components/ui';
import type { TableColumn } from '../components/ui';
import type { Company } from '../types';
import { exportAnalysis } from '../api/companies';

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
  { value: 'paused', label: 'Paused' },
];

const SORT_OPTIONS = [
  { value: 'createdAt', label: 'Date Created' },
  { value: 'companyName', label: 'Company Name' },
  { value: 'status', label: 'Status' },
  { value: 'totalTokensUsed', label: 'Tokens Used' },
];

const PAGE_SIZE_OPTIONS = [
  { value: '10', label: '10 per page' },
  { value: '25', label: '25 per page' },
  { value: '50', label: '50 per page' },
];

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
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

export default function Dashboard() {
  const navigate = useNavigate();
  const { showToast } = useToast();

  // Filter state
  const [statusFilter, setStatusFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('createdAt');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Delete modal state
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [companyToDelete, setCompanyToDelete] = useState<Company | null>(null);

  // Export state
  const [exportingId, setExportingId] = useState<string | null>(null);

  // Fetch companies
  const { data, isLoading, error, refetch } = useCompanies({
    status: statusFilter || undefined,
    search: searchQuery || undefined,
    sort: sortBy,
    order: sortOrder,
    page: currentPage,
    pageSize,
  });

  // Delete mutation
  const deleteMutation = useDeleteCompany();

  // Table columns
  const columns: TableColumn<Company>[] = useMemo(
    () => [
      {
        key: 'companyName',
        header: 'Company',
        sortable: true,
        render: (_value, company) => (
          <div>
            <div className="font-medium text-neutral-900">{company.companyName}</div>
            <div className="text-sm text-neutral-500 truncate max-w-xs">
              {company.websiteUrl}
            </div>
          </div>
        ),
      },
      {
        key: 'industry',
        header: 'Industry',
        render: (_value, company) => (
          <span className="text-neutral-600">{company.industry || '-'}</span>
        ),
      },
      {
        key: 'status',
        header: 'Status',
        sortable: true,
        render: (_value, company) => (
          <Badge variant={getStatusBadgeVariant(company.status)}>
            {company.status.replace('_', ' ')}
          </Badge>
        ),
      },
      {
        key: 'totalTokensUsed',
        header: 'Tokens',
        sortable: true,
        render: (_value, company) => (
          <div className="text-right">
            <div className="font-medium">{formatNumber(company.totalTokensUsed)}</div>
            <div className="text-sm text-neutral-500">
              {formatCost(company.estimatedCost)}
            </div>
          </div>
        ),
      },
      {
        key: 'createdAt',
        header: 'Created',
        sortable: true,
        render: (_value, company) => (
          <span className="text-neutral-600">{formatDate(company.createdAt)}</span>
        ),
      },
      {
        key: 'actions',
        header: '',
        render: (_value, company) => (
          <div className="flex items-center gap-2 justify-end">
            {company.status === 'in_progress' && (
              <Link
                to={`/companies/${company.id}/progress`}
                className="text-sm text-primary hover:text-primary-700"
              >
                View Progress
              </Link>
            )}
            {company.status === 'completed' && (
              <>
                <Link
                  to={`/companies/${company.id}`}
                  className="text-sm text-primary hover:text-primary-700"
                >
                  View Results
                </Link>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleExport(company.id, 'markdown');
                  }}
                  disabled={exportingId === company.id}
                >
                  {exportingId === company.id ? 'Exporting...' : 'Export'}
                </Button>
              </>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                openDeleteModal(company);
              }}
              className="text-error hover:text-error-700"
            >
              Delete
            </Button>
          </div>
        ),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [exportingId]
  );

  // Handlers
  const handleRowClick = (company: Company) => {
    if (company.status === 'in_progress') {
      navigate(`/companies/${company.id}/progress`);
    } else if (company.status === 'completed') {
      navigate(`/companies/${company.id}`);
    }
  };

  const handleSort = (key: string) => {
    if (key === sortBy) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(key);
      setSortOrder('desc');
    }
    setCurrentPage(1);
  };

  const openDeleteModal = (company: Company) => {
    setCompanyToDelete(company);
    setDeleteModalOpen(true);
  };

  const handleDelete = async () => {
    if (!companyToDelete) return;

    try {
      await deleteMutation.mutateAsync(companyToDelete.id);
      showToast({
        type: 'success',
        message: `Successfully deleted ${companyToDelete.companyName}`,
      });
      setDeleteModalOpen(false);
      setCompanyToDelete(null);
    } catch {
      showToast({
        type: 'error',
        message: `Failed to delete ${companyToDelete.companyName}`,
      });
    }
  };

  const handleExport = async (companyId: string, format: string) => {
    setExportingId(companyId);
    try {
      const blob = await exportAnalysis(companyId, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `analysis-${companyId}.${format === 'word' ? 'docx' : format}`;
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
      setExportingId(null);
    }
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    setCurrentPage(1);
  };

  const handleStatusChange = (value: string) => {
    setStatusFilter(value);
    setCurrentPage(1);
  };

  // Computed values
  const companies = data?.data ?? [];
  const meta = data?.meta;
  const totalPages = meta?.totalPages ?? 1;
  const total = meta?.total ?? 0;

  // Render loading skeleton
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <Skeleton className="h-9 w-48" />
          <div className="flex gap-3">
            <Skeleton className="h-10 w-32" />
            <Skeleton className="h-10 w-32" />
          </div>
        </div>
        <div className="flex gap-4 items-center">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-10 w-40" />
          <Skeleton className="h-10 w-40" />
        </div>
        <div className="bg-white rounded-lg shadow">
          <Skeleton className="h-[400px] w-full" />
        </div>
      </div>
    );
  }

  // Render error state
  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold text-neutral-900">Companies</h1>
        </div>
        <div className="bg-error-50 border border-error-200 rounded-lg p-6 text-center">
          <p className="text-error-700 mb-4">Failed to load companies. Please try again.</p>
          <Button variant="secondary" onClick={() => refetch()}>
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-neutral-900">Companies</h1>
        <div className="flex gap-3">
          <Link to="/batch">
            <Button variant="secondary">Batch Upload</Button>
          </Link>
          <Link to="/add">
            <Button>Add Company</Button>
          </Link>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4 items-center">
        <div className="flex-1 min-w-[200px] max-w-sm">
          <Input
            label="Search"
            type="text"
            placeholder="Search companies..."
            value={searchQuery}
            onChange={handleSearchChange}
          />
        </div>
        <div className="w-40">
          <Select
            label="Status"
            options={STATUS_OPTIONS}
            value={statusFilter}
            onChange={handleStatusChange}
            placeholder="All Statuses"
          />
        </div>
        <div className="w-40">
          <Select
            label="Sort by"
            options={SORT_OPTIONS}
            value={sortBy}
            onChange={(value) => {
              setSortBy(value);
              setCurrentPage(1);
            }}
          />
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
        >
          {sortOrder === 'asc' ? '↑ Ascending' : '↓ Descending'}
        </Button>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {companies.length === 0 ? (
          <div className="p-12 text-center">
            <svg
              className="mx-auto h-12 w-12 text-neutral-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
              />
            </svg>
            <h3 className="mt-4 text-lg font-medium text-neutral-900">No companies found</h3>
            <p className="mt-2 text-neutral-500">
              {searchQuery || statusFilter
                ? 'Try adjusting your search or filter criteria.'
                : 'Get started by adding a company to analyze.'}
            </p>
            {!searchQuery && !statusFilter && (
              <div className="mt-6">
                <Link to="/add">
                  <Button>Add Your First Company</Button>
                </Link>
              </div>
            )}
          </div>
        ) : (
          <>
            <Table
              data={companies}
              columns={columns}
              onRowClick={handleRowClick}
              onSort={handleSort}
            />

            {/* Pagination */}
            <div className="px-6 py-4 border-t border-neutral-200 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <span className="text-sm text-neutral-600">
                  Showing {companies.length} of {total} companies
                </span>
                <Select
                  label="Page size"
                  options={PAGE_SIZE_OPTIONS}
                  value={String(pageSize)}
                  onChange={(value) => {
                    setPageSize(Number(value));
                    setCurrentPage(1);
                  }}
                />
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1}
                >
                  Previous
                </Button>
                <span className="text-sm text-neutral-600 px-2">
                  Page {currentPage} of {totalPages}
                </span>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage >= totalPages}
                >
                  Next
                </Button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={deleteModalOpen}
        onClose={() => {
          setDeleteModalOpen(false);
          setCompanyToDelete(null);
        }}
        title="Delete Company"
        size="sm"
      >
        <div className="space-y-4">
          <p className="text-neutral-600">
            Are you sure you want to delete <strong>{companyToDelete?.companyName}</strong>?
            This will permanently remove all analysis data, entities, and crawled pages.
          </p>
          <div className="flex justify-end gap-3">
            <Button
              variant="secondary"
              onClick={() => {
                setDeleteModalOpen(false);
                setCompanyToDelete(null);
              }}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={handleDelete}
              loading={deleteMutation.isPending}
            >
              Delete
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
