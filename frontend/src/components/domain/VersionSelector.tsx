/**
 * VersionSelector - Select analysis versions for viewing or comparison
 *
 * Part of Task 8.6: Domain-Specific Components
 * Used with Task 9.3: Re-scan with Change Detection
 */

import { Select } from '../ui';

export interface VersionItem {
  analysisId: string;
  versionNumber: number;
  createdAt: string;
  tokensUsed?: number;
}

interface VersionSelectorProps {
  /** List of available versions */
  versions: VersionItem[];
  /** Currently selected version number */
  currentVersion: number;
  /** Callback when a version is selected */
  onSelect: (versionNumber: number) => void;
  /** Label for the selector */
  label?: string;
  /** Disable the selector */
  disabled?: boolean;
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

/**
 * Version selector component for choosing between analysis versions.
 * Displays version number and creation date for each option.
 */
export function VersionSelector({
  versions,
  currentVersion,
  onSelect,
  label = 'Version',
  disabled = false,
}: VersionSelectorProps) {
  const options = versions.map((v) => ({
    value: String(v.versionNumber),
    label: `Version ${v.versionNumber} (${formatDate(v.createdAt)})`,
  }));

  const handleChange = (value: string) => {
    onSelect(parseInt(value, 10));
  };

  return (
    <Select
      label={label}
      options={options}
      value={String(currentVersion)}
      onChange={handleChange}
      disabled={disabled}
    />
  );
}
