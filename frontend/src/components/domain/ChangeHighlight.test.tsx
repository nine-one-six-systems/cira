/**
 * ChangeHighlight Component Tests
 *
 * Tests for Task 9.3: Re-scan with Change Detection
 */

import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChangeHighlight, type ComparisonResult } from './ChangeHighlight';

const emptyComparison: ComparisonResult = {
  companyId: 'company-123',
  previousVersion: 1,
  currentVersion: 2,
  changes: {
    team: [],
    products: [],
    content: [],
  },
  significantChanges: false,
};

const comparisonWithChanges: ComparisonResult = {
  companyId: 'company-123',
  previousVersion: 1,
  currentVersion: 2,
  changes: {
    team: [
      {
        field: 'CEO',
        previousValue: 'John Smith',
        currentValue: 'Jane Doe',
        changeType: 'modified',
      },
      {
        field: 'CTO',
        previousValue: null,
        currentValue: 'Bob Wilson',
        changeType: 'added',
      },
    ],
    products: [
      {
        field: 'Product A',
        previousValue: 'Product A',
        currentValue: null,
        changeType: 'removed',
      },
    ],
    content: [
      {
        field: 'executiveSummary',
        previousValue: 'Old summary...',
        currentValue: 'New summary...',
        changeType: 'modified',
      },
    ],
  },
  significantChanges: true,
};

