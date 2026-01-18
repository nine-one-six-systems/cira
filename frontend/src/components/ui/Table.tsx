/**
 * Table Component
 *
 * A generic table component with sorting and row click support.
 */

import { useState, useCallback } from 'react';

export interface TableColumn<T> {
  /** Key of the data field */
  key: keyof T | string;
  /** Header display text */
  header: string;
  /** Whether the column is sortable */
  sortable?: boolean;
  /** Custom render function */
  render?: (value: unknown, row: T) => React.ReactNode;
  /** Width class (e.g., 'w-1/4') */
  width?: string;
}

export interface TableProps<T extends { id?: string | number }> {
  /** Column definitions */
  columns: TableColumn<T>[];
  /** Data rows */
  data: T[];
  /** Sort handler */
  onSort?: (key: string, direction: 'asc' | 'desc') => void;
  /** Row click handler */
  onRowClick?: (row: T) => void;
  /** Whether to show loading state */
  loading?: boolean;
  /** Message to show when data is empty */
  emptyMessage?: string;
}

/**
 * Table component with sorting and row selection.
 *
 * @example
 * ```tsx
 * <Table
 *   columns={[
 *     { key: 'name', header: 'Name', sortable: true },
 *     { key: 'status', header: 'Status', render: (v) => <Badge>{v}</Badge> },
 *   ]}
 *   data={companies}
 *   onSort={(key, dir) => setSort({ key, dir })}
 *   onRowClick={(row) => navigate(`/company/${row.id}`)}
 * />
 * ```
 */
export function Table<T extends { id?: string | number }>({
  columns,
  data,
  onSort,
  onRowClick,
  loading = false,
  emptyMessage = 'No data available',
}: TableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  const handleSort = useCallback(
    (key: string) => {
      const newDirection = sortKey === key && sortDirection === 'asc' ? 'desc' : 'asc';
      setSortKey(key);
      setSortDirection(newDirection);
      onSort?.(key, newDirection);
    },
    [sortKey, sortDirection, onSort]
  );

  const getValue = (row: T, key: keyof T | string): unknown => {
    if (typeof key === 'string' && key.includes('.')) {
      const parts = key.split('.');
      let value: unknown = row;
      for (const part of parts) {
        value = (value as Record<string, unknown>)?.[part];
      }
      return value;
    }
    return row[key as keyof T];
  };

  return (
    <div className="overflow-x-auto rounded-lg border border-neutral-200">
      <table className="min-w-full divide-y divide-neutral-200">
        <thead className="bg-neutral-50">
          <tr>
            {columns.map((column) => (
              <th
                key={String(column.key)}
                scope="col"
                className={`
                  px-4 py-3
                  text-left text-sm font-semibold text-neutral-900
                  ${column.width || ''}
                  ${column.sortable ? 'cursor-pointer select-none hover:bg-neutral-100' : ''}
                `.trim()}
                onClick={column.sortable ? () => handleSort(String(column.key)) : undefined}
                aria-sort={
                  sortKey === String(column.key)
                    ? sortDirection === 'asc'
                      ? 'ascending'
                      : 'descending'
                    : undefined
                }
              >
                <div className="flex items-center gap-2">
                  {column.header}
                  {column.sortable && (
                    <span className="text-neutral-400">
                      {sortKey === String(column.key) ? (
                        sortDirection === 'asc' ? (
                          <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                            <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
                          </svg>
                        ) : (
                          <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                            <path fillRule="evenodd" d="M14.77 12.79a.75.75 0 01-1.06-.02L10 8.832 6.29 12.77a.75.75 0 11-1.08-1.04l4.25-4.5a.75.75 0 011.08 0l4.25 4.5a.75.75 0 01-.02 1.06z" clipRule="evenodd" />
                          </svg>
                        )
                      ) : (
                        <svg className="h-4 w-4 opacity-50" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                          <path d="M10 3a.75.75 0 01.55.24l3.25 3.5a.75.75 0 11-1.1 1.02L10 4.852 7.3 7.76a.75.75 0 01-1.1-1.02l3.25-3.5A.75.75 0 0110 3zm-3.7 9.24a.75.75 0 011.1 1.02L10 16.148l2.7-2.908a.75.75 0 111.1 1.02l-3.25 3.5a.75.75 0 01-1.1 0l-3.25-3.5a.75.75 0 01.1-1.02z" />
                        </svg>
                      )}
                    </span>
                  )}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-neutral-200">
          {loading ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-8 text-center text-neutral-500"
              >
                <div className="flex items-center justify-center gap-2">
                  <svg
                    className="animate-spin h-5 w-5"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Loading...
                </div>
              </td>
            </tr>
          ) : data.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-8 text-center text-neutral-500"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, rowIndex) => (
              <tr
                key={row.id ?? rowIndex}
                className={`
                  ${onRowClick ? 'cursor-pointer hover:bg-neutral-50' : ''}
                  transition-colors duration-150
                `.trim()}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                tabIndex={onRowClick ? 0 : undefined}
                onKeyDown={
                  onRowClick
                    ? (e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          onRowClick(row);
                        }
                      }
                    : undefined
                }
              >
                {columns.map((column) => {
                  const value = getValue(row, column.key);
                  return (
                    <td
                      key={String(column.key)}
                      className={`px-4 py-3 text-sm text-neutral-700 ${column.width || ''}`}
                    >
                      {column.render ? column.render(value, row) : String(value ?? '')}
                    </td>
                  );
                })}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export default Table;
