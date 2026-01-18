/**
 * ChangeHighlight - Display comparison results between analysis versions
 *
 * Part of Task 8.6: Domain-Specific Components
 * Used with Task 9.3: Re-scan with Change Detection
 */

import { useState } from 'react';
import { Card, Badge } from '../ui';

export interface VersionChange {
  field: string;
  previousValue: unknown;
  currentValue: unknown;
  changeType: 'added' | 'removed' | 'modified';
}

export interface VersionChanges {
  team: VersionChange[];
  products: VersionChange[];
  content: VersionChange[];
}

export interface ComparisonResult {
  companyId: string;
  previousVersion: number;
  currentVersion: number;
  changes: VersionChanges;
  significantChanges: boolean;
}

interface ChangeHighlightProps {
  /** The comparison result to display */
  comparison: ComparisonResult;
}

function ChangeTypeBadge({ type }: { type: 'added' | 'removed' | 'modified' }) {
  const variants: Record<string, 'success' | 'error' | 'warning'> = {
    added: 'success',
    removed: 'error',
    modified: 'warning',
  };

  return (
    <Badge variant={variants[type]} size="sm">
      {type}
    </Badge>
  );
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) {
    return '(none)';
  }
  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2);
  }
  return String(value);
}

function truncateValue(value: unknown, maxLength = 100): string {
  const str = formatValue(value);
  if (str.length > maxLength) {
    return str.substring(0, maxLength) + '...';
  }
  return str;
}

interface ChangeSectionProps {
  title: string;
  changes: VersionChange[];
  defaultExpanded?: boolean;
}

function ChangeSection({ title, changes, defaultExpanded = false }: ChangeSectionProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  if (changes.length === 0) {
    return null;
  }

  return (
    <div className="border border-neutral-200 rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center justify-between bg-neutral-50 hover:bg-neutral-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          <svg
            className={`h-4 w-4 text-neutral-500 transition-transform ${expanded ? 'rotate-90' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
          <span className="font-medium text-neutral-900">{title}</span>
        </div>
        <span className="text-sm text-neutral-500">{changes.length} change{changes.length !== 1 ? 's' : ''}</span>
      </button>

      {expanded && (
        <div className="divide-y divide-neutral-200">
          {changes.map((change, idx) => (
            <div key={idx} className="p-4 space-y-2">
              <div className="flex items-center gap-2">
                <span className="font-medium text-neutral-900">{change.field}</span>
                <ChangeTypeBadge type={change.changeType} />
              </div>

              {change.changeType === 'modified' && (
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 bg-error-50 rounded-lg border border-error-200">
                    <div className="text-xs text-error-600 font-medium mb-1">Previous</div>
                    <pre className="text-sm text-error-800 whitespace-pre-wrap break-words font-mono">
                      {truncateValue(change.previousValue)}
                    </pre>
                  </div>
                  <div className="p-3 bg-success-50 rounded-lg border border-success-200">
                    <div className="text-xs text-success-600 font-medium mb-1">Current</div>
                    <pre className="text-sm text-success-800 whitespace-pre-wrap break-words font-mono">
                      {truncateValue(change.currentValue)}
                    </pre>
                  </div>
                </div>
              )}

              {change.changeType === 'added' && (
                <div className="p-3 bg-success-50 rounded-lg border border-success-200">
                  <div className="text-xs text-success-600 font-medium mb-1">Added</div>
                  <pre className="text-sm text-success-800 whitespace-pre-wrap break-words font-mono">
                    {truncateValue(change.currentValue)}
                  </pre>
                </div>
              )}

              {change.changeType === 'removed' && (
                <div className="p-3 bg-error-50 rounded-lg border border-error-200">
                  <div className="text-xs text-error-600 font-medium mb-1">Removed</div>
                  <pre className="text-sm text-error-800 whitespace-pre-wrap break-words font-mono">
                    {truncateValue(change.previousValue)}
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * ChangeHighlight component displays a comparison between two analysis versions.
 * Shows changes grouped by category (team, products, content) with color-coded
 * diff view (green for added, red for removed, yellow for modified).
 */
export function ChangeHighlight({ comparison }: ChangeHighlightProps) {
  const { previousVersion, currentVersion, changes, significantChanges } = comparison;

  const totalChanges =
    changes.team.length + changes.products.length + changes.content.length;

  if (totalChanges === 0) {
    return (
      <Card padding="md">
        <div className="text-center py-8">
          <svg
            className="mx-auto h-12 w-12 text-success"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <p className="mt-4 text-lg font-medium text-neutral-900">No Changes Detected</p>
          <p className="mt-2 text-neutral-500">
            Version {previousVersion} and Version {currentVersion} appear to be identical.
          </p>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Summary Header */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-neutral-600">
          Comparing Version {previousVersion} → Version {currentVersion}
        </div>
        <div className="flex items-center gap-2">
          {significantChanges ? (
            <Badge variant="warning">Significant Changes</Badge>
          ) : (
            <Badge variant="info">Minor Changes</Badge>
          )}
          <span className="text-sm text-neutral-500">
            {totalChanges} total change{totalChanges !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      {/* Change Sections */}
      <div className="space-y-3">
        <ChangeSection
          title="Team & Leadership"
          changes={changes.team}
          defaultExpanded={changes.team.length > 0}
        />
        <ChangeSection
          title="Products & Services"
          changes={changes.products}
          defaultExpanded={changes.products.length > 0 && changes.team.length === 0}
        />
        <ChangeSection
          title="Content & Analysis"
          changes={changes.content}
          defaultExpanded={
            changes.content.length > 0 &&
            changes.team.length === 0 &&
            changes.products.length === 0
          }
        />
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 pt-2 border-t border-neutral-200">
        <span className="text-xs text-neutral-500">Legend:</span>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-success" />
          <span className="text-xs text-neutral-600">Added</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-error" />
          <span className="text-xs text-neutral-600">Removed</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-warning" />
          <span className="text-xs text-neutral-600">Modified</span>
        </div>
      </div>
    </div>
  );
}
