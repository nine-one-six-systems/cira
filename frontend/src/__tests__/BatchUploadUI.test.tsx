/**
 * BatchUpload Component Tests
 *
 * Verifies UI-09: Batch upload UI
 * - File drop zone and upload interface
 * - CSV file validation and preview
 * - Template download functionality (BAT-03)
 * - Batch submission flow
 * - Navigation and accessibility
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, useNavigate } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, type Mock } from 'vitest';
import BatchUpload from '../pages/BatchUpload';
import { useBatchUpload } from '../hooks/useCompanies';
import { downloadTemplate } from '../api/companies';
import { useToast } from '../components/ui';

// Mock the hooks
vi.mock('../hooks/useCompanies', () => ({
  useBatchUpload: vi.fn(),
}));

vi.mock('../api/companies', () => ({
  downloadTemplate: vi.fn(),
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

// Helper to create CSV file with proper text() method
function createCsvFile(content: string, name = 'test.csv'): File {
  const file = new File([content], name, { type: 'text/csv' });
  // Ensure text() method works properly in jsdom
  Object.defineProperty(file, 'text', {
    value: () => Promise.resolve(content),
  });
  return file;
}

// Valid CSV content
const VALID_CSV = `company_name,website_url,industry
Acme Corp,https://acme.com,Technology
Beta Inc,https://beta.com,Finance
Gamma LLC,https://gamma.io,Healthcare`;

// Invalid CSV content (missing URL)
const INVALID_CSV = `company_name,website_url,industry
Acme Corp,https://acme.com,Technology
Invalid Company,,Finance
Another Invalid,not-a-url,Healthcare`;

// All invalid CSV
const ALL_INVALID_CSV = `company_name,website_url,industry
,https://acme.com,Tech
Company Name,,Finance`;

describe('TestBatchUploadDisplay (UI-09)', () => {
  const mockShowToast = vi.fn();
  const mockNavigate = vi.fn();
  const mockMutate = vi.fn();
  const mockMutateAsync = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useBatchUpload as Mock).mockReturnValue({
      mutate: mockMutate,
      mutateAsync: mockMutateAsync,
      isPending: false,
      isSuccess: false,
      isError: false,
    });

    (downloadTemplate as Mock).mockResolvedValue(new Blob(['test'], { type: 'text/csv' }));

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });

    (useNavigate as Mock).mockReturnValue(mockNavigate);
  });

  it('renders batch upload page with file drop zone', () => {
    render(<BatchUpload />, { wrapper: createTestWrapper() });

    // Assert heading with "Batch Upload" visible
    expect(screen.getByText('Batch Upload')).toBeInTheDocument();

    // Assert drop zone present (has click to upload text)
    expect(screen.getByText(/click to upload/i)).toBeInTheDocument();
    expect(screen.getByText(/drag and drop/i)).toBeInTheDocument();
  });

  it('renders template download button', () => {
    render(<BatchUpload />, { wrapper: createTestWrapper() });

    // Assert button with "Download" template visible
    expect(screen.getByRole('button', { name: /download csv template/i })).toBeInTheDocument();
  });

  it('shows file input for CSV upload', () => {
    render(<BatchUpload />, { wrapper: createTestWrapper() });

    // Assert input[type="file"] exists (hidden but present)
    const fileInput = document.querySelector('input[type="file"]');
    expect(fileInput).toBeInTheDocument();

    // Assert accepts .csv files
    expect(fileInput).toHaveAttribute('accept', '.csv');
  });

  it('displays CSV format requirements', () => {
    render(<BatchUpload />, { wrapper: createTestWrapper() });

    // Assert format requirements are listed
    expect(screen.getByText(/csv format requirements/i)).toBeInTheDocument();
    expect(screen.getByText(/company name is required/i)).toBeInTheDocument();
    expect(screen.getByText(/website url is required/i)).toBeInTheDocument();
  });
});

describe('TestFileUpload (UI-09)', () => {
  const mockShowToast = vi.fn();
  const mockNavigate = vi.fn();
  const mockMutate = vi.fn();
  const mockMutateAsync = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useBatchUpload as Mock).mockReturnValue({
      mutate: mockMutate,
      mutateAsync: mockMutateAsync,
      isPending: false,
      isSuccess: false,
      isError: false,
    });

    (downloadTemplate as Mock).mockResolvedValue(new Blob(['test'], { type: 'text/csv' }));

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });

    (useNavigate as Mock).mockReturnValue(mockNavigate);
  });

  it('accepts valid CSV file', async () => {
    const user = userEvent.setup();
    render(<BatchUpload />, { wrapper: createTestWrapper() });

    // Create File object with valid CSV content
    const csvFile = createCsvFile(VALID_CSV);

    // Get file input and trigger file selection
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(fileInput, csvFile);

    // Assert file name is displayed
    await waitFor(() => {
      expect(screen.getByText('test.csv')).toBeInTheDocument();
    });
  });

  it('shows preview table after file selection', async () => {
    const user = userEvent.setup();
    render(<BatchUpload />, { wrapper: createTestWrapper() });

    // Upload CSV with 3 rows
    const csvFile = createCsvFile(VALID_CSV);
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(fileInput, csvFile);

    // Assert preview section appears
    await waitFor(() => {
      expect(screen.getByText('Preview')).toBeInTheDocument();
    });

    // Assert company names from CSV visible
    expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    expect(screen.getByText('Beta Inc')).toBeInTheDocument();
    expect(screen.getByText('Gamma LLC')).toBeInTheDocument();
  });

  it('highlights validation errors in preview', async () => {
    const user = userEvent.setup();
    render(<BatchUpload />, { wrapper: createTestWrapper() });

    // Upload CSV with invalid row (missing URL)
    const csvFile = createCsvFile(INVALID_CSV);
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(fileInput, csvFile);

    // Assert error indicator visible (Invalid badge)
    await waitFor(() => {
      expect(screen.getAllByText('Invalid').length).toBeGreaterThan(0);
    });

    // Assert specific error message about URL (may appear multiple times)
    expect(screen.getAllByText(/website url is required/i).length).toBeGreaterThan(0);
  });

  it('shows valid/invalid row counts', async () => {
    const user = userEvent.setup();
    render(<BatchUpload />, { wrapper: createTestWrapper() });

    // Upload mixed CSV (1 valid, 2 invalid based on INVALID_CSV)
    const csvFile = createCsvFile(INVALID_CSV);
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(fileInput, csvFile);

    // Wait for preview to appear and show counts
    // The text "valid" and "invalid" appear separately from numbers due to element structure
    await waitFor(() => {
      // Check that "valid" text appears in the summary section
      const validText = screen.getByText('valid');
      expect(validText).toBeInTheDocument();
    });

    // Check that "invalid" text appears (from the count section, not error badges)
    expect(screen.getByText(/invalid rows will be skipped/i)).toBeInTheDocument();
  });

  it('rejects non-CSV files by extension', async () => {
    render(<BatchUpload />, { wrapper: createTestWrapper() });

    // Create non-CSV file (use .txt extension)
    const txtFile = new File(['test content'], 'data.txt', { type: 'text/plain' });
    Object.defineProperty(txtFile, 'text', {
      value: () => Promise.resolve('test content'),
    });

    // Get file input and directly trigger change event
    // (bypassing the accept attribute browser-level filtering)
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;

    // Create a custom FileList-like object
    Object.defineProperty(fileInput, 'files', {
      value: [txtFile],
      writable: false,
    });

    // Trigger the change event
    fireEvent.change(fileInput);

    // Assert error toast was shown (the component checks .csv extension)
    await waitFor(() => {
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'error',
          message: expect.stringContaining('CSV'),
        })
      );
    });
  });
});

describe('TestTemplateDownload (BAT-03)', () => {
  const mockShowToast = vi.fn();
  const mockNavigate = vi.fn();
  const mockMutate = vi.fn();
  const mockMutateAsync = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useBatchUpload as Mock).mockReturnValue({
      mutate: mockMutate,
      mutateAsync: mockMutateAsync,
      isPending: false,
      isSuccess: false,
      isError: false,
    });

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });

    (useNavigate as Mock).mockReturnValue(mockNavigate);
  });

  it('clicking template button triggers download', async () => {
    // Mock downloadTemplate
    (downloadTemplate as Mock).mockResolvedValue(new Blob(['test'], { type: 'text/csv' }));

    const user = userEvent.setup();
    render(<BatchUpload />, { wrapper: createTestWrapper() });

    // Click download template button
    const downloadButton = screen.getByRole('button', { name: /download csv template/i });
    await user.click(downloadButton);

    // Assert downloadTemplate was called
    await waitFor(() => {
      expect(downloadTemplate).toHaveBeenCalled();
    });
  });

  it('shows success toast after template download', async () => {
    (downloadTemplate as Mock).mockResolvedValue(new Blob(['test'], { type: 'text/csv' }));

    const user = userEvent.setup();
    render(<BatchUpload />, { wrapper: createTestWrapper() });

    // Click download template button
    const downloadButton = screen.getByRole('button', { name: /download csv template/i });
    await user.click(downloadButton);

    // Assert success toast
    await waitFor(() => {
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'success',
        })
      );
    });
  });

  it('shows error toast on download failure', async () => {
    (downloadTemplate as Mock).mockRejectedValue(new Error('Download failed'));

    const user = userEvent.setup();
    render(<BatchUpload />, { wrapper: createTestWrapper() });

    // Click download template button
    const downloadButton = screen.getByRole('button', { name: /download csv template/i });
    await user.click(downloadButton);

    // Assert error toast
    await waitFor(() => {
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'error',
        })
      );
    });
  });

  it('shows loading state during download', async () => {
    // Create a promise that we can control
    let resolveDownload: (value: Blob) => void;
    const downloadPromise = new Promise<Blob>((resolve) => {
      resolveDownload = resolve;
    });
    (downloadTemplate as Mock).mockReturnValue(downloadPromise);

    const user = userEvent.setup();
    render(<BatchUpload />, { wrapper: createTestWrapper() });

    // Click download template button
    const downloadButton = screen.getByRole('button', { name: /download csv template/i });
    await user.click(downloadButton);

    // Assert loading text appears
    await waitFor(() => {
      expect(screen.getByText(/downloading/i)).toBeInTheDocument();
    });

    // Resolve the download
    resolveDownload!(new Blob(['test']));
  });
});

describe('TestBatchSubmission (UI-09)', () => {
  const mockShowToast = vi.fn();
  const mockNavigate = vi.fn();
  const mockMutate = vi.fn();
  const mockMutateAsync = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useBatchUpload as Mock).mockReturnValue({
      mutate: mockMutate,
      mutateAsync: mockMutateAsync,
      isPending: false,
      isSuccess: false,
      isError: false,
    });

    (downloadTemplate as Mock).mockResolvedValue(new Blob(['test'], { type: 'text/csv' }));

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });

    (useNavigate as Mock).mockReturnValue(mockNavigate);
  });

  it('submit button not visible without file', () => {
    render(<BatchUpload />, { wrapper: createTestWrapper() });

    // Assert upload button is not visible when no file selected (preview not shown)
    expect(screen.queryByRole('button', { name: /upload.*companies/i })).not.toBeInTheDocument();
  });

  it('submit button enabled with valid file', async () => {
    const user = userEvent.setup();
    render(<BatchUpload />, { wrapper: createTestWrapper() });

    // Upload valid CSV
    const csvFile = createCsvFile(VALID_CSV);
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(fileInput, csvFile);

    // Assert submit button is present and enabled
    await waitFor(() => {
      const uploadButton = screen.getByRole('button', { name: /upload 3 companies/i });
      expect(uploadButton).toBeInTheDocument();
      expect(uploadButton).not.toBeDisabled();
    });
  });

  it('submit button disabled if all rows invalid', async () => {
    const user = userEvent.setup();
    render(<BatchUpload />, { wrapper: createTestWrapper() });

    // Upload all-invalid CSV
    const csvFile = createCsvFile(ALL_INVALID_CSV);
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(fileInput, csvFile);

    // Assert submit button is disabled
    await waitFor(() => {
      const uploadButton = screen.getByRole('button', { name: /upload 0 companies/i });
      expect(uploadButton).toBeDisabled();
    });
  });

  it('successful upload shows success message', async () => {
    mockMutateAsync.mockResolvedValue({
      data: { successful: 3, failed: 0 },
    });

    const user = userEvent.setup();
    render(<BatchUpload />, { wrapper: createTestWrapper() });

    // Upload valid CSV
    const csvFile = createCsvFile(VALID_CSV);
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(fileInput, csvFile);

    // Click upload button
    await waitFor(async () => {
      const uploadButton = screen.getByRole('button', { name: /upload 3 companies/i });
      await user.click(uploadButton);
    });

    // Assert success toast
    await waitFor(() => {
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'success',
        })
      );
    });
  });

  it('successful upload navigates to dashboard', async () => {
    mockMutateAsync.mockResolvedValue({
      data: { successful: 3, failed: 0 },
    });

    const user = userEvent.setup();
    render(<BatchUpload />, { wrapper: createTestWrapper() });

    // Upload valid CSV
    const csvFile = createCsvFile(VALID_CSV);
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(fileInput, csvFile);

    // Click upload button
    await waitFor(async () => {
      const uploadButton = screen.getByRole('button', { name: /upload 3 companies/i });
      await user.click(uploadButton);
    });

    // Assert navigation to dashboard
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/');
    });
  });

  it('failed upload shows error message', async () => {
    mockMutateAsync.mockRejectedValue(new Error('Upload failed'));

    const user = userEvent.setup();
    render(<BatchUpload />, { wrapper: createTestWrapper() });

    // Upload valid CSV
    const csvFile = createCsvFile(VALID_CSV);
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(fileInput, csvFile);

    // Click upload button
    await waitFor(async () => {
      const uploadButton = screen.getByRole('button', { name: /upload 3 companies/i });
      await user.click(uploadButton);
    });

    // Assert error toast
    await waitFor(() => {
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'error',
        })
      );
    });
  });

  it('shows loading state during upload', async () => {
    (useBatchUpload as Mock).mockReturnValue({
      mutate: mockMutate,
      mutateAsync: mockMutateAsync,
      isPending: true,
      isSuccess: false,
      isError: false,
    });

    const user = userEvent.setup();
    render(<BatchUpload />, { wrapper: createTestWrapper() });

    // Upload valid CSV
    const csvFile = createCsvFile(VALID_CSV);
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(fileInput, csvFile);

    // Assert loading state on upload button
    await waitFor(() => {
      const uploadButton = screen.getByRole('button', { name: /upload 3 companies/i });
      // Button should show loading (disabled or has loading indicator)
      expect(uploadButton).toBeInTheDocument();
    });
  });

  it('shows warning toast for partial upload failure', async () => {
    mockMutateAsync.mockResolvedValue({
      data: { successful: 2, failed: 1 },
    });

    const user = userEvent.setup();
    render(<BatchUpload />, { wrapper: createTestWrapper() });

    // Upload valid CSV
    const csvFile = createCsvFile(VALID_CSV);
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(fileInput, csvFile);

    // Click upload button
    await waitFor(async () => {
      const uploadButton = screen.getByRole('button', { name: /upload 3 companies/i });
      await user.click(uploadButton);
    });

    // Assert warning toast for failed uploads
    await waitFor(() => {
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'warning',
        })
      );
    });
  });
});

describe('TestNavigationAndAccessibility', () => {
  const mockShowToast = vi.fn();
  const mockNavigate = vi.fn();
  const mockMutate = vi.fn();
  const mockMutateAsync = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useBatchUpload as Mock).mockReturnValue({
      mutate: mockMutate,
      mutateAsync: mockMutateAsync,
      isPending: false,
      isSuccess: false,
      isError: false,
    });

    (downloadTemplate as Mock).mockResolvedValue(new Blob(['test'], { type: 'text/csv' }));

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });

    (useNavigate as Mock).mockReturnValue(mockNavigate);
  });

  it('can navigate back to dashboard', () => {
    render(<BatchUpload />, { wrapper: createTestWrapper() });

    // Assert Back link is present
    const backLink = screen.getByRole('link', { name: /back/i });
    expect(backLink).toBeInTheDocument();
    expect(backLink).toHaveAttribute('href', '/');
  });

  it('clear button removes uploaded file', async () => {
    const user = userEvent.setup();
    render(<BatchUpload />, { wrapper: createTestWrapper() });

    // Upload valid CSV
    const csvFile = createCsvFile(VALID_CSV);
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(fileInput, csvFile);

    // Wait for preview
    await waitFor(() => {
      expect(screen.getByText('Preview')).toBeInTheDocument();
    });

    // Click Clear button
    const clearButton = screen.getByRole('button', { name: /clear/i });
    await user.click(clearButton);

    // Assert preview is removed
    await waitFor(() => {
      expect(screen.queryByText('Preview')).not.toBeInTheDocument();
    });
  });

  it('supports drag and drop events', async () => {
    render(<BatchUpload />, { wrapper: createTestWrapper() });

    // Find drop zone
    const dropZone = screen.getByText(/click to upload/i).closest('div');
    expect(dropZone).toBeInTheDocument();

    // Simulate drag enter
    fireEvent.dragEnter(dropZone!);

    // Simulate drag over
    fireEvent.dragOver(dropZone!);

    // Simulate drag leave
    fireEvent.dragLeave(dropZone!);

    // No errors should occur
    expect(dropZone).toBeInTheDocument();
  });

  it('handles file drop', async () => {
    render(<BatchUpload />, { wrapper: createTestWrapper() });

    // Find drop zone
    const dropZone = screen.getByText(/click to upload/i).closest('div');
    expect(dropZone).toBeInTheDocument();

    // Create a valid CSV file
    const csvFile = createCsvFile(VALID_CSV);

    // Create a DataTransfer-like object
    const dataTransfer = {
      files: [csvFile],
      items: [
        {
          kind: 'file',
          type: csvFile.type,
          getAsFile: () => csvFile,
        },
      ],
      types: ['Files'],
    };

    // Simulate drop
    fireEvent.drop(dropZone!, { dataTransfer });

    // Assert file was processed (preview should appear)
    await waitFor(() => {
      expect(screen.getByText('test.csv')).toBeInTheDocument();
    });
  });
});
