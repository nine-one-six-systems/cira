/**
 * Table Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Table } from './Table';

interface TestData {
  id: string;
  name: string;
  status: string;
}

const columns = [
  { key: 'name' as keyof TestData, header: 'Name', sortable: true },
  { key: 'status' as keyof TestData, header: 'Status' },
];

const data: TestData[] = [
  { id: '1', name: 'Company A', status: 'active' },
  { id: '2', name: 'Company B', status: 'pending' },
];

describe('Table', () => {
  it('renders column headers', () => {
    render(<Table columns={columns} data={data} />);
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();
  });

  it('renders data rows', () => {
    render(<Table columns={columns} data={data} />);
    expect(screen.getByText('Company A')).toBeInTheDocument();
    expect(screen.getByText('Company B')).toBeInTheDocument();
    expect(screen.getByText('active')).toBeInTheDocument();
    expect(screen.getByText('pending')).toBeInTheDocument();
  });

  it('shows empty message when data is empty', () => {
    render(<Table columns={columns} data={[]} emptyMessage="No companies found" />);
    expect(screen.getByText('No companies found')).toBeInTheDocument();
  });

  it('shows default empty message', () => {
    render(<Table columns={columns} data={[]} />);
    expect(screen.getByText('No data available')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    render(<Table columns={columns} data={data} loading />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('calls onRowClick when row is clicked', async () => {
    const handleRowClick = vi.fn();
    const user = userEvent.setup();

    render(<Table columns={columns} data={data} onRowClick={handleRowClick} />);
    await user.click(screen.getByText('Company A'));

    expect(handleRowClick).toHaveBeenCalledWith(data[0]);
  });

  it('calls onSort when sortable header is clicked', async () => {
    const handleSort = vi.fn();
    const user = userEvent.setup();

    render(<Table columns={columns} data={data} onSort={handleSort} />);
    await user.click(screen.getByText('Name'));

    expect(handleSort).toHaveBeenCalledWith('name', 'asc');
  });

  it('toggles sort direction on consecutive clicks', async () => {
    const handleSort = vi.fn();
    const user = userEvent.setup();

    render(<Table columns={columns} data={data} onSort={handleSort} />);

    await user.click(screen.getByText('Name'));
    expect(handleSort).toHaveBeenLastCalledWith('name', 'asc');

    await user.click(screen.getByText('Name'));
    expect(handleSort).toHaveBeenLastCalledWith('name', 'desc');
  });

  it('shows sort indicator on sortable columns', () => {
    render(<Table columns={columns} data={data} />);
    const nameHeader = screen.getByText('Name').closest('th');
    expect(nameHeader?.querySelector('svg')).toBeInTheDocument();
  });

  it('does not call onSort for non-sortable columns', async () => {
    const handleSort = vi.fn();
    const user = userEvent.setup();

    render(<Table columns={columns} data={data} onSort={handleSort} />);
    await user.click(screen.getByText('Status'));

    expect(handleSort).not.toHaveBeenCalled();
  });

  it('uses custom render function when provided', () => {
    const customColumns = [
      ...columns,
      {
        key: 'status' as keyof TestData,
        header: 'Custom Status',
        render: (value: unknown) => <span data-testid="custom">{String(value).toUpperCase()}</span>,
      },
    ];

    render(<Table columns={customColumns} data={data} />);
    expect(screen.getAllByTestId('custom')[0]).toHaveTextContent('ACTIVE');
  });

  it('makes rows keyboard accessible when onRowClick is provided', () => {
    render(<Table columns={columns} data={data} onRowClick={() => {}} />);
    const rows = screen.getAllByRole('row');
    // Skip header row
    expect(rows[1]).toHaveAttribute('tabindex', '0');
  });

  it('triggers onRowClick on Enter key', async () => {
    const handleRowClick = vi.fn();
    const user = userEvent.setup();

    render(<Table columns={columns} data={data} onRowClick={handleRowClick} />);
    const row = screen.getByText('Company A').closest('tr')!;
    row.focus();
    await user.keyboard('{Enter}');

    expect(handleRowClick).toHaveBeenCalledWith(data[0]);
  });

  it('applies aria-sort attribute to sorted column', async () => {
    const user = userEvent.setup();
    render(<Table columns={columns} data={data} onSort={() => {}} />);

    await user.click(screen.getByText('Name'));

    const header = screen.getByText('Name').closest('th');
    expect(header).toHaveAttribute('aria-sort', 'ascending');
  });
});