describe('ChangeHighlight', () => {
  describe('Empty changes', () => {
    it('displays no changes message when comparison has no changes', () => {
      render(<ChangeHighlight comparison={emptyComparison} />);

      expect(screen.getByText('No Changes Detected')).toBeInTheDocument();
      expect(
        screen.getByText(/Version 1 and Version 2 appear to be identical/)
      ).toBeInTheDocument();
    });

    it('displays success icon for no changes', () => {
      render(<ChangeHighlight comparison={emptyComparison} />);

      // Check that there's an SVG icon with check mark
      const svg = document.querySelector('svg');
      expect(svg).toBeInTheDocument();
    });
  });

  describe('With changes', () => {
    it('displays version comparison header', () => {
      render(<ChangeHighlight comparison={comparisonWithChanges} />);

      expect(screen.getByText(/Comparing Version 1 → Version 2/)).toBeInTheDocument();
    });

    it('displays significant changes badge when there are significant changes', () => {
      render(<ChangeHighlight comparison={comparisonWithChanges} />);

      expect(screen.getByText('Significant Changes')).toBeInTheDocument();
    });

    it('displays minor changes badge when there are no significant changes', () => {
      const minorChanges = {
        ...comparisonWithChanges,
        significantChanges: false,
      };
      render(<ChangeHighlight comparison={minorChanges} />);

      expect(screen.getByText('Minor Changes')).toBeInTheDocument();
    });

    it('displays total change count', () => {
      render(<ChangeHighlight comparison={comparisonWithChanges} />);

      // 2 team + 1 product + 1 content = 4 total
      expect(screen.getByText('4 total changes')).toBeInTheDocument();
    });

    it('renders Team & Leadership section', () => {
      render(<ChangeHighlight comparison={comparisonWithChanges} />);

      expect(screen.getByText('Team & Leadership')).toBeInTheDocument();
      expect(screen.getByText('2 changes')).toBeInTheDocument();
    });

    it('renders Products & Services section', () => {
      render(<ChangeHighlight comparison={comparisonWithChanges} />);

      expect(screen.getByText('Products & Services')).toBeInTheDocument();
      // The section header shows change count
      const productsSection = screen.getByRole('button', { name: /Products & Services/ });
      expect(productsSection).toBeInTheDocument();
    });

    it('renders Content & Analysis section', () => {
      render(<ChangeHighlight comparison={comparisonWithChanges} />);

      expect(screen.getByText('Content & Analysis')).toBeInTheDocument();
    });
  });

  describe('Section expansion', () => {
    it('first section with changes is expanded by default', () => {
      render(<ChangeHighlight comparison={comparisonWithChanges} />);

      // Team section is first with changes, should be expanded
      expect(screen.getByText('CEO')).toBeInTheDocument();
    });

    it('can toggle section expansion', () => {
      render(<ChangeHighlight comparison={comparisonWithChanges} />);

      // Click on Team & Leadership to collapse
      const teamButton = screen.getByRole('button', { name: /Team & Leadership/ });
      fireEvent.click(teamButton);

      // Content should be hidden after collapse
      // Since we expanded by default, clicking collapses it
      // Let's click again to re-expand
      fireEvent.click(teamButton);

      // Should still show the CEO entry
      expect(screen.getByText('CEO')).toBeInTheDocument();
    });
  });

  describe('Change types', () => {
    it('displays modified badge for modified changes', () => {
      render(<ChangeHighlight comparison={comparisonWithChanges} />);

      const modifiedBadges = screen.getAllByText('modified');
      expect(modifiedBadges.length).toBeGreaterThan(0);
    });

    it('displays added badge for added changes', () => {
      render(<ChangeHighlight comparison={comparisonWithChanges} />);

      expect(screen.getByText('added')).toBeInTheDocument();
    });

    it('displays removed badge for removed changes', () => {
      render(<ChangeHighlight comparison={comparisonWithChanges} />);

      // Click on Products section to expand it (might not be expanded by default)
      const productsButton = screen.getByRole('button', { name: /Products & Services/ });
      fireEvent.click(productsButton);

      expect(screen.getByText('removed')).toBeInTheDocument();
    });
  });

  describe('Modified change display', () => {
    it('shows Previous and Current labels for modified changes', () => {
      render(<ChangeHighlight comparison={comparisonWithChanges} />);

      expect(screen.getByText('Previous')).toBeInTheDocument();
      expect(screen.getByText('Current')).toBeInTheDocument();
    });

    it('shows previous and current values', () => {
      render(<ChangeHighlight comparison={comparisonWithChanges} />);

      expect(screen.getByText('John Smith')).toBeInTheDocument();
      expect(screen.getByText('Jane Doe')).toBeInTheDocument();
    });
  });

  describe('Added change display', () => {
    it('shows Added label in legend for new items', () => {
      render(<ChangeHighlight comparison={comparisonWithChanges} />);

      // The legend shows "Added" with capital A
      const addedInLegend = screen.getAllByText('Added');
      expect(addedInLegend.length).toBeGreaterThan(0);
    });

    it('shows the new value', () => {
      render(<ChangeHighlight comparison={comparisonWithChanges} />);

      expect(screen.getByText('Bob Wilson')).toBeInTheDocument();
    });
  });

  describe('Removed change display', () => {
    it('shows Removed label in legend', () => {
      render(<ChangeHighlight comparison={comparisonWithChanges} />);

      // The legend shows "Removed"
      const removedInLegend = screen.getAllByText('Removed');
      expect(removedInLegend.length).toBeGreaterThan(0);
    });

    it('shows removed badge when Products section is expanded', () => {
      render(<ChangeHighlight comparison={comparisonWithChanges} />);

      // Click on Products section to expand it
      const productsButton = screen.getByRole('button', { name: /Products & Services/ });
      fireEvent.click(productsButton);

      // The badge shows "removed" (lowercase)
      expect(screen.getByText('removed')).toBeInTheDocument();
    });
  });

  describe('Legend', () => {
    it('displays change type legend', () => {
      render(<ChangeHighlight comparison={comparisonWithChanges} />);

      expect(screen.getByText('Legend:')).toBeInTheDocument();
      // Check legend items
      const legendAdded = screen.getAllByText('Added');
      const legendRemoved = screen.getAllByText('Removed');
      const legendModified = screen.getAllByText('Modified');

      expect(legendAdded.length).toBeGreaterThan(0);
      expect(legendRemoved.length).toBeGreaterThan(0);
      expect(legendModified.length).toBeGreaterThan(0);
    });
  });

  describe('Value formatting', () => {
    it('handles null values', () => {
      const comparisonWithNull: ComparisonResult = {
        companyId: 'company-123',
        previousVersion: 1,
        currentVersion: 2,
        changes: {
          team: [
            {
              field: 'CFO',
              previousValue: null,
              currentValue: 'New CFO',
              changeType: 'added',
            },
          ],
          products: [],
          content: [],
        },
        significantChanges: false,
      };

      render(<ChangeHighlight comparison={comparisonWithNull} />);

      expect(screen.getByText('New CFO')).toBeInTheDocument();
    });

    it('handles long values by truncating', () => {
      const longValue = 'A'.repeat(150);
      const comparisonWithLongValue: ComparisonResult = {
        companyId: 'company-123',
        previousVersion: 1,
        currentVersion: 2,
        changes: {
          team: [],
          products: [],
          content: [
            {
              field: 'description',
              previousValue: longValue,
              currentValue: 'Short',
              changeType: 'modified',
            },
          ],
        },
        significantChanges: false,
      };

      render(<ChangeHighlight comparison={comparisonWithLongValue} />);

      // Content section should be expanded by default (it's the only section with changes)
      // Check that the truncated value contains "..." at the end
      // The truncateValue function truncates to 100 chars and adds "..."
      const expectedTruncated = 'A'.repeat(100) + '...';
      expect(screen.getByText(expectedTruncated)).toBeInTheDocument();
    });
  });
});
