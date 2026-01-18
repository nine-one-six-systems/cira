/**
 * VersionSelector Component Tests
 *
 * Tests for Task 9.3: Re-scan with Change Detection
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { VersionSelector, type VersionItem } from './VersionSelector';

const mockVersions: VersionItem[] = [
  {
    analysisId: 'v1-id',
    versionNumber: 1,
    createdAt: '2024-01-15T10:00:00Z',
    tokensUsed: 1000,
  },
  {
    analysisId: 'v2-id',
    versionNumber: 2,
    createdAt: '2024-02-20T14:30:00Z',
    tokensUsed: 1500,
  },
  {
    analysisId: 'v3-id',
    versionNumber: 3,
    createdAt: '2024-03-25T09:15:00Z',
    tokensUsed: 1200,
  },
];

describe('VersionSelector', () => {
  it('renders with default label', () => {
    render(
      <VersionSelector
        versions={mockVersions}
        currentVersion={1}
        onSelect={() => {}}
      />
    );

    expect(screen.getByText('Version')).toBeInTheDocument();
  });

  it('renders with custom label', () => {
    render(
      <VersionSelector
        versions={mockVersions}
        currentVersion={1}
        onSelect={() => {}}
        label="Previous Version"
      />
    );

    expect(screen.getByText('Previous Version')).toBeInTheDocument();
  });

  it('displays version options with formatted dates', () => {
    render(
      <VersionSelector
        versions={mockVersions}
        currentVersion={1}
        onSelect={() => {}}
      />
    );

    // Check that select element is present
    const select = screen.getByRole('combobox');
    expect(select).toBeInTheDocument();

    // Check option values
    const options = select.querySelectorAll('option');
    expect(options.length).toBe(3);
    expect(options[0]).toHaveValue('1');
    expect(options[1]).toHaveValue('2');
    expect(options[2]).toHaveValue('3');
  });

  it('shows current version as selected', () => {
    render(
      <VersionSelector
        versions={mockVersions}
        currentVersion={2}
        onSelect={() => {}}
      />
    );

    const select = screen.getByRole('combobox') as HTMLSelectElement;
    expect(select.value).toBe('2');
  });

  it('calls onSelect with version number when changed', () => {
    const onSelect = vi.fn();
    render(
      <VersionSelector
        versions={mockVersions}
        currentVersion={1}
        onSelect={onSelect}
      />
    );

    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: '3' } });

    expect(onSelect).toHaveBeenCalledWith(3);
  });

  it('is disabled when disabled prop is true', () => {
    render(
      <VersionSelector
        versions={mockVersions}
        currentVersion={1}
        onSelect={() => {}}
        disabled={true}
      />
    );

    const select = screen.getByRole('combobox');
    expect(select).toBeDisabled();
  });

  it('handles empty versions array', () => {
    render(
      <VersionSelector
        versions={[]}
        currentVersion={0}
        onSelect={() => {}}
      />
    );

    const select = screen.getByRole('combobox');
    const options = select.querySelectorAll('option');
    expect(options.length).toBe(0);
  });

  it('handles single version', () => {
    const singleVersion = [mockVersions[0]];
    render(
      <VersionSelector
        versions={singleVersion}
        currentVersion={1}
        onSelect={() => {}}
      />
    );

    const select = screen.getByRole('combobox');
    const options = select.querySelectorAll('option');
    expect(options.length).toBe(1);
  });
});
