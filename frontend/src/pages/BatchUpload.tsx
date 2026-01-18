/**
 * Batch Upload Page - CSV batch upload interface
 *
 * Implements Task 8.3: Batch Upload Page
 * - File drop zone
 * - Template download
 * - Preview table with validation
 * - Confirm valid rows
 */

import { useState, useRef, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useBatchUpload } from '../hooks/useCompanies';
import { downloadTemplate } from '../api/companies';
import {
  Button,
  Card,
  Table,
  Badge,
  useToast,
} from '../components/ui';
import type { TableColumn } from '../components/ui';

interface CsvRow {
  id: number;
  rowNumber: number;
  companyName: string;
  websiteUrl: string;
  industry: string;
  isValid: boolean;
  errors: string[];
}

interface ParseResult {
  rows: CsvRow[];
  validCount: number;
  invalidCount: number;
}

function validateUrl(url: string): boolean {
  if (!url) return false;
  try {
    const withProtocol = url.match(/^https?:\/\//i) ? url : `https://${url}`;
    const parsed = new URL(withProtocol);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

function parseCsv(content: string): ParseResult {
  const lines = content.split('\n').filter((line) => line.trim());
  const rows: CsvRow[] = [];
  let validCount = 0;
  let invalidCount = 0;

  // Skip header row
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i];
    const values = line.split(',').map((v) => v.trim().replace(/^"|"$/g, ''));
    const [companyName, websiteUrl, industry] = values;

    const errors: string[] = [];

    // Validate company name
    if (!companyName) {
      errors.push('Company name is required');
    } else if (companyName.length > 200) {
      errors.push('Company name must be 200 characters or less');
    }

    // Validate URL
    if (!websiteUrl) {
      errors.push('Website URL is required');
    } else if (!validateUrl(websiteUrl)) {
      errors.push('Invalid URL format');
    }

    // Validate industry (optional, but max length)
    if (industry && industry.length > 100) {
      errors.push('Industry must be 100 characters or less');
    }

    const isValid = errors.length === 0;
    if (isValid) {
      validCount++;
    } else {
      invalidCount++;
    }

    rows.push({
      id: i,
      rowNumber: i,
      companyName: companyName || '',
      websiteUrl: websiteUrl || '',
      industry: industry || '',
      isValid,
      errors,
    });
  }

  return { rows, validCount, invalidCount };
}

export default function BatchUpload() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const batchUploadMutation = useBatchUpload();

  // State
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [parseResult, setParseResult] = useState<ParseResult | null>(null);
  const [isDownloadingTemplate, setIsDownloadingTemplate] = useState(false);

  // Handle file selection
  const handleFileSelect = useCallback(async (file: File) => {
    if (!file.name.endsWith('.csv')) {
      showToast({
        type: 'error',
        message: 'Please select a CSV file',
      });
      return;
    }

    setSelectedFile(file);

    // Parse CSV
    try {
      const content = await file.text();
      const result = parseCsv(content);
      setParseResult(result);

      if (result.rows.length === 0) {
        showToast({
          type: 'warning',
          message: 'No valid data rows found in the CSV file',
        });
      }
    } catch {
      showToast({
        type: 'error',
        message: 'Failed to parse CSV file',
      });
    }
  }, [showToast]);

  // Handle drag events
  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  // Handle file input change
  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  // Handle template download
  const handleDownloadTemplate = async () => {
    setIsDownloadingTemplate(true);
    try {
      const blob = await downloadTemplate();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'company-upload-template.csv';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      showToast({
        type: 'success',
        message: 'Template downloaded',
      });
    } catch {
      showToast({
        type: 'error',
        message: 'Failed to download template',
      });
    } finally {
      setIsDownloadingTemplate(false);
    }
  };

  // Handle upload
  const handleUpload = async () => {
    if (!selectedFile || !parseResult || parseResult.validCount === 0) return;

    try {
      const response = await batchUploadMutation.mutateAsync(selectedFile);
      const { successful, failed } = response.data;

      if (successful > 0) {
        showToast({
          type: 'success',
          message: `Successfully queued ${successful} companies for analysis`,
        });
      }

      if (failed > 0) {
        showToast({
          type: 'warning',
          message: `${failed} companies failed to upload`,
        });
      }

      // Navigate to dashboard
      navigate('/');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to upload batch';
      showToast({
        type: 'error',
        message,
      });
    }
  };

  // Clear selection
  const handleClear = () => {
    setSelectedFile(null);
    setParseResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Table columns
  const columns: TableColumn<CsvRow>[] = [
    {
      key: 'rowNumber',
      header: '#',
      render: (_value, row) => <span className="text-neutral-500">{row.rowNumber}</span>,
    },
    {
      key: 'companyName',
      header: 'Company Name',
      render: (_value, row) => (
        <span className={row.errors.some((e) => e.includes('name')) ? 'text-error' : ''}>
          {row.companyName || <span className="text-neutral-400 italic">Empty</span>}
        </span>
      ),
    },
    {
      key: 'websiteUrl',
      header: 'Website URL',
      render: (_value, row) => (
        <span className={row.errors.some((e) => e.includes('URL')) ? 'text-error' : ''}>
          {row.websiteUrl || <span className="text-neutral-400 italic">Empty</span>}
        </span>
      ),
    },
    {
      key: 'industry',
      header: 'Industry',
      render: (_value, row) => row.industry || <span className="text-neutral-400">-</span>,
    },
    {
      key: 'status',
      header: 'Status',
      render: (_value, row) => (
        <div>
          {row.isValid ? (
            <Badge variant="success">Valid</Badge>
          ) : (
            <div className="space-y-1">
              <Badge variant="error">Invalid</Badge>
              <ul className="text-xs text-error list-disc list-inside">
                {row.errors.map((error, i) => (
                  <li key={i}>{error}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
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
        <h1 className="text-3xl font-bold text-neutral-900">Batch Upload</h1>
      </div>

      {/* Upload Area */}
      <Card>
        <div className="space-y-6">
          {/* Drop Zone */}
          <div
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`
              border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
              transition-colors duration-200
              ${isDragging
                ? 'border-primary bg-primary-50'
                : 'border-neutral-300 hover:border-primary hover:bg-neutral-50'
              }
            `}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={handleFileInputChange}
              className="hidden"
            />

            <svg
              className="mx-auto h-12 w-12 text-neutral-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>

            {selectedFile ? (
              <div className="mt-4">
                <p className="text-neutral-900 font-medium">{selectedFile.name}</p>
                <p className="text-sm text-neutral-500">
                  {(selectedFile.size / 1024).toFixed(1)} KB
                </p>
              </div>
            ) : (
              <div className="mt-4">
                <p className="text-neutral-700">
                  <span className="text-primary font-medium">Click to upload</span> or drag
                  and drop
                </p>
                <p className="text-sm text-neutral-500 mt-1">CSV files only</p>
              </div>
            )}
          </div>

          {/* Template Download */}
          <div className="text-center">
            <Button
              variant="ghost"
              onClick={handleDownloadTemplate}
              disabled={isDownloadingTemplate}
            >
              {isDownloadingTemplate ? 'Downloading...' : 'Download CSV Template'}
            </Button>
          </div>
        </div>
      </Card>

      {/* Preview Table */}
      {parseResult && parseResult.rows.length > 0 && (
        <Card>
          <div className="space-y-4">
            {/* Summary */}
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-neutral-900">Preview</h2>
              <div className="flex items-center gap-4 text-sm">
                <span className="text-success">
                  <strong>{parseResult.validCount}</strong> valid
                </span>
                {parseResult.invalidCount > 0 && (
                  <span className="text-error">
                    <strong>{parseResult.invalidCount}</strong> invalid
                  </span>
                )}
              </div>
            </div>

            {/* Table */}
            <div className="border rounded-lg overflow-hidden">
              <Table
                data={parseResult.rows}
                columns={columns}
              />
            </div>

            {/* Actions */}
            <div className="flex items-center justify-between pt-4 border-t border-neutral-200">
              <Button variant="secondary" onClick={handleClear}>
                Clear
              </Button>
              <div className="flex items-center gap-3">
                {parseResult.invalidCount > 0 && (
                  <p className="text-sm text-warning">
                    {parseResult.invalidCount} invalid rows will be skipped
                  </p>
                )}
                <Button
                  onClick={handleUpload}
                  disabled={parseResult.validCount === 0}
                  loading={batchUploadMutation.isPending}
                >
                  Upload {parseResult.validCount} Companies
                </Button>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Instructions */}
      <Card padding="sm">
        <div className="flex items-start gap-3">
          <svg
            className="h-5 w-5 text-primary mt-0.5 flex-shrink-0"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z"
              clipRule="evenodd"
            />
          </svg>
          <div className="text-sm text-neutral-600">
            <p className="font-medium text-neutral-900 mb-2">CSV Format Requirements</p>
            <ul className="list-disc list-inside space-y-1">
              <li>First row must be headers: company_name, website_url, industry</li>
              <li>Company name is required (max 200 characters)</li>
              <li>Website URL is required and must be valid</li>
              <li>Industry is optional (max 100 characters)</li>
            </ul>
          </div>
        </div>
      </Card>
    </div>
  );
}
